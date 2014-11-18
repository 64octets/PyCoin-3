import socket, pickle, threading, socketserver
from P2P.messages import Message
from P2P.p2pserver import P2PServer

#from TransactionManager.transaction import Transaction
from struct import *

class P2PClient(object):
  HOST = '192.168.1.2'   # hard coded IP of the peer list server (for now)
  PORT = P2PServer.PORT  # grab the port number of the server
  #CLIENT_PORT = 65000       # right now this is set prior to creating a P2PClient
  server = None
  
  def __init__(self, host, port=None):
    if port:
      P2PClient.CLIENT_PORT = port
    else:
      P2PClient.CLIENT_PORT = 65000
    print('Creating client on port...', self.CLIENT_PORT)
    self.p2pserver = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    print('Connecting to host...')
    self.p2pserver.connect((host, P2PClient.PORT))
    self.myIP = self.p2pserver.getsockname()[0] # the ip of this machine
    self.trans_queue = []
    self.received_trans = []
    self.peer_list = []
    
  def send_message(self, message, payload=None):
    print('Sending message...')
    if message == Message.ADD:
      # if the message is add, send an 'ADD' message to the p2p server
      self.p2pserver.sendall(message)
      import time
      time.sleep(0.1)
      self.p2pserver.sendall(pack('I', self.CLIENT_PORT))
      self.peer_list = pickle.loads(self.p2pserver.recv(1024).strip())
      #print('Received peer list: ', self.peer_list)
      
    elif message == Message.NEW_TRANSACTION:
      # if the message is 'NEW_TRANSACTION', send the message and payload (packed transaction) to each peer
      if len(self.peer_list) == 1 and self.peer_is_self(self.peer_list[0]):
        self.queue_transaction(payload)
        print('queued transaction')
        return
      for peer in self.peer_list:
        
        # make sure we don't send the transaction back to ourselves.
        if self.peer_is_self(peer):
          continue
        
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        print('Connecting to peer', peer)
        s.connect(peer)
        print('sent message: ', message)
        s.sendall(message)
        import time
        time.sleep(0.1)
        print('sending payload...')
        s.sendall(payload)
        s.close()
    
    elif message == Message.REMOVE:
      self.p2pserver.sendall(message)
      
  def peer_is_self(self, peer):
    return peer[0] == self.myIP and peer[1] == self.CLIENT_PORT
    
  def queue_transaction(self, t):
    self.trans_queue.append(t)
    
  def queue_transaction_received(self, t):
    self.received_trans.append(t)
  
  def broadcast_transaction(self, t):
    self.send_message(Message.NEW_TRANSACTION, t)
    
  def update_peer_list(self, peer_list):
    self.peer_list = peer_list
    if len(self.trans_queue) > 0:
      print('sending queued transactions')
      for t in self.trans_queue:
        self.send_message(Message.NEW_TRANSACTION, t)
      
  def __del__(self):
    print('client dying...')
    try:
      self.p2pserver.sendall(Message.QUIT)
    except:
      pass
    finally:
      self.p2pserver.close()
      if self.server:
        self.server.shutdown()
        print('server dying...')
      
  #@classmethod
  def start_server(self):
    if self.server:
      return
    print('starting server...')
    HOST = ''     #allow connections from any ip address
    print('Serving on: ', ('', self.CLIENT_PORT))
    self.server = socketserver.TCPServer((HOST, self.CLIENT_PORT), TCPHandler)
    print('running...')
    self.server.serve_forever()
  
  def run(self):
    t = threading.Thread(target=self.start_server)
    t.start()

class TCPHandler(socketserver.BaseRequestHandler):
  """ Handles incoming tcp requests """
  def handle(self):
    print('received message from a peer...')
    message = self.request.recv(15).strip()
    if message == Message.NEW_TRANSACTION:
      from TransactionManager.transaction import Transaction
      trans = self.request.recv(1024).strip()
      t = Transaction()
      t.unpack(trans)
      from P2P.client_manager import P2PClientManager
      client = P2PClientManager.getClient()
      client.queue_transaction_received(t)
      print(client.received_trans)
    elif message == Message.ADD:
      from P2P.client_manager import P2PClientManager
      client = P2PClientManager.getClient()
      port = self.request.recv(128).strip()
      peer_list = pickle.loads(port)
      print('peer list: ', peer_list)
      client.update_peer_list(peer_list)
      
      

if __name__ == '__main__':
  import sys
  from keystore import KeyStore
  port = sys.argv[1]
  P2PClient.CLIENT_PORT = int(port)
  trans = Transaction()
  trans.add_input(Transaction.Input(20, b'FFFFFFFF'))
  trans.add_output(Transaction.Output(10, KeyStore.getPublicKey())) # just pay to ourselves for now
  trans.add_input(Transaction.Input(5, b'FFFFFFFF'))
  s = trans.build_struct()
  
  c = P2PClient()
  c.send_message(Message.add)
  c.send_message(Message.NEW_TRANSACTION, s)
  
  import time
  time.sleep(5)
  
  trans = Transaction()
  trans.add_input(Transaction.Input(100, b'FFFFFFFF'))
  trans.add_output(Transaction.Output(55, KeyStore.getPublicKey())) # just pay to ourselves for now
  trans.add_input(Transaction.Input(4, b'FFFFFFFF'))
  s = trans.build_struct()
  c.send_message(Message.NEW_TRANSACTION, s)