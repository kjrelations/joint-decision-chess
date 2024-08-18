import time
import random
import math
import pygame
from game import *

global_pos = {"position_count": 0}

def ai_move(game, init, drawing_settings, bot):
    if not game._starting_player and game.white_played or game._starting_player and game.black_played:
        return
    
    stored = {
        "stored_white_active_move": game.white_active_move.copy() if game.white_active_move is not None else None,
        "stored_white_promote": game._promotion_white,
        "stored_black_active_move": game.black_active_move.copy() if game.black_active_move is not None else None,
        "stored_black_promote": game._promotion_black
    }

    if bot == "minimax_ai":
        try:
            moves_score_dict = get_best_move(game, global_pos)
        except Exception as e:
            if str(e) == "Quit":
                init["running"] = False
                return
    else:
        root_node = Node()
        best_node = mcts(root_node, global_pos, game)
        best_state = best_node.move
    needs_update = True
    while needs_update:
        needs_update = False if game.white_active_move is None and game.black_active_move is None else True
        if bot == "minimax_ai":
            best_move_tuple = select_best_move(moves_score_dict, game._starting_player)
            selected_piece = best_move_tuple[0]
            best_move = best_move_tuple[1]
            special = best_move_tuple[2]
            promotion_piece = best_move_tuple[3] if len(best_move_tuple) == 4 else None

            update, _ = ai_play_move(game, best_move, selected_piece, special=special, promotion_piece=promotion_piece)
        else:
            selected_piece = best_state["selected_piece"]
            best_move = best_state["move"]
            special = best_state["special"]
            promotion_piece = best_state["promotion_piece"]

            update, _ = ai_play_move(game, best_move, selected_piece, special=special, promotion_piece=promotion_piece)

        if update:
            print("ALG_MOVES:", game.alg_moves)
            needs_update = False
        elif needs_update:
            reset_state(game, stored)
            if bot == "minimax_ai":
                del moves_score_dict[best_move_tuple]
            else:
                root_node.children.remove(best_node)
                best_node = select_best_node(root_node)

    drawing_settings["recalc_selections"] = True
    if game.alg_moves != []:
        if not any(symbol in game.alg_moves[-1] for symbol in ['0-1', '1-0', '1-1', '½–½']): # Could add a winning or losing sound
            if update and ("x" in game.alg_moves[-1][0] or "x" in game.alg_moves[-1][1]):
                capture_sound.play()
            else:
                move_sound.play()
        if game.end_position:
            checkmate_white, remaining_moves_white = is_checkmate_or_stalemate(game.board, True, game.moves)
            checkmate_black, remaining_moves_black = is_checkmate_or_stalemate(game.board, False, game.moves)
            checkmate = checkmate_white or checkmate_black
            no_remaining_moves = remaining_moves_white == 0 or remaining_moves_black == 0
            if checkmate:
                print("CHECKMATE")
            elif no_remaining_moves:
                print("STALEMATE")
            elif game.threefold_check():
                print("DRAW BY THREEFOLD REPETITION")
            elif game.forced_end != "":
                print(game.forced_end)
            print("ALG_MOVES: ", game.alg_moves)
    init["sent"] = 0

def new_game_board_moves(game, white_side):
    all_valid_moves = []
    all_valid_specials = []
    
    for row in range(len(game.board)):
        for col in range(8):
            piece = game.board[row][col]
            is_white = piece.isupper()
            if piece != ' ' and white_side == is_white:
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

def select_best_move(moves_score_dict, is_maximizing_player):
    best = -9999 if is_maximizing_player else 9999
    best_move = None
    for move, value in moves_score_dict.items():
        if is_maximizing_player and value >= best or not is_maximizing_player and value <= best:
            best = value
            best_move = move
    return best_move

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

def ai_play_move(game, move, selected_piece, special = False, promotion_piece = None):
    update, illegal = game.update_state(move[0], move[1], selected_piece, special = special)
    if promotion_piece:
        game.promote_to_piece(move[0], move[1], promotion_piece)
    return update, illegal

