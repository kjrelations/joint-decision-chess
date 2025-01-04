import json

def deepcopy_list_of_lists(original):
    n = len(original)
    copy = [None] * n
    
    for i in range(n):
        copy[i] = original[i][:]
    
    return copy

def pawn_moves(board, row, col, is_white):
    moves = []
    captures = []

    forwards = -1 if is_white else 1

    if row in [0, 7]:
        return moves, captures

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
    for c in [-1, 1]:
        new_col = col + c
        if 0 <= new_col <= 7:
            piece = board[row + forwards][new_col]
            if piece != ' ' and piece.lower() != 'k': # Can guard own pieces; no capturing kings
                moves.append((row + forwards, new_col))
                captures.append((row + forwards, new_col))
    
    return moves, captures

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

def rook_moves(board, row, col):
    moves = []
    captures = []

    # Rook moves horizontally
    for i in range(col + 1, 8):
        piece = board[row][i]
        if piece == ' ':
            moves.append((row, i))
        else:
            if piece.lower() != 'k':
                moves.append((row, i))
                captures.append((row, i))
            break

    for i in range(col - 1, -1, -1):
        piece = board[row][i]
        if piece == ' ':
            moves.append((row, i))
        else:
            if piece.lower() != 'k':
                moves.append((row, i))
                captures.append((row, i))
            break

    # Rook moves vertically
    for i in range(row + 1, 8):
        piece = board[i][col]
        if piece == ' ':
            moves.append((i, col))
        else:
            if piece.lower() != 'k':
                moves.append((i, col))
                captures.append((i, col))
            break

    for i in range(row - 1, -1, -1):
        piece = board[i][col]
        if piece == ' ':
            moves.append((i, col))
        else:
            if piece.lower() != 'k':
                moves.append((i, col))
                captures.append((i, col))
            break

    return moves, captures

def rook_captures_king(board, row, col, is_white):
    opposite_king = 'k' if is_white else 'K'

    # Rook moves horizontally
    for i in range(col + 1, 8):
        piece = board[row][i]
        if piece == ' ':
            continue
        elif board[row][i] == opposite_king:
            return True
        else:
            break

    for i in range(col - 1, -1, -1):
        piece = board[row][i]
        if piece == ' ':
            continue
        elif piece == opposite_king:
            return True
        else:
            break

    # Rook moves vertically
    for i in range(row + 1, 8):
        piece = board[i][col]
        if piece == ' ':
            continue
        elif piece == opposite_king:
            return True
        else:
            break

    for i in range(row - 1, -1, -1):
        piece = board[i][col]
        if piece == ' ':
            continue
        elif piece == opposite_king:
            return True
        else:
            break

    return False

def knight_moves(board, row, col):
    moves = []
    captures = []

    knight_moves = [(row - 2, col - 1), (row - 2, col + 1), (row - 1, col - 2), (row - 1, col + 2),
                    (row + 1, col - 2), (row + 1, col + 2), (row + 2, col - 1), (row + 2, col + 1)]

    # Remove moves that are out of bounds
    valid_knight_moves = [(move[0], move[1]) for move in knight_moves if 0 <= move[0] < 8 and 0 <= move[1] < 8]

    # Cannot superimpose with own king or capture enemy king
    valid_knight_moves = [(move[0], move[1]) for move in valid_knight_moves if board[move[0]][move[1]].lower() != 'k']

    # Valid captures
    captures = [move for move in valid_knight_moves if board[move[0]][move[1]] != " "]

    moves.extend(valid_knight_moves)

    return moves, captures

def knight_captures_king(board, row, col, is_white):
    opposite_king = 'k' if is_white else 'K'
    knight_moves = [(row - 2, col - 1), (row - 2, col + 1), (row - 1, col - 2), (row - 1, col + 2),
                    (row + 1, col - 2), (row + 1, col + 2), (row + 2, col - 1), (row + 2, col + 1)]

    valid_knight_moves = [(move[0], move[1]) for move in knight_moves if 0 <= move[0] < 8 and 0 <= move[1] < 8]

    for move_row, move_col in valid_knight_moves:
        if board[move_row][move_col] == opposite_king:
            return True

    return False

def bishop_moves(board, row, col):
    moves = []
    captures = []
    directions = [(-1, -1), (-1, 1), (1, -1), (1, 1)]  # Top-left, Top-right, Bottom-left, Bottom-right

    for dr, dc in directions:
        for i in range(1, 8):
            new_row, new_col = row + dr * i, col + dc * i
            if 0 <= new_row < 8 and 0 <= new_col < 8:
                if board[new_row][new_col] == ' ':
                    moves.append((new_row, new_col))
                else:
                    if board[new_row][new_col].lower() != 'k':
                        moves.append((new_row, new_col))
                        captures.append((new_row, new_col))
                    break
            else:
                break

    return moves, captures

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

