import json
import fetch
import asyncio
import pygbag.aio as asyncio
import builtins
from game import *
from constants import *
from helpers import *

debug_prints = True
production = True
local = "http://127.0.0.1:8000"

## Network helper logic
# Helper to get a game state or post a state with a jwt token
async def get_or_update_game(window, game_id, access_keys, client_game = "", post = False):
    secret_key = access_keys["updatekey"] + game_id
    if post:
        if isinstance(client_game, str): # could just be not game but we add hinting later
            raise Exception('Wrong POST input')
        client_game_str = client_game.to_json(include_states=True).replace('"_sync": false', '"_sync": true')
        try:
            domain = 'https://decisionchess.com' if production else local
            url = f'{domain}/game-state/' + game_id + '/'
            handler = fetch.RequestHandler()
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
        except Exception as e:
            exc_str = str(e).replace("'", "\\x27").replace('"', '\\x22')
            js_code = f"console.log('{exc_str}')".replace(secret_key, "####")
            window.eval(js_code)
            raise Exception(str(e))
    else:
        try:
            domain = 'https://decisionchess.com' if production else local
            url = f'{domain}/game-state/' + game_id + '/'
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
            while window.payload is None: # Keep trying here
                await asyncio.sleep(0)
            game_payload = window.payload
            window.payload = None
            return game_payload
        except Exception as e:
            exc_str = str(e).replace("'", "\\x27").replace('"', '\\x22')
            js_code = f"console.log('{exc_str}')".replace(secret_key, "####")
            window.eval(js_code)
            raise Exception(str(e))

async def post_error(error, window, script_type):
    access_keys = load_keys("secrets.txt")
    game_id = "exercise"
    secret_key = access_keys["updatekey"] + game_id
    try:
        error = str(error).replace('\n', '\\n').replace("'", "\\x27").replace('"', '\\x22')#.replace('(', 'o-p').replace(')', 'c-p')
        domain = 'https://decisionchess.com' if production else local
        url = f'{domain}/error/{game_id}/'
        handler = fetch.RequestHandler()
        csrf = window.sessionStorage.getItem("csrftoken")
        js_code = """
            function generateToken(error, script_type, secret) {
                const oPayload = {error: error, script_type: script_type};
                const oHeader = {alg: 'HS256', typ: 'JWT'};
                return KJUR.jws.JWS.sign('HS256', JSON.stringify(oHeader), JSON.stringify(oPayload), secret);
            };
            const existingScript = document.querySelector(`script[src='https://cdnjs.cloudflare.com/ajax/libs/jsrsasign/8.0.20/jsrsasign-all-min.js']`);
            if (!existingScript) {
                const script = document.createElement('script');
                script.src = 'https://cdnjs.cloudflare.com/ajax/libs/jsrsasign/8.0.20/jsrsasign-all-min.js';
                script.onload = function() {
                    window.encryptedToken = generateToken('error_msg', 'script_type_str', 'secret_key');
                };
                document.head.appendChild(script);
            } else {
                window.encryptedToken = generateToken('error_msg', 'script_type_str', 'secret_key');
            };
        """.replace('secret_key', secret_key).replace("error_msg", error).replace('script_type_str', script_type)
        window.eval(js_code)
        await asyncio.sleep(0)
        while window.encryptedToken is None:
            await asyncio.sleep(0)
        encrytedToken = window.encryptedToken
        window.encryptedToken = None
        _ = await handler.post(url, data = {"token": encrytedToken}, headers = {'X-CSRFToken': csrf})
    except Exception as e:
        exc_str = str(e).replace("'", "\\x27").replace('"', '\\x22')
        js_code = f"console.log('{exc_str}')".replace(secret_key, "####")
        window.eval(js_code)
        raise Exception(str(e))

