import socket
import struct
import json
import game

def send_data(conn, data):
    """
    Send data over the connection by first sending its length as a 4-byte integer,
    followed by the actual data.
    """
    if isinstance(data, game.Game):
        data_json = data.to_json()
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
    if isinstance(result, list):
        returned_object = []
        for json_game_str in result:
            returned_object.append(game.Game(custom_params=json.loads(json_game_str)))
    else:
        returned_object = result

    return returned_object

class Network:
    def __init__(self):
        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server = ""
        self.port = 5555
        self.addr = (self.server, self.port)
        self.player = self.connect() # To send a player specification to each client for them to know whether they're the starting player: white or black

    def get_player(self):
        return self.player

    def connect(self):
        try:
            self.client.connect(self.addr) # When we connect we should send some sort of validation token or object back to our client
            return receive_data(self.client)
        except Exception as err:
            print("Connection error...", err)

    def send(self, data):
        try:
            send_data(self.client, data)
            return receive_data(self.client)
        except socket.error as err:
            print("Error sending data to server...", err)