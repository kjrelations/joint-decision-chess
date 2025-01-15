from django.shortcuts import render, redirect
from django.conf import settings
from django.contrib.sites.shortcuts import get_current_site
from django.db import transaction
from django.db.utils import IntegrityError
from django.db.models import Q, F, OuterRef, Subquery, Value
from django.db.models.functions import Coalesce
from django.utils import timezone
from django.template.loader import render_to_string
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.core.signing import dumps, loads, SignatureExpired, BadSignature
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash, logout
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.views import LoginView
from django.http import JsonResponse, HttpResponseNotFound, Http404
from django.urls import reverse
from django.utils.timesince import timesince
from django.views.decorators.http import require_GET
from base64 import binascii
from datetime import datetime, timedelta, timezone as dt_timezone
from .models import BlogPosts, User, ChessLobby, ActiveGames, GameHistoryTable, ActiveChatMessages, ChatMessages, UserSettings
from .models import  Lessons, Pages, EmbeddedGames, Message, Challenge, Blocks, Notification, ReportedChats
from .forms import ChangeEmailForm, EditProfile, CloseAccount, ChangeThemesForm, CreateNewGameForm, BoardEditorForm, GameSearch
from .user_settings import default_themes
from .game_helpers import *
from .screenshot import *
from .screenshot.save_image import save_screenshot
import uuid
import json
import random
import jwt
import re
import os

def get_static_file_path(file_name):
    if settings.DEBUG:
        return os.path.join('.', 'static', 'images', file_name)
    else:
        print(os.listdir(os.getcwd()))
        return os.path.join('./app', 'static_collected_files', file_name)

def index(request):
    return render(request, "main/home.html", {})

def home(request):
    recent_blogs = BlogPosts.objects.all().order_by('-timestamp')[:2]
    context = {"blogs": recent_blogs}
    if request.user and request.user.id is not None:
        user_id = request.user.id
    else:
        user_id = request.session.get('guest_uuid')

    time_threshold = timezone.now() - timedelta(minutes=5)
    preview_game = None
    preview_game_available = False
    if ActiveGames.objects.exists():
        lobby_subquery = ChessLobby.objects.filter(
            lobby_id=OuterRef('active_game_id'),  # Match lobby_id to active_game_id
            private=False,
            computer_game=False,
            solo_game=False
        ).exclude(gametype='Classical')
        preview_game = ActiveGames.objects.filter(
            active_game_id__in=Subquery(lobby_subquery.values('lobby_id')),
            start_time__gte=time_threshold
        ).annotate(
            white_username=Coalesce(
                Subquery(
                    User.objects.filter(id=OuterRef('white_id')).values('username')[:1]
                ), Value("Anonymous")
            ),
            black_username=Coalesce(
                Subquery(
                    User.objects.filter(id=OuterRef('black_id')).values('username')[:1]
                ), Value("Anonymous")
            )
        ).values(
            'active_game_id',
            'white_username',
            'black_username',
            'start_time'
        ).order_by('?').first()
        preview_game_available = True if preview_game else False
    context["preview_game"] = preview_game
    context["preview_game_available"] = preview_game_available

    # Active games with the same id, where there is a disconnect via the lobby column, and it matches the lobby game id
    games_in_play = ChessLobby.objects.filter(
        lobby_id__in=ActiveGames.objects.filter(
            Q(white_id=user_id) | Q(black_id=user_id),
        ).values('active_game_id')
    ).filter(
        Q(opponent_connected=False) | Q(initiator_connected=False)
    ).annotate(
        fen=Subquery(ActiveGames.objects.filter(
            active_game_id=OuterRef('lobby_id')
        ).values('FEN')[:1]),
        start_time=Subquery(ActiveGames.objects.filter(
            active_game_id=OuterRef('lobby_id')
        ).values('start_time')[:1])
    ).order_by('-start_time')

    context["has_games_in_play"] = bool(games_in_play)
    for game in games_in_play:
        if game.white_id == user_id:
            opponent_id = game.black_id
        else:
            opponent_id = game.white_id
        try:
            opponent_username = User.objects.get(id=opponent_id)
            opponent_username = opponent_username.username
        except User.DoesNotExist:
            opponent_username = "Anonymous"
        game.opponent_name = opponent_username
        game.FEN_image_name = "/media/" + game.fen.replace("/", "-") + ".png" if game.fen is not None else ""

    context["games_in_play"] = games_in_play
    context['form'] = CreateNewGameForm()
    context['white_side_svg'] = open(get_static_file_path("side-white.svg")).read()
    context['black_side_svg'] = open(get_static_file_path("side-black.svg")).read()
    context['random_side_svg'] = open(get_static_file_path("side-random.svg")).read()
    context['complete_svg'] = open(get_static_file_path("complete-variant-icon.svg")).read()
    context['relay_svg'] = open(get_static_file_path("reveal-stage-icon.svg")).read()
    context['countdown_svg'] = open(get_static_file_path("decision-stage-icon.svg")).read()
    context['standard_svg'] = open(get_static_file_path("decision-icon-colored.svg")).read()
    context['x_svg'] = open(get_static_file_path("x.svg")).read()
    context['envelope_svg'] = open(get_static_file_path("envelope.svg")).read()
    context['hourglass_svg'] = open(get_static_file_path("hourglass.svg")).read()
    context['bird_svg'] = open(get_static_file_path("bird.svg")).read()
    context['lightning_svg'] = open(get_static_file_path("lightning.svg")).read()
    context['eye_svg'] = open(get_static_file_path("eye.svg")).read()
    context['masks_svg'] = open(get_static_file_path("masks.svg")).read()
    context['a1_svg'] = open(get_static_file_path("a1.svg")).read()
    context['b1_svg'] = open(get_static_file_path("b1.svg")).read()
    context['classic_svg'] = open(get_static_file_path("classic-icon.svg")).read()
    return render(request, "main/home.html", context)

