#!/usr/bin/env python3
import pickle

# paths (adjust if needed)
eval_path = "bot/evaluation_table_current/eval_table_zobrist_pruned.pkl"
fen_path  = eval_path.replace(".pkl", "_zkey2fen.pkl")

# load both
with open(eval_path, "rb") as f:
    eval_table = pickle.load(f)
with open(fen_path, "rb") as f:
    fen_map = pickle.load(f)

# keep only keys in eval_table
keep = set(eval_table.keys())
pruned_fen = {k:fen for k,fen in fen_map.items() if k in keep}

print(f"Original FEN entries: {len(fen_map):,}")
print(f"Pruned   FEN entries: {len(pruned_fen):,}")

# overwrite the file
with open(fen_path, "wb") as f:
    pickle.dump(pruned_fen, f)

print("Pruning complete.")
