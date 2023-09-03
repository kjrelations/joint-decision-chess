import pygame
import sys
from constants import *

## General Helpers
# Helper Function for generating bespoke Game moves
def output_move(piece, selected_piece, new_row, new_col, potential_capture, special_string= ''):
    return [piece+str(selected_piece[0])+str(selected_piece[1]), piece+str(new_row)+str(new_col), potential_capture, special_string]

## Move logic
# Helper function to calculate moves for a pawn
def pawn_moves(board, row, col, is_white):
    moves = []
    captures = []

    # Pawn moves one square forward
    if is_white:
        if row > 0 and board[row - 1][col] == ' ':
            moves.append((row - 1, col))
    else:
        if row < 7 and board[row + 1][col] == ' ':
            moves.append((row + 1, col))

    # Pawn's initial double move
    if is_white:
        if row == 6 and board[row - 1][col] == ' ' \
                    and board[row - 2][col] == ' ':
            moves.append((row - 2, col))
    else:
        if row == 1 and board[row + 1][col] == ' ' \
                    and board[row + 2][col] == ' ':
            moves.append((row + 2, col))

    # No captures possible when pawns reach the end, otherwise list index out of range
    if is_white and row == 0 or not is_white and row == 7:
        return moves, captures

    # Pawn captures diagonally
    forwards = -1 if is_white else 1 # The forward direction for white is counting down rows
    if row > 0 and col > 0 and board[row + forwards][col - 1] != ' ' and \
        board[row + forwards][col - 1].islower() == is_white:
        moves.append((row + forwards, col - 1))
        captures.append((row + forwards, col - 1))
    if row > 0 and col < 7 and board[row + forwards][col + 1] != ' ' \
        and board[row + forwards][col + 1].islower() == is_white:
        moves.append((row + forwards, col + 1))
        captures.append((row + forwards, col + 1))
    # Edge case diagonal captures
    if row > 0 and col == 7 and board[row + forwards][col - 1] != ' ' \
        and board[row + forwards][col - 1].islower() == is_white:
        moves.append((row + forwards, col - 1))
        captures.append((row + forwards, col - 1))
    if row > 0 and col == 0 and board[row + forwards][col + 1] != ' ' \
        and board[row + forwards][col + 1].islower() == is_white:
        moves.append((row + forwards, col + 1))
        captures.append((row + forwards, col + 1))

    return moves, captures

# Helper function to calculate moves for a rook
def rook_moves(board, row, col, is_white):
    moves = []
    captures = []

    # Rook moves horizontally
    for i in range(col + 1, 8):
        if board[row][i] == ' ':
            moves.append((row, i))
        else:
            if board[row][i].islower() == is_white:
                moves.append((row, i))
                captures.append((row, i))
            break

    for i in range(col - 1, -1, -1):
        if board[row][i] == ' ':
            moves.append((row, i))
        else:
            if board[row][i].islower() == is_white:
                moves.append((row, i))
                captures.append((row, i))
            break

    # Rook moves vertically
    for i in range(row + 1, 8):
        if board[i][col] == ' ':
            moves.append((i, col))
        else:
            if board[i][col].islower() == is_white:
                moves.append((i, col))
                captures.append((i, col))
            break

    for i in range(row - 1, -1, -1):
        if board[i][col] == ' ':
            moves.append((i, col))
        else:
            if board[i][col].islower() == is_white:
                moves.append((i, col))
                captures.append((i, col))
            break
    return moves, captures

# Helper function to calculate moves for a knight
def knight_moves(board, row, col, is_white):
    moves = []
    captures = []

    knight_moves = [(row - 2, col - 1), (row - 2, col + 1), (row - 1, col - 2), (row - 1, col + 2),
                    (row + 1, col - 2), (row + 1, col + 2), (row + 2, col - 1), (row + 2, col + 1)]

    # Remove moves that are out of bounds
    valid_knight_moves = [(move[0], move[1]) for move in knight_moves if 0 <= move[0] < 8 and 0 <= move[1] < 8]

    # Remove moves that would capture the player's own pieces
    valid_knight_moves = [move for move in valid_knight_moves if board[move[0]][move[1]] == " " or board[move[0]][move[1]].islower() == is_white]

    # Valid captures
    captures = [move for move in valid_knight_moves if board[move[0]][move[1]] != " " and board[move[0]][move[1]].islower() == is_white]

    moves.extend(valid_knight_moves)

    return moves, captures

