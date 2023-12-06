import pygame
import sys
import json
import asyncio
import pygbag
import pygbag.aio as asyncio
import fetch
import pygbag_net
import builtins
from game import *
from constants import *
from helpers import *

# Handle Persistent Storage
if __import__("sys").platform == "emscripten":
    from platform import window

# Initialize Pygame
pygame.init()

current_theme = Theme()

with open('themes.json', 'r') as file:
    themes = json.load(file)

# Initialize Pygame window
game_window = pygame.display.set_mode((current_theme.WIDTH, current_theme.HEIGHT))

# Load the chess pieces dynamically
pieces = {}
transparent_pieces = {}
for color in ['w', 'b']:
    for piece_lower in ['r', 'n', 'b', 'q', 'k', 'p']:
        piece_key, image_name_key = name_keys(color, piece_lower)
        pieces[piece_key], transparent_pieces[piece_key] = load_piece_image(image_name_key, current_theme.GRID_SIZE)

def handle_new_piece_selection(game, row, col, is_white, hovered_square):
    piece = game.board[row][col]
    # Initialize variables based on turn
    if game._starting_player == is_white or game._debug:
        first_intent = True
        selected_piece = (row, col)
        selected_piece_image = transparent_pieces[piece]
        valid_moves, valid_captures, valid_specials = game.validate_moves(row, col)
    else:
        first_intent = False
        selected_piece = None
        selected_piece_image = None
        valid_moves, valid_captures, valid_specials = [], [], []

    if (row, col) != hovered_square:
        hovered_square = (row, col)
    
    return first_intent, selected_piece, selected_piece_image, valid_moves, valid_captures, valid_specials, hovered_square

def handle_piece_move(game, selected_piece, row, col, valid_captures):
    # Initialize Variables
    promotion_square = None
    promotion_required = False
    # Need to be considering the selected piece for this section not an old piece
    piece = game.board[selected_piece[0]][selected_piece[1]]
    is_white = piece.isupper()

    temp_board = [rank[:] for rank in game.board]  
    temp_moves = game.moves.copy()
    temp_moves.append(output_move(piece, selected_piece, row, col, temp_board[row][col]))
    temp_board[row][col] = temp_board[selected_piece[0]][selected_piece[1]]
    temp_board[selected_piece[0]][selected_piece[1]] = ' '

    # Move the piece if the king does not enter check
    if not is_check(temp_board, is_white, temp_moves): # redundant now? Not for premoves
        game.update_state(row, col, selected_piece)
        if piece.lower() != 'p' or (piece.lower() == 'p' and (row != 7 and row != 0)):
            print("ALG_MOVES:", game.alg_moves)
        
        if (row, col) in valid_captures:
            capture_sound.play()
        else:
            move_sound.play()
        
        selected_piece = None

        checkmate, remaining_moves = is_checkmate_or_stalemate(game.board, not is_white, game.moves)
        if checkmate:
            print("CHECKMATE")
            game.end_position = True
            game.add_end_game_notation(checkmate)
            return None, promotion_required
        elif remaining_moves == 0:
            print("STALEMATE")
            game.end_position = True
            game.add_end_game_notation(checkmate)
            return None, promotion_required
        elif game.threefold_check():
            print("STALEMATE BY THREEFOLD REPETITION")
            game.forced_end = "Stalemate by Threefold Repetition"
            game.end_position = True
            game.add_end_game_notation(checkmate)
            return None, promotion_required

    # Pawn Promotion
    if game.board[row][col].lower() == 'p' and (row == 0 or row == 7):
        promotion_required = True
        promotion_square = (row, col)

    return promotion_square, promotion_required

def handle_piece_special_move(game, selected_piece, row, col):
    # Need to be considering the selected piece for this section not an old piece
    piece = game.board[selected_piece[0]][selected_piece[1]]
    is_white = piece.isupper()

    # Castling and Enpassant moves are already validated, we simply update state
    game.update_state(row, col, selected_piece, special=True)
    print("ALG_MOVES:", game.alg_moves)
    if (row, col) in [(7, 2), (7, 6), (0, 2), (0, 6)]:
        move_sound.play()
    else:
        capture_sound.play()

    checkmate, remaining_moves = is_checkmate_or_stalemate(game.board, not is_white, game.moves)
    if checkmate:
        print("CHECKMATE")
        game.end_position = True
        game.add_end_game_notation(checkmate)
        return piece, is_white
    elif remaining_moves == 0:
        print("STALEMATE")
        game.end_position = True
        game.add_end_game_notation(checkmate)
        return piece, is_white
    elif game.threefold_check():
        print("STALEMATE BY THREEFOLD REPETITION")
        game.forced_end = "Stalemate by Threefold Repetition"
        game.end_position = True
        game.add_end_game_notation(checkmate)
        return piece, is_white

    return piece, is_white

def handle_command(status_names, client_state_actions, web_metadata_dict, games_metadata_name, game_tab_id):
    command_name, client_action_name, client_executed_name, *remaining = status_names
    if len(status_names) == 3:
        client_reset_name = None 
    else:
        client_reset_name = remaining[0]
    client_executed_status, client_reset_status = \
        client_state_actions[client_executed_name], client_state_actions.get(client_reset_name)
    
    status_metadata_dict = web_metadata_dict[game_tab_id]
    if status_metadata_dict.get(command_name) is not None:
        if status_metadata_dict[command_name]['execute'] and not status_metadata_dict[command_name]['update_executed'] and not client_reset_status:
            if client_state_actions[client_action_name] != True:
                client_state_actions[client_action_name] = True
            if client_executed_status:
                status_metadata_dict[command_name]['update_executed'] = True
                web_metadata_dict[game_tab_id] = status_metadata_dict
                json_metadata = json.dumps(web_metadata_dict)
                
                window.localStorage.setItem(games_metadata_name, json_metadata)
                client_state_actions[client_action_name] = False

        # Handling race conditions assuming speed differences and sychronizing states with this.
        # That is, only once we stop receiving the command, after an execution, do we allow it to be executed again
        if client_executed_status and not status_metadata_dict[command_name]['execute']:
            client_state_actions[client_executed_name] = False    

        if client_reset_status is not None and client_reset_status == True and not status_metadata_dict[command_name]['reset']:
            status_metadata_dict[command_name]['reset'] = True
            status_metadata_dict[command_name]['execute'] = False
            web_metadata_dict[game_tab_id] = status_metadata_dict
            json_metadata = json.dumps(web_metadata_dict)
            
            window.localStorage.setItem(games_metadata_name, json_metadata)
            client_state_actions[client_reset_name] = False
            client_state_actions[client_action_name] = False

