# python -m main.new_message
import os
import django

# Set the DJANGO_SETTINGS_MODULE environment variable
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "decisionchess.settings")

# Configure Django settings
django.setup()

# Given the above the model import should work and settings can be accessed
from main.models import Message, User, Inbox

user = User.objects.get(username='kjrelations')

message = Message(
    sender = user,
    subject="Please have fun!",
    recipient=user,
    body="Play a game by challenging an online opponent, block challenges from specific users."
)

message.save()