def ai_handle_piece_move(
        game, 
        white_selected_piece, 
        white_move, 
        black_selected_piece, 
        black_move, 
        white_special = False, 
        white_promotion_piece = None,
        black_special = False,
        black_promotion_piece = None
        ):
    _, illegal1 = ai_play_move(game, white_move, white_selected_piece, special = white_special, promotion_piece = white_promotion_piece)
    _, illegal2 = ai_play_move(game, black_move, black_selected_piece, special = black_special, promotion_piece = black_promotion_piece)
    return illegal1 or illegal2

def get_best_move(game, pos):
    pos["position_count"] = 0
    depth = 2
    start = time.time()
    moves_score_dict = minimax_root(depth, game, not game._starting_player, pos)
    end = time.time()
    move_time = end - start
    print("Move time: ", move_time)
    positionspers = (pos["position_count"] / move_time) if move_time != 0.0 else 'Instantaneous'
    print("Positions: ", pos["position_count"])
    print("Positions/s: ", positionspers)
    return moves_score_dict

def minimax_root(depth, game, is_maximizing_player, pos):

    stored = {
        "stored_white_active_move": game.white_active_move.copy() if game.white_active_move is not None else None,
        "stored_white_promote": game._promotion_white,
        "stored_black_active_move": game.black_active_move.copy() if game.black_active_move is not None else None,
        "stored_black_promote": game._promotion_black
    }

    stored_empty = {
        "stored_white_active_move": None,
        "stored_white_promote": None,
        "stored_black_active_move": None,
        "stored_black_promote": None
    }
    reset_state(game, stored_empty)

    white_new_valid_game_moves, white_special_index = new_game_board_moves(game, True)
    black_new_valid_game_moves, black_special_index = new_game_board_moves(game, False)

    moves_score_dict = {}
    if is_maximizing_player:
        for i in range(len(white_new_valid_game_moves)):
            white_selected_piece = white_new_valid_game_moves[i][0]
            white_moves = white_new_valid_game_moves[i][1]
            white_special_move = False if i < white_special_index else True
            for move in white_moves:
                if isinstance(move, list):
                    for choice in move[1]:
                        moves_score_dict[(white_selected_piece, move[0], white_special_move, choice)] = -9999 if is_maximizing_player else 9999
                else:
                    moves_score_dict[(white_selected_piece, move, white_special_move)] = -9999 if is_maximizing_player else 9999
    else:
        for i in range(len(black_new_valid_game_moves)):
            black_selected_piece = black_new_valid_game_moves[i][0]
            black_moves = black_new_valid_game_moves[i][1]
            black_special_move = False if i < black_special_index else True
            for move in black_moves:
                if isinstance(move, list):
                    for choice in move[1]:
                        moves_score_dict[(black_selected_piece, move[0], black_special_move, choice)] = -9999 if is_maximizing_player else 9999
                else:
                    moves_score_dict[(black_selected_piece, move, black_special_move)] = -9999 if is_maximizing_player else 9999
    
    for i in range(len(white_new_valid_game_moves)):
        for j in range(len(black_new_valid_game_moves)):
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    raise Exception("Quit")
            white_selected_piece = white_new_valid_game_moves[i][0]
            white_moves = white_new_valid_game_moves[i][1]
            white_special_move = False if i < white_special_index else True
            black_selected_piece = black_new_valid_game_moves[j][0]
            black_moves = black_new_valid_game_moves[j][1]
            black_special_move = False if j < black_special_index else True
            for white_move in white_moves:
                for black_move in black_moves:
                    white_move_new = white_move[0] if isinstance(white_move, list) else white_move
                    white_promotion_choices = white_move[1] if isinstance(white_move, list) else None
                    black_move_new = black_move[0] if isinstance(black_move, list) else black_move
                    black_promotion_choices = black_move[1] if isinstance(black_move, list) else None
                    if isinstance(white_move, list) and isinstance(black_move, list):
                        for white_promotion in white_promotion_choices:
                            for black_promotion in black_promotion_choices:
                                illegal = ai_handle_piece_move(
                                    game, 
                                    white_selected_piece, 
                                    white_move_new, 
                                    black_selected_piece, 
                                    black_move_new, 
                                    white_special = white_special_move, 
                                    white_promotion_piece = white_promotion,
                                    black_special = black_special_move, 
                                    black_promotion_piece = black_promotion
                                    )
                                if illegal:
                                    reset_state(game, stored_empty)
                                    continue
                                value = minimax(depth - 1, game, -10000, 10000, not is_maximizing_player, pos)
                                game.undo_move()
                                reset_state(game, stored_empty)
                                if is_maximizing_player and value >= moves_score_dict[(white_selected_piece, white_move[0], white_special_move, white_promotion)]:
                                    moves_score_dict[(white_selected_piece, white_move[0], white_special_move, white_promotion)] = value
                                elif not is_maximizing_player and value <= moves_score_dict[(black_selected_piece, black_move[0], black_special_move, black_promotion)]:
                                    moves_score_dict[(black_selected_piece, black_move[0], black_special_move, black_promotion)] = value
                    elif not isinstance(white_move, list) and isinstance(black_move, list):
                        for black_promotion in black_promotion_choices:
                            illegal = ai_handle_piece_move(
                                game, 
                                white_selected_piece, 
                                white_move_new, 
                                black_selected_piece, 
                                black_move_new, 
                                white_special = white_special_move, 
                                white_promotion_piece = None,
                                black_special = black_special_move, 
                                black_promotion_piece = black_promotion
                                )
                            if illegal:
                                reset_state(game, stored_empty)
                                continue
                            value = minimax(depth - 1, game, -10000, 10000, not is_maximizing_player, pos)
                            game.undo_move()
                            reset_state(game, stored_empty)
                            if is_maximizing_player and value >= moves_score_dict[(white_selected_piece, white_move, white_special_move)]:
                                moves_score_dict[(white_selected_piece, white_move, white_special_move)] = value
                            elif not is_maximizing_player and value <= moves_score_dict[(black_selected_piece, black_move[0], black_special_move, black_promotion)]:
                                moves_score_dict[(black_selected_piece, black_move[0], black_special_move, black_promotion)] = value
                    elif isinstance(white_move, list) and not isinstance(black_move, list):
                        for white_promotion in white_promotion_choices:
                            illegal = ai_handle_piece_move(
                                game, 
                                white_selected_piece, 
                                white_move_new, 
                                black_selected_piece, 
                                black_move_new, 
                                white_special = white_special_move, 
                                white_promotion_piece = white_promotion,
                                black_special = black_special_move, 
                                black_promotion_piece = None
                                )
                            if illegal:
                                reset_state(game, stored_empty)
                                continue
                            value = minimax(depth - 1, game, -10000, 10000, not is_maximizing_player, pos)
                            game.undo_move()
                            reset_state(game, stored_empty)
                            if is_maximizing_player and value >= moves_score_dict[(white_selected_piece, white_move[0], white_special_move, white_promotion)]:
                                moves_score_dict[(white_selected_piece, white_move[0], white_special_move, white_promotion)] = value
                            elif not is_maximizing_player and value <= moves_score_dict[(black_selected_piece, black_move, black_special_move)]:
                                moves_score_dict[(black_selected_piece, black_move, black_special_move)] = value
                    else:
                        illegal = ai_handle_piece_move(
                            game, 
                            white_selected_piece, 
                            white_move_new, 
                            black_selected_piece, 
                            black_move_new, 
                            white_special = white_special_move, 
                            white_promotion_piece = None,
                            black_special = black_special_move, 
                            black_promotion_piece = None
                            )
                        if illegal:
                            reset_state(game, stored_empty)
                            continue
                        value = minimax(depth - 1, game, -10000, 10000, not is_maximizing_player, pos)
                        game.undo_move()
                        reset_state(game, stored_empty)
                        if is_maximizing_player and value >= moves_score_dict[(white_selected_piece, white_move, white_special_move)]:
                            moves_score_dict[(white_selected_piece, white_move, white_special_move)] = value
                        elif not is_maximizing_player and value <= moves_score_dict[(black_selected_piece, black_move, black_special_move)]:
                            moves_score_dict[(black_selected_piece, black_move, black_special_move)] = value
    reset_state(game, stored)
    return moves_score_dict