# Helper to retrieve game from DB
async def reconnect(window, game_id, access_keys, init):
    init["reconnecting"] = True
    retrieved_state = None
    try:
        retrieved_state = await asyncio.wait_for(get_or_update_game(window, game_id, access_keys), timeout = 5)
        if retrieved_state is None:
            init["retrieved"] = Game(new_board.copy(), init["starting_player"])
        else:
            retrieved_state = json.loads(retrieved_state)
            init["retrieved"] = Game(custom_params=retrieved_state)
        init["sent"] = 1
    except:
        err = 'Reconnection Failed. Reattempting...'
        js_code = f"console.log('{err}')"
        window.eval(js_code)
        print(err)
    init["reconnecting"] = False

# Helper to reset client state variables
def apply_resets(window, offers, client_state_actions):
    any_reset = False
    for offer_states in offers:
        reset_required = client_state_actions[offer_states[1]]
        any_reset = any_reset or reset_required
        if len(offer_states) == 5:
            request_state = window.sessionStorage.getItem(offer_states[-1])
            reset_required = reset_required or (request_state == "true")
        if reset_required:
            client_state_actions[offer_states[1]] = False 
            client_state_actions[offer_states[3]] = True 
            if "accept" not in offer_states[1] and "deny" not in offer_states[1]:
                sent_status = offer_states[1] + "_sent"
                received_status = offer_states[1] + "_received"
                client_state_actions[sent_status] = False
                client_state_actions[received_status] = False
    if any_reset:
        window.sessionStorage.setItem("total_reset", "true")

