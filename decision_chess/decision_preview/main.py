import pygame
import sys
import json
import asyncio
import pygbag.aio as asyncio
import fetch
import pygbag_net
import builtins
import time
from datetime import datetime
import os
from game import *
from constants import *
from helpers import *
from network import *

production = False
local = "http://127.0.0.1:8000"
local_debug = False

# Handle Persistent Storage
if __import__("sys").platform == "emscripten":
    from platform import window

# Initialize Pygame
pygame.init()

current_theme = Theme()

with open('themes.json', 'r') as file:
    themes = json.load(file)

# Initialize Pygame window
game_window = pygame.display.set_mode((current_theme.WIDTH, current_theme.HEIGHT))

# Load the chess pieces dynamically
pieces = {}
transparent_pieces = {}
for color in ['w', 'b']:
    for piece_lower in ['r', 'n', 'b', 'q', 'k', 'p']:
        piece_key, image_name_key = name_keys(color, piece_lower)
        # https://commons.wikimedia.org/wiki/Category:SVG_chess_pieces
        pieces[piece_key], transparent_pieces[piece_key] = load_piece_image(image_name_key, current_theme.GRID_SIZE)

outlines = king_outlines(transparent_pieces['k'])

debug_prints = True

def initialize_game(init, drawing_settings, game_key):
    current_theme.INVERSE_PLAYER_VIEW = not init["starting_player"]
    if init["starting_player"]:
        pygame.display.set_caption("Chess - White")
    else:
        pygame.display.set_caption("Chess - Black")
    if init["starting_position"] is None:
        client_game = Game(new_board.copy(), init["starting_player"], init["game_type"], init["subvariant"], init["increment"])
    else:
        client_game = Game(custom_params=init["starting_position"])
    if client_game.reveal_stage_enabled and client_game.decision_stage_enabled:
        init["game_type"] = "Complete"
    elif client_game.reveal_stage_enabled and not client_game.decision_stage_enabled:
        init["game_type"] = "Relay"
    elif not client_game.reveal_stage_enabled and client_game.decision_stage_enabled:
        init["game_type"] = "Countdown"
    else:
        init["game_type"] = "Standard"
    drawing_settings["chessboard"] = generate_chessboard(current_theme)
    drawing_settings["coordinate_surface"] = generate_coordinate_surface(current_theme)
    if not init["initialized"]:
        init["initializing"], init["initialized"] = False, True
    else:
        init["initializing"] = False
    if client_game.timed_mode:
        client_game.white_clock_running = True if not client_game.white_played else False
        client_game.black_clock_running = True if not client_game.black_played else False
        if client_game.white_clock_running:
            client_game.remaining_white_time -= init["delay"]
        if client_game.black_clock_running:
            client_game.remaining_black_time -= init["delay"]
        init["reference_time"] = time.monotonic()
        init["delay"] = 0
    window.sessionStorage.setItem(f'waiting-{game_key}', "false")
    return client_game

class Node(pygbag_net.Node):
    ...

