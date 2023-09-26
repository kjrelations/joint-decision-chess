from django.shortcuts import render
from django.http import HttpResponse, HttpResponseRedirect

# Create your views here.
# views.py file


def index(response):
    return render(response, "main/home.html", {})

def home(response):
    return render(response, "main/home.html", {})

def play(response):
    return render(response, "main/play.html", {})