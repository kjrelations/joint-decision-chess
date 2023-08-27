import pygame
import sys
# Consider first publishing a version that is the classical variant of chess. Decide when the two versions branch off.
# Initialize Pygame
pygame.init()
# Initialize mixer for sounds
pygame.mixer.init()

# Sound Effects
move_sound = pygame.mixer.Sound('sounds/move.mp3')
capture_sound = pygame.mixer.Sound('sounds/capture.mp3')

# Constants
WIDTH, HEIGHT = 800, 800
GRID_SIZE = WIDTH // 8
WHITE_SQUARE = (255, 230, 155)
BLACK_SQUARE = (140, 215, 230)
TRANSPARENT_CIRCLES = (255, 180, 155, 160)
HOVER_OUTLINE_COLOR_WHITE = (255, 240, 200)
HOVER_OUTLINE_COLOR_BLACK = (200, 235, 245)
TEXT_OFFSET = 7
HIGHLIGHT_WHITE = (255, 215, 105)
HIGHLIGHT_BLACK = (75, 215, 230)
PREVIOUS_WHITE = (255, 215, 105)
PREVIOUS_BLACK = (75, 215, 230)

# Coordinate font
FONT_SIZE = 36
font = pygame.font.Font(None, FONT_SIZE)
COORDINATES = ['a','b','c','d','e','f','g','h']
NUMBERS = ['1','2','3','4','5','6','7','8']
letter_surfaces = []
number_surfaces = []
for i, letter in enumerate(COORDINATES):
    SQUARE = WHITE_SQUARE if i % 2 == 0 else BLACK_SQUARE
    letter_surfaces.append(font.render(letter, True, SQUARE))
    number_surfaces.append(font.render(NUMBERS[i], True, SQUARE))

# Chess board representation (for simplicity, just pieces are represented)
# Our convention is that white pieces are upper case.
board = [
    ['r', 'n', 'b', 'q', 'k', 'b', 'n', 'r'],
    ['p', 'p', 'p', 'p', 'p', 'p', 'p', 'p'],
    [' ', ' ', ' ', ' ', ' ', ' ', ' ', ' '],
    [' ', ' ', ' ', ' ', ' ', ' ', ' ', ' '],
    [' ', ' ', ' ', ' ', ' ', ' ', ' ', ' '],
    [' ', ' ', ' ', ' ', ' ', ' ', ' ', ' '],
    ['P', 'P', 'P', 'P', 'P', 'P', 'P', 'P'],
    ['R', 'N', 'B', 'Q', 'K', 'B', 'N', 'R']
]

# Initialize Pygame window
window = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Chess")

# Load the chessboard as a reference image (drawn only once)
chessboard = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
for row in range(8):
    for col in range(8):
        color = WHITE_SQUARE if (row + col) % 2 == 0 else BLACK_SQUARE
        pygame.draw.rect(chessboard, color, (col * GRID_SIZE, row * GRID_SIZE, GRID_SIZE, GRID_SIZE))

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

# Function to draw transparent circles on half of the tiles
def draw_transparent_circles(valid_moves, valid_captures):
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

    return transparent_surface

# Function to draw a temporary rectangle with only an outline on a square
def draw_hover_outline(row, col):
    hover_outline = pygame.Surface((GRID_SIZE, GRID_SIZE), pygame.SRCALPHA)
    HOVER_OUTLINE_COLOR = HOVER_OUTLINE_COLOR_WHITE if (row + col) % 2 == 0 else HOVER_OUTLINE_COLOR_BLACK
    pygame.draw.rect(hover_outline, HOVER_OUTLINE_COLOR, (0, 0, GRID_SIZE, GRID_SIZE), 5)
    window.blit(hover_outline, (col * GRID_SIZE, row * GRID_SIZE))

# Function to highlight selected squares
def draw_highlight(row, col):
    square_highlight = pygame.Surface((GRID_SIZE, GRID_SIZE), pygame.SRCALPHA)
    HIGHLIGHT_COLOR = HIGHLIGHT_WHITE if (row + col) % 2 == 0 else HIGHLIGHT_BLACK
    pygame.draw.rect(square_highlight, HIGHLIGHT_COLOR, (0, 0, GRID_SIZE, GRID_SIZE))
    window.blit(square_highlight, (col * GRID_SIZE, row * GRID_SIZE))

## TODO is in check function

# Function to load chess piece images dynamically
def load_piece_image(piece):
    filename = f'images/{piece}.png'
    img = pygame.image.load(filename)
    img = pygame.transform.scale(img, (GRID_SIZE, GRID_SIZE))

    # Create a transparent surface with the same size as GRID_SIZE x GRID_SIZE
    transparent_surface = pygame.Surface((GRID_SIZE, GRID_SIZE), pygame.SRCALPHA)
    # Add transparency alpha
    transparent_surface.set_alpha(128)

    # Blit the image onto the transparent surface with transparency
    transparent_surface.blit(img, (0, 0))

    return img, transparent_surface

