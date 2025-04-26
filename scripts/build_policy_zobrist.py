import pickle, math, time
import chess
from bot.utils.zobrist import zobrist
from bot.evaluation.positional_heuristics import positional_score

# ─── CONFIG ────────────────────────────────────────────────────────────────
Z_TABLE_PATH  = "bot/evaluation_table_current/eval_table_zobrist_pruned.pkl"
FEN_MAP_PATH  = "bot/evaluation_table_current/fen_map_v1.0.0.pkl"
POLICY_PATH   = "bot/policy_zobrist_v1.0.0.pkl"
# ───────────────────────────────────────────────────────────────────────────

def build_policy(z_table: dict[int, float], fen_map: dict[int, str]) -> dict[int, str]:
    policy = {}
    total  = len(z_table)
    start  = time.time()

    for idx, (key, val) in enumerate(z_table.items(), start=1):
        if key not in fen_map:
            continue
        board = chess.Board(fen_map[key])
        if board.is_game_over():
            continue

        maximise = board.turn == chess.WHITE
        best_val = -math.inf if maximise else +math.inf
        best_mv  = None

        for mv in board.legal_moves:
            board.push(mv)
            child_key = zobrist.hash(board)
            board.pop()
            # lookup or fallback
            score = z_table.get(child_key, positional_score(board))
            if (maximise and score > best_val) or (not maximise and score < best_val):
                best_val, best_mv = score, mv

        if best_mv:
            policy[key] = best_mv.uci()

        # Progress logging
        if idx % 100_000 == 0 or idx == total:
            elapsed = time.time() - start
            eta     = (total-idx)/(idx/elapsed) if idx>0 else float("inf")
            pct     = idx/total*100
            print(f"{idx:,}/{total:,} ({pct:.1f}%)  elapsed {elapsed:.0f}s  ETA ~{eta:.0f}s")

    return policy

def main():
    print("Loading Zobrist table…", end="", flush=True)
    with open(Z_TABLE_PATH, "rb") as f:
        z_table = pickle.load(f)
    print(f" {len(z_table):,} entries.")

    print("Loading fen_map…", end="", flush=True)
    with open(FEN_MAP_PATH, "rb") as f:
        fen_map = pickle.load(f)
    print(f" {len(fen_map):,} entries.")

    print("Building Zobrist→Move policy…")
    policy = build_policy(z_table, fen_map)

    print(f"Saving policy to {POLICY_PATH}…", end="", flush=True)
    with open(POLICY_PATH, "wb") as f:
        pickle.dump(policy, f)
    print(" done.")

if __name__ == "__main__":
    main()