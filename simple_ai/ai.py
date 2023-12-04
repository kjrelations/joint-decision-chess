# In progress simple ai 
import time
from game import *

global_pos = {"position_count": 0}

def ai_move(game, init, drawing_settings):
    if game._starting_player == game.current_turn:
        return
    
    opponent_positions = []
    for row in range(len(game.board)):
        for col in range(8):
            piece = game.board[row][col]
            is_white = piece.isupper()
            if piece != ' ' and game.current_turn != is_white:
                opponent_positions.append((row, col))

    selected_piece, best_move, promotion_piece, special = get_best_move(game, global_pos)
    row, col = best_move
    
    ai_handle_piece_move(game, selected_piece, row, col, special=special, promotion_piece=promotion_piece)

    if piece.lower() != 'p' or (piece.lower() == 'p' and (row != 7 and row != 0)):
        print("ALG_MOVES:", game.alg_moves)

    # Replace following with subsequent version and in other main scripts
    if special and (row, col) in [(7, 2), (7, 6), (0, 2), (0, 6)]:
        move_sound.play()
    elif special:
        capture_sound.play()
    elif (row, col) in opponent_positions:
        capture_sound.play()
    else:
        move_sound.play()

    drawing_settings["recalc_selections"] = True
    if game.alg_moves != []:
        if not any(symbol in game.alg_moves[-1] for symbol in ['0-1', '1-0', '½–½']): # Could add a winning or losing sound
            if "x" not in game.alg_moves[-1]:
                move_sound.play()
            else:
                capture_sound.play()
        if game.end_position:
            is_white = game.current_turn
            checkmate, remaining_moves = is_checkmate_or_stalemate(game.board, is_white, game.moves)
            if checkmate:
                print("CHECKMATE")
            elif remaining_moves == 0:
                print("STALEMATE")
            elif game.threefold_check():
                print("DRAW BY THREEFOLD REPETITION")
            elif game.forced_end != "":
                print(game.forced_end)
            print("ALG_MOVES: ", game.alg_moves)
    init["sent"] = 0

def new_game_board_moves(game):
    all_valid_moves = []
    all_valid_specials = []
    for row in range(len(game.board)):
        for col in range(8):
            piece = game.board[row][col]
            is_white = piece.isupper()
            if piece != ' ' and game.current_turn == is_white:
                valid_moves, _, valid_specials = game.validate_moves(row, col)
                if valid_moves != []:
                    if piece.lower() == 'p':
                        valid_moves = [
                            [move] + ([elem.upper() if piece.isupper() else elem for elem in ['q', 'r', 'n', 'b']])
                            if move[0] in (0, 7)
                            else move
                            for move in valid_moves
                        ]
                    all_valid_moves.append([(row, col), valid_moves])
                if valid_specials != []:
                    all_valid_specials.append([(row, col), valid_specials])
    special_index_start = len(all_valid_moves)
    all_valid_moves.extend(all_valid_specials)
    return all_valid_moves, special_index_start

def get_piece_value(piece, row, col):
    if piece == ' ':
        return 0
    is_white = piece.isupper()
    def get_absolute_value(piece, is_white):
        type = piece.lower()
        if type == 'p':
            return 10 + (pawn_eval_white[row][col] if is_white else pawn_eval_black[row][col])
        elif type == 'n':
            return 30 + knight_eval[row][col]
        elif type == 'b':
            return 30 + (bishop_eval_white[row][col] if is_white else bishop_eval_black[row][col])
        elif type == 'r':
            return 50 + (rook_eval_white[row][col] if is_white else rook_eval_black[row][col])
        elif type == 'q':
            return 90 + queen_eval[row][col]
        elif type == 'k':
            return 900 + (king_eval_white[row][col] if is_white else king_eval_black[row][col])
    abs_val = get_absolute_value(piece, is_white)
    piece_value = abs_val if is_white else -1 * abs_val
    return piece_value

def evaluate_board(board):
    total_value = 0
    for row in range(8):
        for col in range(8):
            total_value += get_piece_value(board[row][col], row, col)
    return total_value

def ai_handle_piece_move(game, selected_piece, row, col, special = False, promotion_piece = None):
    game.update_state(row, col, selected_piece, special = special)

    if promotion_piece:
        game.promote_to_piece(row, col, promotion_piece)

