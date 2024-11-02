import pygame
import sys
import json
import asyncio
import pygbag.aio as asyncio
from game import *
from constants import *
from helpers import *
from network import *
from builder_utils import *

# Handle Persistent Storage
if __import__("sys").platform == "emscripten":
    from platform import window

# Initialize Pygame
pygame.init()

current_theme = Theme()

with open('themes.json', 'r') as file:
    themes = json.load(file)

# Initialize Pygame window
game_window = pygame.display.set_mode((current_theme.WIDTH + current_theme.GRID_SIZE * 2, current_theme.HEIGHT))

# Load the chess pieces dynamically
pieces = {}
transparent_pieces = {}
for color in ['w', 'b']:
    for piece_lower in ['r', 'n', 'b', 'q', 'k', 'p']:
        piece_key, image_name_key = name_keys(color, piece_lower)
        # https://commons.wikimedia.org/wiki/Category:SVG_chess_pieces
        pieces[piece_key], transparent_pieces[piece_key] = load_piece_image(image_name_key, current_theme.GRID_SIZE)

pieces['d'] = pygame.transform.smoothscale(pygame.image.load('images/delete.png'), (current_theme.GRID_SIZE, current_theme.GRID_SIZE))

outlines = king_outlines(transparent_pieces['k'])

debug_prints = True

def handle_new_piece_selection(game, row, col, hovered_square, drawing_settings):
    if col < 8:
        piece = game.board[row][col]
        first_intent = True
        selected_piece = (row, col)
        selected_piece_image = transparent_pieces[piece]
        valid_moves, valid_captures, valid_specials = game.validate_moves(row, col)

        if (row, col) != hovered_square:
            hovered_square = (row, col)
    else:
        side_columns = [
            [' ', ' '],
            [' ', 'd'],
            ['p', 'P'],
            ['n', 'N'],
            ['b', 'B'],
            ['r', 'R'],
            ['q', 'Q'],
            ['k', 'K'],
        ]
        piece = side_columns[row][col - 8]
        if piece != ' ':
            first_intent = True
            selected_piece = (row, col)
            selected_piece_image = transparent_pieces[piece] if piece != 'd' else None
            for key in drawing_settings["side_selection_states"].keys():
                drawing_settings["side_selection_states"][key] = False if key != piece else True
        else:
            first_intent = False
            selected_piece = None
            selected_piece_image = None
            for key in drawing_settings["side_selection_states"].keys():
                drawing_settings["side_selection_states"][key] = False
        valid_moves, valid_captures, valid_specials = [], [], []

        hovered_square = None
    return first_intent, selected_piece, selected_piece_image, valid_moves, valid_captures, valid_specials, hovered_square

