#build_policy_from_zobrist.py
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pickle
import chess
import math
import time
from bot.utils.zobrist import zobrist

# Paths
#  - FEN backup (your original eval_table.pkl before conversion)
#  - ZOBRIST table (your live table)
FEN_BACKUP_PATH      = "bot/evaluation_table_files/eval_table_backup2.pkl"
ZOBRIST_TABLE_PATH   = "bot/evaluation_table_current/eval_table_zobrist_pruned.pkl"
POLICY_PATH          = "bot/policy_book.pkl"

def material_score(board: chess.Board) -> float:
    vals = {
        chess.PAWN:1, chess.KNIGHT:3, chess.BISHOP:3,
        chess.ROOK:5, chess.QUEEN:9
    }
    return sum(
        v * (len(board.pieces(p, chess.WHITE)) -
             len(board.pieces(p, chess.BLACK)))
        for p, v in vals.items()
    )

def main():
    print("Loading FEN‐keyed backup…", end="", flush=True)
    with open(FEN_BACKUP_PATH, "rb") as f:
        fen_table = pickle.load(f)
    print(f" got {len(fen_table):,} entries.")

    print("Loading Zobrist‐keyed live table…", end="", flush=True)
    with open(ZOBRIST_TABLE_PATH, "rb") as f:
        z_table = pickle.load(f)
    print(f" got {len(z_table):,} entries.")

    # Merge: for each FEN in the fen_table, override with any new strength from z_table
    print("Merging…", end="", flush=True)
    merged = {}
    for fen, old_val in fen_table.items():
        board = chess.Board(fen)
        key   = zobrist.hash(board)
        val   = z_table.get(key, old_val)
        merged[fen] = val
    print(f" merged into {len(merged):,} entries.")

    # Build policy
    print("Building policy…", end="", flush=True)
    policy = {}
    total = len(merged)
    start = time.time()
    for idx, fen in enumerate(merged, start=1):
        if idx % 100_000 == 0 or idx == total:
            elapsed = time.time() - start
            rate = idx / elapsed if elapsed>0 else 0
            eta  = (total-idx) / rate if rate>0 else float("inf")
            pct  = idx/total*100
            print(f"\n  {idx:,}/{total:,} ({pct:.1f}%)  "
                  f"{elapsed:.0f}s elapsed, ~{eta:.0f}s to go", end="", flush=True)

        board = chess.Board(fen)
        legal = list(board.legal_moves)
        if not legal:
            continue

        maximise = board.turn == chess.WHITE
        best_val = -math.inf if maximise else +math.inf
        best_mv  = None

        for mv in legal:
            board.push(mv)
            child_fen = board.fen()
            # get merged value for that position
            v = merged.get(child_fen, material_score(board))
            board.pop()
            if (maximise and v > best_val) or (not maximise and v < best_val):
                best_val, best_mv = v, mv

        if best_mv:
            policy[fen] = best_mv.uci()

    with open(POLICY_PATH, "wb") as f:
        pickle.dump(policy, f)

    total_time = time.time() - start
    print(f"\nBuilt policy for {len(policy):,} positions in {total_time:.0f}s → {POLICY_PATH}")

if __name__ == "__main__":
    main()
