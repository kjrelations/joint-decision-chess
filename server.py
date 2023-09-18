import socket
from _thread import *
import pickle
from game import *

server = ""
port = 5555

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

try:
    s.bind((server, port))
except socket.error as err:
    str(err)

s.listen(2)
print("Waiting for Connection, Server Started...")

games = {}
id_count = 0

new_board = [
    ['r', 'n', 'b', 'q', 'k', 'b', 'n', 'r'],
    ['p', 'p', 'p', 'p', 'p', 'p', 'p', 'p'],
    [' ', ' ', ' ', ' ', ' ', ' ', ' ', ' '],
    [' ', ' ', ' ', ' ', ' ', ' ', ' ', ' '],
    [' ', ' ', ' ', ' ', ' ', ' ', ' ', ' '],
    [' ', ' ', ' ', ' ', ' ', ' ', ' ', ' '],
    ['P', 'P', 'P', 'P', 'P', 'P', 'P', 'P'],
    ['R', 'N', 'B', 'Q', 'K', 'B', 'N', 'R']
]

def threaded_client(conn, starting_player, game_id):
    global id_count
    conn.send(pickle.dumps(starting_player))

    reply = ""
    while True:
        try:
            data = pickle.loads(conn.recv(2048*59))

            if game_id in games:
                paired_games = games[game_id]

                if not data:
                    print("Disconnected")
                    break
                else:
                    if starting_player:
                        if data.current_turn != paired_games[0].current_turn or data._sync != paired_games[0]._sync or data.end_position != paired_games[0].end_position:
                            paired_games[0] = data
                    else:
                        # I could just set sync to false upon end position reached, after turns, or move undone
                        if data.current_turn != paired_games[1].current_turn or data._sync != paired_games[1]._sync or data.end_position != paired_games[1].end_position:
                            paired_games[1] = data
                    reply = paired_games
                    print("Received: ", data)
                    print("Sending: ", reply)

                conn.sendall(pickle.dumps(reply))
            else:
                break
        except:
            break
    print("Lost connection")
    try:
        del games[game_id]
        print("Closing Game", game_id)
    except:
        pass
    id_count -= 1
    conn.close()

while True:
    conn, addr = s.accept()
    print("Connected to: ", addr)

    id_count += 1
    starting_player = True
    game_id = (id_count - 1) // 2
    if id_count % 2 == 1:
        games[game_id] = [Game(new_board.copy(), starting_player)]
        print("Creating a new game...")
    else:
        starting_player = False
        games[game_id].append(Game(new_board.copy(), starting_player))
    start_new_thread(threaded_client, (conn, starting_player, game_id))
    starting_player = not starting_player
