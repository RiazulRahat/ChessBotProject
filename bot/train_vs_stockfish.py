"""
Train ChessBotAgent against Stockfish with a depth-based curriculum
plus live Stockfish evaluation blending.

After each game, every position is fed back through SF's analyser. The
centipawn score is normalised to [-1, 1] and blended into the eval table.
This teaches the bot Stockfish's positional understanding directly rather
than relying solely on the noisy game-outcome signal.

Normalisation: sf_value = clamp(cp / 1000, -1, 1)
  0 cp   →  0.0   (equal)
  300 cp →  0.3   (about a minor piece ahead)
  700 cp →  0.7   (large advantage)
  1000+  →  1.0   (winning)

Run with:
    python -m bot.train_vs_stockfish --minutes 40 --sf-max-depth 2
    python -m bot.train_vs_stockfish --minutes 60 --clear-table --material-weight 1.0
"""
import argparse
import collections
import datetime
import time
import chess
import chess.engine

from bot.utils.debug import dprint
from bot.utils.zobrist import zobrist
from bot.chess_bot import ChessBotAgent

# ─── hyper-parameters ────────────────────────────────────────────────────────
STOCKFISH_PATH    = "/opt/homebrew/bin/stockfish"
DEFAULT_GAMES     = 10_000
BOT_DEPTH         = 3
SF_START_DEPTH    = 1
SF_MAX_DEPTH      = 6
PROMOTE_THRESHOLD = 0.55
PROMOTE_WINDOW    = 50

INITIAL_EPS       = 0.10
DECAY_EVERY       = 200
DECAY_FACTOR      = 0.90
LEARNING_RATE     = 0.15
GAMMA             = 0.99
MATERIAL_WEIGHT   = 0.15
USE_QUIESCENCE    = False
QUIESCENCE_DEPTH  = 5
SAVE_INTERVAL     = 200
PRINT_EVERY       = 50

SF_EVAL_DEPTH     = 3     # depth SF uses when analysing positions (separate from game depth)
SF_EVAL_WEIGHT    = 0.20  # alpha: how strongly SF's eval overwrites the table each position

TABLE_PATH        = "bot/evaluation_table_current/eval_table_zobrist_pruned.pkl"
BOOK_PATH         = "book_library/Perfect2023.bin"
# ─────────────────────────────────────────────────────────────────────────────


def play_one(
    bot: ChessBotAgent,
    engine: chess.engine.SimpleEngine,
    bot_is_white: bool,
    sf_limit: chess.engine.Limit,
):
    bot.tt.clear()
    bot.history = [[0] * 64 for _ in range(64)]

    board = chess.Board()
    hist = []

    while not board.is_game_over():
        hist.append((zobrist.hash(board), board.turn == chess.WHITE, board.fen()))
        if (board.turn == chess.WHITE) == bot_is_white:
            mv = bot.choose_move(board)
            if mv is None:
                break
        else:
            mv = engine.play(board, sf_limit).move
        board.push(mv)

    return board.result(), hist


def blend_sf_evals(
    bot: ChessBotAgent,
    engine: chess.engine.SimpleEngine,
    hist: list,
    eval_limit: chess.engine.Limit,
    alpha: float,
):
    """
    For every position in hist, ask SF for its centipawn evaluation and blend
    it into the eval table using:
        new = old + alpha * (sf_value - old)

    SF scores from White's perspective; sf_value is clamped to [-1, 1].
    This runs between games and does not affect move generation.
    """
    for zkey, _white_to_move, fen in hist:
        board = chess.Board(fen)
        try:
            info = engine.analyse(board, eval_limit)
            cp = info["score"].white().score(mate_score=10000)
        except Exception:
            continue
        if cp is None:
            continue
        sf_value = max(-1.0, min(1.0, cp / 1000.0))
        old = bot.evaluation_table.get(zkey, 0.0)
        bot.evaluation_table[zkey] = old + alpha * (sf_value - old)
        bot.zkey_to_fen.setdefault(zkey, fen)


def _win_rate(results: collections.deque, sides: collections.deque) -> float:
    if not results:
        return 0.0
    wins = sum(
        1 for r, biw in zip(results, sides)
        if (r == "1-0" and biw) or (r == "0-1" and not biw)
    )
    return wins / len(results)


