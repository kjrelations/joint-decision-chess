from django.db import models
from django.contrib.auth.models import AbstractUser
from django_countries.fields import CountryField
from django.utils import timezone
import uuid

class User(AbstractUser):
	id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False) # unique
	email = models.EmailField(unique=True)
	bio = models.TextField(blank=True)
	country = CountryField(blank=True, null=True)

	def __str__(self):
		return self.username

class ChessLobby(models.Model):
	game_uuid = models.UUIDField(unique=True) # change to gameid later make it primary
	white_uuid = models.UUIDField(null=True)
	black_uuid = models.UUIDField(null=True)
	initiator_name = models.CharField(max_length=150, blank=False, null=False, default="Anonymous")
	timestamp = models.DateTimeField()
	expire = models.DateTimeField()
	is_open = models.BooleanField(default=True)
	initiator_connected = models.BooleanField(default=False)
	private = models.BooleanField(default=False)

	def save(self, *args, **kwargs):
		if not self.timestamp:
			self.timestamp = timezone.now()
		if not self.expire:
			self.expire = self.timestamp + timezone.timedelta(minutes=10)
		if self.private:
			self.is_open = False
		elif self.white_uuid and self.black_uuid:
			self.is_open = False
		elif (self.white_uuid or self.black_uuid) and self.initiator_connected:
			self.is_open = True
		else:
			self.is_open = False
		super(ChessLobby, self).save(*args, **kwargs)

	def __str__(self):
		return f"Lobby {self.id} ({self.lobby_url})"

class ActiveGames(models.Model):
	gameid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False) # unique
	whiteid = models.UUIDField(null=False)
	blackid = models.UUIDField(null=False)
	starttime = models.DateTimeField(blank=False, null=False, auto_now_add=True)
	gametype = models.CharField(max_length=300, blank=False, null=False, default="")
	status = models.CharField(max_length=50, blank=False, null=False, default="")

class GameHistoryTable(models.Model):
	gameid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False) # unique
	whiteid = models.UUIDField(null=False)
	blackid = models.UUIDField(null=False)
	algebraic_moves = models.TextField(blank=False, null=False, default="")
	starttime = models.DateTimeField(blank=False, null=False)
	endtime = models.DateTimeField(blank=False, null=False, auto_now_add=True)
	gametype = models.CharField(max_length=300, blank=False, null=False, default="")
	outcome = models.CharField(max_length=7, blank=False, null=False, default="")
	computed_moves = models.TextField(blank=False, null=False, default="")
	FEN_outcome = models.CharField(max_length=85, blank=False, null=False, default="")
	termination_reason = models.CharField(max_length=85, blank=True, null=False, default="")

class ActiveChatMessages(models.Model):
	messageid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, unique=True)
	gameid = models.UUIDField(null=False)
	sender_color = models.CharField(max_length=5, null=True)
	sender = models.UUIDField(null=False)
	sender_username = models.CharField(max_length=150, blank=False, null=False, default="Anonymous")
	message = models.TextField()
	timestamp = models.DateTimeField(default=timezone.now)

class ChatMessages(models.Model):
	messageid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, unique=True)
	gameid = models.UUIDField(null=False)
	sender_color = models.CharField(max_length=5, null=True)
	sender = models.UUIDField(null=False)
	sender_username = models.CharField(max_length=150, blank=False, null=False, default="Anonymous")
	message = models.TextField()
	timestamp = models.DateTimeField(default=timezone.now)

class BlogPosts(models.Model):
	# Have blogid later that's unique
	title = models.CharField(max_length=300, blank=False, null=False, default="")
	author = models.CharField(max_length=150, default="")
	content = models.TextField(blank=False, null=False, default="")
	timestamp = models.DateTimeField(blank=False, null=False, auto_now_add=True)

	def __str__(self):
		return f'{self.timestamp} {self.title} {self.author}: {self.content}'