# Function to dynamically generate keys between board conventions and image naming to avoid a hardcoded mapping
def name_keys(color, piece):
    piece_key = piece
    if color == 'w':
        piece_key = piece_key.upper()
    return piece_key, color + piece 

# Load the chess pieces dynamically
pieces = {}
transparent_pieces = {}
for color in ['w', 'b']:
    for piece in ['r', 'n', 'b', 'q', 'k', 'p']:
        piece_key, image_name_key = name_keys(color, piece)
        pieces[piece_key], transparent_pieces[piece_key] = load_piece_image(image_name_key)

# Function to draw the chess pieces
def draw_pieces():
    for row in range(8):
        for col in range(8):
            piece = board[row][col]
            if piece != ' ':
                window.blit(pieces[piece], (col * GRID_SIZE, row * GRID_SIZE))

# Function to get the chessboard coordinates from mouse click coordinates
def get_board_coordinates(x, y):
    col = x // GRID_SIZE
    row = y // GRID_SIZE
    return row, col

class Button:
    def __init__(self, x, y, width, height, piece, callback):
        self.rect = pygame.Rect(x, y, width, height)
        self.scale_ratio = 1.5
        self.scaled_width = int(self.rect.width * self.scale_ratio)
        self.scaled_height = int(self.rect.height * self.scale_ratio)
        self.scaled_x = self.rect.centerx - self.scaled_width // 2
        self.scaled_y = self.rect.centery - self.scaled_height // 2
        self.callback = callback
        self.is_hovered = False
        self.original_rect = self.rect.copy()
        self.piece = piece

    def check_hover(self, pos):
        current = self.is_hovered
        self.is_hovered = self.rect.collidepoint(pos)

    def handle_event(self, event):
        if event.type == pygame.MOUSEMOTION:
                self.check_hover(event.pos)

# TODO Implement "extra" potential moves that occur with blocked pieces of the same color
# so .islower() == is_black and break out of loops, put these into "extra" helper functions
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

# Function to return moves for the selected piece
def calculate_moves(board, row, col):
    piece = board[row][col]
    moves = []
    captures = []

    is_white = piece.isupper() # Check if the piece is white

    if piece.lower() == 'p':  # Pawn
        p_moves, p_captures = pawn_moves(board, row, col, is_white)
        moves.extend(p_moves)
        captures.extend(p_captures)

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

    elif piece == ' ':
        return [], []
    else:
        return ValueError
    
    return moves, captures

