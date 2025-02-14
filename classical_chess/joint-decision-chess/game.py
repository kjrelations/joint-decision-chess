from helpers import *
import json

class Game:

    def __init__(self, board=None, starting_player=None, whites_turn=True, custom_params=None):
        if custom_params is None:
            if board is None or starting_player is None:
                raise ValueError("board and starting_player are required parameters when custom_params is not provided.")
            # whites_turn, the final version will always default to True for new games but not custom ones
            self.whites_turn = whites_turn
            self.board = board
            self.moves = []
            self.alg_moves = []
            self.castle_attributes = {
                'white_king_moved' : [False, None],
                'left_white_rook_moved' : [False, None],
                'right_white_rook_moved' : [False, None],
                'black_king_moved' : [False, None],
                'left_black_rook_moved' : [False, None],
                'right_black_rook_moved' : [False, None]
            }
            self.current_position = None
            self.previous_position = None
            # Appending an empty set of special states and initialised castling states to rows of board row tuples
            _current_board_state = tuple(tuple(row) for row in board)
            _current_board_state = _current_board_state + ((),) # Empty set of specials
            flat_castle_values = [value for sublist in self.castle_attributes.values() for value in sublist]
            _current_board_state = _current_board_state + (tuple(flat_castle_values),)
            self.board_states = { _current_board_state: 1}
            # Apparently highest move count for a legal game so far is like 269 moves, not sure if only for one player or not
            # hence 500 is reasonable
            self.max_states = 500 
            self.end_position = False
            self.forced_end = ""
            self._starting_player = starting_player
            self._move_undone = False
            self._sync = True
            self._move_index = -1
            self._latest = True
            self._state_update = {}
            self._max_states_reached = False
        else:
            self.whites_turn = custom_params["whites_turn"]
            self.board = custom_params["board"]
            self.moves = custom_params["moves"]
            self.alg_moves = custom_params["alg_moves"]
            self.castle_attributes = custom_params["castle_attributes"]
            self.current_position = custom_params["current_position"]
            self.previous_position = custom_params["previous_position"]
            self.board_states = {}
            self._state_update = {}
            if "board_states" in custom_params:
                for state in custom_params["board_states"]:
                    key = ()
                    for item in state["key"]:
                        key = key + (tuple(item),)
                    self.board_states[key] = state["value"]
            elif "_state_update" in custom_params:
                for state in custom_params["_state_update"]:
                    key = ()
                    for item in state["key"]:
                        key = key + (tuple(item),)
                    self._state_update[key] = state["value"]
            self.max_states = custom_params["max_states"]
            self.end_position = custom_params["end_position"]
            self.forced_end = custom_params["forced_end"]
            self._starting_player = custom_params["_starting_player"]
            self._move_undone = custom_params["_move_undone"]
            self._sync = custom_params["_sync"]
            self._move_index = len(self.moves) - 1 # This could be custom eventually
            self._latest = True # I think this will always default to true for now, could be a custom move in the future
            self._max_states_reached = custom_params["_max_states_reached"]

    def synchronize(self, new_game):
        self.whites_turn = new_game.whites_turn
        self.board = new_game.board
        self.moves = new_game.moves
        self.alg_moves = new_game.alg_moves
        self.castle_attributes = new_game.castle_attributes
        self.current_position = new_game.current_position
        self.previous_position = new_game.previous_position
        if new_game._state_update:
            for state, update in new_game._state_update.items():
                if update is None:
                    try:
                        del self.board_states[state]
                    except Exception as e:
                        print(self.board_states)
                        raise e
                else:
                    self.board_states.update({state: update})
        self.end_position = new_game.end_position
        self.forced_end = new_game.forced_end
        self._move_undone = False
        self._sync = True
        self._move_index = new_game._move_index
        self._latest = True
        self._state_update = {}
        self._max_states_reached = new_game._max_states_reached

    def validate_moves(self, row, col):
        piece = self.board[row][col]
        is_white = piece.isupper()
        selected_piece = (row, col)
        valid_moves, valid_captures, valid_specials = calculate_moves(self.board, row, col, self.moves, self.castle_attributes)
        for move in valid_moves.copy():
            # Before making the move, create a copy of the board where the piece has moved
            temp_board = [rank[:] for rank in self.board]  
            temp_board[move[0]][move[1]] = temp_board[selected_piece[0]][selected_piece[1]]
            temp_board[selected_piece[0]][selected_piece[1]] = ' '
            
            # Temporary invalid move check, Useful for my variant later
            if is_invalid_capture(temp_board, not is_white):
                valid_moves.remove(move)
                if move in valid_captures:
                    valid_captures.remove(move)
            elif is_check(temp_board, is_white):
                valid_moves.remove(move)
                if move in valid_captures:
                    valid_captures.remove(move)
        
        for move in valid_specials.copy():
            # Castling moves are already validated in calculate moves, this is only for enpassant
            if (move[0], move[1]) not in [(7, 2), (7, 6), (0, 2), (0, 6)]:
                temp_board = [rank[:] for rank in self.board]  
                temp_board[move[0]][move[1]] = temp_board[selected_piece[0]][selected_piece[1]]
                temp_board[selected_piece[0]][selected_piece[1]] = ' '
                capture_row = 4 if move[0] == 5 else 3
                temp_board[capture_row][move[1]] = ' '
                if is_check(temp_board, is_white):
                    valid_specials.remove(move)
        return valid_moves, valid_captures, valid_specials

    def update_state(self, new_row, new_col, selected_piece, special=False):
        # Jump to current state before applying moves
        if self._move_index < len(self.moves) - 1: # should be same as not _latest
            self.step_to_move(len(self.moves) - 1)
            self._latest = True

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
        self.current_position = (new_row, new_col)
        self.previous_position = (selected_piece[0], selected_piece[1])
        
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
        self._move_index += 1

        if piece == 'K' and selected_piece == (7, 4) and not self.castle_attributes['white_king_moved'][0]:
            self.castle_attributes['white_king_moved'] = [True, self._move_index]

            if special_string == 'castle' and (new_row, new_col) == (7, 2):
                self.castle_attributes['left_white_rook_moved'] = [True, self._move_index]
            elif special_string == 'castle' and (new_row, new_col) == (7, 6):
                self.castle_attributes['right_white_rook_moved'] = [True, self._move_index]
        
        elif piece == 'k' and selected_piece == (0, 4) and not self.castle_attributes['black_king_moved'][0]:
            self.castle_attributes['black_king_moved'] = [True, self._move_index]

            if special_string == 'castle' and (new_row, new_col) == (0, 2):
                self.castle_attributes['left_black_rook_moved'] = [True, self._move_index]
            elif special_string == 'castle' and (new_row, new_col) == (0, 6):
                self.castle_attributes['right_black_rook_moved'] = [True, self._move_index]
        
        elif piece == 'R' and selected_piece == (7, 0) and not self.castle_attributes['left_white_rook_moved'][0]:
            self.castle_attributes['left_white_rook_moved'] = [True, self._move_index]
        elif piece == 'R' and selected_piece == (7, 7) and not self.castle_attributes['right_white_rook_moved'][0]:
            self.castle_attributes['right_white_rook_moved'] = [True, self._move_index]
        elif piece == 'r' and selected_piece == (0, 0) and not self.castle_attributes['left_black_rook_moved'][0]:
            self.castle_attributes['left_black_rook_moved'] = [True, self._move_index]
        elif piece == 'r' and selected_piece == (0, 7) and not self.castle_attributes['right_black_rook_moved'][0]:
            self.castle_attributes['right_black_rook_moved'] = [True, self._move_index]

        # Change turns once a standard move is played, not during a pawn promotion
        if piece.lower() != 'p' or (piece.lower() == 'p' and (new_row != 7 and new_row != 0)):
            self.whites_turn = not self.whites_turn
            self._move_undone = False
            self._sync = True
            
            # Update dictionary of board states
            current_special_moves = []
            for row in range(8):
                for col in range(8):
                    other_piece = self.board[row][col]
                    if other_piece.islower() != piece.islower() and other_piece != ' ':
                        _, _, specials = calculate_moves(self.board, row, col, self.moves, self.castle_attributes, True) 
                        current_special_moves.extend(specials)
            _current_board_state = tuple(tuple(r) for r in self.board)
            special_tuple = ((),) if current_special_moves == [] else tuple(tuple(s) for s in current_special_moves)
            _current_board_state = _current_board_state + special_tuple
            flat_castle_values = [value for sublist in self.castle_attributes.values() for value in sublist]
            _current_board_state = _current_board_state + (tuple(flat_castle_values),)
            
            if _current_board_state in self.board_states:
                self.board_states[_current_board_state] += 1
                self._state_update[_current_board_state] = self.board_states[_current_board_state]
            else:
                self.board_states[_current_board_state] = 1
                self._state_update[_current_board_state] = self.board_states[_current_board_state]
                if len(self.board_states) > self.max_states:
                    # Find and remove the least accessed board state, this also happens to be the oldest 
                    # least accessed state based on Python 3.7+ storing dictionary items by insertion order
                    least_accessed = min(self.board_states, key=self.board_states.get)
                    del self.board_states[least_accessed]
            self._max_states_reached = len(self.board_states.keys()) == self.max_states

    def translate_into_notation(self, new_row, new_col, piece, selected_piece, potential_capture, castle, enpassant):
        file_conversion = {0: 'a', 1: 'b', 2: 'c', 3: 'd', 4: 'e', 5: 'f', 6: 'g', 7: 'h'}
        rank_conversion = {i: str(8 - i) for i in range(8)}
        alg_move = ''
        is_white = piece.isupper()
        
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
                        similar_pieces.append((row, col))
        
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
        
        if potential_capture != ' ':
            if piece.upper() == 'P' and added_file == '':
                alg_move += str(file_conversion[selected_piece[1]])
            alg_move += 'x'
        
        # Destination
        alg_move += str(file_conversion[new_col]) + str(rank_conversion[new_row])

        # We haven't moved yet so temp board for state check
        temp_board = [rank[:] for rank in self.board]  
        temp_board[new_row][new_col] = temp_board[selected_piece[0]][selected_piece[1]]
        temp_board[selected_piece[0]][selected_piece[1]] = ' '
        
        if enpassant:
            capture_row = 4 if new_row == 3 else 5
            temp_board[capture_row][new_col] = ' '
        if is_checkmate_or_stalemate(temp_board, not is_white, self.moves)[0]:
            alg_move += '#'
        elif is_check(temp_board, not is_white):
            alg_move += '+'

        return alg_move

    def translate_into_FEN(self):
        FEN = ''
        for row in self.board:
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

    def add_end_game_notation(self, checkmate):
        if checkmate:
            symbol = '0-1' if self.whites_turn else '1-0'
            self.alg_moves.append(symbol)
            print('ALG_MOVES: ', self.alg_moves)
        else:
            self.alg_moves.append('½–½')
            print('ALG_MOVES: ', self.alg_moves)

    def promote_to_piece(self, current_row, current_col, piece):
        self.board[current_row][current_col] = piece
        
        is_white = piece.isupper()
        
        # Need to edit the temporary last moves/alg_moves in state once a decision is made
        string_list = list(self.moves[-1][1])
        string_list[0] = piece
        self.moves[-1][1] = ''.join(string_list)
 
        self.alg_moves[-1] += piece.upper()
        self.alg_moves[-1].replace('#', '').replace('+', '')
        
        if is_checkmate_or_stalemate(self.board, not is_white, self.moves)[0]:
            self.alg_moves[-1] += '#'
        elif is_check(self.board, not is_white):
            self.alg_moves[-1] += '+'
        
        # Change turns after pawn promotion
        self.whites_turn = not self.whites_turn
        self._move_undone = False
        self._sync = True
        # Update dictionary of board states
        current_special_moves = []
        for row in range(8):
            for col in range(8):
                other_piece = self.board[row][col]
                if other_piece.islower() != piece.islower() and other_piece != ' ':
                    _, _, specials = calculate_moves(self.board, row, col, self.moves, self.castle_attributes, True) 
                    current_special_moves.extend(specials)
        _current_board_state = tuple(tuple(r) for r in self.board)
        special_tuple = ((),) if current_special_moves == [] else tuple(tuple(s) for s in current_special_moves)
        _current_board_state = _current_board_state + special_tuple
        flat_castle_values = [value for sublist in self.castle_attributes.values() for value in sublist]
        _current_board_state = _current_board_state + (tuple(flat_castle_values),)
        
        if _current_board_state in self.board_states:
            self.board_states[_current_board_state] += 1
            self._state_update[_current_board_state] = self.board_states[_current_board_state]
        else:
            self.board_states[_current_board_state] = 1
            self._state_update[_current_board_state] = self.board_states[_current_board_state]
            if len(self.board_states) > self.max_states:
                # Find and remove the least accessed board state, this also happens to be the oldest 
                # least accessed state based on Python 3.7+ storing dictionary items by insertion order
                least_accessed = min(self.board_states, key=self.board_states.get)
                del self.board_states[least_accessed]
        self._max_states_reached = len(self.board_states.keys()) == self.max_states

    def threefold_check(self):
        for count in self.board_states.values():
            if count >= 3:
                return True
        return False

    def undo_move(self):
        # In an advanced system with an analysis/exploration board we would have multiple saved move lists or games somehow
        if len(self.moves) != 0:
            # If we are not undoing a move during pawn promotion the current state of the board is saved, else skip
            if 'p' not in self.board[7] and 'P' not in self.board[0]:
                # Deincrement or remove current state from dictionary of board states
                current_special_moves = []
                for row in range(8):
                    for col in range(8):
                        current_piece = self.board[row][col]
                        if current_piece.islower() != self.whites_turn and current_piece != ' ':
                            _, _, specials = calculate_moves(self.board, row, col, self.moves, self.castle_attributes, True) 
                            current_special_moves.extend(specials)
                _current_board_state = tuple(tuple(r) for r in self.board)
                special_tuple = ((),) if current_special_moves == [] else tuple(tuple(s) for s in current_special_moves)
                _current_board_state = _current_board_state + special_tuple
                flat_castle_values = [value for sublist in self.castle_attributes.values() for value in sublist]
                _current_board_state = _current_board_state + (tuple(flat_castle_values),)
                
                self._state_update = {} # On consecutive undos this wouldn't be reset and on syncronization a key error can occur
                if self.board_states.get(_current_board_state) or not self._max_states_reached:
                    if self.board_states[_current_board_state] == 1:
                        del self.board_states[_current_board_state]
                        self._state_update[_current_board_state] = None
                    else:
                        self.board_states[_current_board_state] -= 1
                        self._state_update[_current_board_state] = self.board_states[_current_board_state]
            
            move = self.moves[-1]

            prev_pos = list(move[0])
            curr_pos = list(move[1])
            potential_capture = move[2]
            special = move[3]

            piece, prev_row, prev_col = prev_pos[0], int(prev_pos[1]), int(prev_pos[2])
            curr_row, curr_col = int(curr_pos[1]), int(curr_pos[2])

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
                    self.castle_attributes['white_king_moved'] = [False, None]
                    self.castle_attributes['left_white_rook_moved'] = [False, None]
                elif (curr_row, curr_col) == (7, 6):
                    self.board[7][7] = 'R'
                    self.board[7][5] = ' '
                    self.castle_attributes['white_king_moved'] = [False, None]
                    self.castle_attributes['right_white_rook_moved'] = [False, None]
                elif (curr_row, curr_col) == (0, 2):
                    self.board[0][0] = 'r'
                    self.board[0][3] = ' '
                    self.castle_attributes['black_king_moved'] = [False, None]
                    self.castle_attributes['left_black_rook_moved'] = [False, None]
                elif (curr_row, curr_col) == (0, 6):
                    self.board[0][7] = 'r'
                    self.board[0][5] = ' '
                    self.castle_attributes['black_king_moved'] = [False, None]
                    self.castle_attributes['right_black_rook_moved'] = [False, None]
            elif special == '':
                for move_name, moved_attributes in self.castle_attributes.items():
                    moved_index = moved_attributes[1]
                    if moved_index is not None and moved_index == self._move_index:
                            self.castle_attributes[move_name] = [False, None]

            del self.moves[-1]
            del self.alg_moves[-1]
            self._move_index -= 1
            self._move_undone = True
            self._sync = False

            # Change turns once a standard move is played, not during a pawn promotion
            if piece.lower() != 'p' or (piece.lower() == 'p' and (curr_row != 7 and curr_row != 0)):
                self.whites_turn = not self.whites_turn
            # Change turn right after a pawn promotion by checking that the piece type changed
            elif piece.lower() == 'p' and (curr_row == 7 or curr_row == 0) and curr_pos[0].lower() != piece.lower():
                self.whites_turn = not self.whites_turn

            if len(self.moves) != 0:
                new_recent_positions = self.moves[-1]
                new_last_pos, new_current_pos = list(new_recent_positions[0]), list(new_recent_positions[1])

                new_curr_row, new_curr_col = int(new_current_pos[1]), int(new_current_pos[2])
                new_last_row, new_last_col = int(new_last_pos[1]), int(new_last_pos[2])

                self.current_position = (new_curr_row, new_curr_col)
                self.previous_position = (new_last_row, new_last_col)
            else:
                self.current_position = None
                self.previous_position = None
    
    def step_to_move(self, move_index):
        increment = -1
        move_index_offset = 0 # We always undo the current move
        target_index = max(move_index - 1, -1)
        if move_index > len(self.moves) - 1 or move_index < -1: # If it's the same assume it's a backwards step, handle on frontend by disabling button
            return
        elif move_index > self._move_index:
            increment = 1
            move_index_offset = 1 # We always apply the next move
            target_index = move_index
        while self._move_index != target_index:
            current_move_index = self._move_index + move_index_offset
            move = self.moves[current_move_index]

            prev_pos = list(move[0])
            curr_pos = list(move[1])
            potential_capture = move[2]
            special = move[3]

            piece = prev_pos[0] if increment < 0 else curr_pos[0]
            prev_row, prev_col = int(prev_pos[1]), int(prev_pos[2])
            curr_row, curr_col = int(curr_pos[1]), int(curr_pos[2])

            if special != 'enpassant':
                replacement = potential_capture if increment < 0 else piece
                fill = piece if increment < 0 else ' '
                self.board[curr_row][curr_col] = replacement
                self.board[prev_row][prev_col] = fill
            else:
                move_replacement = ' ' if increment < 0 else piece
                capture_replacement = potential_capture if increment < 0 else ' '
                self.board[curr_row][curr_col] = move_replacement
                self.board[prev_row][curr_col] = capture_replacement

            if special == 'castle':
                rook_old_pos = ' '
                rook_future_pos = 'R' if curr_row == 7 else 'r'
                if increment < 0:
                    rook_old_pos = 'R' if curr_row == 7 else 'r'
                    rook_future_pos = ' '
                if (curr_row, curr_col) == (7, 2):
                    self.board[7][0] = rook_old_pos
                    self.board[7][3] = rook_future_pos
                    self.castle_attributes['white_king_moved'] = [False, None] if increment < 0 else [True, current_move_index]
                    self.castle_attributes['left_white_rook_moved'] = [False, None] if increment < 0 else [True, current_move_index]
                elif (curr_row, curr_col) == (7, 6):
                    self.board[7][7] = rook_old_pos
                    self.board[7][5] = rook_future_pos
                    self.castle_attributes['white_king_moved'] = [False, None] if increment < 0 else [True, current_move_index]
                    self.castle_attributes['right_white_rook_moved'] = [False, None] if increment < 0 else [True, current_move_index]
                elif (curr_row, curr_col) == (0, 2):
                    self.board[0][0] = rook_old_pos
                    self.board[0][3] = rook_future_pos
                    self.castle_attributes['black_king_moved'] = [False, None] if increment < 0 else [True, current_move_index]
                    self.castle_attributes['left_black_rook_moved'] = [False, None] if increment < 0 else [True, current_move_index]
                elif (curr_row, curr_col) == (0, 6):
                    self.board[0][7] = rook_old_pos
                    self.board[0][5] = rook_future_pos
                    self.castle_attributes['black_king_moved'] = [False, None] if increment < 0 else [True, current_move_index]
                    self.castle_attributes['right_black_rook_moved'] = [False, None] if increment < 0 else [True, current_move_index]
            else:
                for move_name, moved_attributes in self.castle_attributes.items():
                    moved_index = moved_attributes[1]
                    if increment > 0 and moved_index is None:
                        if (prev_row, prev_col) in [(7, 0), (7, 7)] and piece == 'R':
                            self.castle_attributes[move_name] = [True, current_move_index]
                        elif (prev_row, prev_col) in [(0, 0), (0, 7)] and piece == 'r':
                            self.castle_attributes[move_name] = [True, current_move_index]
                        elif (prev_row, prev_col) == (7, 4) and piece == 'K':
                            self.castle_attributes[move_name] = [True, current_move_index]
                        elif (prev_row, prev_col) == (0, 4) and piece == 'k':
                            self.castle_attributes[move_name] = [True, current_move_index]
                    elif increment < 0 and moved_index is not None and moved_index == current_move_index:
                            self.castle_attributes[move_name] = [False, None]

            self._move_index += increment
            # TODO Eventually, this is only for historic/completed games not live ones, will eventually rework with _latest and branching paths
            # self.whites_turn = not self.whites_turn

        if self._move_index == len(self.moves) - 1:
            self._latest = True
            if any(symbol in self.alg_moves[-1] for symbol in ['0-1', '1-0', '½–½']):
                self.end_position = True
        else:
            self._latest = False
            self.end_position = False
        
        if self._move_index != -1:
            new_recent_positions = self.moves[self._move_index]
            new_last_pos, new_current_pos = list(new_recent_positions[0]), list(new_recent_positions[1])

            new_curr_row, new_curr_col = int(new_current_pos[1]), int(new_current_pos[2])
            new_last_row, new_last_col = int(new_last_pos[1]), int(new_last_pos[2])

            self.current_position = (new_curr_row, new_curr_col)
            self.previous_position = (new_last_row, new_last_col)
        else:
            self.current_position = None
            self.previous_position = None

    def to_json(self, include_states=False):
        return json.dumps(self, cls=GameEncoder, include_states=include_states)

class GameEncoder(json.JSONEncoder):
    def __init__(self, include_states=False, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.include_states = include_states

    def default(self, obj):
        if isinstance(obj, Game):
            data = {
                "whites_turn": obj.whites_turn,
                "board": obj.board,
                "moves": obj.moves,
                "alg_moves": obj.alg_moves,
                "castle_attributes": obj.castle_attributes,
                "current_position": obj.current_position,
                "previous_position": obj.previous_position,
                "max_states": obj.max_states,
                "end_position": obj.end_position,
                "forced_end": obj.forced_end,
                "_starting_player": obj._starting_player,
                "_move_undone": obj._move_undone,
                "_sync": obj._sync,
                "_state_update": [{"key": k, "value": v} for k, v in obj._state_update.items()],
                "_max_states_reached": obj._max_states_reached
            }
            if self.include_states:
                data["board_states"] = [{"key": k, "value": v} for k, v in obj.board_states.items()]
                del data["_state_update"]
            elif obj._state_update == []:
                del data["_state_update"]

            return data
        return super().default(obj)