def reset_state(game, stored):
    game.white_active_move = stored["stored_white_active_move"]
    game.black_active_move = stored["stored_black_active_move"]
    game.white_played = False if game.white_active_move is None else True
    game.black_played = False if game.black_active_move is None else True
    game._promotion_white = stored["stored_white_promote"]
    game._promotion_black = stored["stored_black_promote"]

def minimax(depth, game, alpha, beta, is_maximizing_player, pos):
    pos["position_count"] += 1
    if depth == 0:
        return -evaluate_board(game.board)
    
    stored = {
        "stored_white_active_move": None,
        "stored_white_promote": None,
        "stored_black_active_move": None,
        "stored_black_promote": None
    }
    reset_state(game, stored)

    white_new_valid_game_moves, white_special_index = new_game_board_moves(game, True)
    black_new_valid_game_moves, black_special_index = new_game_board_moves(game, True)

    best_move = -9999 if is_maximizing_player else 9999
    for i in range(len(white_new_valid_game_moves)):
        for j in range(len(black_new_valid_game_moves)):
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    raise Exception("Quit")
            white_selected_piece = white_new_valid_game_moves[i][0]
            black_selected_piece = black_new_valid_game_moves[j][0]
            white_moves = white_new_valid_game_moves[i][1]
            black_moves = black_new_valid_game_moves[j][1]
            white_special_move = False if i < white_special_index else True
            black_special_move = False if i < black_special_index else True
            for white_move in white_moves:
                for black_move in black_moves:
                    white_move_new = white_move[0] if isinstance(white_move, list) else white_move
                    white_promotion_choices = white_move[1] if isinstance(white_move, list) else None
                    black_move_new = black_move[0] if isinstance(black_move, list) else black_move
                    black_promotion_choices = black_move[1] if isinstance(black_move, list) else None
                    if isinstance(white_move, list) and isinstance(black_move, list):
                        for white_promotion in white_promotion_choices:
                            for black_promotion in black_promotion_choices:
                                illegal = ai_handle_piece_move(
                                    game, 
                                    white_selected_piece, 
                                    white_move_new, 
                                    black_selected_piece, 
                                    black_move_new, 
                                    white_special = white_special_move, 
                                    white_promotion_piece = white_promotion,
                                    black_special = black_special_move, 
                                    black_promotion_piece = black_promotion
                                    )
                                if illegal:
                                    reset_state(game, stored)
                                    continue
                                best_move = select_minimax_optimum(best_move, depth, game, alpha, beta, is_maximizing_player, pos)
                                game.undo_move()
                                reset_state()
                                alpha, beta = alpha_beta_calc(alpha, beta, best_move, is_maximizing_player)
                                if beta <= alpha:
                                    return best_move
                    elif not isinstance(white_move, list) and isinstance(black_move, list):
                        for black_promotion in black_promotion_choices:
                            illegal = ai_handle_piece_move(
                                game, 
                                white_selected_piece, 
                                white_move_new, 
                                black_selected_piece, 
                                black_move_new, 
                                white_special = white_special_move, 
                                white_promotion_piece = None,
                                black_special = black_special_move, 
                                black_promotion_piece = black_promotion
                                )
                            if illegal:
                                reset_state(game, stored)
                                continue
                            best_move = select_minimax_optimum(best_move, depth, game, alpha, beta, is_maximizing_player, pos)
                            game.undo_move()
                            reset_state(game, stored)
                            alpha, beta = alpha_beta_calc(alpha, beta, best_move, is_maximizing_player)
                            if beta <= alpha:
                                return best_move
                    elif isinstance(white_move, list) and not isinstance(black_move, list):
                        for white_promotion in white_promotion_choices:
                            illegal = ai_handle_piece_move(
                                game, 
                                white_selected_piece, 
                                white_move_new, 
                                black_selected_piece, 
                                black_move_new, 
                                white_special = white_special_move, 
                                white_promotion_piece = white_promotion,
                                black_special = black_special_move, 
                                black_promotion_piece = None
                                )
                            if illegal:
                                reset_state(game, stored)
                                continue
                            best_move = select_minimax_optimum(best_move, depth, game, alpha, beta, is_maximizing_player, pos)
                            game.undo_move()
                            reset_state(game, stored)
                            alpha, beta = alpha_beta_calc(alpha, beta, best_move, is_maximizing_player)
                            if beta <= alpha:
                                return best_move
                    else:
                        illegal = ai_handle_piece_move(
                            game, 
                            white_selected_piece, 
                            white_move_new, 
                            black_selected_piece, 
                            black_move_new, 
                            white_special = white_special_move, 
                            white_promotion_piece = None,
                            black_special = black_special_move, 
                            black_promotion_piece = None
                            )
                        if illegal:
                            reset_state(game, stored)
                            continue
                        best_move = select_minimax_optimum(best_move, depth, game, alpha, beta, is_maximizing_player, pos)
                        game.undo_move()
                        reset_state(game, stored)
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

