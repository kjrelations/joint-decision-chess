from django.shortcuts import render, redirect
from django.conf import settings
from django.contrib.sites.shortcuts import get_current_site
from django.db import transaction
from django.db.utils import IntegrityError
from django.db.models import Q
from django.utils import timezone
from django.template.loader import render_to_string
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.core.signing import dumps, loads, SignatureExpired, BadSignature
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash, logout
from django.contrib.auth.forms import PasswordChangeForm
from django.http import JsonResponse, HttpResponseNotFound
from django.urls import reverse
from django.utils.timesince import timesince
from base64 import binascii
from datetime import datetime, timedelta, timezone as dt_timezone
from .models import BlogPosts, User, ChessLobby, ActiveGames, GameHistoryTable, ActiveChatMessages, ChatMessages, UserSettings, Lessons
from .forms import ChangeEmailForm, EditProfile, CloseAccount, ChangeThemesForm, CreateNewGameForm
from .user_settings import default_themes
import uuid
import json
import random
import jwt

def index(request):
    return render(request, "main/home.html", {})

def home(request):
    recent_blogs = BlogPosts.objects.all().order_by('-timestamp')[:2]
    context = {"blogs": recent_blogs}
    if request.user and request.user.id is not None:
        user_id = request.user.id
    else:
        user_id = request.session.get('guest_uuid')

    # Active games with the same id, where there is a disconnect via the lobby column, and it matches the lobby game id
    user_games = ActiveGames.objects.filter(
        Q(white_id=user_id) | Q(black_id=user_id)
    )

    lobby_ids = ChessLobby.objects.filter(
        Q(opponent_connected=False) | Q(initiator_connected=False),
        lobby_id__in=user_games.values('active_game_id')
    ).values_list('lobby_id', flat=True)

    games_in_play = user_games.filter(
        active_game_id__in=lobby_ids
    ).order_by('-start_time')

    context["has_games_in_play"] = bool(games_in_play)
    context["games_in_play"] = games_in_play
    sides, opponents = [], []
    for game in games_in_play:
        if game.white_id == user_id:
            sides.append('white')
            try:
                opponent_username = User.objects.get(id=game.black_id)
                opponent_username = opponent_username.username
            except User.DoesNotExist:
                opponent_username = "Anonymous"
            opponents.append(opponent_username)
        else:
            sides.append('black')
            try:
                opponent_username = User.objects.get(id=game.white_id)
                opponent_username = opponent_username.username
            except User.DoesNotExist:
                opponent_username = "Anonymous"
            opponents.append(opponent_username)
    context['sides'] = sides
    context['opponents'] = opponents
    context['form'] = CreateNewGameForm()
    context['white_side_svg'] = open(".\\static\\images\\side-white.svg").read()
    context['black_side_svg'] = open(".\\static\\images\\side-black.svg").read()
    context['random_side_svg'] = open(".\\static\\images\\side-random.svg").read()
    context['complete_svg'] = open(".\\static\\images\\complete-variant-icon.svg").read()
    context['relay_svg'] = open(".\\static\\images\\reveal-stage-icon.svg").read()
    context['countdown_svg'] = open(".\\static\\images\\decision-stage-icon.svg").read()
    context['standard_svg'] = open(".\\static\\images\\decision-icon-colored.svg").read()
    context['x_svg'] = open(".\\static\\images\\x.svg").read()
    context['envelope_svg'] = open(".\\static\\images\\envelope.svg").read()
    context['hourglass_svg'] = open(".\\static\\images\\hourglass.svg").read()
    context['bird_svg'] = open(".\\static\\images\\bird.svg").read()
    context['lightning_svg'] = open(".\\static\\images\\lightning.svg").read()
    context['eye_svg'] = open(".\\static\\images\\eye.svg").read()
    context['masks_svg'] = open(".\\static\\images\\masks.svg").read()
    context['a1_svg'] = open(".\\static\\images\\a1.svg").read()
    context['b1_svg'] = open(".\\static\\images\\b1.svg").read()
    return render(request, "main/home.html", context)

def custom_404(request, exception):
    return render(request, 'main/404.html', {'exception': exception}, status=404)

def quick_pair(request):
    try:
        body = json.loads(request.body)
        gametype = body.get('gametype', '')
    except json.JSONDecodeError:
        return JsonResponse({'redirect': False, 'error': 'Invalid JSON'}, status=400)
    
    game = ChessLobby.objects.filter(is_open=True, gametype=gametype).order_by('-timestamp').first()
    if game is not None:
        return JsonResponse({'redirect': True, 'url': reverse('join_new_game', args=[str(game.lobby_id)])})
    else:
        return JsonResponse({'redirect': False, 'error': 'No open games found'}, status=404)

