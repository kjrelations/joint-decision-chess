from django.db import models
# from django.contrib.auth.models import User

# Create your models here.
class BlogPosts(models.Model):
	title = models.CharField(max_length=300)
	author = models.CharField(max_length=100)
	content = models.TextField()
	timestamp = models.DateTimeField()

	def __str__(self):
		return f'{self.timestamp} {self.title} {self.author}: {self.content}'