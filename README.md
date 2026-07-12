# Chess Bot

A self-learning chess engine built with **TD(0) reinforcement learning** and **alpha-beta search**.
The bot learns by playing against itself, improving its positional evaluation over time through
temporal-difference updates — and it runs **continuously on AWS**, playing the public on Lichess
24/7 while training in the background.

**▶ Play it / watch it live:** [lichess.org/@/Riazul-Rahat](https://lichess.org/@/Riazul-Rahat)
Create Lichess account and play with blitz 3+2 casual

---

## Deployment (always-on, ~$12/month)

The bot is deployed to a single **AWS EC2** `t4g.micro` instance as a containerized, always-on
system. A two-container **Docker Compose** architecture runs the Lichess bridge and a self-play
trainer side by side, sharing one Docker volume — so the bot competes against real opponents
around the clock **while simultaneously training and improving its own evaluation.**

```
┌─────────────────────────┐        ┌─────────────────────────┐
│  Container: bot         │        │  Container: trainer     │
│  lichess-bot bridge     │        │  continuous_train.py    │
│  → run_engine.py (UCI)  │        │  self-play, ε-annealed  │
│  plays humans/bots 24/7 │        │  depth-limited search   │
│  reads eval table       │        │  sole writer of table   │
└───────────┬─────────────┘        └───────────┬─────────────┘
            │ reads                             │ writes
            └───────────────┬───────────────────┘
                            ▼
              ┌───────────────────────────────┐
              │  shared Docker volume  /data   │
              │  eval table · zobrist keys ·   │
              │  game PGNs · dated snapshots   │
              └───────────────────────────────┘
```

**Engineered for unattended operation:**

- **Atomic weight persistence** — write-to-temp-then-`os.replace` so a reader never sees a torn table file
- **Single-writer policy** — the trainer owns the eval table; the live bot reads it, avoiding lost-update races on the shared volume
- **Per-game continuous weight pickup** — the bridge spawns a fresh engine process per game, so newly-trained weights go live with zero downtime and no restarts
- **CPU-credit-aware budgeting** — the trainer is capped (`cpus`, `mem_limit`) so burstable-instance credits never starve the public-facing bot
- **Graceful shutdown** — `stop_signal: SIGINT` triggers the trainer's save-on-exit, so `docker compose down` never discards in-progress learning
- **Automated daily S3 backups** — dated snapshots pairing the eval table with the Zobrist keys that make it meaningful, plus every archived game PGN
- **CloudWatch monitoring & alerts** — instance health and CPU-credit alarms via SNS email

> **Deployment files:** `Dockerfile`, `docker-compose.yml`, and `entrypoint.sh` at the repo root
> define the image and the two services. The token-bearing `training_model/config.yml` is
> gitignored — supply your own from the lichess-bot config template.

---

## Architecture

### Core components

| File | Role |
|---|---|
| `bot/chess_bot.py` | `ChessBotAgent` — move selection, alpha-beta search, TD learning |
| `bot/evaluation/positional_heuristics.py` | Piece-square table eval (standard Simplified Evaluation Function) |
| `bot/utils/zobrist.py` | Zobrist hashing singleton — 64-bit position keys |
| `bot/utils/opening_book.py` | FEN-dict opening book loader (PGN-sourced fallback) |
| `bot/continuous_train.py` | Self-play training loop |
| `chess_engine/pygame_bot_human.py` | Pygame GUI for human vs bot |
| `training_model/run_engine.py` | UCI engine entry point (lichess-bot / any UCI GUI) |
| `tests/evaluate_elo.py` | Elo benchmark runner vs Stockfish |

### How move selection works

1. **Polyglot opening book** (`book_library/Perfect2023.bin`) — weighted random book move if the position is in book
2. **FEN-dict book** (`bot/opening_book.pkl`) — fallback book from PGN files
3. **ε-greedy exploration** — random legal move with probability ε
4. **Alpha-beta search** — minimax with:
   - Transposition table (depth-gated reuse)
   - Iterative deepening with aspiration windows (`choose_move_timed`)
   - Quiescence search (captures-only, MVV-LVA ordered)
   - History heuristic for quiet move ordering

### How evaluation works

```
state_value = eval_table[zobrist_key]      # TD-learned value (primary)
            + material_weight * material   # centipawn material balance
            + positional_weight * PST      # piece-square table bonus
```

### How learning works

After each game, a TD(0) backward pass updates every visited position:

```
new_value = old + α * (target - old)
target    = +1.0 (White win) | -1.0 (Black win) | 0.0 (draw)
```

A discount factor **γ = 0.99** reduces the weight of early-game positions so the bot doesn't
over-index on opening moves.

---

## Installation

```bash
git clone --recurse-submodules <repo_url>
cd ChessBotProject

python3 -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate

pip install -r requirements.txt
```

> The `--recurse-submodules` flag matters: `training_model/lichess-bot/` is a submodule.
> If you already cloned without it, run `git submodule update --init`.

**Optional — Stockfish** (only needed for Elo evaluation):

```bash
brew install stockfish          # macOS
# or download from https://stockfishchess.org/download/
```

---

## Quick Start

### Play against the bot (Pygame GUI)

```bash
python -m chess_engine.pygame_bot_human
```

Click a piece to select it, then click a destination square. The bot plays as Black by default.

### Run self-play training

```bash
python -m bot.continuous_train --games 1000
```

The eval table is saved every 500 games (configurable via `SAVE_INTERVAL`) and also on `Ctrl+C`
interrupt. Progress is printed every 100 games showing W-L-D, table size, and current ε.

**Training hyperparameters** (edit `bot/continuous_train.py`):

| Constant | Default | Description |
|---|---|---|
| `INITIAL_EPS` | `0.20` | Starting exploration rate |
| `DECAY_EVERY` | `150` | Games between ε decay steps |
| `DECAY_FACTOR` | `0.88` | Multiplier per decay step |
| `GAMMA` | `0.99` | TD discount factor |
| `SEARCH_DEPTH` | `3` | Alpha-beta depth during training |
| `SAVE_INTERVAL` | `500` | Games between auto-saves |

### Run the UCI engine (lichess-bot / arena)

```bash
python training_model/run_engine.py
```

This speaks UCI over stdin/stdout and learns from each completed game. Point any UCI-compatible
GUI or lichess-bot at this script. The engine uses time controls when provided
(`wtime`/`btime`/`winc`/`binc`) and falls back to fixed-depth search for analysis mode.

### Run the full deployed stack locally (Docker)

```bash
# supply training_model/config.yml with your Lichess bot token first
docker compose up -d --build
docker compose logs -f trainer      # watch it learn
```

### Evaluate Elo vs Stockfish

```bash
# Requires stockfish on PATH
python tests/evaluate_elo.py --games 20
```

Runs the bot against Stockfish at Skill Level 0, computes an estimated Elo, and saves all games
to `vs_stockfish.pgn`.

---

## Configuration

### Search depth

- **Training** (`continuous_train.py`): `SEARCH_DEPTH = 3` — kept lower for training speed
- **UCI engine** (`run_engine.py`): `search_depth = 5`
- **GUI** (`pygame_bot_human.py`): `search_depth = 5`

### Positional weights

In `bot/chess_bot.py` constructor defaults:

```python
material_weight  = 0.15   # pawn units per unit of material imbalance
positional_weight = 0.05  # pawn units per PST centipawn score
```

### Opening book

The bot uses `book_library/Perfect2023.bin` (polyglot format) for opening moves. To rebuild the
FEN-dict fallback from PGN files, use `bot/utils/opening_book.py`:

```python
from bot.utils.opening_book import build_opening_book, save_opening_book

book = build_opening_book(["path/to/openings.pgn"], max_depth=12)
save_opening_book(book, "bot/opening_book.pkl")
```

---

## Project Structure

```
ChessBotProject/
├── bot/
│   ├── chess_bot.py               # ChessBotAgent (core)
│   ├── continuous_train.py        # Self-play training loop
│   ├── evaluation/
│   │   └── positional_heuristics.py  # Piece-square tables
│   ├── evaluation_table_current/  # Saved eval tables (pkl, gitignored)
│   └── utils/
│       ├── zobrist.py             # Zobrist hashing
│       ├── opening_book.py        # Book build/load helpers
│       └── debug.py               # Conditional debug logging
├── chess_engine/
│   ├── chess_engine.py            # chess.Board wrapper
│   ├── pygame_bot_human.py        # Pygame GUI
│   ├── pygame_chess.py            # Rendering helpers
│   └── utils.py                   # Image scale utility
├── book_library/
│   └── Perfect2023.bin            # Polyglot opening book
├── training_model/
│   ├── run_engine.py              # UCI engine entry point
│   ├── config.yml                 # lichess-bot config (gitignored — holds token)
│   └── lichess-bot/               # lichess-bot submodule
├── tests/
│   ├── test_engine_basics.py      # Move legality / search tests
│   ├── test_quiescence.py         # Quiescence search tests
│   └── evaluate_elo.py            # Stockfish Elo benchmark
├── Dockerfile                     # single image for both services
├── docker-compose.yml             # bot + trainer services
├── entrypoint.sh                  # wires shared-volume paths on startup
└── requirements.txt
```

> **Note:** Pickle files (`*.pkl`) are gitignored — the eval table, Zobrist keys, and opening-book
> pkl are local/volume only. The repo includes `book_library/Perfect2023.bin` (polyglot binary,
> 52 KB) as the primary opening book.

---

## Running Tests

```bash
pytest
```

All tests are in `tests/` and cover move legality, alpha-beta search termination, and quiescence
search correctness. The training loop and eval function are validated manually via
`tests/evaluate_elo.py`.

---

## Tech Stack

**Language:** Python
**ML/RL:** TD(0) temporal-difference learning, self-play, ε-greedy exploration
**Search:** alpha-beta, quiescence, transposition tables, Zobrist hashing, iterative deepening
**Deployment:** AWS (EC2, S3, IAM, CloudWatch) · Docker · Docker Compose · Linux
**Libraries:** python-chess, pygame, lichess-bot
