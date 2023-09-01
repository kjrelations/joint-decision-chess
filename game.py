from helpers import *

class Game:

    def __init__(self, board):
        self.current_turn = None
        self.board = board
        self.moves = []
        self.alg_moves = []
        self.castle_attributes = {
            'white_king_moved' : False,
            'left_white_rook_moved' : False,
            'right_white_rook_moved' : False,
            'black_king_moved' : False,
            'left_black_rook_moved' : False,
            'right_black_rook_moved' : False
        }

    def update_state(self, new_row, new_col, selected_piece, special=False):
        piece = self.board[selected_piece[0]][selected_piece[1]]
        potential_capture = self.board[new_row][new_col]

        # Special moves
        enpassant, castle, special_string = False, False, ''
        if special and (new_row, new_col) not in [(7, 2), (7, 6), (0, 2), (0, 6)]:
            capture_row = 3 if new_row == 2 else 4
            potential_capture = self.board[capture_row][new_col]
            enpassant = True
            special_string = 'enpassant'
        elif special:
            castle = True
            special_string = 'castle'
        # Need to calculate alg_moves before we update board to settle disambiguities
        algebraic_move = self.translate_into_notation(new_row, new_col, piece, selected_piece, potential_capture, castle, enpassant)

        self.board[new_row][new_col] = piece
        self.board[selected_piece[0]][selected_piece[1]] = ' '
        if enpassant:
            self.board[capture_row][new_col] = ' '
        elif castle:
            if (new_row, new_col) == (7,2):
                self.board[7][3] = 'R'
                self.board[7][0] = ' '
            elif (new_row, new_col) == (7, 6):
                self.board[7][5] = 'R'
                self.board[7][7] = ' '
            elif (new_row, new_col) == (0, 2):
                self.board[0][3] = 'r'
                self.board[0][0] = ' '
            elif (new_row, new_col) == (0, 6):
                self.board[0][5] = 'r'
                self.board[0][7] = ' '

        self.moves.append(output_move(piece, selected_piece, new_row, new_col, potential_capture, special_string))
        self.alg_moves.append(algebraic_move)

        if piece == 'K' and selected_piece == (7, 4) and not self.castle_attributes['white_king_moved']:
            self.castle_attributes['white_king_moved'] = True
        elif piece == 'k' and selected_piece == (0, 4) and not self.castle_attributes['black_king_moved']:
            self.castle_attributes['black_king_moved'] = True
        elif piece == 'R' and selected_piece == (7, 0) and not self.castle_attributes['left_white_rook_moved']:
            self.castle_attributes['left_white_rook_moved'] = True
        elif piece == 'R' and selected_piece == (7, 7) and not self.castle_attributes['right_white_rook_moved']:
            self.castle_attributes['right_white_rook_moved'] = True
        elif piece == 'r' and selected_piece == (0, 0) and not self.castle_attributes['left_black_rook_moved']:
            self.castle_attributes['left_black_rook_moved'] = True
        elif piece == 'r' and selected_piece == (0, 7) and not self.castle_attributes['right_black_rook_moved']:
            self.castle_attributes['right_black_rook_moved'] = True

    def translate_into_notation(self, new_row, new_col, piece, selected_piece, potential_capture, castle, enpassant):
        file_conversion = {0: 'a', 1: 'b', 2: 'c', 3: 'd', 4: 'e', 5: 'f', 6: 'g', 7: 'h'}
        rank_conversion = {i: str(8 - i) for i in range(8)}
        alg_move = ''
        is_white = piece.isupper()
        
        # Castling
        if castle:
            if (new_row, new_col) == (7,2) or (new_row, new_col) == (0, 2):
                return '0-0-0'
            elif (new_row, new_col) == (7, 6) or (new_row, new_col) == (0, 6):
                return '0-0'

        # Don't add pawns to the move
        if piece.upper() != 'P':
            alg_move += piece.upper()
        
        # Disambiguation's in potential move with similar pieces by specifying position
        similar_pieces = []
        for row in range(8):
            for col in range(8):
                other_piece = self.board[row][col]
                if other_piece == piece and (row, col) != selected_piece:
                    other_moves, _, _ = calculate_moves(self.board, row, col, self.moves)
                    if (new_row, new_col) in other_moves:
                        similar_pieces.append((row,col))
        added_file, added_rank = '', ''
        for similar in similar_pieces:
            row, col = similar
            if col != selected_piece[1] and added_file == '': 
                added_file += str(file_conversion[selected_piece[1]])
                continue
            elif row != selected_piece[0] and added_rank == '':
                added_rank += str(rank_conversion[selected_piece[0]])
                continue
            if added_file != '' and added_rank != '':
                break
        
        if added_file != '' and added_rank == '':
            alg_move += added_file
        elif added_file == '' and added_rank != '':
            alg_move += added_rank
        elif added_file != '' and added_rank != '':
            alg_move += added_file + added_rank
        
        # Captures
        if potential_capture != ' ':
            if piece.upper() == 'P' and added_file == '':
                alg_move += str(file_conversion[selected_piece[1]])
            alg_move += 'x'
        
        # Destination
        alg_move += str(file_conversion[new_col]) + str(rank_conversion[new_row])

        # We haven't moved yet so temp board for state check
        temp_board = [rank[:] for rank in self.board]  
        temp_moves = self.moves.copy()
        temp_moves.append(output_move(piece, selected_piece, new_row, new_col, potential_capture))
        temp_board[new_row][new_col] = temp_board[selected_piece[0]][selected_piece[1]]
        temp_board[selected_piece[0]][selected_piece[1]] = ' '
        if enpassant:
            capture_row = 4 if new_row == 3 else 5
            temp_board[capture_row][new_col] = ' '
        if is_checkmate_or_stalemate(temp_board, not is_white, self.moves)[0]:
            alg_move += '#'
        elif is_check(temp_board, not is_white, temp_moves):
            alg_move += '+'

        return alg_move

    def promote_to_piece(self, row, col, piece):
        is_white = piece.isupper()
        self.board[row][col] = piece
        # Need to edit the temporary last moves/alg_moves in state one a decision is made
        string_list = list(self.moves[-1][1])
        string_list[0] = piece
        self.moves[-1][1] = ''.join(string_list)
 
        self.alg_moves[-1] += piece.upper()
        
        if is_checkmate_or_stalemate(self.board, not is_white, self.moves)[0]:
            self.alg_moves[-1] += 'X'
        elif is_check(self.board, not is_white, self.moves):
            self.alg_moves[-1] += 'x'
        print("ALG_MOVES:", self.alg_moves)

    def undo_move(self, move):
        pass

