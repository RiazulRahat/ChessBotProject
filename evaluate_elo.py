# evaluate_elo.py

import shutil
import sys
import math
import statistics
import chess
import chess.engine
from bot.chess_bot import ChessBotAgent

# ─── Configuration ────────────────────────────────────────────────────────
# automatically find stockfish in your PATH
STOCKFISH_PATH = shutil.which("stockfish")
if STOCKFISH_PATH is None:
    sys.exit(
        "ERROR: `stockfish` not found on your PATH.\n"
        "Install it (e.g. `brew install stockfish`) or adjust STOCKFISH_PATH."
    )
STOCKFISH_REF_ELO = 600     # assumed Elo of the Stockfish instance
TIME_PER_MOVE    = 0.100     # seconds per move
NUM_GAMES        = 50        # total games (half as White, half as Black)
SEARCH_DEPTH     = 3         # your bot’s search depth for testing
EPSILON          = 0.1       # no randomness during test
TABLE_PATH       = "bot/eval_table.pkl"
# ────────────────────────────────────────────────────────────────────────

def elo_from_score(score_fraction, ref_elo):
    """Convert a score fraction S into an Elo vs. ref_elo."""
    if score_fraction <= 0.0:
        return ref_elo - 400
    if score_fraction >= 1.0:
        return ref_elo + 400
    return ref_elo + 400 * math.log10(score_fraction / (1 - score_fraction))

def play_match(bot, engine, bot_plays_white: bool):
    board = chess.Board()
    while not board.is_game_over():
        if board.turn == (chess.WHITE if bot_plays_white else chess.BLACK):
            mv = bot.choose_move(board)
        else:
            mv = engine.play(board, chess.engine.Limit(depth=1)).move
        board.push(mv)

    result = board.result()
    if result == "1-0":
        return 1.0 if bot_plays_white else 0.0
    if result == "0-1":
        return 0.0 if bot_plays_white else 1.0
    return 0.5

def main():
    # launch stockfish
    engine = chess.engine.SimpleEngine.popen_uci(STOCKFISH_PATH)

    # init your bot (no learning, no randomness)
    bot = ChessBotAgent(
        exploration_rate=EPSILON,
        learning_rate=0.3,
        save_interval=NUM_GAMES,
        table_path=TABLE_PATH,
        search_depth=SEARCH_DEPTH
    )

    print(f"→ Testing {NUM_GAMES} games vs Stockfish (Elo {STOCKFISH_REF_ELO})…")
    scores = []
    half = NUM_GAMES // 2

    for i in range(1, NUM_GAMES + 1):
        white = (i <= half)
        s = play_match(bot, engine, white)
        scores.append(s)
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
