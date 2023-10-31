from django.shortcuts import render, redirect
from django.utils import timezone
from django.contrib import messages
from django.http import JsonResponse
from django.urls import reverse
from .models import ChessLobby
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