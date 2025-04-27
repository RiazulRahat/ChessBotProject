"""
Self-play trainer.  Edit TOTAL_GAMES or run Ctrl-C to stop.
"""

import chess, datetime, statistics, sys
from bot.utils.zobrist import zobrist
from bot.chess_bot import ChessBotAgent

# ─── hyper-parameters ──────────────────────────────────────────────────
TOTAL_GAMES   = 50_000
INITIAL_EPS   = 0.20
DECAY_EVERY   = 1000
DECAY_FACTOR  = 0.95
LEARNING_RATE = 0.25
MOB_WEIGHT    = 0.05
SEARCH_DEPTH  = 2        
POS_WEIGHT    = 0.5
SAVE_INTERVAL = 2000
PRINT_EVERY   = 200
TABLE_PATH    = "bot/evaluation_table_current/eval_table_zobrist_pruned.pkl"
# ───────────────────────────────────────────────────────────────────────

def play_one(bot_w, bot_b):
    board, hist = chess.Board(), []
    while not board.is_game_over():
        # record hash directly
        hist.append((zobrist.hash(board), board.turn, board.fen()))
        mv = bot_w.choose_move(board) if board.turn else bot_b.choose_move(board)
        board.push(mv)
    return board.result(), hist

def main():
    # instantiate *before* try so we can save in finally
    bot_w = ChessBotAgent(
        exploration_rate=INITIAL_EPS,
        learning_rate=LEARNING_RATE,
        mobility_weight=MOB_WEIGHT,
        positional_weight=POS_WEIGHT,
        save_interval=SAVE_INTERVAL,
        table_path=TABLE_PATH,
        search_depth=SEARCH_DEPTH,
        use_policy=False
    )
    bot_b = ChessBotAgent(
        exploration_rate=INITIAL_EPS,
        learning_rate=LEARNING_RATE,
        mobility_weight=MOB_WEIGHT,
        positional_weight=POS_WEIGHT,
        save_interval=SAVE_INTERVAL,
        table_path=TABLE_PATH,
        search_depth=SEARCH_DEPTH,
        use_policy=False
    )

    white_wins = black_wins = draws = 0
    eps = INITIAL_EPS

    try:
        for g in range(1, TOTAL_GAMES + 1):
            # ── 1) Swap who is White vs. Black ───────────────────────
            if g % 2 == 0:
                white_bot, black_bot = bot_w, bot_b
            else:
                white_bot, black_bot = bot_b, bot_w

            result, history = play_one(white_bot, black_bot)

            # update W–L–D counters
            if result == "1-0":
                # if it was bot_w in White, that's a white-side win; 
                # if it was bot_b in White, that's a black-side win
                if white_bot is bot_w:
                    white_wins += 1
                else:
                    black_wins += 1
            elif result == "0-1":
                # black_bot won
                if black_bot is bot_w:
                    white_wins += 1
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