# Helper function to calculate moves for a bishop
def bishop_moves(board, row, col, is_white):
    moves = []
    captures = []

    # Bishop moves diagonally
    for i in range(1, 8):
        # Top-left diagonal
        if row - i >= 0 and col - i >= 0:
            if board[row - i][col - i] == ' ': # Vacant spaces
                moves.append((row - i, col - i))
            elif board[row - i][col - i].islower() == is_white: # Opposite pieces
                moves.append((row - i, col - i))
                captures.append((row - i, col - i))
                break
            else: # Allied pieces encountered
                break
    for i in range(1, 8):
        # Top-right diagonal
        if row - i >= 0 and col + i < 8:
            if board[row - i][col + i] == ' ':
                moves.append((row - i, col + i))
            elif board[row - i][col + i].islower() == is_white:
                moves.append((row - i, col + i))
                captures.append((row - i, col + i))
                break
            else:
                break
    for i in range(1, 8):
        # Bottom-left diagonal
        if row + i < 8 and col - i >= 0:
            if board[row + i][col - i] == ' ':
                moves.append((row + i, col - i))
            elif board[row + i][col - i].islower() == is_white:
                moves.append((row + i, col - i))
                captures.append((row + i, col - i))
                break
            else:
                break
    for i in range(1, 8):
        # Bottom-right diagonal
        if row + i < 8 and col + i < 8:
            if board[row + i][col + i] == ' ':
                moves.append((row + i, col + i))
            elif board[row + i][col + i].islower() == is_white:
                moves.append((row + i, col + i))
                captures.append((row + i, col + i))
                break
            else:
                break

    return moves, captures

# Helper function to calculate moves for a queen
def queen_moves(board, row, col, is_white):
    moves = []
    captures = []

    # Bishop-like moves
    b_moves, b_captures = bishop_moves(board, row, col, is_white)
    moves.extend(b_moves)
    captures.extend(b_captures)

    # Rook-like moves
    r_moves, r_captures = rook_moves(board, row, col, is_white)
    moves.extend(r_moves)
    captures.extend(r_captures)

    return moves, captures

# Helper function to calculate moves for a king
def king_moves(board, row, col, is_white):
    moves = []
    captures = []

    # King can move in all eight adjacent squares
    king_moves = [(row - 1, col - 1), (row - 1, col), (row - 1, col + 1),
                  (row, col - 1),                     (row, col + 1),
                  (row + 1, col - 1), (row + 1, col), (row + 1, col + 1)]

    # Remove moves that are out of bounds
    valid_king_moves = [move for move in king_moves if 0 <= move[0] < 8 and 0 <= move[1] < 8]

    # Remove moves that would capture the player's own pieces
    valid_king_moves = [move for move in valid_king_moves if board[move[0]][move[1]] == " " or board[move[0]][move[1]].islower() == is_white]

    # Valid captures
    captures = [move for move in valid_king_moves if board[move[0]][move[1]] != " " and board[move[0]][move[1]].islower() == is_white]

    moves.extend(valid_king_moves)

    return moves, captures

