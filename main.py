import pygame
import sys
import json
import asyncio
from game import *
from constants import *
from helpers import *
from network import Network

# # Handle Persistent Storage
# if __import__("sys").platform == "emscripten":
#     from platform import window

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

# Main loop piece selection logic that updates state
def handle_new_piece_selection(game, row, col, is_white, hovered_square):
    piece = game.board[row][col]
    # Initialize variables based on turn
    if game._starting_player == is_white or game._debug:
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

# Main loop piece move selection logic that updates state
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

# Main loop piece special move selection logic that updates state
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

# # Command-Action synchronization function
# def handle_command(command_name, client_action_status, client_executed_status, status_metadata_dict, status_metadata_name):
#     # Command to execute is received and no update is sent
#     if status_metadata_dict[command_name]['execute'] and not status_metadata_dict[command_name]['update_executed']:
#         client_action_status = True
#         if client_executed_status:
#             status_metadata_dict[command_name]['update_executed'] = True
#             json_metadata = json.dumps(status_metadata_dict)
#             window.localStorage.setItem(status_metadata_name, json_metadata)
#             client_action_status = False

#     # Handling race conditions assuming speed differences and sychronizing states with this.
#     # That is only once we stop receiving the command, after an execution, do we allow it to be executed again
#     if client_executed_status and not status_metadata_dict[command_name]['execute']:
#         client_executed_status = False    

#     return client_action_status, client_executed_status

# Game State loop for promotion
async def promotion_state(promotion_square, game, row, col, draw_board_params):
    promotion_buttons = display_promotion_options(current_theme, promotion_square[0], promotion_square[1])
    promoted, promotion_required, end_state = False, True, None
    
    while promotion_required:
        for event in pygame.event.get():
            for button in promotion_buttons:
                button.handle_event(event)
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    x, y = pygame.mouse.get_pos()
                    if button.rect.collidepoint(x, y):
                        game.promote_to_piece(row, col, button.piece)
                        promotion_required = False  # Exit promotion state condition
                        promoted = True
            # if event.type == pygame.KEYDOWN:

            #     # Undo move
            #     if event.key == pygame.K_u:
            #         # Update current and previous position highlighting
            #         game.undo_move()
            #         promotion_required = False
                
            #     # Resignation
            #     elif event.key == pygame.K_r:
            #         game.undo_move()
            #         print(game.forced_end)
            #         game.forced_end = "White Resigned" if game.current_turn else "Black Resigned"
            #         promotion_required = False
            #         game.end_position = True
            #         end_state = True
                
            #     # Draw
            #     elif event.key == pygame.K_d:
            #         game.undo_move()
            #         print(game.forced_end)
            #         game.forced_end = "Draw by mutual agreement"
            #         promotion_required = False
            #         game.end_position = True
            #         end_state = False
        
        # Clear the screen
        game_window.fill((0, 0, 0))
        
        # Draw the board, we need to copy the params else we keep mutating them with each call for inverse board draws
        draw_board(draw_board_params.copy())
        
        # Darken the screen
        overlay = pygame.Surface((current_theme.WIDTH, current_theme.HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 128))

        # Blit the overlay surface onto the main window
        game_window.blit(overlay, (0, 0))

        # Draw buttons and update the display
        for button in promotion_buttons:
            img = pieces[button.piece]
            img_x, img_y = button.rect.x, button.rect.y
            if button.is_hovered:
                img = pygame.transform.smoothscale(img, (current_theme.GRID_SIZE * 1.5, current_theme.GRID_SIZE * 1.5))
                img_x, img_y = button.scaled_x, button.scaled_y
            game_window.blit(img, (img_x, img_y))

        pygame.display.flip()
        await asyncio.sleep(0)

    return promoted, end_state

