# Run from main directory with python -m main.lesson
import os
import django

# Set the DJANGO_SETTINGS_MODULE environment variable
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "decisionchess.settings")

# Configure Django settings
django.setup()

# Given the above the model import should work and settings can be accessed
from main.models import Lessons

if __name__ == "__main__":
    lesson = Lessons(
        title="Basics",
        url_name="basics",
        description="Learn the core basics of the game. How to select and move pieces, how to draw arrows, what the main difference is between Decision Chess and classical Chess and more"
    )
    lesson.save()