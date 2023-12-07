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

def handle_new_piece_selection(game, row, col, is_white, hovered_square):
    piece = game.board[row][col]
    # Initialize variables based on turn
    if game.current_turn == is_white or game._debug:
        first_intent = True
        selected_piece = (row, col)
        selected_piece_image = transparent_pieces[piece]
        valid_moves, valid_captures, valid_specials = calculate_moves(game.board, row, col, game.moves, game.castle_attributes)
    else:
        first_intent = False
        selected_piece = None
        selected_piece_image = None
        valid_moves, valid_captures, valid_specials = [], [], []

    # Remove invalid moves that place the king under check
    for move in valid_moves.copy():
        # Before making the move, create a copy of the board where the piece has moved
        temp_board = [rank[:] for rank in game.board]  
        temp_moves = game.moves.copy()
        temp_moves.append(output_move(piece, selected_piece, move[0], move[1], temp_board[move[0]][move[1]]))
        temp_board[move[0]][move[1]] = temp_board[selected_piece[0]][selected_piece[1]]
        temp_board[selected_piece[0]][selected_piece[1]] = ' '
        
        # Temporary invalid move check, Useful for my variant later
        if is_invalid_capture(temp_board, not is_white):
            valid_moves.remove(move)
            if move in valid_captures:
                valid_captures.remove(move)
        elif is_check(temp_board, is_white, temp_moves):
            valid_moves.remove(move)
            if move in valid_captures:
                valid_captures.remove(move)
    
    for move in valid_specials.copy():
        # Castling moves are already validated in calculate moves, this is only for enpassant
        if (move[0], move[1]) not in [(7, 2), (7, 6), (0, 2), (0, 6)]:
            temp_board = [rank[:] for rank in game.board]  
            temp_moves = game.moves.copy()
            temp_moves.append(output_move(piece, selected_piece, move[0], move[1], temp_board[move[0]][move[1]], 'enpassant'))
            temp_board[move[0]][move[1]] = temp_board[selected_piece[0]][selected_piece[1]]
            temp_board[selected_piece[0]][selected_piece[1]] = ' '
            capture_row = 4 if move[0] == 3 else 5
            temp_board[capture_row][move[1]] = ' '
            if is_check(temp_board, is_white, temp_moves):
                valid_specials.remove(move)
    
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
    temp_moves = game.moves.copy()
    temp_moves.append(output_move(piece, selected_piece, row, col, temp_board[row][col]))
    temp_board[row][col] = temp_board[selected_piece[0]][selected_piece[1]]
    temp_board[selected_piece[0]][selected_piece[1]] = ' '

    # Move the piece if the king does not enter check
    if not is_check(temp_board, is_white, temp_moves):
        game.update_state(row, col, selected_piece)
        if piece.lower() != 'p' or (piece.lower() == 'p' and (row != 7 and row != 0)):
            print("ALG_MOVES:", game.alg_moves)
        
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
    print("ALG_MOVES:", game.alg_moves)
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

def initialize_game(init, game_id, drawing_settings):
    web_game_metadata = window.localStorage.getItem("web_game_metadata")
    if web_game_metadata is not None:
        web_game_metadata_dict = json.loads(web_game_metadata)
        historic_game = web_game_metadata_dict.get(game_id)
        if historic_game is None:
            raise Exception("Failed to retrieve web values")
    else:
        raise Exception("Failed to retrieve web values")

    loaded_params = load_historic_game(historic_game)
    client_game = Game(custom_params=loaded_params)
    current_theme.INVERSE_PLAYER_VIEW = not client_game._starting_player # Later have initial view depend on player who played
    pygame.display.set_caption("Chess - View Game")
    drawing_settings["chessboard"] = generate_chessboard(current_theme)
    drawing_settings["coordinate_surface"] = generate_coordinate_surface(current_theme)

    init["initializing"], init["initialized"] = False, True
    window.sessionStorage.setItem("initialized", "true")
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
        "local_debug": False
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
        "flip_executed": False,
    }
    # This holds the command name for the web localstorage object and the associated keys in the above dictionary
    command_status_names = [
        ("step", "step", "step_executed"),
        ("cycle_theme", "cycle_theme", "cycle_theme_executed"),
        ("flip_board", "flip", "flip_executed")
    ]

    console_log_messages = []

    selected_piece = None
    hovered_square = None
    current_right_clicked_square = None
    end_right_released_square = None
    right_clicked_squares = []
    drawn_arrows = []
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
        "clear_selections": False
    }

    # Main game loop
    while init["running"]:

        if init["initializing"]:
            client_game = initialize_game(init, game_id, drawing_settings)
        
        elif not init["initialized"]:
            if not init["config_retrieved"] and not init["local_debug"]:
                # Eventually access keys and game config setup get, 
                # I could get state here too instead of browser and set browser like normal
                # TODO add Retry loop on disconnect
                try:
                    url = 'http://127.0.0.1:8000/config/' + game_id + '/?type=historic'
                    handler = fetch.RequestHandler()
                    response = await handler.get(url)
                    data = json.loads(response)
                    if data["message"]["theme_names"]:
                        theme_names = data["message"]["theme_names"]
                        global themes
                        themes = [next(theme for theme in themes if theme['name'] == name) for name in theme_names]
                        current_theme.apply_theme(themes[0])
                    else:
                        raise Exception("Bad request")
                except Exception as e:
                    exc_str = str(e).replace("'", "\\x27").replace('"', '\\x22')
                    js_code = f"console.log('{exc_str}')" # TODO escape quotes in other console logs
                    window.eval(js_code)
                    raise Exception(str(e))
            init["initializing"] = True
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

        if client_state_actions["step"]:
            web_game_metadata = window.localStorage.getItem("web_game_metadata")
            web_game_metadata_dict = json.loads(web_game_metadata)
            move_index = web_game_metadata_dict[game_id]["step"]["index"]
            client_game.step_to_move(move_index)
            client_state_actions["step"] = False
            client_state_actions["step_executed"] = True

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

        # An ugly indent but we need to lock on end game
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
                        
                        if (row, col) in valid_moves or (row, col) in valid_specials:
                            # Clear valid moves so it doesn't re-enter the loop and potentially replace the square with an empty piece
                            valid_moves, valid_captures, valid_specials = [], [], []
                            # Reset selected piece variables to represent state
                            selected_piece, selected_piece_image = None, None

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
        
        # Only allow for retrieval of algebraic notation at this point after potential promotion, if necessary in the future
        web_game_metadata = window.localStorage.getItem("web_game_metadata")

        web_game_metadata_dict = json.loads(web_game_metadata)

        # DEV logs to console
        # web_game_metadata_dict[game_tab_id]['console_messages'] = console_log_messages
        
        # TODO Can just put this into an asynchronous loop if I wanted or needed, can also speed up by only executing when there are true values
        # Step, cycle theme, flip command handle
        for status_names in command_status_names:
            handle_command(status_names, client_state_actions, web_game_metadata_dict, "web_game_metadata", game_id)

        pygame.display.flip()
        await asyncio.sleep(0)

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    asyncio.run(main())