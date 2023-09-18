import socket
import pickle

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
            return pickle.loads(self.client.recv(2048*59))
        except:
            pass

    def send(self, data):
        try:
            self.client.send(pickle.dumps(data))
            return pickle.loads(self.client.recv(2048*59))
        except socket.error as err:
            print(err)