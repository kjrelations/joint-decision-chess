import pygame
import sys
import json
import asyncio
import pygbag.aio as asyncio
import fetch
import pygbag_net
import builtins
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

def initialize_game(init, drawing_settings):
    current_theme.INVERSE_PLAYER_VIEW = not init["starting_player"]
    if init["starting_player"]:
        pygame.display.set_caption("Chess - White")
    else:
        pygame.display.set_caption("Chess - Black")
    if init["starting_position"] is None:
        client_game = Game(new_board.copy(), init["starting_player"], init["game_type"])
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
    return client_game

class Node(pygbag_net.Node):
    ...

# Main loop
async def main():
    game_id = os.environ.get('current_game_id') if not local_debug else '222'
    if game_id is None:
        raise Exception("No game id set")
    
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
        "state": {'board': [], 'active_moves': []},
        "new_state": {'board': [], 'active_moves': []}
    }

    # Main game loop
    while init["running"]:

        try:
            if not init["final_updates"]:
                await handle_node_events(node, init, client_game, drawing_settings)
        except Exception as e:
            log_err_and_print(e, window)
            raise Exception(str(e))

        if init["initializing"]:
            client_game = initialize_game(init, drawing_settings)

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
                        retrieved_state = await asyncio.wait_for(get_or_update_game(window, game_id, access_keys), timeout = 5)
                        retrieved = True
                    except Exception as e:
                        err = 'Game State retreival Failed. Reattempting...'
                        js_code = f"console.log('{err}')"
                        window.eval(js_code)
                        print(err)
            
            current_theme.INVERSE_PLAYER_VIEW = not init["starting_player"]
            pygame.display.set_caption("Chess - Waiting on Connection")
            if retrieved_state is None:
                client_game = Game(new_board.copy(), init["starting_player"])
                init["loaded"] = True
            else:
                init["starting_position"] = json.loads(retrieved_state)
                init["starting_position"]["_starting_player"] = True
                client_game = Game(custom_params=init["starting_position"])
                init["initializing"] = True
                init["loaded"] = True
                continue

        if not init["reloaded"] and not init["reconnecting"]:
            if init["retrieved"] is None:
                asyncio.create_task(reconnect(window, game_id, access_keys, init))
            else:
                client_game = init["retrieved"]
                if not node.offline:
                    init["retrieved"] = None
                    init["reloaded"] = True

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
        if drawing_settings['new_state'] != drawing_settings['state']:
            set_check_or_checkmate_settings(drawing_settings, client_game)

        game_window.fill((0, 0, 0))

        draw_board_params = {
            'window': game_window,
            'theme': current_theme,
            'board': client_game.board,
            'starting_player': client_game._starting_player,
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

        if client_game.end_position and client_game._latest:
            # Clear any selected highlights
            drawing_settings["right_clicked_squares"] = []
            drawing_settings["opposing_right_clicked_squares"] = []
            drawing_settings["drawn_arrows"] = []
            drawing_settings["opposing_drawn_arrows"] = []
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    init["running"] = False

            game_window.fill((0, 0, 0))

            draw_board({
                'window': game_window,
                'theme': current_theme,
                'board': client_game.board,
                'starting_player': client_game._starting_player,
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

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        log_err_and_print(e, window)