# Helper Function to return moves for the selected piece
def calculate_moves(board, row, col, game_history, castle_attributes=None):
    piece = board[row][col]
    moves = []
    captures = []
    special_moves = []

    is_white = piece.isupper() # Check if the piece is white

    if piece.lower() == 'p':  # Pawn
        p_moves, p_captures = pawn_moves(board, row, col, is_white)
        moves.extend(p_moves)
        captures.extend(p_captures)
        if game_history is not None and len(game_history) != 0:
            previous_turn = game_history[-1]
            
            add_enpassant = False
            if is_white and row == 3:
                previous_pawn, previous_start_row, previous_end_row, destination_row = 'p', '1', '3', 2
                add_enpassant = True
            elif not is_white and row == 4:
                previous_pawn, previous_start_row, previous_end_row, destination_row = 'P', '6', '4', 5
                add_enpassant = True
            if add_enpassant:
                start, end = list(previous_turn[0]), list(previous_turn[1])
                # En-passant condition: A pawn moves twice onto a square with an adjacent pawn in the same rank
                if start[0] == previous_pawn and end[0] == previous_pawn and start[1] == previous_start_row and end[1] == previous_end_row \
                    and abs(col - int(end[2])) == 1:
                    special_moves.append((destination_row, int(end[2])))

    elif piece.lower() == 'r':  # Rook
        r_moves, r_captures = rook_moves(board, row, col, is_white)
        moves.extend(r_moves)
        captures.extend(r_captures)

    elif piece.lower() == 'n':  # Knight (L-shaped moves)
        n_moves, n_captures = knight_moves(board, row, col, is_white)
        moves.extend(n_moves)
        captures.extend(n_captures)

    elif piece.lower() == 'b':  # Bishop
        b_moves, b_captures = bishop_moves(board, row, col, is_white)
        moves.extend(b_moves)
        captures.extend(b_captures)

    elif piece.lower() == 'q':  # Queen (Bishop-like + Rook-like moves)
        q_moves, q_captures = queen_moves(board, row, col, is_white)
        moves.extend(q_moves)
        captures.extend(q_captures)

    elif piece.lower() == 'k':  # King
        k_moves, k_captures = king_moves(board, row, col, is_white)
        moves.extend(k_moves)
        captures.extend(k_captures)
        # Eliminates need to deepcopy everywhere and unnecessarily consider special moves
        if castle_attributes is not None:
            # Castling
            queen_castle = True
            king_castle = True
            if is_white:
                moved_king = castle_attributes['white_king_moved']
                left_rook_moved = castle_attributes['left_white_rook_moved']
                right_rook_moved = castle_attributes['right_white_rook_moved']
                king_row = 7
                king_piece = 'K'
            else:
                moved_king = castle_attributes['black_king_moved']
                left_rook_moved = castle_attributes['left_black_rook_moved']
                right_rook_moved = castle_attributes['right_black_rook_moved']
                king_row = 0
                king_piece = 'k'

            if not moved_king:
                if not left_rook_moved:
                    # Empty squares between king and rook
                    if not all(element == ' ' for element in board[king_row][2:4]):
                        queen_castle = False
                    else:
                        # Not moving through/into check and not currently under check
                        temp_boards_and_moves = []
                        for placement_col in [4, 3, 2]:
                            temp_board = [rank[:] for rank in board]
                            temp_moves = game_history.copy()
                            temp_moves.append(output_move(piece, (king_row, 4), king_row, placement_col, ' '))
                            temp_board[king_row][4] = ' '
                            temp_board[king_row][placement_col] = king_piece
                            temp_boards_and_moves.append([temp_board, temp_moves])
                        clear_checks = all(not is_check(temp[0], is_white, temp[1]) for temp in temp_boards_and_moves)
                        if not clear_checks:
                            queen_castle = False
                else:
                    queen_castle = False
                if not right_rook_moved:
                    # Empty squares between king and rook
                    if not all(element == ' ' for element in board[king_row][5:7]):
                        king_castle = False
                    else:
                        # Not moving through/into check and not currently under check
                        temp_boards_and_moves = []
                        for placement_col in [4, 5, 6]:
                            temp_board = [rank[:] for rank in board]
                            temp_moves = game_history.copy()
                            temp_moves.append(output_move(piece, (king_row, 4), king_row, placement_col, ' '))
                            temp_board[king_row][4] = ' '
                            temp_board[king_row][placement_col] = king_piece
                            temp_boards_and_moves.append([temp_board, temp_moves])
                        clear_checks = all(not is_check(temp[0], is_white, temp[1]) for temp in temp_boards_and_moves)
                        if not clear_checks:
                            king_castle = False
                else:
                    king_castle = False
            else:
                queen_castle = False
                king_castle = False

            if queen_castle:
                king_pos = (7, 2) if is_white else (0, 2) 
                special_moves.append(king_pos)
            if king_castle:
                king_pos = (7, 6) if is_white else (0, 6) 
                special_moves.append(king_pos)

    elif piece == ' ':
        return [], [], []
    else:
        return ValueError
    
    return moves, captures, special_moves