# Main loop
async def main():
    n = Network()
    starting_player = n.get_player()
    current_theme.INVERSE_PLAYER_VIEW = not starting_player
    if starting_player:
        pygame.display.set_caption("Chess - White")
    else:
        pygame.display.set_caption("Chess - Black")
    client_game = Game(new_board.copy(), starting_player)
    running = True
    waiting = True

    # # Web Browser actions affect these only. Even if players try to alter it, 
    # # It simply enables the buttons or does a local harmless action
    # # The following are client-side status variables, the first is whether an action should be performed,
    # # the second on whether an action has been performed, the optional reset variable is unimplemented but indicates whether an action has been aborted
    # # based on other multiplayer actions.
    # undo, undo_executed, reset_undo = False, False, False
    # cycle_theme, cycle_theme_executed = False, False
    # resign, resign_executed, reset_resign = False, False, False
    # draw_offer, draw_offer_accepted_executed, reset_draw = False, False, False
    # flip, flip_executed = False, False
    # console_log_messages = []

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

    # Only draw these surfaces as needed; once per selection of theme
    chessboard = generate_chessboard(current_theme)
    coordinate_surface = generate_coordinate_surface(current_theme)
    theme_index = 0

    print("Waiting to connect to second game...")
    while waiting:
        try:
            games = n.send(client_game)
            if games is None or len(games) == 1:
                if games is not None:
                    client_game = games[0]
                # Need to pump the event queque like below in order to move window
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        running = False
                        waiting = False

                # Clear the screen
                game_window.fill((0, 0, 0))

                # Draw the board
                draw_board({
                    'window': game_window,
                    'theme': current_theme,
                    'board': client_game.board,
                    'chessboard': chessboard,
                    'selected_piece': selected_piece,
                    'current_position': client_game.current_position,
                    'previous_position': client_game.previous_position,
                    'right_clicked_squares': right_clicked_squares,
                    'coordinate_surface': coordinate_surface,
                    'drawn_arrows': drawn_arrows,
                    'starting_player': client_game._starting_player,
                    'valid_moves': valid_moves,
                    'valid_captures': valid_captures,
                    'valid_specials': valid_specials,
                    'pieces': pieces,
                    'hovered_square': hovered_square,
                    'selected_piece_image': selected_piece_image
                })

                # Darken the screen
                overlay = pygame.Surface((current_theme.WIDTH, current_theme.HEIGHT), pygame.SRCALPHA)
                overlay.fill((0, 0, 0, 128))

                # Blit the overlay surface onto the main window
                game_window.blit(overlay, (0, 0))
                pygame.display.flip()
            else:
                waiting = False
        except Exception as err:
            running = False
            print("Could not get game, connection to server failed... ", err)
            break
        await asyncio.sleep(0)

    # Main game loop
    while running:
        # Web browser actions/commands are received
        # if undo:
        #     # Update current and previous position highlighting
        #     client_game.undo_move()
        #     hovered_square = None
        #     selected_piece_image = None
        #     selected_piece = None
        #     first_intent = False
        #     valid_moves, valid_captures, valid_specials = [], [], []
        #     right_clicked_squares = []
        #     drawn_arrows = []
        #     undo = False
        #     undo_executed = True
        
        # if resign:
        #     client_game.forced_end = "White Resigned" if client_game.current_turn else "Black Resigned"
        #     print(client_game.forced_end)
        #     running = False
        #     client_game.end_position = True
        #     client_game.add_end_game_notation(True)
        #     resign = False
        #     resign_executed = True
        #     break

        # if draw_offer:
        #     client_game.forced_end = "Draw by mutual agreement"
        #     print(client_game.forced_end)
        #     running = False
        #     client_game.end_position = True
        #     client_game.add_end_game_notation(False)
        #     draw_offer = False
        #     draw_offer_accepted_executed = True
        #     break

        # # Theme cycle
        # if cycle_theme:
        #     theme_index += 1
        #     theme_index %= len(themes)
        #     current_theme.apply_theme(themes[theme_index])
        #     # Redraw board and coordinates
        #     chessboard = generate_chessboard(current_theme)
        #     coordinate_surface = generate_coordinate_surface(current_theme)
        #     cycle_theme = False
        #     cycle_theme_executed = True

        # if flip:
        #     current_theme.INVERSE_PLAYER_VIEW = not current_theme.INVERSE_PLAYER_VIEW
        #     # Redraw board and coordinates
        #     chessboard = generate_chessboard(current_theme)
        #     coordinate_surface = generate_coordinate_surface(current_theme)
        #     flip = False
        #     flip_executed = True

        try:
            games = n.send(client_game)
            if starting_player:
                if client_game._sync:
                    # Previously had the redundant and incorrect games[0].current_turn == game._starting_player and game.current_turn != game._starting_player as a first condition
                    # but this won't work when undo button undoes two moves
                    if (len(games[1].alg_moves) > len(client_game.alg_moves)) or (len(games[1].alg_moves) < len(client_game.alg_moves) and games[1]._move_undone) or \
                        games[1].end_position:
                        client_game.synchronize(games[1])
                        if client_game.alg_moves != []:
                            if not any(symbol in client_game.alg_moves[-1] for symbol in ['0-1', '1-0', '½–½']): # Could add a winning or losing sound
                                if "x" not in client_game.alg_moves[-1]:
                                    move_sound.play()
                                else:
                                    capture_sound.play()
                            if client_game.end_position:
                                running = False
                                is_white = True
                                checkmate, remaining_moves = is_checkmate_or_stalemate(client_game.board, is_white, client_game.moves)
                                if checkmate:
                                    print("CHECKMATE")
                                elif remaining_moves == 0:
                                    print("STALEMATE")
                                elif client_game.threefold_check():
                                    print("DRAW BY THREEFOLD REPETITION")
                                elif client_game.forced_end != "":
                                    print(client_game.forced_end)
                                print("ALG_MOVES: ", client_game.alg_moves)
                                break
                            print("ALG_MOVES: ", client_game.alg_moves)
                else:
                    if games[1].board == client_game.board:
                        print("Syncing White...")
                        client_game._sync = True
                        client_game._move_undone = False
                        games = n.send(client_game)
            else:
                if client_game._sync:
                    if (len(games[0].alg_moves) > len(client_game.alg_moves)) or (len(games[0].alg_moves) < len(client_game.alg_moves) and games[0]._move_undone) or \
                        games[0].end_position:
                        client_game.synchronize(games[0])
                        if client_game.alg_moves != []:
                            if not any(symbol in client_game.alg_moves[-1] for symbol in ['0-1', '1-0', '½–½']):
                                if "x" not in client_game.alg_moves[-1]:
                                    move_sound.play()
                                else:
                                    capture_sound.play()
                            if client_game.end_position:
                                running = False
                                is_white = False
                                checkmate, remaining_moves = is_checkmate_or_stalemate(client_game.board, is_white, client_game.moves)
                                if checkmate:
                                    print("CHECKMATE")
                                elif remaining_moves == 0:
                                    print("STALEMATE")
                                elif client_game.threefold_check():
                                    print("DRAW BY THREEFOLD REPETITION")
                                elif client_game.forced_end != "":
                                    print(client_game.forced_end)
                                print("ALG_MOVES: ", client_game.alg_moves)
                                break
                            print("ALG_MOVES: ", client_game.alg_moves)
                else:
                    if games[0].board == client_game.board:
                        print("Syncing Black...")
                        client_game._sync = True
                        client_game._move_undone = False
                        games = n.send(client_game)
        except Exception as err:
            running = False
            print("Could not get game... ", err)
            break
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
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
                        if client_game.current_turn == client_game._starting_player:
                            ## Free moves or captures
                            if (row, col) in valid_moves:
                                promotion_square, promotion_required = \
                                    handle_piece_move(client_game, selected_piece, row, col, valid_captures)
                                
                                # Clear valid moves so it doesn't re-enter the loop and potentially replace the square with an empty piece
                                valid_moves, valid_captures, valid_specials = [], [], []
                                # Reset selected piece variables to represent state
                                selected_piece, selected_piece_image = None, None
                                
                                if client_game.end_position:
                                    running = False
                                    break
                            
                            ## Specials
                            elif (row, col) in valid_specials:
                                piece, is_white = handle_piece_special_move(client_game, selected_piece, row, col)
                                
                                # Clear valid moves so it doesn't re-enter the loop and potentially replace the square with an empty piece
                                valid_moves, valid_captures, valid_specials = [], [], []
                                # Reset selected piece variables to represent state
                                selected_piece, selected_piece_image = None, None

                                if client_game.end_position:
                                    running = False
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
                    
                    if client_game.current_turn == client_game._starting_player:
                        ## Free moves or captures
                        if (row, col) in valid_moves:
                            promotion_square, promotion_required = \
                                handle_piece_move(client_game, selected_piece, row, col, valid_captures)
                            
                            # Clear valid moves so it doesn't re-enter the loop and potentially replace the square with an empty piece
                            valid_moves, valid_captures, valid_specials = [], [], []
                            # Reset selected piece variables to represent state
                            selected_piece, selected_piece_image = None, None

                            if client_game.end_position:
                                running = False
                                break

                        ## Specials
                        elif (row, col) in valid_specials:
                            piece, is_white = handle_piece_special_move(client_game, selected_piece, row, col)
                            
                            # Clear valid moves so it doesn't re-enter the loop and potentially replace the square with an empty piece
                            valid_moves, valid_captures, valid_specials = [], [], []
                            # Reset selected piece variables to represent state
                            selected_piece, selected_piece_image = None, None

                            if client_game.end_position:
                                running = False
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

        # Clear the screen
        game_window.fill((0, 0, 0))

        # Draw the board
        draw_board({
            'window': game_window,
            'theme': current_theme,
            'board': client_game.board,
            'chessboard': chessboard,
            'selected_piece': selected_piece,
            'current_position': client_game.current_position,
            'previous_position': client_game.previous_position,
            'right_clicked_squares': right_clicked_squares,
            'coordinate_surface': coordinate_surface,
            'drawn_arrows': drawn_arrows,
            'starting_player': client_game._starting_player,
            'valid_moves': valid_moves,
            'valid_captures': valid_captures,
            'valid_specials': valid_specials,
            'pieces': pieces,
            'hovered_square': hovered_square,
            'selected_piece_image': selected_piece_image
        })

        # Pawn Promotion
        if promotion_required:
            # Lock the game state (disable other input)
            
            # Display an overlay or popup with promotion options
            draw_board_params = {
                'window': game_window,
                'theme': current_theme,
                'board': client_game.board,
                'chessboard': chessboard,
                'selected_piece': selected_piece,
                'current_position': client_game.current_position,
                'previous_position': client_game.previous_position,
                'right_clicked_squares': right_clicked_squares,
                'coordinate_surface': coordinate_surface,
                'drawn_arrows': drawn_arrows,
                'starting_player': client_game._starting_player,
                'valid_moves': valid_moves,
                'valid_captures': valid_captures,
                'valid_specials': valid_specials,
                'pieces': pieces,
                'hovered_square': hovered_square,
                'selected_piece_image': selected_piece_image
            }

            promoted, end_state = await promotion_state(promotion_square, client_game, row, col, draw_board_params)
            promotion_required, promotion_square = False, None

            if promoted:
                hovered_square = None
                selected_piece_image = None
                selected_piece = None
                first_intent = False
                valid_moves, valid_captures, valid_specials = [], [], []
                
            if client_game.end_position:
                running = False
                client_game.add_end_game_notation(end_state)

            # Remove the overlay and buttons by redrawing the board
            game_window.fill((0, 0, 0))
            # We likely need to reinput the arguments and can't use the above params as they are updated.
            draw_board({
                'window': game_window,
                'theme': current_theme,
                'board': client_game.board,
                'chessboard': chessboard,
                'selected_piece': selected_piece,
                'current_position': client_game.current_position,
                'previous_position': client_game.previous_position,
                'right_clicked_squares': right_clicked_squares,
                'coordinate_surface': coordinate_surface,
                'drawn_arrows': drawn_arrows,
                'starting_player': client_game._starting_player,
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
                running = False
                client_game.end_position = True
                client_game.add_end_game_notation(checkmate)
            elif remaining_moves == 0:
                print("STALEMATE")
                running = False
                client_game.end_position = True
                client_game.add_end_game_notation(checkmate)
            # This seems redundant as promotions should lead to unique boards but we leave it in anyway
            elif client_game.threefold_check():
                print("STALEMATE BY THREEFOLD REPETITION")
                client_game.forced_end = "Stalemate by Threefold Repetition"
                running = False
                client_game.end_position = True
                client_game.add_end_game_notation(checkmate)
        
        # # Only allow for retrieval of algebraic notation at this point after potential promotion, if necessary in the future
        # web_game_metadata = window.localStorage.getItem("web_game_metadata")

        # web_game_metadata_dict = json.loads(web_game_metadata)

        # # DEV logs to console
        # # web_game_metadata_dict['console_messages'].extend(console_log_messages)

        # # TODO Can just put this into an asynchronous loop if I wanted or needed
        # command_status = [
        #     ("undo_move", undo, undo_executed),
        #     ("resign", resign, resign_executed),
        #     ("draw_offer", draw_offer, draw_offer_accepted_executed),
        #     ("cycle_theme", cycle_theme, cycle_theme_executed),
        #     ("flip", flip, flip_executed)
        # ]
        
        # # Undo move, resign, draw offer, cycle theme, flip command handle
        # for client_status in command_status:
        #     command, client_action_status, client_executed_status = client_status
        #     client_action_status, client_executed_status = handle_command(command, client_action_status, client_executed_status, web_game_metadata_dict, "web_game_metadata")        

        # if web_game_metadata_dict['alg_moves'] != client_game.alg_moves:
        #     web_game_metadata_dict['alg_moves'] = client_game.alg_moves

        #     web_game_metadata = json.dumps(web_game_metadata_dict)
        #     window.localStorage.setItem("web_game_metadata", web_game_metadata)
        
        # # Maybe I just set this initially in a better way, this looks clunky
        # if client_game._starting_player and web_game_metadata_dict['player_color'] != 'white':
        #     web_game_metadata_dict['player_color'] = 'white'

        #     web_game_metadata = json.dumps(web_game_metadata_dict)
        #     window.localStorage.setItem("web_game_metadata", web_game_metadata)
        # elif not client_game._starting_player and web_game_metadata_dict['player_color'] != 'black':
        #     web_game_metadata_dict['player_color'] = 'black'

        #     web_game_metadata = json.dumps(web_game_metadata_dict)
        #     window.localStorage.setItem("web_game_metadata", web_game_metadata)
        
        try:
            if client_game.current_turn != client_game._starting_player or not client_game._sync:
                _ = n.send(client_game)
        except Exception as err:
            running = False
            client_game.end_position = True
            print("Could not send/get games... ", err)
            break

        # Only allow for retrieval of algebraic notation at this point after potential promotion, if necessary in the future
        pygame.display.flip()
        await asyncio.sleep(0)

    if client_game.end_position:
        try:
            _ = n.send(client_game)
        except Exception as err:
            print("Could not send game... ", err)

    while client_game.end_position:
        # Clear any selected highlights
        right_clicked_squares = []
        drawn_arrows = []
        
        # Clear the screen
        game_window.fill((0, 0, 0))

        # Draw the board
        draw_board({
            'window': game_window,
            'theme': current_theme,
            'board': client_game.board,
            'chessboard': chessboard,
            'selected_piece': selected_piece,
            'current_position': client_game.current_position,
            'previous_position': client_game.previous_position,
            'right_clicked_squares': right_clicked_squares,
            'coordinate_surface': coordinate_surface,
            'drawn_arrows': drawn_arrows,
            'starting_player': client_game._starting_player,
            'valid_moves': valid_moves,
            'valid_captures': valid_captures,
            'valid_specials': valid_specials,
            'pieces': pieces,
            'hovered_square': hovered_square,
            'selected_piece_image': selected_piece_image
        })

        # Darken the screen
        overlay = pygame.Surface((current_theme.WIDTH, current_theme.HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 128))

        # Blit the overlay surface onto the main window
        game_window.blit(overlay, (0, 0))
        pygame.display.flip()

        # web_game_metadata = window.localStorage.getItem("web_game_metadata")

        # web_game_metadata_dict = json.loads(web_game_metadata)

        # if web_game_metadata_dict['end_state'] != client_game.alg_moves[-1]:
        #     web_game_metadata_dict['end_state'] = client_game.alg_moves[-1]
        #     web_game_metadata_dict['forced_end'] = client_game.forced_end
        #     web_game_metadata_dict['alg_moves'] = client_game.alg_moves

        #     web_game_metadata = json.dumps(web_game_metadata_dict)
        #     window.localStorage.setItem("web_game_metadata", web_game_metadata)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                client_game.end_position = False
        await asyncio.sleep(0)

    # Quit Pygame
    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    asyncio.run(main())