def game_exists(game_uuid):
    lobby_game_exists = ChessLobby.objects.filter(lobby_id=game_uuid).exists()
    active_game_exists = ActiveGames.objects.filter(active_game_id=game_uuid).exists()
    historic_game_exists = GameHistoryTable.objects.filter(historic_game_id=game_uuid).exists()
    return lobby_game_exists or active_game_exists or historic_game_exists

def is_valid_uuid(value):
    try:
        uuid.UUID(value)
        return True
    except (ValueError, AttributeError):
        return False

# TODO on refactor: optional_uuid to a body thing, rename new_open_game, change method to POST only
def create_new_game(request, optional_uuid = None):
    while True:
        game_uuid = optional_uuid if optional_uuid else uuid.uuid4()
        if not game_exists(game_uuid):
            new_open_game = ChessLobby(
                lobby_id=game_uuid,
                is_open=True,
                initiator_connected=False
            )
            if optional_uuid:
                new_open_game.private = True
            if request.user and request.user.id is not None:
                user_id = request.user.id
                new_open_game.initiator_name = request.user.username
            else:
                user_id = request.session.get('guest_uuid')
            # TODO Test the removal of all these sets
            if user_id is None:
                user_id = uuid.uuid4()
                request.session["guest_uuid"] = str(user_id)
            if request.method == "POST":
                data = json.loads(request.body.decode('utf-8'))
                if data.get('computer_game'):
                    new_open_game.computer_game = True
                    new_open_game.private = True
                    new_open_game.opponent_name = "minimax" # Later look up name with more bots
                if data.get('solo'):
                    new_open_game.solo_game = True
                    new_open_game.private = True
                position = data.get('position')
                opponent_column_to_fill = "black_id"
                if position == "white":
                    new_open_game.white_id = user_id
                    new_open_game.initiator_color = "white"
                elif position == "black":
                    new_open_game.black_id = user_id
                    new_open_game.initiator_color = "black"
                    opponent_column_to_fill = "white_id"
                elif position == "random":
                    column_to_fill = random.choice(["black_id", "white_id"])
                    setattr(new_open_game, column_to_fill, user_id)
                    new_open_game.initiator_color = "white" if column_to_fill == "white_id" else "black"
                    opponent_column_to_fill = "white_id" if column_to_fill == "black_id" else "black_id"
                else:
                    return JsonResponse({"status": "error", "message": "Unauthorized"}, status=401)
                if data.get('rematch'):
                    try:
                        historic = GameHistoryTable.objects.get(historic_game_id=data.get('rematch'))
                        opponent_id = getattr(historic, opponent_column_to_fill)
                        setattr(new_open_game, opponent_column_to_fill, opponent_id)
                        try:
                            opponent = User.objects.get(id=opponent_id)
                            new_open_game.opponent_name = opponent.username
                        except User.DoesNotExist:
                            new_open_game.opponent_name = "Anonymous"
                    except:
                        return JsonResponse({"status": "error", "message": "Recent Game DNE"}, status=401)
                private = data.get('private')
                if private:
                    new_open_game.private = True
                if data.get('main_mode') in ['Decision', 'Classical']:
                    if data.get('main_mode') == 'Decision':
                        if data.get('reveal_stage') and data.get('decision_stage'):
                            new_open_game.gametype = 'Complete'
                        elif data.get('reveal_stage') and not data.get('decision_stage'):
                            new_open_game.gametype = 'Relay'
                        elif not data.get('reveal_stage') and data.get('decision_stage'):
                            new_open_game.gametype = 'Countdown'
                        else:
                            new_open_game.gametype = 'Standard'
                    else:
                        new_open_game.gametype = data.get('main_mode')
                else:
                    return JsonResponse({"status": "error", "message": "Unauthorized"}, status=401)
                new_open_game.save()
                return JsonResponse({'redirect': True, 'url': reverse('join_new_game', args=[str(game_uuid)])}, status=200)
        elif optional_uuid:
            return JsonResponse({"status": "error", "message": "Unauthorized"}, status=401)