# Game State loop for promotion
async def promotion_state(promotion_square, client_game, row, col, draw_board_params, client_state_actions, command_status_names, drawing_settings, game_tab_id, node, init, offers):
    promotion_buttons = display_promotion_options(current_theme, promotion_square[0], promotion_square[1])
    promoted, promotion_required = False, True
    
    window.sessionStorage.setItem("promoting", "true")

    while promotion_required:

        # Web browser actions/commands are received in previous loop iterations
        if client_state_actions["undo"] and not client_state_actions["undo_sent"]:
            offer_data = {node.CMD: "undo_offer"}
            node.tx(offer_data)
            client_state_actions["undo_sent"] = True
        # The sender will sync, only need to apply for receiver
        if client_state_actions["undo_accept"] and client_state_actions["undo_received"]:
            offer_data = {node.CMD: "undo_accept"}
            node.tx(offer_data)
            # Undo two times if we accepted a takeback to set it to their turn
            client_game.undo_move()
            client_game.undo_move()
            init["sent"] = 0
            window.sessionStorage.setItem("undo_request", "false")
            client_state_actions["undo_received"] = False
            client_state_actions["undo_accept"] = False
            client_state_actions["undo_accept_executed"] = True
            promotion_required = False
            continue
        # If we are the sender during a promotion we wish to exit this state and sync
        if client_state_actions["undo_response_received"]:
            client_state_actions["undo_sent"] = False
            client_state_actions["undo_response_received"] = False
            client_state_actions["undo"] = False
            client_state_actions["undo_executed"] = True
            promotion_required = False
            continue
        if client_state_actions["undo_deny"]:
            reset_data = {node.CMD: "undo_reset"}
            node.tx(reset_data)
            client_state_actions["undo_deny"] = False
            client_state_actions["undo_deny_executed"] = True
            client_state_actions["undo_received"] = False
            window.sessionStorage.setItem("undo_request", "false")

        if client_state_actions["resign"]:
            client_game.undo_move()
            client_game._move_undone = False
            client_game._sync = True
            reset_data = {node.CMD: "reset"}
            node.tx(reset_data)
            client_game.forced_end = "White Resigned" if client_game.current_turn else "Black Resigned"
            print(client_game.forced_end)
            client_game.end_position = True
            client_game.add_end_game_notation(True)
            client_state_actions["resign"] = False
            client_state_actions["resign_executed"] = True
            promotion_required = False
            continue

        if client_state_actions["draw_offer"] and not client_state_actions["draw_offer_sent"]:
            offer_data = {node.CMD: "draw_offer"}
            node.tx(offer_data)
            client_state_actions["draw_offer_sent"] = True
        if client_state_actions["draw_accept"] and client_state_actions["draw_offer_received"]:
            client_game.undo_move()
            client_game._move_undone = False
            client_game._sync = True
            offer_data = {node.CMD: "draw_accept"}
            node.tx(offer_data)
            client_game.forced_end = "Draw by mutual agreement"
            print(client_game.forced_end)
            client_game.end_position = True
            client_game.add_end_game_notation(False)
            client_state_actions["draw_offer_received"] = False
            client_state_actions["draw_accept"] = False
            client_state_actions["draw_accept_executed"] = True
            promotion_required = False
            continue
        if client_state_actions["draw_response_received"]:
            client_game.undo_move()
            client_game._move_undone = False
            client_game._sync = True
            client_game.forced_end = "Draw by mutual agreement"
            print(client_game.forced_end)
            client_game.end_position = True
            client_game.add_end_game_notation(False)
            client_state_actions["draw_offer_sent"] = False
            client_state_actions["draw_response_received"] = False
            client_state_actions["draw_offer"] = False
            client_state_actions["draw_offer_executed"] = True
            promotion_required = False
            continue
        if client_state_actions["draw_deny"]:
            reset_data = {node.CMD: "draw_offer_reset"}
            node.tx(reset_data)
            client_state_actions["draw_deny"] = False
            client_state_actions["draw_deny_executed"] = True
            client_state_actions["draw_offer_received"] = False
            window.sessionStorage.setItem("draw_request", "false")

        if client_state_actions["cycle_theme"]:
            drawing_settings["theme_index"] += 1
            drawing_settings["theme_index"] %= len(themes)
            current_theme.apply_theme(themes[drawing_settings["theme_index"]])
            drawing_settings["chessboard"] = generate_chessboard(current_theme)
            drawing_settings["coordinate_surface"] = generate_coordinate_surface(current_theme)
            draw_board_params["chessboard"] = drawing_settings["chessboard"]
            draw_board_params["coordinate_surface"] = drawing_settings["coordinate_surface"]
            client_state_actions["cycle_theme"] = False
            client_state_actions["cycle_theme_executed"] = True

        if client_state_actions["flip"]:
            current_theme.INVERSE_PLAYER_VIEW = not current_theme.INVERSE_PLAYER_VIEW
            drawing_settings["chessboard"] = generate_chessboard(current_theme)
            drawing_settings["coordinate_surface"] = generate_coordinate_surface(current_theme)
            draw_board_params["chessboard"] = drawing_settings["chessboard"]
            draw_board_params["coordinate_surface"] = drawing_settings["coordinate_surface"]
            promotion_buttons = display_promotion_options(current_theme, promotion_square[0], promotion_square[1])
            client_state_actions["flip"] = False
            client_state_actions["flip_executed"] = True
        
        if not init["final_updates"]:
            await handle_node_events(node, init, client_game, client_state_actions, offers, drawing_settings)

        for event in pygame.event.get():
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_t:
                    drawing_settings["theme_index"] += 1
                    drawing_settings["theme_index"] %= len(themes)
                    current_theme.apply_theme(themes[drawing_settings["theme_index"]])
                    # Redraw board and coordinates
                    drawing_settings["chessboard"] = generate_chessboard(current_theme)
                    drawing_settings["coordinate_surface"] = generate_coordinate_surface(current_theme)
                    draw_board_params["chessboard"] = drawing_settings["chessboard"]
                    draw_board_params["coordinate_surface"] = drawing_settings["coordinate_surface"]

                elif event.key == pygame.K_f:
                    current_theme.INVERSE_PLAYER_VIEW = not current_theme.INVERSE_PLAYER_VIEW
                    # Redraw board and coordinates
                    drawing_settings["chessboard"] = generate_chessboard(current_theme)
                    drawing_settings["coordinate_surface"] = generate_coordinate_surface(current_theme)
                    draw_board_params["chessboard"] = drawing_settings["chessboard"]
                    draw_board_params["coordinate_surface"] = drawing_settings["coordinate_surface"]
                    promotion_buttons = display_promotion_options(current_theme, promotion_square[0], promotion_square[1])

            for button in promotion_buttons:
                button.handle_event(event)
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    x, y = pygame.mouse.get_pos()
                    if button.rect.collidepoint(x, y):
                        client_game.promote_to_piece(row, col, button.piece)
                        promotion_required = False  # Exit promotion state condition
                        promoted = True

        game_window.fill((0, 0, 0))
        
        # Draw the board, we need to copy the params else we keep mutating them with each call for inverse board draws in 
        # the reverse_coordinates helper
        draw_board(draw_board_params.copy())
        
        overlay = pygame.Surface((current_theme.WIDTH, current_theme.HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 128))

        game_window.blit(overlay, (0, 0))

        for button in promotion_buttons:
            img = pieces[button.piece]
            img_x, img_y = button.rect.x, button.rect.y
            if button.is_hovered:
                img = pygame.transform.smoothscale(img, (current_theme.GRID_SIZE * 1.5, current_theme.GRID_SIZE * 1.5))
                img_x, img_y = button.scaled_x, button.scaled_y
            game_window.blit(img, (img_x, img_y))

        web_game_metadata = window.localStorage.getItem("web_game_metadata")

        web_game_metadata_dict = json.loads(web_game_metadata)

        # DEV logs to console
        # web_game_metadata_dict['console_messages'] = console_log_messages

        # TODO Can just put this into an asynchronous loop if I wanted or needed
        # Undo move, resign, draw offer, cycle theme, flip command handle
        for status_names in command_status_names:
            handle_command(status_names, client_state_actions, web_game_metadata_dict, "web_game_metadata", game_tab_id)     

        pygame.display.flip()
        await asyncio.sleep(0)

    window.sessionStorage.setItem("promoting", "false")
    await asyncio.sleep(0)
    return promoted

class Node(pygbag_net.Node):
    ...

