import pygame
import sys
import json
import asyncio
import pygbag
import pygbag.aio as asyncio
import fetch
from game import *
from constants import *
from helpers import *

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
        pieces[piece_key], transparent_pieces[piece_key] = load_piece_image(image_name_key, current_theme.GRID_SIZE)

outlines = king_outlines(transparent_pieces['k'])

debug_prints = True

def handle_new_piece_selection(game, row, col, is_white, hovered_square):
    piece = game.board[row][col]
    # Initialize variables based on turn
    if game.current_turn == is_white or game._debug:
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

def handle_piece_move(game, selected_piece, row, col, valid_captures):
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
    if not is_check(temp_board, is_white):
        game.update_state(row, col, selected_piece)
        if piece.lower() != 'p' or (piece.lower() == 'p' and (row != 7 and row != 0)):
            print_d("ALG_MOVES:", game.alg_moves, debug=debug_prints)
        
        if (row, col) in valid_captures:
            capture_sound.play()
        else:
            move_sound.play()
        
        selected_piece = None

        checkmate, remaining_moves = is_checkmate_or_stalemate(game.board, not is_white, game.moves)
        if checkmate:
            print("CHECKMATE")
            game.end_position = True
            game.add_end_game_notation(checkmate)
            return None, promotion_required
        elif remaining_moves == 0:
            print("STALEMATE")
            game.end_position = True
            game.add_end_game_notation(checkmate)
            return None, promotion_required
        elif game.threefold_check():
            print("STALEMATE BY THREEFOLD REPETITION")
            game.forced_end = "Stalemate by Threefold Repetition"
            game.end_position = True
            game.add_end_game_notation(checkmate)
            return None, promotion_required

    # Pawn Promotion
    if game.board[row][col].lower() == 'p' and (row == 0 or row == 7):
        promotion_required = True
        promotion_square = (row, col)

    return promotion_square, promotion_required

def handle_piece_special_move(game, selected_piece, row, col):
    # Need to be considering the selected piece for this section not an old piece
    piece = game.board[selected_piece[0]][selected_piece[1]]
    is_white = piece.isupper()

    # Castling and Enpassant moves are already validated, we simply update state
    game.update_state(row, col, selected_piece, special=True)
    print_d("ALG_MOVES:", game.alg_moves, debug=debug_prints)
    if (row, col) in [(7, 2), (7, 6), (0, 2), (0, 6)]:
        move_sound.play()
    else:
        capture_sound.play()

    checkmate, remaining_moves = is_checkmate_or_stalemate(game.board, not is_white, game.moves)
    if checkmate:
        print("CHECKMATE")
        game.end_position = True
        game.add_end_game_notation(checkmate)
        return piece, is_white
    elif remaining_moves == 0:
        print("STALEMATE")
        game.end_position = True
        game.add_end_game_notation(checkmate)
        return piece, is_white
    elif game.threefold_check():
        print("STALEMATE BY THREEFOLD REPETITION")
        game.forced_end = "Stalemate by Threefold Repetition"
        game.end_position = True
        game.add_end_game_notation(checkmate)
        return piece, is_white

    return piece, is_white

def handle_command(status_names, client_state_actions, web_metadata_dict, games_metadata_name, game_tab_id):
    command_name, client_action_name, client_executed_name, *remaining = status_names
    if len(status_names) == 3:
        client_reset_name = None 
    else:
        client_reset_name = remaining[0]
    client_executed_status, client_reset_status = \
        client_state_actions[client_executed_name], client_state_actions.get(client_reset_name)
    
    status_metadata_dict = web_metadata_dict[game_tab_id]
    if status_metadata_dict.get(command_name) is not None:
        if status_metadata_dict[command_name]['execute'] and not status_metadata_dict[command_name]['update_executed'] and not client_reset_status:
            if client_state_actions[client_action_name] != True:
                client_state_actions[client_action_name] = True
            if client_executed_status:
                status_metadata_dict[command_name]['update_executed'] = True
                web_metadata_dict[game_tab_id] = status_metadata_dict
                json_metadata = json.dumps(web_metadata_dict)
                
                window.localStorage.setItem(games_metadata_name, json_metadata)
                client_state_actions[client_action_name] = False

        # Handling race conditions assuming speed differences and sychronizing states with this.
        # That is, only once we stop receiving the command, after an execution, do we allow it to be executed again
        if client_executed_status and not status_metadata_dict[command_name]['execute']:
            client_state_actions[client_executed_name] = False    

        if client_reset_status is not None and client_reset_status == True and not status_metadata_dict[command_name]['reset']:
            status_metadata_dict[command_name]['reset'] = True
            status_metadata_dict[command_name]['execute'] = False
            web_metadata_dict[game_tab_id] = status_metadata_dict
            json_metadata = json.dumps(web_metadata_dict)
            
            window.localStorage.setItem(games_metadata_name, json_metadata)
            client_state_actions[client_reset_name] = False
            client_state_actions[client_action_name] = False