def create_signed_key(request):
    # TODO handle invalid requests: Missing recent_game_id, not logged in users and not a guest id available
    if request.method == "POST":
        data = json.loads(request.body.decode('utf-8'))
        if data.get('signed_uuid'):
            
            # This authentication is rematch logic only, this POST uses a rematch specific key in the body; the recent game uuid
            # SessionStored completed game ids have color prefixed to them.
            recent_game_id = data.get("recent_game_id").replace("white-", "").replace("black-", "")
            if request.user.id:
                user_id = request.user.id
            else:
                user_id = uuid.UUID(request.session.get('guest_uuid'))
            try:
                recent_game = GameHistoryTable.objects.get(historic_game_id=recent_game_id)
            except GameHistoryTable.DoesNotExist:
                return JsonResponse({"status": "error"}, status=401)
            if str(user_id) not in [str(recent_game.white_id), str(recent_game.black_id)]:
                return JsonResponse({"status": "error"}, status=401)
            
            try:
                original_value = loads(data.get('signed_uuid'), key=settings.SIGNING_KEY)
                return JsonResponse({"uuid": original_value}, status=200)
            except (SignatureExpired, BadSignature):
                return JsonResponse({"status": "error"}, status=401)
        elif data == {}:
            while True:
                game_uuid = uuid.uuid4()
                if not game_exists(game_uuid):
                    signed_uuid = dumps(str(game_uuid), key=settings.SIGNING_KEY)
                    return JsonResponse({"uuid": signed_uuid}, status=200)
        else:
            return JsonResponse({"status": "error"}, status=401)

def get_lobby_games(request):
    expired_games = ChessLobby.objects.filter(expire__lt=timezone.now(), is_open=True)
    expired_games.delete()

    lobby_games = ChessLobby.objects.filter(is_open=True)
    position_filter = request.GET.get('position')
    username_filter = request.GET.get('username')

    position_query = Q()
    if position_filter == 'white':
        position_query = Q(Q(white_id__isnull=True) & Q(initiator_color="black"))
    elif position_filter == 'black':
        position_query = Q(Q(black_id__isnull=True) & Q(initiator_color="white"))

    lobby_games = lobby_games.filter(
        Q(initiator_name=username_filter) if username_filter else Q(),
        position_query
    )
    serialized_data = [
        {
            "initiator_name": game.initiator_name,
            "game_uuid": game.lobby_id,
            "timestamp": game.timestamp.strftime("%H:%M:%S"),
            "side": "white" if game.white_id is None else "black",
            "game_type": game.gametype
        }
        for game in lobby_games
    ]
    return JsonResponse(serialized_data, safe=False)

def check_game_availability(request):
    if request.method == 'POST':
        data = json.loads(request.body.decode('utf-8'))
        game_id = data.get('gameId')
        try:
            game = ChessLobby.objects.get(lobby_id=game_id)
            available = game.is_open
        except ChessLobby.DoesNotExist:
            available = False

        serialized_data = {
            "open": available,
        }
        return JsonResponse(serialized_data)
    else:
        return JsonResponse({}, status=405)  # Method Not Allowed

def get_config(request, game_uuid):
    if request.user and request.user.id is not None:
        user_id = request.user.id
    else:
        guest_uuid = request.session.get('guest_uuid')
        if guest_uuid is None:
            return JsonResponse({"status": "error"}, status=401)
        else:
            user_id = uuid.UUID(guest_uuid)
    
    if request.user and request.user.id is not None:
        user_settings = UserSettings.objects.get(user=request.user)
        user_themes = user_settings.themes
        user_themes = [theme.replace("'", "\"") for theme in user_themes] # Single quotes in DB
        theme_names = [json.loads(theme)["name"] for theme in user_themes]
    else:
        themes = default_themes()
        themes = [theme.replace("'", "\"") for theme in themes]
        theme_names = [json.loads(theme)["name"] for theme in themes]

    type = request.GET.get('type')
    if type == 'live':
        try:
            game = ChessLobby.objects.get(lobby_id=game_uuid)
            if str(user_id) not in [str(game.white_id), str(game.black_id)]:
                return JsonResponse({"status": "error"}, status=401)
            fill = None
            if str(user_id) == str(game.white_id) == str(game.black_id):
                if game.initiator_color == "black":
                    fill = "white"
                elif game.initiator_color == "white":
                    fill = "black"
                else:
                    return JsonResponse({"status": "error"}, status=401)
            elif str(user_id) == str(game.white_id):
                fill = "white"
            elif str(user_id) == str(game.black_id):
                fill = "black"
            else:
                return JsonResponse({"status": "error"}, status=401)

            return JsonResponse({"message": {"starting_side": fill, "game_type": game.gametype, "theme_names": theme_names}}, status=200)
        except ChessLobby.DoesNotExist:
            # TODO check historic games and send a special refresh message if available
            return JsonResponse({"status": "error"}, status=401)
    elif type == 'historic':
        # TODO historic game type
        return JsonResponse({"message": {"theme_names": theme_names}}, status=200)
    else:
        return JsonResponse({"status": "error"}, status=401)