# Main network event loop
async def handle_node_events(node, window, init, client_game, client_state_actions, offers, drawing_settings):
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
                        if init["starting_player"]:
                            played_condition = init["starting_player"] == init["starting_position"]["white_played"]
                        else:
                            played_condition = not init["starting_player"] == init["starting_position"]["black_played"]
                        init["sent"] = int(played_condition)
                        drawing_settings["recalc_selections"] = True
                        drawing_settings["clear_selections"] = True
                    else:
                        init["sent"] = 0
                    init["initializing"] = True
                    init["reloaded"] = True
                elif cmd == f"{init['opponent']} ready":
                    init["waiting"] = False
                elif f"{init['opponent']}_update" in cmd or "_sync" in cmd:
                    if f"{init['opponent']}_update" in cmd:
                        game = Game(custom_params=json.loads(node.data.pop("game")))
                        if client_game._sync:
                            temp_alg_moves = client_game.alg_moves
                            illegal = client_game.synchronize(game)
                            drawing_settings["recalc_selections"] = True
                            # Unnecessary?
                            if not (client_game.white_played and client_game._starting_player) and \
                               not (client_game.black_played and not client_game._starting_player):
                                init["sent"] = 0
                            if client_game.alg_moves != [] and temp_alg_moves != client_game.alg_moves:
                                if not any(symbol in client_game.alg_moves[-1] for symbol in ['0-1', '1-0', '1-1', '½–½']): # Could add a winning or losing sound
                                    if "x" in client_game.alg_moves[-1][0] or "x" in client_game.alg_moves[-1][1]:
                                        handle_play(window, capture_sound)
                                    else:
                                        handle_play(window, move_sound)
                                if client_game.end_position:
                                    checkmate_white, remaining_moves_white = is_checkmate_or_stalemate(client_game.board, True, client_game.moves)
                                    checkmate_black, remaining_moves_black = is_checkmate_or_stalemate(client_game.board, False, client_game.moves)
                                    checkmate = checkmate_white or checkmate_black
                                    no_remaining_moves = remaining_moves_white == 0 or remaining_moves_black == 0
                                    if checkmate:
                                        print("CHECKMATE")
                                    elif no_remaining_moves:
                                        print("STALEMATE")
                                    elif client_game.threefold_check():
                                        print("DRAW BY THREEFOLD REPETITION")
                                    elif client_game.forced_end != "":
                                        print(client_game.forced_end)
                                    print("ALG_MOVES: ", client_game.alg_moves)
                                    break
                                print_d("ALG_MOVES: ", client_game.alg_moves, debug=debug_prints)
                            if illegal:
                                txdata = {node.CMD: f"{init['player']}_update"}
                                txdata[node.CMD] += "_req_sync"
                                send_game = client_game.to_json()
                                txdata.update({"game": send_game, "illegal": True})
                                node.tx(txdata)
                                init["sent"] = 1
                        if node.data.get('illegal'):
                            handle_play(window, error_sound)
                    if "_sync" in cmd:
                        # Need to set game here if no update cmd is trigerred, else we have an old game we're comparing to
                        if "game" in node.data:
                            game = Game(custom_params=json.loads(node.data.pop("game")))
                        if (game.board == client_game.board and not client_game._sync) or "retrieve_sync" in cmd:
                            print(f"Syncing {init['player'].capitalize()}...")
                            client_game._sync = True
                            client_game._move_undone = False
                            if client_game._starting_player:
                                played_condition = client_game._starting_player == client_game.white_played
                            else:
                                played_condition = not client_game._starting_player == client_game.black_played
                            init["sent"] = int(played_condition)
                            init["desync"] = False if init["desync"] else False
                        # Handle double desync first to prevent infinite syncs sent back and forth
                        elif not game._sync and not client_game._sync and not init["desync"]:
                            confirmed_state = None
                            if not init["local_debug"]:
                                try:
                                    confirmed_state = await asyncio.wait_for(get_or_update_game(window, init["game_id"], init["access_keys"]), timeout = 5)
                                except:
                                    err = 'Confirmed state retrieval failed. Quitting...'
                                    js_code = f"console.log('{err}')"
                                    window.eval(js_code)
                                    print(err)
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
                            init["sent"] = 0
                elif cmd == "drawings":
                    drawings = json.loads(node.data.pop("drawings"))
                    opposing_right_clicked_squares, opposing_drawn_arrows, right_clicked_squares, drawn_arrows = load_drawings(drawings)
                    drawing_settings["opposing_right_clicked_squares"] = opposing_right_clicked_squares
                    drawing_settings["opposing_drawn_arrows"] = opposing_drawn_arrows
                    if node.data.get("redraw"):
                        drawing_settings["right_clicked_squares"] = right_clicked_squares
                        drawing_settings["drawn_arrows"] = drawn_arrows
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
                    apply_resets(window, offers, client_state_actions)
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
                    if node.data['forked_node'] != node.pid:
                        node.publish()
                elif cmd == "_retrieve":
                    confirmed_state = None
                    if not init["local_debug"]:
                        try:
                            confirmed_state = await asyncio.wait_for(get_or_update_game(window, init["game_id"], init["access_keys"]), timeout = 5)
                        except:
                            err = 'Confirmed state retrieval failed. Quitting...'
                            js_code = f"console.log('{err}')"
                            window.eval(js_code)
                            print(err)
                    if confirmed_state is not None:
                        confirmed_state = json.loads(confirmed_state)
                        confirmed_state["_starting_player"] = init["starting_player"]
                        client_game = Game(custom_params=confirmed_state)
                        if client_game._starting_player:
                            played_condition = client_game._starting_player == client_game.white_played
                        else:
                            played_condition = not client_game._starting_player == client_game.black_played
                        init["sent"] = int(played_condition)
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
                            temp_alg_moves = client_game.alg_moves
                            illegal = client_game.synchronize(game)
                            drawing_settings["recalc_selections"] = True
                            # Unnecessary?
                            if not (client_game.white_played and client_game._starting_player) and \
                               not (client_game.black_played and not client_game._starting_player):
                                init["sent"] = 0
                            if client_game.alg_moves != [] and temp_alg_moves != client_game.alg_moves:
                                if not any(symbol in client_game.alg_moves[-1] for symbol in ['0-1', '1-0', '1-1', '½–½']): # Could add a winning or losing sound
                                    if "x" in client_game.alg_moves[-1][0] or "x" in client_game.alg_moves[-1][1]:
                                        handle_play(window, capture_sound)
                                    else:
                                        handle_play(window, move_sound)
                                if client_game.end_position:
                                    checkmate_white, remaining_moves_white = is_checkmate_or_stalemate(client_game.board, True, client_game.moves)
                                    checkmate_black, remaining_moves_black = is_checkmate_or_stalemate(client_game.board, False, client_game.moves)
                                    checkmate = checkmate_white or checkmate_black
                                    no_remaining_moves = remaining_moves_white == 0 or remaining_moves_black == 0
                                    if checkmate:
                                        print("CHECKMATE")
                                    elif no_remaining_moves:
                                        print("STALEMATE")
                                    elif client_game.threefold_check():
                                        print("DRAW BY THREEFOLD REPETITION")
                                    elif client_game.forced_end != "":
                                        print(client_game.forced_end)
                                    print("ALG_MOVES: ", client_game.alg_moves)
                                    break
                                print_d("ALG_MOVES: ", client_game.alg_moves, debug=debug_prints)
                            if illegal:
                                txdata = {node.CMD: f"{init['player']}_update"}
                                txdata[node.CMD] += "_req_sync"
                                send_game = client_game.to_json()
                                txdata.update({"game": send_game, "illegal": True})
                                node.tx(txdata)
                                init["sent"] = 1
                        if node.data.get('illegal'):
                            handle_play(window, error_sound)
                    if "_sync" in cmd:
                        # Need to set game here if no update cmd is triggered, else we have an old game
                        if "game" in node.data:
                            game = Game(custom_params=json.loads(node.data.pop("game")))
                        if (game.board == client_game.board and not client_game._sync) or "retrieve_sync" in cmd:
                            print(f"Syncing {init['player'].capitalize()}...")
                            client_game._sync = True
                            client_game._move_undone = False
                            if client_game._starting_player:
                                played_condition = client_game._starting_player == client_game.white_played
                            else:
                                played_condition = not client_game._starting_player == client_game.black_played
                            init["sent"] = int(played_condition)
                            init["desync"] = False if init["desync"] else False
                        # Handle double desync first to prevent infinite syncs sent back and forth
                        elif not game._sync and not client_game._sync and not init["desync"]:
                            confirmed_state = None
                            if not init["local_debug"]:
                                try:
                                    confirmed_state = await asyncio.wait_for(get_or_update_game(window, init["game_id"], init["access_keys"]), timeout = 5)
                                except:
                                    err = 'Confirmed state retrieval failed. Quitting...'
                                    js_code = f"console.log('{err}')"
                                    window.eval(js_code)
                                    print(err)
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
                            init["sent"] = 0
                elif cmd == "drawings":
                    drawings = json.loads(node.data.pop("drawings"))
                    opposing_right_clicked_squares, opposing_drawn_arrows, right_clicked_squares, drawn_arrows = load_drawings(drawings)
                    drawing_settings["opposing_right_clicked_squares"] = opposing_right_clicked_squares
                    drawing_settings["opposing_drawn_arrows"] = opposing_drawn_arrows
                    if node.data.get("redraw"):
                        drawing_settings["right_clicked_squares"] = right_clicked_squares
                        drawing_settings["drawn_arrows"] = drawn_arrows
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
                    apply_resets(window, offers, client_state_actions)
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
                        init_message.update({"starting_position": client_game.to_json(include_states=True)})
                    else:
                        if client_game._starting_player:
                            played_condition = client_game._starting_player == client_game.white_played
                        else:
                            played_condition = not client_game._starting_player == client_game.black_played
                        init["sent"] = int(played_condition)
                    node.tx(init_message)
                    if client_game.reveal_stage:
                        drawings = {
                            "right_clicked_squares": drawing_settings["right_clicked_squares"],
                            "drawn_arrows": drawing_settings["drawn_arrows"],
                            "opposing_right_clicked_squares": drawing_settings["opposing_right_clicked_squares"],
                            "opposing_drawn_arrows": drawing_settings["opposing_drawn_arrows"]
                        }
                        txdata = {node.CMD: "drawings", "drawings": json.dumps(drawings), "redraw": True}
                        node.tx(txdata)
                    if not init["initialized"]:
                        init["initializing"] = True
                elif cmd == "join_game":
                    print(node.data["nick"], "joined game")
                elif cmd == "rejoin":
                    print("Lobby/Game:", "Welcome", node.data['nick'])
                    if node.fork: # Need to handle spectators by not publishing to them if they live in a different room
                        node.fork = 0
                    if node.data['forked_node'] != node.pid:
                        node.publish()
                elif cmd == "_retrieve":
                    confirmed_state = None
                    if not init["local_debug"]:
                        try:
                            confirmed_state = await asyncio.wait_for(get_or_update_game(window, init["game_id"], init["access_keys"]), timeout = 5)
                        except:
                            err = 'Confirmed state retrieval failed. Quitting...'
                            js_code = f"console.log('{err}')"
                            window.eval(js_code)
                            print(err)
                    if confirmed_state is not None:
                        confirmed_state = json.loads(confirmed_state)
                        confirmed_state["_starting_player"] = init["starting_player"]
                        client_game = Game(custom_params=confirmed_state)
                        if client_game._starting_player:
                            played_condition = client_game._starting_player == client_game.white_played
                        else:
                            played_condition = not client_game._starting_player == client_game.black_played
                        init["sent"] = int(played_condition)
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
                    node.tx({node.CMD: "join_game", 'nick': node.nick}) # tx() joins the game lobby and sends another JOINED event
                if node.joined == game_channel and not init["reloaded"]: # This should handle rejoining spectators differently, especially if not present in that code
                    node.pstree[node.pid]["forks"] = []
                    if node.oid in node.pstree and "forks" in node.pstree[node.oid]:
                        node.pstree[node.oid]["forks"] = []
                    node.tx({node.CMD: "rejoin", node.PID: node.pid, 'nick': node.nick, "forked_node": node.fork})

            elif ev == node.TOPIC:
                print(f'[{node.channel}] TOPIC "{node.topics[node.channel]}"')

            elif ev == node.QUIT:
                print(f"Quit: {node.proto}, Reason: {node.data}")
                # Only if it's the other main player here, spectators can have different prefix names
                window.sessionStorage.setItem("connected", "false")
                u = node.proto.split("!")[0]
                if u in node.users:
                    del node.users[u]
                apply_resets(window, offers, client_state_actions)
                if node.fork:
                    node.fork = 0

            elif ev in [node.LOBBY, node.LOBBY_GAME]:
                cmd, pid, nick, info = node.proto

                if cmd == node.HELLO:
                    print("Lobby/Game:", "Welcome", nick)
                    game_status = window.sessionStorage.getItem("connected")
                    if game_status != "true":
                        window.sessionStorage.setItem("connected", "true")
                    # publish if main
                    if not node.fork or node.fork != pid:
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
                            retrieved = False
                            while not retrieved:
                                try:
                                    confirmed_state = await asyncio.wait_for(get_or_update_game(window, init["game_id"], init["access_keys"]), timeout = 5)
                                    retrieved = True
                                except:
                                    err = 'Game State retreival Failed. Reattempting...'
                                    js_code = f"console.log('{err}')"
                                    window.eval(js_code)
                                    print(err)
                        if confirmed_state is not None:
                            confirmed_state = json.loads(confirmed_state)
                            confirmed_state["_starting_player"] = init["starting_player"]
                            client_game = Game(custom_params=confirmed_state)
                            if client_game._starting_player:
                                played_condition = client_game._starting_player == client_game.white_played
                            else:
                                played_condition = not client_game._starting_player == client_game.black_played
                            init["sent"] = int(played_condition)
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