# Game State loop for promotion
async def promotion_state(promotion_square, client_game, row, col, draw_board_params, client_state_actions, command_status_names, drawing_settings, game_tab_id, init):
    promotion_buttons = display_promotion_options(current_theme, promotion_square[0], promotion_square[1])
    promoted, promotion_required = False, True
    
    window.sessionStorage.setItem("promoting", "true")

    while promotion_required:

        # Web browser actions/commands are received in previous loop iterations
        # We wish to exit this state after undoing once to go to our recent turn
        if client_state_actions["undo"]:
            client_game.undo_move()
            client_state_actions["undo"] = False
            client_state_actions["undo_executed"] = True
            promotion_required = False
            continue

        if client_state_actions["resign"]:
            client_game.undo_move()
            client_game._move_undone = False
            client_game._sync = True
            client_game.forced_end = "White Resigned" if client_game.current_turn else "Black Resigned"
            print(client_game.forced_end)
            client_game.end_position = True
            client_game.add_end_game_notation(True)
            client_state_actions["resign"] = False
            client_state_actions["resign_executed"] = True
            promotion_required = False
            continue

        if client_state_actions["cycle_theme"]:
            drawing_settings["theme_index"] += 1
            drawing_settings["theme_index"] %= len(themes)
            current_theme.apply_theme(themes[drawing_settings["theme_index"]])
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
                    current_theme.apply_theme(themes[drawing_settings["theme_index"]])
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

            for button in promotion_buttons:
                button.handle_event(event)
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    x, y = pygame.mouse.get_pos()
                    if button.rect.collidepoint(x, y):
                        client_game.promote_to_piece(row, col, button.piece)
                        print_d("ALG_MOVES:", client_game.alg_moves, debug=debug_prints)
                        promotion_required = False
                        promoted = True

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

        web_game_metadata = window.localStorage.getItem("web_game_metadata")

        web_game_metadata_dict = json.loads(web_game_metadata)

        # TODO Can just put this into an asynchronous loop if I wanted or needed
        # Undo move, resign, draw offer, cycle theme, flip command handle
        for status_names in command_status_names:
            handle_command(status_names, client_state_actions, web_game_metadata_dict, "web_game_metadata", game_tab_id)     

        pygame.display.flip()
        await asyncio.sleep(0)

    window.sessionStorage.setItem("promoting", "false")
    await asyncio.sleep(0)
    return promoted