def play(request, game_uuid):
    if request.user and request.user.id is not None:
        user_id = request.user.id
    else:
        guest_uuid = request.session.get('guest_uuid')
        if guest_uuid is None:
            user_id = uuid.uuid4()
            request.session["guest_uuid"] = str(user_id)
        else:
            user_id = uuid.UUID(guest_uuid)
    sessionVariables = {
        'game_uuid': game_uuid,
        'connected': 'false',
        'current_game_id': str(game_uuid),
        'initialized': 'null',
        'draw_request': 'false',
        'undo_request': 'false',
        'total_reset': 'false'
    }

    # Validate uuid (ensure not expired), direct to play, spectator, or historic html, check authentication on former
    # For now, temporarily disallow multiple people from loading the same game
    try:
        game = ChessLobby.objects.get(lobby_id=game_uuid)
        play_html = "main/play.html" if game.gametype == 'Classical' else "main/play/decision_play.html"
        
        player = "Anonymous"
        if request.user.is_authenticated:
            player = request.user.username
        if (game.initiator_color == 'black' and str(game.black_id) == str(user_id)) or \
           (game.initiator_color == 'white' and str(game.white_id) == str(user_id)):
            opponent = game.opponent_name
        else:
            opponent = game.initiator_name
        sessionVariables.update({'opponent': opponent})

        if (game.computer_game or game.solo_game) and str(user_id) in [str(game.white_id), str(game.black_id)]:
            solo_html = "main/play/computer.html" if game.gametype == 'Classical' else "main/play/decision_computer.html"
            sessionVariables['computer_game'] = True if game.computer_game else False
            return render(request, solo_html, sessionVariables) ## TODO rename html file name and this variable so it's agnostic for solo or computer games
        elif not game.is_open and str(user_id) not in [str(game.white_id), str(game.black_id)]:
            # This should later redirect spectators to a spectator view if it's an active game, otherwise to home, maybe also to home for private games
            return redirect('home')
        elif str(user_id) in [str(game.white_id), str(game.black_id)]:
            # For now we won't allow multiple joins even from the same person after they've connected twice
            if game.black_id is None and game.initiator_connected:
                game.black_id = user_id
                game.opponent_connected = True
                game.opponent_name = player
                game.save()
            elif game.white_id is None and game.initiator_connected:
                game.white_id = user_id
                game.opponent_connected = True
                game.opponent_name = player
                game.save()
            # Later we change the below conditions to allow for reconnection ONLY not multiple tabs of the same game unless it's a spectator view
            elif str(user_id) == str(game.white_id) == str(game.black_id):
                if game.opponent_connected and game.initiator_connected:
                    return redirect('home')
                else:
                    game.opponent_connected = False
                    game.initiator_connected = False
                    game.save()
            elif str(user_id) == str(game.white_id) and game.black_id is not None:
                if game.initiator_connected and game.opponent_connected:
                    return redirect('home')
                else:
                    game.initiator_connected = False
                    game.opponent_connected = False
                    game.save()
            elif str(user_id) == str(game.black_id) and game.white_id is not None:
                if game.initiator_connected and game.opponent_connected:
                    return redirect('home')
                else:
                    game.initiator_connected = False
                    game.opponent_connected = False
                    game.save()
            game_chat_messages = ActiveChatMessages.objects.filter(game_id=game_uuid).order_by('timestamp')
            sessionVariables["chat_messages"] = game_chat_messages
            return render(request, play_html, sessionVariables)
        else:
            column_to_fill = "black_id"
            if game.white_id is None:
                column_to_fill = "white_id"
            game.opponent_connected = True
            game.opponent_name = player
            setattr(game, column_to_fill, user_id)
            game.save()
            return render(request, play_html, sessionVariables)
    except ChessLobby.DoesNotExist:
        try:
            historic = GameHistoryTable.objects.get(historic_game_id=game_uuid)
            historic_html = "main/historic.html" if historic.gametype == 'Classical' else "main/play/decision_historic.html"
            sessionVariables = {
                'current_game_id': str(game_uuid),
                'initialized': 'null',
                'alg_moves': historic.algebraic_moves,
                'comp_moves': historic.computed_moves,
                'FEN': historic.FEN_outcome,
                'outcome': historic.outcome,
                'forced_end': historic.termination_reason,
                'game_type': historic.gametype
            }
            try:
                white_user = User.objects.get(id=historic.white_id)
                white_user = white_user.username
            except User.DoesNotExist:
                white_user = "Anonymous"
            try:
                black_user = User.objects.get(id=historic.black_id)
                black_user = black_user.username
            except User.DoesNotExist:
                black_user = "Anonymous"
            player_side = white_user
            opponent_side = black_user
            flip = False
            if str(historic.black_id) == str(user_id) and str(historic.white_id) != str(user_id):
                player_side = black_user
                opponent_side = white_user
                flip = True
            sessionVariables.update({'player': player_side, 'opponent': opponent_side, 'init_flip': flip})
            game_chat_messages = ChatMessages.objects.filter(game_id=game_uuid).order_by('timestamp')
            sessionVariables["chat_messages"] = game_chat_messages
            return render(request, historic_html, sessionVariables)
        except GameHistoryTable.DoesNotExist:
            return redirect('home')
        except:
            JsonResponse({"status": "error"}, status=401)

