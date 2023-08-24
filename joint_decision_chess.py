import pygame
import sys
# Consider first publishing a version that is the classical variant of chess. Decide when the two versions branch off.
# Initialize Pygame
pygame.init()

# Constants
WIDTH, HEIGHT = 800, 800
GRID_SIZE = WIDTH // 8
WHITE_SQUARE = (200, 150, 100)
BLACK_SQUARE = (240, 220, 130)
# TODO try drawing a transparent circle
transparent_image = pygame.transform.scale(pygame.image.load("./images/Circle_with_Central_Point.png"), (GRID_SIZE, GRID_SIZE))

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

## TODO is in check function

# Function to load chess piece images dynamically
def load_piece_image(piece):
    filename = f'images/{piece}.png'
    img = pygame.image.load(filename)
    return pygame.transform.scale(img, (GRID_SIZE, GRID_SIZE))

# Function to dynamically generate keys between board conventions and image naming to avoid a hardcoded mapping
def name_keys(color, piece):
    piece_key = piece
    if color == 'w':
        piece_key = piece_key.upper()
    return piece_key, color + piece 

# Load the chess pieces dynamically
pieces = {}
for color in ['w', 'b']:
    for piece in ['r', 'n', 'b', 'q', 'k', 'p']:
        piece_key, image_name_key = name_keys(color, piece)
        pieces[piece_key] = load_piece_image(image_name_key)

# Load the chessboard as a reference image (drawn only once)
chessboard = pygame.Surface((WIDTH, HEIGHT))
for row in range(8):
    for col in range(8):
        color = WHITE_SQUARE if (row + col) % 2 == 0 else BLACK_SQUARE
        pygame.draw.rect(chessboard, color, (col * GRID_SIZE, row * GRID_SIZE, GRID_SIZE, GRID_SIZE))

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

# TODO promotion
# Helper function to calculate moves for a pawn
def pawn_moves(board, row, col, is_white):
    moves = []

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
    if row > 0 and col < 7 and board[row + forwards][col + 1] != ' ' \
        and board[row + forwards][col + 1].islower() == is_white:
        moves.append((row + forwards, col + 1))
    # Edge case diagonal captures
    if row > 0 and col == 7 and board[row + forwards][col - 1] != ' ' \
        and board[row + forwards][col - 1].islower() == is_white:
        moves.append((row + forwards, col - 1))
    if row > 0 and col == 0 and board[row + forwards][col + 1] != ' ' \
        and board[row + forwards][col + 1].islower() == is_white:
        moves.append((row + forwards, col + 1))

    return moves

# Helper function to calculate moves for a rook
def rook_moves(board, row, col, is_white):
    moves = []

    # Rook moves horizontally
    for i in range(col + 1, 8):
        if board[row][i] == ' ':
            moves.append((row, i))
        else:
            if board[row][i].islower() == is_white:
                moves.append((row, i))
            break

    for i in range(col - 1, -1, -1):
        if board[row][i] == ' ':
            moves.append((row, i))
        else:
            if board[row][i].islower() == is_white:
                moves.append((row, i))
            break

    # Rook moves vertically
    for i in range(row + 1, 8):
        if board[i][col] == ' ':
            moves.append((i, col))
        else:
            if board[i][col].islower() == is_white:
                moves.append((i, col))
            break

    for i in range(row - 1, -1, -1):
        if board[i][col] == ' ':
            moves.append((i, col))
        else:
            if board[i][col].islower() == is_white:
                moves.append((i, col))
            break
    return moves

# Helper function to calculate moves for a knight
def knight_moves(board, row, col, is_white):
    moves = []

    knight_moves = [(row - 2, col - 1), (row - 2, col + 1), (row - 1, col - 2), (row - 1, col + 2),
                    (row + 1, col - 2), (row + 1, col + 2), (row + 2, col - 1), (row + 2, col + 1)]

    # Remove moves that are out of bounds
    valid_knight_moves = [(move[0], move[1]) for move in knight_moves if 0 <= move[0] < 8 and 0 <= move[1] < 8]

    # Remove moves that would capture the player's own pieces
    valid_knight_moves = [move for move in valid_knight_moves if board[move[0]][move[1]] == " " or board[move[0]][move[1]].islower() == is_white]

    moves.extend(valid_knight_moves)

    return moves

