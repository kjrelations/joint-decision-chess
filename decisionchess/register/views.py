# views.py
from django.contrib.sites.shortcuts import get_current_site
from django.conf import settings
from django.shortcuts import render, redirect
from django.db.utils import IntegrityError
from django.template.loader import render_to_string
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.contrib.auth import get_user_model, update_session_auth_hash
from django.contrib import messages
from django.http import HttpResponseNotFound
from main.models import UserSettings, Inbox
from base64 import binascii
from datetime import datetime, timedelta
from .forms import RegisterForm, ResendActivationEmailForm, CustomResetForm, CustomPasswordChangeForm
import jwt

User = get_user_model()

def register(request):
    if request.user and request.user.is_authenticated:
        return redirect("home")
    
    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            user.is_active = False  # Mark the user as inactive until they validate their email
            user.save()

            # Generate a token for email validation
            token = default_token_generator.make_token(user)

            # Create a validation link with the user's ID and token
            payload = {
                'user_id': str(user.pk),
                'exp': datetime.utcnow() + timedelta(days=1)
            }
            uid_token = jwt.encode(payload, settings.EMAIL_KEY, algorithm='HS256')
            protocol = 'https' if request.is_secure() else 'http'
            validation_link = f"{protocol}://{get_current_site(request)}/register/validate/{uid_token}/{token}/"

            # Send an email with the validation link to the user
            subject = "Decision Chess Account Activation"
            html_message = render_to_string('registration/activation_email.html', {
                'user': user,
                'validation_link': validation_link,
            })
            from_email = 'DecisionChess <decisionchess@gmail.com>'
            to_email = form.cleaned_data.get('email')
            send_mail(subject, "", from_email, [to_email], html_message=html_message)

            return redirect("home")
    else:
        form = RegisterForm()    

    return render(request, "register/register.html", {"form": form })

def password_reset_request(request):
    if request.method == "POST":
        form = CustomResetForm(request.POST)
        if form.is_valid():
            to_email = form.cleaned_data.get('email')
            
            try:
                user = User.objects.get(email=to_email)

                if not user.is_active:
                    messages.error(request, 'User not activated')
                    form = CustomResetForm()
                    return render(request, "register/password.html", {"form": form })
                
                # Generate a token for reset link validation
                token = default_token_generator.make_token(user)

                # Create a reset link with the user's ID and token
                payload = {
                    'user_id': str(user.pk),
                    'exp': datetime.utcnow() + timedelta(days=1)
                }
                uid_token = jwt.encode(payload, settings.EMAIL_KEY, algorithm='HS256')
                protocol = 'https' if request.is_secure() else 'http'
                reset_link = f"{protocol}://{get_current_site(request)}/register/pass_reset/{uid_token}/{token}/"
                subject = "Decision Chess Password Reset"
                html_message = render_to_string('registration/passwd_reset_email.html', {
                    'user': user,
                    'reset_link': reset_link,
                })
                from_email = 'DecisionChess <decisionchess@gmail.com>'
                to_email = form.cleaned_data.get('email')
                send_mail(subject, "", from_email, [to_email], html_message=html_message)

                form = CustomResetForm()

                messages.success(request, 'Password reset email sent')
                return render(request, "register/password.html", {"form": form })
            except User.DoesNotExist:
                messages.error(request, 'No user with that email address found')
            except Exception as e:
                print(e)
                messages.error(request, f'An error occurred {e}')

    else:
        form = CustomResetForm()    

    return render(request, "register/password.html", {"form": form })
                