async def handle_node_events(node, init, client_game, client_state_actions, offers, drawing_settings):
    if node.offline and init["reloaded"]:
        init["reloaded"] = False
    # Network events
    for ev in node.get_events():
        try:
            if ev == node.SYNC:
                print("SYNC:", node.proto, node.data[node.CMD])
                cmd = node.data[node.CMD]
                if cmd == "initialize":
                    init["starting_player"] = node.data.pop("start")
                    if node.data.get("starting_position"):
                        init["starting_position"] = json.loads(node.data.pop("starting_position"))
                        init["starting_position"]["_starting_player"] = init["starting_player"]
                        init["sent"] = int(init["starting_player"] != init["starting_position"]["current_turn"])
                        drawing_settings["recalc_selections"] = True
                        drawing_settings["clear_selections"] = True
                    else:
                        init["sent"] = int(not init["starting_player"])
                    init["initializing"] = True
                    init["reloaded"] = True
                elif cmd == f"{init['opponent']} ready":
                    init["waiting"] = False
                elif f"{init['opponent']}_update" in cmd or "_sync" in cmd:
                    if f"{init['opponent']}_update" in cmd:
                        game = Game(custom_params=json.loads(node.data.pop("game")))
                        if client_game._sync:
                            if (len(game.alg_moves) > len(client_game.alg_moves)) or (len(game.alg_moves) < len(client_game.alg_moves) and game._move_undone) or \
                                game.end_position:
                                    client_game.synchronize(game)
                                    drawing_settings["recalc_selections"] = True
                                    init["sent"] = 0
                                    if client_game.alg_moves != []:
                                        if not any(symbol in client_game.alg_moves[-1] for symbol in ['0-1', '1-0', '½–½']): # Could add a winning or losing sound
                                            if "x" not in client_game.alg_moves[-1]:
                                                move_sound.play()
                                            else:
                                                capture_sound.play()
                                        if client_game.end_position:
                                            is_white = client_game.current_turn
                                            checkmate, remaining_moves = is_checkmate_or_stalemate(client_game.board, is_white, client_game.moves)
                                            if checkmate:
                                                print("CHECKMATE")
                                            elif remaining_moves == 0:
                                                print("STALEMATE")
                                            elif client_game.threefold_check():
                                                print("DRAW BY THREEFOLD REPETITION")
                                            elif client_game.forced_end != "":
                                                print(client_game.forced_end)
                                            print("ALG_MOVES: ", client_game.alg_moves)
                                            break
                                        print("ALG_MOVES: ", client_game.alg_moves)
                    if "_sync" in cmd:
                        # Need to set game here if no update cmd is trigerred, else we have an old game we're comparing to
                        if "game" in node.data:
                            game = Game(custom_params=json.loads(node.data.pop("game")))
                        if (game.board == client_game.board and not client_game._sync) or "retrieve_sync" in cmd:
                            print(f"Syncing {init['player'].capitalize()}...")
                            client_game._sync = True
                            client_game._move_undone = False
                            your_turn = client_game.current_turn == client_game._starting_player
                            init["sent"] = 0 if your_turn else 1
                            init["desync"] = False if init["desync"] else False
                        # Handle double desync first to prevent infinite syncs sent back and forth
                        elif not game._sync and not client_game._sync and not init["desync"]:
                            confirmed_state = None
                            if not init["local_debug"]:
                                confirmed_state = await get_or_update_game(init["game_id"], init["access_keys"])
                            if confirmed_state is not None:
                                confirmed_state = json.loads(confirmed_state)
                                confirmed_state["_starting_player"] = init["starting_player"]
                                client_game = Game(custom_params=confirmed_state)
                                init["sent"] = 1
                                drawing_settings["recalc_selections"] = True
                                drawing_settings["clear_selections"] = True
                                node.tx({node.CMD: "_retrieve"})
                                init["desync"] = True
                                client_game._sync = False
                            else:
                                node.tx({node.CMD: "_fail"})
                                await asyncio.sleep(1)
                                node.quit()
                                raise Exception("Desynced")
                        elif "req_sync" in cmd:
                            txdata = {node.CMD: "_sync"}
                            send_game = client_game.to_json()
                            txdata.update({"game": send_game})
                            node.tx(txdata)
                            your_turn = client_game.current_turn == client_game._starting_player
                            init["sent"] = 0 if your_turn else 1
                elif cmd == "draw_offer":
                    if not client_state_actions["draw_offer_sent"]:
                        window.sessionStorage.setItem("draw_request", "true")
                        client_state_actions["draw_offer_received"] = True
                elif cmd == "draw_accept":
                    client_state_actions["draw_response_received"] = True
                elif cmd == "undo_offer":
                    if not client_state_actions["undo_sent"]:
                        window.sessionStorage.setItem("undo_request", "true")
                        client_state_actions["undo_received"] = True
                elif cmd == "undo_accept":
                    client_state_actions["undo_response_received"] = True
                elif cmd == "reset":
                    # TODO move this into a function
                    for offer_states in offers:
                        reset_required = client_state_actions[offer_states[1]]
                        if len(offer_states) == 5:
                            request_state = window.sessionStorage.getItem(offer_states[-1])
                            reset_required = reset_required or (request_state == "true")
                        if reset_required:
                            # TODO Maybe only set this once at the end
                            window.sessionStorage.setItem("total_reset", "true")
                            client_state_actions[offer_states[1]] = False 
                            client_state_actions[offer_states[3]] = True 
                            if "accept" not in offer_states[1] and "deny" not in offer_states[1]:
                                sent_status = offer_states[1] + "_sent"
                                received_status = offer_states[1] + "_received"
                                client_state_actions[sent_status] = False
                                client_state_actions[received_status] = False
                elif "reset" in cmd:
                    for offer_states in offers:
                        reset_required = client_state_actions[offer_states[1]]
                        if offer_states[-1] != cmd or not reset_required:
                            continue
                        client_state_actions[offer_states[1]] = False 
                        client_state_actions[offer_states[3]] = True
                        sent_status = offer_states[1] + "_sent"
                        client_state_actions[sent_status] = False

                elif cmd == "join_game":
                    print(node.data["nick"], "joined game")
                elif cmd == "rejoin":
                    print("Lobby/Game:", "Welcome", node.data['nick'])
                    if node.fork: # Need to handle spectators
                        node.fork = 0
                    node.publish()
                elif cmd == "_retrieve":
                    confirmed_state = None
                    if not init["local_debug"]:
                        confirmed_state = await get_or_update_game(init["game_id"], init["access_keys"])
                    if confirmed_state is not None:
                        confirmed_state = json.loads(confirmed_state)
                        confirmed_state["_starting_player"] = init["starting_player"]
                        client_game = Game(custom_params=confirmed_state)
                        init["sent"] = int(client_game._starting_player != client_game.current_turn)
                        drawing_settings["recalc_selections"] = True
                        drawing_settings["clear_selections"] = True
                        node.tx({node.CMD: "retrieve_sync"})
                    else:
                        node.tx({node.CMD: "_fail"})
                        await asyncio.sleep(1)
                        node.quit()
                        raise Exception("Desynced")
                elif cmd == "_fail":
                    node.quit()
                    raise Exception("Desynced")

            elif ev == node.GAME:
                print("GAME:", node.proto, node.data[node.CMD])
                cmd = node.data[node.CMD]

                if cmd == f"{init['opponent']} initialized":
                    node.tx({node.CMD: f"{init['player']} ready"})
                    init["waiting"] = False
                elif f"{init['opponent']}_update" in cmd or "_sync" in cmd:
                    if f"{init['opponent']}_update" in cmd:
                        game = Game(custom_params=json.loads(node.data.pop("game")))
                        if client_game._sync:
                            if (len(game.alg_moves) > len(client_game.alg_moves)) or (len(game.alg_moves) < len(client_game.alg_moves) and game._move_undone) or \
                                game.end_position:
                                    client_game.synchronize(game)
                                    drawing_settings["recalc_selections"] = True
                                    init["sent"] = 0
                                    if client_game.alg_moves != []:
                                        if not any(symbol in client_game.alg_moves[-1] for symbol in ['0-1', '1-0', '½–½']): # Could add a winning or losing sound
                                            if "x" not in client_game.alg_moves[-1]:
                                                move_sound.play()
                                            else:
                                                capture_sound.play()
                                        if client_game.end_position:
                                            is_white = True
                                            checkmate, remaining_moves = is_checkmate_or_stalemate(client_game.board, is_white, client_game.moves)
                                            if checkmate:
                                                print("CHECKMATE")
                                            elif remaining_moves == 0:
                                                print("STALEMATE")
                                            elif client_game.threefold_check():
                                                print("DRAW BY THREEFOLD REPETITION")
                                            elif client_game.forced_end != "":
                                                print(client_game.forced_end)
                                            print("ALG_MOVES: ", client_game.alg_moves)
                                            break
                                        print("ALG_MOVES: ", client_game.alg_moves)
                    if "_sync" in cmd:
                        # Need to set game here if no update cmd is triggered, else we have an old game
                        if "game" in node.data:
                            game = Game(custom_params=json.loads(node.data.pop("game")))
                        if (game.board == client_game.board and not client_game._sync) or "retrieve_sync" in cmd:
                            print(f"Syncing {init['player'].capitalize()}...")
                            client_game._sync = True
                            client_game._move_undone = False
                            your_turn = client_game.current_turn == client_game._starting_player
                            init["sent"] = 0 if your_turn else 1
                            init["desync"] = False if init["desync"] else False
                        # Handle double desync first to prevent infinite syncs sent back and forth
                        elif not game._sync and not client_game._sync and not init["desync"]:
                            confirmed_state = None
                            if not init["local_debug"]:
                                confirmed_state = await get_or_update_game(init["game_id"], init["access_keys"])
                            if confirmed_state is not None:
                                confirmed_state = json.loads(confirmed_state)
                                confirmed_state["_starting_player"] = init["starting_player"]
                                client_game = Game(custom_params=confirmed_state)
                                init["sent"] = 1
                                drawing_settings["recalc_selections"] = True
                                drawing_settings["clear_selections"] = True
                                node.tx({node.CMD: "_retrieve"})
                                init["desync"] = True
                                client_game._sync = False
                            else:
                                node.tx({node.CMD: "_fail"})
                                await asyncio.sleep(1)
                                node.quit()
                                raise Exception("Desynced")
                        # elif both games are unsynced, synchronize? and maybe or maybe not send something to halt infinite sync signals?
                        elif "req_sync" in cmd:
                            txdata = {node.CMD: "_sync"}
                            send_game = client_game.to_json()
                            txdata.update({"game": send_game})
                            node.tx(txdata)
                            your_turn = client_game.current_turn == client_game._starting_player
                            init["sent"] = 0 if your_turn else 1
                elif cmd == "draw_offer":
                    if not client_state_actions["draw_offer_sent"]:
                        window.sessionStorage.setItem("draw_request", "true")
                        client_state_actions["draw_offer_received"] = True
                elif cmd == "draw_accept":
                    client_state_actions["draw_response_received"] = True
                elif cmd == "undo_offer":
                    if not client_state_actions["undo_sent"]:
                        window.sessionStorage.setItem("undo_request", "true")
                        client_state_actions["undo_received"] = True
                elif cmd == "undo_accept":
                    client_state_actions["undo_response_received"] = True
                elif cmd == "reset":
                    # TODO move this into a function
                    for offer_states in offers:
                        reset_required = client_state_actions[offer_states[1]]
                        if len(offer_states) == 5:
                            request_state = window.sessionStorage.getItem(offer_states[-1])
                            reset_required = reset_required or (request_state == "true")
                        if reset_required:
                            # TODO Maybe only set this once at the end
                            window.sessionStorage.setItem("total_reset", "true")
                            client_state_actions[offer_states[1]] = False 
                            client_state_actions[offer_states[3]] = True 
                            if "accept" not in offer_states[1] and "deny" not in offer_states[1]:
                                sent_status = offer_states[1] + "_sent"
                                received_status = offer_states[1] + "_received"
                                client_state_actions[sent_status] = False
                                client_state_actions[received_status] = False
                elif "reset" in cmd:
                    for offer_states in offers:
                        reset_required = client_state_actions[offer_states[1]]
                        if offer_states[-1] != cmd or not reset_required:
                            continue
                        client_state_actions[offer_states[1]] = False 
                        client_state_actions[offer_states[3]] = True
                        sent_status = offer_states[1] + "_sent"
                        client_state_actions[sent_status] = False
                
                elif cmd == "clone":
                    # send all history to child
                    node.checkout_for(node.data)
                    init_message = {node.CMD: "initialize", "start": not init["starting_player"]}
                    if init["initialized"]:
                        init_message.update({"starting_position": client_game.to_json()})
                    else:
                        init["sent"] = int(not init["starting_player"])
                    node.tx(init_message)
                    if not init["initialized"]:
                        init["initializing"] = True
                elif cmd == "join_game":
                    print(node.data["nick"], "joined game")
                elif cmd == "rejoin":
                    print("Lobby/Game:", "Welcome", node.data['nick'])
                    if node.fork: # Need to handle spectators by not publishing to them if they live in a different room
                        node.fork = 0
                    node.publish()
                elif cmd == "_retrieve":
                    confirmed_state = None
                    if not init["local_debug"]:
                        confirmed_state = await get_or_update_game(init["game_id"], init["access_keys"])
                    if confirmed_state is not None:
                        confirmed_state = json.loads(confirmed_state)
                        confirmed_state["_starting_player"] = init["starting_player"]
                        client_game = Game(custom_params=confirmed_state)
                        init["sent"] = int(client_game._starting_player != client_game.current_turn)
                        drawing_settings["recalc_selections"] = True
                        drawing_settings["clear_selections"] = True
                        node.tx({node.CMD: "retrieve_sync"})
                    else:
                        node.tx({node.CMD: "_fail"})
                        await asyncio.sleep(1)
                        node.quit()
                        raise Exception("Desynced")
                elif cmd == "_fail":
                    node.quit()
                    raise Exception("Desynced")
                else:
                    print("87 ?", node.data)

            elif ev == node.CONNECTED:
                print(f"CONNECTED as {node.nick}")
                window.sessionStorage.setItem("connected", "true")
                if not init["network_reset_ready"]:
                    init["network_reset_ready"] = True

            elif ev == node.JOINED:
                print("Entered channel", node.joined)
                game_channel = f"{node.lobby}-{init['game_id']}"
                if node.joined == node.lobby_channel:
                    node.tx({node.CMD: "join_game", 'nick': node.nick})
                if node.joined == game_channel and not init["reloaded"]: # This should handle rejoining spectators differently, especially if not present in that code
                    node.pstree[node.pid]["forks"] = []
                    if node.oid in node.pstree and "forks" in node.pstree[node.oid]:
                        node.pstree[node.oid]["forks"] = []
                    node.tx({node.CMD: "rejoin", node.PID: node.pid, 'nick': node.nick})

            elif ev == node.TOPIC:
                print(f'[{node.channel}] TOPIC "{node.topics[node.channel]}"')

            elif ev == node.QUIT:
                print(f"Quit: {node.proto}, Reason: {node.data}")
                # Only if it's the other main player here, spectators can have different prefix names
                window.sessionStorage.setItem("connected", "false")
                u = node.proto.split("!")[0]
                if u in node.users:
                    del node.users[u]
                # TODO move this into a function
                for offer_states in offers:
                    reset_required = client_state_actions[offer_states[1]]
                    if len(offer_states) == 5:
                        request_state = window.sessionStorage.getItem(offer_states[-1])
                        reset_required = reset_required or (request_state == "true")
                    if reset_required:
                        # TODO Maybe only set this once at the end
                        window.sessionStorage.setItem("total_reset", "true")
                        client_state_actions[offer_states[1]] = False 
                        client_state_actions[offer_states[3]] = True 
                        if "accept" not in offer_states[1] and "deny" not in offer_states[1]:
                            sent_status = offer_states[1] + "_sent"
                            received_status = offer_states[1] + "_received"
                            client_state_actions[sent_status] = False
                            client_state_actions[received_status] = False

            elif ev in [node.LOBBY, node.LOBBY_GAME]:
                cmd, pid, nick, info = node.proto

                if cmd == node.HELLO:
                    print("Lobby/Game:", "Welcome", nick)
                    game_status = window.sessionStorage.getItem("connected")
                    if game_status != "true":
                        window.sessionStorage.setItem("connected", "true")
                    # publish if main
                    if not node.fork:
                        node.publish()

                elif (ev == node.LOBBY_GAME) and (cmd == node.OFFER):
                    if node.fork:
                        print("cannot fork, already a clone/fork pid=", node.fork)
                    elif len(node.pstree[node.pid]["forks"]):
                        print("cannot fork, i'm main for", node.pstree[node.pid]["forks"])
                    else:
                        print("forking to game offer", node.hint)
                        node.clone(pid)
                        print("cloning", init["player"], pid)

                else:
                    print(f"\nLOBBY/GAME: {node.fork=} {node.proto=} {node.data=} {node.hint=}")

            elif ev in [node.USERS]:
                ...

            elif ev in [node.GLOBAL]:
                print("GLOBAL:", node.data)

            elif ev in [node.SPURIOUS]:
                print(f"\nRAW: {node.proto=} {node.data=}")

            elif ev in [node.USERLIST]:
                print(node.proto, node.users)
                count = sum(1 for key in node.users.keys() if key.startswith("u_"))
                if count == 1:
                    if init["starting_position"] is not None:
                        init["waiting"] = False # Can be dependant on starting position later/game state
                    if not init["reloaded"]:
                        confirmed_state = None
                        if not init["local_debug"]:
                            confirmed_state = await get_or_update_game(init["game_id"], init["access_keys"])
                        if confirmed_state is not None:
                            confirmed_state = json.loads(confirmed_state)
                            confirmed_state["_starting_player"] = init["starting_player"]
                            client_game = Game(custom_params=confirmed_state)
                            init["sent"] = int(client_game._starting_player != client_game.current_turn)
                            drawing_settings["recalc_selections"] = True
                            drawing_settings["clear_selections"] = True
                        init["reloaded"] = True

            elif ev == node.RAW:
                print("RAW:", node.data)

            elif ev == node.PING:
                # print("ping", node.data)
                ...
            elif ev == node.PONG:
                # print("pong", node.data)
                ...

            # promisc mode dumps everything.
            elif ev == node.RX:
                ...

            else:
                print(f"52:{ev=} {node.rxq=}")
        except Exception as e:
            print(f"52:{ev=} {node.rxq=} {node.proto=} {node.data=}")
            sys.print_exception(e)

