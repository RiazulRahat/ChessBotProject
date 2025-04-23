"""
Self-play trainer.  Edit TOTAL_GAMES or run Ctrl-C to stop.
"""

import chess, datetime, statistics, sys
from chess_bot import ChessBotAgent

# ─── hyper-parameters ──────────────────────────────────────────────────
TOTAL_GAMES   = 20_000
INITIAL_EPS   = 0.15
DECAY_EVERY   = 5_000
DECAY_FACTOR  = 0.85
LEARNING_RATE = 0.60
SAVE_INTERVAL = 50
PRINT_EVERY   = 200
TABLE_PATH    = "bot/eval_table.pkl"
# ───────────────────────────────────────────────────────────────────────

def play_one(bot_w, bot_b):
    board, hist = chess.Board(), []
    while not board.is_game_over():
        hist.append((board.fen(), board.turn))
        mv = bot_w.choose_move(board) if board.turn else bot_b.choose_move(board)
        board.push(mv)
    res = board.result()
    bot_w.update_evaluation(hist, res)
    bot_b.update_evaluation(hist, res)

def main():
    bot_w = ChessBotAgent(INITIAL_EPS, LEARNING_RATE, SAVE_INTERVAL, TABLE_PATH)
    bot_b = ChessBotAgent(INITIAL_EPS, LEARNING_RATE, SAVE_INTERVAL, TABLE_PATH)
    for g in range(1, TOTAL_GAMES + 1):
        play_one(bot_w, bot_b)
        if g % PRINT_EVERY == 0:
            sd = statistics.pstdev(bot_w.evaluation_table.values())
            now = datetime.datetime.now().strftime("%H:%M:%S")
            print(f"{now} | {g:,} games  stdev {sd:.4f}  ε {bot_w.exploration_rate:.3f}")
        if g % DECAY_EVERY == 0:
            eps = bot_w.exploration_rate * DECAY_FACTOR
            bot_w.exploration_rate = bot_b.exploration_rate = eps
            print(f"--- decayed ε → {eps:.3f} at game {g:,} ---")

    bot_w._save_table(); bot_b._save_table()
    print("Training complete.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nInterrupted.")