def update_connected(request):
    # Have this handle live disconnects later
    if request.method == 'POST':
        data = json.loads(request.body.decode('utf-8'))
        # TODO It's best to use a JWT in the python script
        # TODO check that it matches some value in session
        connect_game_uuid = data.get('game_uuid')
        if not is_valid_uuid(connect_game_uuid):
            return JsonResponse({"status": "error"}, status=400)
        if request.user and request.user.id is not None:
            user_id = request.user.id
        else:
            guest_uuid = request.session.get('guest_uuid')
            if guest_uuid is None:
                return JsonResponse({"status": "error"}, status=400)
            else:
                user_id = uuid.UUID(guest_uuid)
        web_connect = data.get('web_connect')
        if web_connect != True and web_connect != False:
            return JsonResponse({"status": "error"}, status=400)
        try:
            game = ChessLobby.objects.get(lobby_id=connect_game_uuid)
            
            compare = game.white_id
            null_id = "black"
            if compare is None:
                compare = game.black_id
                null_id = "white"
            
            waiting_game = game.white_id is None or game.black_id is None
            # This allows the one player to join their own game or different games and 
            # multiples of each type
            is_initiator = False
            if (str(game.white_id) == str(user_id) and game.initiator_color == "white") or \
               (str(game.black_id) == str(user_id) and game.initiator_color == "black"):
                is_initiator = True

            message = {}
            update_and_check = False
            if waiting_game and game.initiator_connected != web_connect and is_initiator:
                game.initiator_connected = web_connect
                if game.computer_game:
                    bot_user = User.objects.get(username="minimax") # later from the message body
                    bot_id = bot_user.id
                    if null_id == "black":
                        game.black_id = bot_id
                    else:
                        game.white_id = bot_id
                    update_and_check = True
                elif data.get('computer_game') == False:
                    if null_id == "black":
                        game.black_id = user_id
                    else:
                        game.white_id = user_id
                    game.opponent_name = request.user.username if request.user else "Anonymous"
                    update_and_check = True
                game.save()
                message = {"status": "updated"}
            elif not waiting_game:
                update_and_check = True
                message = {"status": "updated"}
            if update_and_check:
                # We prefer this first definition that can't be tampered with in live matches,
                # but need the second for self-play
                message_sending_player = "white" if str(game.white_id) == str(user_id) else "black"
                message_sending_player = data["color"] if game.white_id == game.black_id else message_sending_player
                # A disconnect message means the other player disconnected, not the current player, but we set both to allow for reconnecting on both sides
                if game.initiator_color == message_sending_player:
                    field_to_update = "initiator_connected" if web_connect else "opponent_connected"
                    setattr(game, field_to_update, web_connect)
                    if not web_connect:
                        setattr(game, "initiator_connected", web_connect)
                else:
                    field_to_update = "opponent_connected" if web_connect else "initiator_connected"
                    setattr(game, field_to_update, web_connect)
                    if not web_connect:
                        setattr(game, "opponent_connected", web_connect)
                game.save()
                active_game_exists = ActiveGames.objects.filter(active_game_id=connect_game_uuid).exists()
                if not active_game_exists:
                    active_game = ActiveGames(
                        active_game_id = connect_game_uuid,
                        white_id = game.white_id,
                        black_id = game.black_id,
                        gametype = game.gametype
                    )
                    active_game.save()
            return JsonResponse(message, status=200)
        except ChessLobby.DoesNotExist:
            return JsonResponse({"status": "error", "message": "Lobby row DNE"}, status=400)
    else:
        return JsonResponse({"status": "error"}, status=400)

