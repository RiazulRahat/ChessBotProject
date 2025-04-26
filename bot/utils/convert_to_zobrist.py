import os
import pickle
import shutil
import chess
from bot.utils.zobrist import zobrist

# Paths
OLD_TABLE = "bot/evaluation_table_files/eval_table_backup2.pkl"
BACKUP    = "bot/eval_table_backup.pkl"
NEW_TABLE = "bot/evaluation_table_current/eval_table_zobrist_pruned.pkl"

# 1) Backup old table
shutil.copy(OLD_TABLE, BACKUP)
print(f"Backed up old table to {BACKUP}")

# 2) Load FEN-based table
with open(OLD_TABLE, 'rb') as f:
    fen_table = pickle.load(f)

# 3) Build new Zobrist table
zobrist_table = {}
for fen, val in fen_table.items():
    board = chess.Board(fen)
    key = zobrist.hash(board)
    zobrist_table[key] = val

# 4) Save new table
with open(NEW_TABLE, 'wb') as f:
    pickle.dump(zobrist_table, f)
print(f"Saved Zobrist-keyed table with {len(zobrist_table)} entries to {NEW_TABLE}")