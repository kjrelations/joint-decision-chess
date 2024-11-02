from math import copysign
from helpers import *
import json

class Game:

    def __init__(self, board=None, starting_player=None, game_type=None, custom_params=None):
        if custom_params is None:
            if board is None or starting_player is None:
                raise ValueError("board and starting_player are required parameters when custom_params is not provided.")
            self.white_played = False
            self.black_played = False
            self.reveal_stage_enabled = True if game_type in [None, "Complete", "Relay"] else False
            self.decision_stage_enabled = True if game_type in [None, "Complete", "Countdown"] else False
            self.playing_stage = True
            self.reveal_stage = False
            self.decision_stage = False
            self.board = board
            self.moves = []
            self.alg_moves = []
            self.castle_attributes = {
                'white_king_moved' : [False, None], # TODO update using board
                'left_white_rook_moved' : [False, None],
                'right_white_rook_moved' : [False, None],
                'black_king_moved' : [False, None],
                'left_black_rook_moved' : [False, None],
                'right_black_rook_moved' : [False, None]
            }
            self.white_active_move = None
            self.black_active_move = None
            self.white_current_position = None
            self.white_previous_position = None
            self.black_current_position = None
            self.black_previous_position = None
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
            self.white_lock = False
            self.black_lock = False
            self.decision_stage_complete = False
            self.white_undo_count = 0
            self.black_undo_count = 0
            self._starting_player = starting_player
            self._move_undone = False
            self._sync = True
            self._move_index = -1
            self._latest = True
            self._state_update = {}
            self._promotion_white = None
            self._promotion_black = None
            self._set_last_move = False
            self._temp_actives = None
            self._max_states_reached = False
        else:
            self.white_played = custom_params["white_played"]
            self.black_played = custom_params["black_played"]
            self.reveal_stage_enabled = custom_params["reveal_stage_enabled"]
            self.decision_stage_enabled = custom_params["decision_stage_enabled"]
            self.playing_stage = custom_params["playing_stage"]
            self.reveal_stage = custom_params["reveal_stage"]
            self.decision_stage = custom_params["decision_stage"]
            self.board = custom_params["board"]
            self.moves = custom_params["moves"]
            self.alg_moves = custom_params["alg_moves"]
            self.castle_attributes = custom_params["castle_attributes"]
            self.white_active_move = custom_params["white_active_move"]
            self.black_active_move = custom_params["black_active_move"]
            self.white_current_position = custom_params["white_current_position"]
            self.white_previous_position = custom_params["white_previous_position"]
            self.black_current_position = custom_params["black_current_position"]
            self.black_previous_position = custom_params["black_previous_position"]
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
            self.white_lock = custom_params["white_lock"]
            self.black_lock = custom_params["black_lock"]
            self.decision_stage_complete = custom_params["decision_stage_complete"]
            self.white_undo_count = custom_params["white_undo_count"]
            self.black_undo_count = custom_params["black_undo_count"]
            self._starting_player = custom_params["_starting_player"]
            self._move_undone = custom_params["_move_undone"]
            self._sync = custom_params["_sync"]
            self._move_index = len(self.moves) - 1 # This could be custom eventually
            self._latest = True # I think this will always default to true for now, could be a custom move in the future
            self._promotion_white = custom_params["_promotion_white"]
            self._promotion_black = custom_params["_promotion_black"]
            self._set_last_move = custom_params["_set_last_move"]
            self._temp_actives = None
            self._max_states_reached = custom_params["_max_states_reached"]

    def synchronize(self, new_game):
        self.board = new_game.board
        self.moves = new_game.moves
        self.alg_moves = new_game.alg_moves
        self.castle_attributes = new_game.castle_attributes
        illegal = False
        if self.white_played and new_game.black_played and not new_game.white_played:
            self.black_played = new_game.black_played
            self.black_active_move = new_game.black_active_move
            self.black_active_move[2] = '2'
            if self._temp_actives is not None:
                self._temp_actives[1] = self.black_active_move
            self._promotion_black = new_game._promotion_black
            # TODO add special
            _, illegal = self.update_state(self.black_active_move[1][0], self.black_active_move[1][1], self.black_active_move[0], update_positions=False)
        elif self.black_played and new_game.white_played and not new_game.black_played:
            self.white_played = new_game.white_played
            self.white_active_move = new_game.white_active_move
            self.white_active_move[2] = '2'
            if self._temp_actives is not None:
                self._temp_actives[0] = self.white_active_move
            self._promotion_white = new_game._promotion_white
            _, illegal = self.update_state(self.white_active_move[1][0], self.white_active_move[1][1], self.white_active_move[0], update_positions=False)
        else:
            self.white_played = new_game.white_played
            self.black_played = new_game.black_played
            self.white_active_move = new_game.white_active_move
            self.black_active_move = new_game.black_active_move
            if self._temp_actives is not None:
                self._temp_actives = [self.white_active_move, self.black_active_move]
            self._promotion_white = new_game._promotion_white
            self._promotion_black = new_game._promotion_black
        self.reveal_stage_enabled = new_game.reveal_stage_enabled
        self.decision_stage_enabled = new_game.decision_stage_enabled
        self.playing_stage = new_game.playing_stage
        self.reveal_stage = new_game.reveal_stage
        self.decision_stage = new_game.decision_stage
        self.white_current_position = new_game.white_current_position
        self.white_previous_position = new_game.white_previous_position
        self.black_current_position = new_game.black_current_position
        self.black_previous_position = new_game.black_previous_position
        if new_game._state_update:
            for state, update in new_game._state_update.items():
                if update is None:
                    del self.board_states[state]
                else:
                    self.board_states.update({state: update})
        self.end_position = new_game.end_position
        self.forced_end = new_game.forced_end
        self.white_lock = new_game.white_lock
        self.black_lock = new_game.black_lock
        self.decision_stage_complete = new_game.decision_stage_complete
        self.white_undo_count = new_game.white_undo_count
        self.black_undo_count = new_game.black_undo_count
        self._move_undone = False
        self._sync = True
        self._move_index = new_game._move_index
        self._latest = True
        self._state_update = {}
        self._max_states_reached = new_game._max_states_reached
        return illegal

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
            
            # Invalid move check
            dest_piece = self.board[move[0]][move[1]]
            if is_check(temp_board, is_white) and \
               not (piece.lower() == 'k' and dest_piece.isupper() == is_white and dest_piece != ' '):
                valid_moves.remove(move)
                if move in valid_captures:
                    valid_captures.remove(move)
            elif piece.lower() == 'k' and dest_piece.isupper() == is_white and dest_piece != ' ' and is_check(self.board, is_white):
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

    def update_state(self, new_row, new_col, selected_piece, special=False, update_positions=True):
        # Jump to current state before applying moves
        if self._move_index < len(self.moves) - 1: # should be same as not _latest
            self.step_to_move(len(self.moves) - 1)
            self._latest = True

        piece = self.board[selected_piece[0]][selected_piece[1]]

        special_string = ''
        if special and (new_row, new_col) not in [(7, 2), (7, 6), (0, 2), (0, 6)]:
            special_string = 'enpassant'
        elif special:
            special_string = 'castle'
        
        if not self.white_played or not self.black_played:
            if piece.isupper():
                self.white_played = True
                move_priority = '1' if not self.black_played else '2'
                self.white_active_move = [selected_piece, (new_row, new_col), move_priority, special_string]
            else:
                self.black_played = True
                move_priority = '1' if not self.white_played else '2'
                self.black_active_move = [selected_piece, (new_row, new_col), move_priority, special_string]
        
        if not self.white_played or not self.black_played:
            self._move_undone = False
            self._sync = True
            return False, False

        pieces_info = {
            'first': 'white' if self.white_active_move[2] == '1' else 'black',
            'white_initial_pos': tuple(self.white_active_move[0]),
            'white_piece': self.board[self.white_active_move[0][0]][self.white_active_move[0][1]],
            'new_row_white': self.white_active_move[1][0], 
            'new_col_white': self.white_active_move[1][1],
            'potential_white_capture': self.board[self.white_active_move[1][0]][self.white_active_move[1][1]],
            'black_initial_pos': tuple(self.black_active_move[0]),
            'black_piece': self.board[self.black_active_move[0][0]][self.black_active_move[0][1]],
            'new_row_black': self.black_active_move[1][0],
            'new_col_black': self.black_active_move[1][1],
            'potential_black_capture': self.board[self.black_active_move[1][0]][self.black_active_move[1][1]],
            'white_captured': False,
            'black_captured': False
        }

        self.update_blocking_positions(pieces_info)

        first = pieces_info['first']
        white_initial_pos = pieces_info['white_initial_pos']
        white_piece = pieces_info['white_piece']
        new_row_white, new_col_white = pieces_info['new_row_white'], pieces_info['new_col_white']
        potential_white_capture = pieces_info['potential_white_capture']
        white_captured = pieces_info['white_captured']
        
        black_initial_pos = pieces_info['black_initial_pos']
        black_piece = pieces_info['black_piece']
        new_row_black, new_col_black = pieces_info['new_row_black'], pieces_info['new_col_black']
        potential_black_capture = pieces_info['potential_black_capture']
        black_captured = pieces_info['black_captured']

        annihilation_superposition = None

        # Illegal guarding moves
        if self.board[new_row_white][new_col_white].isupper() \
           and (new_row_white, new_col_white) != (white_initial_pos[0], white_initial_pos[1]) \
           and (new_row_white, new_col_white) != (new_row_black, new_col_black):
            self.white_active_move = None
            self.white_played = False
            return False, True
        if self.board[new_row_black][new_col_black].islower() \
           and (new_row_black, new_col_black) != (black_initial_pos[0], black_initial_pos[1]) \
           and (new_row_white, new_col_white) != (new_row_black, new_col_black):
            self.black_active_move = None
            self.black_played = False
            return False, True
        # King moves
        if white_piece == 'K':
            if black_piece != 'k' and (new_row_black, new_col_black) == (new_row_white, new_col_white):
                # Covers superposition or king superposition
                capture = self.board[new_row_black][new_col_black]
                potential_black_capture = capture if capture.isupper() else ' '
                potential_white_capture = black_piece if capture.isupper() else [capture, black_piece]
                black_captured = True
                white_captured = False
                annihilation_superposition = capture
            elif black_piece == 'k' and (new_row_black, new_col_black) == (new_row_white, new_col_white):
                if first == 'white':
                    self.black_active_move = None
                    self.black_played = False
                else:
                    self.white_active_move = None
                    self.white_played = False
                return False, True
        elif black_piece == 'k' and (new_row_white, new_col_white) == (new_row_black, new_col_black):
            # Covers superposition or king superposition
            capture = self.board[new_row_white][new_col_white]
            potential_white_capture = capture if capture.islower() else ' '
            potential_black_capture = white_piece if capture.islower() else [capture, white_piece]
            white_captured = True
            black_captured = False
            annihilation_superposition = capture
        # Annihilation and Superposition moves
        elif (new_row_white, new_col_white) == (new_row_black, new_col_black):
            if self.board[new_row_white][new_col_white].isupper():
                potential_white_capture = black_piece
                black_captured = True
                annihilation_superposition = self.board[new_row_white][new_col_white]
            elif self.board[new_row_black][new_col_black].islower():
                potential_black_capture = white_piece
                white_captured = True
                annihilation_superposition = self.board[new_row_black][new_col_black]
            else:
                potential_white_capture = black_piece
                potential_black_capture = white_piece
                white_captured = True
                black_captured = True
                annihilation_superposition = self.board[new_row_white][new_col_white]

        enpassant_white, enpassant_black, castle_white, castle_black = False, False, False, False
        if self.white_active_move[-1] == 'enpassant':
            capture_row = 3 if new_row_white == 2 else 4
            potential_white_capture = [self.board[capture_row][new_col_white], potential_white_capture] \
                if potential_white_capture != ' ' else self.board[capture_row][new_col_white]
            enpassant_white = True
            black_captured = True if black_initial_pos == (capture_row, new_col_white) else black_captured
        if self.black_active_move[-1] == 'enpassant':
            capture_row = 3 if new_row_black == 2 else 4
            potential_black_capture = [self.board[capture_row][new_col_black], potential_black_capture] \
                if potential_black_capture != ' ' else self.board[capture_row][new_col_black]
            enpassant_black = True
            white_captured = True if white_initial_pos == (capture_row, new_col_black) else white_captured
        if self.white_active_move[-1] == 'castle':
            castle_white = True
        if self.black_active_move[-1] == 'castle':
            castle_black = True

        if (new_row_white, new_col_white) == (new_row_black, new_col_black) and self._promotion_black is not None:
            if isinstance(potential_white_capture, list):
                potential_white_capture[1] = self._promotion_black
            else:
                potential_white_capture = self._promotion_black
        if (new_row_white, new_col_white) == (new_row_black, new_col_black) and self._promotion_white is not None:
            if isinstance(potential_white_capture, list):
                potential_black_capture[1] = self._promotion_white
            else:
                potential_black_capture = self._promotion_white

        def update_specials(board, new_row, new_col, enpassant, castle, captured, new_row_other, new_col_other):
            if enpassant:
                capture_row = 3 if new_row == 2 else 4
                if not captured:
                    board[capture_row][new_col] = ' '
            elif castle:
                if (new_row, new_col) == (7, 2) and (new_row_other, new_col_other) != (7, 0):
                    board[7][3] = 'R'
                    board[7][0] = ' '
                elif (new_row, new_col) == (7, 6) and (new_row_other, new_col_other) != (7, 7):
                    board[7][5] = 'R'
                    board[7][7] = ' '
                elif (new_row, new_col) == (0, 2) and (new_row_other, new_col_other) != (0, 0):
                    board[0][3] = 'r'
                    board[0][0] = ' '
                elif (new_row, new_col) == (0, 6) and (new_row_other, new_col_other) != (0, 7):
                    board[0][5] = 'r'
                    board[0][7] = ' '
            return board
        
        def update_board(
            self,
            board, 
            white_initial_pos, 
            black_initial_pos, 
            white_captured, 
            black_captured, 
            new_row_white, 
            new_col_white, 
            new_row_black, 
            new_col_black,
            white_piece,
            black_piece,
            enpassant_white,
            enpassant_black,
            castle_white,
            castle_black,
            update_positions
            ):
            if not update_positions:
                return board
            board[white_initial_pos[0]][white_initial_pos[1]] = ' '
            board[black_initial_pos[0]][black_initial_pos[1]] = ' '
            if not white_captured:
                board[new_row_white][new_col_white] = white_piece if self._promotion_white is None else self._promotion_white
            if not black_captured:
                board[new_row_black][new_col_black] = black_piece if self._promotion_black is None else self._promotion_black

            board = update_specials(board, new_row_white, new_col_white, enpassant_white, castle_white, white_captured, new_row_black, new_col_black)
            board = update_specials(board, new_row_black, new_col_black, enpassant_black, castle_black, black_captured, new_row_white, new_col_white)
            return board
        
        # Update a temp_board first for correct algebraic moves
        temp_board = deepcopy_list_of_lists(self.board)
        temp_board = update_board(
            self, 
            temp_board, 
            white_initial_pos, 
            black_initial_pos,
            white_captured, 
            black_captured, 
            new_row_white, 
            new_col_white, 
            new_row_black, 
            new_col_black,
            white_piece,
            black_piece,
            enpassant_white,
            enpassant_black,
            castle_white,
            castle_black,
            update_positions
        )
        
        # Need to calculate alg_moves before we update board to settle disambiguities
        white_algebraic_move = self.translate_into_notation(new_row_white, new_col_white, white_piece, white_initial_pos, potential_white_capture, castle_white, temp_board)
        black_algebraic_move = self.translate_into_notation(new_row_black, new_col_black, black_piece, black_initial_pos, potential_black_capture, castle_black, temp_board)
        
        self.board = update_board(
            self,
            self.board,
            white_initial_pos, 
            black_initial_pos,
            white_captured, 
            black_captured, 
            new_row_white, 
            new_col_white, 
            new_row_black, 
            new_col_black,
            white_piece,
            black_piece,
            enpassant_white,
            enpassant_black,
            castle_white,
            castle_black,
            update_positions
        )

        if self.reveal_stage_enabled and self.playing_stage:
            self.playing_stage = False
            self.reveal_stage = True
        elif self.decision_stage_enabled and self.playing_stage:
            self.playing_stage = False
            self.decision_stage = True
        else:
            self.playing_stage = True

        if update_positions:
            same_position = (new_row_white, new_col_white) == (new_row_black, new_col_black)
            self.white_current_position = (new_row_white, new_col_white) if not white_captured or same_position else None
            self.white_previous_position = (white_initial_pos[0], white_initial_pos[1])
            self.black_current_position = (new_row_black, new_col_black) if not black_captured or same_position else None
            self.black_previous_position = (black_initial_pos[0], black_initial_pos[1])

            white_move = output_move(
                white_piece, 
                white_initial_pos, 
                new_row_white, 
                new_col_white, 
                potential_white_capture, 
                self.white_active_move[2], 
                annihilation_superposition,
                self.white_active_move[-1]
                )
            black_move = output_move(
                black_piece, 
                black_initial_pos, 
                new_row_black, 
                new_col_black, 
                potential_black_capture, 
                self.black_active_move[2], 
                annihilation_superposition,
                self.black_active_move[-1]
                )
            # This will handle out of sychronized promotion states in the synchronize function
            if self._promotion_white is not None:
                string_list = list(white_move[1])
                string_list[0] = self._promotion_white
                white_move[1] = ''.join(string_list)
                white_algebraic_move += self._promotion_white.upper()
            if self._promotion_black is not None:
                string_list = list(black_move[1])
                string_list[0] = self._promotion_black
                black_move[1] = ''.join(string_list)
                black_algebraic_move += self._promotion_black.upper()
            if self._promotion_white is not None or self._promotion_black is not None:
                white_algebraic_move = white_algebraic_move.replace('#', '').replace('+', '')
                black_algebraic_move = black_algebraic_move.replace('#', '').replace('+', '')
                for is_white in [True, False]:
                    if is_checkmate_or_stalemate(self.board, is_white, self.moves)[0]:
                        if is_white:
                            black_algebraic_move += '#'
                        else:
                            white_algebraic_move += '#'
                    elif is_check(self.board, is_white):
                        if is_white:
                            black_algebraic_move += '+'
                        else:
                            white_algebraic_move += '+'
            self.moves.append([white_move, black_move])
            self.alg_moves.append([white_algebraic_move, black_algebraic_move])
            self._move_index += 1
            self.white_played = False
            self.black_played = False
            # Need the check for is None for synchronization
            if piece.lower() == 'p' and new_row in [0, 7] \
            and (self._promotion_white is None or self._promotion_black is None):
                self._set_last_move = True
            self._promotion_white = None
            self._promotion_black = None
            self._temp_actives = None

            if white_piece == 'K' and white_initial_pos == (7, 4) and not self.castle_attributes['white_king_moved'][0]:
                self.castle_attributes['white_king_moved'] = [True, self._move_index]

                if self.white_active_move[-1] == 'castle' and (new_row_white, new_col_white) == (7, 2):
                    self.castle_attributes['left_white_rook_moved'] = [True, self._move_index]
                elif self.white_active_move[-1] == 'castle' and (new_row_white, new_col_white) == (7, 6):
                    self.castle_attributes['right_white_rook_moved'] = [True, self._move_index]
            
            elif white_piece == 'R' and white_initial_pos == (7, 0) and not self.castle_attributes['left_white_rook_moved'][0]:
                self.castle_attributes['left_white_rook_moved'] = [True, self._move_index]
            elif white_piece == 'R' and white_initial_pos == (7, 7) and not self.castle_attributes['right_white_rook_moved'][0]:
                self.castle_attributes['right_white_rook_moved'] = [True, self._move_index]
            
            if black_piece == 'k' and black_initial_pos == (0, 4) and not self.castle_attributes['black_king_moved'][0]:
                self.castle_attributes['black_king_moved'] = [True, self._move_index]

                if self.black_active_move[-1] == 'castle' and (new_row_black, new_col_black) == (0, 2):
                    self.castle_attributes['left_black_rook_moved'] = [True, self._move_index]
                elif self.black_active_move[-1] == 'castle' and (new_row_black, new_col_black) == (0, 6):
                    self.castle_attributes['right_black_rook_moved'] = [True, self._move_index]
            
            elif black_piece == 'r' and black_initial_pos == (0, 0) and not self.castle_attributes['left_black_rook_moved'][0]:
                self.castle_attributes['left_black_rook_moved'] = [True, self._move_index]
            elif black_piece == 'r' and black_initial_pos == (0, 7) and not self.castle_attributes['right_black_rook_moved'][0]:
                self.castle_attributes['right_black_rook_moved'] = [True, self._move_index]

            if (new_row_white, new_col_white) == (0, 0) and potential_white_capture is not None and \
               'r' in potential_white_capture and not self.castle_attributes['left_black_rook_moved'][0]:
                self.castle_attributes['left_black_rook_moved'] = [True, self._move_index]
            elif (new_row_white, new_col_white) == (0, 7) and potential_white_capture is not None and \
                 'r' in potential_white_capture and not self.castle_attributes['right_black_rook_moved'][0]:
                self.castle_attributes['right_black_rook_moved'] = [True, self._move_index]
            
            if (new_row_black, new_col_black) == (7, 0) and potential_black_capture is not None and \
               'R' in potential_black_capture and not self.castle_attributes['left_white_rook_moved'][0]:
                self.castle_attributes['left_white_rook_moved'] = [True, self._move_index]
            elif (new_row_black, new_col_black) == (7, 7) and potential_black_capture is not None and \
                 'R' in potential_black_capture and not self.castle_attributes['right_white_rook_moved'][0]:
                self.castle_attributes['right_white_rook_moved'] = [True, self._move_index]

            
            self.white_active_move = None
            self.black_active_move = None

            # Update state once standard moves are played, not during a pawn promotion
            if not self._set_last_move:
                self._move_undone = False
                self._sync = True
                
                # Update dictionary of board states
                current_special_moves = []
                for row in range(8):
                    for col in range(8):
                        other_piece = self.board[row][col]
                        if other_piece != ' ':
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
        
        return update_positions, False

    def update_blocking_positions(self, pieces_info):
        first = pieces_info['first']
        white_initial_pos = pieces_info['white_initial_pos']
        white_piece = pieces_info['white_piece']
        new_row_white, new_col_white = pieces_info['new_row_white'], pieces_info['new_col_white']
        potential_white_capture = pieces_info['potential_white_capture']
        white_captured = pieces_info['white_captured']
        
        black_initial_pos = pieces_info['black_initial_pos']
        black_piece = pieces_info['black_piece']
        new_row_black, new_col_black = pieces_info['new_row_black'], pieces_info['new_col_black']
        potential_black_capture = pieces_info['potential_black_capture']
        black_captured = pieces_info['black_captured']

        blocked = False
        if first == 'white':
            first_piece = white_piece
            first_init_row, first_init_col = white_initial_pos[0], white_initial_pos[1]
            first_new_row, first_new_col = new_row_white, new_col_white
            second_piece = black_piece
            second_init_row, second_init_col = black_initial_pos[0], black_initial_pos[1]
            second_new_row, second_new_col = new_row_black, new_col_black
        else:
            first_piece = black_piece 
            first_init_row, first_init_col = black_initial_pos[0], black_initial_pos[1]
            first_new_row, first_new_col = new_row_black, new_col_black
            second_piece = white_piece
            second_init_row, second_init_col = white_initial_pos[0], white_initial_pos[1]
            second_new_row, second_new_col = new_row_white, new_col_white

        # Entanglement or collapse
        if (first_new_row, first_new_col) == (second_init_row, second_init_col):
            potential_capture = None if (second_new_row, second_new_col) != (first_init_row, first_init_col) else first_piece
            if first == 'white':
                potential_black_capture = potential_capture
                black_captured = True
                white_captured = False if (second_new_row, second_new_col) != (first_init_row, first_init_col) else True
            else:
                potential_white_capture = potential_capture
                white_captured = True
                black_captured = False if (second_new_row, second_new_col) != (first_init_row, first_init_col) else True
        # Blocking
        elif second_piece.lower() in ['r', 'q'] and \
            second_init_row == second_new_row and first_new_row == second_new_row and \
            (
            (second_init_col < second_new_col and second_init_col < first_new_col < second_new_col) or \
            (second_init_col > second_new_col and second_init_col > first_new_col > second_new_col)
            ):
            if first == 'white':
                potential_black_capture = ' '
                new_col_black = new_col_white - int(copysign(1, new_col_black - black_initial_pos[1]))
            else:
                potential_white_capture = ' '
                new_col_white = new_col_black - int(copysign(1, new_col_white - white_initial_pos[1]))
            blocked = True
        elif second_piece.lower() in ['r', 'q', 'p'] and \
            second_init_col == second_new_col and first_new_col == second_new_col and \
            (
            (second_init_row < second_new_row and second_init_row < first_new_row < second_new_row) or \
            (second_init_row > second_new_row and second_init_row > first_new_row > second_new_row)
            ):
            if first == 'white':
                potential_black_capture = ' '
                new_row_black = new_row_white - int(copysign(1, new_row_black - black_initial_pos[0]))
            else:
                potential_white_capture = ' '
                new_row_white = new_row_black - int(copysign(1, new_row_white - white_initial_pos[0]))
            blocked = True
        elif second_piece.lower() in ['b', 'q'] \
            and abs(second_new_row - second_init_row) == abs(second_new_col - second_init_col):
            blocking_positions = []
            second_row_increment = int(copysign(1, second_new_row - second_init_row))
            second_col_increment = int(copysign(1, second_new_col - second_init_col))
            current_row, current_col = second_init_row + second_row_increment, second_init_col + second_col_increment
            while (current_row, current_col) != (second_new_row, second_new_col):
                blocking_positions.append((current_row, current_col))
                current_row += second_row_increment
                current_col += second_col_increment
            if (first_new_row, first_new_col) in blocking_positions:
                if first == 'white':
                    potential_black_capture = ' '
                    new_row_black = new_row_white - second_row_increment
                    new_col_black = new_col_white - second_col_increment
                else:
                    potential_white_capture = ' '
                    new_row_white = new_row_black - second_row_increment
                    new_col_white = new_col_black - second_col_increment
                blocked = True
        
        if not blocked:
            # Entanglement or collapse
            if (second_new_row, second_new_col) == (first_init_row, first_init_col):
                potential_capture = None if (first_new_row, first_new_col) != (second_init_row, second_init_col) else second_piece
                if first == 'white':
                    potential_white_capture = potential_capture
                    white_captured = True
                    black_captured = False if (first_new_row, first_new_col) != (second_init_row, second_init_col) else True
                else:
                    potential_black_capture = potential_capture
                    black_captured = True
                    white_captured = False if (first_new_row, first_new_col) != (second_init_row, second_init_col) else True
            # Blocking
            elif first_piece.lower() in ['r', 'q'] and \
                first_init_row == first_new_row and second_new_row == first_new_row and \
                (
                (first_init_col < first_new_col and first_init_col < second_new_col < first_new_col) or \
                (first_init_col > first_new_col and first_init_col > second_new_col > first_new_col)
                ):
                if first == 'white':
                    potential_white_capture = ' '
                    new_col_white = new_col_black - int(copysign(1, new_col_white - white_initial_pos[1]))
                else:
                    potential_black_capture = ' '
                    new_col_black = new_col_white - int(copysign(1, new_col_black - black_initial_pos[1]))
            elif first_piece.lower() in ['r', 'q', 'p'] and \
                first_init_col == first_new_col and second_new_col == first_new_col and \
                (
                (first_init_row < first_new_row and first_init_row < second_new_row < first_new_row) or \
                (first_init_row > first_new_row and first_init_row > second_new_row > first_new_row)
                ):
                if first == 'white':
                    potential_white_capture = ' '
                    new_row_white = new_row_black - int(copysign(1, new_row_white - white_initial_pos[0]))
                else:
                    potential_black_capture = ' '
                    new_row_black = new_row_white - int(copysign(1, new_row_black - black_initial_pos[0]))
            elif first_piece.lower() in ['b', 'q'] \
                and abs(first_new_row - first_init_row) == abs(first_new_col - first_init_col):
                blocking_positions = []
                first_row_increment = int(copysign(1, first_new_row - first_init_row))
                first_col_increment = int(copysign(1, first_new_col - first_init_col))
                current_row, current_col = first_init_row + first_row_increment, first_init_col + first_col_increment
                while (current_row, current_col) != (first_new_row, first_new_col):
                    blocking_positions.append((current_row, current_col))
                    current_row += first_row_increment
                    current_col += first_col_increment
                if (second_new_row, second_new_col) in blocking_positions:
                    if first == 'white':
                        potential_white_capture = ' '
                        new_row_white = new_row_black - first_row_increment
                        new_col_white = new_col_black - first_col_increment
                    else:
                        potential_black_capture = ' '
                        new_row_black = new_row_white - first_row_increment
                        new_col_black = new_col_white - first_col_increment
                    blocked = True
        pieces_info['white_initial_pos'] = white_initial_pos
        pieces_info['white_piece'] = white_piece
        pieces_info['new_row_white'], pieces_info['new_col_white'] = new_row_white, new_col_white
        pieces_info['potential_white_capture'] = potential_white_capture
        pieces_info['white_captured'] = white_captured
        
        pieces_info['black_initial_pos'] = black_initial_pos
        pieces_info['black_piece'] = black_piece
        pieces_info['new_row_black'], pieces_info['new_col_black'] = new_row_black, new_col_black
        pieces_info['potential_black_capture'] = potential_black_capture
        pieces_info['black_captured'] = black_captured

    def translate_into_notation(self, new_row, new_col, piece, selected_piece, potential_capture, castle, temp_board):
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
        
        if potential_capture not in [' ', None]:
            if piece.upper() == 'P' and added_file == '':
                alg_move += str(file_conversion[selected_piece[1]])
            alg_move += 'x'
        
        # Destination
        alg_move += str(file_conversion[new_col]) + str(rank_conversion[new_row])

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

    def add_end_game_notation(self, checkmate, white_wins, black_wins):
        if checkmate:
            if white_wins and not black_wins:
                symbol = '1-0'
            elif not white_wins and black_wins:
                symbol = '0-1'
            elif white_wins and black_wins:
                symbol = '1-1'
            self.alg_moves.append(symbol)
            print('ALG_MOVES: ', self.alg_moves)
        else:
            self.alg_moves.append('½–½')
            print('ALG_MOVES: ', self.alg_moves)

    def promote_to_piece(self, current_row, current_col, piece):
        is_white = piece.isupper()
        
        self._promotion_white = piece if is_white else None
        self._promotion_black = piece if not is_white else None
        move_index = 0 if is_white else 1
        if self._set_last_move:
            if is_white:
                prev_pos = (int(self.moves[-1][0][0][1]), int(self.moves[-1][0][0][2]))
                other_curr_pos = (int(self.moves[-1][1][1][1]), int(self.moves[-1][1][1][2]))
            else:
                prev_pos = (int(self.moves[-1][1][0][1]), int(self.moves[-1][1][0][2]))
                other_curr_pos = (int(self.moves[-1][0][1][1]), int(self.moves[-1][0][1][2]))
            captured = prev_pos == other_curr_pos
            if not captured:
                self.board[current_row][current_col] = piece
            # Need to edit the temporary last moves/alg_moves in state once a decision is made
            string_list = list(self.moves[-1][move_index][1])
            string_list[0] = piece
            self.moves[-1][move_index][1] = ''.join(string_list)
 
            self.alg_moves[-1][move_index] += piece.upper()
            self._promotion_white = None
            self._promotion_black = None
            self._set_last_move = False
        
            self.alg_moves[-1][0].replace('#', '').replace('+', '')
            self.alg_moves[-1][1].replace('#', '').replace('+', '')
            for is_white, index in [[True, 1], [False, 0]]:
                if is_checkmate_or_stalemate(self.board, is_white, self.moves)[0]:
                    self.alg_moves[-1][index] += '#'
                elif is_check(self.board, is_white):
                    self.alg_moves[-1][index] += '+'

            # Update dictionary of board states
            current_special_moves = []
            for row in range(8):
                for col in range(8):
                    other_piece = self.board[row][col]
                    if other_piece != ' ':
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

        self._move_undone = False
        self._sync = True
        return self._set_last_move

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
                        if current_piece != ' ':
                            _, _, specials = calculate_moves(self.board, row, col, self.moves, self.castle_attributes, True) 
                            current_special_moves.extend(specials)
                _current_board_state = tuple(tuple(r) for r in self.board)
                special_tuple = ((),) if current_special_moves == [] else tuple(tuple(s) for s in current_special_moves)
                _current_board_state = _current_board_state + special_tuple
                flat_castle_values = [value for sublist in self.castle_attributes.values() for value in sublist]
                _current_board_state = _current_board_state + (tuple(flat_castle_values),)
                
                if self.board_states.get(_current_board_state) or not self._max_states_reached:
                    if self.board_states[_current_board_state] == 1:
                        del self.board_states[_current_board_state]
                        self._state_update[_current_board_state] = None
                    else:
                        self.board_states[_current_board_state] -= 1
                        self._state_update[_current_board_state] = self.board_states[_current_board_state]
            
            self.white_active_move = None
            self.black_active_move = None
            self.white_played = False
            self.black_played = False
            self.white_lock = False
            self.black_lock = False

            moves = self.moves[-1]
            annihilation_superposition = moves[0][4]

            white_prev_pos = list(moves[0][0])
            white_curr_pos = list(moves[0][1])
            white_potential_capture = moves[0][2]
            special_white = moves[0][-1]

            white_piece, white_prev_row, white_prev_col = white_prev_pos[0], int(white_prev_pos[1]), int(white_prev_pos[2])
            white_curr_row, white_curr_col = int(white_curr_pos[1]), int(white_curr_pos[2])

            black_prev_pos = list(moves[1][0])
            black_curr_pos = list(moves[1][1])
            black_potential_capture = moves[1][2]
            special_black = moves[1][-1]

            black_piece, black_prev_row, black_prev_col = black_prev_pos[0], int(black_prev_pos[1]), int(black_prev_pos[2])
            black_curr_row, black_curr_col = int(black_curr_pos[1]), int(black_curr_pos[2])

            self.board[white_prev_row][white_prev_col] = white_piece
            self.board[black_prev_row][black_prev_col] = black_piece
            if (black_curr_row, black_curr_col) != (white_curr_row, white_curr_col):
                white_null_condition = isinstance(white_potential_capture, list) and None in white_potential_capture
                if special_white != 'enpassant':
                    if (white_curr_row, white_curr_col) != (white_prev_row, white_prev_col) \
                       and white_potential_capture is not None:
                        self.board[white_curr_row][white_curr_col] = white_potential_capture
                else:
                    if white_potential_capture is not None and not white_null_condition:
                        self.board[white_curr_row][white_curr_col] = ' '
                        self.board[white_prev_row][white_curr_col] = white_potential_capture
                black_null_condition = isinstance(black_potential_capture, list) and None in black_potential_capture
                if special_black != 'enpassant':
                    if (black_curr_row, black_curr_col) != (black_prev_row, black_prev_col) \
                       and black_potential_capture is not None:
                        self.board[black_curr_row][black_curr_col] = black_potential_capture
                else:
                    if black_potential_capture is not None and not black_null_condition:
                        self.board[black_curr_row][black_curr_col] = ' '
                        self.board[black_prev_row][black_curr_col] = black_potential_capture
            else:
                if isinstance(black_potential_capture, list):
                    potential_capture = black_potential_capture[0]
                elif isinstance(white_potential_capture, list):
                    potential_capture = white_potential_capture[0]
                else:
                    potential_capture = black_potential_capture if black_potential_capture != ' ' else white_potential_capture
                if special_white == 'enpassant':
                    self.board[white_curr_row][white_curr_col] = ' '
                    self.board[white_prev_row][white_curr_col] = potential_capture
                elif special_black == 'enpassant':
                    self.board[black_curr_row][black_curr_col] = ' '
                    self.board[black_prev_row][black_curr_col] = potential_capture
                else:
                    self.board[white_curr_row][white_curr_col] = potential_capture
                if annihilation_superposition is not None:
                    self.board[white_curr_row][white_curr_col] = annihilation_superposition
            
            if special_white == 'castle':
                if (white_curr_row, white_curr_col) == (7, 2):
                    self.board[7][0] = 'R'
                    self.board[7][3] = ' '
                    self.castle_attributes['white_king_moved'] = [False, None]
                    self.castle_attributes['left_white_rook_moved'] = [False, None]
                elif (white_curr_row, white_curr_col) == (7, 6):
                    self.board[7][7] = 'R'
                    self.board[7][5] = ' '
                    self.castle_attributes['white_king_moved'] = [False, None]
                    self.castle_attributes['right_white_rook_moved'] = [False, None]
            if special_black == 'castle':
                if (black_curr_row, black_curr_col) == (0, 2):
                    self.board[0][0] = 'r'
                    self.board[0][3] = ' '
                    self.castle_attributes['black_king_moved'] = [False, None]
                    self.castle_attributes['left_black_rook_moved'] = [False, None]
                elif (black_curr_row, black_curr_col) == (0, 6):
                    self.board[0][7] = 'r'
                    self.board[0][5] = ' '
                    self.castle_attributes['black_king_moved'] = [False, None]
                    self.castle_attributes['right_black_rook_moved'] = [False, None]
            if special_white == '' or special_black == '':
                for move_name, moved_attributes in self.castle_attributes.items():
                    moved_index = moved_attributes[1]
                    if moved_index is not None and moved_index == self._move_index:
                        self.castle_attributes[move_name] = [False, None]

            del self.moves[-1]
            del self.alg_moves[-1]
            self.playing_stage = True
            self.reveal_stage = False
            self.decision_stage = False
            self._temp_actives = None
            self._move_index -= 1
            self._move_undone = True
            self._sync = False
            self._promotion_white = None
            self._promotion_black = None

            if len(self.moves) != 0:
                new_recent_positions = self.moves[-1]
                new_white_last_pos, new_white_current_pos = list(new_recent_positions[0][0]), list(new_recent_positions[0][1])

                new_white_curr_row, new_white_curr_col = int(new_white_current_pos[1]), int(new_white_current_pos[2])
                new_white_last_row, new_white_last_col = int(new_white_last_pos[1]), int(new_white_last_pos[2])

                self.white_current_position = (new_white_curr_row, new_white_curr_col)
                self.white_previous_position = (new_white_last_row, new_white_last_col)

                new_black_last_pos, new_black_current_pos = list(new_recent_positions[1][0]), list(new_recent_positions[1][1])

                new_black_curr_row, new_black_curr_col = int(new_black_current_pos[1]), int(new_black_current_pos[2])
                new_black_last_row, new_black_last_col = int(new_black_last_pos[1]), int(new_black_last_pos[2])

                self.black_current_position = (new_black_curr_row, new_black_curr_col)
                self.black_previous_position = (new_black_last_row, new_black_last_col)
            else:
                self.white_current_position = None
                self.white_previous_position = None
                self.black_current_position = None
                self.black_previous_position = None
        else:
            self.white_active_move = None
            self.black_active_move = None
            self.white_played = False
            self.black_played = False
            self.white_lock = False
            self.black_lock = False
            self.playing_stage = True
            self.reveal_stage = False
            self.decision_stage = False
            self._move_undone = True
            self._sync = False
    
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
            moves = self.moves[current_move_index]
            annihilation_superposition = moves[0][4]

            white_prev_pos = list(moves[0][0])
            white_curr_pos = list(moves[0][1])
            white_potential_capture = moves[0][2]
            special_white = moves[0][-1]

            white_piece = white_prev_pos[0] if increment < 0 else white_curr_pos[0]
            white_prev_row, white_prev_col = int(white_prev_pos[1]), int(white_prev_pos[2])
            white_curr_row, white_curr_col = int(white_curr_pos[1]), int(white_curr_pos[2])

            black_prev_pos = list(moves[1][0])
            black_curr_pos = list(moves[1][1])
            black_potential_capture = moves[1][2]
            special_black = moves[1][-1]

            black_piece = black_prev_pos[0] if increment < 0 else black_curr_pos[0]
            black_prev_row, black_prev_col = int(black_prev_pos[1]), int(black_prev_pos[2])
            black_curr_row, black_curr_col = int(black_curr_pos[1]), int(black_curr_pos[2])
            
            def step_move(
                special, 
                board, 
                color_potential_capture, 
                curr_row, 
                curr_col, 
                prev_row, 
                prev_col, 
                other_curr_row, 
                other_curr_col, 
                color_piece, 
                other_color_piece
            ):
                if (prev_row, prev_col) == (curr_row, curr_col):
                    return board
                is_white = color_piece.isupper()
                allied_king = 'K' if is_white else 'k'
                opposing_king = 'k' if is_white else 'K'
                if is_white:
                    allied_piece = board[curr_row][curr_col].isupper()
                    opposing_piece = board[curr_row][curr_col].islower()
                else:
                    allied_piece = board[curr_row][curr_col].islower()
                    opposing_piece = board[curr_row][curr_col].isupper()
                if special != 'enpassant':
                    potential_capture = color_potential_capture
                    if isinstance(color_potential_capture, list):
                        potential_capture = color_potential_capture[0]
                    new_piece = color_piece
                    update = True
                    if (curr_row, curr_col) == (other_curr_row, other_curr_col):
                        if (color_piece == allied_king or allied_piece) and other_color_piece != opposing_king:
                            new_piece = color_piece  
                        else:
                            new_piece = other_color_piece if other_color_piece == opposing_king or opposing_piece else ' '
                    elif (prev_row, prev_col) == (other_curr_row, other_curr_col) and increment > 0:
                        update = False
                    replacement = potential_capture if increment < 0 else new_piece
                    fill = color_piece if increment < 0 else ' '
                    if update and replacement is not None:
                        board[curr_row][curr_col] = replacement
                    board[prev_row][prev_col] = fill
                else:
                    null_condition = False
                    potential_capture = color_potential_capture
                    if isinstance(color_potential_capture, list):
                        null_condition = None in potential_capture
                        potential_capture = color_potential_capture[0]
                    new_piece = color_piece
                    if (curr_row, curr_col) == (other_curr_row, other_curr_col):
                        new_piece = ' ' if other_color_piece != opposing_king else other_color_piece
                    move_replacement = ' ' if increment < 0 else new_piece
                    capture_replacement = potential_capture if increment < 0 else ' '
                    board[curr_row][curr_col] = move_replacement
                    if capture_replacement is not None and not null_condition:
                        board[prev_row][curr_col] = capture_replacement
                return board
            
            self.board = step_move(
                special_white, 
                self.board, 
                white_potential_capture,
                white_curr_row,
                white_curr_col,
                white_prev_row,
                white_prev_col,
                black_curr_row,
                black_curr_col,
                white_piece,
                black_piece
                )
            self.board = step_move(
                special_black, 
                self.board, 
                black_potential_capture,
                black_curr_row,
                black_curr_col,
                black_prev_row,
                black_prev_col,
                white_curr_row,
                white_curr_col,
                black_piece,
                white_piece
                )
            if annihilation_superposition and increment < 0:
                self.board[white_curr_row][white_curr_col] = annihilation_superposition
            
            if special_white == 'castle':
                if (white_curr_row, white_curr_col) == (7, 2):
                    self.board[7][0] = ' ' if increment > 0 else 'R'
                    self.board[7][3] = 'R' if increment > 0 else ' '
                    self.castle_attributes['white_king_moved'] = [False, None] if increment < 0 else [True, current_move_index]
                    self.castle_attributes['left_white_rook_moved'] = [False, None] if increment < 0 else [True, current_move_index]
                elif (white_curr_row, white_curr_col) == (7, 6):
                    self.board[7][7] = ' ' if increment > 0 else 'R'
                    self.board[7][5] = 'R' if increment > 0 else ' '
                    self.castle_attributes['white_king_moved'] = [False, None] if increment < 0 else [True, current_move_index]
                    self.castle_attributes['right_white_rook_moved'] = [False, None] if increment < 0 else [True, current_move_index]
            elif special_black == 'castle':
                if (black_curr_row, black_curr_col) == (0, 2):
                    self.board[0][0] = ' ' if increment > 0 else 'r'
                    self.board[0][3] = 'r' if increment > 0 else ' '
                    self.castle_attributes['black_king_moved'] = [False, None] if increment < 0 else [True, current_move_index]
                    self.castle_attributes['left_black_rook_moved'] = [False, None] if increment < 0 else [True, current_move_index]
                elif (black_curr_row, black_curr_col) == (0, 6):
                    self.board[0][7] = ' ' if increment > 0 else 'r'
                    self.board[0][5] = 'r' if increment > 0 else ' '
                    self.castle_attributes['black_king_moved'] = [False, None] if increment < 0 else [True, current_move_index]
                    self.castle_attributes['right_black_rook_moved'] = [False, None] if increment < 0 else [True, current_move_index]
            if special_white != 'castle' or special_black != 'castle':
                for move_name, moved_attributes in self.castle_attributes.items():
                    moved_index = moved_attributes[1]
                    if increment > 0 and moved_index is None:
                        if (white_prev_row, white_prev_col) in [(7, 0), (7, 7)] and white_piece == 'R':
                            self.castle_attributes[move_name] = [True, current_move_index]
                        elif (black_prev_row, black_prev_col) in [(0, 0), (0, 7)] and black_piece == 'r':
                            self.castle_attributes[move_name] = [True, current_move_index]
                        elif (white_prev_row, white_prev_col) == (7, 4) and white_piece == 'K':
                            self.castle_attributes[move_name] = [True, current_move_index]
                        elif (black_prev_row, black_prev_col) == (0, 4) and black_piece == 'k':
                            self.castle_attributes[move_name] = [True, current_move_index]
                    elif increment < 0 and moved_index is not None and moved_index == current_move_index:
                            self.castle_attributes[move_name] = [False, None]

            self._move_index += increment

        if self._move_index == len(self.moves) - 1:
            self._latest = True
            if self._temp_actives is not None:
                self.white_active_move = self._temp_actives[0]
                self.black_active_move = self._temp_actives[1]
                self._temp_actives = None
            if any(symbol in self.alg_moves[-1] for symbol in ['1-1', '0-1', '1-0', '1-1', '½–½']):
                self.end_position = True
        else:
            if self.white_active_move is not None or self.black_active_move is not None:
                self._temp_actives = [self.white_active_move, self.black_active_move]
                self.white_active_move = None
                self.black_active_move = None
            self._latest = False
            self.end_position = False
        
        if self._move_index != -1:
            new_recent_positions = self.moves[self._move_index]
            new_white_last_pos, new_white_current_pos = list(new_recent_positions[0][0]), list(new_recent_positions[0][1])

            new_white_curr_row, new_white_curr_col = int(new_white_current_pos[1]), int(new_white_current_pos[2])
            new_white_last_row, new_white_last_col = int(new_white_last_pos[1]), int(new_white_last_pos[2])

            self.white_current_position = (new_white_curr_row, new_white_curr_col)
            self.white_previous_position = (new_white_last_row, new_white_last_col)

            new_black_last_pos, new_black_current_pos = list(new_recent_positions[1][0]), list(new_recent_positions[1][1])

            new_black_curr_row, new_black_curr_col = int(new_black_current_pos[1]), int(new_black_current_pos[2])
            new_black_last_row, new_black_last_col = int(new_black_last_pos[1]), int(new_black_last_pos[2])

            self.black_current_position = (new_black_curr_row, new_black_curr_col)
            self.black_previous_position = (new_black_last_row, new_black_last_col)

        else:
            self.white_current_position = None
            self.white_previous_position = None
            self.black_current_position = None
            self.black_previous_position = None

    def to_json(self, include_states=False):
        return json.dumps(self, cls=GameEncoder, include_states=include_states)