def initialize_game(init, game_id, node, drawing_settings):
    current_theme.INVERSE_PLAYER_VIEW = not init["starting_player"]
    if init["starting_player"]:
        pygame.display.set_caption("Chess - White")
    else:
        pygame.display.set_caption("Chess - Black")
    if init["starting_position"] is None:
        client_game = Game(new_board.copy(), init["starting_player"])
    else:
        client_game = Game(custom_params=init["starting_position"])
    drawing_settings["chessboard"] = generate_chessboard(current_theme)
    drawing_settings["coordinate_surface"] = generate_coordinate_surface(current_theme)
    init["player"] = "white" if init["starting_player"] else "black"
    init["opponent"] = "black" if init["starting_player"] else "white"
    window.sessionStorage.setItem("draw_request", "false")
    window.sessionStorage.setItem("undo_request", "false")
    window.sessionStorage.setItem("total_reset", "false")
    web_game_metadata = window.localStorage.getItem("web_game_metadata")
    if web_game_metadata is not None:
        web_game_metadata_dict = json.loads(web_game_metadata)
    else:
        web_game_metadata_dict = {}
    game_tab_id =  init["player"] + "-" + game_id
    window.sessionStorage.setItem("current_game_id", game_tab_id)
    # TODO extend this to load starting defaults for in play and historic games in script or through browser
    if not init["initialized"]:
        if (isinstance(web_game_metadata_dict, dict) or web_game_metadata is None):
            web_game_metadata_dict[game_tab_id] = {
                "end_state": '',
                "forced_end": '',
                "player_color": init["player"],
                "alg_moves": [],
                "comp_moves": [],
                "FEN_final_pos": "",
                "step": {
                    "execute": False,
                    "update_executed": False,
                    "index": None
                },
                "undo_move": {
                    "execute": False,
                    "update_executed": False,
                    "reset": False
                },
                "undo_move_accept": {
                    "execute": False,
                    "update_executed": False,
                    "reset": False
                },
                "undo_move_deny": {
                    "execute": False,
                    "update_executed": False,
                    "reset": False
                },
                "resign": {
                    "execute": False,
                    "update_executed": False
                },
                "draw_offer": {
                    "execute": False,
                    "update_executed": False,
                    "reset": False
                },
                "draw_offer_accept": {
                    "execute": False,
                    "update_executed": False,
                    "reset": False
                },
                "draw_offer_deny": {
                    "execute": False,
                    "update_executed": False,
                    "reset": False
                },
                "cycle_theme": {
                    "execute": False,
                    "update_executed": False
                },
                "flip_board": {
                    "execute": False,
                    "update_executed": False
                },
                "console_messages": []
            }
        else:
            raise Exception("Browser game metadata of wrong type", web_game_metadata_dict)
        web_game_metadata = json.dumps(web_game_metadata_dict)
        window.localStorage.setItem("web_game_metadata", web_game_metadata)
        web_ready = False
        web_game_metadata = window.localStorage.getItem("web_game_metadata")
        if web_game_metadata is not None:
            web_game_metadata_dict = json.loads(web_game_metadata)
            if web_game_metadata_dict.get(game_tab_id) is not None:
                web_ready = True
                init["initializing"], init["initialized"] = False, True
                node.tx({node.CMD: f"{init['player']} initialized"})
                window.sessionStorage.setItem("initialized", "true")
        if not web_ready:
            raise Exception("Failed to set web value")
    else:
        init["initializing"] = False
        node.tx({node.CMD: f"{init['player']} initialized"})
    return client_game, game_tab_id