# Main loop
async def main():
    game_key = os.environ.get('key') if not local_debug else '222'
    if game_key is None:
        raise Exception('No iframe key param set')
    else:
        game_id = window.sessionStorage.getItem(game_key)
        if game_id is None:
            raise Exception('No game id set')
    
    builtins.node = Node(gid=game_id, groupname="Decision Chess", offline="offline" in sys.argv)
    node = builtins.node
    init = {
        "game_id": game_id,
        "running": True,
        "loaded": False,
        "initializing": False,
        "initialized": False,
        "config_retrieved": False,
        "starting_player": None,
        "game_type": None,
        "subvariant": None,
        "reference_time": None,
        "white_grace_time": None,
        "black_grace_time": None,
        "delay": 0,
        "retrieved_delay": 0,
        "increment": None,
        "starting_position": None,
        "local_debug": local_debug,
        "access_keys": None,
        "desync": False,
        "reloaded": True,
        "reconnecting": False,
        "retrieved": None,
        "final_updates": False
    }
    client_game = None
    if game_id == "":
        if node.aiosock != None:
            node.quit()
        init["starting_position"] = None
        init["starting_player"] = True 
        init["gametype"] = "Standard"
        init["subvariant"] = "Normal"
        init["increment"] = None
        init["initializing"] = True
        init["config_retrieved"] = True # TODO won't get user themes, handle later
        init["loaded"] = True
        window.sessionStorage.setItem(f'waiting-{game_key}', "true")

    valid_moves = []
    valid_captures = []
    valid_specials = []

    drawing_settings = {
        # Only draw these surfaces as needed; once per selection of theme
        "chessboard": generate_chessboard(current_theme),
        "coordinate_surface": generate_coordinate_surface(current_theme),
        "theme_index": 0,
        "right_clicked_squares": [],
        "drawn_arrows": [],
        "opposing_right_clicked_squares": [],
        "opposing_drawn_arrows": [],
        "king_outlines": outlines,
        "checkmate_white": False,
        "check_white": False,
        "checkmate_black": False,
        "check_black": False,
        "draw": True,
        "state": {'board': [], 'active_moves': []},
        "new_state": {'board': [], 'active_moves': []}
    }

    # Main game loop
    while init["running"]:

        loaded_id = window.sessionStorage.getItem(game_key) if not local_debug else '222'
        if loaded_id is None:
            loaded_id = ""
        if loaded_id != game_id:
            game_id = loaded_id
            init["game_id"] = game_id
            if loaded_id == "":
                if node.aiosock != None:
                    node.quit()
                init["starting_position"] = None
                init["starting_player"] = True 
                init["gametype"] = "Standard"
                init["initializing"] = True
                init["loaded"] = True
                drawing_settings["draw"] = True
                window.sessionStorage.setItem(f'waiting-{game_key}', "true")
            else:
                builtins.node = Node(gid=loaded_id, groupname="Decision Chess", offline="offline" in sys.argv)
                node = builtins.node
                init["loaded"] = False
                window.sessionStorage.setItem(f'waiting-{game_key}', "false")

        try:
            if not init["final_updates"]:
                await handle_node_events(node, init, client_game, drawing_settings)
        except Exception as e:
            log_err_and_print(e, window)
            raise Exception(str(e))

        if init["initializing"]:
            client_game = initialize_game(init, drawing_settings, game_key)

        elif not init["loaded"]:
            if not init["config_retrieved"] and not init["local_debug"]:
                access_keys = load_keys("secrets.txt")
                init["access_keys"] = access_keys
                # TODO Consider whether to merge with retreival
                try:
                    domain = 'https://decisionchess.com' if production else local
                    url = f'{domain}/config/' + game_id + '/?type=spectate'
                    handler = fetch.RequestHandler()
                    while not init["config_retrieved"]:
                        try:
                            response = await asyncio.wait_for(handler.get(url), timeout = 5)
                            data = json.loads(response)
                            init["config_retrieved"] = True
                        except Exception as e:
                            if not isinstance(e, asyncio.TimeoutError):
                                await asyncio.sleep(5)
                            err = 'Game config retreival failed. Reattempting...'
                            js_code = f"console.log('{err}')"
                            window.eval(js_code)
                            print(err)
                    if data.get("status") and data["status"] == "error":
                        raise Exception(f'Request failed {data}')
                    init["starting_player"] = True 
                    if data["message"]["theme_names"]:
                        theme_names = data["message"]["theme_names"]
                        global themes
                        themes = [next(theme for theme in themes if theme['name'] == name) for name in theme_names]
                        current_theme.apply_theme(themes[0], current_theme.INVERSE_PLAYER_VIEW)
                        drawing_settings["chessboard"] = generate_chessboard(current_theme)
                        drawing_settings["coordinate_surface"] = generate_coordinate_surface(current_theme)
                    else:
                        raise Exception("Bad request")
                    if data["message"]["game_type"]:
                        init["game_type"] = data["message"]["game_type"]
                    else:
                        raise Exception("Bad request")
                    if data["message"]["subvariant"]:
                        init["subvariant"] = data["message"]["subvariant"]
                    else:
                        raise Exception("Bad request")
                    if data["message"]["increment"] is not None:
                        init["increment"] = data["message"]["increment"]
                    else:
                        raise Exception("Bad request")
                except Exception as e:
                    log_err_and_print(e, window)
                    raise Exception(str(e))
            retrieved_state = None
            if init["local_debug"]:
                init["starting_player"] = True
            else:
                retrieved = False
                while not retrieved:
                    try:
                        retrieved_state, submitted_time, retrieved_time = await asyncio.wait_for(get_or_update_game(window, game_id, access_keys), timeout = 5)
                        retrieved = True
                    except Exception as e:
                        if not isinstance(e, asyncio.TimeoutError):
                            await asyncio.sleep(5)
                        err = 'Game State retreival Failed. Reattempting...'
                        js_code = f"console.log('{err}')"
                        window.eval(js_code)
                        print(err)
            
            current_theme.INVERSE_PLAYER_VIEW = not init["starting_player"]
            pygame.display.set_caption("Chess - Waiting on Connection")
            if retrieved_state is not None:
                init["starting_position"] = json.loads(retrieved_state)
                init["starting_position"]["_starting_player"] = True
                if init["starting_position"]["timed_mode"] and submitted_time is not None:
                    datetime_delay = retrieved_time - submitted_time
                    delay = datetime_delay.total_seconds()
                    if delay > 30:
                        init["delay"] = delay - 30
                    else:
                        init["delay"] = 0
                        if init["starting_position"]["white_clock_running"]:
                            init["white_grace_time"] = 30
                        if init["starting_position"]["black_clock_running"]:
                            init["black_grace_time"] = 30
            init["initializing"] = True
            init["loaded"] = True
            drawing_settings["draw"] = True
            continue

        if not init["reloaded"] and not init["reconnecting"]:
            if init["retrieved"] is None:
                asyncio.create_task(reconnect(window, game_id, access_keys, init, drawing_settings))
            else:
                init["retrieved"]._starting_player = True
                client_game = init["retrieved"]
                if not node.offline:
                    init["retrieved"] = None
                    init["reloaded"] = True
                    if client_game.timed_mode:
                        if client_game.white_clock_running:
                            client_game.remaining_white_time -= init["retrieved_delay"]
                        if client_game.black_clock_running:
                            client_game.remaining_black_time -= init["retrieved_delay"]
                        init["white_penalty_applied"] = False
                        init["black_penalty_applied"] = False
                        if not client_game.white_clock_running:
                            init["white_grace_time"] = None
                        if not client_game.black_clock_running:
                            init["black_grace_time"] = None
                        init["retrieved_delay"] = 0
                        init["reference_time"] = time.monotonic()
                elif client_game.timed_mode:
                    # Retrieve again as accurate timing delay is crucial for timed modes
                    init["retrieved"] = None
                    await asyncio.sleep(1)

        # An ugly indent but we need to send the draw_offer and resign execution status and skip unnecessary events
        # TODO make this skip cleaner or move it into a function
        if not client_game.end_position:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    init["running"] = False

        drawing_settings['new_state'] = {
            'board': deepcopy_list_of_lists(client_game.board),
            'active_moves': [client_game.white_active_move, client_game.black_active_move]
            }
        if drawing_settings['new_state'] != drawing_settings['state'] and drawing_settings["draw"]:
            set_check_or_checkmate_settings(drawing_settings, client_game)

        if drawing_settings["draw"]:
            game_window.fill((0, 0, 0))

            draw_board_params = {
                'window': game_window,
                'theme': current_theme,
                'board': client_game.board,
                'starting_player': client_game._starting_player,
                'suggestive_stage': False,
                'latest': client_game._latest,
                'drawing_settings': drawing_settings.copy(),
                'selected_piece': None,
                'white_current_position': client_game.white_current_position,
                'white_previous_position': client_game.white_previous_position,
                'black_current_position': client_game.black_current_position,
                'black_previous_position': client_game.black_previous_position,
                'valid_moves': valid_moves,
                'valid_captures': valid_captures,
                'valid_specials': valid_specials,
                'pieces': pieces,
                'hovered_square': None,
                'white_active_position': None,
                'black_active_position': None,
                'white_selected_piece_image': None,
                'black_selected_piece_image': None,
                'selected_piece_image': None
            }

            draw_board(draw_board_params)

        if client_game.end_position and not init["final_updates"] and init["reloaded"]:
            node.quit()
            init["final_updates"] = True
            window.sessionStorage.setItem(f'waiting-{game_key}', "true")

        if client_game.end_position and client_game._latest:
            # Clear any selected highlights
            drawing_settings["right_clicked_squares"] = []
            drawing_settings["opposing_right_clicked_squares"] = []
            drawing_settings["drawn_arrows"] = []
            drawing_settings["opposing_drawn_arrows"] = []
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    init["running"] = False

            if drawing_settings["draw"]:
                game_window.fill((0, 0, 0))

                draw_board({
                    'window': game_window,
                    'theme': current_theme,
                    'board': client_game.board,
                    'starting_player': client_game._starting_player,
                    'suggestive_stage': False,
                    'latest': client_game._latest,
                    'drawing_settings': drawing_settings.copy(),
                    'selected_piece': None,
                    'white_current_position': client_game.white_current_position,
                    'white_previous_position': client_game.white_previous_position,
                    'black_current_position': client_game.black_current_position,
                    'black_previous_position': client_game.black_previous_position,
                    'valid_moves': valid_moves,
                    'valid_captures': valid_captures,
                    'valid_specials': valid_specials,
                    'pieces': pieces,
                    'hovered_square': None,
                    'white_active_position': None,
                    'black_active_position': None,
                    'white_selected_piece_image': None,
                    'black_selected_piece_image': None,
                    'selected_piece_image': None
                })
        drawing_settings['state'] = {
            'board': deepcopy_list_of_lists(client_game.board),
            'active_moves': [client_game.white_active_move, client_game.black_active_move]
            }

        pygame.display.flip()
        await asyncio.sleep(0)
        drawing_settings["draw"] = False

        # TODO set times in session
    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        log_err_and_print(e, window)