def get_or_update_state(request, game_uuid):
    if request.user and request.user.id is not None:
        user_id = request.user.id
    else:
        guest_uuid = request.session.get('guest_uuid')
        if guest_uuid is None:
            return JsonResponse({"status": "error"}, status=401)
        else:
            user_id = uuid.UUID(guest_uuid)
    if request.method == "POST":
        data = json.loads(request.body.decode('utf-8'))
        if data.get("token"):
            decoded = jwt.decode(data["token"], settings.STATE_UPDATE_KEY + str(game_uuid), algorithms=['HS256'])
            if decoded.get('game'):
                try:
                    active_game = ActiveGames.objects.get(active_game_id=game_uuid)
                    active_game.state = decoded['game']
                    if str(user_id) not in [str(active_game.white_id), str(active_game.black_id)]:
                        return JsonResponse({"status": "error"}, status=401)
                    active_game.save()
                    return JsonResponse({"status": "updated"}, status=200)
                except ActiveGames.DoesNotExist:
                    return JsonResponse({"message": "DNE"}, status=200)
            else:
                return JsonResponse({"status": "error"}, status=400)
        else:
            return JsonResponse({"status": "error"}, status=400)
    elif request.method == "GET":
        try:
            active_game = ActiveGames.objects.get(active_game_id=game_uuid)
            if active_game.state == "":
                return JsonResponse({"message": "DNE"}, status=200)
            if str(user_id) not in [str(active_game.white_id), str(active_game.black_id)]:
                return JsonResponse({"status": "error"}, status=401)
            token = jwt.encode(json.loads(active_game.state), settings.STATE_UPDATE_KEY + str(game_uuid), algorithm='HS256')
            return JsonResponse({"token": token}, status=200)
        except ActiveGames.DoesNotExist:
            try:
                finished_game = GameHistoryTable.objects.get(historic_game_id=game_uuid)
                token = jwt.encode(json.loads(finished_game.state), settings.STATE_UPDATE_KEY + str(game_uuid), algorithm='HS256')
                return JsonResponse({"token": token}, status=200)
            except GameHistoryTable.DoesNotExist:
                return JsonResponse({"message": "DNE"}, status=200)

def save_game(request):
    if request.method == 'PUT':
        # TODO validate data values, can't have nulls or blanks for example
        data = json.loads(request.body.decode('utf-8'))
        # TODO It's best to use a JWT in the python script
        # TODO check that it matches some value in session
        completed_game_uuid = data.get('game_uuid') # Retrieve from server somehow? Would need websockets to bypass web data. That's best and this shouldn't be a http response then
        if not is_valid_uuid(completed_game_uuid):
            return JsonResponse({"status": "error"}, status=400)
        if request.user and request.user.id is not None:
            user_id = request.user.id
        else:
            guest_uuid = request.session.get('guest_uuid')
            if guest_uuid is None:
                return JsonResponse({"status": "error"}, status=400)
            else:
                user_id = uuid.UUID(guest_uuid)
        try:
            active_game = ActiveGames.objects.get(active_game_id=completed_game_uuid)
            if str(user_id) != str(active_game.white_id) and str(user_id) != str(active_game.black_id):
                return JsonResponse({"status": "error", "message": "Unauthorized"}, status=401)
            lobby_game = ChessLobby.objects.get(lobby_id=completed_game_uuid)
            try:
                save_chat_and_game(active_game, data)
            except Exception:
                return JsonResponse({"status": "error", "message": "Game and chat not Saved"}, status=400)
            lobby_game.delete()
            active_game.delete()
            return JsonResponse({"status": "updated"}, status=200)
        except ActiveGames.DoesNotExist:
            try:
                saved_game = GameHistoryTable.objects.get(historic_game_id=completed_game_uuid)
                return JsonResponse({}, status=200)
            except:
                return JsonResponse({"status": "error", "message": "Game DNE"}, status=400)

