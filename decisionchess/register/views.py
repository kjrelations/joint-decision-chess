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
from main.models import UserSettings
from base64 import binascii
from .forms import RegisterForm, ResendActivationEmailForm

User = get_user_model()

def register(request):
    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            user.is_active = False  # Mark the user as inactive until they validate their email
            user.save()

            # Generate a token for email validation
            token = default_token_generator.make_token(user)

            # Create a validation link with the user's ID and token
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            validation_link = f"{get_current_site(request)}/register/validate/{uid}/{token}/"

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

def activate_account(request, uidb64, token):
    try:
        # Decode the user ID and get the user
        uid = urlsafe_base64_decode(uidb64).decode()
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

            # Redirect to a success page
            return redirect('account_activated')
        else:
            # Token is invalid
            return redirect('activation_failed')
    except (TypeError, ValueError, OverflowError, binascii.Error):
        # Handle exceptions, e.g., invalid user ID
        return redirect('activation_failed')
    except IntegrityError:
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
                    uid = urlsafe_base64_encode(force_bytes(user.pk))
                    validation_link = f"{request.get_host()}/register/validate/{uid}/{token}/"

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