def handle_piece_move(game, selected_piece, row, col):
    if col < 8:
        if selected_piece[1] > 7:
            side_columns = [
                [' ', ' '],
                [' ', ' '],
                ['p', 'P'],
                ['n', 'N'],
                ['b', 'B'],
                ['r', 'R'],
                ['q', 'Q'],
                ['k', 'K'],
            ]
            piece = side_columns[selected_piece[0]][selected_piece[1] - 8]
        elif selected_piece[1] < 8:
            piece = game.board[selected_piece[0]][selected_piece[1]]
            game.board[selected_piece[0]][selected_piece[1]] = ' '
        game.board[row][col] = piece
    elif (row, col) == (1, 9) and selected_piece[1] < 8:
        game.board[selected_piece[0]][selected_piece[1]] = ' '

    invalid = False
    white_king_count, black_king_count = 0, 0
    for r in game.board:
        for c in r:
            if c == 'k':
                black_king_count += 1
            elif c == 'K':
                white_king_count += 1
    invalid = white_king_count != 1 or black_king_count != 1
    if invalid:
        return True
    
    checkmate_white, remaining_moves_white = is_checkmate_or_stalemate(game.board, True, game.moves)
    checkmate_black, remaining_moves_black = is_checkmate_or_stalemate(game.board, False, game.moves)
    checkmate = checkmate_white or checkmate_black
    no_remaining_moves = remaining_moves_white == 0 or remaining_moves_black == 0
    if checkmate:
        return True
    elif no_remaining_moves:
        return True
    return False

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
    current_theme.INVERSE_PLAYER_VIEW = False
    pygame.display.set_caption("Chess - Setup")
    client_game = Game(new_board.copy(), True, "Standard")
    drawing_settings["chessboard"] = generate_chessboard(current_theme)
    drawing_settings["coordinate_surface"] = generate_coordinate_surface(current_theme)
    web_game_metadata_dict = {
        "game_over_or_invalid": False,
        "alg_moves": [],
        "comp_moves": [],
        "FEN": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR",
        "cycle_theme": {
            "execute": False,
            "update_executed": False
        },
        "flip_board": {
            "execute": False,
            "update_executed": False
        }
    }
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
    
    init = {
        "running": True,
        "initializing": False,
        "initialized": False,
    }
    client_game = None

    # Web Browser actions affect these only. Even if players try to alter it, 
    # It simply enables the buttons or does a local harmless action
    client_state_actions = {
        "cycle_theme": False,
        "cycle_theme_executed": False,
        "flip": False,
        "flip_executed": False
    }
    # This holds the command name for the web sessionStorage object and the associated keys in the above dictionary
    command_status_names = [
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
    game_over_or_invalid = False
    FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR"

    left_mouse_button_down = False
    right_mouse_button_down = False

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
        "new_state": {'board': [], 'active_moves': []},
        "side_selection_states": {
            'd': False,
            'p': False, 
            'P': False, 
            'n': False, 
            'N': False, 
            'b': False, 
            'B': False, 
            'r': False, 
            'R': False, 
            'q': False, 
            'Q': False, 
            'k': False, 
            'K': False
        }
    }

    # Main game loop
    while init["running"]:

        if init["initializing"]:
            client_game = initialize_game(init, drawing_settings)

        elif not init["initialized"]:
            init["initializing"] = True
            continue

        web_FEN = window.sessionStorage.getItem("FEN")
        if web_FEN is not None and web_FEN != FEN and is_valid_FEN(web_FEN):
            client_game.board = translate_FEN_into_board(web_FEN)
            FEN = web_FEN

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
                        if col < 8:
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

                    side_columns = [
                        [' ', ' '],
                        [' ', 'd'],
                        ['p', 'P'],
                        ['n', 'N'],
                        ['b', 'B'],
                        ['r', 'R'],
                        ['q', 'Q'],
                        ['k', 'K'],
                    ]
                    if col < 8:
                        piece = client_game.board[row][col]
                    else:
                        piece = side_columns[row][col - 8]
                    
                    if client_game.playing_stage and (not selected_piece or (col > 7 and selected_piece != (row, col))):
                        if piece != ' ':
                            # Update states with new piece selection
                            first_intent, selected_piece, selected_piece_image, valid_moves, valid_captures, valid_specials, hovered_square = \
                                handle_new_piece_selection(client_game, row, col, hovered_square, drawing_settings)
                            
                    elif client_game.playing_stage:
                        game_over_or_invalid = handle_piece_move(client_game, selected_piece, row, col)

                        # Clear valid moves so it doesn't re-enter the loop and potentially replace the square with an empty piece
                        valid_moves, valid_captures, valid_specials = [], [], []
                        # Reset selected piece variables to represent state
                        if not any(drawing_settings["side_selection_states"].values()):
                            selected_piece, selected_piece_image = None, None
                        for key in drawing_settings["side_selection_states"].keys():
                            if drawing_settings["side_selection_states"][key]:
                                selected_piece_image = transparent_pieces[key] if key != 'd' else None

            elif event.type == pygame.MOUSEMOTION:
                x, y = pygame.mouse.get_pos()
                row, col = get_board_coordinates(x, y, current_theme.GRID_SIZE)
                if current_theme.INVERSE_PLAYER_VIEW:
                    row, col = map_to_reversed_board(row, col)

                # Draw new hover with a selected piece and LMB
                if left_mouse_button_down and selected_piece is not None:  
                    if (row, col) != hovered_square:
                        hovered_square = (row, col) if col < 8 else None

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
                        for key in drawing_settings["side_selection_states"].keys():
                            drawing_settings["side_selection_states"][key] = False
                    
                    # First intent changed to false if mouseup on same square the first time
                    if first_intent and (row, col) == selected_piece:
                        first_intent = not first_intent
                    
                    if selected_piece is not None and (row, col) != selected_piece:
                        first_intent = False
                        
                        game_over_or_invalid = handle_piece_move(client_game, selected_piece, row, col)
                    
                        # Clear valid moves so it doesn't re-enter the loop and potentially replace the square with an empty piece
                        valid_moves, valid_captures, valid_specials = [], [], []
                        # Reset selected piece variables to represent state
                        if not any(drawing_settings["side_selection_states"].values()):
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

                elif event.key == pygame.K_f:
                    current_theme.INVERSE_PLAYER_VIEW = not current_theme.INVERSE_PLAYER_VIEW
                    # Redraw board and coordinates
                    drawing_settings["chessboard"] = generate_chessboard(current_theme)
                    drawing_settings["coordinate_surface"] = generate_coordinate_surface(current_theme)

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

        metadata_update = False

        game_FEN = translate_board_into_FEN(client_game.board)
        if web_game_metadata_dict['FEN'] != game_FEN:
            web_game_metadata_dict['FEN'] = game_FEN
            metadata_update = True

        if web_game_metadata_dict['game_over_or_invalid'] != game_over_or_invalid:
            web_game_metadata_dict['game_over_or_invalid'] = game_over_or_invalid
            metadata_update = True

        if web_game_metadata_dict['alg_moves'] != client_game.alg_moves:
            web_game_metadata_dict['alg_moves'] = client_game.alg_moves
            web_game_metadata_dict['comp_moves'] = client_game.moves
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