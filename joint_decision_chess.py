import pygame
import sys
from game import *
from constants import *
from helpers import *

# Consider first publishing a version that is the classical variant of chess. Decide when the two versions branch off.
# Initialize Pygame
pygame.init()
# Initialize mixer for sounds
pygame.mixer.init()

# Sound Effects
move_sound = pygame.mixer.Sound('sounds/move.mp3')
capture_sound = pygame.mixer.Sound('sounds/capture.mp3')

# Initialize Pygame window
window = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Chess")

# Load the chessboard as a reference image (drawn only once)
chessboard = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
for row in range(8):
    for col in range(8):
        color = WHITE_SQUARE if (row + col) % 2 == 0 else BLACK_SQUARE
        pygame.draw.rect(chessboard, color, (col * GRID_SIZE, row * GRID_SIZE, GRID_SIZE, GRID_SIZE))

# Load the chess pieces dynamically
pieces = {}
transparent_pieces = {}
for color in ['w', 'b']:
    for piece in ['r', 'n', 'b', 'q', 'k', 'p']:
        piece_key, image_name_key = name_keys(color, piece)
        pieces[piece_key], transparent_pieces[piece_key] = load_piece_image(image_name_key)

# Main loop piece selection logic that updates state
def handle_new_piece_selection(game, row, col, is_white, hovered_square):
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
            # Before making the move, create a copy of the board where the piece has moved
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
    # Need to be considering the selected piece for this section
    piece = game.board[selected_piece[0]][selected_piece[1]]
    is_white = piece.isupper()

    # Before making the move, create a copy of the game where the piece has moved
    temp_board = [rank[:] for rank in game.board]  
    temp_moves = game.moves.copy()
    temp_moves.append(output_move(piece, selected_piece, row, col, temp_board[row][col]))
    temp_board[row][col] = temp_board[selected_piece[0]][selected_piece[1]]
    temp_board[selected_piece[0]][selected_piece[1]] = ' '

    if not is_check(temp_board, is_white, temp_moves):
        # Move the piece if the king does not enter check
        game.update_state(row, col, selected_piece)
        if piece.lower() != 'p' or (piece.lower() == 'p' and (row != 7 and row != 0)):
            print("ALG_MOVES:", game.alg_moves)
        previous_position = (selected_piece[0], selected_piece[1])
        current_position = (row, col)
        
        if (row, col) in valid_captures:
            capture_sound.play()
        else:
            move_sound.play()
        
        selected_piece = None

        # Check for checkmate or stalemate
        checkmate, remaining_moves = is_checkmate_or_stalemate(game.board, not is_white, game.moves)
        if checkmate:
            print("CHECKMATE")
            game.add_end_game_notation(checkmate)
            return True, remaining_moves, None, previous_position, current_position, promotion_required
        if remaining_moves == 0:
            print("STALEMATE")
            game.add_end_game_notation(checkmate)
            return True, remaining_moves, None, previous_position, current_position, promotion_required

    # Pawn Promotion
    if game.board[row][col].lower() == 'p' and (row == 0 or row == 7):
        promotion_required = True
        promotion_square = (row, col)

    return False, None, promotion_square, previous_position, current_position, promotion_required

# Main loop piece special move selection logic that updates state
def handle_piece_special_move(game, selected_piece, row, col):
    # Need to be considering the selected piece for this section
    piece = game.board[selected_piece[0]][selected_piece[1]]
    is_white = piece.isupper()

    # Castling and Enpassant moves are already validated, we simply update state
    game.update_state(row, col, selected_piece, special=True)
    print("ALG_MOVES:", game.alg_moves)
    if (row, col) in [(7, 2), (7, 6), (0, 2), (0, 6)]:
        move_sound.play()
    else:
        capture_sound.play()

    # Check for checkmate or stalemate
    checkmate, remaining_moves = is_checkmate_or_stalemate(game.board, not is_white, game.moves)
    if checkmate:
        print("CHECKMATE")
        game.add_end_game_notation(checkmate)
        return True, remaining_moves, piece, is_white
    if remaining_moves == 0:
        print("STALEMATE")
        game.add_end_game_notation(checkmate)
        return True, remaining_moves, piece, is_white

    return False, None, piece, is_white

