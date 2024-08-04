import pygame
import sys
import asyncio
import json
import copy
from constants import *

## General Helpers
# Helper function to dynamically generate keys between board conventions and image naming to avoid a hardcoded mapping
def name_keys(color, piece):
    piece_key = piece
    if color == 'w':
        piece_key = piece_key.upper()
    return piece_key, color + piece 

# Helper function to load chess piece images dynamically and output a transparent version as well
def load_piece_image(piece, GRID_SIZE):
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

# Helper function to create a blurred edge surface
def blur_surface(surface):
    # Create a temporary surface to hold the blurred result
    temp_surface = surface.copy()
    width, height = surface.get_size()

    for y in range(height):
        for x in range(width):
            # Average color values of neighboring pixels
            color_sum = [0, 0, 0, 0]
            total_pixels = 0
            for dy in range(-2, 3):
                for dx in range(-2, 3):
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < width and 0 <= ny < height:
                        pixel_color = surface.get_at((nx, ny))
                        color_sum[0] += pixel_color[0]
                        color_sum[1] += pixel_color[1]
                        color_sum[2] += pixel_color[2]
                        color_sum[3] += pixel_color[3]
                        total_pixels += 1
            
            # Calculate the average color
            average_color = (
                color_sum[0] // total_pixels,
                color_sum[1] // total_pixels,
                color_sum[2] // total_pixels,
                color_sum[3] // total_pixels
            )
            temp_surface.set_at((x, y), average_color)
    
    # Update the original surface with the blurred result
    surface.blit(temp_surface, (0, 0))
    
    return surface

# Check and checkmate outlines
def king_outlines(king_image):
    # TODO get colors from current theme
    check_color = (111, 230, 70)
    checkmate_color = (255, 0, 0)
    check_surface = king_image.copy()
    checkmate_surface = king_image.copy()

    mask = pygame.mask.from_surface(king_image)

    king_height = king_image.get_height()
    king_width = king_image.get_width()
    for y in range(king_height):
        for x in range(king_width):
            # TODO add outline width param for this
            if mask.get_at((x, y)) or \
               (x + 3 <= king_width - 1 and mask.get_at((x + 3, y))) or \
               (y + 3 <= king_height - 1 and mask.get_at((x, y + 3))) or \
               (x - 3 >= 0 and mask.get_at((x - 3, y ))) or \
               (y - 3 >= 0 and mask.get_at((x, y - 3))):
                for offset in range(3):
                    check_surface.set_at((x - offset, y), check_color)
                    check_surface.set_at((x + offset, y), check_color)
                    check_surface.set_at((x, y - offset), check_color)
                    check_surface.set_at((x, y + offset), check_color)
                    checkmate_surface.set_at((x - offset, y), checkmate_color)
                    checkmate_surface.set_at((x + offset, y), checkmate_color)
                    checkmate_surface.set_at((x, y - offset), checkmate_color)
                    checkmate_surface.set_at((x, y + offset), checkmate_color)
                
    check_surface = blur_surface(check_surface)
    checkmate_surface = blur_surface(checkmate_surface)
    return [check_surface, checkmate_surface]

# Helper for showing debug print statements
def print_d(*args, debug=False, **kwargs):
    if debug:
        print(*args, **kwargs)
    else:
        return

# Helper function for generating bespoke Game moves
def output_move(piece, selected_piece, new_row, new_col, potential_capture, priority, special_string= ''):
    return [piece+str(selected_piece[0])+str(selected_piece[1]), piece+str(new_row)+str(new_col), potential_capture, priority, special_string]

# Helper function for translating a simple FEN into a board position
def translate_FEN_into_board(FEN):
    board = []
    FEN_rows = FEN.split('/')
    for row in FEN_rows:
        new_row = []
        for position in row:
            if position.isdigit():
                new_row.extend([' '] * int(position))
            else:
                new_row.append(position)
        board.append(new_row)
    return board

# Helper function for loading a historic game parameters from sessionStorage values
def load_historic_game(json_game):
    starting_player = True
    # Would depend on starting for games that start at a different position
    whites_turn = len(json_game["comp_moves"]) % 2 == 0

    move = json_game["comp_moves"][-1]
    prev, curr = list(move[0]), list(move[1])
    prev_row, prev_col = int(prev[1]), int(prev[2])
    curr_row, curr_col = int(curr[1]), int(curr[2])
    previous_position = (prev_row, prev_col)
    current_position = (curr_row, curr_col)

    _castle_attributes = {
        'white_king_moved' : [False, None],
        'left_white_rook_moved' : [False, None],
        'right_white_rook_moved' : [False, None],
        'black_king_moved' : [False, None],
        'left_black_rook_moved' : [False, None],
        'right_black_rook_moved' : [False, None]
    }

    for move_index, comp_move in enumerate(json_game["comp_moves"]):
        piece = comp_move[0][0]
        prev_pos = (int(comp_move[0][1]), int(comp_move[0][2]))
        if comp_move[3] == 'castle':
            side = 'left' if comp_move[1][2] == '2' else 'right'
            _castle_attributes['white_king_moved' if piece == 'K' else 'black_king_moved'] = [True, move_index]
            if side == 'left':
                _castle_attributes['left_white_rook_moved' if piece == 'K' else 'left_black_rook_moved'] = [True, move_index]
            else:
                _castle_attributes['right_white_rook_moved' if piece == 'K' else 'right_black_rook_moved'] = [True, move_index]
        if piece == 'K' and not _castle_attributes['white_king_moved'][0]:
            _castle_attributes['white_king_moved'] = [True, move_index]
        elif piece == 'k' and not _castle_attributes['black_king_moved'][0]:
            _castle_attributes['black_king_moved'] = [True, move_index]
        elif piece == 'R' and prev_pos in [(7, 0), (7, 7)]:
            _castle_attributes['left_black_rook_moved' if prev_pos == (7, 0) else 'right_black_rook_moved'] = [True, move_index]
        elif piece == 'r' and prev_pos in [(0, 0), (0, 7)]:
            _castle_attributes['left_white_rook_moved' if prev_pos == (0, 0) else 'right_white_rook_moved'] = [True, move_index]

    game_param_dict = {
        "whites_turn": whites_turn,
        "board": translate_FEN_into_board(json_game["FEN_final_pos"]),
        "moves": json_game["comp_moves"],
        "alg_moves": json_game["alg_moves"],
        "castle_attributes": _castle_attributes,
        "current_position": current_position,
        "previous_position": previous_position,
        "board_states": {},
        "max_states": 500,
        "end_position": True,
        "forced_end": json_game["forced_end"],
        "_debug": False,
        "_starting_player": starting_player,
        "_move_undone": False,
        "_sync": True
    }
    return game_param_dict

