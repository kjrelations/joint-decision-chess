import pygame
import sys
import json
import asyncio
import pygbag.aio as asyncio
from game import *
from constants import *
from helpers import *

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
    # Initialize variables based on turn
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

def handle_piece_move(game, selected_piece, row, col):
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
        update, illegal = game.update_state(row, col, selected_piece)
        if piece.lower() != 'p' or (piece.lower() == 'p' and (row != 7 and row != 0)):
            print_d("ALG_MOVES:", game.alg_moves, debug=debug_prints)
        
        if update and ("x" in game.alg_moves[-1][0] or "x" in game.alg_moves[-1][1]):
            capture_sound.play()
        elif update:
            move_sound.play()
        elif illegal:
            error_sound.play()
        
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
    if piece.lower() == 'p' and (row == 0 or row == 7):
        promotion_required = True
        promotion_square = (row, col)

    return promotion_square, promotion_required

def handle_piece_special_move(game, selected_piece, row, col):
    # Need to be considering the selected piece for this section not an old piece
    piece = game.board[selected_piece[0]][selected_piece[1]]
    is_white = piece.isupper()

    # Castling and Enpassant moves are already validated, we simply update state
    update, illegal = game.update_state(row, col, selected_piece, special=True)
    print_d("ALG_MOVES:", game.alg_moves, debug=debug_prints)
    if update and ("x" in game.alg_moves[-1][0] or "x" in game.alg_moves[-1][1]):
        capture_sound.play()
    elif update:
        move_sound.play()
    elif illegal:
        error_sound.play()

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

# Game State loop for promotion
def promotion_state(
        promotion_square, 
        client_game, 
        row, col, 
        draw_board_params, 
        drawing_settings
        ):
    promotion_buttons = display_promotion_options(current_theme, promotion_square[0], promotion_square[1])
    promoted, promotion_required = False, True

    while promotion_required:

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
                        client_game.promote_to_piece(row, col, button.piece)
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

        pygame.display.flip()

    return promoted

def initialize_game(init, drawing_settings):
    current_theme.INVERSE_PLAYER_VIEW = not init["starting_player"]
    if init["starting_player"]:
        pygame.display.set_caption("Chess - White")
    else:
        pygame.display.set_caption("Chess - Black")
    if init["starting_position"] is None:
        client_game = Game(new_board.copy(), init["starting_player"])
    else:
        client_game = Game(custom_params=init["starting_position"])
    drawing_settings["chessboard"] = generate_chessboard(current_theme)
    drawing_settings["coordinate_surface"] = generate_coordinate_surface(current_theme)
    init["player"] = "white" if init["starting_player"] else "black"
    init["opponent"] = "black" if init["starting_player"] else "white"
    if not init["initialized"]:
        init["initializing"], init["initialized"] = False, True
    else:
        init["initializing"] = False
    return client_game

