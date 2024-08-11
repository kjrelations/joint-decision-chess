from django.db import models
from django.contrib.postgres.fields import ArrayField
from django.contrib.auth.models import AbstractUser
from django_countries.fields import CountryField
from django.utils import timezone
from . import user_settings
import uuid

class User(AbstractUser):
	id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
	email = models.EmailField(unique=True)
	bio = models.TextField(blank=True)
	country = CountryField(blank=True, null=True)
	bot_account = models.BooleanField(default=False)
	email_reference = models.EmailField()
	account_closed = models.BooleanField(default=False)

	def __str__(self):
		return self.username

class UserSettings(models.Model):
	settings_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
	user = models.ForeignKey(User, on_delete=models.CASCADE, null=False)
	themes = ArrayField(models.TextField(), blank=False, null=False, default=user_settings.default_themes)
	username = models.CharField(max_length=150, blank=False)

	def save(self, *args, **kwargs):
		if self.user:
			self.username = self.user.username
		super().save(*args, **kwargs)

class BotInformation(models.Model):
	bot_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
	config = models.TextField(blank=False)

class ChessLobby(models.Model):
	lobby_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
	white_id = models.UUIDField(null=True)
	black_id = models.UUIDField(null=True)
	initiator_name = models.CharField(max_length=150, blank=False, null=False, default="Anonymous")
	opponent_name = models.CharField(max_length=150, blank=False, null=False, default="Waiting...")
	timestamp = models.DateTimeField()
	expire = models.DateTimeField()
	is_open = models.BooleanField(default=True)
	initiator_connected = models.BooleanField(default=False)
	opponent_connected = models.BooleanField(default=False)
	initiator_color = models.CharField(max_length=5, null=True)
	private = models.BooleanField(default=False)
	computer_game = models.BooleanField(default=False)
	solo_game = models.BooleanField(default=False)
	status = models.CharField(max_length=50, blank=False, null=False, default="waiting") # "playing" or "completed"
	gametype = models.CharField(max_length=300, blank=False, null=False, default="")

	def save(self, *args, **kwargs):
		if not self.timestamp:
			self.timestamp = timezone.now()
		if not self.expire:
			self.expire = self.timestamp + timezone.timedelta(minutes=10)
		if self.private:
			self.is_open = False
			self.status = "playing"
		elif self.white_id and self.black_id:
			self.is_open = False
			self.status = "playing"
		elif (self.white_id or self.black_id) and self.initiator_connected:
			self.is_open = True
		else:
			self.is_open = False
		super(ChessLobby, self).save(*args, **kwargs)

	def __str__(self):
		return f"{self.lobby_id}"

class ActiveGames(models.Model):
	active_game_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
	white_id = models.UUIDField(null=False)
	black_id = models.UUIDField(null=False)
	start_time = models.DateTimeField(blank=False, null=False, auto_now_add=True)
	gametype = models.CharField(max_length=300, blank=False, null=False, default="")
	state = models.TextField(default="")

class GameHistoryTable(models.Model):
	historic_game_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
	white_id = models.UUIDField(null=False)
	black_id = models.UUIDField(null=False)
	algebraic_moves = models.TextField(blank=False, null=False, default="")
	start_time = models.DateTimeField(blank=False, null=False)
	end_time = models.DateTimeField(blank=False, null=False, auto_now_add=True)
	gametype = models.CharField(max_length=300, blank=False, null=False, default="")
	outcome = models.CharField(max_length=7, blank=False, null=False, default="")
	computed_moves = models.TextField(blank=False, null=False, default="")
	FEN_outcome = models.CharField(max_length=85, blank=False, null=False, default="")
	termination_reason = models.CharField(max_length=85, blank=True, null=False, default="")

class ActiveChatMessages(models.Model):
	active_message_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
	game_id = models.UUIDField(null=False)
	sender_color = models.CharField(max_length=5, null=True)
	sender = models.UUIDField(null=False)
	sender_username = models.CharField(max_length=150, blank=False, null=False, default="Anonymous")
	message = models.TextField()
	timestamp = models.DateTimeField(default=timezone.now)

class ChatMessages(models.Model):
	message_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
	game_id = models.UUIDField(null=False)
	sender_color = models.CharField(max_length=5, null=True)
	sender = models.UUIDField(null=False)
	sender_username = models.CharField(max_length=150, blank=False, null=False, default="Anonymous")
	message = models.TextField()
	timestamp = models.DateTimeField(default=timezone.now)

class BlogPosts(models.Model):
	blog_id = models.AutoField(primary_key=True)
	title = models.CharField(max_length=300, blank=False, null=False, default="")
	author = models.CharField(max_length=150, default="")
	content = models.TextField(blank=False, null=False, default="")
	timestamp = models.DateTimeField(blank=False, null=False, auto_now_add=True)

	def __str__(self):
		return f'{self.timestamp} {self.title} {self.author}: {self.content}'