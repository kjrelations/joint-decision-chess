from django.shortcuts import render
from django.http import HttpResponse, HttpResponseRedirect
from .models import BlogPosts

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