# Helper for playing sound
def handle_play(window, sound):
    muted = window.sessionStorage.getItem('muted')
    muted = json.loads(muted)
    if not muted:
        sound.play()

# Helper for reading text file key value pairs
def load_keys(file_path):
    keys = {}
    with open(file_path, 'r') as file:
        lines = file.readlines()
        for line in lines:
            parts = line.strip().split('_')
            if len(parts) == 2:
                key, value = parts
                keys[key] = value
    return keys

# Helper for logging errors
def log_err_and_print(e, window):
    exc_str = str(e).replace("'", "\\x27").replace('"', '\\x22')
    js_code = f"console.log('{exc_str}')"
    window.eval(js_code)

# Helper for sending a reset signal to the node and web values
def reset_request(request, init, node, client_state_actions, window):
    if request == "draw":
        request_name, accept_reset, deny_reset, request_received = \
            "draw_request", "draw_accept_reset", "draw_deny_reset", "draw_offer_received"
        request_sent, offer_action, offer_reset = "draw_offer_sent", "draw_offer", "draw_offer_reset"
    elif request == "undo":
        request_name, accept_reset, deny_reset, request_received = \
            "undo_request", "undo_accept_reset", "undo_deny_reset", "undo_received"
        request_sent, offer_action, offer_reset = "undo_sent", "undo", "undo_reset"
    else:
        return
    
    request_value = window.sessionStorage.getItem(request_name)
    try:
        request_value = json.loads(request_value)
    except (json.JSONDecodeError, ValueError):
        request_value = False
    if not init["sent"] and request_value:
        reset_data = {node.CMD: "reset"}
        node.tx(reset_data)
        window.sessionStorage.setItem("total_reset", "true")
        client_state_actions[accept_reset] = True
        client_state_actions[deny_reset] = True
        client_state_actions[request_received] = False
    if not init["sent"] and client_state_actions[request_sent]:
        reset_data = {node.CMD: "reset"}
        node.tx(reset_data)
        window.sessionStorage.setItem("total_reset", "true")
        client_state_actions[offer_action] = False
        client_state_actions[offer_reset] = True
        client_state_actions[request_sent] = False

## Move logic
# Helper function to calculate moves for a pawn
def pawn_moves(board, row, col, is_white):
    moves = []
    captures = []

    forwards = -1 if is_white else 1

    # Pawn moves one square forward
    if board[row + forwards][col] == ' ':
        moves.append((row + forwards, col))

        # Pawn's initial double move
        if (row == 6 and is_white) or (row == 1 and not is_white):
            if board[row + 2 * forwards][col] == ' ':
                moves.append((row + 2 * forwards, col))

    # No captures possible when pawns reach the end, otherwise list index out of range
    if is_white and row == 0 or not is_white and row == 7:
        return moves, captures
    
    # Loop over neighboring columns for captures
    allied_king = 'K' if is_white else 'k'
    for c in [-1, 1]:
        new_col = col + c
        if 0 <= new_col <= 7:
            piece = board[row + forwards][new_col]
            if piece != ' ' and piece != allied_king: # Can guard own pieces
                moves.append((row + forwards, new_col))
                captures.append((row + forwards, new_col))
    
    return moves, captures

# Helper to calculate if the pawn can capture the opposite king
def pawn_captures_king(board, row, col, is_white):
    forwards = -1 if is_white else 1
    opposite_king = 'k' if is_white else 'K'

    # No captures possible when pawns reach the end, otherwise list index out of range
    if is_white and row == 0 or not is_white and row == 7:
        return False
    
    # Loop over neighboring columns for captures
    for c in [-1, 1]:
        new_col = col + c
        if 0 <= new_col <= 7:
            piece = board[row + forwards][new_col]
            if piece == opposite_king:
                return True
    
    return False

# Helper function to calculate moves for a rook
def rook_moves(board, row, col, is_white):
    moves = []
    captures = []
    allied_king = 'K' if is_white else 'k'

    # Rook moves horizontally
    for i in range(col + 1, 8):
        if board[row][i] == ' ':
            moves.append((row, i))
        else:
            if board[row][i] != allied_king:
                moves.append((row, i))
                captures.append((row, i))
            break

    for i in range(col - 1, -1, -1):
        if board[row][i] == ' ':
            moves.append((row, i))
        else:
            if board[row][i] != allied_king:
                moves.append((row, i))
                captures.append((row, i))
            break

    # Rook moves vertically
    for i in range(row + 1, 8):
        if board[i][col] == ' ':
            moves.append((i, col))
        else:
            if board[i][col] != allied_king:
                moves.append((i, col))
                captures.append((i, col))
            break

    for i in range(row - 1, -1, -1):
        if board[i][col] == ' ':
            moves.append((i, col))
        else:
            if board[i][col] != allied_king:
                moves.append((i, col))
                captures.append((i, col))
            break

    return moves, captures

# Helper to calculate if the rook can capture the opposite king
def rook_captures_king(board, row, col, is_white):
    opposite_king = 'k' if is_white else 'K'

    # Rook moves horizontally
    for i in range(col + 1, 8):
        if board[row][i] == ' ':
            continue
        elif board[row][i] == opposite_king:
            return True
        else:
            break

    for i in range(col - 1, -1, -1):
        if board[row][i] == ' ':
            continue
        elif board[row][i] == opposite_king:
            return True
        else:
            break

    # Rook moves vertically
    for i in range(row + 1, 8):
        if board[i][col] == ' ':
            continue
        elif board[i][col] == opposite_king:
            return True
        else:
            break

    for i in range(row - 1, -1, -1):
        if board[i][col] == ' ':
            continue
        elif board[i][col] == opposite_king:
            return True
        else:
            break

    return False

