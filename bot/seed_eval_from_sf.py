"""
Seed the eval table with Stockfish's positional understanding by having SF
play itself at high depth, then analysing every position from those games.

This is a one-time (or periodic) offline pass — run it before or between
training sessions to pre-populate the table with high-quality evaluations
instead of waiting for gameplay to slowly accumulate them.

Run with:
    python -m bot.seed_eval_from_sf --games 50
    python -m bot.seed_eval_from_sf --games 200 --game-depth 10 --eval-depth 5
    python -m bot.seed_eval_from_sf --pgn path/to/games.pgn  (use existing PGN instead)
"""
import argparse
import datetime
import os
import pickle
import time
import chess
import chess.engine
import chess.pgn

from bot.utils.zobrist import zobrist

# ─── defaults ────────────────────────────────────────────────────────────────
STOCKFISH_PATH = "/opt/homebrew/bin/stockfish"
DEFAULT_GAMES  = 100
GAME_DEPTH     = 10    # SF vs SF self-play depth — higher = better quality games
EVAL_DEPTH     = 5     # depth used when analysing each position
EVAL_WEIGHT    = 0.50  # alpha: higher than training (0.20) because this is offline seeding
SAVE_EVERY     = 20    # save table every N games
TABLE_PATH     = "bot/evaluation_table_current/eval_table_zobrist_pruned.pkl"
# ─────────────────────────────────────────────────────────────────────────────


def load_table(path: str) -> dict:
    if os.path.exists(path):
        try:
            with open(path, "rb") as f:
                return pickle.load(f)
        except Exception as e:
            print(f"Warning: could not load table ({e}), starting fresh.")
    return {}


def save_table(table: dict, zkey_to_fen: dict, path: str):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        pickle.dump(table, f)
    fen_path = path.replace(".pkl", "_zkey2fen.pkl")
    with open(fen_path, "wb") as f:
        pickle.dump(zkey_to_fen, f)


def blend(table: dict, zkey_to_fen: dict,
          zkey: int, fen: str, sf_value: float, alpha: float):
    old = table.get(zkey, 0.0)
    table[zkey] = old + alpha * (sf_value - old)
    zkey_to_fen.setdefault(zkey, fen)


def analyse_game(
    board_history: list,   # list of (zkey, fen) pairs
    engine: chess.engine.SimpleEngine,
    eval_limit: chess.engine.Limit,
    table: dict,
    zkey_to_fen: dict,
    alpha: float,
) -> int:
    """Analyse every position in the game and blend SF's eval. Returns positions updated."""
    updated = 0
    for zkey, fen in board_history:
        board = chess.Board(fen)
        try:
            info = engine.analyse(board, eval_limit)
            cp = info["score"].white().score(mate_score=10000)
        except Exception:
            continue
        if cp is None:
            continue
        sf_value = max(-1.0, min(1.0, cp / 1000.0))
        blend(table, zkey_to_fen, zkey, fen, sf_value, alpha)
        updated += 1
    return updated


def play_sf_game(
    engine: chess.engine.SimpleEngine,
    game_limit: chess.engine.Limit,
) -> list:
    """Have SF play itself; return list of (zkey, fen) for every position."""
    board = chess.Board()
    history = []
    while not board.is_game_over():
        history.append((zobrist.hash(board), board.fen()))
        mv = engine.play(board, game_limit).move
        board.push(mv)
    return history


def seed_from_pgn(
    pgn_path: str,
    engine: chess.engine.SimpleEngine,
    eval_limit: chess.engine.Limit,
    table: dict,
    zkey_to_fen: dict,
    alpha: float,
    save_every: int,
    table_path: str,
):
    total_positions = 0
    g = 0
    with open(pgn_path) as f:
        while True:
            game = chess.pgn.read_game(f)
            if game is None:
                break
            g += 1
            board = game.board()
            history = []
            for move in game.mainline_moves():
                history.append((zobrist.hash(board), board.fen()))
                board.push(move)

            updated = analyse_game(history, engine, eval_limit,
                                   table, zkey_to_fen, alpha)
            total_positions += updated

            now = datetime.datetime.now().strftime("%H:%M:%S")
            print(f"{now} | game {g:,}  positions={updated}  "
                  f"table={len(table):,}  total_analysed={total_positions:,}")

            if g % save_every == 0:
                save_table(table, zkey_to_fen, table_path)
                print(f"  → saved ({len(table):,} entries)")

    return g, total_positions


