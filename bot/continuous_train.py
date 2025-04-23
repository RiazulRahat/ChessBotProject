"""
Continuous self-play until 10 000 games (or Ctrl-C).
– ε starts at 0.20 and decays ×0.9 every 2 000 games
– learning-rate kept high (0.80) for fast TD-0 updates
– table saved every 50 games
"""

import chess, datetime, statistics, sys
from chess_bot import ChessBotAgent

TOTAL_GAMES      = 10_000          # hard stop
PRINT_EVERY      = 200             # stdev log
SAVE_INTERVAL    = 50              # pickle write
DECAY_EVERY      = 2_000           # games between ε decays
DECAY_FACTOR     = 0.9             # multiply ε by this
INITIAL_EPS      = 0.20
LEARNING_RATE    = 0.80

def play_one_game(white_bot, black_bot):
    board   = chess.Board()
    history = []

    while not board.is_game_over():
        history.append((board.fen(), board.turn))
        move = white_bot.choose_move(board) if board.turn == chess.WHITE \
               else black_bot.choose_move(board)
        board.push(move)

    white_bot.update_evaluation(history, board.result())
    black_bot.update_evaluation(history, board.result())

def main():
    white_bot = ChessBotAgent(exploration_rate=INITIAL_EPS,
                              learning_rate=LEARNING_RATE,
                              save_interval=SAVE_INTERVAL)
    black_bot = ChessBotAgent(exploration_rate=INITIAL_EPS,
                              learning_rate=LEARNING_RATE,
                              save_interval=SAVE_INTERVAL)

    try:
        for game_no in range(1, TOTAL_GAMES + 1):
            play_one_game(white_bot, black_bot)

            # ---- live stats ------------------------------------------------
            if game_no % PRINT_EVERY == 0:
                vals = white_bot.evaluation_table.values()
                now  = datetime.datetime.now().strftime("%H:%M:%S")
                print(f"{now} | {game_no:>5}/{TOTAL_GAMES}  "
                      f"stdev {statistics.pstdev(vals):.4f}  "
                      f"ε {white_bot.exploration_rate:.3f}")

            # ---- ε decay ---------------------------------------------------
            if game_no % DECAY_EVERY == 0:
                new_eps = white_bot.exploration_rate * DECAY_FACTOR
                white_bot.exploration_rate = new_eps
                black_bot.exploration_rate = new_eps
                print(f"--- decayed ε to {new_eps:.3f} at game {game_no} ---")

        print("\nTraining complete (10 000 games).")

    except KeyboardInterrupt:
        print("\nInterrupted – saving tables …")
    finally:
        white_bot._save_table()
        black_bot._save_table()
        print("Tables saved. Goodbye!")
        sys.exit()

if __name__ == "__main__":
    main()