# Main loop
def main():
    game = Game(new_board.copy(), STARTING_PLAYER)
    running = True
    end_position = False

    selected_piece = None
    current_position = None
    previous_position = None
    hovered_square = None
    current_right_clicked_square = None
    right_clicked_squares = []
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

    # Main game loop
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.MOUSEBUTTONDOWN:
                # LIKELY UGLY IMPLEMENTATION
                if event.button == 1:  # Left mouse button
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
                    row, col = get_board_coordinates(x, y)
                    if not left_mouse_button_down:
                        current_right_clicked_square = (row, col)
                    continue

                if left_mouse_button_down:
                    # Clear highlights
                    right_clicked_squares = []

                    x, y = pygame.mouse.get_pos()
                    row, col = get_board_coordinates(x, y)
                    piece = game.board[row][col]
                    is_white = piece.isupper()
                    
                    if not selected_piece:
                        if piece != ' ':
                             # Update states with new piece selection
                             first_intent, selected_piece, selected_piece_image, valid_moves, valid_captures, valid_specials, hovered_square = \
                                handle_new_piece_selection(game, row, col, is_white, hovered_square)
                    else:
                        ## Free moves or captures
                        if (row, col) in valid_moves:
                            end_position, _ , promotion_square, previous_position, current_position, promotion_required = \
                                handle_piece_move(game, selected_piece, row, col, valid_captures)
                            
                            # Clear valid moves so it doesn't re-enter the loop and potentially replace the square with an empty piece
                            valid_moves, valid_captures, valid_specials = [], [], []
                            # Reset selected piece variables to represent state
                            selected_piece, selected_piece_image = None, None
                            # End-game condition
                            if end_position:
                                running = False
                                break
                        
                        ## Specials
                        elif (row, col) in valid_specials:
                            end_position, _, piece, is_white = handle_piece_special_move(game, selected_piece, row, col)
                            
                            # Clear valid moves so it doesn't re-enter the loop and potentially replace the square with an empty piece
                            valid_moves, valid_captures, valid_specials = [], [], []
                            # Reset selected piece variables to represent state
                            selected_piece, selected_piece_image = None, None
                            # End-game condition
                            if end_position:
                                running = False
                                break

                        else:
                            # Otherwise we are considering another piece or a re-selected piece
                            if piece != ' ':
                                # If the mouse stays on a square and a piece is clicked a second time 
                                # this ensures that mouseup on this square deselects the piece
                                if (row, col) == selected_piece and first_intent:
                                    first_intent = False
                                    selected_piece_image = transparent_pieces[piece]
                                
                                # Redraw the transparent dragged piece on subsequent clicks
                                if (row, col) == selected_piece and not first_intent:
                                    selected_piece_image = transparent_pieces[piece]
                                
                                # New piece
                                if (row, col) != selected_piece:
                                     first_intent, selected_piece, selected_piece_image, valid_moves, valid_captures, valid_specials, hovered_square = \
                                        handle_new_piece_selection(game, row, col, is_white, hovered_square)

            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button == 1:  # Left mouse button
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
                    
                    ## Free moves or captures
                    if (row, col) in valid_moves:
                        end_position, _, promotion_square, previous_position, current_position, promotion_required = \
                            handle_piece_move(game, selected_piece, row, col, valid_captures)
                        
                        # Clear valid moves so it doesn't re-enter the loop and potentially replace the square with an empty piece
                        valid_moves, valid_captures, valid_specials = [], [], []
                        # Reset selected piece variables to represent state
                        selected_piece, selected_piece_image = None, None
                        # End-game condition
                        if end_position:
                            running = False
                            break

                    ## Specials
                    elif (row, col) in valid_specials:
                        end_position, _, piece, is_white = handle_piece_special_move(game, selected_piece, row, col)
                        
                        # Clear valid moves so it doesn't re-enter the loop and potentially replace the square with an empty piece
                        valid_moves, valid_captures, valid_specials = [], [], []
                        # Reset selected piece variables to represent state
                        selected_piece, selected_piece_image = None, None
                        # End-game condition
                        if end_position:
                            running = False
                            break

                if event.button == 3:  # Right mouse button
                    right_mouse_button_down = False
                    # Highlighting individual squares at will
                    if (row, col) == current_right_clicked_square:
                        if (row, col) not in right_clicked_squares:
                            right_clicked_squares.append((row, col))
                        else:
                            right_clicked_squares.remove((row, col))
                    # drawing logic end here also append lines to list then blit them all at once later
                    # Also have active draw list with [[start,end], [start,end], ...] that clear on left mouse click down

            elif event.type == pygame.MOUSEMOTION:
                x, y = pygame.mouse.get_pos()
                row, col = get_board_coordinates(x, y)

                # Only draw hover outline when left button is down and a piece is selected
                if left_mouse_button_down and selected_piece is not None:  
                    if (row, col) != hovered_square:
                        hovered_square = (row, col)

            elif event.type == pygame.KEYDOWN:

                # Undo move
                if event.key == pygame.K_u:
                    # Update current and previous position highlighting
                    current_position, previous_position = game.undo_move()
                    hovered_square = None
                    selected_piece_image = None
                    selected_piece = None
                    first_intent = False
                    valid_moves, valid_captures, valid_specials = [], [], []

                # Resignation
                if event.key == pygame.K_r:
                    print("RESIGNATION")
                    running = False
                    end_position = True
                    game.add_end_game_notation(True)
                    break
                
                # Draw
                elif event.key == pygame.K_d:
                    print("DRAW")
                    running = False
                    end_position = True
                    game.add_end_game_notation(False)
                    break

        # Clear the screen
        window.fill((0, 0, 0))

        # Draw the board
        draw_board({
            'window': window,
            'board': game.board,
            'chessboard': chessboard,
            'selected_piece': selected_piece,
            'current_position': current_position,
            'previous_position': previous_position,
            'right_clicked_squares': right_clicked_squares,
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
                'window': window,
                'board': game.board,
                'chessboard': chessboard,
                'selected_piece': selected_piece,
                'current_position': current_position,
                'previous_position': previous_position,
                'right_clicked_squares': right_clicked_squares,
                'valid_moves': valid_moves,
                'valid_captures': valid_captures,
                'valid_specials': valid_specials,
                'pieces': pieces,
                'hovered_square': hovered_square,
                'selected_piece_image': selected_piece_image
            }

            new_current_position, new_previous_position, end_position, end_state = \
                display_promotion_options(draw_board_params, window, promotion_square[0], promotion_square[1], pieces, promotion_required, game)
            promotion_required, promotion_square = False, None

            if new_current_position is not None:
                current_position, previous_position = new_current_position, new_previous_position
                hovered_square = None
                selected_piece_image = None
                selected_piece = None
                first_intent = False
                valid_moves, valid_captures, valid_specials = [], [], []
                
            if end_position:
                running = False
                game.add_end_game_notation(end_state)

            # Remove the overlay and buttons by redrawing the board
            window.fill((0, 0, 0))
            # We likely need to reinput the arguments and can't use the above params as they are updated.
            draw_board({
                'window': window,
                'board': game.board,
                'chessboard': chessboard,
                'selected_piece': selected_piece,
                'current_position': current_position,
                'previous_position': previous_position,
                'right_clicked_squares': right_clicked_squares,
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
            piece = game.board[row][col]
            is_white = piece.isupper()
            # Check for checkmate or stalemate
            checkmate, remaining_moves = is_checkmate_or_stalemate(game.board, not is_white, game.moves)
            if checkmate:
                print("CHECKMATE")
                running = False
                end_position = True
                game.add_end_game_notation(checkmate)
            if remaining_moves == 0:
                print("STALEMATE")
                running = False
                end_position = True
                game.add_end_game_notation(checkmate)
        
        # Only allow for retrieval of algebraic notation at this point after potential promotion, if necessary
        pygame.display.flip()
    
    while end_position:
        # Clear any selected highlights
        right_clicked_squares = []
        # Clear the screen
        window.fill((0, 0, 0))

        # Draw the board
        draw_board({
            'window': window,
            'board': game.board,
            'chessboard': chessboard,
            'selected_piece': selected_piece,
            'current_position': current_position,
            'previous_position': previous_position,
            'right_clicked_squares': right_clicked_squares,
            'valid_moves': valid_moves,
            'valid_captures': valid_captures,
            'valid_specials': valid_specials,
            'pieces': pieces,
            'hovered_square': hovered_square,
            'selected_piece_image': selected_piece_image
        })

        # Darken the screen
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 128))

        # Blit the overlay surface onto the main window
        window.blit(overlay, (0, 0))
        pygame.display.flip()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                end_position = False

    # Quit Pygame
    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()