class Node:
    def __init__(self, parent=None):
        self.parent = parent
        self.children = []
        self.visits = 0
        self.value = 0
        self.move = {}

def generate_all_moves(game, white_side):
    all_valid_moves = []
    all_valid_specials = []
    
    for row in range(len(game.board)):
        for col in range(8):
            piece = game.board[row][col]
            is_white = piece.isupper()
            if piece != ' ' and white_side == is_white:
                valid_moves, _, valid_specials = game.validate_moves(row, col)
                if valid_moves != []:
                    for move in valid_moves:
                        appending_move = move
                        if piece.lower() == 'p' and move[0] in (0, 7):
                            promote_options = ['q', 'r', 'n', 'b'] if piece.islower() else ['Q', 'R', 'N', 'B']
                            appending_move = [[move, p] for p in promote_options]
                        if isinstance(appending_move, list):
                            for promotion_move in appending_move:
                                all_valid_moves.append([(row, col), promotion_move])
                        else:
                            all_valid_moves.append([(row, col), appending_move])
                if valid_specials != []:
                    for move in valid_specials:
                        all_valid_specials.append([(row, col), move])
    special_index_start = len(all_valid_moves)
    all_valid_moves.extend(all_valid_specials)
    return all_valid_moves, special_index_start

def game_is_over(game):
    checkmate_white, remaining_moves_white = is_checkmate_or_stalemate(game.board, True, game.moves)
    checkmate_black, remaining_moves_black = is_checkmate_or_stalemate(game.board, False, game.moves)
    no_remaining_moves = remaining_moves_white == 0 or remaining_moves_black == 0
    return checkmate_white or checkmate_black or no_remaining_moves