def main(
    total_games: int = DEFAULT_GAMES,
    stockfish_path: str = STOCKFISH_PATH,
    bot_depth: int = BOT_DEPTH,
    minutes: float = 0,
    sf_max_depth: int = SF_MAX_DEPTH,
    clear_table: bool = False,
    material_weight: float = MATERIAL_WEIGHT,
    sf_eval_depth: int = SF_EVAL_DEPTH,
    sf_eval_weight: float = SF_EVAL_WEIGHT,
):
    bot = ChessBotAgent(
        exploration_rate=INITIAL_EPS,
        learning_rate=LEARNING_RATE,
        save_interval=SAVE_INTERVAL,
        table_path=TABLE_PATH,
        search_depth=bot_depth,
        use_quiescence=USE_QUIESCENCE,
        quiescence_depth=QUIESCENCE_DEPTH,
        gamma=GAMMA,
        material_weight=material_weight,
        book_bin_path=BOOK_PATH,
    )

    if clear_table:
        bot.evaluation_table = {}
        bot.zkey_to_fen = {}
        bot.zkey_stats = {}
        print("Table cleared — bot relies on material + positional heuristics only.")

    engine = chess.engine.SimpleEngine.popen_uci(stockfish_path)
    sf_depth = SF_START_DEPTH
    sf_game_limit = chess.engine.Limit(depth=sf_depth)
    sf_eval_limit = chess.engine.Limit(depth=sf_eval_depth)

    recent_results = collections.deque(maxlen=PROMOTE_WINDOW)
    recent_sides   = collections.deque(maxlen=PROMOTE_WINDOW)

    bot_wins = bot_losses = draws = 0
    eps = INITIAL_EPS
    g = 0
    deadline = time.time() + minutes * 60 if minutes > 0 else None

    target_str = f"{minutes:.0f} min" if minutes > 0 else f"{total_games} games"
    print(f"Stockfish curriculum training  bot-depth={bot_depth}  target={target_str}")
    print(f"SF game depth: {sf_depth} → {sf_max_depth}  "
          f"(promote at {PROMOTE_THRESHOLD:.0%} over {PROMOTE_WINDOW} games)")
    print(f"SF eval blending: depth={sf_eval_depth}  weight={sf_eval_weight}")
    print(f"material_weight={material_weight}  table={'cleared' if clear_table else 'loaded'}")
    print(f"Table: {TABLE_PATH}\n")

    try:
        for g in range(1, total_games + 1):
            bot_is_white = (g % 2 == 1)
            result, hist = play_one(bot, engine, bot_is_white, sf_game_limit)

            bot_won  = (result == "1-0" and bot_is_white) or \
                       (result == "0-1" and not bot_is_white)
            bot_lost = (result == "0-1" and bot_is_white) or \
                       (result == "1-0" and not bot_is_white)
            if bot_won:
                bot_wins += 1
            elif bot_lost:
                bot_losses += 1
            else:
                draws += 1

            recent_results.append(result)
            recent_sides.append(bot_is_white)

            dprint("game %d  result=%s  plies=%d  sf-depth=%d",
                   g, result, len(hist), sf_depth)

            # TD(0) update from game outcome
            bot.update_evaluation(hist, result)

            # Blend SF's positional evaluation into the table for every position
            blend_sf_evals(bot, engine, hist, sf_eval_limit, sf_eval_weight)

            if g % PRINT_EVERY == 0:
                now  = datetime.datetime.now().strftime("%H:%M:%S")
                wr   = _win_rate(recent_results, recent_sides)
                total = bot_wins + bot_losses + draws
                overall_wr = bot_wins / total if total else 0
                print(f"{now} | game {g:,}  sf-depth={sf_depth}  ε={eps:.3f}")
                print(f"    W–L–D: {bot_wins}–{bot_losses}–{draws}  "
                      f"overall={overall_wr:.1%}  "
                      f"rolling({PROMOTE_WINDOW})={wr:.1%}  "
                      f"table={len(bot.evaluation_table):,}")

            if g % DECAY_EVERY == 0:
                eps *= DECAY_FACTOR
                bot.exploration_rate = eps
                print(f"--- ε decayed → {eps:.4f} at game {g:,} ---")

            if (len(recent_results) == PROMOTE_WINDOW and
                    _win_rate(recent_results, recent_sides) >= PROMOTE_THRESHOLD and
                    sf_depth < sf_max_depth):
                sf_depth += 1
                sf_game_limit = chess.engine.Limit(depth=sf_depth)
                recent_results.clear()
                recent_sides.clear()
                print(f"\n=== PROMOTED: Stockfish depth → {sf_depth} at game {g:,} ===\n")

            if deadline and time.time() >= deadline:
                print(f"\nTime limit reached after {g:,} games.")
                break

    except KeyboardInterrupt:
        print("\nInterrupted — saving …")
    finally:
        engine.quit()
        bot._save_table()
        total = bot_wins + bot_losses + draws
        wr = bot_wins / total if total else 0
        print(f"\nDone.  Table saved to {TABLE_PATH}")
        print(f"Final record  W–L–D: {bot_wins}–{bot_losses}–{draws}  ({wr:.1%} win-rate)")
        print(f"Final SF depth: {sf_depth}")
        print(f"Games completed: {g:,}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Train ChessBotAgent vs Stockfish with curriculum + live eval blending.")
    parser.add_argument("--games",           type=int,   default=DEFAULT_GAMES)
    parser.add_argument("--stockfish-path",  type=str,   default=STOCKFISH_PATH)
    parser.add_argument("--bot-depth",       type=int,   default=BOT_DEPTH)
    parser.add_argument("--sf-max-depth",    type=int,   default=SF_MAX_DEPTH,
                        help="curriculum ceiling for Stockfish game depth")
    parser.add_argument("--minutes",         type=float, default=0)
    parser.add_argument("--clear-table",     action="store_true",
                        help="wipe the eval table before training")
    parser.add_argument("--material-weight", type=float, default=MATERIAL_WEIGHT)
    parser.add_argument("--sf-eval-depth",   type=int,   default=SF_EVAL_DEPTH,
                        help="depth SF uses when analysing positions for eval blending")
    parser.add_argument("--sf-eval-weight",  type=float, default=SF_EVAL_WEIGHT,
                        help="blending alpha: how far each position moves toward SF's eval")
    args = parser.parse_args()
    main(args.games, args.stockfish_path, args.bot_depth, args.minutes,
         args.sf_max_depth, args.clear_table, args.material_weight,
         args.sf_eval_depth, args.sf_eval_weight)
