from django.db import models
from django.contrib.auth.models import AbstractUser
from django_countries.fields import CountryField
import uuid

class User(AbstractUser):
	id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
	email = models.EmailField(unique=True)
	bio = models.TextField(blank=True)
	country = CountryField(blank=True, null=True)

	def __str__(self):
		return self.username

# Create your models here.
class BlogPosts(models.Model):
	title = models.CharField(max_length=300, blank=False, null=False, default="")
	author = models.CharField(max_length=150, default="")
	content = models.TextField(blank=False, null=False, default="")
	timestamp = models.DateTimeField(blank=False, null=False, auto_now_add=True)

	def __str__(self):
		return f'{self.timestamp} {self.title} {self.author}: {self.content}'