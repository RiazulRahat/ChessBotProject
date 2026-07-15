"""
Light‑weight debug printer.

Usage
-----
from bot.utils.debug import dprint

dprint("αβ depth=%d  value=%.1f", depth, val)
"""
import os, sys, logging

DEBUG = os.getenv("PYTHONLOGLEVEL", "DEBUG").upper() == "DEBUG"
DEBUG_LEVEL = int(os.getenv("ENGINE_DEBUG_LEVEL", "2"))

if DEBUG:
    logging.basicConfig(
        level   = logging.DEBUG,
        format  = "[%(asctime)s] %(message)s",
        datefmt = "%H:%M:%S",
        stream  = sys.stderr,
    )

def dprint(msg: str, *args, lvl: int = 2):
    if DEBUG and DEBUG_LEVEL >= lvl:
        logging.debug(msg % args)