## Board State Check Logic
# Helper function to calculate if a board does not have a king
def is_invalid_capture(board, is_color):
    # Find the king's position
    king = 'K' if is_color else 'k'
    king_position = None
    for row in range(8):
        for col in range(8):
            if board[row][col] == king:
                king_position = (row, col)
                break
    if king_position is None:
        return True # Illegal move not allowed for now until turns are implemented
    else:
        return False

# Helper function to search for checks
def is_check(board, is_color, moves):
    # Find the king's position
    king = 'K' if is_color else 'k'
    for row in range(8):
        for col in range(8):
            if board[row][col] == king:
                king_position = (row, col)
                break
    # Check if any opponent's pieces can attack the king
    for row in range(8):
        for col in range(8):
            piece = board[row][col]
            if piece.islower() == is_color and piece != ' ':
                _, captures, _ = calculate_moves(board, row, col, moves)
                if king_position in captures:
                    return True
    return False

# Helper function to search for end-game state
def is_checkmate_or_stalemate(board, is_color, moves):
    possible_moves = 0
    pos_moves = [] # For DEBUG only, TO REMOVE IN FINAL VERSION
    # Consider this as a potential checkmate if under check
    checkmate = is_check(board, is_color, moves)
    # Iterate through all the player's pieces
    for row in range(8):
        for col in range(8):
            piece = board[row][col]
            if piece.isupper() == is_color and piece != ' ':
                other_moves, _, other_specials = calculate_moves(board, row, col, moves)
                # and it will never be the only move left if available
                for move in other_moves:
                    # Try each move and see if it removes the check
                    # Before making the move, create a copy of the board where the piece has moved
                    temp_board = [rank[:] for rank in board]  
                    temp_moves = moves.copy()
                    temp_moves.append(output_move(piece, (row, col), move[0], move[1], temp_board[move[0]][move[1]]))
                    temp_board[move[0]][move[1]] = temp_board[row][col]
                    temp_board[row][col] = ' '
                    if not is_check(temp_board, is_color, temp_moves):
                        possible_moves += 1
                        checkmate = False
                        pos_moves.append([move, row, col]) # For DEBUG only, TO REMOVE IN FINAL VERSION
                # Can implement an if checkmate == True check here for efficiency but it's probably best to accurately update possible_moves
                # En-passants can remove checks
                for move in other_specials:
                    # We never have to try castling moves because you can never castle under check
                    if move not in [(7, 2), (7, 6), (0, 2), (0, 6)]:
                        temp_moves = moves.copy()
                        temp_moves.append(output_move(piece, (row, col), move[0], move[1], temp_board[move[0]][move[1]], 'enpassant'))
                        temp_board[move[0]][move[1]] = temp_board[row][col]
                        temp_board[row][col] = ' '
                        capture_row = 4 if move[0] == 3 else 5
                        temp_board[capture_row][move[1]] = ' '
                        if not is_check(temp_board, is_color, temp_moves):
                            possible_moves += 1
                            checkmate = False
                            pos_moves.append([move, row, col]) # For DEBUG only, TO REMOVE IN FINAL VERSION

    return checkmate, possible_moves

## Drawing Logic
# Helper Function to load chess piece images dynamically
def load_piece_image(piece):
    filename = f'images/{piece}.png'
    img = pygame.image.load(filename)
    img = pygame.transform.smoothscale(img, (GRID_SIZE, GRID_SIZE))

    # Create a transparent surface with the same size as GRID_SIZE x GRID_SIZE
    transparent_surface = pygame.Surface((GRID_SIZE, GRID_SIZE), pygame.SRCALPHA)
    # Add transparency alpha
    transparent_surface.set_alpha(128)

    # Blit the image onto the transparent surface with transparency
    transparent_surface.blit(img, (0, 0))

    return img, transparent_surface

# Helper Function to dynamically generate keys between board conventions and image naming to avoid a hardcoded mapping
def name_keys(color, piece):
    piece_key = piece
    if color == 'w':
        piece_key = piece_key.upper()
    return piece_key, color + piece 

# Helper Function to get the chessboard coordinates from mouse click coordinates
def get_board_coordinates(x, y):
    col = x // GRID_SIZE
    row = y // GRID_SIZE
    return row, col

