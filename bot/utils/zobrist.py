# Zobrist.py

import os
import pickle
import random
import chess
# =====================================================
# Number of random 64-bit keys:
# 12 piece types (6 white + 6 black) × 64 squares
# + 1 for side to move
# + 16 for castling rights
# + 8 for en-passant file
# =====================================================
NUM_KEYS = 12*64 + 1 + 16 + 8 # 793 keys in total


# Function:    Random Number Generator
def _randomNumberGenerator():
    return random.getrandbits(64)



""" Zobrist Class =========================================================
    # Inputs  :        key_path -> path to new/existing zobrist_keys.pkl
    #                  self.keys -> list of generated keys
    # Methods :        
    #      1.   hash   ->   generate the input board hash (int) - and return
========================================================================"""
class Zobrist:


    # Class Definition =========================================
    def __init__(self, key_path="zobrist_keys.pkl"):
        self.key_path = key_path
        if os.path.exists(key_path):
            with open(key_path, 'rb') as f:
                self.keys = pickle.load(f)
        else:
            # Generating a new zobrist converting table for the board pieces
            self.keys = [_randomNumberGenerator() for _num in range(NUM_KEYS)]
            os.makedirs(os.path.dirname(key_path), exist_ok=True)
            with open(key_path, 'wb') as f:
                pickle.dump(self.keys, f)
    # ===========================================================

    # ============================================================
    # Method :   hash
    # Inputs :   chess.Board -> Board object of chess
    # Output :   INTEGER
    #
    # Generating the current board hash using the Zobrist keys
    # ============================================================
    def hash(self, board: chess.Board) -> int:
        h = 0
      
        # Pieces----------
        for sq in chess.SQUARES:
            p = board.piece_at(sq)  
            if p:   # piece exists
                idx = (p.piece_type - 1) + (0 if p.color else 6)    # p.color -> Boolean
                h ^= self.keys[idx*64 + sq]
        # ----------------

        # Side to move ----
        if board.turn == chess.BLACK:
            h ^= self.keys[12*64]
        # -----------------

        # Castling rights (KQkq) ---
        rights = [(board.has_kingside_castling_rights(chess.WHITE), 0),
                  (board.has_queenside_castling_rights(chess.WHITE), 1),
                  (board.has_kingside_castling_rights(chess.BLACK), 2),
                  (board.has_queenside_castling_rights(chess.BLACK), 3)]
        for flag, i in rights:
            if flag:
                h ^= self.keys[12*64 + 1 + i]
        # --------------------------

        # En-passant file ------
        ep = board.ep_square
        if ep is not None:
            file = ep % 8
            h ^= self.keys[12*64 + 1 + 4 + file]

        return h
        # -----------------------
    # ============================================================

# Shared zobrist object 
zobrist = Zobrist()