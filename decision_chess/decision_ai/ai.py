import time
import random
import math
import pygame
from game import *

global_pos = {
    "position_count": 0, 
    "simulated_positions": 0, 
    "sim_captures": 0, 
    "sim_wins": 0, 
    "sim_losses": 0, 
    "sim_win_wins": 0, 
    "sim_draws": 0,
    "total_sig_pos": 0
    }

def ai_move(game, init, drawing_settings):
    if not game._starting_player and game.white_played or game._starting_player and game.black_played:
        return

    root_node = Node()
    best_node = mcts(root_node, global_pos, game, 10, 26, 10)
    best_state = best_node.move
    
    stored_empty = {
        "stored_white_active_move": None,
        "stored_white_promote": None,
        "stored_black_active_move": None,
        "stored_black_promote": None
    }
    if game._starting_player and game.white_active_move is not None:
        white_selected_piece = game.white_active_move[0]
        white_promotion = game._promotion_white
        white_move_new = game.white_active_move[1]
        white_special_move = game.white_active_move[3] != ''
    elif not game._starting_player and game.black_active_move is not None:
        black_selected_piece = game.black_active_move[0]
        black_promotion = game._promotion_black
        black_move_new = game.black_active_move[1]
        black_special_move = game.black_active_move[3] != ''

    reset_state(game, stored_empty)
    play_first_legal = False
    needs_update = True
    illegal = False
    while needs_update:
        needs_update = False if game.white_active_move is None and game.black_active_move is None else True
        illegal_side = None
        if play_first_legal:
            needs_update = False

        selected_piece = best_state["selected_piece"]
        best_move = best_state["move"]
        special = best_state["special"]
        promotion_piece = best_state["promotion_piece"]

        if needs_update:
            if game._starting_player:
                black_selected_piece = selected_piece
                black_move_new = best_move
                black_special_move = special
            else:
                white_selected_piece = selected_piece
                white_move_new = best_move
                white_special_move = special
            illegal, illegal_side = ai_handle_piece_move(
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
            update = not illegal
        else:
            update, _ = ai_play_move(game, best_move, selected_piece, special=special, promotion_piece=promotion_piece)

        if update:
            print("ALG_MOVES:", game.alg_moves)
            needs_update = False
        elif needs_update:
            if illegal_side is not None and (illegal_side == "White" and game._starting_player or illegal_side == "Black" and not game._starting_player):
                play_first_legal = True
                continue
            root_node.children.remove(best_node)
            best_node = select_best_node(root_node, 0, game, None)

    drawing_settings["recalc_selections"] = True
    if game.alg_moves != []:
        if not any(symbol in game.alg_moves[-1] for symbol in ['0-1', '1-0', '1-1', '½–½']): # Could add a winning or losing sound
            if update and ("x" in game.alg_moves[-1][0] or "x" in game.alg_moves[-1][1]):
                capture_sound.play()
            elif update:
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

def get_absolute_value(piece):
    type = piece.lower()
    if type == 'p':
        return 10 
    elif type == 'n':
        return 30 
    elif type == 'b':
        return 30 
    elif type == 'r':
        return 50 
    elif type == 'q':
        return 90 
    elif type == 'k':
        return 900 
    
def get_piece_value(piece, is_white):
    if piece == ' ':
        return 0
    abs_val = get_absolute_value(piece)
    piece_value = abs_val if is_white else -1 * abs_val
    return piece_value

def evaluate_board(board):
    total_value = 0
    for row in range(8):
        for col in range(8):
            piece = board[row][col]
            if piece == ' ':
                continue
            is_white = piece.isupper()
            total_value += get_piece_value(piece, is_white)
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
    illegal_side = None
    if illegal1:
        illegal_side = "White"
    elif illegal2:
        illegal_side = "Black"
    return illegal1 or illegal2, illegal_side

def reset_state(game, stored):
    game.white_active_move = stored["stored_white_active_move"]
    game.black_active_move = stored["stored_black_active_move"]
    game.white_played = False if game.white_active_move is None else True
    game.black_played = False if game.black_active_move is None else True
    game._promotion_white = stored["stored_white_promote"]
    game._promotion_black = stored["stored_black_promote"]

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

def game_over_outcome(game):
    checkmate_white, remaining_moves_white = is_checkmate_or_stalemate(game.board, True, game.moves)
    checkmate_black, remaining_moves_black = is_checkmate_or_stalemate(game.board, False, game.moves)
    no_remaining_moves = remaining_moves_white == 0 or remaining_moves_black == 0
    if checkmate_white and checkmate_black:
        return 1250 if not game._starting_player else -1250
    elif checkmate_white:
        return 900
    elif checkmate_black:
        return -900
    elif no_remaining_moves:
        return 500
    return ValueError('Game not over')

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

def uct_value(node, previous_result, game, boards=None, exploration=1.414):
    if node.visits == 0:
        if previous_result == 0:
            return 0
        elif previous_result > 0:
            first_term = (previous_result / 1000) * previous_result if previous_result < 1000 else 0
        else:
            first_term = (1 + previous_result / -1000) * 1000
        
        piece_type = game.board[node.move['selected_piece'][0]][node.move['selected_piece'][1]].lower()
        row, col = node.move['move'][0], node.move['move'][1]
        move_value = boards[piece_to_board[piece_type]][1][row][col]
        move_visits = boards[piece_to_board[piece_type]][0][row][col]
        total_visits = sum_boards(boards, 0)
        total_sig_moves = sum(1 for key in boards.keys() for i in boards[key][0] for j in i if j != 0)
        avg_visit = sum(sum(i) for key in boards.keys() for i in boards[key][0]) / total_sig_moves
        second_term = move_value / abs(previous_result) * (move_visits / total_visits) * 1000
        
        third_term = 0
        if move_visits > 2 * avg_visit:
            sign = 1 if move_value >= 0 else -1
            if abs(move_value) >= abs(previous_result):
                s = math.exp((abs(move_value) - abs(previous_result)) // max(abs(int(previous_result)), 1))
                effective_score = sign * abs(move_value) - abs(previous_result)
            else:
                denom = ((abs(previous_result) - abs(move_value)) // max(abs(int(move_value)), 1))
                s = math.exp(1/ denom) if denom != 0 else 0
                effective_score = move_value
            third_term = s * ((move_visits // avg_visit) / total_visits) * effective_score
        #print(move_visits, avg_visit, total_visits, first_term, second_term, third_term, previous_result, first_term + second_term + third_term)
        return first_term + second_term + third_term
    return node.value / node.visits + exploration * (2 * math.log(node.parent.visits) / node.visits) ** 0.5

def select_best_node(node, result, game, boards):
    return max(node.children, key=lambda child: uct_value(child, result, game, boards))

def expand_node(node, game, pos):

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
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    raise Exception("Quit")
            black_selected_piece = black_moves[j][0]
            black_selection = black_moves[j][1]
            black_move = black_selection[0] if isinstance(black_selection, list) else black_selection
            black_special_move = False if j < black_special_index else True
            black_promotion = None if not isinstance(black_selection, list) else black_selection[1]
            illegal, _ = ai_handle_piece_move(
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
            pos["position_count"] += 1
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

def sum_boards(boards, index):
    evaluation = 0
    for key in boards.keys():
        for row in boards[key][index]:
            for cell in row:
                evaluation += cell
    return evaluation

def simulate_random_playout(game, pos, depth, search_depth, boards, factor, final_sim, temp_boards, simulation_sets):
    white_moves, white_special_index = generate_all_moves(game, True)
    black_moves, black_special_index = generate_all_moves(game, False)
    game_over = len(white_moves) == 0 or len(black_moves) == 0
    execution_depth = search_depth - depth
    if depth == 0 or game_over:
        if game_over and not final_sim:
            backpropagate_consequence(game, execution_depth, boards, pos, end_game_value=game_over_outcome(game))
        if not final_sim:
            return 0, execution_depth
        expected_playout_value = factor * evaluate_board(game.board)
        random_playout_value = factor * sum_boards(boards, 1)
        return max(depth / search_depth, 1 / simulation_sets) * random_playout_value + (execution_depth / search_depth) * expected_playout_value, execution_depth
    
    stored_empty = {
        "stored_white_active_move": None,
        "stored_white_promote": None,
        "stored_black_active_move": None,
        "stored_black_promote": None
    }

    update = False
    running = False
    running_white_moves = white_moves
    running_black_moves = black_moves
    while not update:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                raise Exception("Quit")
        if running_white_moves == [] or running_black_moves == []:
            update = True
            depth = depth + 1
            continue
        if not final_sim:
            i = random.choice(range(len(running_white_moves)))
            j = random.choice(range(len(running_black_moves)))
        else:
            if not running:
                probabilities = []
                moves = running_white_moves if not game._starting_player else running_black_moves
                for move in moves:
                    piece = game.board[move[0][0]][move[0][1]]
                    position = move[1][0] if isinstance(move[1], list) else move[1]
                    board = boards[piece_to_board[piece.lower()]][1]
                    score = board[position[0]][position[1]]
                    probabilities.append(score / pos["total_sig_pos"])
                sum_of_boosts = sum(x for x in probabilities if x > 0)
                sum_of_reductions = sum(x for x in probabilities if x < 0)
                p0 = (1 / (len(moves))) * (1 - sum_of_boosts + sum_of_reductions)
                probabilities = [p0 + x for x in probabilities]
                shift = -min(min(probabilities), 0)
                probabilities = [x + shift for x in probabilities]
                unnormalised_sum = sum(abs(x) for x in probabilities) 
                probabilities = [x * 1/unnormalised_sum for x in probabilities]
            if not game._starting_player:
                i = random.choices(range(len(running_white_moves)), weights=probabilities, k=1)[0]
                j = random.choice(range(len(running_black_moves)))
            else:
                i = random.choice(range(len(running_white_moves)))
                j = random.choices(range(len(running_black_moves)), weights=probabilities, k=1)[0]
        running = True
        white_selected_piece = running_white_moves[i][0]
        white_move = running_white_moves[i][1]
        white_special_move = False if i < white_special_index else True
        white_promotion = None if not isinstance(white_move, list) else white_move[1]
        black_selected_piece = running_black_moves[j][0]
        black_move = running_black_moves[j][1]
        black_special_move = False if j < black_special_index else True
        black_promotion = None if not isinstance(black_move, list) else black_move[1]
        illegal, illegal_side = ai_handle_piece_move(
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
            if illegal_side == "White":
                del running_white_moves[i]
                white_special_index = white_special_index - 1 if i < white_special_index else white_special_index
            else:
                del running_black_moves[j]
                black_special_index = black_special_index - 1 if j < black_special_index else black_special_index
            if final_sim:
                if illegal_side == "White" and not game._starting_player:
                    del probabilities[i]
                elif illegal_side == "Black" and game._starting_player:
                    del probabilities[j]
                else:
                    continue
                if len(probabilities) != 0:
                    shift = min(min(probabilities), 0)
                    probabilities = [x + shift for x in probabilities]
                    unnormalised_sum = sum(abs(x) for x in probabilities)
                    probabilities = [x * 1/unnormalised_sum for x in probabilities]
            continue
        update = True
        execution_depth += 1
        pos["position_count"] += 1
        if not final_sim:
            pos["simulated_positions"] += 1
            potential_white_capture, potential_black_capture = game.moves[-1][0][2], game.moves[-1][1][2]
            if potential_white_capture is not None and potential_white_capture != ' ' and not (isinstance(potential_white_capture, list) and None in potential_white_capture):
                backpropagate_consequence(game, execution_depth, boards, pos, capture=potential_white_capture, temp_boards=temp_boards)
            if potential_black_capture is not None and potential_black_capture != ' ' and not (isinstance(potential_black_capture, list) and None in potential_black_capture):
                backpropagate_consequence(game, execution_depth, boards, pos, capture=potential_black_capture, temp_boards=temp_boards)

    return simulate_random_playout(game, pos, depth - 1, search_depth, boards, factor, final_sim, temp_boards, simulation_sets)

piece_values = {
    'p': 10,
    'r': 50,
    'n': 30,
    'b': 30,
    'q': 90,
    'P': -10,
    'R': -50,
    'N': -30,
    'B': -30,
    'Q': -90
}

piece_to_board = {'p': 'pawn_eval', 'r': 'rook_eval', 'n': 'knight_eval', 'b': 'bishop_eval', 'q': 'queen_eval', 'k': 'king_eval'}

def boards_to_update(boards, temp_boards, board_type, end_game_value):
    visit_board = boards[board_type][0]
    if end_game_value is not None:
        value_board = boards[board_type][2]
    else:
        value_board = temp_boards[board_type]
    return visit_board, value_board

def backpropagate_consequence(game, execution_depth, boards, pos, capture=None, end_game_value=None, temp_boards=None):
    if isinstance(capture, list):
        value = 0
        if capture[0] != ' ':
            value = piece_values[capture[0]]
        if capture[1] != ' ':
            value += piece_values[capture[1]]
    else:
        value = piece_values[capture] if capture is not None else end_game_value
    sign = 1 if value > 0 else -1

    if end_game_value is not None:
        if end_game_value == 1250:
            pos["sim_win_wins"] += 1
            end_game_count = pos["sim_win_wins"]
        elif end_game_value == 1000:
            pos["sim_wins"] += 1
            end_game_count = pos["sim_wins"]
        elif end_game_value == -1000:
            pos["sim_losses"] += 1
            end_game_count = pos["sim_losses"]
        else:
            pos["sim_draws"] += 1
            end_game_count = pos["sim_draws"]
        value = value / ((execution_depth + 1) * end_game_count)
        if end_game_value in [1250, 500] and game._starting_player:
            sign = -1
    else:
        pos["sim_captures"] += 1

    for i in range(execution_depth):
        move_to_adjust = game.moves[-i - 1][game._starting_player]
        move_piece_type = move_to_adjust[0][0].lower()
        row, col = int(move_to_adjust[1][1]), int(move_to_adjust[1][2])
        visit_board, value_board = boards_to_update(boards, temp_boards, piece_to_board[move_piece_type], end_game_value)
        visit_board[row][col] += 1
        value_board[row][col] += value + sign * (i + 1)

def backpropagate(node, result, game):
    while node is not None:
        node.visits += 1
        node.value += result
        if node is not None and node.parent is not None:
            game.undo_move()
        node = node.parent

def mcts(root, pos, game, iterations=10, simulation_sets=26, sim_depth=10):
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
    
    # profiler = cProfile.Profile()
    # profiler.enable()
    pos["position_count"] = 0
    start = time.time()
    factor = 1 if not game._starting_player else -1
    
    boards = {}
    result = 0
    for i in range(iterations):
        node = root
        while node.children:
            node = select_best_node(node, result, game, boards)
            apply_node(game, node)
        if not game_is_over(game):
            expand_node(node, game, pos)
        pos["simulated_positions"] = 0
        boards = {
            "pawn_eval": [
                [[0 for _ in range(8)] for _ in range(8)], 
                [[0 for _ in range(8)] for _ in range(8)],
                [[0 for _ in range(8)] for _ in range(8)]
                ],
            "rook_eval": [
                [[0 for _ in range(8)] for _ in range(8)], 
                [[0 for _ in range(8)] for _ in range(8)],
                [[0 for _ in range(8)] for _ in range(8)]
                ],
            "knight_eval": [
                [[0 for _ in range(8)] for _ in range(8)], 
                [[0 for _ in range(8)] for _ in range(8)],
                [[0 for _ in range(8)] for _ in range(8)]
                ],
            "bishop_eval": [
                [[0 for _ in range(8)] for _ in range(8)], 
                [[0 for _ in range(8)] for _ in range(8)],
                [[0 for _ in range(8)] for _ in range(8)]
                ],
            "queen_eval": [
                [[0 for _ in range(8)] for _ in range(8)], 
                [[0 for _ in range(8)] for _ in range(8)],
                [[0 for _ in range(8)] for _ in range(8)]
                ],
            "king_eval": [
                [[0 for _ in range(8)] for _ in range(8)], 
                [[0 for _ in range(8)] for _ in range(8)],
                [[0 for _ in range(8)] for _ in range(8)]
                ]
        }
        final_sim = False
        for simulation_set in range(simulation_sets):
            temp_boards = {
                "pawn_eval": [[0 for _ in range(8)] for _ in range(8)],
                "rook_eval": [[0 for _ in range(8)] for _ in range(8)],
                "knight_eval": [[0 for _ in range(8)] for _ in range(8)],
                "bishop_eval": [[0 for _ in range(8)] for _ in range(8)],
                "queen_eval": [[0 for _ in range(8)] for _ in range(8)],
                "king_eval": [[0 for _ in range(8)] for _ in range(8)]
            }
            if simulation_set == simulation_sets - 1:
                final_sim = True
            result, execution_depth = simulate_random_playout(game, pos, sim_depth, sim_depth, boards, factor, final_sim, temp_boards, simulation_sets)
            for _ in range(execution_depth):
                game.undo_move()
            if not final_sim:
                pos["total_sig_pos"] += pos["sim_captures"]
                if pos["sim_captures"]:
                    for key in temp_boards.keys():
                        for row in range(8):
                            for col in range(8):
                                boards[key][1][row][col] += temp_boards[key][row][col] / (sim_depth * pos["sim_captures"])
                if simulation_set == simulation_sets - 2:
                    for key in boards.keys():
                        for row in range(8):
                            for col in range(8):
                                boards[key][1][row][col] += boards[key][2][row][col]
                    pos["total_sig_pos"] = max(pos["total_sig_pos"] + pos["sim_win_wins"] + pos["sim_wins"] + pos["sim_losses"] + pos["sim_draws"], 1)
            pos["sim_captures"] = 0
        backpropagate(node, result, game)
    
    end = time.time()
    # profiler.disable()
    move_time = end - start
    print("Move time: ", move_time)
    positionspers = (pos["position_count"] / move_time) if move_time != 0.0 else 'Instantaneous'
    print("Positions: ", pos["position_count"])
    print("Positions/s: ", positionspers)

    # stats = pstats.Stats(profiler)
    # stats.sort_stats('time')
    # stats.print_stats()

    reset_state(game, stored)
    return select_best_node(root, result, game, boards)