# Main loop
def main():

    init = {
        "running": True,
        "loaded": False,
        "waiting": True,
        "initializing": False,
        "initialized": False,
        "starting_player": None,
        "starting_position": None,
        "sent": None,
        "player": None,
        "opponent": None,
        "final_updates": False
    }
    client_game = None

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
        "wait_screen_drawn": False,
        "recalc_selections": False,
        "clear_selections": False,
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

        if init["initializing"]:
            client_game = initialize_game(init, drawing_settings)

        elif not init["loaded"]:
            init["starting_player"] = True
            current_theme.INVERSE_PLAYER_VIEW = not init["starting_player"]
            pygame.display.set_caption("Chess - Waiting on Connection")
            client_game = Game(new_board.copy(), init["starting_player"])
            init["player"] = "white"
            init["opponent"] = "black"
            init["loaded"] = True
            continue

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
                            # Allow moves only on current turn, if up to date, and synchronized
                            if not client_game.white_played or not client_game.black_played and client_game._latest and client_game._sync:
                                ## Free moves or captures
                                if (row, col) in valid_moves:
                                    promotion_square, promotion_required = \
                                        handle_piece_move(client_game, selected_piece, row, col)
                                    
                                    # Clear valid moves so it doesn't re-enter the loop and potentially replace the square with an empty piece
                                    valid_moves, valid_captures, valid_specials = [], [], []
                                    # Reset selected piece variables to represent state
                                    selected_piece, selected_piece_image = None, None
                                    
                                    if client_game.end_position:
                                        break

                                ## Specials
                                elif (row, col) in valid_specials:
                                    piece, is_white = handle_piece_special_move(client_game, selected_piece, row, col)
                                    
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
                        # For the second time a mouseup occurs on the same square it deselects it
                        # This can be an arbitrary number of mousedowns later
                        if not first_intent and (row, col) == selected_piece:
                                selected_piece = None
                                valid_moves, valid_captures, valid_specials = [], [], []
                        
                        # First intent changed to false if mouseup on same square the first time
                        if first_intent and (row, col) == selected_piece:
                            first_intent = not first_intent
                        
                        # Allow moves only on current turn, if up to date, and synchronized
                        if not client_game.white_played or not client_game.black_played and client_game._latest and client_game._sync:
                            ## Free moves or captures
                            if (row, col) in valid_moves:
                                promotion_square, promotion_required = \
                                    handle_piece_move(client_game, selected_piece, row, col)
                                
                                # Clear valid moves so it doesn't re-enter the loop and potentially replace the square with an empty piece
                                valid_moves, valid_captures, valid_specials = [], [], []
                                # Reset selected piece variables to represent state
                                selected_piece, selected_piece_image = None, None

                                if client_game.end_position:
                                    break

                            ## Specials
                            elif (row, col) in valid_specials:
                                piece, is_white = handle_piece_special_move(client_game, selected_piece, row, col)
                                
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
            'board': client_game.board,
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
            'drawing_settings': drawing_settings,
            'selected_piece': selected_piece,
            'white_current_position': client_game.white_current_position,
            'white_previous_position': client_game.white_previous_position,
            'black_current_position': client_game.black_current_position,
            'black_previous_position': client_game.black_previous_position,
            'right_clicked_squares': right_clicked_squares,
            'drawn_arrows': drawn_arrows,
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
                'white_current_position': client_game.white_current_position,
                'white_previous_position': client_game.white_previous_position,
                'black_current_position': client_game.black_current_position,
                'black_previous_position': client_game.black_previous_position,
                'right_clicked_squares': right_clicked_squares,
                'drawn_arrows': drawn_arrows,
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

            promoted = promotion_state(
                promotion_square, 
                client_game, 
                row, 
                col, 
                draw_board_params, # These are mutated on first draw then flipped again
                drawing_settings
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
            # We also need new promotion decisions for selected pieces
            white_selected_piece_image, black_selected_piece_image = get_transparent_active_piece(client_game, transparent_pieces)
            draw_board({
                'window': game_window,
                'theme': current_theme,
                'board': client_game.board,
                'drawing_settings': drawing_settings,
                'selected_piece': selected_piece,
                'white_current_position': client_game.white_current_position,
                'white_previous_position': client_game.white_previous_position,
                'black_current_position': client_game.black_current_position,
                'black_previous_position': client_game.black_previous_position,
                'right_clicked_squares': right_clicked_squares,
                'drawn_arrows': drawn_arrows,
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
                checkmate_white, remaining_moves_white = is_checkmate_or_stalemate(client_game.board, True)
                checkmate_black, remaining_moves_black = is_checkmate_or_stalemate(client_game.board, False)
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

        if client_game.end_position and client_game._latest:
            # Clear any selected highlights
            right_clicked_squares = []
            drawn_arrows = []
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    init["running"] = False

            game_window.fill((0, 0, 0))

            draw_board({
                'window': game_window,
                'theme': current_theme,
                'board': client_game.board,
                'drawing_settings': drawing_settings,
                'selected_piece': selected_piece,
                'white_current_position': client_game.white_current_position,
                'white_previous_position': client_game.white_previous_position,
                'black_current_position': client_game.black_current_position,
                'black_previous_position': client_game.black_previous_position,
                'right_clicked_squares': right_clicked_squares,
                'drawn_arrows': drawn_arrows,
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
            'board': client_game.board,
            'active_moves': [client_game.white_active_move, client_game.black_active_move]
            }

        pygame.display.flip()

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()