# Helper function to calculate moves for a knight
def knight_moves(board, row, col, is_white):
    moves = []
    captures = []
    allied_king = 'K' if is_white else 'k'

    knight_moves = [(row - 2, col - 1), (row - 2, col + 1), (row - 1, col - 2), (row - 1, col + 2),
                    (row + 1, col - 2), (row + 1, col + 2), (row + 2, col - 1), (row + 2, col + 1)]

    # Remove moves that are out of bounds
    valid_knight_moves = [(move[0], move[1]) for move in knight_moves if 0 <= move[0] < 8 and 0 <= move[1] < 8]

    # Cannot superimpose with own king
    valid_knight_moves = [(move[0], move[1]) for move in valid_knight_moves if board[move[0]][move[1]] != allied_king]

    # Valid captures
    captures = [move for move in valid_knight_moves if board[move[0]][move[1]] != " "]

    moves.extend(valid_knight_moves)

    return moves, captures

# Helper to calculate if the knight can capture the opposite king
def knight_captures_king(board, row, col, is_white):
    opposite_king = 'k' if is_white else 'K'
    knight_moves = [(row - 2, col - 1), (row - 2, col + 1), (row - 1, col - 2), (row - 1, col + 2),
                    (row + 1, col - 2), (row + 1, col + 2), (row + 2, col - 1), (row + 2, col + 1)]

    valid_knight_moves = [(move[0], move[1]) for move in knight_moves if 0 <= move[0] < 8 and 0 <= move[1] < 8]

    for move_row, move_col in valid_knight_moves:
        if board[move_row][move_col] == opposite_king:
            return True

    return False

# Helper function to calculate moves for a bishop
def bishop_moves(board, row, col, is_white):
    moves = []
    captures = []
    directions = [(-1, -1), (-1, 1), (1, -1), (1, 1)]  # Top-left, Top-right, Bottom-left, Bottom-right
    allied_king = 'K' if is_white else 'k'

    for dr, dc in directions:
        for i in range(1, 8):
            new_row, new_col = row + dr * i, col + dc * i
            if 0 <= new_row < 8 and 0 <= new_col < 8:
                if board[new_row][new_col] == ' ':
                    moves.append((new_row, new_col))
                else:
                    if board[new_row][new_col] != allied_king:
                        moves.append((new_row, new_col))
                        captures.append((new_row, new_col))
                    break
            else:
                break

    return moves, captures

# Helper to calculate if the bishop can capture the opposite king
def bishop_captures_king(board, row, col, is_white):
    opposite_king = 'k' if is_white else 'K'
    directions = [(-1, -1), (-1, 1), (1, -1), (1, 1)]  # Top-left, Top-right, Bottom-left, Bottom-right

    for dr, dc in directions:
        for i in range(1, 8):
            new_row, new_col = row + dr * i, col + dc * i
            if 0 <= new_row < 8 and 0 <= new_col < 8:
                if board[new_row][new_col] == ' ':
                    continue
                elif board[new_row][new_col] == opposite_king:
                    return True
                else:
                    break
            else:
                break

    return False

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

# Helper to calculate if the queen can capture the opposite king
def queen_captures_king(board, row, col, is_white):
    # Bishop-like moves
    if bishop_captures_king(board, row, col, is_white):
        return True

    # Rook-like moves
    if rook_captures_king(board, row, col, is_white):
        return True

    return False

# Helper function to calculate moves for a king
def king_moves(board, row, col, is_white):
    moves = []
    captures = []

    # King can move to all eight adjacent squares
    king_moves = [(row - 1, col - 1), (row - 1, col), (row - 1, col + 1),
                  (row, col - 1),                     (row, col + 1),
                  (row + 1, col - 1), (row + 1, col), (row + 1, col + 1)]

    # Remove moves that are out of bounds
    valid_king_moves = [move for move in king_moves if 0 <= move[0] < 8 and 0 <= move[1] < 8]

    # Valid captures
    captures = [move for move in valid_king_moves if board[move[0]][move[1]] != " "]

    moves.extend(valid_king_moves)

    return moves, captures

# Helper to calculate if the king can capture the opposite king, redundant since illegal
def king_captures_king(board, row, col, is_white):
    opposite_king = 'k' if is_white else 'K'

    king_moves = [
        (row - 1, col - 1), (row - 1, col), (row - 1, col + 1),
        (row, col - 1),                     (row, col + 1),
        (row + 1, col - 1), (row + 1, col), (row + 1, col + 1)
    ]

    # Remove moves that are out of bounds
    valid_king_moves = [move for move in king_moves if 0 <= move[0] < 8 and 0 <= move[1] < 8]

    for move_row, move_col in valid_king_moves:
        if board[move_row][move_col] == opposite_king:
            return True

    return False

