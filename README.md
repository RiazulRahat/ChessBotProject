# Neurochess Bot

> **NOTE:** This is a fork of [ChessBotProject](https://github.com/RiazulRahat/chess-bot).
> Also Github version does not include pkl files

A modular, self-learning chess engine built with TD(0) learning, Zobrist hashing, and positional heuristics, with support for:

- Self-play training and Stockfish bootstrapping
- Eval-table pruning and policy generation
- Opening-book integration via PGN files
- Pygame GUI for human vs. bot play
- Elo evaluation against Stockfish

## Current Features

  Key Capabilities (2025‑05)

- Transposition Table (TT) Cache – 64‑bit keyed, depth‑aware replacement that dramatically reduces re‑search of repeated positions.

- Iterative Deepening / Alpha‑Beta Search – defaults to depth 3 (full ply) with PV‑move reordering; configurable per front‑end.

- Quiescence Extension – capture‑only follow‑up out to 5 ply to remove horizon noise.

- TD‑Learning Evaluation – >550 k Zobrist‑keyed positions learned via self‑play + Stockfish bootstrapping.

- Positional Heuristics – piece‑square tables, pawn structure, development, king safety, mobility differential, bishop‑pair & passed‑pawn bonuses.

- Zobrist Pruning Tools – scripts to convert, merge and prune massive eval tables.

- Policy Book Generation – offline probability tables for instant move selection in known states.

- Opening‑Book Support – load PGN theory lines into a lightweight opening book.

- Elo Evaluation Harness – automated match runner vs. Stockfish (any elo level) with CSV output.

- Pygame GUI – play against the engine, watch self‑play, or step through search in real‑time.

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



Note::: Policy might not work and will be playing against a 0 knowledge bot... pkl files too large for github