@transaction.atomic
def save_chat_and_game(active_game, data):
    game_chat_messages = ActiveChatMessages.objects.filter(game_id=active_game.active_game_id).order_by('timestamp')

    for chat_message in game_chat_messages:
        new_chat_message = ChatMessages(
            game_id=chat_message.game_id,
            sender_color=chat_message.sender_color,
            sender=chat_message.sender,
            sender_username=chat_message.sender_username,
            message=chat_message.message,
            timestamp=chat_message.timestamp,
        )
        new_chat_message.save()
        chat_message.delete()

    # Create and save GameHistoryTable object
    completed_game = GameHistoryTable(
        historic_game_id=active_game.active_game_id,
        white_id=active_game.white_id,
        black_id=active_game.black_id,
        algebraic_moves=data.get('alg_moves'),
        start_time=active_game.start_time,
        gametype=active_game.gametype,
        outcome=data.get('outcome'),
        computed_moves=data.get('comp_moves'),
        FEN_outcome=data.get('FEN'),
        termination_reason=data.get('termination_reason'),
        state = active_game.state
    )
    completed_game.save()

def lessons(request):
    lessons = Lessons.objects.all()
    basic_titles = ['Introduction']
    standard_titles = ['Rook', 'Bishop', 'Knight', 'Queen', 'Pawn', 'King']
    decision_titles = ['Potential Barriers', 'Annihilation', 'Entanglement & Collapse', 'Double Checkmate']
    basic_rules, standard_rules, decision_rules = [], [], []
    for lesson in lessons:
        if lesson.title in basic_titles:
            basic_rules.append(lesson)
        elif lesson.title in standard_titles:
            standard_rules.append(lesson)
        else:
            decision_rules.append(lesson)
    basic_rules = sorted(basic_rules, key=lambda x: basic_titles.index(x.title))
    standard_rules = sorted(standard_rules, key=lambda x: standard_titles.index(x.title))
    decision_rules = sorted(decision_rules, key=lambda x: decision_titles.index(x.title))
    return render(request, "main/lessons.html", {"basic_rules": basic_rules, "standard_rules": standard_rules, "decision_rules": decision_rules})

def news(request):
    blogs = BlogPosts.objects.all().order_by('-timestamp')
    return render(request, "main/news.html", {"blogs": blogs})

def profile(request, username):
    try:
        profile_user = User.objects.get(username=username)
    except User.DoesNotExist:
        return HttpResponseNotFound(render(request, 'main/404.html', status=404))
    if profile_user.bot_account and request.user and request.user.username != "kjrelations":
        return HttpResponseNotFound(render(request, 'main/404.html', status=404))
    member_since = profile_user.date_joined.strftime("%b %d, %Y")
    historic_games = GameHistoryTable.objects.filter(Q(white_id=profile_user.id) | Q(black_id=profile_user.id))
    games_details = []
    for game in historic_games:
        if profile_user.id == game.white_id:
            side = "White"
            try:
                opponent_username = User.objects.get(id=game.black_id).username
            except User.DoesNotExist:
                opponent_username = "Anonymous"
        else:
            side = "Black"
            try:
                opponent_username = User.objects.get(id=game.white_id).username
            except User.DoesNotExist:
                opponent_username = "Anonymous"
        relative_game_time = timesince(game.end_time, datetime.utcnow().replace(tzinfo=dt_timezone.utc))
        result = []
        move_list = game.algebraic_moves.split(',')
        end_scores = ['0-0', '1-0', '0-1', '½–½']
        for string in end_scores:
            if string in move_list:
                move_list.remove(string)
        for i in range(0, len(move_list), 2):
            pair = move_list[i:i+2]
            pair_string = " ".join(pair)
            result.append(f"{(i//2) + 1}. {pair_string}")
        
        init_index = 2 if len(move_list) > 5 else len(result)
        formatted_moves_string = " ".join(result[:init_index])
        if len(move_list) > 5:
            formatted_moves_string += f" ... {result[-1]}"
        games_details.append({
            'game_id': game.historic_game_id,
            'outcome': game.outcome,
            'opponent': opponent_username,
            'game_type': game.gametype.capitalize(),
            'side': side,
            'relative_game_time': relative_game_time,
            'formatted_moves_string': formatted_moves_string
        })
        
    return render(request, "main/profile.html", {"profile_user": profile_user, "member_since": member_since, "games_details": games_details})

def terms_of_service(request):
    return render(request, "main/terms.html", {})

def privacy_policy(request):
    return render(request, "main/privacy.html", {})

