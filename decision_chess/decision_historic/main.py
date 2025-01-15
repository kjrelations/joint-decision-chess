import pygame
import sys
import json
import asyncio
import pygbag.aio as asyncio
import fetch
from game import *
from constants import *
from helpers import *
from network import *

production = True
local = "http://127.0.0.1:8000"

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

def handle_new_piece_selection(game, row, col, is_white, hovered_square):
    piece = game.board[row][col]
    # Initialize variables based on player
    if (not game.white_played and is_white) or (not game.black_played and not is_white):
        first_intent = True
        selected_piece = (row, col)
        selected_piece_image = transparent_pieces[piece]
        valid_moves, valid_captures, valid_specials = game.validate_moves(row, col)
    else:
        first_intent = False
        selected_piece = None
        selected_piece_image = None
        valid_moves, valid_captures, valid_specials = [], [], []

    if (row, col) != hovered_square:
        hovered_square = (row, col)
    
    return first_intent, selected_piece, selected_piece_image, valid_moves, valid_captures, valid_specials, hovered_square

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

def initialize_game(init, game_id, drawing_settings):
    web_game_metadata = window.sessionStorage.getItem("web_game_metadata")
    if web_game_metadata is not None:
        web_game_metadata_dict = json.loads(web_game_metadata)
        if web_game_metadata_dict is None:
            raise Exception("Failed to retrieve web values")
    else:
        raise Exception("Failed to retrieve web values")
    
    client_game = Game(custom_params=init["starting_position"])
    initial_flip = window.sessionStorage.getItem('init_flip')
    current_theme.INVERSE_PLAYER_VIEW = True if initial_flip == "true" else False
    pygame.display.set_caption("Chess - View Game")
    drawing_settings["chessboard"] = generate_chessboard(current_theme)
    drawing_settings["coordinate_surface"] = generate_coordinate_surface(current_theme)

    web_game_metadata = window.sessionStorage.getItem("web_game_metadata")
    if web_game_metadata is not None:
        web_game_metadata_dict = json.loads(web_game_metadata)
    else:
        web_game_metadata_dict = {}
    if (isinstance(web_game_metadata_dict, dict) or web_game_metadata is None):
        web_game_metadata_dict = {
            "end_state": '',
            "forced_end": '',
            "alg_moves": [],
            "comp_moves": [],
            "net_pieces": {'p': 0, 'r': 0, 'n': 0, 'b': 0, 'q': 0},
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

    return client_game

# Main loop
async def main():
    game_id = window.sessionStorage.getItem("current_game_id")
    if game_id is None:
        raise Exception("No game id set")
    
    init = {
        "running": True,
        "initializing": False,
        "initialized": False,
        "config_retrieved": False,
        "access_keys": None,
    }
    client_game = None

    # Web Browser actions affect these only. Even if players try to alter it, 
    # It simply enables the buttons or does a local harmless action
    client_state_actions = {
        "step": False,
        "step_executed": False,
        "cycle_theme": False,
        "cycle_theme_executed": False,
        "flip": False,
        "flip_executed": False
    }
    # This holds the command name for the web sessionStorage object and the associated keys in the above dictionary
    command_status_names = [
        ("step", "step", "step_executed"),
        ("cycle_theme", "cycle_theme", "cycle_theme_executed"),
        ("flip_board", "flip", "flip_executed")
    ]

    selected_piece = None
    hovered_square = None
    current_right_clicked_square = None
    end_right_released_square = None
    # Boolean stating the first intention of moving a piece
    first_intent = False
    selected_piece_image = None
    valid_moves = []
    valid_captures = []
    valid_specials = []

    left_mouse_button_down = False
    right_mouse_button_down = False

    drawing_settings = {
        # Only draw these surfaces as needed; once per selection of theme
        "chessboard": generate_chessboard(current_theme),
        "coordinate_surface": generate_coordinate_surface(current_theme),
        "theme_index": 0,
        "clear_selections": False,
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

        if init["initializing"]:
            client_game = initialize_game(init, game_id, drawing_settings)

        elif not init["initialized"]:
            if not init["config_retrieved"]:
                access_keys = load_keys("secrets.txt")
                init["access_keys"] = access_keys
                # TODO Consider whether to merge with retreival
                try:
                    domain = 'https://decisionchess.com' if production else local
                    url = f'{domain}/config/' + game_id + '/?type=historic'
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
                    if data["message"]["theme_names"]:
                        theme_names = data["message"]["theme_names"]
                        global themes
                        themes = [next(theme for theme in themes if theme['name'] == name) for name in theme_names]
                        current_theme.apply_theme(themes[0], current_theme.INVERSE_PLAYER_VIEW)
                        drawing_settings["chessboard"] = generate_chessboard(current_theme)
                        drawing_settings["coordinate_surface"] = generate_coordinate_surface(current_theme)
                    else:
                        raise Exception("Bad request")
                    if data["message"]["game_type"]: # don't think I need any of these
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
            retrieved = False
            while not retrieved:
                try:
                    retrieved_state, _, _ = await asyncio.wait_for(get_or_update_game(window, game_id, access_keys), timeout = 5)
                    retrieved = True
                except Exception as e: # Handle DNE with failure
                    err = 'Game State retreival Failed. Reattempting...'
                    js_code = f"console.log('{str(e)}')"
                    window.eval(js_code)
                    print(err)
            init["starting_position"] = json.loads(retrieved_state)
            init["starting_position"]["_starting_player"] = True
            init["initializing"] = True
            drawing_settings["draw"] = True
            continue

        if drawing_settings["clear_selections"]:
            if selected_piece:
                row, col = selected_piece
                piece = client_game.board[row][col]
                is_white = piece.isupper()
                first_intent, selected_piece, selected_piece_image, \
                valid_moves, valid_captures, valid_specials, hovered_square = \
                    handle_new_piece_selection(client_game, row, col, is_white, hovered_square)
                selected_piece_image = None
            drawing_settings["clear_selections"] = False
            drawing_settings["draw"] = True

        # Web browser actions/commands are received in previous loop iterations
        if client_state_actions["step"]:
            if client_game._sync: # Preventing stepping while syncing required
                drawing_settings["recalc_selections"] = True
                drawing_settings["clear_selections"] = True
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

        # An ugly indent but we need to send the draw_offer and resign execution status and skip unnecessary events
        # TODO make this skip cleaner or move it into a function
        if not client_game.end_position:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    init["running"] = False
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    drawing_settings["draw"] = True
                    if event.button == 1:
                        left_mouse_button_down = True
                    if event.button == 3:
                        right_mouse_button_down = True
                    
                    if right_mouse_button_down:
                        # If a piece is selected, unselect them and do not execute move logic
                        hovered_square = None
                        selected_piece_image = None
                        selected_piece = None
                        first_intent = False
                        valid_moves, valid_captures, valid_specials = [], [], []
                        
                        x, y = pygame.mouse.get_pos()
                        row, col = get_board_coordinates(x, y, current_theme.GRID_SIZE)
                        # Change input to reversed board given inverse view
                        if current_theme.INVERSE_PLAYER_VIEW:
                            row, col = map_to_reversed_board(row, col)
                        if not left_mouse_button_down:
                            current_right_clicked_square = (row, col)
                        continue

                    if left_mouse_button_down:
                        # Clear highlights and arrows
                        drawing_settings["right_clicked_squares"] = []
                        drawing_settings["drawn_arrows"] = []

                        x, y = pygame.mouse.get_pos()
                        row, col = get_board_coordinates(x, y, current_theme.GRID_SIZE)
                        # Change input to reversed board given inverse view
                        if current_theme.INVERSE_PLAYER_VIEW:
                            row, col = map_to_reversed_board(row, col)
                        piece = client_game.board[row][col]
                        is_white = piece.isupper()
                        
                        if client_game.playing_stage and not selected_piece:
                            if piece != ' ':
                                # Update states with new piece selection
                                first_intent, selected_piece, selected_piece_image, valid_moves, valid_captures, valid_specials, hovered_square = \
                                    handle_new_piece_selection(client_game, row, col, is_white, hovered_square)
                                
                        elif client_game.playing_stage:
                            if piece != ' ':
                                if (row, col) == selected_piece:
                                    # If the mouse stays on a square and a piece is clicked a second time 
                                    # this ensures that mouseup on this square deselects the piece
                                    if first_intent:
                                        first_intent = False
                                    # Redraw the transparent dragged piece on subsequent clicks
                                    selected_piece_image = transparent_pieces[piece]
                                
                                if (row, col) != selected_piece:
                                    first_intent, selected_piece, selected_piece_image, valid_moves, valid_captures, valid_specials, hovered_square = \
                                        handle_new_piece_selection(client_game, row, col, is_white, hovered_square)    

                elif event.type == pygame.MOUSEMOTION:
                    x, y = pygame.mouse.get_pos()
                    row, col = get_board_coordinates(x, y, current_theme.GRID_SIZE)
                    if current_theme.INVERSE_PLAYER_VIEW:
                        row, col = map_to_reversed_board(row, col)

                    # Draw new hover with a selected piece and LMB
                    if left_mouse_button_down and selected_piece is not None:  
                        drawing_settings["draw"] = True
                        if (row, col) != hovered_square:
                            hovered_square = (row, col)

                elif event.type == pygame.MOUSEBUTTONUP:
                    drawing_settings["draw"] = True
                    if event.button == 1:
                        left_mouse_button_down = False
                        hovered_square = None
                        selected_piece_image = None
                        if not client_game.playing_stage:
                            continue
                        # For the second time a mouseup occurs on the same square it deselects it
                        # This can be an arbitrary number of mousedowns later
                        if not first_intent and (row, col) == selected_piece:
                                selected_piece = None
                                valid_moves, valid_captures, valid_specials = [], [], []
                        
                        # First intent changed to false if mouseup on same square the first time
                        if first_intent and (row, col) == selected_piece:
                            first_intent = not first_intent
                        
                        if (row, col) in valid_moves or (row, col) in valid_specials:
                            # Clear valid moves so it doesn't re-enter the loop and potentially replace the square with an empty piece
                            valid_moves, valid_captures, valid_specials = [], [], []
                            # Reset selected piece variables to represent state
                            selected_piece, selected_piece_image = None, None

                    if event.button == 3:
                        right_mouse_button_down = False
                        # Highlighting individual squares at will
                        if (row, col) == current_right_clicked_square:
                            if (row, col) not in drawing_settings["right_clicked_squares"]:
                                drawing_settings["right_clicked_squares"].append((row, col))
                            else:
                                drawing_settings["right_clicked_squares"].remove((row, col))
                        elif current_right_clicked_square is not None:
                            x, y = pygame.mouse.get_pos()
                            row, col = get_board_coordinates(x, y, current_theme.GRID_SIZE)
                            if current_theme.INVERSE_PLAYER_VIEW:
                                row, col = map_to_reversed_board(row, col)
                            end_right_released_square = (row, col)

                            if [current_right_clicked_square, end_right_released_square] not in drawing_settings["drawn_arrows"]:
                                # Disallow out of bound arrows
                                if 0 <= end_right_released_square[0] < 8 and 0 <= end_right_released_square[1] < 8:
                                    drawing_settings["drawn_arrows"].append([current_right_clicked_square, end_right_released_square])
                            else:
                                drawing_settings["drawn_arrows"].remove([current_right_clicked_square, end_right_released_square])
                
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_t:
                        drawing_settings["theme_index"] += 1
                        drawing_settings["theme_index"] %= len(themes)
                        current_theme.apply_theme(themes[drawing_settings["theme_index"]], current_theme.INVERSE_PLAYER_VIEW)
                        # Redraw board and coordinates
                        drawing_settings["chessboard"] = generate_chessboard(current_theme)
                        drawing_settings["coordinate_surface"] = generate_coordinate_surface(current_theme)
                        drawing_settings["draw"] = True

                    elif event.key == pygame.K_f:
                        current_theme.INVERSE_PLAYER_VIEW = not current_theme.INVERSE_PLAYER_VIEW
                        # Redraw board and coordinates
                        drawing_settings["chessboard"] = generate_chessboard(current_theme)
                        drawing_settings["coordinate_surface"] = generate_coordinate_surface(current_theme)
                        drawing_settings["draw"] = True

        drawing_settings['new_state'] = {
            'board': deepcopy_list_of_lists(client_game.board),
            'active_moves': [client_game.white_active_move, client_game.black_active_move]
            }
        if drawing_settings['new_state'] != drawing_settings['state'] and drawing_settings["draw"]:
            set_check_or_checkmate_settings(drawing_settings, client_game)

        if drawing_settings["draw"]:
            game_window.fill((0, 0, 0))

            white_selected_piece_image, black_selected_piece_image = get_transparent_active_piece(client_game, transparent_pieces)
            draw_board_params = {
                'window': game_window,
                'theme': current_theme,
                'board': client_game.board,
                'starting_player': client_game._starting_player,
                'suggestive_stage': False,
                'latest': client_game._latest,
                'drawing_settings': drawing_settings.copy(),
                'selected_piece': selected_piece,
                'white_current_position': client_game.white_current_position,
                'white_previous_position': client_game.white_previous_position,
                'black_current_position': client_game.black_current_position,
                'black_previous_position': client_game.black_previous_position,
                'valid_moves': valid_moves,
                'valid_captures': valid_captures,
                'valid_specials': valid_specials,
                'pieces': pieces,
                'hovered_square': hovered_square,
                'white_active_position': client_game.white_active_move[1] if client_game.white_active_move is not None else None,
                'black_active_position': client_game.black_active_move[1] if client_game.black_active_move is not None else None,
                'white_selected_piece_image': white_selected_piece_image,
                'black_selected_piece_image': black_selected_piece_image,
                'selected_piece_image': selected_piece_image
            }

            draw_board(draw_board_params)

        drawing_settings['state'] = {
            'board': deepcopy_list_of_lists(client_game.board),
            'active_moves': [client_game.white_active_move, client_game.black_active_move]
            }

        pygame.display.flip()
        await asyncio.sleep(0)
        drawing_settings["draw"] = False

        # Only allow for retrieval of algebraic notation at this point after potential promotion, if necessary in the future
        web_game_metadata = window.sessionStorage.getItem("web_game_metadata")

        web_game_metadata_dict = json.loads(web_game_metadata)
        
        # Undo move, resign, draw offer, cycle theme, flip command handle
        for status_names in command_status_names:
            handle_command(status_names, client_state_actions, web_game_metadata_dict, "web_game_metadata")        

        net_pieces = net_board(client_game.board)

        metadata_update = False
        if web_game_metadata_dict['net_pieces'] != net_pieces:
            web_game_metadata_dict['net_pieces'] = net_pieces
            metadata_update = True

        if web_game_metadata_dict['alg_moves'] != client_game.alg_moves:
            web_game_metadata_dict['alg_moves'] = client_game.alg_moves
            web_game_metadata_dict['comp_moves'] = client_game.moves
            metadata_update = True
            
        if web_game_metadata_dict['end_state'] != client_game.alg_moves[-1]:
            web_game_metadata_dict['end_state'] = client_game.alg_moves[-1]
            web_game_metadata_dict['forced_end'] = client_game.forced_end
            metadata_update = True
        
        if metadata_update:
            web_game_metadata = json.dumps(web_game_metadata_dict)
            window.sessionStorage.setItem("web_game_metadata", web_game_metadata)

        if client_game.timed_mode:
            if client_game._temp_remaining_white_time is not None:
                white_time = client_game._temp_remaining_white_time
            else:
                white_time = client_game.remaining_white_time
            
            if window.sessionStorage.getItem('white_time') != white_time:
                window.sessionStorage.setItem('white_time', white_time)

            if client_game._temp_remaining_black_time is not None:
                black_time = client_game._temp_remaining_black_time
            else:
                black_time = client_game.remaining_black_time

            if window.sessionStorage.getItem('black_time') != black_time:
                window.sessionStorage.setItem('black_time', black_time)

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        log_err_and_print(e, window)