# Helper Function to draw a temporary rectangle with only an outline on a square
def draw_hover_outline(window, row, col):
    hover_outline = pygame.Surface((GRID_SIZE, GRID_SIZE), pygame.SRCALPHA)
    HOVER_OUTLINE_COLOR = HOVER_OUTLINE_COLOR_WHITE if (row + col) % 2 == 0 else HOVER_OUTLINE_COLOR_BLACK
    pygame.draw.rect(hover_outline, HOVER_OUTLINE_COLOR, (0, 0, GRID_SIZE, GRID_SIZE), 5)
    window.blit(hover_outline, (col * GRID_SIZE, row * GRID_SIZE))

# Helper Function to draw the chess pieces
def draw_pieces(window, board, pieces):
    for row in range(8):
        for col in range(8):
            piece = board[row][col]
            if piece != ' ':
                window.blit(pieces[piece], (col * GRID_SIZE, row * GRID_SIZE))

# Helper Function to draw transparent circles on half of the tiles
def draw_transparent_circles(valid_moves, valid_captures, valid_specials):
    free_moves = [move for move in valid_moves if move not in valid_captures]
    transparent_surface = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    for row, col in free_moves:
        square_x = col * GRID_SIZE + GRID_SIZE // 2
        square_y = row * GRID_SIZE + GRID_SIZE // 2
        pygame.draw.circle(transparent_surface, TRANSPARENT_CIRCLES, (square_x, square_y), GRID_SIZE * 0.15)
    for row, col in valid_captures:
        square_x = col * GRID_SIZE + GRID_SIZE // 2
        square_y = row * GRID_SIZE + GRID_SIZE // 2
        pygame.draw.circle(transparent_surface, TRANSPARENT_CIRCLES, (square_x, square_y), GRID_SIZE * 0.5, 8)
    for row, col in valid_specials:
        square_x = col * GRID_SIZE + GRID_SIZE // 2
        square_y = row * GRID_SIZE + GRID_SIZE // 2
        pygame.draw.circle(transparent_surface, TRANSPARENT_SPECIAL_CIRCLES, (square_x, square_y), GRID_SIZE * 0.15)

    return transparent_surface

# Helper Function to highlight selected squares
def draw_highlight(window, row, col):
    square_highlight = pygame.Surface((GRID_SIZE, GRID_SIZE), pygame.SRCALPHA)
    HIGHLIGHT_COLOR = HIGHLIGHT_WHITE if (row + col) % 2 == 0 else HIGHLIGHT_BLACK
    pygame.draw.rect(square_highlight, HIGHLIGHT_COLOR, (0, 0, GRID_SIZE, GRID_SIZE))
    window.blit(square_highlight, (col * GRID_SIZE, row * GRID_SIZE))

# Helper Function for drawing the board
def draw_board(params):
    window = params['window']
    board = params['board']
    chessboard = params['chessboard']
    selected_piece = params['selected_piece']
    current_position = params['current_position']
    previous_position = params['previous_position']
    valid_moves = params['valid_moves']
    valid_captures = params['valid_captures']
    valid_specials = params['valid_specials']
    pieces = params['pieces']
    hovered_square = params['hovered_square']
    selected_piece_image = params['selected_piece_image']
    
    # Draw the reference chessboard (constructed only once)
    window.blit(chessboard, (0, 0))

    # Highlight selected squares
    if selected_piece is not None:
        draw_highlight(window, selected_piece[0], selected_piece[1])
    if current_position is not None:
        draw_highlight(window, current_position[0], current_position[1])
    if previous_position is not None:
        draw_highlight(window, previous_position[0], previous_position[1])

    # Perhaps this will be moved to constants or depend on player turn or something
    # Blit the coordinates onto the reference image
    coordinate_surface = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    for i, letter in enumerate(letter_surfaces):
        square_y = 8 * GRID_SIZE - FONT_SIZE // 2 - TEXT_OFFSET
        square_x = (1 + i) * GRID_SIZE - FONT_SIZE // 2
        coordinate_surface.blit(letter, (square_x, square_y))

    for i, number in enumerate(number_surfaces):
        square_x = 5
        square_y = (7 - i) * GRID_SIZE + TEXT_OFFSET
        coordinate_surface.blit(number, (square_x, square_y))

    # Draw coordinates after highlights
    window.blit(coordinate_surface, (0, 0))

    # Highlight valid move squares
    transparent_circles = draw_transparent_circles(valid_moves, valid_captures, valid_specials)
    window.blit(transparent_circles, (0, 0))
    
    # Draw the chess pieces on top of the reference board
    draw_pieces(window, board, pieces)

    # Draw the hover outline if a square is hovered
    if hovered_square is not None:
        draw_hover_outline(window, hovered_square[0], hovered_square[1])

    # On mousedown and a piece is selected draw a transparent copy of the piece
    # Draw after outline and previous layers
    if selected_piece_image is not None:
        x, y = pygame.mouse.get_pos()
        # Calculate the position to center the image on the mouse
        image_x = x - GRID_SIZE // 2
        image_y = y - GRID_SIZE // 2
        window.blit(selected_piece_image, (image_x, image_y))

