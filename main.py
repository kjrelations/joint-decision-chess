import pygame
import sys
import json
import asyncio
from game import *
from constants import *
from helpers import *

# Initialize Pygame
pygame.init()

current_theme = Theme()

with open('themes.json', 'r') as file:
    themes = json.load(file)

# Initialize Pygame window
window = pygame.display.set_mode((current_theme.WIDTH, current_theme.HEIGHT))
pygame.display.set_caption("Chess")

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
            print("DRAW BY THREEFOLD REPETITION")
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
        print("DRAW BY THREEFOLD REPETITION")
        game.end_position = True
        game.add_end_game_notation(checkmate)
        return piece, is_white

    return piece, is_white

# Main loop
async def main():
    starting_player = True
    current_theme.INVERSE_PLAYER_VIEW = not starting_player
    game = Game(new_board.copy(), starting_player)
    running = True

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

    # Main game loop
    while running:
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
                            promotion_square, promotion_required = \
                                handle_piece_move(game, selected_piece, row, col, valid_captures)
                            
                            # Clear valid moves so it doesn't re-enter the loop and potentially replace the square with an empty piece
                            valid_moves, valid_captures, valid_specials = [], [], []
                            # Reset selected piece variables to represent state
                            selected_piece, selected_piece_image = None, None
                            
                            if game.end_position:
                                running = False
                                break
                        
                        ## Specials
                        elif (row, col) in valid_specials:
                            piece, is_white = handle_piece_special_move(game, selected_piece, row, col)
                            
                            # Clear valid moves so it doesn't re-enter the loop and potentially replace the square with an empty piece
                            valid_moves, valid_captures, valid_specials = [], [], []
                            # Reset selected piece variables to represent state
                            selected_piece, selected_piece_image = None, None

                            if game.end_position:
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
                                        handle_new_piece_selection(game, row, col, is_white, hovered_square)

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
                    
                    ## Free moves or captures
                    if (row, col) in valid_moves:
                        promotion_square, promotion_required = \
                            handle_piece_move(game, selected_piece, row, col, valid_captures)
                        
                        # Clear valid moves so it doesn't re-enter the loop and potentially replace the square with an empty piece
                        valid_moves, valid_captures, valid_specials = [], [], []
                        # Reset selected piece variables to represent state
                        selected_piece, selected_piece_image = None, None

                        if game.end_position:
                            running = False
                            break

                    ## Specials
                    elif (row, col) in valid_specials:
                        piece, is_white = handle_piece_special_move(game, selected_piece, row, col)
                        
                        # Clear valid moves so it doesn't re-enter the loop and potentially replace the square with an empty piece
                        valid_moves, valid_captures, valid_specials = [], [], []
                        # Reset selected piece variables to represent state
                        selected_piece, selected_piece_image = None, None

                        if game.end_position:
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

            elif event.type == pygame.KEYDOWN:

                # Undo move
                if event.key == pygame.K_u:
                    # Update current and previous position highlighting
                    game.undo_move()
                    hovered_square = None
                    selected_piece_image = None
                    selected_piece = None
                    first_intent = False
                    valid_moves, valid_captures, valid_specials = [], [], []
                    right_clicked_squares = []
                    drawn_arrows = []

                # Resignation
                if event.key == pygame.K_r:
                    game.forced_end = "WHITE RESIGNATION" if game.current_turn else "BLACK RESIGNATION"
                    print(game.forced_end)
                    running = False
                    game.end_position = True
                    game.add_end_game_notation(True)
                    break
                
                # Draw
                elif event.key == pygame.K_d:
                    print("DRAW")
                    running = False
                    game.end_position = True
                    game.forced_end = "DRAW"
                    game.add_end_game_notation(False)
                    break

                # Theme cycle
                elif event.key == pygame.K_t:
                    theme_index += 1
                    theme_index %= len(themes)
                    current_theme.apply_theme(themes[theme_index])
                    # Redraw board and coordinates
                    chessboard = generate_chessboard(current_theme)
                    coordinate_surface = generate_coordinate_surface(current_theme)

                # Flip Perspective
                elif event.key == pygame.K_i:
                    current_theme.INVERSE_PLAYER_VIEW = not current_theme.INVERSE_PLAYER_VIEW
                    # Redraw board and coordinates
                    chessboard = generate_chessboard(current_theme)
                    coordinate_surface = generate_coordinate_surface(current_theme)

        # Clear the screen
        window.fill((0, 0, 0))

        # Draw the board
        draw_board({
            'window': window,
            'theme': current_theme,
            'board': game.board,
            'chessboard': chessboard,
            'selected_piece': selected_piece,
            'current_position': game.current_position,
            'previous_position': game.previous_position,
            'right_clicked_squares': right_clicked_squares,
            'coordinate_surface': coordinate_surface,
            'drawn_arrows': drawn_arrows,
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
                'theme': current_theme,
                'board': game.board,
                'chessboard': chessboard,
                'selected_piece': selected_piece,
                'current_position': game.current_position,
                'previous_position': game.previous_position,
                'right_clicked_squares': right_clicked_squares,
                'coordinate_surface': coordinate_surface,
                'drawn_arrows': drawn_arrows,
                'valid_moves': valid_moves,
                'valid_captures': valid_captures,
                'valid_specials': valid_specials,
                'pieces': pieces,
                'hovered_square': hovered_square,
                'selected_piece_image': selected_piece_image
            }

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
                    if event.type == pygame.KEYDOWN:

                        # Undo move
                        if event.key == pygame.K_u:
                            # Update current and previous position highlighting
                            game.undo_move()
                            promotion_required = False
                        
                        # Resignation
                        elif event.key == pygame.K_r:
                            game.undo_move()
                            game.forced_end = "WHITE RESIGNATION" if game.current_turn else "BLACK RESIGNATION"
                            print(game.forced_end)
                            promotion_required = False
                            game.end_position = True
                            end_state = True
                        
                        # Draw
                        elif event.key == pygame.K_d:
                            game.undo_move()
                            print("DRAW")
                            promotion_required = False
                            game.end_position = True
                            game.forced_end = "DRAW"
                            end_state = False
                
                # Clear the screen
                window.fill((0, 0, 0))
                
                # Draw the board, we need to copy the params else we keep mutating them with each call for inverse board draws
                draw_board(draw_board_params.copy())
                
                # Darken the screen
                overlay = pygame.Surface((current_theme.WIDTH, current_theme.HEIGHT), pygame.SRCALPHA)
                overlay.fill((0, 0, 0, 128))

                # Blit the overlay surface onto the main window
                window.blit(overlay, (0, 0))

                # Draw buttons and update the display
                for button in promotion_buttons:
                    img = pieces[button.piece]
                    img_x, img_y = button.rect.x, button.rect.y
                    if button.is_hovered:
                        img = pygame.transform.smoothscale(img, (current_theme.GRID_SIZE * 1.5, current_theme.GRID_SIZE * 1.5))
                        img_x, img_y = button.scaled_x, button.scaled_y
                    window.blit(img, (img_x, img_y))

                pygame.display.flip()
                await asyncio.sleep(0)

            promotion_required, promotion_square = False, None

            if promoted:
                hovered_square = None
                selected_piece_image = None
                selected_piece = None
                first_intent = False
                valid_moves, valid_captures, valid_specials = [], [], []
                
            if game.end_position:
                running = False
                game.add_end_game_notation(end_state)

            # Remove the overlay and buttons by redrawing the board
            window.fill((0, 0, 0))
            # We likely need to reinput the arguments and can't use the above params as they are updated.
            draw_board({
                'window': window,
                'theme': current_theme,
                'board': game.board,
                'chessboard': chessboard,
                'selected_piece': selected_piece,
                'current_position': game.current_position,
                'previous_position': game.previous_position,
                'right_clicked_squares': right_clicked_squares,
                'coordinate_surface': coordinate_surface,
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
            piece = game.board[row][col]
            is_white = piece.isupper()

            checkmate, remaining_moves = is_checkmate_or_stalemate(game.board, not is_white, game.moves)
            if checkmate:
                print("CHECKMATE")
                running = False
                game.end_position = True
                game.add_end_game_notation(checkmate)
            elif remaining_moves == 0:
                print("STALEMATE")
                running = False
                game.end_position = True
                game.add_end_game_notation(checkmate)
            # This seems redundant as promotions should lead to unique boards but we leave it in anyway
            elif game.threefold_check():
                print("DRAW BY THREEFOLD REPETITION")
                running = False
                game.end_position = True
                game.add_end_game_notation(checkmate)
        
        # Only allow for retrieval of algebraic notation at this point after potential promotion, if necessary in the future
        pygame.display.flip()
        await asyncio.sleep(0)

    while game.end_position:
        # Clear any selected highlights
        right_clicked_squares = []
        drawn_arrows = []
        
        # Clear the screen
        window.fill((0, 0, 0))

        # Draw the board
        draw_board({
            'window': window,
            'theme': current_theme,
            'board': game.board,
            'chessboard': chessboard,
            'selected_piece': selected_piece,
            'current_position': game.current_position,
            'previous_position': game.previous_position,
            'right_clicked_squares': right_clicked_squares,
            'coordinate_surface': coordinate_surface,
            'drawn_arrows': drawn_arrows,
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
        window.blit(overlay, (0, 0))
        pygame.display.flip()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                game.end_position = False
        await asyncio.sleep(0)

    # Quit Pygame
    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    asyncio.run(main())