def queen_moves(board, row, col):
    moves = []
    captures = []

    # Bishop-like moves
    b_moves, b_captures = bishop_moves(board, row, col)
    moves.extend(b_moves)
    captures.extend(b_captures)

    # Rook-like moves
    r_moves, r_captures = rook_moves(board, row, col)
    moves.extend(r_moves)
    captures.extend(r_captures)

    return moves, captures

def queen_captures_king(board, row, col, is_white):
    # Bishop-like moves
    if bishop_captures_king(board, row, col, is_white):
        return True

    # Rook-like moves
    if rook_captures_king(board, row, col, is_white):
        return True

    return False

def king_moves(board, row, col):
    moves = []
    captures = []

    # King can move to all eight adjacent squares
    king_moves = [(row - 1, col - 1), (row - 1, col), (row - 1, col + 1),
                  (row, col - 1),                     (row, col + 1),
                  (row + 1, col - 1), (row + 1, col), (row + 1, col + 1)]

    # Remove moves that are out of bounds and capture kings
    valid_king_moves = [move for move in king_moves if 0 <= move[0] < 8 and 0 <= move[1] < 8 and board[move[0]][move[1]].lower() != 'k']

    # Valid captures
    captures = [move for move in valid_king_moves if board[move[0]][move[1]] != " "]

    moves.extend(valid_king_moves)

    return moves, captures

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
            r_moves, r_captures = rook_moves(board, row, col)
            moves.extend(r_moves)
            captures.extend(r_captures)

        elif piece_type == 'n':
            n_moves, n_captures = knight_moves(board, row, col)
            moves.extend(n_moves)
            captures.extend(n_captures)

        elif piece_type == 'b':
            b_moves, b_captures = bishop_moves(board, row, col)
            moves.extend(b_moves)
            captures.extend(b_captures)

        elif piece_type == 'q':
            q_moves, q_captures = queen_moves(board, row, col)
            moves.extend(q_moves)
            captures.extend(q_captures)

        elif piece_type == 'k':
            k_moves, k_captures = king_moves(board, row, col)
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
                board[int(end[1])][int(end[2])] == previous_pawn and
                abs(col - int(end[2])) == 1
            ):
                special_moves.append((destination_row, int(end[2])))

    # Using these attributes instead of a game copy eliminates the need to deepcopy the game below
    # and instead use a temp board
    if piece_type == 'k' and castle_attributes is not None:
        if is_white:
            moved_king = castle_attributes['white_king_moved'][0] or board[7][4] != 'K'
            left_rook_moved = castle_attributes['left_white_rook_moved'][0] or board[7][0] != 'R'
            right_rook_moved = castle_attributes['right_white_rook_moved'][0] or board[7][7] != 'R'
            king_row = 7
            king_piece = 'K'
        else:
            moved_king = castle_attributes['black_king_moved'][0] or board[0][4] != 'k'
            left_rook_moved = castle_attributes['left_black_rook_moved'][0] or board[0][0] != 'r'
            right_rook_moved = castle_attributes['right_black_rook_moved'][0] or board[0][7] != 'r'
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
                        temp_boards.append(deepcopy_list_of_lists(temp_board))
                        # Undo
                        temp_board[king_row][4] = king_piece
                        temp_board[king_row][placement_col] = ' '
                    # Empty squares are clear of checks
                    if all(not is_check(temp, is_white) for temp in temp_boards):
                        special_moves.append((king_row, 2))
            if not right_rook_moved:
                # Empty squares between king and rook
                if all(element == ' ' for element in board[king_row][5:7]):
                    # Not moving through/into check and not currently under check
                    temp_boards = []
                    for placement_col in [4, 5, 6]:
                        temp_board[king_row][4] = ' '
                        temp_board[king_row][placement_col] = king_piece
                        temp_boards.append(deepcopy_list_of_lists(temp_board))
                        # Undo
                        temp_board[king_row][4] = king_piece
                        temp_board[king_row][placement_col] = ' '
                    # Empty squares are clear of checks
                    if all(not is_check(temp, is_white) for temp in temp_boards):
                        special_moves.append((king_row, 6))

    return moves, captures, special_moves

def king_is_captured(board, row, col, piece_type, is_white):

    if piece_type == 'p':
        return pawn_captures_king(board, row, col, is_white)

    elif piece_type == 'r':
        return rook_captures_king(board, row, col, is_white)

    elif piece_type == 'n':
        return knight_captures_king(board, row, col, is_white)

    elif piece_type == 'b':
        return bishop_captures_king(board, row, col, is_white)

    elif piece_type == 'q':
        return queen_captures_king(board, row, col, is_white)

    elif piece_type == 'k':
        return king_captures_king(board, row, col, is_white)
        
    elif piece_type == ' ':
        return False
    else:
        return ValueError