def get_best_move(game, pos):
    pos["position_count"] = 0
    depth = 2
    start = time.time()
    best_piece, best_move, best_promotion, special = minimax_root(depth, game, True, pos)
    end = time.time()
    move_time = end - start
    print("Move time: ", move_time)
    positionspers = (pos["position_count"] / move_time)
    print("Positions: ", pos["position_count"])
    print("Positions/s: ", positionspers)
    return best_piece, best_move, best_promotion, special

def minimax_root(depth, game, is_maximizing_player, pos):

    new_valid_game_moves, special_index = new_game_board_moves(game)
    best_move = -9999
    best_piece = None
    best_move_found = None
    best_promotion = None
    special = False

    for i in range(len(new_valid_game_moves)):
        selected_piece = new_valid_game_moves[i][0]
        moves = new_valid_game_moves[i][1]
        for move in moves:
            special_move = False if i < special_index else True
            if isinstance(move, list):
                row, col = move[0]
                promotion_choices = move[1]
                for promotion in promotion_choices:
                    ai_handle_piece_move(game, selected_piece, row, col, special=special_move, promotion_piece = promotion)
                    value = minimax(depth - 1, game, -10000, 10000, not is_maximizing_player, pos)
                    game.undo_move()
                    if value >= best_move:
                        best_move = value
                        best_piece = selected_piece
                        best_move_found = move
                        best_promotion = promotion
                        special = special_move
            else:
                row, col = move
                ai_handle_piece_move(game, selected_piece, row, col, special=special_move)
                value = minimax(depth - 1, game, -10000, 10000, not is_maximizing_player, pos)
                game.undo_move()
                if value >= best_move:
                    best_move = value
                    best_piece = selected_piece
                    best_move_found = move
                    best_promotion = None
                    special = special_move
    return best_piece, best_move_found, best_promotion, special

def minimax(depth, game, alpha, beta, is_maximizing_player, pos):
    pos["position_count"] += 1
    if depth == 0:
        return -evaluate_board(game.board)
    
    new_valid_game_moves, special_index = new_game_board_moves(game)

    best_move = -9999 if is_maximizing_player else 9999
    for i in range(len(new_valid_game_moves)):
        selected_piece = new_valid_game_moves[i][0]
        moves = new_valid_game_moves[i][1]
        for move in moves:
            special_move = False if i < special_index else True
            if isinstance(move, list):
                row, col = move[0]
                promotion_choices = move[1]
                for promotion in promotion_choices:
                    ai_handle_piece_move(game, selected_piece, row, col, special=special_move, promotion_piece = promotion)
                    best_move = select_minimax_optimum(best_move, depth, game, alpha, beta, is_maximizing_player, pos)
                    game.undo_move()
                    alpha, beta = alpha_beta_calc(alpha, beta, best_move, is_maximizing_player)
                    if beta <= alpha:
                        return best_move
            else:
                row, col = move
                ai_handle_piece_move(game, selected_piece, row, col, special=special_move)
                best_move = select_minimax_optimum(best_move, depth, game, alpha, beta, is_maximizing_player, pos)
                game.undo_move()
                alpha, beta = alpha_beta_calc(alpha, beta, best_move, is_maximizing_player)
                if beta <= alpha:
                    return best_move
    return best_move

def select_minimax_optimum(best_move, depth, game, alpha, beta, is_maximizing_player, pos):
    if is_maximizing_player:
        return max(best_move, minimax(depth - 1, game, alpha, beta, not is_maximizing_player, pos))
    else:
        return min(best_move, minimax(depth - 1, game, alpha, beta, not is_maximizing_player, pos))
    
def alpha_beta_calc(alpha, beta, best_move, is_maximizing_player):
    if is_maximizing_player:
        return max(alpha, best_move), beta
    else:
        return alpha, min(beta, best_move)
    
pawn_eval_white =[
    [0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0],
    [5.0,  5.0,  5.0,  5.0,  5.0,  5.0,  5.0,  5.0],
    [1.0,  1.0,  2.0,  3.0,  3.0,  2.0,  1.0,  1.0],
    [0.5,  0.5,  1.0,  2.5,  2.5,  1.0,  0.5,  0.5],
    [0.0,  0.0,  0.0,  2.0,  2.0,  0.0,  0.0,  0.0],
    [0.5, -0.5, -1.0,  0.0,  0.0, -1.0, -0.5,  0.5],
    [0.5,  1.0, 1.0,  -2.0, -2.0,  1.0,  1.0,  0.5],
    [0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0]
]