def apply_node(game, node):
    ai_move = node.move
    if game._starting_player:
        ai_handle_piece_move(
            game, 
            ai_move['player_piece'], 
            ai_move['player_move'], 
            ai_move['selected_piece'], 
            ai_move['move'], 
            white_special = ai_move['player_special'], 
            white_promotion_piece = ai_move['player_promotion_piece'],
            black_special = ai_move['special'],
            black_promotion_piece = ai_move['promotion_piece']
            )
    else:
        ai_handle_piece_move(
            game, 
            ai_move['selected_piece'], 
            ai_move['move'], 
            ai_move['player_piece'], 
            ai_move['player_move'], 
            white_special = ai_move['special'], 
            white_promotion_piece = ai_move['promotion_piece'],
            black_special = ai_move['player_special'],
            black_promotion_piece = ai_move['player_promotion_piece']
            )

def uct_value(node, exploration=1.414):
    if node.visits == 0:
        return float('inf')
    return node.value / node.visits + exploration * (2 * math.log(node.parent.visits) / node.visits) ** 0.5

def select_best_node(node):
    return max(node.children, key=uct_value)

def expand_node(node, game):

    stored_empty = {
        "stored_white_active_move": None,
        "stored_white_promote": None,
        "stored_black_active_move": None,
        "stored_black_promote": None
    }

    white_moves, white_special_index = generate_all_moves(game, True)
    black_moves, black_special_index = generate_all_moves(game, False)
    for i in range(len(white_moves)):
        white_selected_piece = white_moves[i][0]
        white_selection = white_moves[i][1]
        white_move = white_selection[0] if isinstance(white_selection, list) else white_selection
        white_special_move = False if i < white_special_index else True
        white_promotion = None if not isinstance(white_selection, list) else white_selection[1]
        for j in range(len(black_moves)):
            black_selected_piece = black_moves[j][0]
            black_selection = black_moves[j][1]
            black_move = black_selection[0] if isinstance(black_selection, list) else black_selection
            black_special_move = False if j < black_special_index else True
            black_promotion = None if not isinstance(black_selection, list) else black_selection[1]
            illegal = ai_handle_piece_move(
                game, 
                white_selected_piece, 
                white_move, 
                black_selected_piece, 
                black_move, 
                white_special = white_special_move, 
                white_promotion_piece = white_promotion,
                black_special = black_special_move, 
                black_promotion_piece = black_promotion
                )
            if illegal:
                reset_state(game, stored_empty)
                continue
            child_node = Node(node)
            ai_move = {
                "move": white_move,
                "selected_piece": white_selected_piece,
                "special": white_special_move,
                "promotion_piece": white_promotion,
                "player_move": black_move,
                "player_piece": black_selected_piece,
                "player_special": black_special_move,
                "player_promotion_piece": black_promotion
            } if not game._starting_player else \
            {
                "move": black_move,
                "selected_piece": black_selected_piece,
                "special": black_special_move,
                "promotion_piece": black_promotion,
                "player_move": white_move,
                "player_piece": white_selected_piece,
                "player_special": white_special_move,
                "player_promotion_piece": white_promotion
            }
            child_node.move = ai_move
            node.children.append(child_node)
            game.undo_move()

