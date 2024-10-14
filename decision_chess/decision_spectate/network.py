import json
import fetch
import asyncio
import pygbag.aio as asyncio
import pygbag_net
import builtins
from game import *
from constants import *
from helpers import *

debug_prints = True
production = False
local = "http://127.0.0.1:8000"

## Network helper logic
# Helper to get a game state or post a state with a jwt token
async def get_or_update_game(window, game_id, access_keys, client_game = "", post = False):
    secret_key = access_keys["updatekey"] + game_id
    if post:
        if isinstance(client_game, str): # could just be not game but we add hinting later
            raise Exception('Wrong POST input')
        client_game._sync = True
        client_game._move_undone = False
        client_game_str = client_game.to_json(include_states=True)
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
            url = f'{domain}/game-state/' + game_id + '/?spectator=True'
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

# Helper to retrieve game from DB
async def reconnect(window, game_id, access_keys, init, drawing_settings):
    init["reconnecting"] = True
    retrieved_state = None
    try:
        if game_id != "":
            retrieved_state = await asyncio.wait_for(get_or_update_game(window, game_id, access_keys), timeout = 5)
        else:
            retrieved_state = None
        if retrieved_state is None:
            init["retrieved"] = Game(new_board.copy(), init["starting_player"], init["game_type"])
        else:
            retrieved_state = json.loads(retrieved_state)
            init["retrieved"] = Game(custom_params=retrieved_state)
        drawing_settings["draw"] = True
    except:
        err = 'Reconnection Failed. Reattempting...'
        js_code = f"console.log('{err}')"
        window.eval(js_code)
        print(err)
    init["reconnecting"] = False

# Main network event loop
async def handle_node_events(node, init, client_game, drawing_settings):
    if node.offline and init["reloaded"]:
        init["reloaded"] = False
    # Network events
    for ev in node.get_events():
        try:
            if ev == node.SYNC:
                print("SYNC:", node.proto, node.data[node.CMD])
                cmd = node.data[node.CMD]
                spectator_pid = node.data.get("spectator_pid")
                if cmd == "initialize" and (spectator_pid is None or spectator_pid == node.pid):
                    init["starting_player"] = True
                    if node.data.get("starting_position"):
                        init["starting_position"] = json.loads(node.data.pop("starting_position"))
                        init["starting_position"]["_starting_player"] = True
                    init["initializing"] = True
                    init["reloaded"] = True
                    drawing_settings["draw"] = True
                elif "_update" in cmd or "_sync" in cmd:
                    if "_update" in cmd:
                        game = Game(custom_params=json.loads(node.data.pop("game")))
                        if client_game._sync:
                            temp_alg_moves = client_game.alg_moves
                            client_game.synchronize(game)
                            drawing_settings["draw"] = True
                            if client_game.alg_moves != [] and temp_alg_moves != client_game.alg_moves:
                                if client_game.end_position:
                                    break
                    if "_sync" in cmd:
                        # Need to set game here if no update cmd is trigerred, else we have an old game we're comparing to
                        if "game" in node.data:
                            game = Game(custom_params=json.loads(node.data.pop("game")))
                        if (game.board == client_game.board and not client_game._sync) or "retrieve_sync" in cmd:
                            print("Syncing...")
                            client_game._sync = True
                            client_game._move_undone = False
                            init["desync"] = False if init["desync"] else False
                elif cmd == "drawings" and (spectator_pid is None or spectator_pid == node.data.get("spectator_pid")):
                    drawings = json.loads(node.data.pop("drawings"))
                    opposing_right_clicked_squares, opposing_drawn_arrows, right_clicked_squares, drawn_arrows = load_drawings(drawings)
                    drawing_settings["opposing_right_clicked_squares"] = opposing_right_clicked_squares
                    drawing_settings["opposing_drawn_arrows"] = opposing_drawn_arrows
                    if node.data.get("redraw"):
                        drawing_settings["right_clicked_squares"] = right_clicked_squares
                        drawing_settings["drawn_arrows"] = drawn_arrows
                    drawing_settings["draw"] = True

                elif cmd == "rejoin":
                    print("Lobby/Game:", "Welcome", node.data['nick'])
                elif cmd == "_fail":
                    node.quit()
                    raise Exception("Desynced")

            elif ev == node.GAME:
                print("GAME:", node.proto, node.data[node.CMD])
                cmd = node.data[node.CMD]
                spectator_pid = node.data.get("spectator_pid")
                if "_update" in cmd or "_sync" in cmd:
                    if "_update" in cmd:
                        game = Game(custom_params=json.loads(node.data.pop("game")))
                        if client_game._sync:
                            temp_alg_moves = client_game.alg_moves
                            client_game.synchronize(game)
                            drawing_settings["draw"] = True
                            if client_game.alg_moves != [] and temp_alg_moves != client_game.alg_moves:
                                if client_game.end_position:
                                    break
                    if "_sync" in cmd:
                        # Need to set game here if no update cmd is trigerred, else we have an old game we're comparing to
                        if "game" in node.data:
                            game = Game(custom_params=json.loads(node.data.pop("game")))
                        if (game.board == client_game.board and not client_game._sync) or "retrieve_sync" in cmd:
                            print("Syncing...")
                            client_game._sync = True
                            client_game._move_undone = False
                            init["desync"] = False if init["desync"] else False
                elif cmd == "drawings" and (spectator_pid is None or spectator_pid == node.data.get("spectator_pid")):
                    drawings = json.loads(node.data.pop("drawings"))
                    opposing_right_clicked_squares, opposing_drawn_arrows, right_clicked_squares, drawn_arrows = load_drawings(drawings)
                    drawing_settings["opposing_right_clicked_squares"] = opposing_right_clicked_squares
                    drawing_settings["opposing_drawn_arrows"] = opposing_drawn_arrows
                    if node.data.get("redraw"):
                        drawing_settings["right_clicked_squares"] = right_clicked_squares
                        drawing_settings["drawn_arrows"] = drawn_arrows
                    drawing_settings["draw"] = True
                    
                elif cmd == "join_game":
                    print(node.data["nick"], "joined game")
                elif cmd == "rejoin":
                    print("Lobby/Game:", "Welcome", node.data['nick'])
                elif cmd == "_fail":
                    node.quit()
                    raise Exception("Desynced")
                else:
                    print("87 ?", node.data)

            elif ev == node.CONNECTED:
                print(f"CONNECTED as {node.nick}")

            elif ev == node.JOINED:
                print("Entered channel", node.joined)
                game_channel = f"{node.lobby}-{init['game_id']}"
                if node.joined == node.lobby_channel and not node.in_game:
                    node.tx({node.CMD: "join_game", 'nick': node.nick}) # tx() joins the game lobby and sends another JOINED event
                    node.in_game = True
                if node.joined == game_channel and not init["reloaded"] and node.in_game:
                    node.tx({node.CMD: "rejoin", node.PID: node.pid, 'nick': node.nick, "forked_node": node.fork})

            elif ev == node.TOPIC:
                print(f'[{node.channel}] TOPIC "{node.topics[node.channel]}"')

            elif ev == node.QUIT:
                print(f"Quit: {node.proto}, Reason: {node.data}")
                u = node.proto.split("!")[0]
                if u in node.users:
                    del node.users[u]

            elif ev in [node.LOBBY, node.LOBBY_GAME]:
                cmd, pid, nick, info = node.proto

                if cmd == node.HELLO:
                    print("Lobby/Game:", "Welcome", nick)

                elif (ev == node.LOBBY_GAME) and (cmd == node.SPEC_OFFER):
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