def seed_from_selfplay(
    num_games: int,
    engine: chess.engine.SimpleEngine,
    game_limit: chess.engine.Limit,
    eval_limit: chess.engine.Limit,
    table: dict,
    zkey_to_fen: dict,
    alpha: float,
    save_every: int,
    table_path: str,
    deadline: float = 0,
) -> tuple:
    total_positions = 0
    g = 0
    for g in range(1, num_games + 1):
        if deadline and time.time() >= deadline:
            print(f"\nTime limit reached after {g - 1} games.")
            g -= 1
            break
        history = play_sf_game(engine, game_limit)
        updated = analyse_game(history, engine, eval_limit,
                               table, zkey_to_fen, alpha)
        total_positions += updated

        now = datetime.datetime.now().strftime("%H:%M:%S")
        limit_str = f"/{num_games}" if not deadline else ""
        print(f"{now} | game {g:,}{limit_str}  plies={len(history)}  "
              f"positions_analysed={updated}  table={len(table):,}")

        if g % save_every == 0:
            save_table(table, zkey_to_fen, table_path)
            print(f"  → saved ({len(table):,} entries)")

    return g, total_positions


def main(
    num_games: int = DEFAULT_GAMES,
    stockfish_path: str = STOCKFISH_PATH,
    game_depth: int = GAME_DEPTH,
    eval_depth: int = EVAL_DEPTH,
    eval_weight: float = EVAL_WEIGHT,
    pgn_path: str = "",
    table_path: str = TABLE_PATH,
    minutes: float = 0,
):
    table = load_table(table_path)
    zkey_to_fen_path = table_path.replace(".pkl", "_zkey2fen.pkl")
    zkey_to_fen = {}
    if os.path.exists(zkey_to_fen_path):
        with open(zkey_to_fen_path, "rb") as f:
            zkey_to_fen = pickle.load(f)

    engine = chess.engine.SimpleEngine.popen_uci(stockfish_path)
    game_limit = chess.engine.Limit(depth=game_depth)
    eval_limit = chess.engine.Limit(depth=eval_depth)
    deadline = time.time() + minutes * 60 if minutes > 0 else 0

    source = f"PGN: {pgn_path}" if pgn_path else \
             f"SF self-play (game depth={game_depth})"
    target_str = f"{minutes:.0f} min" if minutes > 0 else f"{num_games} games"
    print(f"Seeding eval table from {source}")
    print(f"Target={target_str}  eval-depth={eval_depth}  blend-alpha={eval_weight}")
    print(f"Table: {table_path}  (starting size: {len(table):,})\n")

    try:
        if pgn_path:
            g, total = seed_from_pgn(
                pgn_path, engine, eval_limit,
                table, zkey_to_fen, eval_weight, SAVE_EVERY, table_path)
        else:
            g, total = seed_from_selfplay(
                num_games, engine, game_limit, eval_limit,
                table, zkey_to_fen, eval_weight, SAVE_EVERY, table_path,
                deadline)

    except KeyboardInterrupt:
        print("\nInterrupted — saving …")
    finally:
        engine.quit()
        save_table(table, zkey_to_fen, table_path)
        print(f"\nDone.  Table saved to {table_path}")
        print(f"Final table size: {len(table):,} entries")
        print(f"Games processed: {g:,}  |  Positions analysed: {total:,}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Seed eval table from SF self-play or a PGN file.")
    parser.add_argument("--games",          type=int,   default=DEFAULT_GAMES,
                        help="number of SF self-play games to generate (ignored with --pgn)")
    parser.add_argument("--stockfish-path", type=str,   default=STOCKFISH_PATH)
    parser.add_argument("--game-depth",     type=int,   default=GAME_DEPTH,
                        help="SF vs SF self-play search depth")
    parser.add_argument("--eval-depth",     type=int,   default=EVAL_DEPTH,
                        help="depth used when analysing each position")
    parser.add_argument("--eval-weight",    type=float, default=EVAL_WEIGHT,
                        help="blending alpha (0–1); higher = faster convergence")
    parser.add_argument("--pgn",            type=str,   default="",
                        dest="pgn_path",
                        help="path to a PGN file; skips self-play generation")
    parser.add_argument("--table-path",     type=str,   default=TABLE_PATH)
    parser.add_argument("--minutes",        type=float, default=0,
                        help="stop after this many minutes (overrides --games if > 0)")
    args = parser.parse_args()
    main(args.games, args.stockfish_path, args.game_depth,
         args.eval_depth, args.eval_weight, args.pgn_path, args.table_path,
         args.minutes)