def is_check(board, is_white):
    # Check if any of the opponent's pieces can attack the king
    for row in range(8):
        for col in range(8):
            piece = board[row][col]
            piece_is_black = piece.islower()
            is_opposite_piece = piece_is_black == is_white
            if piece != ' ' and is_opposite_piece:
                king_captured = king_is_captured(board, row, col, piece.lower(), not piece_is_black)
                if king_captured:
                    return True
    return False

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
                    if old_position != ' ' and old_position.isupper() == is_color:
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
                        capture_row = 4 if move[0] == 5 else 3
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

def game_is_invalid(FEN):
    board = translate_FEN_into_board(FEN)

    invalid = False
    white_king_count, black_king_count = 0, 0
    for r in board:
        for c in r:
            if c == 'k':
                black_king_count += 1
            elif c == 'K':
                white_king_count += 1
    invalid = white_king_count != 1 or black_king_count != 1
    if invalid:
        return True
    
    checkmate_white, remaining_moves_white = is_checkmate_or_stalemate(board, True, [])
    checkmate_black, remaining_moves_black = is_checkmate_or_stalemate(board, False, [])
    checkmate = checkmate_white or checkmate_black
    no_remaining_moves = remaining_moves_white == 0 or remaining_moves_black == 0
    if checkmate:
        return True
    elif no_remaining_moves:
        return True
    return False

def is_valid_FEN(FEN):
    if not isinstance(FEN, str):
        return False
    count = 0
    rows = 0
    for piece in FEN:
        if count > 8 or rows >= 8:
            return False
        if (piece.isdigit() and (int(piece) < 1 or int(piece) > 8)) or \
           (not piece.isdigit() and piece.lower() not in 'pnbrqk/'):
            return False
        if piece == '/':
            if count != 8:
                return False
            else:
                count = 0
                rows += 1
        elif piece.isdigit():
            count += int(piece)
        else:
            count += 1
    if not count == 8 and rows == 7:
        return False
    return not game_is_invalid(FEN)

def is_valid_castling_dict(data):
    required_keys = {
        "white_kingside": bool,
        "white_queenside": bool,
        "black_kingside": bool,
        "black_queenside": bool
    }

    for key, expected_type in required_keys.items():
        if key not in data:
            return False
        if not isinstance(data[key], expected_type):
            return False

    return True

def format_state(FEN, castling_rights, gametype):
    board = translate_FEN_into_board(FEN)
    castle_attributes = {
        "white_king_moved": [board[7][4] != 'K' or castling_rights['white_kingside'] or castling_rights['white_queenside'], None],
        "left_white_rook_moved": [board[7][0] != 'R' or castling_rights['white_queenside'], None],
        "right_white_rook_moved": [board[7][7] != 'R' or castling_rights['white_kingside'], None],
        "black_king_moved": [board[0][4] != 'k' or castling_rights['black_kingside'] or castling_rights['black_queenside'], None],
        "left_black_rook_moved": [board[0][0] != 'r' or castling_rights['black_queenside'], None],
        "right_black_rook_moved": [board[0][7] != 'r' or castling_rights['black_kingside'], None]
    }
    board_states = []
    
    reveal_stage_enabled = True if gametype in ["Complete", "Relay"] else False
    decision_stage_enabled = True if gametype in ["Complete", "Countdown"] else False

    state = json.dumps({
        "white_played": False,
        "black_played": False,
        "subvariant": "Normal", # TODO parameter
        "timed_mode": False, # TODO condition
        "increment": None, # TODO parameter
        # TODO fill other time fields
        "reveal_stage_enabled": reveal_stage_enabled,
        "decision_stage_enabled": decision_stage_enabled,
        "playing_stage": True,
        "reveal_stage": False,
        "decision_stage": False,
        "board": board,
        "moves": [],
        "alg_moves": [],
        "castle_attributes": castle_attributes,
        "white_active_move": None,
        "black_active_move": None,
        "white_current_position": None,
        "white_previous_position": None,
        "black_current_position": None,
        "black_previous_position": None,
        "max_states": 500,
        "end_position": False,
        "forced_end": "",
        "white_lock": False,
        "black_lock": False,
        "decision_stage_complete": False,
        "white_undo_count": 0,
        "black_undo_count": 0,
        "_starting_player": False,
        "_move_undone": False,
        "_sync": True,
        "_promotion_white": None,
        "_promotion_black": None,
        "_set_last_move": False,
        "_max_states_reached": False,
        "board_states": board_states
    })
    return state

def custom_state(FEN, castling_rights, gametype):
    if not is_valid_FEN(FEN):
        return None
    if not is_valid_castling_dict(castling_rights):
        return None
    state = format_state(FEN, castling_rights, gametype)
    return state