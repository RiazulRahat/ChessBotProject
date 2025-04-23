# bot/continuous_train.py
"""
Run self‑play games forever (or until you press Ctrl‑C).
Uses the same ChessBotAgent implementation that pickles its table after each game.
"""

import chess, datetime
from chess_bot import ChessBotAgent

def play_one_game(white_bot, black_bot, game_no):
    board = chess.Board()
    history = []                       # [(fen, white_to_move_bool), …]

    while not board.is_game_over():
        history.append((board.fen(), board.turn))
        move = white_bot.choose_move(board) if board.turn == chess.WHITE \
               else black_bot.choose_move(board)
        board.push(move)

    result = board.result()            # "1-0" / "0-1" / "1/2-1/2"
    # print(f"[{game_no}] result {result:7} | plies {board.fullmove_number*2}")
    white_bot.update_evaluation(history, result)
    black_bot.update_evaluation(history, result)

def main():
    white_bot = ChessBotAgent(exploration_rate=0.2, learning_rate=0.10, save_interval=50)
    black_bot = ChessBotAgent(exploration_rate=0.2, learning_rate=0.10, save_interval=50)

    game_counter = 1
    try:
        while True:
            play_one_game(white_bot, black_bot, game_counter)

            if game_counter % 50 == 0:                    # show every 50 games
                print(f"== finished {game_counter} games ==")
                print(datetime.datetime.now().strftime("%H:%M:%S"), f"| {game_counter} games")


            game_counter += 1

    except KeyboardInterrupt:
        white_bot._save_table()
        black_bot._save_table()
        print("\nTraining interrupted by user. Table already saved. Goodbye!")

if __name__ == "__main__":
    main()