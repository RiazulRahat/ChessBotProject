import os
import pickle
import random
import chess

# Number of random 64-bit keys:
# 12 piece types (6 white + 6 black) × 64 squares
# + 1 for side to move
# + 16 for castling rights
# + 8 for en-passant file
NUM_KEYS = 12*64 + 1 + 16 + 8

def _random_64():
    return random.getrandbits(64)

class Zobrist:
    def __init__(self, key_path="bot/zobrist_keys.pkl"):
        self.key_path = key_path
        if os.path.exists(key_path):
            with open(key_path, 'rb') as f:
                self.keys = pickle.load(f)
        else:
            self.keys = [_random_64() for _ in range(NUM_KEYS)]
            os.makedirs(os.path.dirname(key_path), exist_ok=True)
            with open(key_path, 'wb') as f:
                pickle.dump(self.keys, f)

    def hash(self, board: chess.Board) -> int:
        h = 0
      
        # Pieces
        for sq in chess.SQUARES:
            p = board.piece_at(sq)
            if p:
                idx = (p.piece_type - 1) + (0 if p.color else 6)
                h ^= self.keys[idx*64 + sq]

        # Side to move
        if board.turn == chess.BLACK:
            h ^= self.keys[12*64]

        # Castling rights (KQkq)
        rights = [(board.has_kingside_castling_rights(chess.WHITE), 0),
                  (board.has_queenside_castling_rights(chess.WHITE), 1),
                  (board.has_kingside_castling_rights(chess.BLACK), 2),
                  (board.has_queenside_castling_rights(chess.BLACK), 3)]
        for flag, i in rights:
            if flag:
                h ^= self.keys[12*64 + 1 + i]

        # En-passant file
        ep = board.ep_square
        if ep is not None:
            file = ep % 8
            h ^= self.keys[12*64 + 1 + 4 + file]

        return h

# Singleton instance
zobrist = Zobrist()