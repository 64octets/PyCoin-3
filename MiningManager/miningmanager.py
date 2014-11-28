#!/usr/bin/env python
import logging
from globals import LOG_LEVEL
from P2P.messages import Message
from BlockManager.block import Block
from TransactionManager.coinbase import CoinBase
from P2P.client_manager import P2PClientManager
import copy, threading

log = logging.getLogger(__name__)
log.setLevel(LOG_LEVEL)

from Crypto.Hash import SHA256
	
class Miner:
  
  INVALID = -1
  
  def __init__(self):
    self.hashnum = SHA256.new()
    self.transactions = []
    self.start_over = False
    self.b = Block(bytearray(32))
    self.client = P2PClientManager.getClient()
    self.client.subscribe(Message.NEW_BLOCK, self.handle_new_block)
    self.client.subscribe(Message.NEW_TRANSACTION, self.handle_new_transaction)
    self.mining_thread = None

  def handle_new_transaction(self, trans):
    self.transactions.append(trans)
    log.info('Received new transaction')
    if len(self.transactions) > 2:
      self.mining_thread = threading.Thread(target=self.solve_on_thread)
      self.mining_thread.start()
        
  def solve_on_thread(self):
    result = self.solve_proof_of_work()
    if result:
      log.info('Block solution found!, %d', self.b.nonce)
      c = CoinBase()
      self.b.transactions.append(c)
      self.client.broadcast_block(self.b.pack())
      
  def handle_new_block(self, block):
    self.start_over = True

  def solve_proof_of_work(self):
    log.info('Mining started...')
    hash = SHA256.new()
    
    #self.b.computeMerkleRoot()
    self.b.transactions = copy.copy(self.transactions)
    # create an array of target-length bytes
    target = bytes(self.b.target)
    hash.update(self.b.pack())
    digest = hash.digest()
    while digest[:self.b.target] != target:
      hash = SHA256.new()
      # update the nonce
      self.b.nonce += 1

      hash.update(self.b.pack())
      digest = hash.digest()
      #print(digest[:self.b.target], target)
      if self.start_over:
        return False
    return True

if __name__ == '__main__':
	m = Miner()
