import socket
import pickle
import struct
from _thread import *
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

def send_data(conn, data):
    """
    Send data over the connection by first sending its length as a 4-byte integer,
    followed by the actual data.
    """
    data_pickle = pickle.dumps(data)
    data_length = len(data_pickle)
    conn.send(struct.pack("!I", data_length))  # Send message length
    conn.send(data_pickle)  # Send the actual data

def receive_data(conn):
    """
    Receive data from the connection by first reading the message length,
    then reading the actual data.
    """
    data_length_bytes = conn.recv(4)  # Read 4 bytes for message length
    if not data_length_bytes:
        return None
    data_length = struct.unpack("!I", data_length_bytes)[0]  # Unpack message length
    data = b""
    while len(data) < data_length:
        packet = conn.recv(data_length - len(data))
        if not packet:
            return None
        data += packet
    return pickle.loads(data)

def threaded_client(conn, starting_player, game_id):
    global id_count
    send_data(conn, starting_player)

    reply = ""
    while True:
        try:
            data = receive_data(conn)

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

                send_data(conn, reply)
            else:
                break
        except Exception as err:
            print("Error receiving, handling, or sending data...", err)
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
