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

def handle_command(status_names, client_state_actions, web_metadata_dict, games_metadata_name):
    command_name, client_action_name, client_executed_name, *remaining = status_names
    if len(status_names) == 3:
        client_reset_name = None 
    else:
        client_reset_name = remaining[0]
    client_executed_status, client_reset_status = \
        client_state_actions[client_executed_name], client_state_actions.get(client_reset_name)
    
    if web_metadata_dict.get(command_name) is not None:
        if web_metadata_dict[command_name]['execute'] and not web_metadata_dict[command_name]['update_executed'] and not client_reset_status:
            if client_state_actions[client_action_name] != True:
                client_state_actions[client_action_name] = True
            if client_executed_status:
                web_metadata_dict[command_name]['update_executed'] = True
                web_metadata_dict = web_metadata_dict
                json_metadata = json.dumps(web_metadata_dict)
                
                window.sessionStorage.setItem(games_metadata_name, json_metadata)
                client_state_actions[client_action_name] = False

        # Handling race conditions assuming speed differences and sychronizing states with this.
        # That is, only once we stop receiving the command, after an execution, do we allow it to be executed again
        if client_executed_status and not web_metadata_dict[command_name]['execute']:
            client_state_actions[client_executed_name] = False    

        if client_reset_status is not None and client_reset_status == True and not web_metadata_dict[command_name]['reset']:
            web_metadata_dict[command_name]['reset'] = True
            web_metadata_dict[command_name]['execute'] = False
            json_metadata = json.dumps(web_metadata_dict)
            
            window.sessionStorage.setItem(games_metadata_name, json_metadata)
            client_state_actions[client_reset_name] = False
            client_state_actions[client_action_name] = False

def initialize_game(init, drawing_settings):
    current_theme.INVERSE_PLAYER_VIEW = not init["starting_player"]
    if init["starting_player"]:
        pygame.display.set_caption("Chess - White")
    else:
        pygame.display.set_caption("Chess - Black")
    if init["starting_position"] is None:
        client_game = Game(new_board.copy(), init["starting_player"], init["game_type"], init["subvariant"])
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
    web_game_metadata = window.sessionStorage.getItem("web_game_metadata")
    if web_game_metadata is not None:
        web_game_metadata_dict = json.loads(web_game_metadata)
    else:
        web_game_metadata_dict = {}
    if not init["initialized"]:
        if (isinstance(web_game_metadata_dict, dict) or web_game_metadata is None):
            web_game_metadata_dict = {
                "end_state": '',
                "forced_end": '',
                "alg_moves": [],
                "comp_moves": [],
                "FEN_final_pos": "",
                "net_pieces": {'p': 0, 'r': 0, 'n': 0, 'b': 0, 'q': 0},
                "white_played": False,
                "black_played": False,
                "white_active_move": None,
                "black_active_move": None,
                "playing_stage": True,
                "white_undo": 0,
                "black_undo": 0,
                "decision_stage_enabled": client_game.decision_stage_enabled,
                "game_type": init["game_type"],
                "step": {
                    "execute": False,
                    "update_executed": False,
                    "index": None
                },
                "cycle_theme": {
                    "execute": False,
                    "update_executed": False
                },
                "flip_board": {
                    "execute": False,
                    "update_executed": False
                }
            }
            if client_game.reveal_stage_enabled:
                web_game_metadata_dict.update(
                    {
                        "reveal_stage": client_game.reveal_stage
                    }
                )
            if client_game.decision_stage_enabled:
                web_game_metadata_dict.update(
                    {
                        "decision_stage": client_game.decision_stage,
                        "next_stage": False,
                        "reset_timer": False
                    }
                )
        else:
            raise Exception("Browser game metadata of wrong type", web_game_metadata_dict)
        web_game_metadata = json.dumps(web_game_metadata_dict)
        window.sessionStorage.setItem("web_game_metadata", web_game_metadata)
        web_ready = False
        web_game_metadata = window.sessionStorage.getItem("web_game_metadata")
        if web_game_metadata is not None:
            web_game_metadata_dict = json.loads(web_game_metadata)
            web_ready = True
            init["initializing"], init["initialized"] = False, True
            window.sessionStorage.setItem("initialized", "true")
        if not web_ready:
            raise Exception("Failed to set web value")
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
    return client_game

class Node(pygbag_net.Node):
    ...

