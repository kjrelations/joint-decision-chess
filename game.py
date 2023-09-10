from helpers import *

class Game:

    def __init__(self, board, current_turn):
        # current_turn = True for white, False for black, the final version will always default to True, but for now we keep it like this
        self.current_turn = current_turn
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
        # Appending an empty set of special states and initialised castling states to rows of board row tuples
        _current_board_state = tuple(tuple(row) for row in board)
        _current_board_state = _current_board_state + ((),) # Empty set of specials
        _current_board_state = _current_board_state + (tuple(self.castle_attributes.values()),)
        self.board_states = { _current_board_state: 1}
        self.max_states = 1000
        self._debug = False # Dev private attribute for removing turns

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
            if (new_row, new_col) == (7, 2):
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

        if not self._debug:
            # Change turns once a standard move is played, not during a pawn promotion
            if piece.lower() != 'p' or (piece.lower() == 'p' and (new_row != 7 and new_row != 0)):
                self.current_turn = not self.current_turn
                # Update dictionary of board states
                current_special_moves = []
                for row in range(8):
                    for col in range(8):
                        other_piece = self.board[row][col]
                        if other_piece.islower() != piece.islower() and other_piece != ' ':
                            _, _, specials = calculate_moves(self.board, row, col, self.moves, self.castle_attributes, True) 
                            current_special_moves.extend(specials)
                _current_board_state = tuple(tuple(r) for r in self.board)
                _current_board_state = _current_board_state + (tuple(current_special_moves),)
                _current_board_state = _current_board_state + (tuple(self.castle_attributes.values()),)
                if _current_board_state in self.board_states:
                    self.board_states[_current_board_state] += 1
                else:
                    self.board_states[_current_board_state] = 1
                    if len(self.board_states) > self.max_states:
                        # Find and remove the least accessed board state, this also happens to be the oldest 
                        # least accessed state based on Python 3.7+ storing dictionary items by insertion order
                        least_accessed = min(self.board_states, key=self.board_states.get)
                        del self.board_states[least_accessed]

    def translate_into_notation(self, new_row, new_col, piece, selected_piece, potential_capture, castle, enpassant):
        file_conversion = {0: 'a', 1: 'b', 2: 'c', 3: 'd', 4: 'e', 5: 'f', 6: 'g', 7: 'h'}
        rank_conversion = {i: str(8 - i) for i in range(8)}
        alg_move = ''
        is_white = piece.isupper()
        
        # Castling
        if castle:
            if (new_row, new_col) == (7, 2) or (new_row, new_col) == (0, 2):
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

    def add_end_game_notation(self, checkmate):
        if not self._debug:
            if checkmate:
                symbol = '0-1' if self.current_turn else '1-0'
                self.alg_moves.append(symbol)
                print('ALG_MOVES: ', self.alg_moves)
            else:
                self.alg_moves.append('½–½')
                print('ALG_MOVES: ', self.alg_moves)

    def promote_to_piece(self, current_row, current_col, piece):
        is_white = piece.isupper()
        self.board[current_row][current_col] = piece
        # Need to edit the temporary last moves/alg_moves in state one a decision is made
        string_list = list(self.moves[-1][1])
        string_list[0] = piece
        self.moves[-1][1] = ''.join(string_list)
 
        self.alg_moves[-1] += piece.upper()
        
        if is_checkmate_or_stalemate(self.board, not is_white, self.moves)[0]:
            self.alg_moves[-1] += 'X'
        elif is_check(self.board, not is_white, self.moves):
            self.alg_moves[-1] += 'x'
        
        # Change turns after pawn promotion
        if not self._debug:
            self.current_turn = not self.current_turn
            # Update dictionary of board states
            current_special_moves = []
            for row in range(8):
                for col in range(8):
                    other_piece = self.board[row][col]
                    if other_piece.islower() != piece.islower() and other_piece != ' ':
                        _, _, specials = calculate_moves(self.board, row, col, self.moves, self.castle_attributes, True) 
                        current_special_moves.extend(specials)
            _current_board_state = tuple(tuple(r) for r in self.board)
            _current_board_state = _current_board_state + (tuple(current_special_moves),)
            _current_board_state = _current_board_state + (tuple(self.castle_attributes.values()),)
            
            if _current_board_state in self.board_states:
                self.board_states[_current_board_state] += 1
            else:
                self.board_states[_current_board_state] = 1
                if len(self.board_states) > self.max_states:
                    # Find and remove the least accessed board state, this also happens to be the oldest 
                    # least accessed state based on Python 3.7+ storing dictionary items by insertion order
                    least_accessed = min(self.board_states, key=self.board_states.get)
                    del self.board_states[least_accessed]
            
        print("ALG_MOVES:", self.alg_moves)

    def threefold_check(self):
        for count in self.board_states.values():
            if count >= 3:
                return True
        return False

    def undo_move(self):
        # In an advanced system with an analysis/exploration board we would have multiple saved move lists or games somehow
        if len(self.moves) != 0:
            # Deincrement or remove current state from dictionary of board states
            current_special_moves = []
            for row in range(8):
                for col in range(8):
                    current_piece = self.board[row][col]
                    if current_piece.islower() != self.current_turn and current_piece != ' ':
                        _, _, specials = calculate_moves(self.board, row, col, self.moves, self.castle_attributes, True) 
                        current_special_moves.extend(specials)
            _current_board_state = tuple(tuple(r) for r in self.board)
            _current_board_state = _current_board_state + (tuple(current_special_moves),)
            _current_board_state = _current_board_state + (tuple(self.castle_attributes.values()),)
            
            if self.board_states[_current_board_state] == 1:
                del self.board_states[_current_board_state]
            else:
                self.board_states[_current_board_state] -= 1
            
            move = self.moves[-1]

            prev_move = list(move[0])
            curr_move = list(move[1])
            potential_capture = move[2]
            special = move[3]

            piece, prev_row, prev_col = prev_move[0], int(prev_move[1]), int(prev_move[2])
            curr_row, curr_col = int(curr_move[1]), int(curr_move[2])

            self.board[prev_row][prev_col] = piece
            if special != 'enpassant':
                self.board[curr_row][curr_col] = potential_capture
            else:
                self.board[curr_row][curr_col] = ' '
                self.board[prev_row][curr_col] = potential_capture

            if special == 'castle':
                if (curr_row, curr_col) == (7, 2):
                    self.board[7][0] = 'R'
                    self.board[7][3] = ' '
                    self.castle_attributes['white_king_moved'] = False
                    self.castle_attributes['left_white_rook_moved'] = False
                elif (curr_row, curr_col) == (7, 6):
                    self.board[7][7] = 'R'
                    self.board[7][5] = ' '
                    self.castle_attributes['white_king_moved'] = False
                    self.castle_attributes['right_white_rook_moved'] = False
                elif (curr_row, curr_col) == (0, 2):
                    self.board[0][0] = 'r'
                    self.board[0][3] = ' '
                    self.castle_attributes['black_king_moved'] = False
                    self.castle_attributes['left_black_rook_moved'] = False
                elif (curr_row, curr_col) == (0, 6):
                    self.board[0][7] = 'r'
                    self.board[0][5] = ' '
                    self.castle_attributes['black_king_moved'] = False
                    self.castle_attributes['right_black_rook_moved'] = False
            
            del self.moves[-1]
            del self.alg_moves[-1]

            if not self._debug:
                # Change turns once a standard move is played, not during a pawn promotion
                if piece.lower() != 'p' or (piece.lower() == 'p' and (curr_row != 7 and curr_row != 0)):
                    self.current_turn = not self.current_turn

            if len(self.moves) != 0:
                new_recent_positions = self.moves[-1]
                new_last_move, new_current_move = list(new_recent_positions[0]), list(new_recent_positions[1])

                new_curr_row, new_curr_col = int(new_current_move[1]), int(new_current_move[2])
                last_row, last_col = int(new_last_move[1]), int(new_last_move[2])

                return (new_curr_row, new_curr_col), (last_row, last_col)
            
            
        return None, None
