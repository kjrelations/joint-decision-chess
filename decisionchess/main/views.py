from django.shortcuts import render, redirect
from django.contrib.sites.shortcuts import get_current_site
from django.db.utils import IntegrityError
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes
from django.template.loader import render_to_string
from django.utils.http import urlsafe_base64_encode
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from base64 import binascii
from .models import BlogPosts, User
from .forms import ChangeEmailForm, EditProfile

# Create your views here.
# views.py file

def index(request):
    return render(request, "main/home.html", {})

def home(request):
    return render(request, "main/home.html", {})

def play(request):
    return render(request, "main/play.html", {})

def news(request):
    blogs = BlogPosts.objects.all().order_by('-timestamp')
    return render(request, "main/news.html", {"blogs": blogs})

def profile(request, username):
    profile_user = User.objects.get(username=username)
    member_since = profile_user.date_joined.strftime("%b %d, %Y")
    return render(request, "main/profile.html", {"profile_user": profile_user, "member_since": member_since})

@login_required
def change_email(request):
    if request.method == "POST":
        form = ChangeEmailForm(request.user, request.POST)
        if form.is_valid():
            try:
                new_email = form.cleaned_data['email']

                # Generate a token for email confirmation
                token = default_token_generator.make_token(request.user)

                # Create a confirmation link with the user's ID, email, and token
                # TODO only use hash for uuid this is too easily decoded
                uid = urlsafe_base64_encode(force_bytes(request.user.pk))
                new_email_encoded = urlsafe_base64_encode(force_bytes(new_email))
                confirmation_link = f"{get_current_site(request)}/account/confirm/{uid}/{token}/?new_email={new_email_encoded}"

                # Send an email with the confirmation link to the user
                subject = "Confirm Email - Decision Chess"
                html_message = render_to_string('main/settings/change_email_confirmation.html', {
                    'user': request.user,
                    'confirmation_link': confirmation_link,
                })
                from_email = 'DecisionChess <decisionchess@gmail.com>'
                to_email = new_email
                send_mail(subject, "", from_email, [to_email], html_message=html_message)

                messages.success(request, 'A confirmation email has been sent to your new email address with a confirmation link')

                form = ChangeEmailForm(request.user)
                return render(request, "main/settings/change_email.html", {"form": form })
            except Exception:
                messages.error(request, 'An error occurred')
    else:
        form = ChangeEmailForm(request.user)    

    return render(request, "main/settings/change_email.html", {"form": form })

@login_required
def confirm_email(request, uidb64, token):
    try:
        # Decode the user ID and get the user TODO hash it and compare to db also simply retrieve new emails from sessions
        uid = urlsafe_base64_decode(uidb64).decode()
        user = User.objects.get(pk=uid)
        new_email_encoded = request.GET.get('new_email')
        if new_email_encoded:
            # This a security issue and is only for basic testing
            new_email = urlsafe_base64_decode(new_email_encoded).decode()

            # Check if the token is valid
            if default_token_generator.check_token(user, token):
                user.email = new_email
                user.save()

                form = ChangeEmailForm(user) 
                messages.success(request, 'Your email has been updated')

                return render(request, "main/settings/change_email.html", {"form": form })
            else:
                messages.error(request, 'Token is invalid or expired')
                form = ChangeEmailForm(user) 
                
                return render(request, "main/settings/change_email.html", {"form": form })
        else:
            messages.error(request, 'Token is invalid or expired')
            form = ChangeEmailForm(user) 
            
            return render(request, "main/settings/change_email.html", {"form": form })
    except (TypeError, ValueError, OverflowError, binascii.Error):
        messages.error(request, 'An error occurred')
        form = ChangeEmailForm(user) 
        
        return render(request, "main/settings/change_email.html", {"form": form })
    except IntegrityError:
        messages.error(request, 'An error occurred')
        form = ChangeEmailForm(user) 
        
        return render(request, "main/settings/change_email.html", {"form": form })
    except Exception:
        messages.error(request, 'An error occurred')
        form = ChangeEmailForm(user) 
        
        return render(request, "main/settings/change_email.html", {"form": form })
    
@login_required
def change_password(request):
    if request.method == "POST":
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            try:
                user = form.save()

                # Re-authenticate the user
                update_session_auth_hash(request, user)

                messages.success(request, 'Your password was updated')

                form = PasswordChangeForm(user)
                return render(request, "main/settings/change_password.html", {"form": form })
            except Exception:
                messages.error(request, 'An error occurred')
    else:
        form = PasswordChangeForm(request.user)    

    return render(request, "main/settings/change_password.html", {"form": form })

@login_required
def edit_profile(request):
    user = request.user
    if request.method == 'POST':
        form = EditProfile(request.POST)
        if form.is_valid():
            bio = form.cleaned_data['biography']
            country = form.cleaned_data['country']
            user.bio = bio
            user.country = country
            user.save()

            member_since = user.date_joined.strftime("%b %d, %Y")
            return redirect(f'/profile/{user}', {"profile_user": user, "member_since": member_since})
    else:
        form = EditProfile(initial={'biography': user.bio, 'country': user.country})
    
    return render(request, "main/settings/edit_profile.html", {"form": form })