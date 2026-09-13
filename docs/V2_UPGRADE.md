# FraudMesh v2 upgrade and operating guide

## Preserved deployment

The repository still has separate `frontend/` and `backend/` directories. Existing REST routes, JWT configuration, database connection variables, Railway Docker/start configuration, Vercel rewriting, landing page, animations and original palette styles are retained. New controls use a separate `workflow.css` stylesheet based on the existing console palette.

Migration `20260913_0002` adds transaction labels, model artifacts, one-time password resets and indexes for workspace/time/entity queries. It does not delete or rewrite existing transactions, users, alerts, cases or model runs. The existing container startup runs `alembic upgrade head`. `/health` remains compatible; `/ready` additionally checks database connectivity.

Rollback: redeploy the previous Git commit. Leave the additive tables in place; do not run a database downgrade on live data. No new paid services are needed.

## End-to-end workflow

1. Sign in or create a workspace. Administrators can add analysts/investigators in Administration and manage their roles or activation status.
2. Open Live monitor. Submit a transaction, import UTF-8 CSV, or explicitly start simulation. API clients can post authenticated events to `/api/v1/transactions`. There is no preconnected bank feed.
3. Every accepted event is persisted, scored, connected to the entity graph and broadcast after commit. Duplicate external IDs with matching payloads return the original record. Conflicting payloads return HTTP 409.
4. Inspect transaction features, stored score/model details, and graph relationships. Live updates invalidate relevant screens throughout the application; reconnecting reconciles from REST. Authentication refresh and WebSocket expiration are handled.
5. High-risk events create alerts. Three or more accounts sharing a device within 24 hours can produce a candidate ring. Amounts are grouped by currency. Treat rings as leads requiring review.
6. Create a case from an alert or ring. The server snapshots its stored evidence. Assign an active workspace user, add notes, review linked alerts and record a decision. Export the case's evidence and audit history as JSON.
7. Confirmed/false-positive alert and linked case decisions become training labels. Optional API/CSV `is_fraud` values also provide labels.
8. Open Model Lab. Choose a synthetic or labelled workspace dataset and run any model family. Export metrics. Administrators can activate the saved model for subsequent transactions; historical scores are preserved. Restore the heuristic scorer at any time.
9. AI briefings use stored evidence and remain optional. A missing/failed provider returns usable structured evidence. Verify generated text against source records.

## CSV and exports

Download the complete CSV template from Live monitor or Model Lab. Required columns: `account_id, merchant_id, merchant_name, amount, device_id, ip_address, location`. Optional: `external_id, customer_id, currency, occurred_at, status, is_fraud`.

- Maximum 10 MB and 500 rows per upload. Oversized row-count files are rejected before ingestion; no silent truncation.
- Rows are validated, then ingested in event-time order. Missing timestamps use the ingestion time; timezone-naive timestamps are treated as UTC.
- Import results show imported, duplicate and rejected rows with row numbers/reasons. Other valid rows can succeed when some rows fail.
- Supply stable external IDs for safe retry; otherwise each import creates new transaction IDs.
- CSV export starts at the selected page and returns up to 500 matching transactions. Download subsequent pages as needed. Spreadsheet formula-like cells are escaped.
- A dataset filename does not establish authenticity; imported data remains user-provided evidence.

## Runtime and cost limits

The current Railway service has one replica. WebSockets and simulation scheduling are process-local; use **one Uvicorn worker / one replica** until a shared broker and task scheduler are added. PostgreSQL workspace row locks serialize ingestion and model activation; an in-process lock also protects local SQLite.

Simulation is opt-in, workspace-specific, uses unique event IDs after restarts, and stops after 500 events per run. It pauses/stops explicitly and shuts down on process exit. A restart does not resume simulation automatically. Requested 1/5/10 events-per-second is a pacing target; database and explanation time reduce actual throughput.

Model training is one job per process, at most 10,000 requested events, with one numerical thread. It executes in a worker thread and remains request-bound: reload/restart during a run can lose that run's response; completed runs are persisted. Production-scale async queues, distributed scheduling and heavy TGN/TGAT training are outside this deployment.

## Optional recovery email

Existing OpenRouter variables are unchanged. Password recovery additionally supports `SMTP_HOST`, `SMTP_PORT` (587), `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_SENDER`. STARTTLS is required; reset links use `FRONTEND_URL`. No email is sent unless SMTP is configured and a recovery request is submitted. Links are hashed at rest, expire after 15 minutes and are single-use. Without SMTP, the screen explicitly directs users to administrator recovery. Auth request throttling is process-local.

## Verification

Run from the repository root:

```sh
python -m venv .venv
.venv/bin/pip install -r backend/requirements.txt
DATABASE_URL=sqlite+aiosqlite:///./verification.db .venv/bin/python -m pytest -q backend/app/tests
cd frontend
npm ci
npm run test
npm run lint
npm run build
```

Regression coverage includes causal and simultaneous event handling, duplicate/conflicting/concurrent ingestion, partial imports, source-aware analytics, workspace access/assignment validation, immutable case snapshots, audit exports, analyst labels, all four executed model families, JSON artifact round trips, activation/inference/fallback, AI outage handling, refresh replay, disabled users, password reset replay, workspace-specific simulation, WebSocket heartbeat pacing and migration preservation of legacy data.
