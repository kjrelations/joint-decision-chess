from django.db import models
# from django.contrib.auth.models import User

# Create your models here.
class BlogPosts(models.Model):
	title = models.CharField(max_length=300, blank=False, null=False, default="")
	author = models.CharField(max_length=100, default="")
	content = models.TextField(blank=False, null=False, default="")
	timestamp = models.DateTimeField(blank=False, null=False, auto_now_add=True)

	def __str__(self):
		return f'{self.timestamp} {self.title} {self.author}: {self.content}'