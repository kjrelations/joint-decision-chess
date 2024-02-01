import pygame
import sys
from constants import *
from helpers import *

pygame.init()

current_theme = Theme()

with open('themes.json', 'r') as file:
    themes = json.load(file)

pygame.display.init()
pygame.display.set_mode((1, 1), pygame.NOFRAME)
virtual_screen = pygame.Surface((current_theme.WIDTH, current_theme.HEIGHT))

# Load the chess pieces dynamically
pieces = {}
transparent_pieces = {}
for color in ['w', 'b']:
    for piece_lower in ['r', 'n', 'b', 'q', 'k', 'p']:
        piece_key, image_name_key = name_keys(color, piece_lower)
        pieces[piece_key], transparent_pieces[piece_key] = load_piece_image(image_name_key, current_theme.GRID_SIZE)

outlines = king_outlines(transparent_pieces['k'])

def initialize_game(drawing_settings, board): 
    virtual_screen.fill((0, 0, 0))
    draw_board({
        'window': virtual_screen,
        'theme': current_theme,
        'board': board,
        'drawing_settings': drawing_settings,
        'selected_piece': None,
        'current_position': None,
        'previous_position': None,
        'right_clicked_squares': [],
        'drawn_arrows': [],
        'valid_moves': [],
        'valid_captures': [],
        'valid_specials': [],
        'pieces': pieces,
        'hovered_square': None,
        'selected_piece_image': None
    })

    pygame.image.save(virtual_screen, "screenshot.png") # custom name: user_dt.png later
    return
    
def main():
    if len(sys.argv) != 2:
        print("Usage: python save_image.py <FEN>")
        sys.exit(1)

    FEN = sys.argv[1]
    board = FEN.split("/")
    game_board = []
    for row in board:
        r = []
        for column_s in row:
            if column_s.isdigit():
                empty = [" "] * int(column_s)
                r.extend(empty)
            else:
                r.append(column_s)
        game_board.append(r)

    current_theme.INVERSE_PLAYER_VIEW = False
    drawing_settings = {
        "chessboard": generate_chessboard(current_theme),
        "coordinate_surface": generate_coordinate_surface(current_theme),
        "theme_index": 0,
        "king_outlines": outlines,
        "checkmate_white": False,
        "check_white": False,
        "checkmate_black": False,
        "check_black": False
    }

    initialize_game(drawing_settings, game_board)

if __name__ == "__main__":
    main()