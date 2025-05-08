"""
Self‑play trainer.  Run with:

    python -m bot.continuous_train --games 1000
or
    PYTHONLOGLEVEL=DEBUG python -m bot.continuous_train --games 20
"""
import argparse, datetime, statistics, random
import chess

from bot.utils.debug import dprint
from bot.utils.zobrist import zobrist
from bot.chess_bot import ChessBotAgent

# ─── hyper‑parameters you may tweak ─────────────────────────────────────
DEFAULT_GAMES     = 2_000
INITIAL_EPS       = 0.05
DECAY_EVERY       = 250
DECAY_FACTOR      = 0.90
LEARNING_RATE     = 0.15
MOB_WEIGHT        = 0.05
POS_WEIGHT        = 0.65
SEARCH_DEPTH      = 3
USE_QUIESCENCE    = True
QUIESCENCE_DEPTH  = 5
SAVE_INTERVAL     = 500
PRINT_EVERY       = 100
TABLE_PATH        = "bot/evaluation_table_current/eval_table_zobrist_pruned.pkl"
# ────────────────────────────────────────────────────────────────────────


def play_one(wbot: ChessBotAgent, bbot: ChessBotAgent):
    """Return (result_str, history_list)."""
    board, hist = chess.Board(), []
    while not board.is_game_over():
        hist.append((zobrist.hash(board), board.turn == chess.WHITE, board.fen()))
        mv = wbot.choose_move(board) if board.turn == chess.WHITE else bbot.choose_move(board)
        board.push(mv)
    return board.result(), hist


def main(total_games: int = DEFAULT_GAMES):
    # instantiate two identical bots
    bot_w = ChessBotAgent(INITIAL_EPS, LEARNING_RATE, MOB_WEIGHT, SAVE_INTERVAL,
                          TABLE_PATH, search_depth=SEARCH_DEPTH,
                          positional_weight=POS_WEIGHT,
                          use_quiescence=USE_QUIESCENCE, quiescence_depth=QUIESCENCE_DEPTH,
                          use_policy=False)
    bot_b = ChessBotAgent(INITIAL_EPS, LEARNING_RATE, MOB_WEIGHT, SAVE_INTERVAL,
                          TABLE_PATH, search_depth=SEARCH_DEPTH,
                          positional_weight=POS_WEIGHT,
                          use_quiescence=USE_QUIESCENCE, quiescence_depth=QUIESCENCE_DEPTH,
                          use_policy=False)

    white_wins = black_wins = draws = 0
    eps = INITIAL_EPS

    try:
        for g in range(1, total_games + 1):
            white_bot, black_bot = (bot_w, bot_b) if g % 2 == 0 else (bot_b, bot_w)
            result, hist = play_one(white_bot, black_bot)
            dprint("--- game %d  result=%s  plies=%d", g, result, len(hist))

            # W‑L‑D accounting
            if result == "1-0":
                white_wins += white_bot is bot_w
                black_wins += white_bot is bot_b
            elif result == "0-1":
                white_wins += black_bot is bot_w
                black_wins += black_bot is bot_b
            else:
                draws += 1

            # learning
            bot_w.update_evaluation(hist, result)
            bot_b.update_evaluation(hist, result)

            # periodic logging
            if g % PRINT_EVERY == 0:
                now = datetime.datetime.now().strftime("%H:%M:%S")
                stdev = statistics.pstdev(bot_w.evaluation_table.values())
                size  = len(bot_w.evaluation_table)
                q_calls = bot_w.quiesce_calls + bot_b.quiesce_calls
                print(f"{now} | {g:,} games  stdev {stdev:.4f}  ε {eps:.3f}")
                print(f"    table entries: {size:,}")
                print(f"    record  W–L–D: {white_wins}–{black_wins}–{draws}, "
                      f"quiesce={q_calls}")
                bot_w.quiesce_calls = bot_b.quiesce_calls = 0
                dprint("ε now %.4f  table=%d", eps, size)

            # ε decay
            if g % DECAY_EVERY == 0:
                eps *= DECAY_FACTOR
                bot_w.exploration_rate = bot_b.exploration_rate = eps
                print(f"--- decayed ε → {eps:.3f} at game {g:,} ---")

    except KeyboardInterrupt:
        print("Interrupted – saving …")
    finally:
        bot_w._save_table()
        print(f"Table saved to {TABLE_PATH}")
        print(f"Final record  W–L–D: {white_wins}–{black_wins}–{draws}")
        print(f"Games completed: {g:,}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--games", type=int, default=DEFAULT_GAMES,
                        help="number of self‑play games to run")
    args = parser.parse_args()
    main(args.games)
