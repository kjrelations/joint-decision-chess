from django.shortcuts import render
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
from base64 import binascii
from .models import BlogPosts, User
from .forms import ChangeEmailForm

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

@login_required
def change_email(response):
    if response.method == "POST":
        form = ChangeEmailForm(response.user, response.POST)
        if form.is_valid():
            try:
                new_email = form.cleaned_data['email']

                # Generate a token for email confirmation
                token = default_token_generator.make_token(response.user)

                # Create a confirmation link with the user's ID, email, and token
                # TODO only use hash for uuid this is too easily decoded
                uid = urlsafe_base64_encode(force_bytes(response.user.pk))
                new_email_encoded = urlsafe_base64_encode(force_bytes(new_email))
                confirmation_link = f"{get_current_site(response)}/account/confirm/{uid}/{token}/?new_email={new_email_encoded}"

                # Send an email with the confirmation link to the user
                subject = "Confirm Email - Decision Chess"
                html_message = render_to_string('main/settings/change_email_confirmation.html', {
                    'user': response.user,
                    'confirmation_link': confirmation_link,
                })
                from_email = 'DecisionChess <decisionchess@gmail.com>'
                to_email = new_email
                send_mail(subject, "", from_email, [to_email], html_message=html_message)

                messages.success(response, 'A confirmation email has been sent to your new email address with a confirmation link')

                form = ChangeEmailForm(response.user)
                return render(response, "main/settings/change_email.html", {"form": form })
            except Exception:
                messages.error(response, 'An error occurred')
    else:
        form = ChangeEmailForm(response.user)    

    return render(response, "main/settings/change_email.html", {"form": form })

@login_required
def confirm_email(response, uidb64, token):
    try:
        # Decode the user ID and get the user TODO hash it and compare to db also simply retrieve new emails from sessions
        uid = urlsafe_base64_decode(uidb64).decode()
        user = User.objects.get(pk=uid)
        new_email_encoded = response.GET.get('new_email')
        if new_email_encoded:
            # This a security issue and is only for basic testing
            new_email = urlsafe_base64_decode(new_email_encoded).decode()

            # Check if the token is valid
            if default_token_generator.check_token(user, token):
                user.email = new_email
                user.save()

                form = ChangeEmailForm(user) 
                messages.success(response, 'Your email has been updated')

                return render(response, "main/settings/change_email.html", {"form": form })
            else:
                messages.error(response, 'Token is invalid or expired')
                form = ChangeEmailForm(user) 
                
                return render(response, "main/settings/change_email.html", {"form": form })
        else:
            messages.error(response, 'Token is invalid or expired')
            form = ChangeEmailForm(user) 
            
            return render(response, "main/settings/change_email.html", {"form": form })
    except (TypeError, ValueError, OverflowError, binascii.Error):
        messages.error(response, 'An error occurred')
        form = ChangeEmailForm(user) 
        
        return render(response, "main/settings/change_email.html", {"form": form })
    except IntegrityError:
        messages.error(response, 'An error occurred')
        form = ChangeEmailForm(user) 
        
        return render(response, "main/settings/change_email.html", {"form": form })
    except Exception:
        messages.error(response, 'An error occurred')
        form = ChangeEmailForm(user) 
        
        return render(response, "main/settings/change_email.html", {"form": form })