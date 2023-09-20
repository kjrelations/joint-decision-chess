import socket
import struct
import time
import json
import game
from _thread import *

server = ""
port = 5555

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

try:
    s.bind((server, port))
except socket.error as err:
    str(err)

s.listen(2)
s.settimeout(10) # 10 seconds seems reasonable with a max 35 s before it breaks threads
print("Waiting for Connection, Server Started...")

games = {}
id_count = 0
reconnecting = False # Silly temporary implementation

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
    if isinstance(data, list):
        game_dicts = [game_obj.to_json() for game_obj in data]
        data_json = json.dumps(game_dicts)
    else:
        data_json = json.dumps(data)
    data_length = len(data_json)
    conn.send(struct.pack("!I", data_length))  # Send message length
    conn.send(data_json.encode())  # Send the actual data

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

    result = json.loads(data.decode())
    return result

def threaded_client(conn, starting_player, game_id, orig_addr):
    global id_count, reconnecting
    max_reconnection_attempts = 3
    retry_delay = 2
    send_data(conn, starting_player)

    reply = ""
    while True:
        try:
            data = receive_data(conn)

            if game_id in games:
                paired_games = games[game_id]

                if not data:
                    print("Disconnected")
                    reconnected, reconnecting = False, True
                    # Reconnection loop
                    for attempt in range(max_reconnection_attempts):  
                        try:
                            print("Waiting for client to reconnect, attempt {}/{}...".format(attempt + 1, max_reconnection_attempts))
                            conn, addr = s.accept()
                            if addr[0] == orig_addr[0]: # I know this isn't how things are done, this is only for prototyping
                                reconnected = True
                                print("Reconnected to the same client: ", addr)
                                send_data(conn, starting_player)  # Send starting player info again, ##### or maybe an ok signal
                                reconnecting = False
                                break  # Break out of the reconnection loop and continue receiving data
                            else:
                                print("Connection from a different client: ", addr)
                                conn.close()  # Close the connection from a different client

                        except Exception as reconnect_error:
                            if attempt < max_reconnection_attempts - 1:
                                print("Reconnection error, waiting before attempting to reconnect... ", reconnect_error)
                                time.sleep(retry_delay)  # Sleep for 2 seconds before trying to reconnect again
                                continue

                    if not reconnected:
                        print("Failed to reconnect, terminating...")
                        break
                else:
                    data = game.Game(custom_params=data)
                    if starting_player:
                        if data.current_turn != paired_games[0].current_turn or data._sync != paired_games[0]._sync or data.end_position != paired_games[0].end_position:
                            paired_games[0] = data
                    else:
                        # I could just set sync to false upon end position reached, after turns, or move undone
                        if data.current_turn != paired_games[1].current_turn or data._sync != paired_games[1]._sync or data.end_position != paired_games[1].end_position:
                            paired_games[1] = data
                    reply = paired_games
                    # TODO Could have sending and receiving as debug log, also need to define game __str__ method
                    # print("Received: ", data)
                    # print("Sending: ", reply)

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
    if not reconnecting:
        try:
            conn, addr = s.accept()
            print("Connected to: ", addr)
        except:
            continue
    else:
        continue

    id_count += 1
    starting_player = True
    game_id = (id_count - 1) // 2
    if id_count % 2 == 1:
        games[game_id] = [game.Game(new_board.copy(), starting_player)]
        print("Creating a new game...")
    else:
        starting_player = False
        games[game_id].append(game.Game(new_board.copy(), starting_player))
    start_new_thread(threaded_client, (conn, starting_player, game_id, addr))
    starting_player = not starting_player
