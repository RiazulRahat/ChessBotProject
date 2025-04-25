# evaluate_elo.py

import argparse
import shutil
import sys
import math
import statistics
import chess
import chess.engine
import chess.pgn
from bot.chess_bot import ChessBotAgent

# ─── Configuration ────────────────────────────────────────────────────────
# automatically find stockfish in your PATH
STOCKFISH_PATH = shutil.which("stockfish")
if STOCKFISH_PATH is None:
    sys.exit(
        "ERROR: `stockfish` not found on your PATH.\n"
        "Install it (e.g. `brew install stockfish`) or adjust STOCKFISH_PATH."
    )
STOCKFISH_REF_ELO = 100     # assumed Elo of the Stockfish instance
TIME_PER_MOVE    = 0.200     # seconds per move
NUM_GAMES        = 20        # total games (half as White, half as Black)
POS_WEIGHT       = 0.8
SEARCH_DEPTH     = 3         # your bot’s search depth for testing
EPSILON          = 0.0       # no randomness during test
TABLE_PATH       = "bot/eval_table_zobrist_pruned.pkl"
# ────────────────────────────────────────────────────────────────────────

def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--positional-weight", type=float, default=1.0,
                   help="Multiplier for positional_score")
    p.add_argument("--games",            type=int,   default=NUM_GAMES,
                   help="Number of games to play")
    return p.parse_args()

def elo_from_score(score_fraction, ref_elo):
    S = min(max(score_fraction, 0.01), 0.99)
    return ref_elo + 400 * math.log10(S / (1 - S))

def play_match(bot, engine, bot_plays_white: bool):
    board       = chess.Board()
    history_san = []               # <-- record moves in SAN

    while not board.is_game_over():
        if board.turn == (chess.WHITE if bot_plays_white else chess.BLACK):
            mv = bot.choose_move(board)
        else:
            mv = engine.play(board, chess.engine.Limit(time=TIME_PER_MOVE)).move

        # record the human-readable move
        history_san.append(board.san(mv))
        board.push(mv)

    result = board.result()
    # map result to score fraction
    if   result == "1-0": score = 1.0 if bot_plays_white else 0.0
    elif result == "0-1": score = 0.0 if bot_plays_white else 1.0
    else:                  score = 0.5

    return score, history_san, result

def main():
    args = parse_args()
    # override globals if passed
    global NUM_GAMES
    NUM_GAMES = args.games

    # launch stockfish
    engine = chess.engine.SimpleEngine.popen_uci(STOCKFISH_PATH)
    # limit strength and set Elo
    engine.configure({ "UCI_LimitStrength": True, "Skill Level":       0})

    # init your bot (no learning, no randomness)
    bot = ChessBotAgent(
        exploration_rate=EPSILON,
        learning_rate=0.0,
        save_interval=NUM_GAMES,
        table_path=TABLE_PATH,
        search_depth=SEARCH_DEPTH,
        positional_weight=args.positional_weight,
        use_quiescence=True
        )

    print(f"→ Testing {NUM_GAMES} games vs Stockfish (Elo {STOCKFISH_REF_ELO})…")
    scores = []
    half = NUM_GAMES // 2

    # (re)initialize/clear PGN file
    open("vs_stockfish.pgn", "w").close()

    for i in range(1, NUM_GAMES + 1):
        white = (i <= half)
        s, history_san, result = play_match(bot, engine, white)
        scores.append(s)

        # --- write PGN for this game ---
        game         = chess.pgn.Game()
        game.headers["White"] = "Bot"
        game.headers["Black"] = "Stockfish"
        game.headers["Result"] = result
        node = game
        board = chess.Board()
        for san in history_san:
            node = node.add_variation(board.parse_san(san))
            board.push_san(san)

        with open("vs_stockfish.pgn", "a") as pgn_file:
            print(game, file=pgn_file, end="\n\n")
        
        # console output
        print(f" Game {i:2d}/{NUM_GAMES} — {'White' if white else 'Black'} → "
              f"{'WIN' if s==1 else 'DRAW' if s==0.5 else 'LOSS'}")

    engine.quit()

    total  = sum(scores)
    frac   = total / NUM_GAMES
    est_elo = elo_from_score(frac, STOCKFISH_REF_ELO)

    print("\n=== Summary ===")
    print(f"Score: {total:.1f}/{NUM_GAMES} ({frac*100:.1f}%)")
    print(f"Estimated Elo: {est_elo:.0f} (vs {STOCKFISH_REF_ELO})")

if __name__ == "__main__":
    main()
