import pygame
import sys
import json
import asyncio
import pygbag.aio as asyncio
import fetch
import copy
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

def handle_new_piece_selection(game, row, col, is_white, hovered_square):
    piece = game.board[row][col]
    # Initialize variables
    first_intent = True
    selected_piece = (row, col)
    selected_piece_image = transparent_pieces[piece]
    valid_moves, valid_captures, valid_specials = game.validate_moves(row, col)

    if (row, col) != hovered_square:
        hovered_square = (row, col)
    
    return first_intent, selected_piece, selected_piece_image, valid_moves, valid_captures, valid_specials, hovered_square

def handle_piece_move(game, selected_piece, row, col, init, update_positions=False, allow_promote=True):
    # Initialize Variables
    promotion_square = None
    promotion_required = False
    # Need to be considering the selected piece for this section not an old piece
    piece = game.board[selected_piece[0]][selected_piece[1]]
    is_white = piece.isupper()

    temp_board = [rank[:] for rank in game.board]  
    temp_board[row][col] = temp_board[selected_piece[0]][selected_piece[1]]
    temp_board[selected_piece[0]][selected_piece[1]] = ' '

    # Move the piece if the king does not enter check
    if not (is_check(temp_board, is_white) and \
            not (piece.lower() == 'k' and temp_board[row][col].isupper() == is_white)): # redundant now? Not for premoves
        update, illegal = game.update_state(row, col, selected_piece, update_positions=update_positions)
        if piece.lower() != 'p' or (piece.lower() == 'p' and (row != 7 and row != 0)) and update:
            print_d("ALG_MOVES:", game.alg_moves, debug=debug_prints)
        
        if update and ("x" in game.alg_moves[-1][0] or "x" in game.alg_moves[-1][1]):
            handle_play(window, capture_sound)
        elif update:
            handle_play(window, move_sound)
        elif illegal:
            if game._starting_player and game.black_active_move is not None or \
               not game._starting_player and game.white_active_move is not None:
                handle_play(window, error_sound)
        
        selected_piece = None

        if update:
            checkmate_white, remaining_moves_white = is_checkmate_or_stalemate(game.board, True, game.moves)
            checkmate_black, remaining_moves_black = is_checkmate_or_stalemate(game.board, False, game.moves)
            checkmate = checkmate_white or checkmate_black
            no_remaining_moves = remaining_moves_white == 0 or remaining_moves_black == 0
            if checkmate:
                print("CHECKMATE")
                game.end_position = True
                game.add_end_game_notation(checkmate, checkmate_black, checkmate_white)
                return None, promotion_required
            elif no_remaining_moves:
                print("STALEMATE")
                game.end_position = True
                game.add_end_game_notation(checkmate, checkmate_black, checkmate_white)
                return None, promotion_required
            elif game.threefold_check():
                print("STALEMATE BY THREEFOLD REPETITION")
                game.forced_end = "Stalemate by Threefold Repetition"
                game.end_position = True
                game.add_end_game_notation(checkmate, checkmate_black, checkmate_white)
                return None, promotion_required

    # Pawn Promotion
    if piece.lower() == 'p' and (row == 0 or row == 7) and allow_promote:
        promotion_required = True
        promotion_square = (row, col)

    return promotion_square, promotion_required

def handle_piece_special_move(game, selected_piece, row, col, init, update_positions=False):
    # Need to be considering the selected piece for this section not an old piece
    piece = game.board[selected_piece[0]][selected_piece[1]]
    is_white = piece.isupper()

    # Castling and Enpassant moves are already validated, we simply update state
    update, illegal = game.update_state(row, col, selected_piece, special=True, update_positions=update_positions)
    if update:
        print_d("ALG_MOVES:", game.alg_moves, debug=debug_prints)
    if update and ("x" in game.alg_moves[-1][0] or "x" in game.alg_moves[-1][1]):
        handle_play(window, capture_sound)
    elif update:
        handle_play(window, move_sound)
    elif illegal:
        handle_play(window, error_sound)

    if update:
        checkmate_white, remaining_moves_white = is_checkmate_or_stalemate(game.board, True, game.moves)
        checkmate_black, remaining_moves_black = is_checkmate_or_stalemate(game.board, False, game.moves)
        checkmate = checkmate_white or checkmate_black
        no_remaining_moves = remaining_moves_white == 0 or remaining_moves_black == 0
        if checkmate:
            print("CHECKMATE")
            game.end_position = True
            game.add_end_game_notation(checkmate, checkmate_black, checkmate_white)
            return piece, is_white
        elif no_remaining_moves:
            print("STALEMATE")
            game.end_position = True
            game.add_end_game_notation(checkmate, checkmate_black, checkmate_white)
            return piece, is_white
        elif game.threefold_check():
            print("STALEMATE BY THREEFOLD REPETITION")
            game.forced_end = "Stalemate by Threefold Repetition"
            game.end_position = True
            game.add_end_game_notation(checkmate, checkmate_black, checkmate_white)
            return piece, is_white

    return piece, is_white

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

