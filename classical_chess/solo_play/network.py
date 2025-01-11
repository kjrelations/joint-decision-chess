import json
import fetch
import asyncio
import pygbag.aio as asyncio
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
        # POSTed form is synced yet move can be undone and locally can be unsynced
        client_game_str = client_game.to_json(include_states=True).replace('"_sync": false', '"_sync": true')
        FEN = client_game.translate_into_FEN()
        try:
            domain = 'https://decisionchess.com' if production else local
            url = f'{domain}/game-state/' + game_id + '/'
            handler = fetch.RequestHandler()
            js_code = """
                function generateToken(game_json, secret, FEN_text) {
                    const oPayload = {game: game_json, FEN: FEN_text};
                    const oHeader = {alg: 'HS256', typ: 'JWT'};
                    return KJUR.jws.JWS.sign('HS256', JSON.stringify(oHeader), JSON.stringify(oPayload), secret);
                };
                const existingScript = document.querySelector(`script[src='https://cdnjs.cloudflare.com/ajax/libs/jsrsasign/8.0.20/jsrsasign-all-min.js']`);
                if (!existingScript) {
                    const script = document.createElement('script');
                    script.src = 'https://cdnjs.cloudflare.com/ajax/libs/jsrsasign/8.0.20/jsrsasign-all-min.js';
                    script.onload = function() {
                        window.encryptedToken = generateToken('game_string', 'secret_key', 'FEN_str');
                    };
                    document.head.appendChild(script);
                } else {
                    window.encryptedToken = generateToken('game_string', 'secret_key', 'FEN_str');
                };
            """.replace("game_string", client_game_str).replace("secret_key", secret_key).replace("FEN_str", FEN)
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

async def save_game(window, game_id, alg_moves_str, comp_moves_str, score, FEN_final, forced_end):
    try:
        domain = 'https://decisionchess.com' if production else local
        url = f'{domain}/save_game/'
        handler = fetch.RequestHandler()
        csrf = window.sessionStorage.getItem("csrftoken")
        response = await handler.put(url, data = {
            "game_uuid": game_id,
            "alg_moves": alg_moves_str,
            "outcome": score,
            "comp_moves": comp_moves_str,
            "FEN": FEN_final,
            "termination_reason": forced_end
            }, headers = {'X-CSRFToken': csrf})
        data = json.loads(response)
        if data.get("status") and data["status"] == "error":
            raise Exception(f'Request failed {data}')
    except Exception as e:
        exc_str = str(e).replace("'", "\\x27").replace('"', '\\x22')
        js_code = f"console.log('{exc_str}')"
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