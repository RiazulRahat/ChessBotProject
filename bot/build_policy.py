### This is the old way for building policy on FEN tables ###

# bot/build_policy.py
import os
import math
import pickle
import time
import chess

# where your eval_table lives
TABLE_PATH  = os.path.join(os.path.dirname(__file__), "bot/evaluation_table_current/eval_table_zobrist_pruned.pkl")
# output policy book here
POLICY_PATH = os.path.join(os.path.dirname(__file__), "bot/policy_book.pkl")

def material_score(board: chess.Board) -> float:
    vals = {chess.PAWN:1, chess.KNIGHT:3, chess.BISHOP:3,
            chess.ROOK:5, chess.QUEEN:9}
    return sum(
        v*(len(board.pieces(p, chess.WHITE)) - len(board.pieces(p, chess.BLACK)))
        for p,v in vals.items()
    )

def build_policy(report_every=100_000):
    # 1) load your learned values
    print("Loading eval_table…", end="", flush=True)
    with open(TABLE_PATH, "rb") as f:
        V: dict = pickle.load(f)
    total = len(V)
    print(f" done ({total:,} entries).")

    policy = {}
    start = time.time()
    for idx, fen in enumerate(V, start=1):
        # periodic progress
        if idx % report_every == 0 or idx == total:
            elapsed = time.time() - start
            pct = idx / total * 100
            rate = idx / elapsed if elapsed>0 else 0
            eta  = (total-idx) / rate if rate>0 else float('inf')
            print(f"  → {idx:,}/{total:,} ({pct:.1f}%)  "
                  f"{elapsed:.0f}s elapsed, ~{eta:.0f}s to go")

        board = chess.Board(fen)
        legal = list(board.legal_moves)
        if not legal:
            continue

        maximise = board.turn == chess.WHITE
        best_val = -math.inf if maximise else +math.inf
        best_mv  = None

        for mv in legal:
            board.push(mv)
            val = V.get(board.fen(), material_score(board))
            board.pop()
            if (maximise and val > best_val) or (not maximise and val < best_val):
                best_val, best_mv = val, mv

        if best_mv:
            policy[fen] = best_mv.uci()

    # 2) save it
    with open(POLICY_PATH, "wb") as f:
        pickle.dump(policy, f)

    total_time = time.time() - start
    print(f"\nBuilt policy for {len(policy):,} positions in {total_time:.0f}s → {POLICY_PATH}")

if __name__ == "__main__":
    build_policy()
