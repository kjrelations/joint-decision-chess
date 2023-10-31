from django.db import models
from django.utils import timezone

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
			if self.white_uuid and self.black_uuid:
				self.is_open = False
			elif (self.white_uuid or self.black_uuid) and self.initiator_connected:
				self.is_open = True
			else:
				self.is_open = False
			super(ChessLobby, self).save(*args, **kwargs)

	def __str__(self):
		return f"Lobby {self.id} ({self.lobby_url})"