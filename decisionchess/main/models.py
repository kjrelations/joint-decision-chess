from django.db import models
from django.contrib.auth.models import AbstractUser
from django_countries.fields import CountryField
from django.utils import timezone
import uuid

class User(AbstractUser):
	id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
	email = models.EmailField(unique=True)
	bio = models.TextField(blank=True)
	country = CountryField(blank=True, null=True)

	def __str__(self):
		return self.username

class ChessLobby(models.Model):
	game_uuid = models.UUIDField(unique=True)
	white_uuid = models.UUIDField(null=True)
	black_uuid = models.UUIDField(null=True)
	initiator_name = models.CharField(max_length=150, blank=False, null=False, default="Anonymous")
	timestamp = models.DateTimeField()
	expire = models.DateTimeField()
	is_open = models.BooleanField(default=True)
	initiator_connected = models.BooleanField(default=False)

	def save(self, *args, **kwargs):
			if not self.timestamp:
				self.timestamp = timezone.now()
			if not self.expire:
				self.expire = self.timestamp + timezone.timedelta(minutes=10)
			super(ChessLobby, self).save(*args, **kwargs)

	def __str__(self):
		return f"Lobby {self.id} ({self.lobby_url})"

# Create your models here.
class BlogPosts(models.Model):
	title = models.CharField(max_length=300, blank=False, null=False, default="")
	author = models.CharField(max_length=150, default="")
	content = models.TextField(blank=False, null=False, default="")
	timestamp = models.DateTimeField(blank=False, null=False, auto_now_add=True)

	def __str__(self):
		return f'{self.timestamp} {self.title} {self.author}: {self.content}'