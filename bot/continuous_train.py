"""
Self-play trainer.  Edit TOTAL_GAMES or run Ctrl-C to stop.
"""

import chess, datetime, statistics, sys
from chess_bot import ChessBotAgent

# ─── hyper-parameters ──────────────────────────────────────────────────
TOTAL_GAMES   = 100_000
INITIAL_EPS   = 0.2
DECAY_EVERY   = 10_000
DECAY_FACTOR  = 0.9
LEARNING_RATE = 0.60
SEARCH_DEPTH     = 2           # shallow for speed – depth-1 ≈ 800–1 000 gpm
SAVE_INTERVAL = 100
PRINT_EVERY   = 500
TABLE_PATH    = "bot/eval_table.pkl"
# ───────────────────────────────────────────────────────────────────────

def play_one(bot_w, bot_b):
    board, hist = chess.Board(), []
    while not board.is_game_over():
        hist.append((board.fen(), board.turn))
        mv = bot_w.choose_move(board) if board.turn else bot_b.choose_move(board)
        board.push(mv)
    return board.result(), hist

def main():
    # instantiate *before* try so we can save in finally
    bot_w = ChessBotAgent(
        exploration_rate=INITIAL_EPS,
        learning_rate=LEARNING_RATE,
        save_interval=SAVE_INTERVAL,
        table_path=TABLE_PATH,
        search_depth=SEARCH_DEPTH
    )
    bot_b = ChessBotAgent(
        exploration_rate=INITIAL_EPS,
        learning_rate=LEARNING_RATE,
        save_interval=SAVE_INTERVAL,
        table_path=TABLE_PATH,
        search_depth=SEARCH_DEPTH
    )

    white_wins = black_wins = draws = 0
    eps = INITIAL_EPS

    try:
        for g in range(1, TOTAL_GAMES + 1):
            result, history = play_one(bot_w, bot_b)

            # update W–L–D counters
            if result == "1-0":
                white_wins += 1
            elif result == "0-1":
                black_wins += 1
            else:
                draws += 1

            # run learning updates
            bot_w.update_evaluation(history, result)
            bot_b.update_evaluation(history, result)

            # logging
            if g % PRINT_EVERY == 0:
                sd   = statistics.pstdev(bot_w.evaluation_table.values())
                now  = datetime.datetime.now().strftime("%H:%M:%S")
                size = len(bot_w.evaluation_table)
                print(f"{now} | {g:,} games  stdev {sd:.4f}  ε {eps:.3f}")
                print(f"    table entries: {size:,}")
                print(f"    record  W–L–D: {white_wins:,}–{black_wins:,}–{draws:,}")

            # decay ε
            if g % DECAY_EVERY == 0:
                eps = eps * DECAY_FACTOR
                bot_w.exploration_rate = bot_b.exploration_rate = eps
                print(f"--- decayed ε → {eps:.3f} at game {g:,} ---")

    except KeyboardInterrupt:
        print("\nInterrupted by user — saving table…")

    finally:
        # always save on normal exit or Ctrl-C
        bot_w._save_table()
        print("Table saved to", TABLE_PATH)
        print(f"Final record  W–L–D: {white_wins:,}–{black_wins:,}–{draws:,}")
        if 'g' in locals():
            print(f"Games completed: {g:,}")

if __name__ == "__main__":
    main()