# Helper function to return moves for the selected piece
def calculate_moves(board, row, col, game_history, castle_attributes=None, only_specials=False):
    # only_specials input for only calculating special moves, this is used when updating the dictionary of board states
    # of the game class. Special available moves are one attribute of a unique state
    piece = board[row][col]
    piece_type = piece.lower()
    moves = []
    captures = []
    special_moves = []

    is_white = piece.isupper()

    if not only_specials:
        if piece_type == 'p':
            p_moves, p_captures = pawn_moves(board, row, col, is_white)
            moves.extend(p_moves)
            captures.extend(p_captures)

        elif piece_type == 'r':
            r_moves, r_captures = rook_moves(board, row, col, is_white)
            moves.extend(r_moves)
            captures.extend(r_captures)

        elif piece_type == 'n':
            n_moves, n_captures = knight_moves(board, row, col, is_white)
            moves.extend(n_moves)
            captures.extend(n_captures)

        elif piece_type == 'b':
            b_moves, b_captures = bishop_moves(board, row, col, is_white)
            moves.extend(b_moves)
            captures.extend(b_captures)

        elif piece_type == 'q':
            q_moves, q_captures = queen_moves(board, row, col, is_white)
            moves.extend(q_moves)
            captures.extend(q_captures)

        elif piece_type == 'k':
            k_moves, k_captures = king_moves(board, row, col, is_white)
            moves.extend(k_moves)
            captures.extend(k_captures)
        
        elif piece == ' ':
            return [], [], []
        else:
            return ValueError

    # Special moves
    if piece_type == 'p' and game_history is not None and len(game_history) != 0:
        previous_turn = game_history[-1][0] if not is_white else game_history[-1][1]
        
        pawn_data = {
            'white': ('p', '1', '3', 2),
            'black': ('P', '6', '4', 5)
        }
        
        if is_white and row == 3 or not is_white and row == 4:
            previous_pawn, previous_start_row, previous_end_row, destination_row = pawn_data['white' if is_white else 'black']
            add_enpassant = True
        else:
            add_enpassant = False
        
        if add_enpassant:
            start, end = list(previous_turn[0]), list(previous_turn[1])
            # En-passant condition: A pawn moves twice onto a square with an adjacent pawn in the same rank
            if (
                start[0] == previous_pawn and end[0] == previous_pawn and
                start[1] == previous_start_row and end[1] == previous_end_row and
                abs(col - int(end[2])) == 1
            ):
                special_moves.append((destination_row, int(end[2])))

    # Using these attributes instead of a game copy eliminates the need to deepcopy the game below
    # and instead use a temp board
    if piece_type == 'k' and castle_attributes is not None:
        if is_white:
            moved_king = castle_attributes['white_king_moved'][0]
            left_rook_moved = castle_attributes['left_white_rook_moved'][0]
            right_rook_moved = castle_attributes['right_white_rook_moved'][0]
            king_row = 7
            king_piece = 'K'
        else:
            moved_king = castle_attributes['black_king_moved'][0]
            left_rook_moved = castle_attributes['left_black_rook_moved'][0]
            right_rook_moved = castle_attributes['right_black_rook_moved'][0]
            king_row = 0
            king_piece = 'k'

        temp_board = [rank[:] for rank in board]
        if not moved_king:
            if not left_rook_moved:
                # Empty squares between king and rook
                if all(element == ' ' for element in board[king_row][1:4]):
                    # Not moving through/into check and not currently under check
                    temp_boards = []
                    for placement_col in [4, 3, 2]:
                        temp_board[king_row][4] = ' '
                        temp_board[king_row][placement_col] = king_piece
                        temp_boards.append(copy.deepcopy(temp_board))
                        # Undo
                        temp_board[king_row][4] = king_piece
                        temp_board[king_row][placement_col] = ' '
                    # Empty squares are clear of checks
                    if all(not is_check(temp, is_white) for temp in temp_boards):
                        for board in temp_boards:
                            for row in board:
                                print(row)
                        special_moves.append((king_row, 2))
            if not right_rook_moved:
                # Empty squares between king and rook
                if all(element == ' ' for element in board[king_row][5:7]):
                    # Not moving through/into check and not currently under check
                    temp_boards = []
                    for placement_col in [4, 5, 6]:
                        temp_board[king_row][4] = ' '
                        temp_board[king_row][placement_col] = king_piece
                        temp_boards.append(copy.deepcopy(temp_board))
                        # Undo
                        temp_board[king_row][4] = king_piece
                        temp_board[king_row][placement_col] = ' '
                    # Empty squares are clear of checks
                    if all(not is_check(temp, is_white) for temp in temp_boards):
                        for board in temp_boards:
                            for row in board:
                                print(row)
                        special_moves.append((king_row, 6))

    return moves, captures, special_moves

# Helper function to check if the opposite king can be captured
def king_is_captured(board, row, col, piece, piece_type):
    is_white = piece.isupper()

    if piece_type == 'p':
        if pawn_captures_king(board, row, col, is_white):
            return True

    elif piece_type == 'r':
        if rook_captures_king(board, row, col, is_white):
            return True

    elif piece_type == 'n':
        if knight_captures_king(board, row, col, is_white):
            return True

    elif piece_type == 'b':
        if bishop_captures_king(board, row, col, is_white):
            return True

    elif piece_type == 'q':
        if queen_captures_king(board, row, col, is_white):
            return True

    elif piece_type == 'k':
        if king_captures_king(board, row, col, is_white):
            return True
        
    elif piece_type == ' ':
        return False
    else:
        return ValueError

## Board State Check Logic
# Helper function to search for checks
def is_check(board, is_color):
    # Check if any of the opponent's pieces can attack the king
    for row in range(8):
        for col in range(8):
            piece = board[row][col]
            if piece != ' ' and piece.islower() == is_color:
                king_captured = king_is_captured(board, row, col, piece, piece.lower())
                if king_captured:
                    return True
    return False

# Helper function to search for end-game state
def is_checkmate_or_stalemate(board, is_color, moves):
    possible_moves = 0
    # Consider this as a potential checkmate if under check
    checkmate = is_check(board, is_color)
    
    temp_board = [rank[:] for rank in board]  
    # Iterate through all the player's pieces
    for row in range(8):
        for col in range(8):
            if not checkmate and possible_moves != 0:
                break
            piece = board[row][col]
            if piece != ' ' and piece.isupper() == is_color:
                other_moves, _, other_specials = calculate_moves(board, row, col, moves)
                for move in other_moves:
                    # Try each move and see if it removes the check
                    # Before making the move, create a copy of the board where the piece has moved
                    old_position = board[move[0]][move[1]]
                    new_piece = temp_board[move[0]][move[1]]
                    if new_piece != ' ' and new_piece.isupper() == is_color:
                        continue
                    temp_board[move[0]][move[1]] = temp_board[row][col]
                    temp_board[row][col] = ' '
                    if not is_check(temp_board, is_color):
                        possible_moves += 1
                        checkmate = False
                
                    # Revert changes
                    temp_board[row][col] = temp_board[move[0]][move[1]]
                    temp_board[move[0]][move[1]] = old_position

                # En-passants can remove checks
                for move in other_specials:
                    # We never have to try castling moves because you can never castle under check
                    if move not in [(7, 2), (7, 6), (0, 2), (0, 6)]:
                        temp_board[move[0]][move[1]] = temp_board[row][col]
                        temp_board[row][col] = ' '
                        capture_row = 4 if move[0] == 3 else 5
                        old_pawn = temp_board[capture_row][move[1]]
                        temp_board[capture_row][move[1]] = ' '
                        if not is_check(temp_board, is_color):
                            possible_moves += 1
                            checkmate = False

                        # Revert changes
                        temp_board[row][col] = temp_board[move[0]][move[1]]
                        temp_board[move[0]][move[1]] = ' '
                        temp_board[capture_row][move[1]] = old_pawn

    return checkmate, possible_moves