# Pawn Promotion Button
class Pawn_Button:
    def __init__(self, x, y, width, height, piece):
        self.rect = pygame.Rect(x, y, width, height)
        self.scale_ratio = 1.5
        self.scaled_width = int(self.rect.width * self.scale_ratio)
        self.scaled_height = int(self.rect.height * self.scale_ratio)
        self.scaled_x = self.rect.centerx - self.scaled_width // 2
        self.scaled_y = self.rect.centery - self.scaled_height // 2
        self.is_hovered = False
        self.piece = piece

    def check_hover(self, pos):
        self.is_hovered = self.rect.collidepoint(pos)

    def handle_event(self, event):
        if event.type == pygame.MOUSEMOTION:
                self.check_hover(event.pos)

# Helper Function for displaying and running until a pawn is promoted 
def display_promotion_options(draw_board_params, window, row, col, pieces, promotion_required, game):
    new_current_position, new_previous_position = None, None

    # Draw buttons onto a surface
    if row == 0:
        button_x = col * GRID_SIZE
        button_y_values = [i * GRID_SIZE for i in [0, 1, 2, 3]]
        promotion_buttons = [
            Pawn_Button(button_x, button_y_values[0], GRID_SIZE, GRID_SIZE, 'Q'),
            Pawn_Button(button_x, button_y_values[1], GRID_SIZE, GRID_SIZE, 'R'),
            Pawn_Button(button_x, button_y_values[2], GRID_SIZE, GRID_SIZE, 'B'),
            Pawn_Button(button_x, button_y_values[3], GRID_SIZE, GRID_SIZE, 'N'),
        ]
    elif row == 7:
        button_x = col * GRID_SIZE
        button_y_values = [i * GRID_SIZE for i in [7, 6, 5, 4]]
        promotion_buttons = [
            Pawn_Button(button_x, button_y_values[0], GRID_SIZE, GRID_SIZE, 'q'),
            Pawn_Button(button_x, button_y_values[1], GRID_SIZE, GRID_SIZE, 'r'),
            Pawn_Button(button_x, button_y_values[2], GRID_SIZE, GRID_SIZE, 'b'),
            Pawn_Button(button_x, button_y_values[3], GRID_SIZE, GRID_SIZE, 'n'),
        ]
    
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
            if event.type == pygame.KEYDOWN:

                # Undo move
                if event.key == pygame.K_u:
                    # Update current and previous position highlighting
                    new_current_position, new_previous_position = game.undo_move()
                    promotion_required = False
        
        # Clear the screen
        window.fill((0, 0, 0))

        # Draw the board
        draw_board(draw_board_params)
        
        # Darken the screen
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 128))

        # Blit the overlay surface onto the main window
        window.blit(overlay, (0, 0))

        # Draw buttons and update the display
        for button in promotion_buttons:
            img = pieces[button.piece]
            img_x, img_y = button.rect.x, button.rect.y
            if button.is_hovered:
                img = pygame.transform.smoothscale(img, (GRID_SIZE * 1.5, GRID_SIZE * 1.5))
                img_x, img_y = button.scaled_x, button.scaled_y
            window.blit(img, (img_x, img_y))

        pygame.display.flip()
    
    return new_current_position, new_previous_position