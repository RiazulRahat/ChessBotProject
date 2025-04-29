#!/usr/bin/env python3
import pickle
import chess

# ─── CONFIGURE YOUR PATHS HERE ───────────────────────────────────────────────
EVAL_PATH     = "bot/evaluation_table_current/eval_table_zobrist_pruned.pkl"
FEN_MAP_PATH  = "bot/evaluation_table_current/eval_table_zobrist_pruned_zkey2fen.pkl"
STATS_PATH    = "bot/evaluation_table_current/eval_table_zobrist_pruned_stats.pkl"
POLICY_OUT    = "bot/policy_table_v1.pkl"
# ──────────────────────────────────────────────────────────────────────────────

def main():
    # 1) load your tables
    with open(EVAL_PATH,   "rb") as f:
        eval_table   = pickle.load(f)
    with open(FEN_MAP_PATH,"rb") as f:
        zkey_to_fen  = pickle.load(f)
    with open(STATS_PATH,  "rb") as f:
        zkey_stats   = pickle.load(f)

    print(f"Loaded {len(eval_table)} eval entries, "
          f"{len(zkey_to_fen)} mapped FENs, "
          f"{len(zkey_stats)} stats entries.")

    # 2) invert to go from FEN → zkey
    fen_to_zkey = {fen: zkey for zkey, fen in zkey_to_fen.items()}

    policy = {}
    # 3) for each known position, gather child‐visit counts
    for zkey, fen in zkey_to_fen.items():
        board = chess.Board(fen)
        move_counts = {}

        for move in board.legal_moves:
            board.push(move)
            child_fen = board.fen()
            board.pop()

            # look up visits for that child position (0 if unseen)
            child_z = fen_to_zkey.get(child_fen)
            visits  = zkey_stats.get(child_z, {}).get("visits", 0)
            move_counts[move.uci()] = visits

        # 4) normalize into a probability distribution
        total = sum(move_counts.values())
        if total > 0:
            policy[zkey] = {uci: cnt/total for uci, cnt in move_counts.items()}
        else:
            # fallback to uniform if no data
            n = len(move_counts)
            policy[zkey] = {uci: 1/n for uci in move_counts} if n else {}

    # 5) save out
    with open(POLICY_OUT, "wb") as f:
        pickle.dump(policy, f)

    print(f"Built policy with {len(policy)} entries; saved to {POLICY_OUT}")

if __name__ == "__main__":
    main()
