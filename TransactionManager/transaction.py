from Crypto.Hash import SHA256
from Crypto.Signature import PKCS1_v1_5
from Crypto.PublicKey import RSA
from Crypto import Random
import struct, time

from keystore import *
from P2P.client_manager import *

class Transaction:
  ''' Base "regular" transaction '''
  nVersion = 1
  
  def __init__(self):
    print('Creating a regular transaction')
    self.input = []
    self.output = []
    self.hash = None

  def build(self):
    ''' build a transaction
      this will eventually be encoded in binary format
    '''
    #print(self.payee, self.input, self.output)
    print('Transaction:')
    #print('nVersion: ', Transaction.nVersion)
    print('#vin: ', len(self.input))
    print('vin[]: ', self.input)
    print('#vout: ', len(self.output))
    print('vout[]: ', self.output)
    
  def add_input(self, inp):
    self.input.append(inp)
    return self
    
  def add_output(self, output):
    """ Adds an output to this transaction
    
    Args:
      output: an Transaction.Output object that will be added to this transaction
      
    Returns:
      Self, for use as a factory type builder.
    """
    self.output.append(output)
    from db import DB
    db = DB()
    db.insertUnspentOutput(output)
    return self
    
  def get_outputs(self):
    return self.output
    
  def broadcast(self):
    """ Broadcast this transaction to peers
    
    Broadcast this transaction in json format to the peer network
    """
    p2pclient = P2PClientManager.getClient()
    p2pclient.broadcast_transaction(self.build_struct())
    
  def hash_transaction(self):
    """ Hashes the transaction in raw format """
    self.hash = SHA256.new()
    self.hash.update(self.build_struct())
    
  def get_hash(self):
    """ Retrieves this transaction's hash
    
    Returns:
      This transaction's hash as a hex string
    """
    if not self.hash:
      self.hash_transaction()
    return self.hash.hexdigest()
    
  def build_struct(self):
    
    buffer = bytearray()
    buffer.extend(struct.pack('B', len(self.input)))
    self.pack_inputs(buffer)
    buffer.extend(struct.pack('B', len(self.output)))
    self.pack_outputs(buffer)
    return buffer
    
  def pack_inputs(self, buf):
    for inp in self.input:
      inp.pack(buf)
    return buf
    
  def pack_outputs(self, buf):
    for o in self.output:
      o.pack(buf)
    return buf
    
  def unpack(self, buf):
    """ unpacks a Transaction from a buffer of bytes
    
    """
    num_in = struct.unpack_from('B', buf)[0]
    offset = 1
    self.input = []
    for i in range(num_in):
      self.input.append(Transaction.Input.unpack(buf, offset))
      offset += 66
    ### TODO: Unpack outputs ###
    #print(self.build())
    
  def get_prev_transaction(self):
    f = open('coinbase_transaction.dat', 'rb')
    buf = f.read()
    self.unpack(buf)
    
  def __repr__(self):
    return 'Transaction:' +\
    '\n#vin: ' + str(len(self.input)) +\
    '\nvin[]: ' + str(self.input) +\
    '\n#vout: ' + str(len(self.output)) +\
    '\nvout[]: ' + str(self.output)
    
  # inner class representing inputs/outputs to a transaction
  class Input:
    """ defines an input object in a transaction
    
    Attributes:
      value: the bitcoin value of this input in a transaction
      signature: the digital signature of the entity spending bitcoins
      n: the nth input in a transaction
    """
    
    @staticmethod
    def unpack(buf, offset):
      value = struct.unpack_from('B', buf, offset)[0]
      offset += 1
      prev = buf[offset:offset+32]
      offset += 32
      n = struct.unpack_from('I', buf, offset)[0]
      offset += 1
      signature = buf[offset:offset+32]
      i = Transaction.Input(value, prev, n)
      i.signature = signature
      i.n = n
      return i
    
    def __init__(self, value, prev, n):
      
      ### TODO: prev needs to eb the hash of the previous transaction
      
      self.value = value
      self.prev = prev
      key = KeyStore.getPrivateKey()
      # sign the input
      message = SHA256.new(str.encode('signature'))
      signer = PKCS1_v1_5.new(key)
      self.signature = signer.sign(message)

      self.n = n
      
      print('input #', self.n)
      
    def __repr__(self):
      return str(self.value) + ', ' + str(self.hash_sig())
      
    def hash_sig(self, hex=True):
      hash = SHA256.new()
      hash.update(self.signature)
      if hex:
        return hash.hexdigest()
      else:
        return hash.digest()
    
    def hash_prev(self, hex=True):
      hash = SHA256.new()
      hash.update(self.signature)
      if hex:
        return hash.hexdigest()
      else:
        return hash.digest()
      
    def pack(self, buf):
      print('buf length: ', len(buf))
      buf.extend(struct.pack('B', self.value))
      buf.extend(self.hash_prev(hex=False))
      buf.extend(struct.pack('I', self.n))
      buf.extend(self.hash_sig(hex=False))
      print('buf length: ', len(buf))
      return buf
      
  class Output:
    """ defines an output object in a transaction
    
    Attributes:
      value: the bitcoin value of this output to be transfer to another user
      pubKey: the public key of the recipient of the bitcoins
      n: the nth output in a transaction
    """
    
    _n = 0   # the output count
    
    def __init__(self, value, pubKey):
      self.value = value
      self.pubKey = pubKey
      self.timestamp = int(time.time())  # not sure if this is needed, but this will make each hash unique
      Transaction.Output._n += 1
      self.n = Transaction.Output._n
      
    def __repr__(self):
      return str(self.value) + ', ' + str(self.pubKey.exportKey())
        
    def hash_key(self, hex=True):
      hash = SHA256.new()
      hash.update(self.pubKey.exportKey())
      if hex:
        return hash.hexdigest()
      else:
        return hash.digest()
        
    def hash_output(self):
      bytes = self.pack(bytearray())
      hash = SHA256.new()
      hash.update(bytes)
      return hash.hexdigest()
        
    def pack(self, buf):
      buf.extend(struct.pack('I', self.value))
      buf.extend(struct.pack('I', self.timestamp))
      buf.extend(self.pubKey.exportKey())
      return buf
      
    @staticmethod
    def unpack(buf):
      offset = 0
      value = struct.unpack_from('I', buf, offset)[0]
      offset += 4
      offset += 4 # ignore timestamp
      pubKey = RSA.importKey(buf[offset:offset+512])
      i = Transaction.Output(value, pubKey)
      return i
      
if __name__ == '__main__':
  import sys
  #port = sys.argv[1]
  #P2PClient.CLIENT_PORT = int(port)
  #p2pclient = P2PClientManager.getClient()
  c = CoinBase()
  t = Transaction()
  db = DB()
  prev = db.getUnspentOutput(100)
  t.add_input(Transaction.Input(100, prev, 0))
  t.add_output(Transaction.Output(20, KeyStore.getPublicKey()))
  #t.build()
  #t.broadcast()
  t2 = Transaction()
  t2.get_prev_transaction()
  print(t2)