def output_move(piece, selected_piece, new_row, new_col, potential_capture, special_string= ''):
    return [piece+str(selected_piece[0])+str(selected_piece[1]), piece+str(new_row)+str(new_col), potential_capture, special_string]

# Function to return moves for the selected piece
def calculate_moves(board, row, col, game_history, castle_attributes=None):
    piece = board[row][col]
    moves = []
    captures = []
    special_moves = []

    is_white = piece.isupper() # Check if the piece is white

    if piece.lower() == 'p':  # Pawn
        p_moves, p_captures = pawn_moves(board, row, col, is_white)
        moves.extend(p_moves)
        captures.extend(p_captures)
        if game_history is not None and len(game_history) != 0:
            previous_turn = game_history[-1]
            
            add_enpassant = False
            if is_white and row == 3:
                previous_pawn, previous_start_row, previous_end_row, destination_row = 'p', '1', '3', 2
                add_enpassant = True
            elif not is_white and row == 4:
                previous_pawn, previous_start_row, previous_end_row, destination_row = 'P', '6', '4', 5
                add_enpassant = True
            if add_enpassant:
                start, end = list(previous_turn[0]), list(previous_turn[1])
                # En-passant condition: A pawn moves twice onto a square with an adjacent pawn in the same rank
                if start[0] == previous_pawn and end[0] == previous_pawn and start[1] == previous_start_row and end[1] == previous_end_row \
                    and abs(col - int(end[2])) == 1:
                    special_moves.append((destination_row, int(end[2])))

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
        # Eliminates need to deepcopy everywhere and unnecessarily consider special moves
        if castle_attributes is not None:
            # Castling
            queen_castle = True
            king_castle = True
            if is_white:
                moved_king = castle_attributes['white_king_moved']
                left_rook_moved = castle_attributes['left_white_rook_moved']
                right_rook_moved = castle_attributes['right_white_rook_moved']
                king_row = 7
                king_piece = 'K'
            else:
                moved_king = castle_attributes['black_king_moved']
                left_rook_moved = castle_attributes['left_black_rook_moved']
                right_rook_moved = castle_attributes['right_black_rook_moved']
                king_row = 0
                king_piece = 'k'

            if not moved_king:
                if not left_rook_moved:
                    # Empty squares between king and rook
                    if not all(element == ' ' for element in board[king_row][2:4]):
                        queen_castle = False
                    else:
                        # Not moving through/into check and not currently under check
                        temp_boards_and_moves = []
                        for placement_col in [4, 3, 2]:
                            temp_board = [rank[:] for rank in board]
                            temp_moves = game_history.copy()
                            temp_moves.append(output_move(piece, (king_row, 4), king_row, placement_col, ' '))
                            temp_board[king_row][4] = ' '
                            temp_board[king_row][placement_col] = king_piece
                            temp_boards_and_moves.append([temp_board, temp_moves])
                        clear_checks = all(not is_check(temp[0], is_white, temp[1]) for temp in temp_boards_and_moves)
                        if not clear_checks:
                            queen_castle = False
                else:
                    queen_castle = False
                if not right_rook_moved:
                    # Empty squares between king and rook
                    if not all(element == ' ' for element in board[king_row][5:7]):
                        king_castle = False
                    else:
                        # Not moving through/into check and not currently under check
                        temp_boards_and_moves = []
                        for placement_col in [4, 5, 6]:
                            temp_board = [rank[:] for rank in board]
                            temp_moves = game_history.copy()
                            temp_moves.append(output_move(piece, (king_row, 4), king_row, placement_col, ' '))
                            temp_board[king_row][4] = ' '
                            temp_board[king_row][placement_col] = king_piece
                            temp_boards_and_moves.append([temp_board, temp_moves])
                        clear_checks = all(not is_check(temp[0], is_white, temp[1]) for temp in temp_boards_and_moves)
                        if not clear_checks:
                            king_castle = False
                else:
                    king_castle = False
            else:
                queen_castle = False
                king_castle = False

            if queen_castle:
                king_pos = (7, 2) if is_white else (0, 2) 
                special_moves.append(king_pos)
            if king_castle:
                king_pos = (7, 6) if is_white else (0, 6) 
                special_moves.append(king_pos)

    elif piece == ' ':
        return [], [], []
    else:
        return ValueError
    
    return moves, captures, special_moves

