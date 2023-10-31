# views.py
from django.contrib.sites.shortcuts import get_current_site
from django.shortcuts import render, redirect
from django.db.utils import IntegrityError
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes
from django.template.loader import render_to_string
from django.utils.http import urlsafe_base64_encode
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.contrib.auth import get_user_model
from django.contrib import messages
from base64 import binascii
