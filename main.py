#!/usr/bin/env python3
"""Quick-start entrypoint: run the bot with `python3 main.py`.

Equivalent to `python -m bot.main` — kept as a thin wrapper so the repo
root has an obvious file to run without knowing the package layout.
"""

from bot.main import run

if __name__ == "__main__":
    run()
