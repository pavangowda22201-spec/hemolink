"""
RUN LOCATION: Run this as a SEPARATE, ALWAYS-ON process from the project root,
alongside the API server (main.py).

    cd HemoLinkBackend
    python scripts/no_show_checker.py

This worker performs two automatic lifecycle tasks every 60 seconds:

1. Flags overdue donor acceptances as NO_SHOW.
2. Expires stale OPEN/MATCHING blood requests.

It does NOT run inside the API process.

In production, replace the while-loop with a proper scheduler
(cron, Celery beat, APScheduler as a service, etc.).
"""

import os
import sys
import time

# Allow imports from the project root when this file is run directly.
sys.path.append(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)

from app.database import SessionLocal
from app.services.acceptance_service import check_and_flag_no_shows
from app.services.request_lifecycle import expire_stale_requests


POLL_INTERVAL_SECONDS = 60


if __name__ == "__main__":
    print(
        "HemoLink lifecycle worker started. "
        f"Polling every {POLL_INTERVAL_SECONDS}s. Ctrl+C to stop."
    )

    while True:
        db = SessionLocal()

        try:
            no_shows = check_and_flag_no_shows(db)

            if no_shows:
                print(f"Flagged {no_shows} no-show(s).")

            expired = expire_stale_requests(db)

            if expired:
                print(f"Expired {expired} stale request(s).")

        except Exception as exc:
            print(f"Lifecycle worker error: {exc}")

        finally:
            db.close()

        time.sleep(POLL_INTERVAL_SECONDS)