@login_required
def change_themes(request):
    if request.method == "POST":
        form = ChangeThemesForm(request.POST)
        response_themes = []
        for theme_name in form.fields.keys():
            if theme_name != 'starting_theme':
                response_themes.append([theme_name, theme_name.title().replace("-", " ")])
        
        if form.is_valid():
            selected_themes = []
            initial_theme = form.cleaned_data['starting_theme']
            selected_themes.append(initial_theme.title().replace("-", " "))
            for theme_name, value in form.cleaned_data.items():
                if value and theme_name != 'starting_theme' and theme_name != initial_theme:
                    selected_themes.append(theme_name.title().replace("-", " "))
            
            new_user_themes = default_themes(selected_themes)
            user_settings = UserSettings.objects.get(user=request.user)
            user_settings.themes = new_user_themes
            user_settings.save()
            messages.success(request, 'Themes updated!')

            return render(request, "main/settings/change_themes.html", {"form": form, "themes": response_themes, 'endings': ['1', '2', '3']})
    else:
        selected_themes, snake_case_names, response_themes = [], [], []
        initial_theme = None
        if request.user and request.user.is_authenticated:
            user_settings = UserSettings.objects.get(user=request.user)
            user_themes = user_settings.themes
            user_themes = [theme.replace("'", "\"") for theme in user_themes] # Single quotes in DB
            selected_themes = [json.loads(theme)["name"] for theme in user_themes]
            initial_theme = selected_themes[0].lower().replace(" ", "-")
        form = ChangeThemesForm(initial_value=initial_theme)

        if selected_themes != []:
            snake_case_names = [theme.lower().replace(" ", "-") for theme in selected_themes]
        for theme_name in form.fields.keys():
            if snake_case_names != [] and theme_name in snake_case_names:
                form.fields[theme_name].initial = True
            elif snake_case_names == []:
                form.fields[theme_name].initial = True 
            if theme_name != 'starting_theme':
                response_themes.append([theme_name, theme_name.title().replace("-", " ")])

    return render(request, "main/settings/change_themes.html", {"form": form, "themes": response_themes, 'endings': ['1', '2', '3']})

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
                payload = {
                    'user_id': str(request.user.pk),
                    'email': new_email,
                    'exp': datetime.utcnow() + timedelta(days=1)
                }
                payload_token = jwt.encode(payload, settings.EMAIL_KEY, algorithm='HS256')
                protocol = 'https' if request.is_secure() else 'http'
                confirmation_link = f"{protocol}://{get_current_site(request)}/account/confirm/{payload_token}/{token}/"

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
def confirm_email(request, uidtoken, token):
    target_url = reverse('change_email')
    absolute_url = request.build_absolute_uri(target_url)
    try:
        # Decode the user ID and get the new user email
        decoded_payload = jwt.decode(uidtoken, settings.EMAIL_KEY, algorithms=['HS256'])
        uid = decoded_payload['user_id']
        expired = datetime.utcfromtimestamp(decoded_payload['exp'])
        if expired < datetime.utcnow():
            messages.error(request, 'Token is invalid or expired')
            return redirect(absolute_url)
        
        user = User.objects.get(pk=uid)
        uid = decoded_payload['user_id']
        new_email = decoded_payload['email']
        if new_email:
            # Check if the token is valid
            if default_token_generator.check_token(user, token):
                user.email = new_email
                user.email_reference = new_email
                user.save()

                messages.success(request, 'Your email has been updated')
                return redirect(absolute_url)
            
            else:
                messages.error(request, 'Token is invalid or expired')
                return redirect(absolute_url)
            
        else:
            messages.error(request, 'Token is invalid or expired')
            return redirect(absolute_url)
        
    except (TypeError, ValueError, OverflowError, binascii.Error):
        messages.error(request, 'An error occurred')
        return redirect(absolute_url)
    
    except IntegrityError:
        messages.error(request, 'An error occurred')
        return redirect(absolute_url)
    
    except Exception:
        messages.error(request, 'An error occurred')        
        return redirect(absolute_url)
    
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

@login_required
def close_account(request):
    if request.method == "POST":
        form = CloseAccount(request.user, request.POST)
        if form.is_valid():
            try:
                username = request.user.username
                request.user.is_active = False
                request.user.account_closed = True
                request.user.set_password(str(uuid.uuid4()))
                unique = False
                while not unique:
                    placeholder_email = f"{uuid.uuid4()}@{uuid.uuid4()}.com"
                    if not User.objects.filter(email=placeholder_email).exists():
                        request.user.email = placeholder_email
                        unique = True
                request.user.save()

                logout(request)

                return redirect(reverse('profile', kwargs={'username': username}))
            except Exception as e:
                messages.error(request, 'An error occurred')
    else:
        form = CloseAccount(request.user)    

    return render(request, "main/settings/close_account.html", {"form": form })