def simulate_random_playout(game, pos, depth):
    if depth == 0:
        return evaluate_board(game.board)
    
    stored_empty = {
        "stored_white_active_move": None,
        "stored_white_promote": None,
        "stored_black_active_move": None,
        "stored_black_promote": None
    }

    update = False
    white_moves, white_special_index = generate_all_moves(game, True)
    black_moves, black_special_index = generate_all_moves(game, False)
    while not update:
        if white_moves == [] or black_moves == []:
            update = True
            continue
        i = random.choice(range(len(white_moves)))
        white_selected_piece = white_moves[i][0]
        white_move = white_moves[i][1]
        white_special_move = False if i < white_special_index else True
        white_promotion = None if not isinstance(white_move, list) else white_move[1]
        j = random.choice(range(len(black_moves)))
        black_selected_piece = black_moves[j][0]
        black_move = black_moves[j][1]
        black_special_move = False if j < black_special_index else True
        black_promotion = None if not isinstance(black_move, list) else black_move[1]
        illegal = ai_handle_piece_move(
            game, 
            white_selected_piece, 
            white_move[0] if isinstance(white_move, list) else white_move, 
            black_selected_piece, 
            black_move[0] if isinstance(black_move, list) else black_move, 
            white_special = white_special_move, 
            white_promotion_piece = white_promotion,
            black_special = black_special_move, 
            black_promotion_piece = black_promotion
            )

        if illegal:
            reset_state(game, stored_empty)
            continue
        update = True
        pos["position_count"] += 1
    return simulate_random_playout(game, pos, depth - 1)

def backpropagate(node, result, game):
    while node is not None:
        node.visits += 1
        node.value += result
        node = node.parent
        if node is not None:
            game.undo_move()

def mcts(root, pos, game, iterations=10):
    stored = {
        "stored_white_active_move": game.white_active_move.copy() if game.white_active_move is not None else None,
        "stored_white_promote": game._promotion_white,
        "stored_black_active_move": game.black_active_move.copy() if game.black_active_move is not None else None,
        "stored_black_promote": game._promotion_black
    }
    
    stored_empty = {
        "stored_white_active_move": None,
        "stored_white_promote": None,
        "stored_black_active_move": None,
        "stored_black_promote": None
    }
    reset_state(game, stored_empty)
    
    pos["position_count"] = 0
    start = time.time()
    
    for i in range(iterations):
        print("iter: ", i)
        node = root
        depth = 0
        while node.children:
            node = select_best_node(node)
            apply_node(game, node)
            depth += 1
        if not game_is_over(game):
            expand_node(node, game)
        result = simulate_random_playout(game, pos, 10)
        for _ in range(10):
            game.undo_move()
        backpropagate(node, result, game)
    
    end = time.time()
    move_time = end - start
    print("Move time: ", move_time)
    positionspers = (pos["position_count"] / move_time) if move_time != 0.0 else 'Instantaneous'
    print("Positions: ", pos["position_count"])
    print("Positions/s: ", positionspers)

    reset_state(game, stored)
    return select_best_node(root)