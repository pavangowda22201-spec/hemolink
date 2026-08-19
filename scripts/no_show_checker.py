"""
RUN LOCATION: Run this as a SEPARATE, ALWAYS-ON process from the project root,
alongside the API server (main.py). It does NOT run inside the API process.
    cd hemolink
    python scripts/no_show_checker.py

In production, replace the while-loop with a proper scheduler (cron, Celery
beat, APScheduler as a service, etc.) — this loop is a simple dev-friendly
stand-in that polls every 60 seconds.
"""
import time
import sys
import os

# Allow running this script directly from the scripts/ folder
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from app.services.acceptance_service import check_and_flag_no_shows

POLL_INTERVAL_SECONDS = 60

if __name__ == "__main__":
    print("HemoLink no-show checker started. Polling every "
          f"{POLL_INTERVAL_SECONDS}s. Ctrl+C to stop.")
    while True:
        db = SessionLocal()
        try:
            flagged = check_and_flag_no_shows(db)
            if flagged:
                print(f"Flagged {flagged} no-show(s).")
        finally:
            db.close()
        time.sleep(POLL_INTERVAL_SECONDS)
