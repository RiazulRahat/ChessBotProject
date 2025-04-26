> **NOTE:** This is a fork of [ChessBotProject](https://github.com/RiazulRahat/ChessBotProject).
> Also Github version does not include pkl files

# Neurochess Bot

A modular, self-learning chess engine built with TD(0) learning, Zobrist hashing, and positional heuristics, with support for:

- Self-play training and Stockfish bootstrapping
- Eval-table pruning and policy generation
- Opening-book integration via PGN files
- Pygame GUI for human vs. bot play
- Elo evaluation against Stockfish

## Current Features

  At this level, the bot already supports:

- TD‑Learning Evaluation: a large Zobrist‑keyed eval table built via self‑play and bootstrapping capability with other bots
- Positional Heuristics: piece‑square value tables, pawn structure, piece safety, development & king safety bonuses.
- Quiescence Search as an Extension: lightweight capture‑only to eliminate horizon blunders
- Zobrist Hashing & Pruning: fast 64‑bit state keys (upgrade from FEN) with pruning functionality to remove low‑value entries.
- Policy Book Generation: offline policy compiled from the eval table for instant lookup in known positions.
- Opening‑Book Integration: capability to load PGN books to steer the first dozen plies(moves) into meaningful theory lines.
- Elo Evaluation Harness: automated matches vs. Stockfish version for strength estimation and tuning.
- Pygame GUI: interactive human vs. bot play with timed, iterative‑deepening moves and policy fallback.

## Installation:

- git clone <repo_url>
- cd ChessBotProject
- python3 -m venv .venv
- source .venv/bin/activate
- pip install -r requirements.txt


## Usage:

  ### Self-Play Training

    # Fast bulk training (no quiescence)
    python -m bot.continuous_train

    # (Optional) Enable quiescence in training
    edit bot/continuous_train.py: use_quiescence=True

  ### Policy Generation

    # After training completes:
    python bot/build_policy.py

  ### Opening Book

    # Build opening_book.pkl from your PGN files:
    python scripts/build_opening_book.py

  ### Eval-Table Conversion & Pruning

    # Convert FEN→Zobrist:
    python training/convert_eval_table_to_zobrist.py

    # Prune low-value entries:
    python training/prune_eval_table.py

  ### Elo Evaluation

    # Test bot vs Stockfish (e.g. 100 games):
    python evaluate_elo.py --games 100 --positional-weight 0.8

  ### Human vs Bot GUI

    python -m chess_engine.pygame_bot_human

    Use the GUI to play against the bot with the latest trained policy and heuristics.


## Configuration:

- Hyperparameters for training are in bot/continuous_train.py.
- Heuristic weights (positional, mobility, safety) live in bot/evaluation/positional_heuristics.py.
- Search settings (depth, quiescence, time-per-move) are in bot/chess_bot.py and pygame_bot_human.py.
  
Adjust these to tune difficulty or personality.