class CustomLoginView(LoginView):
    template_name = 'main/login.html'

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('home')
        return super().dispatch(request, *args, **kwargs)

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
            if request.method == "POST": # do an earlier check and pass
                data = json.loads(request.body.decode('utf-8'))
                if data.get('computer_game'):
                    new_open_game.computer_game = True
                    new_open_game.private = True
                    new_open_game.opponent_name = "minimax" # Later look up name with more bots
                elif data.get('solo'): # TODO do validation of subvariant and main mode with this and not timed mode and not ranked for some of these
                    new_open_game.solo_game = True
                    new_open_game.private = True
                if data.get('rematch'):
                    # Make rematches private?
                    try:
                        historic = GameHistoryTable.objects.get(historic_game_id=data.get('rematch'))
                        opponent_id = getattr(historic, opponent_column_to_fill)
                        setattr(new_open_game, opponent_column_to_fill, opponent_id)
                        data["subvariant"] = historic.subvariant
                        data["main_mode"] = "Decision" if historic.gametype in ["Complete", "Relay", "Countdown", "Standard"] else "Classical"
                        if user_id == historic.white_id:
                            data["position"] = "white"
                        elif user_id == historic.black_id:
                            data["position"] = "black"
                        else:
                            return JsonResponse({"status": "error", "message": "Unauthorized"}, status=401)    
                        try:
                            opponent = User.objects.get(id=opponent_id)
                            new_open_game.opponent_name = opponent.username
                        except User.DoesNotExist:
                            new_open_game.opponent_name = "Anonymous"
                    except:
                        return JsonResponse({"status": "error", "message": "Recent Game DNE"}, status=401)
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
                if (data.get('subvariant') in ["Normal", "Classical", "Rapid", "Blitz"] and new_open_game.gametype == "Standard") or\
                   (data.get('subvariant') in ["Normal", "Suggestive"] and new_open_game.gametype in ["Complete", "Relay", "Countdown"]):
                    if new_open_game.gametype != "Standard":
                        new_open_game.subvariant = data.get('subvariant') if data.get('subvariant') != "Normal" else "Simple"
                    else:
                        new_open_game.subvariant = data.get('subvariant')
                        increment = data.get('increment')
                        if increment is None or not (increment.isdigit() and int(increment) >= 0):
                            return JsonResponse({"status": "error", "message": "Unauthorized"}, status=401)
                        new_open_game.increment = int(increment)
                elif data.get('main_mode') != 'Classical':
                    return JsonResponse({"status": "error", "message": "Unauthorized"}, status=401)
                ranked = data.get('ranked')
                if ranked is not None:
                    new_open_game.match_type = ranked
                column_to_fill = 'white_rank_start' if new_open_game.initiator_color == 'white' else 'black_rank_start'
                rank_mapping = {
                    ("Standard", "Normal"): "rank_normal",
                    ("Standard", "Classical"): "rank_classical",
                    ("Standard", "Rapid"): "rank_rapid",
                    ("Standard", "Blitz"): "rank_blitz",
                    ("Complete", "Simple"): "rank_complete_simple",
                    ("Complete", "Suggestive"): "rank_complete_suggestive",
                    ("Relay", "Simple"): "rank_relay_simple",
                    ("Relay", "Suggestive"): "rank_relay_suggestive",
                    ("Countdown", "Simple"): "rank_countdown_simple",
                    ("Countdown", "Suggestive"): "rank_countdown_suggestive",
                }

                rank_attr = rank_mapping.get((new_open_game.gametype, new_open_game.subvariant))
                if rank_attr and request.user and request.user.id is not None:
                    setattr(new_open_game, column_to_fill, getattr(request.user, rank_attr))
                state = None
                if data.get('FEN'):
                    new_open_game.private = True
                    state = custom_state(data.get('FEN'), data.get('castling_rights'), new_open_game.gametype)
                    if state is None or data.get('main_mode') != 'Decision':
                        print("HERE1")
                        return JsonResponse({"status": "error", "message": "Bad Request"}, status=400)
                    new_open_game.initial_state = state
                    new_open_game.FEN = data.get('FEN')
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

    lobby_games = ChessLobby.objects.filter(is_open=True, private=False, computer_game=False, solo_game=False)
    position_filter = request.GET.get('position')
    username_filter = request.GET.get('username')

    position_query = Q()
    if position_filter == 'white':
        position_query = Q(Q(white_id__isnull=True) & Q(initiator_color="black"))
    elif position_filter == 'black':
        position_query = Q(Q(black_id__isnull=True) & Q(initiator_color="white"))

    match_type_query = Q()
    if not request.user or request.user.id is None:
        match_type_query = Q(match_type='Casual')

    lobby_games = lobby_games.filter(
        Q(initiator_name=username_filter) if username_filter else Q(),
        position_query,
        match_type_query
    )
    serialized_data = [
        {
            "initiator_name": game.initiator_name,
            "game_uuid": game.lobby_id,
            "timestamp": game.timestamp.strftime("%H:%M:%S"), # TODO Remove?
            "side": "white" if game.white_id is None else "black",
            "game_type": game.gametype,
            "subvariant": game.subvariant,
            "ranked": game.match_type,
            "initiator_elo": game.white_rank_start if game.initiator_color == 'white' else game.black_rank_start,
            "increment": game.increment
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
    if type == 'live' or type == 'spectate':
        try:
            game = ChessLobby.objects.get(lobby_id=game_uuid)
            if type == 'live' and str(user_id) not in [str(game.white_id), str(game.black_id)]:
                return JsonResponse({"status": "error"}, status=401)
            fill = None
            if type == 'live':
                if str(user_id) == str(game.white_id) == str(game.black_id):
                    if game.initiator_color == "black":
                        fill = "white" if game.opponent_connected else "black"
                    elif game.initiator_color == "white":
                        fill = "black" if game.opponent_connected else "white"
                    else:
                        return JsonResponse({"status": "error"}, status=401)
                elif str(user_id) == str(game.white_id):
                    fill = "white"
                elif str(user_id) == str(game.black_id):
                    fill = "black"
                else:
                    return JsonResponse({"status": "error"}, status=401)

            return JsonResponse({
                "message": {
                    "starting_side": fill, 
                    "game_type": game.gametype, 
                    "theme_names": theme_names, 
                    "subvariant": game.subvariant,
                    "increment": game.increment
                    }
                }, status=200)
        except ChessLobby.DoesNotExist:
            try:
                game = GameHistoryTable.objects.get(historic_game_id=game_uuid)
                return JsonResponse({
                    "message": {
                        "starting_side": fill,
                        "game_type": game.gametype, 
                        "theme_names": theme_names, 
                        "subvariant": game.subvariant,
                        "increment": game.increment
                        }
                    }, status=200)
            except GameHistoryTable.DoesNotExist:
                return JsonResponse({"status": "error"}, status=401)
    elif type == 'historic':
        try:
            game = GameHistoryTable.objects.get(historic_game_id=game_uuid)
            return JsonResponse({
                "message": {
                    "game_type": game.gametype, 
                    "theme_names": theme_names, 
                    "subvariant": game.subvariant,
                    "increment": game.increment
                    }
                }, status=200)
        except GameHistoryTable.DoesNotExist:
            return JsonResponse({"status": "error"}, status=401)
    elif type == 'exercise':
        try:
            game = EmbeddedGames.objects.get(embedded_game_id=game_uuid)
            indexed_moves_json = json.loads(game.indexed_moves)
            return JsonResponse({
                "message": {"starting_side": game.side, 
                            "game_type": game.gametype, 
                            "theme_names": theme_names, 
                            "FEN": game.FEN, 
                            "indexed_moves": indexed_moves_json
                            }
                }, status=200)
        except EmbeddedGames.DoesNotExist:
            return JsonResponse({"status": "error"}, status=401)
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
    rank_mapping = {
        ("Standard", "Normal"): "rank_normal",
        ("Standard", "Classical"): "rank_classical",
        ("Standard", "Rapid"): "rank_rapid",
        ("Standard", "Blitz"): "rank_blitz",
        ("Complete", "Simple"): "rank_complete_simple",
        ("Complete", "Suggestive"): "rank_complete_suggestive",
        ("Relay", "Simple"): "rank_relay_simple",
        ("Relay", "Suggestive"): "rank_relay_suggestive",
        ("Countdown", "Simple"): "rank_countdown_simple",
        ("Countdown", "Suggestive"): "rank_countdown_suggestive",
        ("Classical", "Normal"): None
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

        player_rank = "1500?"
        opponent_rank = "1500?"
        rank_attr = rank_mapping.get((game.gametype, game.subvariant))
        if rank_attr and request.user and request.user.id is not None:
            player_rank = getattr(request.user, rank_attr)
        try:
            opponent_user = User.objects.get(username=opponent)
            if rank_attr:
                opponent_rank = getattr(opponent_user, rank_attr)
        except User.DoesNotExist:
            pass
        sessionVariables['player_rank'] = player_rank
        sessionVariables['opponent_rank'] = opponent_rank

        with open(get_static_file_path("reveal-stage-icon.svg"), 'r') as f:
            sessionVariables["relay_svg"] = f.read()

        if (game.computer_game or game.solo_game) and str(user_id) in [str(game.white_id), str(game.black_id)]:
            solo_html = "main/play/computer.html" if game.gametype == 'Classical' else "main/play/decision_computer.html"
            sessionVariables['computer_game'] = True if game.computer_game else False
            return render(request, solo_html, sessionVariables) ## TODO rename html file name and this variable so it's agnostic for solo or computer games
        elif not game.is_open and str(user_id) not in [str(game.white_id), str(game.black_id)]:
            active_game_exists = ActiveGames.objects.filter(active_game_id=game_uuid).exists()
            if game.computer_game or game.solo_game or game.private or not active_game_exists:
                return redirect('home')
            else:
                if game.initiator_color == "white":
                    sessionVariables.update({'white': game.initiator_name, 'black': game.opponent_name})
                elif game.initiator_color == "black":
                    sessionVariables.update({'white': game.opponent_name, 'black': game.initiator_name})
                if game.gametype != 'Classical':
                    return render(request, "main/play/decision_spectate.html", sessionVariables)
                else:
                    return redirect("home")
        elif str(user_id) in [str(game.white_id), str(game.black_id)]:
            # For now we will allow multiple joins even from the same person after they've connected twice
            # This logic not for ranked modes later
            if (game.black_id is None or game.white_id is None) and game.initiator_connected and game.match_type == "Ranked":
                return redirect("home")
            elif game.black_id is None and game.initiator_connected:
                game.black_id = user_id
                game.opponent_connected = True
                game.opponent_name = player
                game.save()
            elif game.white_id is None and game.initiator_connected:
                game.white_id = user_id
                game.opponent_connected = True
                game.opponent_name = player
                game.save()
            elif str(user_id) == str(game.white_id) == str(game.black_id):
                if game.initiator_connected:
                    game.opponent_connected = True
                    game.initiator_connected = False
                elif game.opponent_connected:
                    game.initiator_connected = True
                    game.opponent_connected = False
                game.save()
            game_chat_messages = ActiveChatMessages.objects.filter(game_id=game_uuid).order_by('timestamp')
            sessionVariables["chat_messages"] = game_chat_messages
            return render(request, play_html, sessionVariables)
        else:
            column_to_fill = "black_id"
            if game.white_id is None:
                column_to_fill = "white_id"
            if game.match_type == "Ranked":
                if player == "Anonymous":
                    if game.initiator_color == "white":
                        sessionVariables.update({'white': game.initiator_name, 'black': game.opponent_name})
                    elif game.initiator_color == "black":
                        sessionVariables.update({'white': game.opponent_name, 'black': game.initiator_name})
                    if game.gametype != 'Classical':
                        return render(request, "main/play/decision_spectate.html", sessionVariables)
                    else:
                        return redirect('home')
            ranked_column_to_fill = 'black_rank_start' if game.initiator_color == 'white' else 'white_rank_start'
            
            rank_attr = rank_mapping.get((game.gametype, game.subvariant))
            if rank_attr and request.user and request.user.id is not None:
                setattr(game, ranked_column_to_fill, getattr(request.user, rank_attr))
            game.opponent_connected = True
            game.opponent_name = player
            setattr(game, column_to_fill, user_id)
            game.save()
            return render(request, play_html, sessionVariables)
    except ChessLobby.DoesNotExist:
        try:
            historic = GameHistoryTable.objects.get(historic_game_id=game_uuid)
            historic_html = "main/play/historic.html" if historic.gametype == 'Classical' else "main/play/decision_historic.html"
            sessionVariables = {
                'current_game_id': str(game_uuid),
                'initialized': 'null',
                'alg_moves': historic.algebraic_moves,
                'comp_moves': historic.computed_moves,
                'FEN': historic.FEN_outcome,
                'outcome': historic.outcome,
                'forced_end': historic.termination_reason,
                'game_type': historic.gametype,
                'subvariant': historic.subvariant
            }
            rank_attr = rank_mapping.get((historic.gametype, historic.subvariant))
            try:
                white_user = User.objects.get(id=historic.white_id)
                player_rank = getattr(white_user, rank_attr) if rank_attr is not None else "1500?"
                white_user = white_user.username
            except User.DoesNotExist:
                white_user = "Anonymous"
                player_rank = "1500?"
            try:
                black_user = User.objects.get(id=historic.black_id)
                opponent_rank = getattr(black_user, rank_attr) if rank_attr is not None else "1500?"
                black_user = black_user.username
            except User.DoesNotExist:
                black_user = "Anonymous"
                opponent_rank = "1500?"
            player_side = white_user
            opponent_side = black_user
            flip = False
            if str(historic.black_id) == str(user_id) and str(historic.white_id) != str(user_id):
                player_side = black_user
                opponent_side = white_user
                flip = True
            sessionVariables['player_rank'] = player_rank
            sessionVariables['opponent_rank'] = opponent_rank
            sessionVariables.update({'player': player_side, 'opponent': opponent_side, 'init_flip': flip})
            game_chat_messages = ChatMessages.objects.filter(game_id=game_uuid).order_by('timestamp')
            sessionVariables["chat_messages"] = game_chat_messages
            return render(request, historic_html, sessionVariables)
        except GameHistoryTable.DoesNotExist:
            return redirect('home')
        except:
            return JsonResponse({"status": "error"}, status=401)

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
                elif data.get('computer_game') == False: # TODO check if we need to remove this, does nothing currently?
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
                else:
                    field_to_update = "opponent_connected" if web_connect else "initiator_connected"
                    setattr(game, field_to_update, web_connect)
                game.save()
                try:
                    active_game = ActiveGames.objects.get(active_game_id=connect_game_uuid)
                    if not web_connect:
                        filename = active_game.FEN.replace('/', '-')
                        filename = os.path.join(settings.MEDIA_ROOT, f"{filename}.png")
                        if not os.path.exists(filename):
                            save_screenshot(active_game.FEN, filename)
                except ActiveGames.DoesNotExist:
                    active_game = ActiveGames(
                        active_game_id = connect_game_uuid,
                        white_id = game.white_id,
                        black_id = game.black_id,
                        gametype = game.gametype,
                        FEN = game.FEN
                    )
                    if game.initial_state is not None:
                        active_game.state = game.initial_state
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
        submit_time = datetime.utcnow()
        data = json.loads(request.body.decode('utf-8'))
        if data.get("token"):
            decoded = jwt.decode(data["token"], settings.STATE_UPDATE_KEY + str(game_uuid), algorithms=['HS256'])
            if decoded.get('game'):
                try:
                    active_game = ActiveGames.objects.get(active_game_id=game_uuid)
                    active_game.state = decoded['game']
                    active_game.FEN = decoded['FEN']
                    if str(user_id) not in [str(active_game.white_id), str(active_game.black_id)]:
                        return JsonResponse({"status": "error"}, status=401)
                    active_game.last_submission_time = submit_time
                    active_game.save()
                    return JsonResponse({"status": "updated"}, status=200)
                except ActiveGames.DoesNotExist:
                    return JsonResponse({"message": "DNE"}, status=200)
            else:
                return JsonResponse({"status": "error"}, status=400)
        else:
            return JsonResponse({"status": "error"}, status=400)
    elif request.method == "GET":
        spectator = request.GET.get('spectator')
        try:
            active_game = ActiveGames.objects.get(active_game_id=game_uuid)
            if active_game.state == "":
                return JsonResponse({"message": "DNE"}, status=200)
            if spectator is None and str(user_id) not in [str(active_game.white_id), str(active_game.black_id)]:
                return JsonResponse({"status": "error"}, status=401)
            token = jwt.encode(json.loads(active_game.state), settings.STATE_UPDATE_KEY + str(game_uuid), algorithm='HS256')
            last_submit = active_game.last_submission_time.isoformat() if active_game.last_submission_time is not None else None
            retrieved = datetime.now(dt_timezone.utc).isoformat()
            return JsonResponse({"token": token, "submitted": last_submit, "retrieved": retrieved}, status=200)
        except ActiveGames.DoesNotExist:
            try:
                lobby_game = ChessLobby.objects.get(lobby_id=game_uuid)
                if lobby_game.initial_state is None:
                    raise ChessLobby.DoesNotExist
                initial_state = json.loads(lobby_game.initial_state)
                initial_state["custom_start"] = True
                token = jwt.encode(initial_state, settings.STATE_UPDATE_KEY + str(game_uuid), algorithm='HS256')
                return JsonResponse({"token": token}, status=200)
            except ChessLobby.DoesNotExist:
                try:
                    finished_game = GameHistoryTable.objects.get(historic_game_id=game_uuid)
                    token = jwt.encode(json.loads(finished_game.state), settings.STATE_UPDATE_KEY + str(game_uuid), algorithm='HS256')
                    return JsonResponse({"token": token}, status=200)
                except GameHistoryTable.DoesNotExist:
                    return JsonResponse({"message": "DNE"}, status=200)

def expected_probability(Ra, Rb):
    return 1/ (1 + 10 ** ((Rb - Ra)/400))

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
                white_rank_new, black_rank_new = save_chat_and_game(active_game, lobby_game, data)
            except Exception:
                return JsonResponse({"status": "error", "message": "Game and chat not Saved"}, status=400)
            lobby_game.delete()
            active_game.delete()
            filename = active_game.FEN.replace('/', '-')
            filename = os.path.join(settings.MEDIA_ROOT, f"{filename}.png")
            if not os.path.exists(filename):
                save_screenshot(active_game.FEN, filename)
            response = {"status": "updated"}
            if white_rank_new is not None: # Maybe return username
                response.update({"white_rank": white_rank_new, "black_rank": black_rank_new})
            return JsonResponse(response, status=200)
        except ActiveGames.DoesNotExist:
            try:
                saved_game = GameHistoryTable.objects.get(historic_game_id=completed_game_uuid)
                response = {}
                if saved_game.white_rank_change is not None: # Maybe return username
                    # white_user = User.objects.get(id=saved_game.white_id)
                    # black_user = User.objects.get(id=saved_game.black_id)
                    response.update({"white_rank_new": [saved_game.white_rank_change], "black_rank_new": [saved_game.black_rank_change]})
                return JsonResponse(response, status=200)
            except:
                return JsonResponse({"status": "error", "message": "Game DNE"}, status=400)

@transaction.atomic
def save_chat_and_game(active_game, lobby_game, data):
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

    completed_game = GameHistoryTable(
        historic_game_id=active_game.active_game_id,
        white_id=active_game.white_id,
        black_id=active_game.black_id,
        algebraic_moves=data.get('alg_moves'),
        start_time=active_game.start_time,
        gametype=active_game.gametype,
        subvariant=lobby_game.subvariant,
        outcome=data.get('outcome'),
        computed_moves=data.get('comp_moves'),
        FEN_outcome=data.get('FEN'),
        termination_reason=data.get('termination_reason'),
        state = active_game.state,
        increment = lobby_game.increment
    )
    if lobby_game.match_type == 'Ranked':
        expected_white_probability = expected_probability(lobby_game.white_rank_start, lobby_game.black_rank_start)
        expected_black_probability = expected_probability(lobby_game.black_rank_start, lobby_game.white_rank_start)
        white_score, black_score = 0, 0
        if data.get('outcome') == '1-1':
            white_score = 1.25
            black_score = 1.25
        elif data.get('outcome') == '1-0':
            white_score = 1
            black_score = 0
        elif data.get('outcome') == '0-1':
            white_score = 0
            black_score = 1
        elif data.get('outcome') == '½–½':
            white_score = 0.5
            black_score = 0.5
        completed_game.white_rank_start = lobby_game.white_rank_start
        completed_game.black_rank_start = lobby_game.black_rank_start
        white_rank_change = 32 * (white_score - expected_white_probability)
        black_rank_change = 32 * (black_score - expected_black_probability)
        completed_game.white_rank_change = white_rank_change
        completed_game.black_rank_change = black_rank_change
        completed_game.match_type = 'Ranked'
        white_user = User.objects.get(id=completed_game.white_id)
        black_user = User.objects.get(id=completed_game.black_id)
        rank_mapping = {
            ("Standard", "Normal"): "rank_normal",
            ("Standard", "Classical"): "rank_classical",
            ("Standard", "Rapid"): "rank_rapid",
            ("Standard", "Blitz"): "rank_blitz",
            ("Complete", "Simple"): "rank_complete_simple",
            ("Complete", "Suggestive"): "rank_complete_suggestive",
            ("Relay", "Simple"): "rank_relay_simple",
            ("Relay", "Suggestive"): "rank_relay_suggestive",
            ("Countdown", "Simple"): "rank_countdown_simple",
            ("Countdown", "Suggestive"): "rank_countdown_suggestive",
        }
        rank_attr = rank_mapping.get((completed_game.gametype, completed_game.subvariant))
        setattr(white_user, rank_attr, getattr(white_user, rank_attr) + white_rank_change)
        setattr(black_user, rank_attr, getattr(black_user, rank_attr) + black_rank_change)
        white_rank_new = getattr(white_user, rank_attr)
        black_rank_new = getattr(black_user, rank_attr)
        white_user.save()
        black_user.save()
    if lobby_game.initial_state is not None:
        completed_game.initial_state = lobby_game.initial_state
    completed_game.save()
    if lobby_game.match_type == 'Ranked':
        return [white_rank_new, completed_game.white_rank_change], [black_rank_new, completed_game.black_rank_change]
    else:
        return None, None

def report_chat(request):
    if request.method == "POST":
        data = json.loads(request.body)

        game_id = data["game_id"]
        if not ReportedChats.objects.filter(game_id=game_id).exists():
            report = ReportedChats(
                game_id= game_id
            )
            report.save()
            return JsonResponse({"status": "OK"}, status=200)
    return JsonResponse({"status": "Unauthorized"}, status=401) 


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

def lesson(request, lesson):
    lesson = Lessons.objects.get(url_name=lesson)
    pages = Pages.objects.filter(lesson=lesson.lesson_id).order_by("page_position")
    embedded_game_ids = []
    for page in pages:
        embedded_game_ids.append(page.embedded_game.embedded_game_id)
    return render(request, "main/lesson.html", {"pages": pages, "embedded_game_ids": embedded_game_ids, "title": lesson.title})

def variants(request):
    svg_files = {
        'standard_svg': get_static_file_path("decision-icon-colored.svg"),
        'envelope_svg': get_static_file_path("envelope.svg"),
        'hourglass_svg': get_static_file_path("hourglass.svg"),
        'bird_svg': get_static_file_path("bird.svg"),
        'lightning_svg': get_static_file_path("lightning.svg"),
        'relay_svg': get_static_file_path("reveal-stage-icon.svg"),
        'eye_svg': get_static_file_path("eye.svg"),
        'masks_svg': get_static_file_path("masks.svg"),
        'countdown_svg': get_static_file_path("decision-stage-icon.svg"),
        'complete_svg': get_static_file_path("complete-variant-icon.svg"),
    }
    context = {}
    for key, path in svg_files.items():
        with open(path, 'r') as f:
            context[key] = f.read()
    context['standard_svg'] = context['standard_svg'].replace("svg-scaled-circle", "standard")
    context['envelope_svg'] = context['envelope_svg'].replace("svg-scaled-circle", "envelope")
    context['hourglass_svg'] = context['hourglass_svg'].replace("svg-scaled-circle", "hourglass")
    context['bird_svg'] = context['bird_svg'].replace("svg-scaled-circle", "bird")
    context['lightning_svg'] = context['lightning_svg'].replace("svg-scaled-circle", "lightning")
    context['relay_svg'] = context['relay_svg'].replace("svg-scaled-circle", "relay")
    context['eye_svg'] = context['eye_svg'].replace("svg-scaled-circle", "eye")
    context['masks_svg'] = context['masks_svg'].replace("svg-scaled-circle", "masks")
    context['countdown_svg'] = context['countdown_svg'].replace("svg-scaled-circle", "countdown")
    context['complete_svg'] = context['complete_svg'].replace("svg-scaled-complete", "complete")
    return render(request, "main/variants.html", context)

def news(request):
    blogs = BlogPosts.objects.all().order_by('-timestamp')
    return render(request, "main/news.html", {"blogs": blogs})

def live(request):
    types_param = request.GET.get('type')
    types = types_param.split(",") if types_param is not None else []
    user_type_param = request.GET.get('user_type')
    user_param = request.GET.get('user')
    active_games = []
    if ActiveGames.objects.exists():
        lobby_subquery = ChessLobby.objects.filter(
            lobby_id=OuterRef('active_game_id'),
            private=False,
            computer_game=False,
            solo_game=False
        ).exclude(gametype='Classical')

        game_filter = Q(gametype__in=types) if types else Q(gametype="Standard")
        if user_param:
            if user_type_param == "white":
                game_filter &= Q(
                    white_id__in=Subquery(
                        User.objects.filter(username__icontains=user_param).values('id')
                    )
                )
            elif user_type_param == "black":
                game_filter &= Q(
                    black_id__in=Subquery(
                        User.objects.filter(username__icontains=user_param).values('id')
                    )
                )
            elif user_type_param == "any":
                game_filter &= Q(
                    Q(white_id__in=Subquery(
                        User.objects.filter(username__icontains=user_param).values('id')
                    )) |
                    Q(black_id__in=Subquery(
                        User.objects.filter(username__icontains=user_param).values('id')
                    ))
                )
            else:
                return JsonResponse({"status": "error", "message": "Invalid user_type value"}, status=400)

        returned_active_games = ActiveGames.objects.filter(
            game_filter,
            active_game_id__in=Subquery(lobby_subquery.values('lobby_id'))
        ).annotate(
            white_username=Coalesce(
                Subquery(
                    User.objects.filter(id=OuterRef('white_id')).values('username')[:1]
                ), Value("Anonymous")
            ),
            black_username=Coalesce(
                Subquery(
                    User.objects.filter(id=OuterRef('black_id')).values('username')[:1]
                ), Value("Anonymous")
            )
        ).values(
            'active_game_id',
            'gametype',
            'white_username',
            'black_username',
            'start_time'
        ).order_by('?')[:100]

        for game in returned_active_games:
            date_obj = datetime.strptime(str(game["start_time"]), "%Y-%m-%d %H:%M:%S.%f%z")
            game["start_time"] = date_obj.strftime("%H:%M:%S %m-%d")
            game["white_username"] = "Anon" if game["white_username"] == "Anonymous" else game["white_username"]
            game["black_username"] = "Anon" if game["black_username"] == "Anonymous" else game["black_username"]
        active_games = [ game for game in returned_active_games ]
    
    if types_param is not None:
        if active_games != []:
            return JsonResponse({"status": "OK", "active_games": active_games}, status=200)
        else:
            return JsonResponse({"status": "DNE", "message": "no games"}, status=200)
    context = {"active_games": active_games}
    context['complete_svg'] = open(get_static_file_path("complete-variant-icon.svg")).read()
    context['relay_svg'] = open(get_static_file_path("reveal-stage-icon.svg")).read()
    context['countdown_svg'] = open(get_static_file_path("decision-stage-icon.svg")).read()
    context['standard_svg'] = open(get_static_file_path("decision-icon-colored.svg")).read()
    return render(request, "main/live.html", context)

def board_editor(request):
    form = BoardEditorForm()
    game_form = CreateNewGameForm()
    return render(request, "main/board_editor.html", {'form': form, 'game_form': game_form})

def game_search(request):
    form = GameSearch(request.GET or None)
    games_details = []
    context = {
        "form": form,
        "games_details": games_details
    }

    if form.is_valid():
        player_1 = form.cleaned_data.get('player_1')
        player_2 = form.cleaned_data.get('player_2')
        white = form.cleaned_data.get('white')
        black = form.cleaned_data.get('black')
        outcome = form.cleaned_data.get('outcome')
        winning_player = form.cleaned_data.get('winning_player')
        losing_player = form.cleaned_data.get('losing_player')
        game_type = form.cleaned_data.get('game_type')
        start_date = form.cleaned_data.get('start_date')
        timezone_offset = request.GET.get('timezone', None)

        player_1 = player_1.strip() or None
        player_2 = player_2.strip() or None
        player_1_id = None
        player_2_id = None
        try:
            if player_1 is not None:
                    player_1_id = User.objects.get(username=player_1).id
            if player_2 is not None:
                    player_2_id = User.objects.get(username=player_2).id
        except User.DoesNotExist:
            return render(request, "main/game_search.html", context)
        
        white = None if white.strip() == '' else white
        black = None if black.strip() == '' else black
        white_id = player_1_id if white == player_1 else player_2_id if white == player_2 else None
        black_id = player_1_id if black == player_1 else player_2_id if black == player_2 else None
        
        outcome = None if outcome.strip() == '' else outcome
        
        winning_player = None if winning_player.strip() == '' else winning_player
        losing_player = None if losing_player.strip() == '' else losing_player
        winning_id = player_1_id if winning_player == player_1 else player_2_id
        losing_id = player_1_id if losing_player == player_1 else player_2_id
        
        game_type = None if game_type.strip() == '' else game_type

        player_filter = Q()
        if white_id and black_id:
            player_filter = Q(white_id=white_id, black_id=black_id)
        elif white_id:
            remaining_player_id = player_1_id if player_1_id != white_id else player_2_id
            if remaining_player_id is not None:
                player_filter = Q(white_id=white_id, black_id=remaining_player_id)
            else:
                player_filter = Q(white_id=white_id)
        elif black_id:
            remaining_player_id = player_1_id if player_1_id != black_id else player_2_id
            if remaining_player_id is not None:
                player_filter = Q(white_id=remaining_player_id, black_id=black_id)
            else:
                player_filter = Q(black_id=black_id)
        elif player_1_id or player_2_id:
            if player_1_id is not None and player_2_id is not None:
                player_filter = Q(white_id=player_1_id) & Q(black_id=player_2_id) | \
                                Q(white_id=player_2_id) & Q(black_id=player_1_id)
            elif player_1_id is not None:
                player_filter |= Q(white_id=player_1_id) | Q(black_id=player_1_id)
            elif player_2_id is not None:
                player_filter |= Q(white_id=player_2_id) | Q(black_id=player_2_id)

        outcome_filter = Q()
        if outcome:
            if outcome == '1-0 or 0-1':
                outcome_filter = Q(outcome__in=['1-0', '0-1'])
            else:
                outcome_filter = Q(outcome=outcome)

        if outcome in ['1-0', '0-1', '1-0 or 0-1'] and winning_player:
            if outcome == '1-0':
                outcome_filter &= Q(white_id=winning_id)
            elif outcome == '0-1':
                outcome_filter &= Q(black_id=winning_id)

        if outcome in ['1-0', '0-1', '1-0 or 0-1'] and losing_player:
            if outcome == '1-0':
                outcome_filter &= Q(black_id=losing_id)
            elif outcome == '0-1':
                outcome_filter &= Q(white_id=losing_id)

        game_type_filter = Q(gametype=game_type) if game_type else Q()

        date_filter = Q()
        if start_date and timezone_offset:
            start_date = datetime.combine(start_date, datetime.min.time())
            start_date = start_date - timedelta(minutes=int(timezone_offset))
            start_date = timezone.make_aware(start_date)
            date_filter = Q(start_time__gte=start_date)

        filters = (
            player_filter &
            outcome_filter &
            game_type_filter &
            date_filter
        )
        historic_games = GameHistoryTable.objects.filter(filters).order_by('-start_time')
        for game in historic_games:
            try:
                black_username = User.objects.get(id=game.black_id).username
            except User.DoesNotExist:
                black_username = "Anonymous"

            try:
                white_username = User.objects.get(id=game.white_id).username
            except User.DoesNotExist:
                white_username = "Anonymous"
            relative_game_time = timesince(game.end_time, datetime.utcnow().replace(tzinfo=dt_timezone.utc))
            result = []
            if game.gametype == 'classical':
                move_list = game.algebraic_moves.split(',')
            else:
                move_list = json.loads(game.algebraic_moves)
            end_scores = ['0-0', '1-0', '0-1', '½–½', '1-1']
            for string in end_scores:
                if string in move_list:
                    move_list.remove(string)
            if game.gametype == 'classical':
                for i in range(0, len(move_list), 2):
                    pair = move_list[i:i+2]
                    pair_string = " ".join(pair)
                    result.append(f"{(i//2) + 1}. {pair_string}")
            else:
                for i in range(0, len(move_list)):
                    pair_string = ", ".join(move_list[i])
                    result.append(f"{i + 1}. {pair_string}")
            
            init_index = 2 if len(move_list) > 5 else len(result)
            formatted_moves_string = " ".join(result[:init_index])
            if len(move_list) > 5:
                formatted_moves_string += f" ... {result[-1]}"
            games_details.append({
                'game_id': game.historic_game_id,
                'outcome': game.outcome,
                'white_name': white_username,
                'black_name': black_username,
                'game_type': game.gametype.capitalize(),
                'relative_game_time': relative_game_time,
                'formatted_moves_string': formatted_moves_string,
                'FEN_image_name': "/media/" + game.FEN_outcome.replace('/', '-') + ".png"
            })
        context["games_details"] = games_details
            
    else:
        form = GameSearch()
    
    return render(request, "main/game_search.html", context)

def leaderboards(request):
    ranks = [
        ("rank_normal", "standard_normal_users"),
        ("rank_classical", "standard_classical_users"),
        ("rank_rapid", "standard_rapid_users"),
        ("rank_blitz", "standard_blitz_users"),
        ("rank_relay_simple", "relay_simple_users"),
        ("rank_relay_suggestive", "relay_suggestive_users"),
        ("rank_countdown_simple", "countdown_simple_users"),
        ("rank_countdown_suggestive", "countdown_suggestive_users"),
        ("rank_complete_simple", "complete_simple_users"),
        ("rank_complete_suggestive", "complete_suggestive_users"),
    ]

    rank_lists = []

    for rank_field, _ in ranks:
        rank_users = User.objects.filter(bot_account=False) \
            .values_list("username", rank_field) \
            .order_by(f'-{rank_field}')[:10]
        
        rank_lists.append(list(rank_users))

    context = {"rank_lists": rank_lists}
    svg_files = {
        'standard_svg': get_static_file_path("decision-icon-colored.svg"),
        'envelope_svg': get_static_file_path("envelope.svg"),
        'hourglass_svg': get_static_file_path("hourglass.svg"),
        'bird_svg': get_static_file_path("bird.svg"),
        'lightning_svg': get_static_file_path("lightning.svg"),
        'relay_svg': get_static_file_path("reveal-stage-icon.svg"),
        'relay_eye_svg': get_static_file_path("eye.svg"),
        'relay_masks_svg': get_static_file_path("masks.svg"),
        'countdown_svg': get_static_file_path("decision-stage-icon.svg"),
        'complete_svg': get_static_file_path("complete-variant-icon.svg"),
    }

    for key, path in svg_files.items():
        with open(path, 'r') as f:
            context[key] = f.read()

    context['countdown_eye_svg'] = context['relay_eye_svg']
    context['countdown_masks_svg'] = context['relay_masks_svg']
    context['complete_eye_svg'] = context['relay_eye_svg']
    context['complete_masks_svg'] = context['relay_masks_svg']

    mapping = {
        'standard_svg': 'rgb(var(--standard-boards))', 
        'envelope_svg': 'var(--standard-subvariant-icons)', 
        'hourglass_svg': 'var(--standard-subvariant-icons)',
        'bird_svg': 'var(--standard-subvariant-icons)',
        'lightning_svg': 'var(--standard-subvariant-icons)',
        'relay_svg': 'rgb(var(--relay-boards))',
        'relay_eye_svg': 'var(--relay-subvariant-icons)',
        'relay_masks_svg': 'var(--relay-subvariant-icons)',
        'countdown_svg': 'rgb(var(--countdown-boards))',
        'countdown_eye_svg': 'var(--countdown-subvariant-icons)',
        'countdown_masks_svg': 'var(--countdown-subvariant-icons)',
        'complete_svg': 'rgb(var(--complete-boards))',
        'complete_eye_svg': 'var(--complete-subvariant-icons)',
        'complete_masks_svg': 'var(--complete-subvariant-icons)',
    }

    for svg, fill in mapping.items():
        context[svg] = re.sub(r"fill='.*?'", f"fill='{fill}'", context[svg])
        context[svg] = re.sub(r'fill=".*?"', f'fill="{fill}"', context[svg])
    return render(request, "main/leaderboards.html", context)

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
    wins = []
    losses = []
    draws = []
    win_wins = []
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
        if game.gametype == 'classical':
            move_list = game.algebraic_moves.split(',')
        else:
            move_list = json.loads(game.algebraic_moves)
        end_scores = ['0-0', '1-0', '0-1', '½–½', '1-1']
        for string in end_scores:
            if string in move_list:
                move_list.remove(string)
        if game.gametype == 'classical':
            for i in range(0, len(move_list), 2):
                pair = move_list[i:i+2]
                pair_string = " ".join(pair)
                result.append(f"{(i//2) + 1}. {pair_string}")
        else:
            for i in range(0, len(move_list)):
                pair_string = ", ".join(move_list[i])
                result.append(f"{i + 1}. {pair_string}")
        
        init_index = 2 if len(move_list) > 5 else len(result)
        formatted_moves_string = " ".join(result[:init_index])
        if len(move_list) > 5:
            formatted_moves_string += f" ... {result[-1]}"
        won = (side == 'White' and game.outcome == '1-0') \
           or (side == 'Black' and game.outcome == '0-1')
        loss = (side == 'White' and game.outcome == '0-1') \
            or (side == 'Black' and game.outcome == '1-0')
        games_details.append({
            'game_id': game.historic_game_id,
            'outcome': game.outcome,
            'opponent': opponent_username,
            'game_type': game.gametype.capitalize(),
            'side': side,
            'won': won,
            'loss': loss,
            'relative_game_time': relative_game_time,
            'formatted_moves_string': formatted_moves_string,
            'FEN_image_name': "/media/" + game.FEN_outcome.replace('/', '-') + ".png"
        })
        
    wins = [game for game in games_details if game['won']]
    losses = [game for game in games_details if game['loss']]
    draws = [game for game in games_details if game['outcome'] == '½–½']
    win_wins = [game for game in games_details if game['outcome'] == '1-1']
    
    context = {
        "profile_user": profile_user, 
        "member_since": member_since, 
        "games_details": games_details, 
        "wins": wins, 
        "losses": losses, 
        "draws": draws, 
        "win_wins": win_wins
    }

    return render(request, "main/profile.html", context)

@login_required
def inbox(request):
    user = request.user
    received = user.received_messages.all().order_by('-sent_at')
    received = received.annotate(
        sender_username=Coalesce(F('sender__username'), Value("Deleted User"))
    )
    return render(request, "main/inbox.html", {'received': received, 'form': CreateNewGameForm()})

@login_required
def message(request, message_id):
    try:
        message = Message.objects.get(message_id=message_id)
    except Message.DoesNotExist:
        return JsonResponse({"status": "error", "message": "Not found"}, status=404)
    if request.user.id != message.recipient_id:
        return JsonResponse({"status": "error", "message": "Forbidden"}, status=403)
    if message.is_deleted:
        return JsonResponse({"status": "error", "message": "This message has been deleted"}, status=404)
    if not message.is_read:
        message.is_read = True
        request.user.inbox.unread_count -= 1
        message.save()
        request.user.inbox.save()
    
    sender = message.sender
    sender_username = sender.username if sender else "Deleted User"
    return JsonResponse({
        "subject": message.subject, 
        "body": message.body, 
        "sender": sender_username, 
        "sent_at": message.sent_at
    }, status=200)

@login_required
def user_search(request):
    query = request.GET.get('user', '')
    if query:
        users = User.objects.filter(username__icontains=query).values_list('username', flat=True)
        filtered_users = list(users)
        try:
            filtered_users.remove(request.user.username)
        except:
            pass
        return JsonResponse(filtered_users, safe=False)
    else:
        return JsonResponse([], safe=False)

@login_required
def challenge(request, challenge_id):
    try:
        challenge = Challenge.objects.get(challenge_id=challenge_id)
        if request.user.username not in [challenge.opponent_name, challenge.initiator_name]:
            raise Http404("Object not found")
        context = {'initiator': request.user.username == challenge.initiator_name, 'challenge': challenge}
        if challenge.initiator_choice == "Random":
            random = open(get_static_file_path("random-pawn.svg")).read()
            context.update({
                'init_svg': random,
                'opp_svg': random
                })
        else:
            black = open(get_static_file_path("black-pawn.svg")).read()
            white = open(get_static_file_path("white-pawn.svg")).read()
            context.update({
                'init_svg': white if challenge.initiator_color == "white" else black,
                'opp_svg': white if not challenge.initiator_color == "white" else black
                })
        if challenge.gametype == "Complete":
            gametype_svg = "complete-variant-icon"
        elif challenge.gametype == "Relay":
            gametype_svg = "reveal-stage-icon"
        elif challenge.gametype == "Countdown":
            gametype_svg = "decision-stage-icon"
        else:
            gametype_svg = "decision-icon-colored" # Handle classical eventually
        context['gametype_svg'] = open(get_static_file_path(f"{gametype_svg}.svg")).read()
        context["chat_messages"] = challenge.messages.all().order_by('timestamp')
        return render(request, 'main/challenge.html', context)
    except Challenge.DoesNotExist:
        raise Http404("Object not found")

@login_required
def upsert_challenge(request):
    if request.method == "POST":
        data = json.loads(request.body)

        initiator_name = request.user.username
        opponent_name = data.get('username')
        if initiator_name == opponent_name and initiator_name != 'kjrelations':
            return JsonResponse({"status": "error", "message": "Bad Request"}, status=400)
        try:
            opponent = User.objects.get(username=opponent_name)
        except User.DoesNotExist:
            return JsonResponse({"status": "error", "message": "User DNE"}, status=404)
        initiator_blocked = Blocks.objects.filter(user=opponent, blocked_user_id=request.user.id).exists()
        if initiator_blocked:
            return JsonResponse({"status": "error", "message": "blocked"}, status=403)
        new_challenge = Challenge(
            initiator_name= initiator_name,
            opponent_name= opponent_name
        )
        position = data.get('position')
        if position == "white":
            new_challenge.white_id = request.user.id
            new_challenge.black_id = opponent.id
            new_challenge.initiator_color = "white"
            new_challenge.initiator_choice = "White"
        elif position == "black":
            new_challenge.black_id = request.user.id
            new_challenge.white_id = opponent.id
            new_challenge.initiator_color = "black"
            new_challenge.initiator_choice = "Black"
        elif position == "random":
            column_to_fill = random.choice(["black_id", "white_id"])
            setattr(new_challenge, column_to_fill, request.user.id)
            new_challenge.initiator_color = "white" if column_to_fill == "white_id" else "black"
            opponent_column_to_fill = "white_id" if column_to_fill == "black_id" else "black_id"
            setattr(new_challenge, opponent_column_to_fill, opponent.id)
            new_challenge.initiator_choice = "Random"
        if data.get('main_mode') in ['Decision', 'Classical']:
            if data.get('main_mode') == 'Decision':
                if data.get('reveal_stage') and data.get('decision_stage'):
                    new_challenge.gametype = 'Complete'
                elif data.get('reveal_stage') and not data.get('decision_stage'):
                    new_challenge.gametype = 'Relay'
                elif not data.get('reveal_stage') and data.get('decision_stage'):
                    new_challenge.gametype = 'Countdown'
                else:
                    new_challenge.gametype = 'Standard'
            else:
                new_challenge.gametype = data.get('main_mode')
        else:
            return JsonResponse({"status": "error", "message": "Unauthorized"}, status=401)
        if (data.get('subvariant') in ["Normal", "Classical", "Rapid", "Blitz"] and new_challenge.gametype == "Standard") or\
            (data.get('subvariant') in ["Normal", "Suggestive"] and new_challenge.gametype in ["Complete", "Relay", "Countdown"]):
            new_challenge.subvariant = data.get('subvariant') if data.get('subvariant') != "Normal" else "Simple"
        else:
            return JsonResponse({"status": "error", "message": "Unauthorized"}, status=401)
        print(request.get_host())
        challenge_message = Message(
            sender = request.user,
            recipient = User.objects.get(username=opponent_name),
            subject = "Challenged by " + initiator_name + " to a " + new_challenge.gametype + " " + new_challenge.subvariant + " game.",
            body = f"Click the following link to enter the challenge lobby room. <br><br><a class='challenge-link' href='{'/challenge/'+str(new_challenge.challenge_id)}'>Challenge</a>"
        )
        challenge_message.save()
        new_challenge.save()

        return JsonResponse({'redirect': True, 'url': reverse('challenge', args=[str(new_challenge.challenge_id)]), "message": "Challenge sent"}, status=200)
    elif request.method == "PUT":
        data = json.loads(request.body)

        challenge_id = data.get('challenge_id')
        accepted = data.get('accepted')
        if accepted not in [True, False] or challenge_id is None:
            return JsonResponse({"status": "error", "message": "Bad Request"}, status=400)
        try:
            challenge = Challenge.objects.get(challenge_id=challenge_id)
        except Challenge.DoesNotExist:
            return JsonResponse({"status": "error", "message": "Bad Request"}, status=400)
        if request.user.username != challenge.opponent_name or \
           challenge.challenge_accepted is not None:
            return JsonResponse({"status": "error", "message": "Bad Request"}, status=400)
        challenge.challenge_accepted = accepted
        json_message = {"accepted": accepted}
        if accepted:
            new_lobby = ChessLobby(
                white_id = challenge.white_id,
                black_id = challenge.black_id,
                initiator_name = challenge.initiator_name,
                opponent_name = challenge.opponent_name,
                timestamp = challenge.timestamp,
                is_open = False,
                initiator_color = challenge.initiator_color,
                gametype = challenge.gametype,
                subvariant = challenge.subvariant
            )
            new_lobby.save()
            challenge.game_id = new_lobby.lobby_id
            json_message.update({'redirect': True, 'url': reverse('join_new_game', args=[str(new_lobby.lobby_id)])})
        challenge.save()
        return JsonResponse(json_message, status=200)

@login_required
def block(request):
    if request.method in ['POST', 'PUT']:
        data = json.loads(request.body)
        username = data.get('username')
        if username == request.user.username:
            return JsonResponse({"status": "error", "message": "Bad Request"}, status=400)
        try:
            blocked_user = User.objects.get(username=username)
        except User.DoesNotExist:
            return JsonResponse({"status": "error", "message": "Bad Request"}, status=400)
        already_blocked = Blocks.objects.filter(blocked_user_id=blocked_user.id).exists()
        if already_blocked:
            unblock = data.get('unblock')
            if unblock:
                try:
                    block = Blocks.objects.get(blocked_user_id=blocked_user.id)
                    block.delete()
                    return JsonResponse({"status": "updated"}, status=200)
                except:
                    return JsonResponse({"status": "error", "message": "Internal Server error"}, status=500)
            return JsonResponse({"status": "error", "message": "Bad Request"}, status=400)
        block = Blocks(
            user = request.user,
            blocked_user_id = blocked_user.id
        )
        block.save()
        return JsonResponse({"status": "updated"}, status=200)
    return JsonResponse({"status": "error", "message": "Not Allowed"}, status=405)

@login_required
@require_GET
def existing_blocks(request):
    blocked_user_ids = list(Blocks.objects.filter(user=request.user).values_list('blocked_user_id', flat=True))
    blocked_usernames = []
    if len(blocked_user_ids) != 0:
        blocked_usernames = list(User.objects.filter(id__in=blocked_user_ids).values_list('username', flat=True))
    return JsonResponse({'blocked': blocked_usernames}, safe=False, status=200)

@login_required
@require_GET
def is_blocked(request):
    try:
        user = User.objects.get(username=request.GET.get('username'))
    except User.DoesNotExist:
        return JsonResponse({"status": "error", "message": "Not Found"}, status=404)
    return JsonResponse({'is_blocked': Blocks.objects.filter(user=request.user, blocked_user_id=user.id).exists()}, status=200)

@login_required
def notifications(request):
    request.user.notifications.filter(
        is_seen=True,
        created_at__lt=timezone.now() - timedelta(days=1)
    ).delete()
    notifications = request.user.notifications.order_by('-created_at')
    notifications_data = [
        {
            'notification_id': str(notification.notification_id),
            'message_id': notification.message.message_id,
            'subject': notification.message.subject,
            'created_at': notification.created_at.isoformat(),
            'sender_username': notification.message.sender.username,
            'is_seen': notification.is_seen
        } for notification in notifications
    ]
    return JsonResponse({'notifications': notifications_data}, status=200)

@login_required
def update_notifications(request):
    if request.method == 'PUT':
        data = json.loads(request.body)

        notification_ids = data.get('notification_ids', [])
        notifications = Notification.objects.filter(notification_id__in=notification_ids)
        for notification in notifications:
            notification.is_seen = True
            notification.save()
        return JsonResponse({"message": "updated"}, status=200)
    else:
        return JsonResponse({"status": "error", "message": "Method Not Allowed"}, status=405)

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