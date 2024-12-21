import pygame
from .constants import *
from .helpers import *

def initialize_game(drawing_settings, board, filename, current_theme, pieces): 
    virtual_screen = pygame.Surface((current_theme.WIDTH, current_theme.HEIGHT))

    virtual_screen.fill((0, 0, 0))
    draw_board({
        'window': virtual_screen,
        'theme': current_theme,
        'board': board,
        'starting_player': True,
        'suggestive_stage': False,
        'latest': True,
        'drawing_settings': drawing_settings,
        'selected_piece': None,
        'white_current_position': None,
        'white_previous_position': None,
        'black_current_position': None,
        'black_previous_position': None,
        'valid_moves': [],
        'valid_captures': [],
        'valid_specials': [],
        'pieces': pieces,
        'hovered_square': None,
        'white_active_position': None,
        'black_active_position': None,
        'white_selected_piece_image': None,
        'black_selected_piece_image': None,
        'selected_piece_image': None
    })

    pygame.image.save(virtual_screen, filename)
    return
    
def load_piece_image_with_directory(piece, GRID_SIZE, dir):
    filename = f'{dir}/images/{piece}.png'
    img = pygame.image.load(filename)
    img = pygame.transform.smoothscale(img, (GRID_SIZE, GRID_SIZE))

    # Create a transparent surface with the same size as GRID_SIZE x GRID_SIZE
    transparent_surface = pygame.Surface((GRID_SIZE, GRID_SIZE), pygame.SRCALPHA)
    # Add transparency alpha
    transparent_surface.set_alpha(128)

    # Blit the image onto the transparent surface with transparency
    transparent_surface.blit(img, (0, 0))

    return img, transparent_surface

def save_screenshot(FEN, filename):
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

    current_theme = Theme()
    # Load the chess pieces dynamically
    pieces = {}
    transparent_pieces = {}
    for color in ['w', 'b']:
        for piece_lower in ['r', 'n', 'b', 'q', 'k', 'p']:
            piece_key, image_name_key = name_keys(color, piece_lower)
            pieces[piece_key], transparent_pieces[piece_key] = load_piece_image_with_directory(image_name_key, current_theme.GRID_SIZE, "main/screenshot")

    outlines = king_outlines(transparent_pieces['k'])

    current_theme.INVERSE_PLAYER_VIEW = False

    pygame.init()
    pygame.display.init()
    pygame.display.set_mode((1, 1), pygame.NOFRAME)
    drawing_settings = {
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
        "check_black": False
    }

    initialize_game(drawing_settings, game_board, filename, current_theme, pieces)

if __name__ == "__main__":
    # FEN = 
    # filename = 
    save_screenshot()