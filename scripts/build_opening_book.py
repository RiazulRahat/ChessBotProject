#!/usr/bin/env python3
from bot.utils.opening_book import build_opening_book, save_opening_book

# List your PGN files here:
pgn_files = [
    "books/caro_kann.pgn",
    # add as many as you like
]

# Build and save
book = build_opening_book(pgn_files, max_depth=12)
save_opening_book(book, "bot/opening_book.pkl")

print(f"Built opening book with {len(book)} positions.")