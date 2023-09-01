### Helpers
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