async def waiting_screen(init, game_window, client_game, drawing_settings):
    # Need to pump the event queque like below in order to move window
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            init["running"] = False
            init["waiting"] = False
    if not drawing_settings["wait_screen_drawn"]:
        game_window.fill((0, 0, 0))

        draw_board({
            'window': game_window,
            'theme': current_theme,
            'board': client_game.board,
            'drawing_settings': drawing_settings,
            'selected_piece': None,
            'current_position': None,
            'previous_position': None,
            'right_clicked_squares': [],
            'drawn_arrows': [],
            'valid_moves': [],
            'valid_captures': [],
            'valid_specials': [],
            'pieces': pieces,
            'hovered_square': None,
            'selected_piece_image': None
        })

        overlay = pygame.Surface((current_theme.WIDTH, current_theme.HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 128))

        game_window.blit(overlay, (0, 0))
        pygame.display.flip()
        drawing_settings["wait_screen_drawn"] = True
    await asyncio.sleep(0)

def reset_request(request, init, node, client_state_actions):
    if request == "draw":
        request_name, accept_reset, deny_reset, request_received = \
            "draw_request", "draw_accept_reset", "draw_deny_reset", "draw_offer_received"
        request_sent, offer_action, offer_reset = "draw_offer_sent", "draw_offer", "draw_offer_reset"
    elif request == "undo":
        request_name, accept_reset, deny_reset, request_received = \
            "undo_request", "undo_accept_reset", "undo_deny_reset", "undo_received"
        request_sent, offer_action, offer_reset = "undo_sent", "undo", "undo_reset"
    else:
        return
    
    request_value = window.sessionStorage.getItem(request_name)
    try:
        request_value = json.loads(request_value)
    except (json.JSONDecodeError, ValueError):
        request_value = False
    if not init["sent"] and request_value:
        reset_data = {node.CMD: "reset"}
        node.tx(reset_data)
        window.sessionStorage.setItem("total_reset", "true")
        client_state_actions[accept_reset] = True
        client_state_actions[deny_reset] = True
        client_state_actions[request_received] = False
    if not init["sent"] and client_state_actions[request_sent]:
        reset_data = {node.CMD: "reset"}
        node.tx(reset_data)
        window.sessionStorage.setItem("total_reset", "true")
        client_state_actions[offer_action] = False
        client_state_actions[offer_reset] = True
        client_state_actions[request_sent] = False

# TODO Move to helpers later on refactor
async def get_or_update_game(game_id, access_keys, client_game = "", post = False):
    if post:
        if isinstance(client_game, str): # could just be not game but we add hinting later
            raise Exception('Wrong POST input')
        client_game._sync = True
        client_game._move_undone = False
        client_game_str = client_game.to_json()
        try:
            url = 'http://127.0.0.1:8000/game-state/' + game_id + '/'
            handler = fetch.RequestHandler()
            secret_key = access_keys["updatekey"] + game_id
            js_code = """
                function generateToken(game_json, secret) {
                    const oPayload = {game: game_json};
                    const oHeader = {alg: 'HS256', typ: 'JWT'};
                    return KJUR.jws.JWS.sign('HS256', JSON.stringify(oHeader), JSON.stringify(oPayload), secret);
                };
                const existingScript = document.querySelector(`script[src='https://cdnjs.cloudflare.com/ajax/libs/jsrsasign/8.0.20/jsrsasign-all-min.js']`);
                if (!existingScript) {
                    const script = document.createElement('script');
                    script.src = 'https://cdnjs.cloudflare.com/ajax/libs/jsrsasign/8.0.20/jsrsasign-all-min.js';
                    script.onload = function() {
                        window.encryptedToken = generateToken('game_string', 'secret_key');
                    };
                    document.head.appendChild(script);
                } else {
                    window.encryptedToken = generateToken('game_string', 'secret_key');
                };
            """.replace("game_string", client_game_str).replace("secret_key", secret_key)
            window.eval(js_code)
            await asyncio.sleep(0)
            while window.encryptedToken is None:
                await asyncio.sleep(0)
            encrytedToken = window.encryptedToken
            window.encryptedToken = None
            csrf = window.sessionStorage.getItem("csrftoken")
            response = await handler.post(url, data = {"token": encrytedToken}, headers = {'X-CSRFToken': csrf})# null token handling
            data = json.loads(response)
            if data.get("status") and data["status"] == "error":
                raise Exception(f'Request failed {data}')
            # # no response handling?
        except Exception as e:
            js_code = f"console.log('{str(e)}')".replace(secret_key, "####")
            window.eval(js_code)
            raise Exception(str(e))
    else:
        try:
            url = 'http://127.0.0.1:8000/game-state/' + game_id + '/'
            handler = fetch.RequestHandler()
            response = await handler.get(url)
            data = json.loads(response)
            if data.get("status") and data["status"] == "error":
                raise Exception('Request failed')
            elif data.get("message") and data["message"] == "DNE":
                return None
            elif data.get("token"):
                response_token = data["token"]
            else:
                raise Exception('Request failed')
            # # no response handling?
            secret_key = access_keys["updatekey"] + game_id
            js_code = """
                function decodeToken(token, secret) {
                    const isValid = KJUR.jws.JWS.verify(token, secret, ['HS256']);
                    if (isValid) {
                        const decoded = KJUR.jws.JWS.parse(token);
                        return JSON.stringify(decoded.payloadObj);
                    } else {
                        return "invalid";
                    };
                };
                const existingScript = document.querySelector(`script[src='https://cdnjs.cloudflare.com/ajax/libs/jsrsasign/8.0.20/jsrsasign-all-min.js']`);
                if (!existingScript) {
                    const script = document.createElement('script');
                    script.src = 'https://cdnjs.cloudflare.com/ajax/libs/jsrsasign/8.0.20/jsrsasign-all-min.js';
                    script.onload = function() {
                        window.payload = decodeToken('response_token', 'secret_key');
                    };
                    document.head.appendChild(script);
                } else {
                    window.payload = decodeToken('response_token', 'secret_key');
                };
            """.replace("response_token", response_token).replace("secret_key", secret_key)
            window.eval(js_code)
            await asyncio.sleep(0)
            while window.payload is None: # Keep trying here for now but add timeout later
                await asyncio.sleep(0)
            game_payload = window.payload
            window.payload = None
            return game_payload
        except Exception as e:
            js_code = f"console.log('{str(e)}')".replace(secret_key, "####")
            window.eval(js_code)
            raise Exception(str(e))

# TODO Move to helpers later on refactor
def load_keys(file_path):
    keys = {}
    with open(file_path, 'r') as file:
        lines = file.readlines()
        for line in lines:
            parts = line.strip().split('_')
            if len(parts) == 2:
                key, value = parts
                keys[key] = value
    return keys

