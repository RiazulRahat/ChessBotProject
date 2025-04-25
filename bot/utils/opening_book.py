import chess
import chess.pgn
import pickle
import os

def build_opening_book(pgn_paths, max_depth=10):
    """
    Build an opening book: map FEN to a list of book moves (in UCI) up to `max_depth` plies per game.

    pgn_paths: list of file paths to PGN files containing opening lines.
    max_depth: maximum number of plies (half-moves) to read per game.

    Returns:
        dict: {fen_string: [uci_move_str, ...]}
    """
    book = {}
    for path in pgn_paths:
        with open(path, 'r') as f:
            while True:
                game = chess.pgn.read_game(f)
                if game is None:
                    break
                board = game.board()
                for i, node in enumerate(game.mainline()):
                    if i >= max_depth:
                        break
                    fen = board.fen()
                    move = node.move
                    uci = move.uci()
                    book.setdefault(fen, []).append(uci)
                    board.push(move)
    return book


def save_opening_book(book, filepath):
    """
    Save the opening book dictionary to disk as a pickle.
    """
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, 'wb') as f:
        pickle.dump(book, f)


def load_opening_book(filepath):
    """
    Load a pickled opening book from disk.
    Returns an empty dict if file not found.
    """
    if not os.path.exists(filepath):
        return {}
    with open(filepath, 'rb') as f:
        return pickle.load(f)

# Example usage (uncomment to run directly):
# if __name__ == '__main__':
#     pgn_files = ['book1.pgn', 'book2.pgn']
#     book = build_opening_book(pgn_files, max_depth=12)
#     save_opening_book(book, 'opening_book.pkl')