def main():
    running = True

    selected_piece = None
    current_position = None
    previous_position = None
    hovered_square = None
    # Boolean stating the first intention of moving a piece
    first_intent = False
    # Lock game state due to pawn promotion
    game_locked = False
    selected_piece_image = None
    promotion_required = False
    promotion_square = None
    valid_moves = []
    valid_captures = []

    left_mouse_button_down = False

    # Function for drawing the board
    def draw_board():
        # Draw the reference chessboard (constructed only once)
        window.blit(chessboard, (0, 0))

        # Highlight selected squares
        if selected_piece is not None:
            draw_highlight(selected_piece[0], selected_piece[1])
        if current_position is not None:
            draw_highlight(current_position[0], current_position[1])
        if previous_position is not None:
            draw_highlight(previous_position[0], previous_position[1])

        # Draw coordinates after highlights
        window.blit(coordinate_surface, (0, 0))

        # Highlight valid move squares
        transparent_circles = draw_transparent_circles(valid_moves, valid_captures)
        window.blit(transparent_circles, (0, 0))
        
        # Draw the chess pieces on top of the reference board
        draw_pieces()

        # Draw the hover outline if a square is hovered
        if hovered_square is not None:
            draw_hover_outline(hovered_square[0], hovered_square[1])

        # On mousedown and a piece is selected draw a transparent copy of the piece
        # Draw after outline and previous layers
        if selected_piece_image is not None:
            x, y = pygame.mouse.get_pos()
            # Calculate the position to center the image on the mouse
            image_x = x - GRID_SIZE // 2
            image_y = y - GRID_SIZE // 2
            window.blit(selected_piece_image, (image_x, image_y))

    def display_promotion_options(row, col, promotion_required):
        
        # Draw buttons onto a surface
        if row == 0:
            button_x = col * GRID_SIZE
            button_y_values = [i * GRID_SIZE for i in [0, 1, 2, 3]]
            promotion_buttons = [
                Button(button_x, button_y_values[0], GRID_SIZE, GRID_SIZE, 'Q', promote_to_piece),
                Button(button_x, button_y_values[1], GRID_SIZE, GRID_SIZE, 'R', promote_to_piece),
                Button(button_x, button_y_values[2], GRID_SIZE, GRID_SIZE, 'B', promote_to_piece),
                Button(button_x, button_y_values[3], GRID_SIZE, GRID_SIZE, 'N', promote_to_piece),
            ]
        elif row == 7:
            button_x = col * GRID_SIZE
            button_y_values = [i * GRID_SIZE for i in [7, 6, 5, 4]]
            promotion_buttons = [
                Button(button_x, button_y_values[0], GRID_SIZE, GRID_SIZE, 'q', promote_to_piece),
                Button(button_x, button_y_values[1], GRID_SIZE, GRID_SIZE, 'r', promote_to_piece),
                Button(button_x, button_y_values[2], GRID_SIZE, GRID_SIZE, 'b', promote_to_piece),
                Button(button_x, button_y_values[3], GRID_SIZE, GRID_SIZE, 'n', promote_to_piece),
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
                            button.callback(row, col, button.piece)
                            promotion_required = False  # Exit promotion state condition
            # Clear the screen
            window.fill((0, 0, 0))

            # Draw the board
            draw_board()
            
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

    def promote_to_piece(row, col, piece):
        # Handle promoting the pawn to the correct colored piece
        board[row][col] = piece

    # TODO right click deselects piece while left clicking
    # Main game loop
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.MOUSEBUTTONDOWN:
                # LIKELY UGLY IMPLEMENTATION
                if event.button == 1:  # Left mouse button
                    left_mouse_button_down = True
                if left_mouse_button_down:
                    x, y = pygame.mouse.get_pos()
                    row, col = get_board_coordinates(x, y)
                    piece = board[row][col]
                    
                    if not selected_piece:
                        if piece != ' ':
                            first_intent = True
                            selected_piece = (row, col)
                            selected_piece_image = transparent_pieces[piece]
                            valid_moves, valid_captures = calculate_moves(board, row, col)
                            if (row, col) != hovered_square:
                                hovered_square = (row, col)
                    else:
                        # Implement logic to check if the clicked square is a valid move
                        if (row, col) in valid_moves:
                            # Move the piece
                            # The following logic will later change for my variant
                            board[row][col] = board[selected_piece[0]][selected_piece[1]]
                            board[selected_piece[0]][selected_piece[1]] = ' '
                            previous_position = (selected_piece[0], selected_piece[1])
                            current_position = (row, col)
                            selected_piece = None
                            selected_piece_image = None
                            if (row, col) in valid_captures:
                                capture_sound.play()
                            else:
                                move_sound.play()
                            valid_moves, valid_captures = [], []
                            # Pawn Promotion
                            if board[row][col].lower() == 'p' and (row == 0 or row == 7):
                                promotion_required = True
                                promotion_square = (row, col)
                        else:
                            if piece != ' ':
                                # If the mouse stays on a square and a piece is clicked a second time 
                                # this ensures that mouseup on this square deselects the piece
                                if (row, col) == selected_piece and first_intent:
                                    first_intent = False
                                    selected_piece_image = transparent_pieces[piece]
                                # Redraw the transparent dragged piece on subsequent clicks
                                if (row, col) == selected_piece and not first_intent:
                                    selected_piece_image = transparent_pieces[piece]
                                if (row, col) != selected_piece:
                                    first_intent = True
                                    selected_piece = (row, col)
                                    selected_piece_image = transparent_pieces[piece]
                                    valid_moves, valid_captures = calculate_moves(board, row, col)
                                    if (row, col) != hovered_square:
                                        hovered_square = (row, col)
                                
            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button == 1:  # Left mouse button
                    left_mouse_button_down = False
                    hovered_square = None
                    selected_piece_image = None
                    # For the second time a mouseup occurs on the same square it deselects it
                    # This can be an arbitrary number of mousedowns later
                    if not first_intent and (row, col) == selected_piece:
                            selected_piece = None
                            valid_moves, valid_captures = [], []
                    # First intent changed to false if mouseup on same square the first time
                    if (row, col) == selected_piece and first_intent:
                        first_intent = not first_intent
                    # Move to valid squares on mouseup
                    if (row, col) in valid_moves:
                        # Move the piece
                        # The following logic will later change for my variant
                        board[row][col] = board[selected_piece[0]][selected_piece[1]]
                        board[selected_piece[0]][selected_piece[1]] = ' '
                        previous_position = (selected_piece[0], selected_piece[1])
                        current_position = (row, col)
                        if (row, col) in valid_captures:
                            capture_sound.play()
                        else:
                            move_sound.play()
                        selected_piece = None
                        # Pawn Promotion
                        if board[row][col].lower() == 'p' and (row == 0 or row == 7):
                            promotion_required = True
                            promotion_square = (row, col)
                        valid_moves, valid_captures = [], []
            elif event.type == pygame.MOUSEMOTION:
                x, y = pygame.mouse.get_pos()
                row, col = get_board_coordinates(x, y)

                # Only draw hover outline when left button is down and a piece is selected
                if left_mouse_button_down:  
                    if (row, col) != hovered_square:
                        hovered_square = (row, col)

        # Clear the screen
        window.fill((0, 0, 0))

        # Draw the board
        draw_board()

        if promotion_required:
            # Lock the game state (disable other input)
            
            # Display an overlay or popup with promotion options
            display_promotion_options(promotion_square[0], promotion_square[1], promotion_required)
            promotion_required = False
            # Remove the overlay or popup by redrawing the board
            window.fill((0, 0, 0))
            draw_board()

        pygame.display.flip()

    # Quit Pygame
    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()