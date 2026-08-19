# HemoLink — Blood Donor Matching Backend (v1 draft)

A FastAPI + PostgreSQL backend implementing the core matching, notification,
parallel-confirmation, and reliability logic. The AI assistant (HemoBot) and
frontend are **not** included in this draft — scope was backend/API only.

## Project layout — what runs where

| File | Where it runs |
|---|---|
| `main.py` | **Run this to start the API server.** `uvicorn main:app --reload` from the project root. |
| `scripts/no_show_checker.py` | **Run this as a second, always-on process** alongside the server. `python scripts/no_show_checker.py`. It polls for overdue acceptances and flags no-shows. |
| `app/database.py` | Imported automatically — never run directly. Reads `DATABASE_URL` env var. |
| `app/models/models.py` | Imported automatically — defines the DB tables. |
| `app/schemas/schemas.py` | Imported automatically — API request/response shapes. |
| `app/services/*.py` | Imported automatically — all business logic (matching, compatibility, geo, reliability, notifications, acceptances). |
| `app/routers/*.py` | Imported automatically — API endpoints, wired into `main.py`. |

You never run anything under `app/` directly — only `main.py` and
`scripts/no_show_checker.py` are entrypoints.

## Setup

1. Install PostgreSQL locally (or use a hosted instance) and create a database:
   ```
   createdb hemolink
   ```
2. From the `hemolink/` project root, install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Set your database connection string:
   ```
   export DATABASE_URL="postgresql://<user>:<password>@localhost:5432/hemolink"
   ```
4. Start the API:
   ```
   uvicorn main:app --reload
   ```
   Tables are created automatically on first run. Visit
   `http://localhost:8000/docs` for interactive API docs (Swagger UI) — the
   easiest way to try every endpoint by hand.
5. In a **second terminal**, start the no-show checker:
   ```
   python scripts/no_show_checker.py
   ```

## Core flow, end to end

1. `POST /donors/` — register a donor (name, phone, blood group, lat/lon).
2. `POST /requests/` — a hospital creates a blood request. This immediately
   runs the tiered matching engine (5km → 10km → 20km) and notifies (logs, in
   this draft) every eligible candidate, ranked by distance + reliability +
   verification + urgency.
3. `POST /acceptances/{request_id}/accept/{donor_id}` — one or more donors
   accept. Each gets a `PENDING` acceptance with an ETA deadline.
4. `POST /acceptances/{acceptance_id}/fulfill` — hospital staff confirm the
   donor arrived and donated. That acceptance becomes `FULFILLED`; every other
   pending acceptance on the same request is automatically `STOOD_DOWN`.
5. If a donor's ETA deadline passes before they fulfill, the background
   `no_show_checker.py` process flags it `NO_SHOW`, penalizes their
   reliability score, and puts them on a 36-hour cooldown.
6. `POST /donors/{donor_id}/verify` — hospital marks a donor's first donation
   verified, unlocking the verified badge (used as a scoring bonus).
7. `POST /requests/{request_id}/rematch` — manually re-trigger matching if a
   request is still unfulfilled (e.g. after a no-show).

## Design notes / what's simplified for this draft

- **Notifications** are logged to the DB and printed to console
  (`send_sms` in `notification_service.py`) instead of actually sending SMS —
  swap in Twilio, FCM, etc. when ready.
- **Suspension** is automatic after 3 lifetime no-shows; `admin_unsuspend()`
  in `reliability_service.py` is there for a future admin endpoint.
- **Migrations**: tables are created via `Base.metadata.create_all` for dev
  convenience. For production, switch to Alembic migrations.
- **Scoring weights** (distance/reliability/verification/urgency) live at the
  top of `matching_engine.py` as named constants — tune freely.

## Next steps this draft doesn't cover

- HemoBot AI assistant (donor-facing + hospital-facing)
- Auth (donor/hospital/admin accounts, login)
- Real SMS/push integration
- Admin dashboard endpoints (suspend/unsuspend, view logs)