# Game State loop for promotion
async def promotion_state(
        promotion_square, 
        client_game, 
        row, col, 
        draw_board_params, 
        client_state_actions,
        command_status_names,
        drawing_settings
        ):
    promotion_buttons = display_promotion_options(current_theme, promotion_square[0], promotion_square[1])
    promoted, promotion_required = False, True

    window.sessionStorage.setItem("promoting", "true")

    while promotion_required:

        # Web browser actions/commands are received in previous loop iterations
        if client_state_actions["cycle_theme"]:
            drawing_settings["theme_index"] += 1
            drawing_settings["theme_index"] %= len(themes)
            current_theme.apply_theme(themes[drawing_settings["theme_index"]], current_theme.INVERSE_PLAYER_VIEW)
            drawing_settings["chessboard"] = generate_chessboard(current_theme)
            drawing_settings["coordinate_surface"] = generate_coordinate_surface(current_theme)
            draw_board_params["chessboard"] = drawing_settings["chessboard"]
            draw_board_params["coordinate_surface"] = drawing_settings["coordinate_surface"]
            client_state_actions["cycle_theme"] = False
            client_state_actions["cycle_theme_executed"] = True

        if client_state_actions["flip"]:
            current_theme.INVERSE_PLAYER_VIEW = not current_theme.INVERSE_PLAYER_VIEW
            drawing_settings["chessboard"] = generate_chessboard(current_theme)
            drawing_settings["coordinate_surface"] = generate_coordinate_surface(current_theme)
            draw_board_params["chessboard"] = drawing_settings["chessboard"]
            draw_board_params["coordinate_surface"] = drawing_settings["coordinate_surface"]
            promotion_buttons = display_promotion_options(current_theme, promotion_square[0], promotion_square[1])
            client_state_actions["flip"] = False
            client_state_actions["flip_executed"] = True

        for event in pygame.event.get():
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_t:
                    drawing_settings["theme_index"] += 1
                    drawing_settings["theme_index"] %= len(themes)
                    current_theme.apply_theme(themes[drawing_settings["theme_index"]], current_theme.INVERSE_PLAYER_VIEW)
                    # Redraw board and coordinates
                    drawing_settings["chessboard"] = generate_chessboard(current_theme)
                    drawing_settings["coordinate_surface"] = generate_coordinate_surface(current_theme)
                    draw_board_params["chessboard"] = drawing_settings["chessboard"]
                    draw_board_params["coordinate_surface"] = drawing_settings["coordinate_surface"]

                elif event.key == pygame.K_f:
                    current_theme.INVERSE_PLAYER_VIEW = not current_theme.INVERSE_PLAYER_VIEW
                    # Redraw board and coordinates
                    drawing_settings["chessboard"] = generate_chessboard(current_theme)
                    drawing_settings["coordinate_surface"] = generate_coordinate_surface(current_theme)
                    draw_board_params["chessboard"] = drawing_settings["chessboard"]
                    draw_board_params["coordinate_surface"] = drawing_settings["coordinate_surface"]
                    promotion_buttons = display_promotion_options(current_theme, promotion_square[0], promotion_square[1])

            collided = False
            for button in promotion_buttons:
                button.handle_event(event)
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    x, y = pygame.mouse.get_pos()
                    if button.rect.collidepoint(x, y):
                        update = client_game.promote_to_piece(row, col, button.piece)
                        if update:
                            print_d("ALG_MOVES:", client_game.alg_moves, debug=debug_prints)
                        promotion_required = False
                        promoted = True
                        collided = True

            if event.type == pygame.MOUSEBUTTONDOWN and not collided:
                client_game.undo_move()
                promotion_required = False

        game_window.fill((0, 0, 0))
        
        # Draw the board, we need to copy the params else we keep mutating them with each call for inverse board draws in 
        # the reverse_coordinates helper
        draw_board(draw_board_params.copy())
        
        overlay = pygame.Surface((current_theme.WIDTH, current_theme.HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 128))

        game_window.blit(overlay, (0, 0))

        for button in promotion_buttons:
            img = pieces[button.piece]
            img_x, img_y = button.rect.x, button.rect.y
            if button.is_hovered:
                img = pygame.transform.smoothscale(img, (current_theme.GRID_SIZE * 1.5, current_theme.GRID_SIZE * 1.5))
                img_x, img_y = button.scaled_x, button.scaled_y
            game_window.blit(img, (img_x, img_y))

        web_game_metadata = window.sessionStorage.getItem("web_game_metadata")

        web_game_metadata_dict = json.loads(web_game_metadata)

        # Undo move, resign, cycle theme, flip command handle
        for status_names in command_status_names:
            handle_command(status_names, client_state_actions, web_game_metadata_dict, "web_game_metadata")     

        pygame.display.flip()
        await asyncio.sleep(0)

    window.sessionStorage.setItem("promoting", "false")
    await asyncio.sleep(0)
    return promoted