def initialize_game(init, game_id, drawing_settings):
    current_theme.INVERSE_PLAYER_VIEW = not init["starting_player"]
    if init["starting_player"]:
        pygame.display.set_caption("Chess - White")
    else:
        pygame.display.set_caption("Chess - Black")
    if init["starting_position"] is None:
        client_game = Game(new_board.copy(), init["starting_player"])
        init["sent"] = 1
    else:
        client_game = Game(custom_params=init["starting_position"])
        init["sent"] = int(client_game._starting_player != client_game.current_turn)
    drawing_settings["chessboard"] = generate_chessboard(current_theme)
    drawing_settings["coordinate_surface"] = generate_coordinate_surface(current_theme)
    init["player"] = "white" if init["starting_player"] else "black"
    init["opponent"] = "black" if init["starting_player"] else "white"
    web_game_metadata = window.localStorage.getItem("web_game_metadata")
    if web_game_metadata is not None:
        web_game_metadata_dict = json.loads(web_game_metadata)
    else:
        web_game_metadata_dict = {}
    game_tab_id =  init["player"] + "-" + game_id
    window.sessionStorage.setItem("current_game_id", game_tab_id)
    if isinstance(web_game_metadata_dict, dict) or web_game_metadata is None:
        web_game_metadata_dict[game_tab_id] = {
            "end_state": '',
            "forced_end": '',
            "player_color": init["player"], # Not necessary
            "alg_moves": [],
            "comp_moves": [],
            "FEN_final_pos": "",
            "net_pieces": {'p': 0, 'r': 0, 'n': 0, 'b': 0, 'q': 0},
            "current_turn": client_game.current_turn,
            "step": {
                "execute": False,
                "update_executed": False,
                "index": None
            },
            "undo_move": {
                "execute": False,
                "update_executed": False
            },
            "resign": {
                "execute": False,
                "update_executed": False
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
    window.localStorage.setItem("web_game_metadata", web_game_metadata)
    web_ready = False
    web_game_metadata = window.localStorage.getItem("web_game_metadata")
    if web_game_metadata is not None:
        web_game_metadata_dict = json.loads(web_game_metadata)
        if web_game_metadata_dict.get(game_tab_id) is not None:
            web_ready = True
            init["initializing"], init["initialized"] = False, True
            window.sessionStorage.setItem("initialized", "true")
            window.sessionStorage.setItem("connected", "true")
    if not web_ready:
        raise Exception("Failed to set web value")
    return client_game, game_tab_id

# TODO Move to helpers later on refactor
async def get_or_update_game(game_id, access_keys, client_game = "", post = False):
    if post:
        if isinstance(client_game, str): # could just be not game but we add hinting later
            raise Exception('Wrong POST input')
        client_game._sync = True
        client_game._move_undone = False
        client_game_str = client_game.to_json(include_states=True)
        try:
            url = 'http://127.0.0.1:8000/game-state/' + game_id + '/'
            handler = fetch.RequestHandler()
            secret_key = access_keys["updatekey"] + game_id
            js_code = """
                function generateToken(game_json, secret) {
                    const oPayload = {game: game_json};
                    const oHeader = {alg: 'HS256', typ: 'JWT'};
                    return KJUR.jws.JWS.sign('HS256', JSON.stringify(oHeader), JSON.stringify(oPayload), secret);
                };
                const existingScript = document.querySelector(`script[src='https://cdnjs.cloudflare.com/ajax/libs/jsrsasign/8.0.20/jsrsasign-all-min.js']`);
                if (!existingScript) {
                    const script = document.createElement('script');
                    script.src = 'https://cdnjs.cloudflare.com/ajax/libs/jsrsasign/8.0.20/jsrsasign-all-min.js';
                    script.onload = function() {
                        window.encryptedToken = generateToken('game_string', 'secret_key');
                    };
                    document.head.appendChild(script);
                } else {
                    window.encryptedToken = generateToken('game_string', 'secret_key');
                };
            """.replace("game_string", client_game_str).replace("secret_key", secret_key)
            window.eval(js_code)
            await asyncio.sleep(0)
            while window.encryptedToken is None:
                await asyncio.sleep(0)
            encrytedToken = window.encryptedToken
            window.encryptedToken = None
            csrf = window.sessionStorage.getItem("csrftoken")
            response = await handler.post(url, data = {"token": encrytedToken}, headers = {'X-CSRFToken': csrf})# null token handling
            data = json.loads(response)
            if data.get("status") and data["status"] == "error":
                raise Exception(f'Request failed {data}')
        except Exception as e:
            js_code = f"console.log('{str(e)}')".replace(secret_key, "####")
            window.eval(js_code)
            raise Exception(str(e))
    else:
        try:
            url = 'http://127.0.0.1:8000/game-state/' + game_id + '/'
            handler = fetch.RequestHandler()
            response = await handler.get(url)
            data = json.loads(response)
            if data.get("status") and data["status"] == "error":
                raise Exception('Request failed')
            elif data.get("message") and data["message"] == "DNE":
                return None
            elif data.get("token"):
                response_token = data["token"]
            else:
                raise Exception('Request failed')
            secret_key = access_keys["updatekey"] + game_id
            js_code = """
                function decodeToken(token, secret) {
                    const isValid = KJUR.jws.JWS.verify(token, secret, ['HS256']);
                    if (isValid) {
                        const decoded = KJUR.jws.JWS.parse(token);
                        return JSON.stringify(decoded.payloadObj);
                    } else {
                        return "invalid";
                    };
                };
                const existingScript = document.querySelector(`script[src='https://cdnjs.cloudflare.com/ajax/libs/jsrsasign/8.0.20/jsrsasign-all-min.js']`);
                if (!existingScript) {
                    const script = document.createElement('script');
                    script.src = 'https://cdnjs.cloudflare.com/ajax/libs/jsrsasign/8.0.20/jsrsasign-all-min.js';
                    script.onload = function() {
                        window.payload = decodeToken('response_token', 'secret_key');
                    };
                    document.head.appendChild(script);
                } else {
                    window.payload = decodeToken('response_token', 'secret_key');
                };
            """.replace("response_token", response_token).replace("secret_key", secret_key)
            window.eval(js_code)
            await asyncio.sleep(0)
            while window.payload is None: # Keep trying here
                await asyncio.sleep(0)
            game_payload = window.payload
            window.payload = None
            return game_payload
        except Exception as e:
            js_code = f"console.log('{str(e)}')".replace(secret_key, "####")
            window.eval(js_code)
            raise Exception(str(e))

# TODO Move to helpers later on refactor
def load_keys(file_path):
    keys = {}
    with open(file_path, 'r') as file:
        lines = file.readlines()
        for line in lines:
            parts = line.strip().split('_')
            if len(parts) == 2:
                key, value = parts
                keys[key] = value
    return keys

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
        "starting_player": None,
        "starting_position": None,
        "sent": None,
        "player": None,
        "opponent": None,
        "local_debug": False,
        "retrieved": None,
        "final_updates": False
    }
    client_game = None
    # Web Browser actions affect these only. Even if players try to alter it, 
    # It simply enables the buttons or does a local harmless action
    client_state_actions = {
        "step": False,
        "step_executed": False,
        "undo": False,
        "undo_executed": False,
        "cycle_theme": False,
        "cycle_theme_executed": False,
        "resign": False,
        "resign_executed": False,
        "flip": False,
        "flip_executed": False,
    }
    # This holds the command name for the web localstorage object and the associated keys in the above dictionary
    command_status_names = [
        ("step", "step", "step_executed"),
        ("undo_move", "undo", "undo_executed"),
        ("resign", "resign", "resign_executed"),
        ("cycle_theme", "cycle_theme", "cycle_theme_executed"),
        ("flip_board", "flip", "flip_executed")
    ]

    selected_piece = None
    hovered_square = None
    current_right_clicked_square = None
    end_right_released_square = None
    right_clicked_squares = []
    drawn_arrows = []
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
        "recalc_selections": False,
        "clear_selections": False,
        "king_outlines": outlines,
        "checkmate_white": False,
        "check_white": False,
        "checkmate_black": False,
        "check_black": False
    }

    # Main game loop
    while init["running"]:

        if init["initializing"]:
            client_game, game_tab_id = initialize_game(init, game_id, drawing_settings)

        elif not init["initialized"] :
            if not init["config_retrieved"] and not init["local_debug"]:
                access_keys = load_keys("secrets.txt")
                try:
                    url = 'http://127.0.0.1:8000/config/' + game_id + '/?type=live'
                    handler = fetch.RequestHandler()
                    while not init["config_retrieved"]:
                        try:
                            response = await asyncio.wait_for(handler.get(url), timeout = 5)
                            data = json.loads(response)
                            init["config_retrieved"] = True
                        except:
                            err = 'Game config retreival failed. Reattempting...'
                            js_code = f"console.log('{err}')"
                            window.eval(js_code)
                            print(err)
                    if data.get("status") and data["status"] == "error":
                        raise Exception(f'Request failed {data}')
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
                        current_theme.apply_theme(themes[0])
                    else:
                        raise Exception("Bad request")
                    window.sessionStorage.setItem("color", data["message"]["starting_side"]) # TODO remove on refactor. Not needed for AI games
                except Exception as e:
                    exc_str = str(e).replace("'", "\\x27").replace('"', '\\x22')
                    js_code = f"console.log('{exc_str}')" # TODO escape quotes in other console logs
                    window.eval(js_code)
                    raise Exception(str(e))
            retrieved_state = None
            if init["local_debug"]:
                init["starting_player"] = True
                window.sessionStorage.setItem("color", "white")
            else:
                retrieved = False
                while not retrieved:
                    try:
                        retrieved_state = await asyncio.wait_for(get_or_update_game(game_id, access_keys), timeout = 5)
                        if retrieved_state is not None:
                            init["starting_position"] = json.loads(retrieved_state)
                        retrieved = True
                    except:
                        err = 'Game State retreival Failed. Reattempting...'
                        js_code = f"console.log('{err}')"
                        window.eval(js_code)
                        print(err)
            
            current_theme.INVERSE_PLAYER_VIEW = not init["starting_player"]
            pygame.display.set_caption("Chess - Setting Up")
            window.sessionStorage.setItem("connected", "true")
            init["initializing"] = True
            continue

        # Web browser actions/commands are received in previous loop iterations
        if client_state_actions["step"]:
            drawing_settings["recalc_selections"] = True
            drawing_settings["clear_selections"] = True
            web_game_metadata = window.localStorage.getItem("web_game_metadata")
            web_game_metadata_dict = json.loads(web_game_metadata)
            move_index = web_game_metadata_dict[game_tab_id]["step"]["index"]
            client_game.step_to_move(move_index)
            client_state_actions["step"] = False
            client_state_actions["step_executed"] = True

        if not client_game.end_position:

            if client_state_actions["undo"]:
                if not client_game._latest:
                    client_game.step_to_move(len(client_game.moves) - 1)
                # Undo once on solo play
                client_game.undo_move()
                # These two are useless in single player mode but we keep a clean state anyway
                client_game._sync = True
                client_game._move_undone = False
                hovered_square = None
                selected_piece_image = None
                selected_piece = None
                first_intent = False
                valid_moves, valid_captures, valid_specials = [], [], []
                right_clicked_squares = []
                drawn_arrows = []
                client_state_actions["undo"] = False
                client_state_actions["undo_executed"] = True

            if client_state_actions["resign"]:
                if not client_game._latest:
                    client_game.step_to_move(len(client_game.moves) - 1)
                client_game.forced_end = "White Resigned" if client_game.current_turn else "Black Resigned"
                print(client_game.forced_end)
                client_game.end_position = True
                client_game.add_end_game_notation(True)
                client_state_actions["resign"] = False
                client_state_actions["resign_executed"] = True

        if client_state_actions["cycle_theme"]:
            drawing_settings["theme_index"] += 1
            drawing_settings["theme_index"] %= len(themes)
            current_theme.apply_theme(themes[drawing_settings["theme_index"]])
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
                        right_clicked_squares = []
                        drawn_arrows = []

                        x, y = pygame.mouse.get_pos()
                        row, col = get_board_coordinates(x, y, current_theme.GRID_SIZE)
                        # Change input to reversed board given inverse view
                        if current_theme.INVERSE_PLAYER_VIEW:
                            row, col = map_to_reversed_board(row, col)
                        piece = client_game.board[row][col]
                        is_white = piece.isupper()
                        
                        if not selected_piece:
                            if piece != ' ':
                                # Update states with new piece selection
                                first_intent, selected_piece, selected_piece_image, valid_moves, valid_captures, valid_specials, hovered_square = \
                                    handle_new_piece_selection(client_game, row, col, is_white, hovered_square)
                                
                        else:
                            if client_game._latest:
                                ## Free moves or captures
                                if (row, col) in valid_moves:
                                    promotion_square, promotion_required = \
                                        handle_piece_move(client_game, selected_piece, row, col, valid_captures)
                                    
                                    # Clear valid moves so it doesn't re-enter the loop and potentially replace the square with an empty piece
                                    valid_moves, valid_captures, valid_specials = [], [], []
                                    # Reset selected piece variables to represent state
                                    selected_piece, selected_piece_image = None, None
                                    
                                    init["sent"] = 0
                                    if client_game.end_position:
                                        break
                                
                                ## Specials
                                elif (row, col) in valid_specials:
                                    piece, is_white = handle_piece_special_move(client_game, selected_piece, row, col)
                                    
                                    # Clear valid moves so it doesn't re-enter the loop and potentially replace the square with an empty piece
                                    valid_moves, valid_captures, valid_specials = [], [], []
                                    # Reset selected piece variables to represent state
                                    selected_piece, selected_piece_image = None, None

                                    init["sent"] = 0
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
                        # For the second time a mouseup occurs on the same square it deselects it
                        # This can be an arbitrary number of mousedowns later
                        if not first_intent and (row, col) == selected_piece:
                                selected_piece = None
                                valid_moves, valid_captures, valid_specials = [], [], []
                        
                        # First intent changed to false if mouseup on same square the first time
                        if first_intent and (row, col) == selected_piece:
                            first_intent = not first_intent
                        
                        if client_game._latest:
                            ## Free moves or captures
                            if (row, col) in valid_moves:
                                promotion_square, promotion_required = \
                                    handle_piece_move(client_game, selected_piece, row, col, valid_captures)
                                
                                # Clear valid moves so it doesn't re-enter the loop and potentially replace the square with an empty piece
                                valid_moves, valid_captures, valid_specials = [], [], []
                                # Reset selected piece variables to represent state
                                selected_piece, selected_piece_image = None, None

                                init["sent"] = 0
                                if client_game.end_position:
                                    break

                            ## Specials
                            elif (row, col) in valid_specials:
                                piece, is_white = handle_piece_special_move(client_game, selected_piece, row, col)
                                
                                # Clear valid moves so it doesn't re-enter the loop and potentially replace the square with an empty piece
                                valid_moves, valid_captures, valid_specials = [], [], []
                                # Reset selected piece variables to represent state
                                selected_piece, selected_piece_image = None, None

                                init["sent"] = 0
                                if client_game.end_position:
                                    break

                    if event.button == 3:
                        right_mouse_button_down = False
                        # Highlighting individual squares at will
                        if (row, col) == current_right_clicked_square:
                            if (row, col) not in right_clicked_squares:
                                right_clicked_squares.append((row, col))
                            else:
                                right_clicked_squares.remove((row, col))
                        elif current_right_clicked_square is not None:
                            x, y = pygame.mouse.get_pos()
                            row, col = get_board_coordinates(x, y, current_theme.GRID_SIZE)
                            if current_theme.INVERSE_PLAYER_VIEW:
                                row, col = map_to_reversed_board(row, col)
                            end_right_released_square = (row, col)

                            if [current_right_clicked_square, end_right_released_square] not in drawn_arrows:
                                # Disallow out of bound arrows
                                if 0 <= end_right_released_square[0] < 8 and 0 <= end_right_released_square[1] < 8:
                                    drawn_arrows.append([current_right_clicked_square, end_right_released_square])
                            else:
                                drawn_arrows.remove([current_right_clicked_square, end_right_released_square])
                
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_t:
                        drawing_settings["theme_index"] += 1
                        drawing_settings["theme_index"] %= len(themes)
                        current_theme.apply_theme(themes[drawing_settings["theme_index"]])
                        # Redraw board and coordinates
                        drawing_settings["chessboard"] = generate_chessboard(current_theme)
                        drawing_settings["coordinate_surface"] = generate_coordinate_surface(current_theme)

                    elif event.key == pygame.K_f:
                        current_theme.INVERSE_PLAYER_VIEW = not current_theme.INVERSE_PLAYER_VIEW
                        # Redraw board and coordinates
                        drawing_settings["chessboard"] = generate_chessboard(current_theme)
                        drawing_settings["coordinate_surface"] = generate_coordinate_surface(current_theme)

        set_check_or_checkmate_settings(drawing_settings, client_game)

        game_window.fill((0, 0, 0))

        draw_board_params = {
            'window': game_window,
            'theme': current_theme,
            'board': client_game.board,
            'drawing_settings': drawing_settings,
            'selected_piece': selected_piece,
            'current_position': client_game.current_position,
            'previous_position': client_game.previous_position,
            'right_clicked_squares': right_clicked_squares,
            'drawn_arrows': drawn_arrows,
            'valid_moves': valid_moves,
            'valid_captures': valid_captures,
            'valid_specials': valid_specials,
            'pieces': pieces,
            'hovered_square': hovered_square,
            'selected_piece_image': selected_piece_image
        }

        draw_board(draw_board_params)

        if promotion_required:
            # Lock the game state (disable other input)
            
            # Display an overlay or popup with promotion options
            # We cannot simply reuse the above declaration as it can be mutated by draw_board
            draw_board_params = {
                'window': game_window,
                'theme': current_theme,
                'board': client_game.board,
                'drawing_settings': drawing_settings,
                'selected_piece': selected_piece,
                'current_position': client_game.current_position,
                'previous_position': client_game.previous_position,
                'right_clicked_squares': right_clicked_squares,
                'drawn_arrows': drawn_arrows,
                'valid_moves': valid_moves,
                'valid_captures': valid_captures,
                'valid_specials': valid_specials,
                'pieces': pieces,
                'hovered_square': hovered_square,
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
                drawing_settings, 
                game_tab_id,
                init
            )
            promotion_required, promotion_square = False, None

            if promoted:
                hovered_square = None
                selected_piece_image = None
                selected_piece = None
                first_intent = False
                valid_moves, valid_captures, valid_specials = [], [], []
                right_clicked_squares = []
                drawn_arrows = []

            set_check_or_checkmate_settings(drawing_settings, client_game)

            # Remove the overlay and buttons by redrawing the board
            game_window.fill((0, 0, 0))
            # We likely need to reinput the arguments and can't use the above params as they are updated.
            draw_board({
                'window': game_window,
                'theme': current_theme,
                'board': client_game.board,
                'drawing_settings': drawing_settings,
                'selected_piece': selected_piece,
                'current_position': client_game.current_position,
                'previous_position': client_game.previous_position,
                'right_clicked_squares': right_clicked_squares,
                'drawn_arrows': drawn_arrows,
                'valid_moves': valid_moves,
                'valid_captures': valid_captures,
                'valid_specials': valid_specials,
                'pieces': pieces,
                'hovered_square': hovered_square,
                'selected_piece_image': selected_piece_image
            })
            # On MOUSEDOWN, piece could become whatever was there before and have the wrong color
            # We need to set the piece to be the pawn/new_piece to confirm checkmate immediately 
            # In the case of an undo this is fine and checkmate is always false
            piece = client_game.board[row][col]
            is_white = piece.isupper()

            checkmate, remaining_moves = is_checkmate_or_stalemate(client_game.board, not is_white, client_game.moves)
            if checkmate:
                print("CHECKMATE")
                client_game.end_position = True
                client_game.add_end_game_notation(checkmate)
            elif remaining_moves == 0:
                print("STALEMATE")
                client_game.end_position = True
                client_game.add_end_game_notation(checkmate)
            # This seems redundant as promotions should lead to unique boards but we leave it in anyway
            elif client_game.threefold_check():
                print("STALEMATE BY THREEFOLD REPETITION")
                client_game.forced_end = "Stalemate by Threefold Repetition"
                client_game.end_position = True
                client_game.add_end_game_notation(checkmate)
        
        # Only allow for retrieval of algebraic notation at this point after potential promotion, if necessary in the future
        web_game_metadata = window.localStorage.getItem("web_game_metadata")

        web_game_metadata_dict = json.loads(web_game_metadata)
        
        # TODO Can just put this into an asynchronous loop if I wanted or needed, can also speed up by only executing when there are true values
        # Undo move, resign, draw offer, cycle theme, flip command handle
        for status_names in command_status_names:
            handle_command(status_names, client_state_actions, web_game_metadata_dict, "web_game_metadata", game_tab_id)        

        if web_game_metadata_dict[game_tab_id]['current_turn'] != client_game.current_turn:
            web_game_metadata_dict[game_tab_id]['current_turn'] = client_game.current_turn

            web_game_metadata = json.dumps(web_game_metadata_dict)
            window.localStorage.setItem("web_game_metadata", web_game_metadata)

        net_pieces = net_board(client_game.board)

        if web_game_metadata_dict[game_tab_id]['net_pieces'] != net_pieces:
            web_game_metadata_dict[game_tab_id]['net_pieces'] = net_pieces

            web_game_metadata = json.dumps(web_game_metadata_dict)
            window.localStorage.setItem("web_game_metadata", web_game_metadata)

        if web_game_metadata_dict[game_tab_id]['alg_moves'] != client_game.alg_moves and not client_game.end_position:
            web_game_metadata_dict[game_tab_id]['alg_moves'] = client_game.alg_moves
            # Maybe a simple range list of the index or move number
            web_game_metadata_dict[game_tab_id]['comp_moves'] = [','.join(move) for move in client_game.moves]

            web_game_metadata = json.dumps(web_game_metadata_dict)
            window.localStorage.setItem("web_game_metadata", web_game_metadata)
        
        # Maybe I just set this in a better/DRY way?
        # The following just sets web information so that we know the playing player side, it might be useless? Can't remember why I implemented this
        if client_game._starting_player and web_game_metadata_dict[game_tab_id]['player_color'] != 'white':
            web_game_metadata_dict[game_tab_id]['player_color'] = 'white'

            web_game_metadata = json.dumps(web_game_metadata_dict)
            window.localStorage.setItem("web_game_metadata", web_game_metadata)
        elif not client_game._starting_player and web_game_metadata_dict[game_tab_id]['player_color'] != 'black':
            web_game_metadata_dict[game_tab_id]['player_color'] = 'black'

            web_game_metadata = json.dumps(web_game_metadata_dict)
            window.localStorage.setItem("web_game_metadata", web_game_metadata)

        if client_game.end_position and client_game._latest:
            # Clear any selected highlights
            right_clicked_squares = []
            drawn_arrows = []
            
            game_window.fill((0, 0, 0))

            draw_board({
                'window': game_window,
                'theme': current_theme,
                'board': client_game.board,
                'drawing_settings': drawing_settings,
                'selected_piece': selected_piece,
                'current_position': client_game.current_position,
                'previous_position': client_game.previous_position,
                'right_clicked_squares': right_clicked_squares,
                'drawn_arrows': drawn_arrows,
                'valid_moves': valid_moves,
                'valid_captures': valid_captures,
                'valid_specials': valid_specials,
                'pieces': pieces,
                'hovered_square': hovered_square,
                'selected_piece_image': selected_piece_image
            })

            overlay = pygame.Surface((current_theme.WIDTH, current_theme.HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 128))

            game_window.blit(overlay, (0, 0))

        pygame.display.flip()
        await asyncio.sleep(0)

        try:
            if not init["sent"] and not init["final_updates"]:
                if not init["local_debug"]:
                    await asyncio.wait_for(get_or_update_game(game_id, access_keys, client_game, post = True), timeout = 5)
                init["sent"] = 1
        except:
            init["sent"] = 1
            err = 'Could not send game...'
            js_code = f"console.log('{err}')"
            window.eval(js_code)
            print(err)
            continue

        if client_game.end_position and not init["final_updates"]:
            web_game_metadata = window.localStorage.getItem("web_game_metadata")

            web_game_metadata_dict = json.loads(web_game_metadata)

            if web_game_metadata_dict[game_tab_id]['end_state'] != client_game.alg_moves[-1]:
                web_game_metadata_dict[game_tab_id]['end_state'] = client_game.alg_moves[-1]
                web_game_metadata_dict[game_tab_id]['forced_end'] = client_game.forced_end
                web_game_metadata_dict[game_tab_id]['alg_moves'] = client_game.alg_moves
                web_game_metadata_dict[game_tab_id]['comp_moves'] = client_game.moves
                web_game_metadata_dict[game_tab_id]['FEN_final_pos'] = client_game.translate_into_FEN()
                web_game_metadata_dict[game_tab_id]['net_pieces'] = net_pieces

                web_game_metadata = json.dumps(web_game_metadata_dict)
                window.localStorage.setItem("web_game_metadata", web_game_metadata)

            init["final_updates"] = True

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        js_code = f"console.log('{str(e)}')"
        window.eval(js_code)