pawn_eval_black = reverse_chessboard(pawn_eval_white)

knight_eval =[
    [-5.0, -4.0, -3.0, -3.0, -3.0, -3.0, -4.0, -5.0],
    [-4.0, -2.0,  0.0,  0.0,  0.0,  0.0, -2.0, -4.0],
    [-3.0,  0.0,  1.0,  1.5,  1.5,  1.0,  0.0, -3.0],
    [-3.0,  0.5,  1.5,  2.0,  2.0,  1.5,  0.5, -3.0],
    [-3.0,  0.0,  1.5,  2.0,  2.0,  1.5,  0.0, -3.0],
    [-3.0,  0.5,  1.0,  1.5,  1.5,  1.0,  0.5, -3.0],
    [-4.0, -2.0,  0.0,  0.5,  0.5,  0.0, -2.0, -4.0],
    [-5.0, -4.0, -3.0, -3.0, -3.0, -3.0, -4.0, -5.0]
]

bishop_eval_white = [
    [ -2.0, -1.0, -1.0, -1.0, -1.0, -1.0, -1.0, -2.0],
    [ -1.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0, -1.0],
    [ -1.0,  0.0,  0.5,  1.0,  1.0,  0.5,  0.0, -1.0],
    [ -1.0,  0.5,  0.5,  1.0,  1.0,  0.5,  0.5, -1.0],
    [ -1.0,  0.0,  1.0,  1.0,  1.0,  1.0,  0.0, -1.0],
    [ -1.0,  1.0,  1.0,  1.0,  1.0,  1.0,  1.0, -1.0],
    [ -1.0,  0.5,  0.0,  0.0,  0.0,  0.0,  0.5, -1.0],
    [ -2.0, -1.0, -1.0, -1.0, -1.0, -1.0, -1.0, -2.0]
]

bishop_eval_black = reverse_chessboard(bishop_eval_white)

rook_eval_white = [
    [  0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0],
    [  0.5,  1.0,  1.0,  1.0,  1.0,  1.0,  1.0,  0.5],
    [ -0.5,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0, -0.5],
    [ -0.5,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0, -0.5],
    [ -0.5,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0, -0.5],
    [ -0.5,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0, -0.5],
    [ -0.5,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0, -0.5],
    [  0.0,   0.0, 0.0,  0.5,  0.5,  0.0,  0.0,  0.0]
]

rook_eval_black = reverse_chessboard(rook_eval_white)

queen_eval =[
    [ -2.0, -1.0, -1.0, -0.5, -0.5, -1.0, -1.0, -2.0],
    [ -1.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0, -1.0],
    [ -1.0,  0.0,  0.5,  0.5,  0.5,  0.5,  0.0, -1.0],
    [ -0.5,  0.0,  0.5,  0.5,  0.5,  0.5,  0.0, -0.5],
    [  0.0,  0.0,  0.5,  0.5,  0.5,  0.5,  0.0, -0.5],
    [ -1.0,  0.5,  0.5,  0.5,  0.5,  0.5,  0.0, -1.0],
    [ -1.0,  0.0,  0.5,  0.0,  0.0,  0.0,  0.0, -1.0],
    [ -2.0, -1.0, -1.0, -0.5, -0.5, -1.0, -1.0, -2.0]
]

king_eval_white = [
    [ -3.0, -4.0, -4.0, -5.0, -5.0, -4.0, -4.0, -3.0],
    [ -3.0, -4.0, -4.0, -5.0, -5.0, -4.0, -4.0, -3.0],
    [ -3.0, -4.0, -4.0, -5.0, -5.0, -4.0, -4.0, -3.0],
    [ -3.0, -4.0, -4.0, -5.0, -5.0, -4.0, -4.0, -3.0],
    [ -2.0, -3.0, -3.0, -4.0, -4.0, -3.0, -3.0, -2.0],
    [ -1.0, -2.0, -2.0, -2.0, -2.0, -2.0, -2.0, -1.0],
    [  2.0,  2.0,  0.0,  0.0,  0.0,  0.0,  2.0,  2.0 ],
    [  2.0,  3.0,  1.0,  0.0,  0.0,  1.0,  3.0,  2.0 ]
]

king_eval_black = reverse_chessboard(king_eval_white)