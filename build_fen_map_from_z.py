#!/usr/bin/env python3
import pickle, time, random
import chess
from bot.utils.zobrist import zobrist
from bot.evaluation.positional_heuristics import positional_score

Z_TABLE_BACKUP = "backups/eval_table_zobrist_pruned.pkl"
FEN_MAP_OUT    = "backups/fen_map_partial.pkl"
MAX_GAMES      = 20_000
SAVE_EVERY     = 100
EPSILON        = 0.02

def select_move_depth1(board, z_table):
    moves = list(board.legal_moves)
    if not moves: return None
    if random.random() < EPSILON:
        return random.choice(moves)
    maximise = board.turn == chess.WHITE
    best_val = -float("inf") if maximise else +float("inf")
    best_mv  = None
    for mv in moves:
        board.push(mv)
        key = zobrist.hash(board)
        val = z_table.get(key, positional_score(board))
        board.pop()
        if (maximise and val > best_val) or (not maximise and val < best_val):
            best_val, best_mv = val, mv
    return best_mv

def main():
    with open(Z_TABLE_BACKUP,"rb") as f:
        z_table = pickle.load(f)
    needed = set(z_table)
    try:
        fen_map = pickle.load(open(FEN_MAP_OUT,"rb"))
    except FileNotFoundError:
        fen_map = {}

    start = time.time()
    print(f"Starting mapping {MAX_GAMES:,} games…")
    for g in range(1, MAX_GAMES+1):
        board = chess.Board()

        while not board.is_game_over():
            key = zobrist.hash(board)
            if key in needed and key not in fen_map:
                fen_map[key] = board.fen()

            mv = random.choice(list(board.legal_moves))
            if mv is None: break
            board.push(mv)

        # final position
        key = zobrist.hash(board)
        if key in needed and key not in fen_map:
            fen_map[key] = board.fen()

        if g % SAVE_EVERY == 0 or g == MAX_GAMES:
            elapsed = time.time() - start
            print(f"Games {g}/{MAX_GAMES} – mapped {len(fen_map)}/{len(needed)} FENs – {elapsed:.0f}s")
            with open(FEN_MAP_OUT,"wb") as f:
                pickle.dump(fen_map, f)

        if len(fen_map) >= len(needed):
            print("All keys covered! Stopping early.")
            break

    print(f"Done: mapped {len(fen_map)} of {len(needed)} keys.")
    with open(FEN_MAP_OUT,"wb") as f:
        pickle.dump(fen_map, f)

if __name__=="__main__":
    main()
