"""
Standalone demo bot worker.

Run this in its own terminal window and leave it running while the market
is open. It does NOT need the FastAPI server (uvicorn) to be running -
this connects to MT5 and Supabase directly.

Usage:
    python scripts/run_demo_bot.py
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "forexai"))

from app.core.logger import logger
from app.models.db import update_bot_status
from app.services.demo_engine import run_cycle

ACCOUNT_ID = "00000000-0000-0000-0000-000000000001"
SYMBOL = "EURUSD"
POLL_SECONDS = 60  # how often to check for a new signal / closed trade


def main():
    print(f"Starting demo bot for {SYMBOL} (account {ACCOUNT_ID})", flush=True)
    logger.info(f"Starting demo bot for {SYMBOL} (account {ACCOUNT_ID})")
    update_bot_status(ACCOUNT_ID, status="running", current_mode="demo", notes="Demo bot worker started")

    cycle_count = 0
    try:
        while True:
            cycle_count += 1
            print(f"[cycle {cycle_count}] checking {SYMBOL}...", flush=True)
            try:
                run_cycle(ACCOUNT_ID, SYMBOL)
                print(f"[cycle {cycle_count}] done, no errors", flush=True)
            except Exception as e:
                print(f"[cycle {cycle_count}] ERROR: {e}", flush=True)
                logger.error(f"Error during demo cycle: {e}")
            print(f"[cycle {cycle_count}] sleeping {POLL_SECONDS}s...", flush=True)
            time.sleep(POLL_SECONDS)
    except KeyboardInterrupt:
        print("Demo bot stopped manually (Ctrl+C)", flush=True)
        logger.info("Demo bot stopped manually (Ctrl+C)")
        update_bot_status(ACCOUNT_ID, status="stopped", current_mode="demo", notes="Demo bot worker stopped manually")


if __name__ == "__main__":
    main()