class GameEncoder(json.JSONEncoder):
    def __init__(self, include_states=False, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.include_states = include_states

    def default(self, obj):
        if isinstance(obj, Game):
            data = {
                "white_played": obj.white_played,
                "black_played": obj.black_played,
                "reveal_stage_enabled": obj.reveal_stage_enabled,
                "decision_stage_enabled": obj.decision_stage_enabled,
                "playing_stage": obj.playing_stage,
                "reveal_stage": obj.reveal_stage,
                "decision_stage": obj.decision_stage,
                "board": obj.board,
                "moves": obj.moves,
                "alg_moves": obj.alg_moves,
                "castle_attributes": obj.castle_attributes,
                "white_active_move": obj.white_active_move,
                "black_active_move": obj.black_active_move,
                "white_current_position": obj.white_current_position,
                "white_previous_position": obj.white_previous_position,
                "black_current_position": obj.black_current_position,
                "black_previous_position": obj.black_previous_position,
                "max_states": obj.max_states,
                "end_position": obj.end_position,
                "forced_end": obj.forced_end,
                "white_lock": obj.white_lock,
                "black_lock": obj.black_lock,
                "decision_stage_complete": obj.decision_stage_complete,
                "white_undo_count": obj.white_undo_count,
                "black_undo_count": obj.black_undo_count,
                "_starting_player": obj._starting_player,
                "_move_undone": obj._move_undone,
                "_sync": obj._sync,
                "_state_update": [{"key": k, "value": v} for k, v in obj._state_update.items()],
                "_promotion_white": obj._promotion_white,
                "_promotion_black": obj._promotion_black,
                "_set_last_move": obj._set_last_move,
                "_max_states_reached": obj._max_states_reached
            }
            if self.include_states:
                data["board_states"] = [{"key": k, "value": v} for k, v in obj.board_states.items()]
                del data["_state_update"]
            elif obj._state_update == []:
                del data["_state_update"]

            return data
        return super().default(obj)