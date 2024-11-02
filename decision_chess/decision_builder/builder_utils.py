def is_valid_FEN(FEN):
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
    return count == 8 and rows == 7

def translate_board_into_FEN(board):
    FEN = ""
    for row in board:
        empty_count = 0
        row_fen = ""
        for cell in row:
            if cell == ' ':
                empty_count += 1
            else:
                if empty_count > 0:
                    row_fen += str(empty_count)
                    empty_count = 0
                row_fen += cell
        if empty_count > 0:
            row_fen += str(empty_count)
        FEN += row_fen + "/"
    return FEN.rstrip("/")