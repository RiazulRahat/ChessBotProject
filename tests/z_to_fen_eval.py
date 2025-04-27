import pickle

# adjust these paths as needed
eval_path = "bot/evaluation_table_current/eval_table_zobrist_pruned.pkl"
fen_path  = eval_path.replace(".pkl", "_zkey2fen.pkl")

# load both tables
with open(eval_path, "rb") as f:
    eval_table = pickle.load(f)
with open(fen_path, "rb") as f:
    zkey2fen   = pickle.load(f)

# counts
n_eval = len(eval_table)
n_fen  = len(zkey2fen)
n_missing = n_eval - n_fen

# coverage
coverage = n_fen / n_eval * 100 if n_eval else 0

print(f"Total eval entries:       {n_eval:,}")
print(f"Total Z-key→FEN mappings: {n_fen:,}")
print(f"Unmapped eval keys:       {n_missing:,}")
print(f"Mapping coverage:         {coverage:.2f}%")

eval_table = pickle.load(open("bot/evaluation_table_current/eval_table_zobrist_pruned.pkl","rb"))
fen_map   = pickle.load(open("bot/evaluation_table_current/eval_table_zobrist_pruned_zkey2fen.pkl","rb"))

eval_keys = set(eval_table)
fen_keys  = set(fen_map)

only_in_eval = eval_keys - fen_keys
only_in_fen  = fen_keys - eval_keys

print("Keys only in eval table: ", len(only_in_eval))
print("Keys only in FEN map:    ", len(only_in_fen))