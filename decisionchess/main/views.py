from django.shortcuts import render, redirect
from django.contrib.sites.shortcuts import get_current_site
from django.db.utils import IntegrityError
from django.utils import timezone
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes
from django.template.loader import render_to_string
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.http import JsonResponse
from django.urls import reverse
from base64 import binascii
from .models import BlogPosts, User, ChessLobby
from .forms import ChangeEmailForm, EditProfile
import uuid
import json

def index(request):
    return render(request, "main/home.html", {})

def home(request):
    return render(request, "main/home.html", {})

def quick_pair(request):
    game = ChessLobby.objects.filter(is_open=True).order_by('-timestamp').first()
    if game is not None:
        return JsonResponse({'redirect': True, 'url': reverse('join_new_game', args=[str(game.game_uuid)])})
    else:
        return JsonResponse({'redirect': False, 'error': 'No open games found'}, status=404)

def create_new_game(request):
    while True:
        game_uuid = uuid.uuid4()
        if not ChessLobby.objects.filter(game_uuid=game_uuid).exists():
            new_open_game = ChessLobby(
                game_uuid=game_uuid,
                is_open=True,
                initiator_connected=False
            )
            # Later get username and add to initiator name if authenticated
            # Retrieve and add user uuid to appropriate position, generate a unique one if needed
            
            guest_uuid = request.session.get('guest_uuid')
            if guest_uuid is None:
                guest_uuid = uuid.uuid4()
                request.session["guest_uuid"] = str(guest_uuid)
            new_open_game.white_uuid = guest_uuid
            new_open_game.save()
            return JsonResponse({'redirect': True, 'url': reverse('join_new_game', args=[str(game_uuid)])})

def get_lobby_games(request):
    expired_games = ChessLobby.objects.filter(expire__lt=timezone.now())
    expired_games.delete()

    lobby_games = ChessLobby.objects.filter(is_open=True)
    serialized_data = [
        {
            "initiator_name": game.initiator_name,
            "game_uuid": game.game_uuid,
            "timestamp": game.timestamp.strftime("%H:%M:%S")
        }
        for game in lobby_games
    ]
    return JsonResponse(serialized_data, safe=False)

def check_game_availability(request):
    if request.method == 'POST':
        data = json.loads(request.body.decode('utf-8'))
        game_id = data.get('gameId')
        try:
            game = ChessLobby.objects.get(game_uuid=game_id)
            available = game.is_open
        except ChessLobby.DoesNotExist:
            available = False

        serialized_data = {
            "open": available,
        }
        return JsonResponse(serialized_data)
    else:
        return JsonResponse({}, status=405)  # Method Not Allowed

def play(request, game_uuid):
    guest_uuid = request.session.get('guest_uuid')
    if guest_uuid is None:
        guest_uuid = uuid.uuid4()
        request.session["guest_uuid"] = str(guest_uuid)
    sessionVariables = {
        'guest_uuid': str(guest_uuid),
        'game_uuid': game_uuid,
        'connected': 'false',
        'current_game_id': str(game_uuid),
        'initialized': 'null',
        'draw_request': 'false',
        'undo_request': 'false',
        'total_reset': 'false',
        'guest_uuid': guest_uuid
    }

    # Validate uuid (ensure not expired), direct to play, spectator, or historic html, check authentication on former
    # For now, temporarily disallow multiple people from loading the same game
    try:
        game = ChessLobby.objects.get(game_uuid=game_uuid)
        if not game.is_open and str(guest_uuid) not in [str(game.white_uuid), str(game.black_uuid)]:
            return redirect('home')
        elif str(guest_uuid) in [str(game.white_uuid), str(game.black_uuid)]:
            # For now we won't allow multiple joins even from the same person after they've connected twice
            if game.black_uuid is None and game.initiator_connected:
                game.black_uuid = guest_uuid
                game.save()
            elif str(guest_uuid) == str(game.white_uuid) == str(game.black_uuid):
                return redirect('home')
            return render(request, "main/play.html", sessionVariables)
        else:
            game.black_uuid = guest_uuid
            game.save()
            return render(request, "main/play.html", sessionVariables)
    except ChessLobby.DoesNotExist:
        return render(request, "main/play.html", sessionVariables)

def is_valid_uuid(value):
    try:
        uuid.UUID(value)
        return True
    except (ValueError, AttributeError):
        return False

def update_connected(request):
    # Have this handle live disconnects later
    if request.method == 'POST':
        data = json.loads(request.body.decode('utf-8'))
        connect_game_uuid = data.get('game_uuid') # Retrieve from server somehow? Would need websockets to bypass web data. That's best and this shouldn't be a http response then
        # Actually just ensuring it's in session should be fine
        if not is_valid_uuid(connect_game_uuid):
            return JsonResponse({"status": "error"}, status=400)
        guest_uuid = request.session.get("guest_uuid")
        web_connect = data.get('web_connect')
        try:
            game = ChessLobby.objects.get(game_uuid=connect_game_uuid)
            
            compare = game.white_uuid
            null_id = "black"
            if compare is None:
                compare = game.black_uuid
                null_id = "white"
            session_game = request.session.get(connect_game_uuid)
            if session_game is not None and "white" in session_game:
                request.session[connect_game_uuid] = ["white", "black"]
            else:
                request.session[connect_game_uuid] = [null_id]
            # maybe fail if None as a starting condition and add it to session in play view function
            
            waiting_game = game.white_uuid is None or game.black_uuid is None
            # This allows the one player to join their own game or different games and 
            # multiples of each type
            is_initiator = True if len(request.session[connect_game_uuid]) == 1 and waiting_game else False

            if game.initiator_connected != web_connect and is_initiator:
                    game.initiator_connected = web_connect
                    game.save()
                    return JsonResponse({"status": "updated"})
            elif compare is not None and waiting_game: # and str(compare) != guest_uuid: # For ranked only
                if null_id == "black":
                    game.black_uuid = guest_uuid
                else:
                    game.white_uuid = guest_uuid
                game.save()
                return JsonResponse({"status": "updated"})
            return JsonResponse({}, status=200)
        except ChessLobby.DoesNotExist:
            return JsonResponse({"status": "error", "message": "Lobby row DNE"}, status=400)
    else:
        return JsonResponse({"status": "error"}, status=400)

def news(request):
    blogs = BlogPosts.objects.all().order_by('-timestamp')
    return render(request, "main/news.html", {"blogs": blogs})

def profile(request, username):
    profile_user = User.objects.get(username=username)
    member_since = profile_user.date_joined.strftime("%b %d, %Y")
    return render(request, "main/profile.html", {"profile_user": profile_user, "member_since": member_since})

def terms_of_service(request):
    return render(request, "main/terms.html", {})

def privacy_policy(request):
    return render(request, "main/privacy.html", {})

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