# Main loop
async def main():
    game_id = window.sessionStorage.getItem('current_game_id') if not local_debug else '222'
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
        "starting_player": True,
        "game_type": None,
        "subvariant": None,
        "reference_time": None,
        "white_grace_time": None,
        "black_grace_time": None,
        "delay": 0,
        "retrieved_delay": 0,
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

    client_state_actions = {
        "step": False,
        "step_executed": False,
        "cycle_theme": False,
        "cycle_theme_executed": False,
        "flip": False,
        "flip_executed": False
    }

    command_status_names = [
        ("step", "step", "step_executed"),
        ("cycle_theme", "cycle_theme", "cycle_theme_executed"),
        ("flip_board", "flip", "flip_executed")
    ]

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

        try:
            if not init["final_updates"]:
                await handle_node_events(node, window, init, client_game, drawing_settings)
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
                except Exception as e:
                    log_err_and_print(e, window)
                    raise Exception(str(e))
            retrieved_state = None
            if init["local_debug"]:
                init["starting_player"] = True
                window.sessionStorage.setItem("muted", "false")
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

        if client_state_actions["step"]:
            if client_game._sync: # Preventing stepping while syncing required
                web_game_metadata = window.sessionStorage.getItem("web_game_metadata")
                web_game_metadata_dict = json.loads(web_game_metadata)
                move_index = web_game_metadata_dict["step"]["index"]
                client_game.step_to_move(move_index)
                if client_game._move_index == -1:
                    pass
                elif 'x' in client_game.alg_moves[client_game._move_index][0] or 'x' in client_game.alg_moves[client_game._move_index][1]:
                    handle_play(window, capture_sound)
                else:
                    handle_play(window, move_sound)
            client_state_actions["step"] = False
            client_state_actions["step_executed"] = True
            drawing_settings["draw"] = True

        if client_state_actions["cycle_theme"]:
            drawing_settings["theme_index"] += 1
            drawing_settings["theme_index"] %= len(themes)
            current_theme.apply_theme(themes[drawing_settings["theme_index"]], current_theme.INVERSE_PLAYER_VIEW)
            # Redraw board and coordinates
            drawing_settings["chessboard"] = generate_chessboard(current_theme)
            drawing_settings["coordinate_surface"] = generate_coordinate_surface(current_theme)
            client_state_actions["cycle_theme"] = False
            client_state_actions["cycle_theme_executed"] = True
            drawing_settings["draw"] = True

        if client_state_actions["flip"]:
            current_theme.INVERSE_PLAYER_VIEW = not current_theme.INVERSE_PLAYER_VIEW
            # Redraw board and coordinates
            drawing_settings["chessboard"] = generate_chessboard(current_theme)
            drawing_settings["coordinate_surface"] = generate_coordinate_surface(current_theme)
            client_state_actions["flip"] = False
            client_state_actions["flip_executed"] = True
            drawing_settings["draw"] = True

        if not client_game.end_position:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    init["running"] = False
                
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_t:
                        drawing_settings["theme_index"] += 1
                        drawing_settings["theme_index"] %= len(themes)
                        current_theme.apply_theme(themes[drawing_settings["theme_index"]], current_theme.INVERSE_PLAYER_VIEW)
                        # Redraw board and coordinates
                        drawing_settings["chessboard"] = generate_chessboard(current_theme)
                        drawing_settings["coordinate_surface"] = generate_coordinate_surface(current_theme)

                    elif event.key == pygame.K_f:
                        current_theme.INVERSE_PLAYER_VIEW = not current_theme.INVERSE_PLAYER_VIEW
                        # Redraw board and coordinates
                        drawing_settings["chessboard"] = generate_chessboard(current_theme)
                        drawing_settings["coordinate_surface"] = generate_coordinate_surface(current_theme)

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
            web_game_metadata = window.sessionStorage.getItem("web_game_metadata")

            web_game_metadata_dict = json.loads(web_game_metadata)

            net_pieces = net_board(client_game.board)

            if web_game_metadata_dict['end_state'] != client_game.alg_moves[-1]:
                web_game_metadata_dict['end_state'] = client_game.alg_moves[-1]
                web_game_metadata_dict['forced_end'] = client_game.forced_end
                web_game_metadata_dict['alg_moves'] = client_game.alg_moves
                web_game_metadata_dict['comp_moves'] = client_game.moves
                web_game_metadata_dict['FEN_final_pos'] = client_game.translate_into_FEN()
                web_game_metadata_dict['net_pieces'] = net_pieces

                web_game_metadata = json.dumps(web_game_metadata_dict)
                window.sessionStorage.setItem("web_game_metadata", web_game_metadata)
            
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

        if client_game.timed_mode:
            end = time.monotonic()
            if client_game._temp_remaining_white_time is not None:
                white_time = client_game._temp_remaining_white_time
            elif init["white_grace_time"] is not None:
                if end - init["reference_time"] > init["white_grace_time"]:
                    client_game.white_clock_running = True
                    white_time = client_game.remaining_white_time
                    init["white_grace_time"] = None
                    if client_game.black_clock_running:
                        client_game.remaining_black_time = max(client_game.remaining_black_time - (end - init["reference_time"]), 0)
                    init["reference_time"] = time.monotonic()
                else:
                    white_time = client_game.remaining_white_time
            elif client_game.white_clock_running:
                white_time = client_game.remaining_white_time - (end - init["reference_time"])
            else:
                white_time = client_game.remaining_white_time

            if window.sessionStorage.getItem('white_time') != white_time:
                window.sessionStorage.setItem('white_time', white_time)

            end = time.monotonic()
            if client_game._temp_remaining_black_time is not None:
                black_time = client_game._temp_remaining_black_time
            elif init["black_grace_time"] is not None:
                if end - init["reference_time"] > init["black_grace_time"]:
                    client_game.black_clock_running = True
                    black_time = client_game.remaining_black_time
                    init["black_grace_time"] = None
                    if client_game.white_clock_running:
                        client_game.remaining_white_time = max(client_game.remaining_white_time - (end - init["reference_time"]), 0)
                    init["reference_time"] = time.monotonic()
                else:
                    black_time = client_game.remaining_black_time
            elif client_game.black_clock_running:
                black_time = client_game.remaining_black_time - (end - init["reference_time"])
            else:
                black_time = client_game.remaining_black_time
            
            if window.sessionStorage.getItem('black_time') != black_time:
                window.sessionStorage.setItem('black_time', black_time)

        # Only allow for retrieval of algebraic notation at this point after potential promotion, if necessary in the future
        web_game_metadata = window.sessionStorage.getItem("web_game_metadata")

        web_game_metadata_dict = json.loads(web_game_metadata)
        
        # cycle theme, flip command handle
        for status_names in command_status_names:
            handle_command(status_names, client_state_actions, web_game_metadata_dict, "web_game_metadata")        

        net_pieces = net_board(client_game.board)

        metadata_update = False
        if web_game_metadata_dict['net_pieces'] != net_pieces:
            web_game_metadata_dict['net_pieces'] = net_pieces
            metadata_update = True

        if web_game_metadata_dict['white_played'] != client_game.white_played:
            web_game_metadata_dict['white_played'] = client_game.white_played
            metadata_update = True

        if web_game_metadata_dict['black_played'] != client_game.black_played:
            web_game_metadata_dict['black_played'] = client_game.black_played
            metadata_update = True

        if web_game_metadata_dict['alg_moves'] != client_game.alg_moves and not client_game.end_position:
            web_game_metadata_dict['alg_moves'] = client_game.alg_moves
            web_game_metadata_dict['comp_moves'] = client_game.moves
            metadata_update = True

        if not client_game.playing_stage:
            if web_game_metadata_dict['playing_stage'] != False:
                web_game_metadata_dict['playing_stage'] = False
                metadata_update = True
            
            file_conversion = {0: 'a', 1: 'b', 2: 'c', 3: 'd', 4: 'e', 5: 'f', 6: 'g', 7: 'h'}
            rank_conversion = {i: str(8 - i) for i in range(8)}
            if client_game.suggestive_stage_enabled:
                white_move = client_game.white_suggested_move
                black_move = client_game.black_suggested_move
            else:
                white_move = client_game.white_active_move[1]
                black_move = client_game.black_active_move[1]
            web_white_move = file_conversion[white_move[1]] + rank_conversion[white_move[0]]
            web_black_move = file_conversion[black_move[1]] + rank_conversion[black_move[0]]
            if web_game_metadata_dict['white_active_move'] != web_white_move:
                web_game_metadata_dict['white_active_move'] = web_white_move
                metadata_update = True

            if web_game_metadata_dict['black_active_move'] != web_black_move:
                web_game_metadata_dict['black_active_move'] = web_black_move
                metadata_update = True
        else:
            if web_game_metadata_dict['playing_stage'] != True:
                web_game_metadata_dict['playing_stage'] = True
                metadata_update = True

            if web_game_metadata_dict['white_active_move'] != None:
                web_game_metadata_dict['white_active_move'] = None
                metadata_update = True

            if web_game_metadata_dict['black_active_move'] != None:
                web_game_metadata_dict['black_active_move'] = None
                metadata_update = True

        if client_game.reveal_stage_enabled:
            if web_game_metadata_dict['reveal_stage'] != client_game.reveal_stage:
                web_game_metadata_dict['reveal_stage'] = client_game.reveal_stage
                metadata_update = True

        if client_game.decision_stage_enabled:
            if web_game_metadata_dict['decision_stage_enabled'] != client_game.decision_stage_enabled:
                web_game_metadata_dict['decision_stage_enabled'] = client_game.decision_stage_enabled
                metadata_update = True

            if web_game_metadata_dict['decision_stage'] != client_game.decision_stage:
                web_game_metadata_dict['decision_stage'] = client_game.decision_stage
                metadata_update = True
            
            if web_game_metadata_dict['white_undo'] != client_game.white_undo_count:
                web_game_metadata_dict['white_undo'] = client_game.white_undo_count
                metadata_update = True
            
            if web_game_metadata_dict['black_undo'] != client_game.black_undo_count:
                web_game_metadata_dict['black_undo'] = client_game.black_undo_count
                metadata_update = True

            if web_game_metadata_dict["next_stage"]:
                client_game.decision_stage_complete = True
                web_game_metadata_dict["next_stage"] = False
                metadata_update = True
            
        if metadata_update:
            web_game_metadata = json.dumps(web_game_metadata_dict)
            window.sessionStorage.setItem("web_game_metadata", web_game_metadata)

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        log_err_and_print(e, window)