# Set check or checkmate draw flags
def set_check_or_checkmate_settings(drawing_settings, client_game):
    drawing_settings["check_white"] = is_check(client_game.board, True)
    drawing_settings["check_black"] = is_check(client_game.board, False)
    if drawing_settings["check_white"] or drawing_settings["check_black"]:
        if drawing_settings["check_white"]:
            drawing_settings["checkmate_white"] = is_checkmate_or_stalemate(client_game.board, True, client_game.moves)[0]
        if drawing_settings["check_black"]:
            drawing_settings["checkmate_black"] = is_checkmate_or_stalemate(client_game.board, False, client_game.moves)[0]
        return
    if drawing_settings["checkmate_white"] or drawing_settings["checkmate_black"]:
        drawing_settings["checkmate_white"] = False
        drawing_settings["checkmate_black"] = False

# Get board score per piece
def net_board(board):
    state = {'p': 0, 'r': 0, 'n': 0, 'b': 0, 'q': 0}
    for row in board:
        for piece in row:
            if piece != ' ' and piece.lower() != 'k':
                value = -1 if piece.islower() else +1
                state[piece.lower()] += value
    return state

## Drawing Logic
# Helper Function to get the chessboard coordinates from mouse click coordinates
def get_board_coordinates(x, y, GRID_SIZE):
    col = x // GRID_SIZE
    row = y // GRID_SIZE
    return row, col

# Helper function to generate a chessboard surface loaded as a reference image (drawn only once)
def generate_chessboard(theme):
    GRID_SIZE, WHITE_SQUARE, BLACK_SQUARE, WIDTH, HEIGHT = \
    theme.GRID_SIZE, theme.WHITE_SQUARE, theme.BLACK_SQUARE, theme.WIDTH, theme.HEIGHT

    chessboard = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    for row in range(8):
        for col in range(8):
            color = WHITE_SQUARE if (row + col) % 2 == 0 else BLACK_SQUARE
            pygame.draw.rect(chessboard, color, (col * GRID_SIZE, row * GRID_SIZE, GRID_SIZE, GRID_SIZE))
    return chessboard

# Helper function to generate coordinate fonts and their surface depending on view
def generate_coordinate_surface(theme):
    GRID_SIZE, FONT_SIZE, WHITE_SQUARE, BLACK_SQUARE, WIDTH, HEIGHT, INVERSE_PLAYER_VIEW, TEXT_OFFSET = \
    theme.GRID_SIZE, theme.FONT_SIZE, theme.WHITE_SQUARE, theme.BLACK_SQUARE, theme.WIDTH, theme.HEIGHT, \
    theme.INVERSE_PLAYER_VIEW, theme.TEXT_OFFSET

    # Pygbag cuts off the bottom by some pixels and cuts off some letters
    # TODO try fixing this in pygbag's source code and replacing this workaround
    pygbag_cutoff_shift = 3

    font = pygame.font.Font(None, FONT_SIZE) # default font is called freesansbold
    COORDINATES = ['a','b','c','d','e','f','g','h']
    NUMBERS = ['1','2','3','4','5','6','7','8']
    white_letter_surfaces = []
    black_letter_surfaces = []
    number_surfaces = []
    for i, letter in enumerate(COORDINATES):
        SQUARE = WHITE_SQUARE if i % 2 == 0 else BLACK_SQUARE
        white_letter_surfaces.append(font.render(letter, True, SQUARE))
        OTHER_SQUARE = BLACK_SQUARE if i % 2 == 0 else WHITE_SQUARE
        black_letter_surfaces.append(font.render(letter, True, OTHER_SQUARE))
        number_surfaces.append(font.render(NUMBERS[i], True, SQUARE))
    
    # Blit the coordinates onto the reference image
    coordinate_surface = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    if not INVERSE_PLAYER_VIEW:
        for i, letter in enumerate(white_letter_surfaces):
            square_y = 8 * GRID_SIZE - FONT_SIZE // 2 - TEXT_OFFSET - pygbag_cutoff_shift
            square_x = (1 + i) * GRID_SIZE - FONT_SIZE // 2
            coordinate_surface.blit(letter, (square_x, square_y))

        for i, number in enumerate(number_surfaces):
            square_x = 5
            square_y = (7 - i) * GRID_SIZE + TEXT_OFFSET
            coordinate_surface.blit(number, (square_x, square_y))
    else:
        for i, letter in enumerate(black_letter_surfaces[::-1]):
            square_y = 8 * GRID_SIZE - FONT_SIZE // 2 - TEXT_OFFSET - pygbag_cutoff_shift
            square_x = i * GRID_SIZE + 5
            coordinate_surface.blit(letter, (square_x, square_y))

        for i, number in enumerate(number_surfaces[::-1]):
            square_x = 8 * GRID_SIZE - 5 - FONT_SIZE // 2
            square_y = (7 - i) * GRID_SIZE + TEXT_OFFSET
            coordinate_surface.blit(number, (square_x, square_y))
    
    return coordinate_surface

