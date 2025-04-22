# bot/trainer.py
import chess
from chess_bot import ChessBotAgent

def self_play_training(num_games=100):
    white = ChessBotAgent(exploration_rate=0.2)
    black = ChessBotAgent(exploration_rate=0.2)

    for n in range(1, num_games + 1):
        board = chess.Board()
        history = []                          # [(fen, white_to_move_bool), …]

        while not board.is_game_over():
            history.append((board.fen(), board.turn))   # BEFORE move
            move = white.choose_move(board) if board.turn == chess.WHITE \
                   else black.choose_move(board)
            board.push(move)

        result = board.result()               # "1-0", "0-1", "1/2-1/2"
        print(f"Game {n}/{num_games} finished: {result}")

        white.update_evaluation(history, result)
        black.update_evaluation(history, result)

    return white, black


if __name__ == "__main__":
    self_play_training(10)
