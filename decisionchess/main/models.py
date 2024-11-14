from django.db import models
from django.contrib.postgres.fields import ArrayField
from django.contrib.auth.models import AbstractUser
from django_countries.fields import CountryField
from django.utils import timezone
from django.db.models.signals import post_save
from django.dispatch import receiver
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
	subvariant = models.CharField(max_length=20, blank=False, null=True, default="Normal")
	initial_state = models.TextField(blank=True, null=True)

	def save(self, *args, **kwargs):
		if not self.timestamp:
			self.timestamp = timezone.now()
		if not self.expire:
			self.expire = self.timestamp + timezone.timedelta(minutes=10)
		if self.solo_game or self.computer_game:
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
	last_submission_time = models.DateTimeField(null=True)

class GameHistoryTable(models.Model):
	historic_game_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
	white_id = models.UUIDField(null=False)
	black_id = models.UUIDField(null=False)
	algebraic_moves = models.TextField(blank=False, null=False, default="")
	start_time = models.DateTimeField(blank=False, null=False)
	end_time = models.DateTimeField(blank=False, null=False, auto_now_add=True)
	gametype = models.CharField(max_length=300, blank=False, null=False, default="")
	subvariant = models.CharField(max_length=20, blank=False, null=True, default="Normal")
	outcome = models.CharField(max_length=7, blank=False, null=False, default="")
	computed_moves = models.TextField(blank=False, null=False, default="")
	FEN_outcome = models.CharField(max_length=85, blank=False, null=False, default="")
	termination_reason = models.CharField(max_length=85, blank=True, null=False, default="")
	state = models.TextField(default="")
	initial_state = models.TextField(blank=True, null=True)

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
	
class Lessons(models.Model):
	lesson_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
	title = models.CharField(max_length=50, blank=False, null=False, default="")
	url_name = models.CharField(max_length=25, blank=False, null=False, default="")
	description = models.TextField(blank=False, null=False, default="")

class EmbeddedGames(models.Model):
	embedded_game_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
	name = models.CharField(max_length=150, blank=False, null=False, default="")
	FEN = models.CharField(max_length=85, blank=False, null=False, default="")
	gametype = models.CharField(max_length=300, blank=False, null=False, default="")
	indexed_moves = models.TextField(blank=False, null=True, default="")
	moves = models.TextField(blank=False, null=True, default="")
	side = models.CharField(max_length=5, blank=False, null=False, default="white")

class Pages(models.Model):
	page_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
	lesson = models.ForeignKey(Lessons, on_delete=models.CASCADE, null=False) 
	page_position = models.IntegerField(blank=False, null=False, default=1)
	content = models.TextField(blank=False, null=False, default="")
	embedded_game = models.ForeignKey(EmbeddedGames, on_delete=models.SET_NULL, null=True)

class Message(models.Model):
	message_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
	sender = models.ForeignKey(User, related_name='sent_messages', on_delete=models.CASCADE)
	recipient = models.ForeignKey(User, related_name='received_messages', on_delete=models.CASCADE)
	subject = models.CharField(max_length=255, null=True, blank=True)
	body = models.TextField()
	sent_at = models.DateTimeField(auto_now_add=True)
	is_read = models.BooleanField(default=False)
	is_deleted = models.BooleanField(default=False)

	def save(self, *args, **kwargs):
		super().save(*args, **kwargs)

		recipient_inbox, created = Inbox.objects.get_or_create(user=self.recipient)
		recipient_inbox.messages.add(self)

		if not self.is_read:
			recipient_inbox.unread_count += 1
			recipient_inbox.save()
		else:
			try:
				notification = Notification.objects.get(message=self)
				notification.is_seen = True
				notification.save()
			except Notification.DoesNotExist:
				pass

@receiver(post_save, sender=Message)
def create_notification(sender, instance, created, **kwargs):
    if created:
        Notification.objects.create(user=instance.recipient, message=instance)

class Inbox(models.Model):
	inbox_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
	user = models.OneToOneField(User, related_name='inbox', on_delete=models.CASCADE)
	messages = models.ManyToManyField(Message, related_name='inboxes')
	unread_count = models.IntegerField(default=0)

class Notification(models.Model):
	notification_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
	user = models.ForeignKey(User, related_name='notifications', on_delete=models.CASCADE)
	message = models.ForeignKey(Message, related_name='notification', on_delete=models.CASCADE)
	created_at = models.DateTimeField(auto_now_add=True)
	is_seen = models.BooleanField(default=False)

class Challenge(models.Model):
	challenge_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
	white_id = models.UUIDField(null=True)
	black_id = models.UUIDField(null=True)
	initiator_name = models.CharField(max_length=150, blank=False, null=False, default="Anonymous")
	opponent_name = models.CharField(max_length=150, blank=False, null=False, default="Waiting...")
	timestamp = models.DateTimeField()
	initiator_color = models.CharField(max_length=5, null=True)
	gametype = models.CharField(max_length=300, blank=False, null=False, default="")
	subvariant = models.CharField(max_length=20, blank=False, null=True, default="Normal") # TODO
	challenge_accepted = models.BooleanField(default=None, null=True)
	choices = [('Random', 'Random'), ('White', 'White'), ('Black', 'Black')]
	initiator_choice = models.CharField(max_length=6, choices=choices, default='Random')
	game_id = models.UUIDField(null=True)

	def save(self, *args, **kwargs):
		if not self.timestamp:
			self.timestamp = timezone.now()
		super(Challenge, self).save(*args, **kwargs)

class ChallengeMessages(models.Model):
	message_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
	challenge = models.ForeignKey(Challenge, related_name='messages', on_delete=models.CASCADE)
	sender_is_initiator = models.BooleanField(default=False, null=False)
	sender = models.UUIDField(null=False)
	sender_username = models.CharField(max_length=150, blank=False, null=False, default="Anonymous")
	message = models.TextField()
	timestamp = models.DateTimeField(default=timezone.now)

class Blocks(models.Model):
	block_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
	user = models.ForeignKey(User, related_name='blocked_users', on_delete=models.CASCADE)
	blocked_user_id = models.UUIDField()