def initialize_game(init, drawing_settings):
    current_theme.INVERSE_PLAYER_VIEW = not init["starting_player"]
    if init["starting_player"]:
        pygame.display.set_caption("Chess - White")
    else:
        pygame.display.set_caption("Chess - Black")
    if init["board"] is None or init["game_type"] is None:
        raise Exception("No starting position or board or game type")
    else:
        client_game = Game(init["board"], init["starting_player"], init["game_type"])
    drawing_settings["chessboard"] = generate_chessboard(current_theme)
    drawing_settings["coordinate_surface"] = generate_coordinate_surface(current_theme)
    init["player"] = "white" if init["starting_player"] else "black"
    init["opponent"] = "black" if init["starting_player"] else "white"
    web_game_metadata = window.sessionStorage.getItem("web_game_metadata")
    if web_game_metadata is not None:
        web_game_metadata_dict = json.loads(web_game_metadata) # Why do I load if I just set it? Artifact?
    else:
        web_game_metadata_dict = {}

    if not init["initialized"]:
        if (isinstance(web_game_metadata_dict, dict) or web_game_metadata is None):
            web_game_metadata_dict = {
                "end_state": '',
                "forced_end": '',
                "player_color": init["player"],
                "alg_moves": [],
                "comp_moves": [],
                "FEN_final_pos": "",
                "net_pieces": {'p': 0, 'r': 0, 'n': 0, 'b': 0, 'q': 0},
                "white_played": False,
                "black_played": False,
                "playing_stage": True,
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
            web_game_metadata_dict = json.loads(web_game_metadata) # why is it loaded again?
            web_ready = True
            init["initializing"], init["initialized"] = False, True
            window.sessionStorage.setItem("initialized", "true")
        if not web_ready:
            raise Exception("Failed to set web value")
    else:
        init["initializing"] = False
    return client_game

# Main loop
async def main():
    game_id = window.sessionStorage.getItem("current_game_id") if not local_debug else '222'
    if game_id is None:
        raise Exception("No game id set")
    
    init = {
        "running": True,
        "initializing": False,
        "initialized": False,
        "config_retrieved": False,
        "starting_player": None,
        "board": None,
        "indexed_moves": None,
        "moves": None,
        "game_type": "Standard",
        # "starting_position": None,
        "player": None,
        "opponent": None,
        "page": 1,
        "proceed": False,
        "local_debug": local_debug,
        "access_keys": None,
        "final_updates": False
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
    # Locks the game state due to pawn promotion
    promotion_required = False
    promotion_square = None
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
        "wait_screen_drawn": False,
        "recalc_selections": False,
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
        "state": {'board': [], 'active_moves': []},
        "new_state": {'board': [], 'active_moves': []}
    }

    # Main game loop
    while init["running"]:

        if game_id != window.sessionStorage.getItem("current_game_id"):
            init["proceed"] = False
            window.sessionStorage.setItem("proceed", "false")
            init["initialized"] = False
            init["config_retrieved"] = False
            game_id = window.sessionStorage.getItem("current_game_id")

        if init["initializing"]:
            client_game = initialize_game(init, drawing_settings)

        elif not init["initialized"]:
            if not init["config_retrieved"] and not init["local_debug"]:
                access_keys = load_keys("secrets.txt")
                init["access_keys"] = access_keys
                # TODO Consider whether to merge with retreival
                try:
                    domain = 'https://decisionchess.com' if production else local
                    url = f'{domain}/config/' + game_id + '/?type=exercise'
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
                    if data["message"]["indexed_moves"]:
                        init["indexed_moves"] = data["message"]["indexed_moves"]
                        page_keys = sorted(init["indexed_moves"].keys())
                        key = "1" if init["page"] == 1 else page_keys[0]
                        init["moves"] = init["indexed_moves"].get(key, [])
                    else:
                        raise Exception('Bad request, no moves')
                    if data["message"]['FEN']:
                        init["board"] = translate_FEN_into_board(data["message"]['FEN'])
                    if data["message"]["starting_side"] == "white":
                        init["starting_player"] = True 
                    elif data["message"]["starting_side"] == "black":
                        init["starting_player"] = False 
                    else:
                        raise Exception("Bad request")
                    if data["message"]["theme_names"]:
                        theme_names = data["message"]["theme_names"]
                        global themes
                        themes = [next(theme for theme in themes if theme['name'] == name) for name in theme_names]
                        current_theme.apply_theme(themes[0], current_theme.INVERSE_PLAYER_VIEW)
                        drawing_settings["chessboard"] = generate_chessboard(current_theme)
                        drawing_settings["coordinate_surface"] = generate_coordinate_surface(current_theme)
                    else:
                        raise Exception("Bad request")
                    window.sessionStorage.setItem("color", data["message"]["starting_side"])
                    window.sessionStorage.setItem("next_page_loaded", "false")
                except Exception as e:
                    log_err_and_print(e, window)
                    raise Exception(str(e))
            
            current_theme.INVERSE_PLAYER_VIEW = not init["starting_player"]
            pygame.display.set_caption("Chess - Setting Up")
            window.sessionStorage.setItem("connected", "true")
            init["initializing"] = True
            continue
        
        # if window page order (incremented on every next page in this script) > highest index key and move list non empty: play all moves
        keys = sorted([int(x) for x in init["indexed_moves"].keys()])
        if len(keys) != 0 and init["page"] > keys[-1]:
            # Skip playing on pages while moving forward or pages with no moves
            if len(init["moves"]) != 0:
                for key in keys:
                    init["moves"] = init["indexed_moves"][str(key)]
                    turns = copy.deepcopy(init["moves"])
                    for moves in turns:
                        player_move = moves[0] if client_game._starting_player else moves[1]
                        row, col, opponent_piece, special = player_move[0], player_move[1], (player_move[2], player_move[3]), player_move[4]
                        promotion_piece = player_move[5] if len(player_move) == 6 else None
                        
                        client_game.update_state(row, col, opponent_piece, special = special)
                        if promotion_piece:
                            client_game.promote_to_piece(row, col, promotion_piece)

                        opponent_move = moves[1] if client_game._starting_player else moves[0]
                        row, col, opponent_piece, special = opponent_move[0], opponent_move[1], (opponent_move[2], opponent_move[3]), opponent_move[4]
                        promotion_piece = opponent_move[5] if len(opponent_move) == 6 else None
                        
                        client_game.update_state(row, col, opponent_piece, special = special)
                        if promotion_piece:
                            client_game.promote_to_piece(row, col, promotion_piece)
                        del init["moves"][0]
                init["indexed_moves"] = {}
                init["proceed"] = True
                window.sessionStorage.setItem("proceed", "true")
        
        if len(init["moves"]) > 0 and \
           ((client_game._starting_player and client_game.white_active_move is not None) or \
           (not client_game._starting_player and client_game.black_active_move is not None)):
            move = init["moves"][0][1] if client_game._starting_player else init["moves"][0][0]
            row, col, opponent_piece, special = move[0], move[1], (move[2], move[3]), move[4]
            promotion_piece = move[5] if len(move) == 6 else None
            
            client_game.update_state(row, col, opponent_piece, special = special)
            if promotion_piece:
                client_game.promote_to_piece(row, col, promotion_piece)
            if ("x" in client_game.alg_moves[-1][0] or "x" in client_game.alg_moves[-1][1]):
                handle_play(window, capture_sound)
            else:
                handle_play(window, move_sound)
            checkmate_white, remaining_moves_white = is_checkmate_or_stalemate(client_game.board, True, client_game.moves)
            checkmate_black, remaining_moves_black = is_checkmate_or_stalemate(client_game.board, False, client_game.moves)
            checkmate = checkmate_white or checkmate_black
            no_remaining_moves = remaining_moves_white == 0 or remaining_moves_black == 0
            if checkmate:
                print("CHECKMATE")
                client_game.end_position = True
                client_game.add_end_game_notation(checkmate, checkmate_black, checkmate_white)
            elif no_remaining_moves:
                print("STALEMATE")
                client_game.end_position = True
                client_game.add_end_game_notation(checkmate, checkmate_black, checkmate_white)
            elif client_game.threefold_check():
                print("STALEMATE BY THREEFOLD REPETITION")
                client_game.forced_end = "Stalemate by Threefold Repetition"
                client_game.end_position = True
                client_game.add_end_game_notation(checkmate, checkmate_black, checkmate_white)
            del init["moves"][0]
        elif len(init["moves"]) == 0:
            next_page_loaded = window.sessionStorage.getItem('next_page_loaded') == "true"
            if next_page_loaded:
                init["proceed"] = False
                window.sessionStorage.setItem("proceed", "false")
                window.sessionStorage.setItem('next_page_loaded', "false")
                if len(keys) >= 2 and int(window.sessionStorage.getItem("currentPage")) == keys[1]:
                    del init["indexed_moves"][str(keys[0])]
                    init["moves"] = init["indexed_moves"][str(keys[1])]
            elif not init["proceed"]:
                window.sessionStorage.setItem("proceed", "true")
                if int(window.sessionStorage.getItem("currentPage")) == init["page"]:
                    init["page"] += 1
                init["proceed"] = True

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

        # Web browser actions/commands are received in previous loop iterations
        if client_state_actions["step"]:
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

        if client_state_actions["cycle_theme"]:
            drawing_settings["theme_index"] += 1
            drawing_settings["theme_index"] %= len(themes)
            current_theme.apply_theme(themes[drawing_settings["theme_index"]], current_theme.INVERSE_PLAYER_VIEW)
            # Redraw board and coordinates
            drawing_settings["chessboard"] = generate_chessboard(current_theme)
            drawing_settings["coordinate_surface"] = generate_coordinate_surface(current_theme)
            client_state_actions["cycle_theme"] = False
            client_state_actions["cycle_theme_executed"] = True

        if client_state_actions["flip"]:
            current_theme.INVERSE_PLAYER_VIEW = not current_theme.INVERSE_PLAYER_VIEW
            # Redraw board and coordinates
            drawing_settings["chessboard"] = generate_chessboard(current_theme)
            drawing_settings["coordinate_surface"] = generate_coordinate_surface(current_theme)
            client_state_actions["flip"] = False
            client_state_actions["flip_executed"] = True

        # Have this after the step commands to not allow previous selections
        if drawing_settings["recalc_selections"]:
            if selected_piece:
                row, col = selected_piece
                piece = client_game.board[row][col]
                is_white = piece.isupper()
                if piece != ' ' and not drawing_settings["clear_selections"]:
                    first_intent, selected_piece, selected_piece_image, \
                    valid_moves, valid_captures, valid_specials, hovered_square = \
                        handle_new_piece_selection(client_game, row, col, is_white, hovered_square)
                else:
                    first_intent = False
                    selected_piece = None
                    valid_moves, valid_captures, valid_specials = [], [], []
                selected_piece_image = None
            drawing_settings["recalc_selections"] = False
            drawing_settings["clear_selections"] = False

        # An ugly indent but we need to send the draw_offer and resign execution status and skip unnecessary events
        # TODO make this skip cleaner or move it into a function
        if not client_game.end_position:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    init["running"] = False
                elif event.type == pygame.MOUSEBUTTONDOWN:
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
                            # Allow moves only on current turn, if up to date, and synchronized
                            current_turn = (not client_game.white_played and client_game._starting_player) or (not client_game.black_played and not client_game._starting_player)
                            if current_turn and client_game._latest and client_game._sync:
                                ## Free moves or captures
                                if len(init["moves"]) != 0:
                                    move_info = init["moves"][0][0] if client_game._starting_player else init["moves"][0][1]
                                    allowed_move = (move_info[0], move_info[1])
                                    allowed_piece = (move_info[2], move_info[3])
                                else:
                                    allowed_move = None
                                    allowed_piece = None
                                if (row, col) in valid_moves and (row, col) == allowed_move and selected_piece == allowed_piece:
                                    update_positions = False if client_game.reveal_stage_enabled or client_game.decision_stage_enabled else True
                                    promotion_square, promotion_required = \
                                        handle_piece_move(client_game, selected_piece, row, col, init, update_positions=update_positions)
                                    
                                    # Clear valid moves so it doesn't re-enter the loop and potentially replace the square with an empty piece
                                    valid_moves, valid_captures, valid_specials = [], [], []
                                    # Reset selected piece variables to represent state
                                    selected_piece, selected_piece_image = None, None
                                    
                                    if client_game.end_position:
                                        break

                                ## Specials
                                elif (row, col) in valid_specials and (row, col) == allowed_move and selected_piece == allowed_piece:
                                    update_positions = False if client_game.reveal_stage_enabled or client_game.decision_stage_enabled else True
                                    piece, is_white = handle_piece_special_move(client_game, selected_piece, row, col, init, update_positions=update_positions)
                                    
                                    # Clear valid moves so it doesn't re-enter the loop and potentially replace the square with an empty piece
                                    valid_moves, valid_captures, valid_specials = [], [], []
                                    # Reset selected piece variables to represent state
                                    selected_piece, selected_piece_image = None, None

                                    if client_game.end_position:
                                        break

                                else:
                                    # Otherwise we are considering another piece or a re-selected piece
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
                            
                            # Otherwise (when not our move) we are considering another piece or a re-selected piece
                            elif piece != ' ':
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
                        if (row, col) != hovered_square:
                            hovered_square = (row, col)

                elif event.type == pygame.MOUSEBUTTONUP:
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
                        
                        # Allow moves only on current turn, if up to date, and synchronized
                        current_turn = (not client_game.white_played and client_game._starting_player) or (not client_game.black_played and not client_game._starting_player)
                        if current_turn and client_game._latest and client_game._sync:
                            ## Free moves or captures
                            if len(init["moves"]) != 0:
                                move_info = init["moves"][0][0] if client_game._starting_player else init["moves"][0][1]
                                allowed_move = (move_info[0], move_info[1])
                                allowed_piece = (move_info[2], move_info[3])
                            else:
                                allowed_move = None
                                allowed_piece = None
                            if (row, col) in valid_moves and (row, col) == allowed_move and selected_piece == allowed_piece:
                                update_positions = False if client_game.reveal_stage_enabled or client_game.decision_stage_enabled else True
                                promotion_square, promotion_required = \
                                    handle_piece_move(client_game, selected_piece, row, col, init, update_positions=update_positions)
                                
                                # Clear valid moves so it doesn't re-enter the loop and potentially replace the square with an empty piece
                                valid_moves, valid_captures, valid_specials = [], [], []
                                # Reset selected piece variables to represent state
                                selected_piece, selected_piece_image = None, None

                                if client_game.end_position:
                                    break

                            ## Specials
                            elif (row, col) in valid_specials and (row, col) == allowed_move and selected_piece == allowed_piece:
                                update_positions = False if client_game.reveal_stage_enabled or client_game.decision_stage_enabled else True
                                piece, is_white = handle_piece_special_move(client_game, selected_piece, row, col, init, update_positions=update_positions)
                                
                                # Clear valid moves so it doesn't re-enter the loop and potentially replace the square with an empty piece
                                valid_moves, valid_captures, valid_specials = [], [], []
                                # Reset selected piece variables to represent state
                                selected_piece, selected_piece_image = None, None

                                if client_game.end_position:
                                    break

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

                    elif event.key == pygame.K_f:
                        current_theme.INVERSE_PLAYER_VIEW = not current_theme.INVERSE_PLAYER_VIEW
                        # Redraw board and coordinates
                        drawing_settings["chessboard"] = generate_chessboard(current_theme)
                        drawing_settings["coordinate_surface"] = generate_coordinate_surface(current_theme)

        if promotion_required:
            # Lock the game state (disable other input)
            
            # Display an overlay or popup with promotion options
            white_selected_piece_image, black_selected_piece_image = get_transparent_active_piece(client_game, transparent_pieces)
            draw_board_params = {
                'window': game_window,
                'theme': current_theme,
                'board': client_game.board,
                'starting_player': client_game._starting_player,
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

            promoted = await promotion_state(
                promotion_square, 
                client_game, 
                row, 
                col, 
                draw_board_params, # These are mutated on first draw then flipped again
                client_state_actions,
                command_status_names,
                drawing_settings
            )
            promotion_required, promotion_square = False, None

            if promoted:
                hovered_square = None
                selected_piece_image = None
                selected_piece = None
                first_intent = False
                valid_moves, valid_captures, valid_specials = [], [], []
                drawing_settings["right_clicked_squares"] = []
                drawing_settings["drawn_arrows"] = []
            else:
                client_game.playing_stage = True
                client_game.reveal_stage = False
                client_game.decision_stage = False

            set_check_or_checkmate_settings(drawing_settings, client_game)

            # Remove the overlay and buttons by redrawing the board
            game_window.fill((0, 0, 0))
            # We likely need to reinput the arguments and can't use the above params as they are updated.
            # We also need new promotion decisions for selected pieces
            white_selected_piece_image, black_selected_piece_image = get_transparent_active_piece(client_game, transparent_pieces)
            draw_board({
                'window': game_window,
                'theme': current_theme,
                'board': client_game.board,
                'starting_player': client_game._starting_player,
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
            })
            # On MOUSEDOWN, piece could become whatever was there before and have the wrong color
            # We need to set the piece to be the pawn/new_piece to confirm checkmate immediately 
            # In the case of an undo this is fine and checkmate is always false
            piece = client_game.board[row][col]
            is_white = piece.isupper()

            if client_game.white_active_move is None and client_game.black_active_move is None:
                checkmate_white, remaining_moves_white = is_checkmate_or_stalemate(client_game.board, True, client_game.moves)
                checkmate_black, remaining_moves_black = is_checkmate_or_stalemate(client_game.board, False, client_game.moves)
                checkmate = checkmate_white or checkmate_black
                no_remaining_moves = remaining_moves_white == 0 or remaining_moves_black == 0
                if checkmate:
                    print("CHECKMATE")
                    client_game.end_position = True
                    client_game.add_end_game_notation(checkmate, checkmate_black, checkmate_white)
                elif no_remaining_moves:
                    print("STALEMATE")
                    client_game.end_position = True
                    client_game.add_end_game_notation(checkmate, checkmate_black, checkmate_white)
                # This seems redundant as promotions should lead to unique boards but we leave it in anyway
                elif client_game.threefold_check():
                    print("STALEMATE BY THREEFOLD REPETITION")
                    client_game.forced_end = "Stalemate by Threefold Repetition"
                    client_game.end_position = True
                    client_game.add_end_game_notation(checkmate, checkmate_black, checkmate_white)

        drawing_settings['new_state'] = {
            'board': deepcopy_list_of_lists(client_game.board),
            'active_moves': [client_game.white_active_move, client_game.black_active_move]
            }
        if drawing_settings['new_state'] != drawing_settings['state']:
            set_check_or_checkmate_settings(drawing_settings, client_game)

        game_window.fill((0, 0, 0))

        white_selected_piece_image, black_selected_piece_image = get_transparent_active_piece(client_game, transparent_pieces)
        draw_board_params = {
            'window': game_window,
            'theme': current_theme,
            'board': client_game.board,
            'starting_player': client_game._starting_player,
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

        if client_game.end_position and not init["final_updates"]:
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
                'white_active_position': None,
                'black_active_position': None,
                'white_selected_piece_image': None,
                'black_selected_piece_image': None,
                'selected_piece_image': selected_piece_image
            })
        drawing_settings['state'] = {
            'board': deepcopy_list_of_lists(client_game.board),
            'active_moves': [client_game.white_active_move, client_game.black_active_move]
            }

        pygame.display.flip()
        await asyncio.sleep(0)

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
        
        starting_player_color = 'white' if client_game._starting_player else 'black'
        if web_game_metadata_dict['player_color'] != starting_player_color:
            web_game_metadata_dict['player_color'] = starting_player_color
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