# Helper function to draw a temporary rectangle with only an outline on a square
def draw_hover_outline(window, theme, row, col):
    GRID_SIZE, HOVER_OUTLINE_COLOR_WHITE, HOVER_OUTLINE_COLOR_BLACK = \
    theme.GRID_SIZE, theme.HOVER_OUTLINE_COLOR_WHITE, theme.HOVER_OUTLINE_COLOR_BLACK

    hover_outline = pygame.Surface((GRID_SIZE, GRID_SIZE), pygame.SRCALPHA)
    HOVER_OUTLINE_COLOR = HOVER_OUTLINE_COLOR_WHITE if (row + col) % 2 == 0 else HOVER_OUTLINE_COLOR_BLACK
    pygame.draw.rect(hover_outline, HOVER_OUTLINE_COLOR, (0, 0, GRID_SIZE, GRID_SIZE), 5)
    window.blit(hover_outline, (col * GRID_SIZE, row * GRID_SIZE))

# Helper function to draw the background king check and checkmate highlights
def draw_king_outline(window, theme, board, king_outlines, drawing_settings):
    if not (drawing_settings['checkmate_white'] or drawing_settings['check_white'] \
        or drawing_settings['checkmate_black'] or drawing_settings['check_black']):
        return
    for row in range(8):
        for col in range(8):
            piece = board[row][col]
            if piece == 'K' and (drawing_settings['checkmate_white'] or drawing_settings['check_white']):
                outline = king_outlines[1] if drawing_settings['checkmate_white'] else king_outlines[0]
                window.blit(outline, (col * theme.GRID_SIZE, row * theme.GRID_SIZE))
            elif piece == 'k' and (drawing_settings['checkmate_black'] or drawing_settings['check_black']):
                outline = king_outlines[1] if drawing_settings['checkmate_black'] else king_outlines[0]
                window.blit(outline, (col * theme.GRID_SIZE, row * theme.GRID_SIZE))

# Helper function to draw the chess pieces
def draw_pieces(window, theme, board, pieces):
    for row in range(8):
        for col in range(8):
            piece = board[row][col]
            if piece != ' ':
                window.blit(pieces[piece], (col * theme.GRID_SIZE, row * theme.GRID_SIZE))

# Helper function to draw transparent circles on half of the tiles
def draw_transparent_circles(theme, valid_moves, valid_captures, valid_specials):
    GRID_SIZE, WIDTH, HEIGHT, TRANSPARENT_CIRCLES, TRANSPARENT_SPECIAL_CIRCLES = \
    theme.GRID_SIZE, theme.WIDTH, theme.HEIGHT, theme.TRANSPARENT_CIRCLES, theme.TRANSPARENT_SPECIAL_CIRCLES

    free_moves = [move for move in valid_moves if move not in valid_captures]
    # Alpha transparency values defined in theme colors 
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

# Helper function to get x, y coordinates from board coordinates
def get_coordinates(row, col, GRID_SIZE):
    x = row * GRID_SIZE
    y = col * GRID_SIZE
    return x, y

# Helper function to draw an arrow
def draw_arrow(theme, arrow):
    ARROW_WHITE, ARROW_BLACK, WIDTH, HEIGHT, GRID_SIZE = \
        theme.ARROW_WHITE, theme.ARROW_BLACK, theme.WIDTH, theme.HEIGHT, theme.GRID_SIZE
    
    arrow_color = ARROW_WHITE if not theme.INVERSE_PLAYER_VIEW else ARROW_BLACK
    transparent_surface = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    # Arrows as row, col -> y, x
    start, end = pygame.Vector2(get_coordinates(arrow[0][1], arrow[0][0], GRID_SIZE)), pygame.Vector2(get_coordinates(arrow[1][1], arrow[1][0], GRID_SIZE))
    # Center start and end positions on Square
    start, end = start + pygame.Vector2(GRID_SIZE / 2, GRID_SIZE / 2),  end + pygame.Vector2(GRID_SIZE / 2, GRID_SIZE / 2) 
    y1, x1 = arrow[0]
    y2, x2 = arrow[1]
    dx = abs(x2 - x1)
    dy = abs(y2 - y1)
    intermediate_col, intermediate_row, intermediate_end = None, None, None
    # Customizable arrow features
    body_width = theme.ARROW_BODY_WIDTH
    head_height = theme.ARROW_HEAD_HEIGHT
    head_width = theme.ARROW_HEAD_WIDTH

    if (dx == 1 and dy == 2 ) or (dx == 2 and dy == 1):
        # Knight's move: L-shaped path
        if dx == 2:
            # Intermediate move is horizontal
            intermediate_col = x2 # Adjusted
            intermediate_row = y1
        else:
            # Intermidiate move is vertical
            intermediate_col = x1
            intermediate_row = y2 # Adjusted
    
    if intermediate_col is not None and intermediate_row is not None:
        # Translate the end point to the end of the body width of the second line to be drawn
        if intermediate_col < x1:
            translate = pygame.Vector2(-body_width / 2, 0)
        elif intermediate_col > x1:
            translate = pygame.Vector2(body_width / 2, 0)
        elif intermediate_row < y1:
            translate = pygame.Vector2(0, -body_width / 2)
        elif intermediate_row > y1:
            translate = pygame.Vector2(0, body_width / 2)
        
        # Need to offset/center to the midpoint as well
        offset = pygame.Vector2(GRID_SIZE / 2, GRID_SIZE / 2)
        intermediate_end = pygame.Vector2(get_coordinates(intermediate_col, intermediate_row, GRID_SIZE)) + offset + translate
        intermediate_point = pygame.Vector2(get_coordinates(intermediate_col, intermediate_row, GRID_SIZE)) + offset
    else:
        intermediate_point = start

    # If the arrow is straight, draw an arrow head at the end of the line, 
    # otherwise draw an arrow head at the end of the second line
    arrow = intermediate_point - end
    # Angle between arrow and a vertical line going up; negative x, y values are off screen left and up, respectively.
    # Value is a clockwise rotation, negative for counterclockwise
    angle = arrow.angle_to(pygame.Vector2(0, -1)) 
    body_length = arrow.length() - head_height

    # Create the triangle head around the origin
    head_verts = [
        pygame.Vector2(0, head_height / 2),                 # Center
        pygame.Vector2(head_width / 2, -head_height / 2),   # Bottom Right
        pygame.Vector2(-head_width / 2, -head_height / 2),  # Bottom Left
    ]
    # Rotate and translate the head into place
    translation = pygame.Vector2(0, arrow.length() - (head_height / 2)).rotate(-angle) # Rotates CCW as per documentation
    for i in range(len(head_verts)):
        head_verts[i].rotate_ip(-angle)     # Rotate the head CCW as per documentation without a length change
        head_verts[i] += translation        # Apply translation from start
        head_verts[i] += intermediate_point # Apply starting vector translation

    pygame.draw.polygon(transparent_surface, arrow_color, head_verts)

    # Calculate the body rectangle, rotate and translate into place, 
    # offset the start/bottom of the line only for a single line to not 
    # have the line overlap with starting piece
    offset = pygame.Vector2(0, GRID_SIZE * 0.25)
    if intermediate_point != start:
        offset = pygame.Vector2(0, 0)
    body_verts = [
        pygame.Vector2(-body_width / 2, body_length / 2),            # Top Left
        pygame.Vector2(body_width / 2, body_length / 2),             # Top Right
        pygame.Vector2(body_width / 2, -body_length / 2) + offset,   # Bottom Right
        pygame.Vector2(-body_width / 2, -body_length / 2) + offset,  # Bottom Left
    ]
    translation = pygame.Vector2(0, body_length / 2).rotate(-angle) # Rotates CCW as per documentation
    for i in range(len(body_verts)):
        body_verts[i].rotate_ip(-angle)     # Rotate the body CCW as per documentation without a length change
        body_verts[i] += translation
        body_verts[i] += intermediate_point
    
    # For a second line repeat the above for the intermediate rectangle
    if intermediate_point != start:
        rectangle = start - intermediate_end
        rec_angle = rectangle.angle_to(pygame.Vector2(0, -1))
        rec_length = rectangle.length()
        offset = pygame.Vector2(0, GRID_SIZE * 0.25) # Must offset these lines
        intermediate_verts = [
            pygame.Vector2(-body_width / 2, rec_length / 2),
            pygame.Vector2(body_width / 2, rec_length / 2),
            pygame.Vector2(body_width / 2, -rec_length / 2) + offset,
            pygame.Vector2(-body_width / 2, -rec_length / 2) + offset,
        ]
        translation = pygame.Vector2(0, rec_length / 2).rotate(-rec_angle)
        for i in range(len(intermediate_verts)):
            intermediate_verts[i].rotate_ip(-rec_angle)
            intermediate_verts[i] += translation
            intermediate_verts[i] += start
        
        pygame.draw.polygon(transparent_surface, arrow_color, intermediate_verts)

    pygame.draw.polygon(transparent_surface, arrow_color, body_verts)
    
    return transparent_surface

