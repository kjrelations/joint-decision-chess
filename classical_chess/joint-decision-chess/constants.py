import pygame

class Theme:
    def __init__(self):
        # Constants
        self.NAME = 'Standard'
        self.WIDTH, self.HEIGHT = 800, 800
        self.GRID_SIZE = self.WIDTH // 8
        self.WHITE_SQUARE = (255, 230, 155)
        self.BLACK_SQUARE = (140, 215, 230)
        self.TRANSPARENT_CIRCLES = (255, 180, 155, 160)
        self.TRANSPARENT_SPECIAL_CIRCLES = (140, 95, 80, 160)
        self.HOVER_OUTLINE_COLOR_WHITE = (255, 240, 200)
        self.HOVER_OUTLINE_COLOR_BLACK = (200, 235, 245)
        self.TEXT_OFFSET = 7
        self.FONT_SIZE = 36
        self.HIGHLIGHT_WHITE = (255, 215, 105)
        self.HIGHLIGHT_BLACK = (75, 215, 230)
        self.HIGHLIGHT_WHITE_BLACK = (170, 144, 70)
        self.HIGHLIGHT_BLACK_BLACK = (43, 124, 132)
        self.HIGHLIGHT_WHITE_RCLICK = (255, 100, 70)
        self.HIGHLIGHT_BLACK_RCLICK = (150, 60, 40)
        self.HIGHLIGHT_WHITE_RCLICK_OPPONENT = (126, 171, 116)
        self.HIGHLIGHT_BLACK_RCLICK_OPPONENT = (81, 137, 68)
        self.ARROW_WHITE = (235, 180, 50, 150)
        self.ARROW_BLACK = (0, 100, 100, 150)
        self.ARROW_BODY_WIDTH = 20
        self.ARROW_HEAD_HEIGHT = 35
        self.ARROW_HEAD_WIDTH = 48
        self.INVERSE_PLAYER_VIEW = False

    def apply_theme(self, theme, inverse_view):
        self.NAME = theme.get("name", self.NAME)
        self.WIDTH, self.HEIGHT = 800, 800
        self.GRID_SIZE = self.WIDTH // 8
        self.WHITE_SQUARE = theme.get("white_square", self.WHITE_SQUARE)
        self.BLACK_SQUARE = theme.get("black_square", self.BLACK_SQUARE)
        self.TRANSPARENT_CIRCLES = theme.get("transparent_circles", self.TRANSPARENT_CIRCLES)
        self.TRANSPARENT_SPECIAL_CIRCLES = theme.get("transparent_special_circles", self.TRANSPARENT_SPECIAL_CIRCLES)
        self.HOVER_OUTLINE_COLOR_WHITE = theme.get("hover_outline_color_white", self.HOVER_OUTLINE_COLOR_WHITE)
        self.HOVER_OUTLINE_COLOR_BLACK = theme.get("hover_outline_color_black", self.HOVER_OUTLINE_COLOR_BLACK)
        self.TEXT_OFFSET = theme.get("text_offset", self.TEXT_OFFSET)
        self.FONT_SIZE = theme.get("font_size", self.FONT_SIZE)
        self.HIGHLIGHT_WHITE = theme.get("highlight_white", self.HIGHLIGHT_WHITE)
        self.HIGHLIGHT_BLACK = theme.get("highlight_black", self.HIGHLIGHT_BLACK)
        self.HIGHLIGHT_WHITE_BLACK = theme.get("highlight_white_black", self.HIGHLIGHT_WHITE_BLACK)
        self.HIGHLIGHT_BLACK_BLACK = theme.get("highlight_black_black", self.HIGHLIGHT_BLACK_BLACK)
        self.HIGHLIGHT_WHITE_RCLICK = theme.get("highlight_white_rclick", self.HIGHLIGHT_WHITE_RCLICK)
        self.HIGHLIGHT_BLACK_RCLICK = theme.get("highlight_black_rclick", self.HIGHLIGHT_BLACK_RCLICK)
        self.HIGHLIGHT_WHITE_RCLICK_OPPONENT = theme.get("highlight_white_rclick_opponent", self.HIGHLIGHT_WHITE_RCLICK_OPPONENT)
        self.HIGHLIGHT_BLACK_RCLICK_OPPONENT = theme.get("highlight_black_rclick_opponent", self.HIGHLIGHT_BLACK_RCLICK_OPPONENT)
        self.ARROW_WHITE = theme.get("arrow_white", self.ARROW_WHITE)
        self.ARROW_BLACK = theme.get("arrow_black", self.ARROW_BLACK)
        self.ARROW_BODY_WIDTH = theme.get("arrow_body_width", self.ARROW_BODY_WIDTH)
        self.ARROW_HEAD_HEIGHT = theme.get("arrow_head_height", self.ARROW_HEAD_HEIGHT)
        self.ARROW_HEAD_WIDTH = theme.get("arrow_head_width", self.ARROW_HEAD_WIDTH)
        self.INVERSE_PLAYER_VIEW = inverse_view

    def __str__(self):
        return self.NAME

# Initialize Pygame to initialize fonts
pygame.init()

# Initialize mixer for sounds
pygame.mixer.init()

# Sound Effects
move_sound = pygame.mixer.Sound('sounds/move.ogg')
capture_sound = pygame.mixer.Sound('sounds/capture.ogg')

pygame.quit()

# Chess board representation (for simplicity, just pieces are represented)
# Our convention is that white pieces are upper case.
new_board = [
    ['r', 'n', 'b', 'q', 'k', 'b', 'n', 'r'],
    ['p', 'p', 'p', 'p', 'p', 'p', 'p', 'p'],
    [' ', ' ', ' ', ' ', ' ', ' ', ' ', ' '],
    [' ', ' ', ' ', ' ', ' ', ' ', ' ', ' '],
    [' ', ' ', ' ', ' ', ' ', ' ', ' ', ' '],
    [' ', ' ', ' ', ' ', ' ', ' ', ' ', ' '],
    ['P', 'P', 'P', 'P', 'P', 'P', 'P', 'P'],
    ['R', 'N', 'B', 'Q', 'K', 'B', 'N', 'R']
]