# Main loop
async def main():
    game_id = window.sessionStorage.getItem("current_game_id")
    if game_id is None:
        raise Exception("No game id set")
    # TODO have dev channel/mode
    builtins.node = Node(gid=game_id, groupname="Classical Chess", offline="offline" in sys.argv)
    node = builtins.node
    init = {
        "game_id": game_id,
        "running": True,
        "loaded": False,
        "waiting": True,
        "initializing": False,
        "initialized": False,
        "config_retrieved": False,
        "starting_player": None,
        "starting_position": None,
        "sent": None,
        "player": None,
        "opponent": None,
        "local_debug": True,
        "access_keys": None,
        "network_reset_ready": True,
        "desync": False,
        "reloaded": True,
        "final_updates": False
    }
    client_game = None
    # Web Browser actions affect these only. Even if players try to alter it, 
    # It simply enables the buttons or does a local harmless action
    client_state_actions = {
        "step": False,
        "step_executed": False,
        "undo": False,
        "undo_executed": False,
        "undo_sent": False,
        "undo_received": False,
        "undo_response_received": False,
        "undo_reset": False,
        "undo_accept": False,
        "undo_accept_executed": False,
        "undo_accept_reset": False,
        "undo_deny": False,
        "undo_deny_executed": False,
        "undo_deny_reset": False,
        "cycle_theme": False,
        "cycle_theme_executed": False,
        "resign": False,
        "resign_executed": False,
        "draw_offer": False,
        "draw_offer_executed": False,
        "draw_offer_sent": False,
        "draw_offer_received": False,
        "draw_response_received": False,
        "draw_offer_reset": False,
        "draw_accept": False,
        "draw_accept_executed": False,
        "draw_accept_reset": False,
        "draw_deny": False,
        "draw_deny_executed": False,
        "draw_deny_reset": False,
        "flip": False,
        "flip_executed": False,
    }
    # This holds the command name for the web localstorage object and the associated keys in the above dictionary
    command_status_names = [
        ("step", "step", "step_executed"),
        ("undo_move", "undo", "undo_executed", "undo_reset"),
        ("undo_move_accept", "undo_accept", "undo_accept_executed", "undo_accept_reset"),
        ("undo_move_deny", "undo_deny", "undo_deny_executed", "undo_deny_reset"),
        ("draw_offer", "draw_offer", "draw_offer_executed", "draw_offer_reset"),
        ("draw_offer_accept", "draw_accept", "draw_accept_executed", "draw_accept_reset"),
        ("draw_offer_deny", "draw_deny", "draw_deny_executed", "draw_deny_reset")
    ]
    offers = command_status_names.copy()

    request_mapping = [
        ["undo_move_accept","undo_request"], 
        ["undo_move_deny","undo_request"],
        ["draw_offer_accept","draw_request"], 
        ["draw_offer_deny","draw_request"]
    ]

    for i in range(len(offers)):
        for associated in request_mapping:
            if offers[i][0] == associated[0]:
                offers[i] += (associated[1],)

    command_status_names.extend(
        [
            ("resign", "resign", "resign_executed"),
            ("cycle_theme", "cycle_theme", "cycle_theme_executed"),
            ("flip_board", "flip", "flip_executed")
        ]
    )

    console_log_messages = []

    selected_piece = None
    hovered_square = None
    current_right_clicked_square = None
    end_right_released_square = None
    right_clicked_squares = []
    drawn_arrows = []
    # Boolean stating the first intention of moving a piece
    first_intent = False
    selected_piece_image = None
    # Locks the game state due to pawn promotion
    promotion_required = False
    promotion_square = None
    valid_moves = []
    valid_captures = []
    valid_specials = []

    left_mouse_button_down = False
    right_mouse_button_down = False

    drawing_settings = {
        # Only draw these surfaces as needed; once per selection of theme
        "chessboard": generate_chessboard(current_theme),
        "coordinate_surface": generate_coordinate_surface(current_theme),
        "theme_index": 0,
        "wait_screen_drawn": False,
        "recalc_selections": False,
        "clear_selections": False
    }

    # Main game loop
    while init["running"]:
        try:
            if not init["final_updates"]:
                await handle_node_events(node, init, client_game, client_state_actions, offers, drawing_settings)
        except Exception as e:
            js_code = f"console.log('{str(e)}')"
            window.eval(js_code)
            raise Exception(str(e))

        if init["initializing"]:
            client_game, game_tab_id = initialize_game(init, game_id, node, drawing_settings)

        elif not init["loaded"]:
            if not init["config_retrieved"] and not init["local_debug"]:
                access_keys = load_keys("secrets.txt")
                init["access_keys"] = access_keys
                try:
                    url = 'http://127.0.0.1:8000/config/' + game_id + '/'
                    handler = fetch.RequestHandler()
                    response = await handler.get(url)
                    data = json.loads(response)
                    if data.get("status") and data["status"] == "error":
                        raise Exception(f'Request failed {data}')
                    init["config_retrieved"] = True
                    if data["message"]["starting_side"] == "white":
                        init["starting_player"] = True 
                    elif data["message"]["starting_side"] == "black":
                        init["starting_player"] = False 
                    else:
                        raise Exception("Bad request")
                    window.sessionStorage.setItem("color", data["message"]["starting_side"])
                except Exception as e:
                    js_code = f"console.log('{str(e)}')"
                    window.eval(js_code)
                    raise Exception(str(e))
            retrieved_state = None
            if init["local_debug"]:
                init["starting_player"] = True
                window.sessionStorage.setItem("color", "white")
            else:
                retrieved_state = await get_or_update_game(game_id, access_keys)
            
            current_theme.INVERSE_PLAYER_VIEW = not init["starting_player"]
            pygame.display.set_caption("Chess - Waiting on Connection")
            if retrieved_state is None:
                client_game = Game(new_board.copy(), init["starting_player"])
                init["player"] = "white"
                init["opponent"] = "black"
                init["loaded"] = True
            else:
                drawing_settings["chessboard"] = generate_chessboard(current_theme)
                drawing_settings["coordinate_surface"] = generate_coordinate_surface(current_theme)
                init["starting_position"] = json.loads(retrieved_state)
                init["starting_position"]["_starting_player"] = init["starting_player"]
                client_game = Game(custom_params=init["starting_position"])
                init["player"] = "white" if init["starting_player"] else "black"
                init["opponent"] = "black" if init["starting_player"] else "white"
                init["sent"] = int(client_game._starting_player != client_game.current_turn)
                init["initializing"] = True
                init["loaded"] = True
                continue

        if init["waiting"]:
            await waiting_screen(init, game_window, client_game, drawing_settings)
            continue

        if node.offline and init["network_reset_ready"]:
            # TODO move this into a function
            for offer_states in offers:
                reset_required = client_state_actions[offer_states[1]]
                if len(offer_states) == 5:
                    request_state = window.sessionStorage.getItem(offer_states[-1])
                    reset_required = reset_required or (request_state == "true")
                if reset_required:
                    # TODO Maybe only set this once at the end
                    window.sessionStorage.setItem("total_reset", "true")
                    client_state_actions[offer_states[1]] = False 
                    client_state_actions[offer_states[3]] = True 
                    if "accept" not in offer_states[1] and "deny" not in offer_states[1]:
                        sent_status = offer_states[1] + "_sent"
                        received_status = offer_states[1] + "_received"
                        client_state_actions[sent_status] = False
                        client_state_actions[received_status] = False
            init["network_reset_ready"] = False

        # Web browser actions/commands are received in previous loop iterations
        if client_state_actions["step"]:
            if client_game._sync: # Preventing stepping while syncing required
                drawing_settings["recalc_selections"] = True
                drawing_settings["clear_selections"] = True
                web_game_metadata = window.localStorage.getItem("web_game_metadata")
                web_game_metadata_dict = json.loads(web_game_metadata)
                move_index = web_game_metadata_dict[game_tab_id]["step"]["index"]
                client_game.step_to_move(move_index)
            client_state_actions["step"] = False
            client_state_actions["step_executed"] = True

        if not client_game.end_position:
            if client_state_actions["undo"] and not client_state_actions["undo_sent"]:
                offer_data = {node.CMD: "undo_offer"}
                node.tx(offer_data)
                client_state_actions["undo_sent"] = True
            # The sender will sync, only need to apply for receiver
            if client_state_actions["undo_accept"] and client_state_actions["undo_received"]:
                if not client_game._latest:
                    client_game.step_to_move(len(client_game.moves) - 1)
                offer_data = {node.CMD: "undo_accept"}
                node.tx(offer_data)
                your_turn = client_game.current_turn == client_game._starting_player
                client_game.undo_move()
                if not your_turn:
                    client_game.undo_move()
                init["sent"] = 0
                window.sessionStorage.setItem("undo_request", "false")
                hovered_square = None
                selected_piece_image = None
                selected_piece = None
                first_intent = False
                valid_moves, valid_captures, valid_specials = [], [], []
                right_clicked_squares = []
                drawn_arrows = []
                client_state_actions["undo_received"] = False
                client_state_actions["undo_accept"] = False
                client_state_actions["undo_accept_executed"] = True
            if client_state_actions["undo_response_received"]:
                client_state_actions["undo_sent"] = False
                client_state_actions["undo_response_received"] = False
                client_state_actions["undo"] = False
                client_state_actions["undo_executed"] = True
            if client_state_actions["undo_deny"]:
                reset_data = {node.CMD: "undo_reset"}
                node.tx(reset_data)
                client_state_actions["undo_deny"] = False
                client_state_actions["undo_deny_executed"] = True
                client_state_actions["undo_received"] = False
                window.sessionStorage.setItem("undo_request", "false")

            if client_state_actions["resign"]:
                if not client_game._latest:
                    client_game.step_to_move(len(client_game.moves) - 1)
                reset_data = {node.CMD: "reset"}
                node.tx(reset_data)
                client_game.forced_end = "White Resigned" if client_game.current_turn else "Black Resigned"
                print(client_game.forced_end)
                client_game.end_position = True
                client_game.add_end_game_notation(True)
                client_state_actions["resign"] = False
                client_state_actions["resign_executed"] = True

            if client_state_actions["draw_offer"] and not client_state_actions["draw_offer_sent"]:
                offer_data = {node.CMD: "draw_offer"}
                node.tx(offer_data)
                client_state_actions["draw_offer_sent"] = True
            if client_state_actions["draw_accept"] and client_state_actions["draw_offer_received"]:
                if not client_game._latest:
                    client_game.step_to_move(len(client_game.moves) - 1)
                offer_data = {node.CMD: "draw_accept"}
                node.tx(offer_data)
                client_game.forced_end = "Draw by mutual agreement"
                print(client_game.forced_end)
                client_game.end_position = True
                client_game.add_end_game_notation(False)
                client_state_actions["draw_offer_received"] = False
                client_state_actions["draw_accept"] = False
                client_state_actions["draw_accept_executed"] = True
            if client_state_actions["draw_response_received"]:
                client_game.forced_end = "Draw by mutual agreement"
                print(client_game.forced_end)
                client_game.end_position = True
                client_game.add_end_game_notation(False)
                client_state_actions["draw_offer_sent"] = False
                client_state_actions["draw_response_received"] = False
                client_state_actions["draw_offer"] = False
                client_state_actions["draw_offer_executed"] = True
            if client_state_actions["draw_deny"]:
                reset_data = {node.CMD: "draw_offer_reset"}
                node.tx(reset_data)
                client_state_actions["draw_deny"] = False
                client_state_actions["draw_deny_executed"] = True
                client_state_actions["draw_offer_received"] = False
                window.sessionStorage.setItem("draw_request", "false")

        if client_state_actions["cycle_theme"]:
            drawing_settings["theme_index"] += 1
            drawing_settings["theme_index"] %= len(themes)
            current_theme.apply_theme(themes[drawing_settings["theme_index"]])
            # Redraw board and coordinates
            drawing_settings["chessboard"] = generate_chessboard(current_theme)
            drawing_settings["coordinate_surface"] = generate_coordinate_surface(current_theme)
            client_state_actions["cycle_theme"] = False
            client_state_actions["cycle_theme_executed"] = True

        if client_state_actions["flip"]:
            current_theme.INVERSE_PLAYER_VIEW = not current_theme.INVERSE_PLAYER_VIEW
            # Redraw board and coordinates
            drawing_settings["chessboard"] = generate_chessboard(current_theme)
            drawing_settings["coordinate_surface"] = generate_coordinate_surface(current_theme)
            client_state_actions["flip"] = False
            client_state_actions["flip_executed"] = True

        # Have this after the step commands to not allow previous selections
        if drawing_settings["recalc_selections"]:
            if selected_piece:
                row, col = selected_piece
                piece = client_game.board[row][col]
                is_white = piece.isupper()
                if piece != ' ' and not drawing_settings["clear_selections"]:
                    first_intent, selected_piece, selected_piece_image, \
                    valid_moves, valid_captures, valid_specials, hovered_square = \
                        handle_new_piece_selection(client_game, row, col, is_white, hovered_square)
                else:
                    first_intent = False
                    selected_piece = None
                    valid_moves, valid_captures, valid_specials = [], [], []
                selected_piece_image = None
            drawing_settings["recalc_selections"] = False
            drawing_settings["clear_selections"] = False

        # An ugly indent but we need to send the draw_offer and resign execution status and skip unnecessary events
        # TODO make this skip cleaner or move it into a function
        if not client_game.end_position:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    init["running"] = False
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:
                        left_mouse_button_down = True
                    if event.button == 3:
                        right_mouse_button_down = True
                    
                    if right_mouse_button_down:
                        # If a piece is selected, unselect them and do not execute move logic
                        hovered_square = None
                        selected_piece_image = None
                        selected_piece = None
                        first_intent = False
                        valid_moves, valid_captures, valid_specials = [], [], []
                        
                        x, y = pygame.mouse.get_pos()
                        row, col = get_board_coordinates(x, y, current_theme.GRID_SIZE)
                        # Change input to reversed board given inverse view
                        if current_theme.INVERSE_PLAYER_VIEW:
                            row, col = map_to_reversed_board(row, col)
                        if not left_mouse_button_down:
                            current_right_clicked_square = (row, col)
                        continue

                    if left_mouse_button_down:
                        # Clear highlights and arrows
                        right_clicked_squares = []
                        drawn_arrows = []

                        x, y = pygame.mouse.get_pos()
                        row, col = get_board_coordinates(x, y, current_theme.GRID_SIZE)
                        # Change input to reversed board given inverse view
                        if current_theme.INVERSE_PLAYER_VIEW:
                            row, col = map_to_reversed_board(row, col)
                        piece = client_game.board[row][col]
                        is_white = piece.isupper()
                        
                        if not selected_piece:
                            if piece != ' ':
                                # Update states with new piece selection
                                first_intent, selected_piece, selected_piece_image, valid_moves, valid_captures, valid_specials, hovered_square = \
                                    handle_new_piece_selection(client_game, row, col, is_white, hovered_square)
                                
                        else:
                            # Allow moves only on current turn, if up to date, and synchronized
                            if client_game.current_turn == client_game._starting_player and client_game._latest and client_game._sync \
                                 and not node.offline and init["reloaded"]:
                                ## Free moves or captures
                                if (row, col) in valid_moves:
                                    promotion_square, promotion_required = \
                                        handle_piece_move(client_game, selected_piece, row, col, valid_captures)
                                    
                                    # Clear valid moves so it doesn't re-enter the loop and potentially replace the square with an empty piece
                                    valid_moves, valid_captures, valid_specials = [], [], []
                                    # Reset selected piece variables to represent state
                                    selected_piece, selected_piece_image = None, None
                                    
                                    if client_game.end_position:
                                        break
                                
                                ## Specials
                                elif (row, col) in valid_specials:
                                    piece, is_white = handle_piece_special_move(client_game, selected_piece, row, col)
                                    
                                    # Clear valid moves so it doesn't re-enter the loop and potentially replace the square with an empty piece
                                    valid_moves, valid_captures, valid_specials = [], [], []
                                    # Reset selected piece variables to represent state
                                    selected_piece, selected_piece_image = None, None

                                    if client_game.end_position:
                                        break

                                else:
                                    # Otherwise we are considering another piece or a re-selected piece
                                    if piece != ' ':
                                        if (row, col) == selected_piece:
                                            # If the mouse stays on a square and a piece is clicked a second time 
                                            # this ensures that mouseup on this square deselects the piece
                                            if first_intent:
                                                first_intent = False
                                            # Redraw the transparent dragged piece on subsequent clicks
                                            selected_piece_image = transparent_pieces[piece]
                                        
                                        if (row, col) != selected_piece:
                                            first_intent, selected_piece, selected_piece_image, valid_moves, valid_captures, valid_specials, hovered_square = \
                                                handle_new_piece_selection(client_game, row, col, is_white, hovered_square)
                            
                            # Otherwise (when not our move) we are considering another piece or a re-selected piece
                            elif piece != ' ':
                                if (row, col) == selected_piece:
                                    # If the mouse stays on a square and a piece is clicked a second time 
                                    # this ensures that mouseup on this square deselects the piece
                                    if first_intent:
                                        first_intent = False
                                    # Redraw the transparent dragged piece on subsequent clicks
                                    selected_piece_image = transparent_pieces[piece]
                                
                                if (row, col) != selected_piece:
                                    first_intent, selected_piece, selected_piece_image, valid_moves, valid_captures, valid_specials, hovered_square = \
                                        handle_new_piece_selection(client_game, row, col, is_white, hovered_square)    

                elif event.type == pygame.MOUSEMOTION:
                    x, y = pygame.mouse.get_pos()
                    row, col = get_board_coordinates(x, y, current_theme.GRID_SIZE)
                    if current_theme.INVERSE_PLAYER_VIEW:
                        row, col = map_to_reversed_board(row, col)

                    # Draw new hover with a selected piece and LMB
                    if left_mouse_button_down and selected_piece is not None:  
                        if (row, col) != hovered_square:
                            hovered_square = (row, col)

                elif event.type == pygame.MOUSEBUTTONUP:
                    if event.button == 1:
                        left_mouse_button_down = False
                        hovered_square = None
                        selected_piece_image = None
                        # For the second time a mouseup occurs on the same square it deselects it
                        # This can be an arbitrary number of mousedowns later
                        if not first_intent and (row, col) == selected_piece:
                                selected_piece = None
                                valid_moves, valid_captures, valid_specials = [], [], []
                        
                        # First intent changed to false if mouseup on same square the first time
                        if first_intent and (row, col) == selected_piece:
                            first_intent = not first_intent
                        
                        # Allow moves only on current turn, if up to date, and synchronized
                        if client_game.current_turn == client_game._starting_player and client_game._latest and client_game._sync \
                            and not node.offline and init["reloaded"]:
                            ## Free moves or captures
                            if (row, col) in valid_moves:
                                promotion_square, promotion_required = \
                                    handle_piece_move(client_game, selected_piece, row, col, valid_captures)
                                
                                # Clear valid moves so it doesn't re-enter the loop and potentially replace the square with an empty piece
                                valid_moves, valid_captures, valid_specials = [], [], []
                                # Reset selected piece variables to represent state
                                selected_piece, selected_piece_image = None, None

                                if client_game.end_position:
                                    break

                            ## Specials
                            elif (row, col) in valid_specials:
                                piece, is_white = handle_piece_special_move(client_game, selected_piece, row, col)
                                
                                # Clear valid moves so it doesn't re-enter the loop and potentially replace the square with an empty piece
                                valid_moves, valid_captures, valid_specials = [], [], []
                                # Reset selected piece variables to represent state
                                selected_piece, selected_piece_image = None, None

                                if client_game.end_position:
                                    break

                    if event.button == 3:
                        right_mouse_button_down = False
                        # Highlighting individual squares at will
                        if (row, col) == current_right_clicked_square:
                            if (row, col) not in right_clicked_squares:
                                right_clicked_squares.append((row, col))
                            else:
                                right_clicked_squares.remove((row, col))
                        elif current_right_clicked_square is not None:
                            x, y = pygame.mouse.get_pos()
                            row, col = get_board_coordinates(x, y, current_theme.GRID_SIZE)
                            if current_theme.INVERSE_PLAYER_VIEW:
                                row, col = map_to_reversed_board(row, col)
                            end_right_released_square = (row, col)

                            if [current_right_clicked_square, end_right_released_square] not in drawn_arrows:
                                # Disallow out of bound arrows
                                if 0 <= end_right_released_square[0] < 8 and 0 <= end_right_released_square[1] < 8:
                                    drawn_arrows.append([current_right_clicked_square, end_right_released_square])
                            else:
                                drawn_arrows.remove([current_right_clicked_square, end_right_released_square])
                
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_t:
                        drawing_settings["theme_index"] += 1
                        drawing_settings["theme_index"] %= len(themes)
                        current_theme.apply_theme(themes[drawing_settings["theme_index"]])
                        # Redraw board and coordinates
                        drawing_settings["chessboard"] = generate_chessboard(current_theme)
                        drawing_settings["coordinate_surface"] = generate_coordinate_surface(current_theme)

                    elif event.key == pygame.K_f:
                        current_theme.INVERSE_PLAYER_VIEW = not current_theme.INVERSE_PLAYER_VIEW
                        # Redraw board and coordinates
                        drawing_settings["chessboard"] = generate_chessboard(current_theme)
                        drawing_settings["coordinate_surface"] = generate_coordinate_surface(current_theme)

        game_window.fill((0, 0, 0))

        draw_board_params = {
            'window': game_window,
            'theme': current_theme,
            'board': client_game.board,
            'drawing_settings': drawing_settings,
            'selected_piece': selected_piece,
            'current_position': client_game.current_position,
            'previous_position': client_game.previous_position,
            'right_clicked_squares': right_clicked_squares,
            'drawn_arrows': drawn_arrows,
            'valid_moves': valid_moves,
            'valid_captures': valid_captures,
            'valid_specials': valid_specials,
            'pieces': pieces,
            'hovered_square': hovered_square,
            'selected_piece_image': selected_piece_image
        }

        draw_board(draw_board_params)

        if promotion_required:
            # Lock the game state (disable other input)
            
            # Display an overlay or popup with promotion options
            # We cannot simply reuse the above declaration as it can be mutated by draw_board
            draw_board_params = {
                'window': game_window,
                'theme': current_theme,
                'board': client_game.board,
                'drawing_settings': drawing_settings,
                'selected_piece': selected_piece,
                'current_position': client_game.current_position,
                'previous_position': client_game.previous_position,
                'right_clicked_squares': right_clicked_squares,
                'drawn_arrows': drawn_arrows,
                'valid_moves': valid_moves,
                'valid_captures': valid_captures,
                'valid_specials': valid_specials,
                'pieces': pieces,
                'hovered_square': hovered_square,
                'selected_piece_image': selected_piece_image
            }
            # TODO remove endState
            promoted = await promotion_state(
                promotion_square, 
                client_game, 
                row, 
                col, 
                draw_board_params, # These are mutated on first draw then flipped again
                client_state_actions, 
                command_status_names, 
                drawing_settings, 
                game_tab_id,
                node,
                init,
                offers
            )
            promotion_required, promotion_square = False, None

            if promoted:
                hovered_square = None
                selected_piece_image = None
                selected_piece = None
                first_intent = False
                valid_moves, valid_captures, valid_specials = [], [], []
                right_clicked_squares = []
                drawn_arrows = []

            # Remove the overlay and buttons by redrawing the board
            game_window.fill((0, 0, 0))
            # We likely need to reinput the arguments and can't use the above params as they are updated.
            draw_board({
                'window': game_window,
                'theme': current_theme,
                'board': client_game.board,
                'drawing_settings': drawing_settings,
                'selected_piece': selected_piece,
                'current_position': client_game.current_position,
                'previous_position': client_game.previous_position,
                'right_clicked_squares': right_clicked_squares,
                'drawn_arrows': drawn_arrows,
                'valid_moves': valid_moves,
                'valid_captures': valid_captures,
                'valid_specials': valid_specials,
                'pieces': pieces,
                'hovered_square': hovered_square,
                'selected_piece_image': selected_piece_image
            })
            # On MOUSEDOWN, piece could become whatever was there before and have the wrong color
            # We need to set the piece to be the pawn/new_piece to confirm checkmate immediately 
            # In the case of an undo this is fine and checkmate is always false
            piece = client_game.board[row][col]
            is_white = piece.isupper()

            checkmate, remaining_moves = is_checkmate_or_stalemate(client_game.board, not is_white, client_game.moves)
            if checkmate:
                print("CHECKMATE")
                client_game.end_position = True
                client_game.add_end_game_notation(checkmate)
            elif remaining_moves == 0:
                print("STALEMATE")
                client_game.end_position = True
                client_game.add_end_game_notation(checkmate)
            # This seems redundant as promotions should lead to unique boards but we leave it in anyway
            elif client_game.threefold_check():
                print("STALEMATE BY THREEFOLD REPETITION")
                client_game.forced_end = "Stalemate by Threefold Repetition"
                client_game.end_position = True
                client_game.add_end_game_notation(checkmate)
        
        # Only allow for retrieval of algebraic notation at this point after potential promotion, if necessary in the future
        web_game_metadata = window.localStorage.getItem("web_game_metadata")

        web_game_metadata_dict = json.loads(web_game_metadata)

        # DEV logs to console
        # web_game_metadata_dict[game_tab_id]['console_messages'] = console_log_messages
        
        # TODO Can just put this into an asynchronous loop if I wanted or needed, can also speed up by only executing when there are true values
        # Undo move, resign, draw offer, cycle theme, flip command handle
        for status_names in command_status_names:
            handle_command(status_names, client_state_actions, web_game_metadata_dict, "web_game_metadata", game_tab_id)        

        if web_game_metadata_dict[game_tab_id]['alg_moves'] != client_game.alg_moves:
            web_game_metadata_dict[game_tab_id]['alg_moves'] = client_game.alg_moves
            # TODO Maybe a simple range list of the index or move number
            web_game_metadata_dict[game_tab_id]['comp_moves'] = [','.join(move) for move in client_game.moves]

            web_game_metadata = json.dumps(web_game_metadata_dict)
            window.localStorage.setItem("web_game_metadata", web_game_metadata)
        
        # TODO Maybe I just set this in a better/DRY way?
        # The following just sets web information so that we know the playing player side, it might be useless? Can't remember why I implemented this
        if client_game._starting_player and web_game_metadata_dict[game_tab_id]['player_color'] != 'white':
            web_game_metadata_dict[game_tab_id]['player_color'] = 'white'

            web_game_metadata = json.dumps(web_game_metadata_dict)
            window.localStorage.setItem("web_game_metadata", web_game_metadata)
        elif not client_game._starting_player and web_game_metadata_dict[game_tab_id]['player_color'] != 'black':
            web_game_metadata_dict[game_tab_id]['player_color'] = 'black'

            web_game_metadata = json.dumps(web_game_metadata_dict)
            window.localStorage.setItem("web_game_metadata", web_game_metadata)
        
        # TODO Maybe move this section to after draw now and above?
        try:
            if (client_game.current_turn != client_game._starting_player or not client_game._sync) and not client_game.end_position:
                txdata = {node.CMD: f"{init['player']}_update"}
                if not client_game._sync:
                    txdata[node.CMD] += "_req_sync"
                send_game = client_game.to_json()
                txdata.update({"game": send_game})
                for potential_request in ["draw", "undo"]:
                    reset_request(potential_request, init, node, client_state_actions)
                if not init["sent"]:
                    node.tx(txdata)
                    if not init["local_debug"]:
                        await get_or_update_game(game_id, access_keys, client_game, post = True)
                    init["sent"] = 1
        except Exception as err:
            # maybe reloaded or offline here?
            print("Could not send/get games... ", err)

        if client_game.end_position and not init["final_updates"] and init["reloaded"]:
            try:
                reset_data = {node.CMD: "reset"}
                node.tx(reset_data)
                window.sessionStorage.setItem("draw_request", "false")
                window.sessionStorage.setItem("undo_request", "false")
                window.sessionStorage.setItem("total_reset", "true")
                txdata = {node.CMD: f"{init['player']}_update"}
                send_game = client_game.to_json()
                txdata.update({"game": send_game})
                node.tx(txdata)
                if not init["local_debug"]:
                    await get_or_update_game(game_id, access_keys, client_game, post = True)
                
                web_game_metadata = window.localStorage.getItem("web_game_metadata")

                web_game_metadata_dict = json.loads(web_game_metadata)

                if web_game_metadata_dict[game_tab_id]['end_state'] != client_game.alg_moves[-1]:
                    web_game_metadata_dict[game_tab_id]['end_state'] = client_game.alg_moves[-1]
                    web_game_metadata_dict[game_tab_id]['forced_end'] = client_game.forced_end
                    web_game_metadata_dict[game_tab_id]['alg_moves'] = client_game.alg_moves
                    web_game_metadata_dict[game_tab_id]['comp_moves'] = client_game.moves
                    web_game_metadata_dict[game_tab_id]['FEN_final_pos'] = client_game.translate_into_FEN()

                    web_game_metadata = json.dumps(web_game_metadata_dict)
                    window.localStorage.setItem("web_game_metadata", web_game_metadata)
                
                await asyncio.sleep(1)
                node.quit()
                init["final_updates"] = True
            except Exception as err:
                print("Could not send endgame position... ", err) # This would keep trying to resend on error which could be fine

        if client_game.end_position and client_game._latest:
            # Clear any selected highlights
            right_clicked_squares = []
            drawn_arrows = []
            
            game_window.fill((0, 0, 0))

            draw_board({
                'window': game_window,
                'theme': current_theme,
                'board': client_game.board,
                'drawing_settings': drawing_settings,
                'selected_piece': selected_piece,
                'current_position': client_game.current_position,
                'previous_position': client_game.previous_position,
                'right_clicked_squares': right_clicked_squares,
                'drawn_arrows': drawn_arrows,
                'valid_moves': valid_moves,
                'valid_captures': valid_captures,
                'valid_specials': valid_specials,
                'pieces': pieces,
                'hovered_square': hovered_square,
                'selected_piece_image': selected_piece_image
            })

            overlay = pygame.Surface((current_theme.WIDTH, current_theme.HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 128))

            game_window.blit(overlay, (0, 0))

        pygame.display.flip()
        await asyncio.sleep(0)

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        js_code = f"console.log('{str(e)}')"
        window.eval(js_code)