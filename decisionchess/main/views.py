from django.shortcuts import render
from .models import BlogPosts, User

# Create your views here.
# views.py file

def index(response):
    return render(response, "main/home.html", {})

def home(response):
    return render(response, "main/home.html", {})

def play(response):
    return render(response, "main/play.html", {})

def news(response):
    blogs = BlogPosts.objects.all().order_by('-timestamp')
    return render(response, "main/news.html", {"blogs": blogs})

def profile(response, username):
    profile_user = User.objects.get(username=username)
    member_since = profile_user.date_joined.strftime("%b %d, %Y")
    return render(response, "main/profile.html", {"profile_user": profile_user, "member_since": member_since})