def reset_pass(request, uidtoken, token):
    try:
        # Decode the user ID and get the user
        decoded_payload = jwt.decode(uidtoken, settings.EMAIL_KEY, algorithms=['HS256'])
        uid = decoded_payload['user_id']
        expired = datetime.utcfromtimestamp(decoded_payload['exp'])
        if expired < datetime.utcnow():
            return HttpResponseNotFound("The resource was not found.")
        user = User.objects.get(pk=uid)

        # Check if the token is valid
        if default_token_generator.check_token(user, token):
            if request.method == "POST":
                form = CustomPasswordChangeForm(user, request.POST)
                if form.is_valid():
                    try:
                        user = form.save()

                        # Re-authenticate the user
                        update_session_auth_hash(request, user)

                        messages.success(request, 'Your password was updated')
                        return redirect("reset_done")
                    except Exception:
                        messages.error(request, 'An error occurred')
                        return HttpResponseNotFound("The resource was not found.")
            else:
                form = CustomPasswordChangeForm(user)    

            return render(request, "register/password.html", {"form": form })
    except (TypeError, ValueError, OverflowError, binascii.Error):
        # Handle exceptions, e.g., invalid user ID
        print("Error: First exception type")
        return HttpResponseNotFound("The resource was not found.")
    except IntegrityError:
        print("Error: Integrity Error")
        return HttpResponseNotFound("The resource was not found.")
    except Exception:
        return HttpResponseNotFound("The resource was not found.")

def reset_done(request):
    return render(request, "register/reset_done.html")

def activate_account(request, uidtoken, token):
    try:
        # Decode the user ID and get the user
        decoded_payload = jwt.decode(uidtoken, settings.EMAIL_KEY, algorithms=['HS256'])
        uid = decoded_payload['user_id']
        expired = datetime.utcfromtimestamp(decoded_payload['exp'])
        if expired < datetime.utcnow():
            return redirect('activation_failed')
        user = User.objects.get(pk=uid)

        # Check if the token is valid
        if default_token_generator.check_token(user, token):
            # Activate the user's account
            user.is_active = True
            user.email_reference = user.email
            user_default_settings = UserSettings()
            user.save()
            user_default_settings.user = user
            user_default_settings.save()
            new_inbox = Inbox(
                user = user,
                unread_count = 0
                )
            new_inbox.save()

            # Redirect to a success page
            return redirect('account_activated')
        else:
            # Token is invalid
            return redirect('activation_failed')
    except (TypeError, ValueError, OverflowError, binascii.Error):
        # Handle exceptions, e.g., invalid user ID
        print("Error: First exception type")
        return redirect('activation_failed')
    except IntegrityError:
        print("Error: Integrity Error")
        return redirect('activation_failed')
    except Exception:
        return redirect('activation_failed')

def account_activated(request):
    return render(request, "register/account_activated.html")

def activation_failed(request):
    if request.method == 'POST':
        form = ResendActivationEmailForm(request.POST)
        if form.is_valid():
            to_email = form.cleaned_data.get('email')
            
            try:
                user = User.objects.get(email=to_email)

                if not user.is_active:
                    # Generate a new token for email validation
                    token = default_token_generator.make_token(user)

                    # Create a new validation link with the user's ID and token
                    payload = {
                        'user_id': str(user.pk),
                        'exp': datetime.utcnow() + timedelta(days=1)  # Token expiration time
                    }
                    uid_token = jwt.encode(payload, settings.EMAIL_KEY, algorithm='HS256')
                    protocol = 'https' if request.is_secure() else 'http'
                    validation_link = f"{protocol}://{get_current_site(request)}/register/validate/{uid_token}/{token}/"

                    # Send the new activation email
                    subject = "Decision Chess Account Activation"
                    html_message = render_to_string('registration/activation_email.html', {
                        'user': user,
                        'validation_link': validation_link,
                    })
                    from_email = 'DecisionChess <decisionchess@gmail.com>'
                    send_mail(subject, "", from_email, [to_email], html_message=html_message)

                    messages.success(request, 'A new activation email has been sent to your email address')
                    
                    form = ResendActivationEmailForm()
                    return render(request, "register/activation_failed.html", {'form': form})
                else:
                    messages.error(request, 'Your account is already active')
            except User.DoesNotExist:
                messages.error(request, 'No user with that email address found')
            except Exception:
                messages.error(request, 'An error occurred')
    else:
        form = ResendActivationEmailForm()

    return render(request, "register/activation_failed.html", {'form': form})