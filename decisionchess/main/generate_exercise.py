# Run from main directory with python -m main.generate_exercise
import os
import django
import json

# Set the DJANGO_SETTINGS_MODULE environment variable
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "decisionchess.settings")

# Configure Django settings
django.setup()

# Given the above the model import should work and settings can be accessed
from main.models import EmbeddedGames

def translate_into_FEN(board):
    FEN = ''
    for row in board:
        row_str, empty_count = '', 0
        for i, position in enumerate(row):
            if position == ' ':
                empty_count += 1
                if i == len(row) - 1 and position == ' ':
                    row_str += str(empty_count)
                    empty_count = 0
            else:
                if empty_count:
                    row_str += str(empty_count)
                    empty_count = 0
                row_str += position
        FEN += row_str + "/"
    return FEN[:-1]

if __name__ == "__main__":
    board = [
        ['r', 'n', 'b', 'q', 'k', 'b', 'n', 'r'],
        ['p', 'p', 'p', ' ', 'p', ' ', 'p', 'p'],
        [' ', ' ', ' ', ' ', ' ', ' ', ' ', ' '],
        [' ', ' ', ' ', ' ', 'n', ' ', ' ', ' '],
        [' ', ' ', ' ', ' ', ' ', ' ', ' ', ' '],
        [' ', ' ', ' ', ' ', ' ', ' ', ' ', ' '],
        ['P', 'P', 'P', 'P', 'P', 'P', 'P', 'P'],
        ['R', 'N', 'B', 'Q', 'K', 'B', 'N', 'R']
    ]
    moves = [
        [[0, 4, 3, 4, False], [7, 3, 4, 3, False]]
    ]
    indexed_moves = {
        "1": []
    }
    indexed_moves_json = json.dumps(indexed_moves)
    embedded_game = EmbeddedGames(
        name="Knight Moves",
        FEN=translate_into_FEN(board),
        gametype="Standard",
        indexed_moves=indexed_moves_json
    )
    embedded_game.save()