# FraudMesh XAI backend

FastAPI service for workspace-scoped authentication, persisted transaction ingestion, time-aware graph scoring, WebSocket simulation, XAI alerts, fraud rings, cases, executed model evaluation, grounded AI summaries, notifications, and audits.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m app.utils.seed
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

Install `requirements-gnn.txt` for the optional PyTorch and PyTorch Geometric research environment. Production configuration is documented in the root README.