# Helper function to highlight selected squares on left or right click
def draw_highlight(window, theme, row, col, left):
    GRID_SIZE, HIGHLIGHT_WHITE, HIGHLIGHT_BLACK, HIGHLIGHT_WHITE_RED, HIGHLIGHT_BLACK_RED = \
    theme.GRID_SIZE, theme.HIGHLIGHT_WHITE, theme.HIGHLIGHT_BLACK, theme.HIGHLIGHT_WHITE_RED, theme.HIGHLIGHT_BLACK_RED

    square_highlight = pygame.Surface((GRID_SIZE, GRID_SIZE), pygame.SRCALPHA)
    colors = [HIGHLIGHT_WHITE, HIGHLIGHT_BLACK] if left else [HIGHLIGHT_WHITE_RED, HIGHLIGHT_BLACK_RED]
    HIGHLIGHT_COLOR = colors[0] if (row + col) % 2 == 0 else colors[1]
    pygame.draw.rect(square_highlight, HIGHLIGHT_COLOR, (0, 0, GRID_SIZE, GRID_SIZE))
    window.blit(square_highlight, (col * GRID_SIZE, row * GRID_SIZE))

# Helper function to shift coordinates as inputs to those of a reversed board
def map_to_reversed_board(original_row, original_col, board_size=8):
    reversed_row = board_size - 1 - original_row
    reversed_col = board_size - 1 - original_col
    
    return reversed_row, reversed_col

# Helper function to reverse the view of a board
def reverse_chessboard(board):
    reversed_board = []
    for row in reversed(board):
        reversed_row = row[::-1]
        reversed_board.append(reversed_row)
    return reversed_board

# Helper function for reversing coordinates of input parameters
def reverse_coordinates(params):
    params['board'] = reverse_chessboard(params['board'])
    for key in ['selected_piece', 'current_position', 'previous_position', 'hovered_square']:
        if params[key] is not None:
            params[key] = map_to_reversed_board(params[key][0], params[key][1])

    reversed_valid_moves, reversed_valid_captures, reversed_valid_specials = [], [], []
    for move in params['valid_moves']:
        reversed_valid_moves.append(map_to_reversed_board(move[0], move[1]))
    for move in params['valid_captures']:
        reversed_valid_captures.append(map_to_reversed_board(move[0], move[1]))
    for move in params['valid_specials']:
        reversed_valid_specials.append(map_to_reversed_board(move[0], move[1]))
    params['valid_moves'] = reversed_valid_moves
    params['valid_captures'] = reversed_valid_captures
    params['valid_specials'] = reversed_valid_specials

    reversed_right_click_squares, reversed_drawn_arrows = [], []
    for square in params['right_clicked_squares']:
        reversed_right_click_squares.append(map_to_reversed_board(square[0], square[1]))
    for arrow in params['drawn_arrows']:
        reversed_start, reversed_end = map_to_reversed_board(arrow[0][0], arrow[0][1]), map_to_reversed_board(arrow[1][0], arrow[1][1])
        reversed_drawn_arrows.append([reversed_start, reversed_end])
    params['right_clicked_squares'], params['drawn_arrows'] = reversed_right_click_squares, reversed_drawn_arrows

    return params