# Helper function to calculate moves for a bishop
def bishop_moves(board, row, col, is_white):
    moves = []

    # Bishop moves diagonally
    for i in range(1, 8):
        # Top-left diagonal
        if row - i >= 0 and col - i >= 0:
            if board[row - i][col - i] == ' ': # Vacant spaces
                moves.append((row - i, col - i))
            elif board[row - i][col - i].islower() == is_white: # Opposite pieces
                moves.append((row - i, col - i))
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
                break
            else:
                break

    return moves

# Helper function to calculate moves for a queen
def queen_moves(board, row, col, is_white):
    moves = []

    # Bishop-like moves
    moves.extend(bishop_moves(board, row, col, is_white))

    # Rook-like moves
    moves.extend(rook_moves(board, row, col, is_white))

    return moves

# Helper function to calculate moves for a king
def king_moves(board, row, col, is_white):
    moves = []

    # King can move in all eight adjacent squares
    king_moves = [(row - 1, col - 1), (row - 1, col), (row - 1, col + 1),
                  (row, col - 1),                     (row, col + 1),
                  (row + 1, col - 1), (row + 1, col), (row + 1, col + 1)]

    # Remove moves that are out of bounds
    valid_king_moves = [move for move in king_moves if 0 <= move[0] < 8 and 0 <= move[1] < 8]

    # Remove moves that would capture the player's own pieces
    valid_king_moves = [move for move in valid_king_moves if board[move[0]][move[1]] == " " or board[move[0]][move[1]].islower() == is_white]

    moves.extend(valid_king_moves)

    return moves

# Function to return moves for the selected piece
def calculate_moves(board, row, col):
    piece = board[row][col]
    moves = []

    is_white = piece.isupper() # Check if the piece is white
    is_black = piece.islower() # Check if the piece is black

    if piece.lower() == 'p':  # Pawn
        moves.extend(pawn_moves(board, row, col, is_white))

    elif piece.lower() == 'r':  # Rook
        moves.extend(rook_moves(board, row, col, is_white))

    elif piece.lower() == 'n':  # Knight (L-shaped moves)
        moves.extend(knight_moves(board, row, col, is_white))

    elif piece.lower() == 'b':  # Bishop
        moves.extend(bishop_moves(board, row, col, is_white))

    elif piece.lower() == 'q':  # Queen (Bishop-like + Rook-like moves)
        moves.extend(queen_moves(board, row, col, is_white))

    elif piece.lower() == 'k':  # King
        moves.extend(king_moves(board, row, col, is_white))
    elif piece == ' ':
        return []
    else:
        return ValueError
    
    return moves

def main():
    running = True
    # Variable to store the currently selected piece
    selected_piece = None
    valid_moves = []

    # Main game loop
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.MOUSEBUTTONDOWN:
                x, y = pygame.mouse.get_pos()
                row, col = get_board_coordinates(x, y)
                piece = board[row][col]

                if not selected_piece:
                    if piece != ' ':
                        selected_piece = (row, col)
                        valid_moves = calculate_moves(board, row, col)
                else:
                    # Implement logic to check if the clicked square is a valid move
                    if (row, col) in valid_moves:
                        # Move the piece
                        # The following logic will later change for my variant
                        board[row][col] = board[selected_piece[0]][selected_piece[1]]
                        board[selected_piece[0]][selected_piece[1]] = ' '
                        selected_piece = None
                        valid_moves = []
                    elif (row, col) == selected_piece:
                        selected_piece = None
                        valid_moves = []
                    else:
                        if piece != ' ':
                            selected_piece = (row, col)
                            valid_moves = calculate_moves(board, row, col)
        # Clear the screen
        window.fill((0, 0, 0))

        # Draw the reference chessboard (constructed only once)
        window.blit(chessboard, (0, 0))

        # Highlight valid move squares
        for move_row, move_col in valid_moves:
            window.blit(transparent_image, (move_col * GRID_SIZE, move_row * GRID_SIZE))

        # Draw the chess pieces on top of the reference board
        draw_pieces()

        pygame.display.flip()

    # Quit Pygame
    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()