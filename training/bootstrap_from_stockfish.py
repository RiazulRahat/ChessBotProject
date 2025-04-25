#!/usr/bin/env python3
import shutil, sys, pickle
import chess, chess.engine, chess.pgn

# ─── Config ─────────────────────────────────────────────────────────────
STOCKFISH_PATH    = shutil.which("stockfish") or sys.exit("stockfish not found")
TABLE_PATH        = "bot/eval_table.pkl"
PGN_PATH          = "vs_stockfish.pgn"
SF_ANALYZE_DEPTH  = 12       # Stockfish search depth for annotations
ALPHA             = 0.5      # how strongly to pull your table toward SF values
# ────────────────────────────────────────────────────────────────────────

def load_games(path):
    with open(path) as f:
        while True:
            game = chess.pgn.read_game(f)
            if game is None:
                return
            yield game

def analyse_game(game, engine):
    """Return dict of {fen_before_move: sf_value} for every ply."""
    oracle = {}
    board = game.board()
    for node in game.mainline():
        fen = board.fen()
        move = node.move
        board.push(move)

        info = engine.analyse(board, chess.engine.Limit(depth=SF_ANALYZE_DEPTH))
        score = info["score"].white()

        # centipawn → normalized [-1.0, +1.0], or ±1.0 on mate
        cp = score.score(mate_score=100000)
        if cp is None:
            sf_val =  1.0 if score.mate() > 0 else -1.0
        else:
            sf_val = max(min(cp/100, 1.0), -1.0)

        oracle[fen] = sf_val
    return oracle

def main():
    # launch SF
    engine = chess.engine.SimpleEngine.popen_uci(STOCKFISH_PATH)

    # build oracle table
    oracle = {}
    for game in load_games(PGN_PATH):
        oracle.update(analyse_game(game, engine))
    engine.quit()
    print(f"Collected {len(oracle):,} positions from {PGN_PATH}")

    # load your existing eval table
    try:
        with open(TABLE_PATH, "rb") as f:
            table = pickle.load(f)
    except FileNotFoundError:
        table = {}

    # merge: V_new = V_old + α*(V_SF - V_old)
    for fen, sf_val in oracle.items():
        old = table.get(fen, sf_val)
        table[fen] = old + ALPHA * (sf_val - old)

    # save back
    with open(TABLE_PATH, "wb") as f:
        pickle.dump(table, f)
    print(f"Bootstrapped {len(oracle):,} entries → {TABLE_PATH}")

if __name__ == "__main__":
    main()