# Helper function for getting transparent pieces for the active moves
def get_transparent_active_piece(game, transparent_pieces):
    if game.white_active_move is not None:
        if game._promotion_white is None:
            white_piece = game.board[game.white_active_move[0][0]][game.white_active_move[0][1]]
        else:
            white_piece = game._promotion_white
        white_selected_piece_image = transparent_pieces[white_piece]
    else: 
        white_selected_piece_image = None
    if game.black_active_move is not None:
        if game._promotion_black is None:
            black_piece = game.board[game.black_active_move[0][0]][game.black_active_move[0][1]]
        else:
            black_piece = game._promotion_black
        black_selected_piece_image = transparent_pieces[black_piece]
    else: 
        black_selected_piece_image = None
    return white_selected_piece_image, black_selected_piece_image

# Helper function for drawing the board
def draw_board(params):
    window = params['window']
    theme = params['theme']
    if theme.INVERSE_PLAYER_VIEW:
        params = reverse_coordinates(params)
    board = params['board']
    chessboard = params['drawing_settings']['chessboard'].copy()
    selected_piece = params['selected_piece']
    white_current_position = params['white_current_position']
    white_previous_position = params['white_previous_position']
    black_current_position = params['black_current_position']
    black_previous_position = params['black_previous_position']
    right_clicked_squares = params['right_clicked_squares']
    coordinate_surface = params['drawing_settings']['coordinate_surface'].copy()
    drawn_arrows = params['drawn_arrows']
    valid_moves = params['valid_moves']
    valid_captures = params['valid_captures']
    valid_specials = params['valid_specials']
    king_outlines = params['drawing_settings']['king_outlines']
    pieces = params['pieces']
    hovered_square = params['hovered_square']
    white_active_position = params['white_active_position']
    black_active_position = params['black_active_position']
    white_selected_piece_image = params['white_selected_piece_image']
    black_selected_piece_image = params['black_selected_piece_image']
    selected_piece_image = params['selected_piece_image']
    
    window.blit(chessboard, (0, 0))

    # Highlight left clicked selected squares
    left = True
    if selected_piece is not None:
        draw_highlight(window, theme, selected_piece[0], selected_piece[1], left)
    if white_current_position is not None:
        draw_highlight(window, theme, white_current_position[0], white_current_position[1], left)
    if white_previous_position is not None:
        draw_highlight(window, theme, white_previous_position[0], white_previous_position[1], left)
    if black_current_position is not None:
        draw_highlight(window, theme, black_current_position[0], black_current_position[1], left)
    if black_previous_position is not None:
        draw_highlight(window, theme, black_previous_position[0], black_previous_position[1], left)

    # Highlight right clicked selected squares
    left = False
    for square in right_clicked_squares:
        draw_highlight(window, theme, square[0], square[1], left)

    # Draw reference coordinates AFTER highlights
    window.blit(coordinate_surface, (0, 0))

    # Highlight valid move squares
    transparent_circles = draw_transparent_circles(theme, valid_moves, valid_captures, valid_specials)
    window.blit(transparent_circles, (0, 0))

    draw_king_outline(window, theme, board, king_outlines, params['drawing_settings'])
    draw_pieces(window, theme, board, pieces)

    if hovered_square is not None:
        draw_hover_outline(window, theme, hovered_square[0], hovered_square[1])

    for arrow in drawn_arrows:
        transparent_arrow = draw_arrow(theme, arrow)
        # Blit each arrow separately to not blend them with each other
        window.blit(transparent_arrow, (0, 0))
    
    if white_active_position is not None:
        x, y = theme.GRID_SIZE * white_active_position[1], theme.GRID_SIZE * white_active_position[0]
        window.blit(white_selected_piece_image, (x, y))
    if black_active_position is not None:
        x, y = theme.GRID_SIZE * black_active_position[1], theme.GRID_SIZE * black_active_position[0]
        window.blit(black_selected_piece_image, (x, y))
    # On mousedown and a piece is selected draw a transparent copy of the piece
    # Draw after/above outline and previous layers
    if selected_piece_image is not None:
        x, y = pygame.mouse.get_pos()
        # Calculate the position to center the image on the mouse
        image_x = x - theme.GRID_SIZE // 2
        image_y = y - theme.GRID_SIZE // 2
        window.blit(selected_piece_image, (image_x, image_y))

# Helper class for a Pawn Promotion Button
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

# Helper function for creating promotion buttons at the right locations 
def display_promotion_options(theme,row, col):
    GRID_SIZE = theme.GRID_SIZE

    if row == 0:
        button_col = col
        button_y_values = [i * GRID_SIZE for i in [0, 1, 2, 3]]
        if theme.INVERSE_PLAYER_VIEW:
            button_y_values = [i * GRID_SIZE for i in [7, 6, 5, 4]]
            button_col = 8 - 1 - col
        button_x = button_col * GRID_SIZE

        promotion_buttons = [
            Pawn_Button(button_x, button_y_values[0], GRID_SIZE, GRID_SIZE, 'Q'),
            Pawn_Button(button_x, button_y_values[1], GRID_SIZE, GRID_SIZE, 'R'),
            Pawn_Button(button_x, button_y_values[2], GRID_SIZE, GRID_SIZE, 'B'),
            Pawn_Button(button_x, button_y_values[3], GRID_SIZE, GRID_SIZE, 'N'),
        ]
    elif row == 7:
        button_col = col
        button_y_values = [i * GRID_SIZE for i in [7, 6, 5, 4]]
        if theme.INVERSE_PLAYER_VIEW:
            button_y_values = [i * GRID_SIZE for i in [0, 1, 2, 3]]
            button_col = 8 - 1 - col
        button_x = button_col * GRID_SIZE

        promotion_buttons = [
            Pawn_Button(button_x, button_y_values[0], GRID_SIZE, GRID_SIZE, 'q'),
            Pawn_Button(button_x, button_y_values[1], GRID_SIZE, GRID_SIZE, 'r'),
            Pawn_Button(button_x, button_y_values[2], GRID_SIZE, GRID_SIZE, 'b'),
            Pawn_Button(button_x, button_y_values[3], GRID_SIZE, GRID_SIZE, 'n'),
        ]
    return promotion_buttons