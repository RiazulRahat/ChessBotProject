# bot/continuous_train.py
"""
Run self‑play games forever (or until you press Ctrl‑C).
Uses the same ChessBotAgent implementation that pickles its table after each game.
"""

import chess, time
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
    print(f"[{game_no}] result {result:7} | plies {board.fullmove_number*2}")
    white_bot.update_evaluation(history, result)
    black_bot.update_evaluation(history, result)

def main():
    white_bot = ChessBotAgent(exploration_rate=0.2)
    black_bot = ChessBotAgent(exploration_rate=0.2)

    game_counter = 1
    try:
        while True:
            play_one_game(white_bot, black_bot, game_counter)
            game_counter += 1

            # --- optional niceties -----------------------------------------
            if game_counter % 50 == 0:        # every 50 games, short pause
                print("== 50 games done, sleeping 2 s ==")
                time.sleep(2)
    except KeyboardInterrupt:
        print("\nTraining interrupted by user. Table already saved. Goodbye!")

if __name__ == "__main__":
    main()
