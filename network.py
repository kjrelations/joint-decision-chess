import socket
import pickle
import struct

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
        except:
            pass

    def send(self, data):
        try:
            send_data(self.client, data)
            return receive_data(self.client)
        except socket.error as err:
            print("Error sending data to server...", err)