## State Logic
def is_check(board, is_color, moves):
    # Find the king's position
    king = 'K' if is_color else 'k'
    for row in range(8):
        for col in range(8):
            if board[row][col] == king:
                king_position = (row, col)
                break
    # Check if any opponent's pieces can attack the king
    for row in range(8):
        for col in range(8):
            piece = board[row][col]
            if piece.islower() == is_color and piece != ' ':
                _, captures, _ = calculate_moves(board, row, col, moves)
                if king_position in captures:
                    return True
    return False

def is_checkmate_or_stalemate(board, is_color, moves):
    possible_moves = 0
    pos_moves = [] # For DEBUG only, TO REMOVE IN FINAL VERSION
    # Consider this as a potential checkmate if under check
    checkmate = is_check(board, is_color, moves)
    # Iterate through all the player's pieces
    for row in range(8):
        for col in range(8):
            piece = board[row][col]
            if piece.isupper() == is_color and piece != ' ':
                other_moves, _, other_specials = calculate_moves(board, row, col, moves)
                # and it will never be the only move left if available
                for move in other_moves:
                    # Try each move and see if it removes the check
                    # Before making the move, create a copy of the board where the piece has moved
                    temp_board = [rank[:] for rank in board]  
                    temp_moves = moves.copy()
                    temp_moves.append(output_move(piece, (row, col), move[0], move[1], temp_board[move[0]][move[1]]))
                    temp_board[move[0]][move[1]] = temp_board[row][col]
                    temp_board[row][col] = ' '
                    if not is_check(temp_board, is_color, temp_moves):
                        possible_moves += 1
                        checkmate = False
                        pos_moves.append([move, row, col]) # For DEBUG only, TO REMOVE IN FINAL VERSION
                # Can implement an if checkmate == True check here for efficiency but it's probably best to accurately update possible_moves
                # En-passants can remove checks
                for move in other_specials:
                    # We never have to try castling moves because you can never castle under check
                    if move not in [(7, 2), (7, 6), (0, 2), (0, 6)]:
                        temp_moves = moves.copy()
                        temp_moves.append(output_move(piece, (row, col), move[0], move[1], temp_board[move[0]][move[1]], 'enpassant'))
                        temp_board[move[0]][move[1]] = temp_board[row][col]
                        temp_board[row][col] = ' '
                        capture_row = 4 if move[0] == 3 else 5
                        temp_board[capture_row][move[1]] = ' '
                        if not is_check(temp_board, is_color, temp_moves):
                            possible_moves += 1
                            checkmate = False
                            pos_moves.append([move, row, col]) # For DEBUG only, TO REMOVE IN FINAL VERSION

    return checkmate, possible_moves