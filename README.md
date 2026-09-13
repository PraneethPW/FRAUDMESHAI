# FraudMesh XAI

**FraudMesh XAI: An Explainable Temporal Graph Neural Network Framework for Real-Time Coordinated Financial Fraud Detection**

FraudMesh XAI is a working full-stack research and investigation platform that treats financial activity as a changing network, rather than a collection of isolated transactions. It persists transactions, builds a heterogeneous graph, generates time-aware and relationship-aware features, computes a fraud score, creates explainable alerts and fraud rings, streams events over WebSockets, and carries verified evidence into an auditable investigation case.

All bundled events and example metrics are labelled as simulated. FraudMesh never presents demo data as live banking activity, and its optional AI assistant never makes the fraud decision.

## Version 2

The functional upgrade preserves the deployed visual theme and service layout. See [v2 operating and upgrade guide](docs/V2_UPGRADE.md) for transaction entry/import, saved-model activation, case evidence/exports, account administration and deployment compatibility.

## Architecture

```text
React + TypeScript + Vite
        │ REST + JWT + WebSocket
        ▼
FastAPI application
        ├── Auth / workspace authorization
        ├── Transaction ingestion + simulator
        ├── Feature engineering + time-aware score
        ├── Relational graph + NetworkX communities
        ├── Alerts / evidence / fraud rings
        ├── Cases / notes / audit history
        ├── Executed model evaluation lab
        └── Grounded AI provider abstraction
        │
        ▼
Neon PostgreSQL in production
SQLite fallback for zero-configuration local development
```

The frontend and backend are completely separated. PostgreSQL is the system of record; graph nodes and timestamped edges are stored relationally and projected into NetworkX or ML-ready structures at analysis time. See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Features

- Argon2 authentication, JWT access tokens, rotating stored refresh tokens, logout revocation, roles, and workspace isolation.
- Versioned `/api/v1` REST API and authenticated WebSocket channel.
- Persisted transaction ingestion, validated CSV imports, and a clearly marked synthetic simulation mode paced at 1, 5, or 10 events per second (up to 500 events per run).
- Data-driven temporal, behavioral, device-sharing, IP-sharing, velocity, amount, location, and graph-risk evidence.
- Heterogeneous graph explorer for customer, account, transaction, merchant, device, IP, and location nodes.
- Graph zoom, pan, drag, type/risk filtering, entity focus, neighborhood expansion, community detection, and suspicious-path highlighting.
- Persisted fraud alerts, structured XAI evidence, feature contribution charts, alert review states, fraud ring detection, and notifications.
- Investigation cases with alert linkage, evidence snapshots, assignments, notes, decisions, status transitions, and audit history.
- Executed Logistic Regression, XGBoost, static graph neural network, and time-decayed graph neural network evaluation.
- Optional OpenRouter or OpenAI-compatible grounded summaries with an explicit no-key fallback.
- Responsive cinematic landing page, mobile investigation console, command palette (`Ctrl + K`), reduced-motion support, and branded loading/empty/error states.

## Technology stack

Frontend: React 19, TypeScript strict mode, Vite, Tailwind CSS, Motion, GSAP + ScrollTrigger, Lenis, Three.js, React Three Fiber, Drei, Cytoscape.js, Recharts, TanStack Query, Zustand, React Hook Form, Zod, Axios, Lucide, and Sonner.

Backend: Python, FastAPI, Pydantic 2, SQLAlchemy 2 async, Alembic, asyncpg, PostgreSQL/Neon, Argon2, PyJWT, HTTPX, NumPy, Pandas, scikit-learn, XGBoost, NetworkX, and WebSockets. Optional research dependencies for PyTorch and PyTorch Geometric are in `backend/requirements-gnn.txt`.

## Folder structure

```text
FraudMesh-XAI/
├── frontend/                 React + TypeScript application
│   ├── src/components/       Shell, Three.js network, shared UI
│   ├── src/pages/            Landing and investigation routes
│   ├── src/lib/              API client and refresh handling
│   ├── src/store/            Auth session state
│   └── src/types/            Shared frontend contracts
├── backend/                  FastAPI + ML backend
│   ├── app/api/              Versioned route modules
│   ├── app/core/             Configuration, database, security
│   ├── app/models/           SQLAlchemy domain schema
│   ├── app/services/         Scoring, graph, simulation, audit
│   ├── app/ml/               Features, baselines, graph/temporal adapters
│   ├── app/ai/               OpenAI-compatible provider abstraction
│   ├── app/tests/            End-to-end API workflow tests
│   └── alembic/              Database migrations
├── docs/                     Architecture and operating guides
├── docker-compose.yml
└── README.md
```

## Environment setup

Copy `backend/.env.example` to `backend/.env` and `frontend/.env.example` to `frontend/.env`.

Required for a production deployment:

```env
# backend
DATABASE_URL=postgresql+asyncpg://USER:PASSWORD@HOST/DATABASE?ssl=require
JWT_SECRET=<at-least-32-random-bytes>
JWT_REFRESH_SECRET=<different-at-least-32-random-bytes>
FRONTEND_URL=https://your-vercel-project.vercel.app

# frontend
VITE_API_URL=https://your-railway-service.up.railway.app/api/v1
VITE_WS_URL=wss://your-railway-service.up.railway.app/api/v1/ws
```

Optional AI variables:

```env
OPENROUTER_API_KEY=
OPENROUTER_MODEL=
OPENAI_API_KEY=
OPENAI_MODEL=
```

The model name always comes from the environment. If no provider/key/model pair exists, the app displays: **AI Investigation Assistant unavailable. Core fraud detection remains operational.**

## Local development

Backend (PowerShell):

```powershell
cd C:\Users\prane\COHORT-HARKIRAT\FraudMesh-XAI\backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m app.utils.seed
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

Frontend (a second PowerShell window):

```powershell
cd C:\Users\prane\COHORT-HARKIRAT\FraudMesh-XAI\frontend
npm install
npm run dev
```

Open `http://localhost:5173`. API documentation is at `http://localhost:8000/docs` and health status at `http://localhost:8000/health`.

## Database migration and Neon setup

1. Create a Neon project and database.
2. Copy its pooled connection string. Keep TLS enabled and replace the scheme with `postgresql+asyncpg://` when necessary.
3. Set `DATABASE_URL` in `backend/.env` or the Railway environment.
4. From `backend`, run `.\.venv\Scripts\python.exe -m alembic upgrade head`.
5. Set `DEMO_SEED=false` in production. For a private demo workspace only, run `.\.venv\Scripts\python.exe -m app.utils.seed` once.

The application accepts pooled Neon strings and normalizes legacy `postgres://`/`postgresql://` schemes for async SQLAlchemy. See [docs/DATABASE.md](docs/DATABASE.md).

## Development demo credentials

These accounts are created only by the explicit development seed command. All use `FraudMesh!2026`:

| Role | Email |
|---|---|
| Admin | `admin@fraudmesh.dev` |
| Analyst | `analyst@fraudmesh.dev` |
| Analyst | `analyst2@fraudmesh.dev` |
| Investigator | `investigator@fraudmesh.dev` |

Never run the demo seed in a production workspace.

## Running simulation

Sign in as the demo analyst, open **Live monitor**, choose 1/5/10 events per second, and select **Start simulation**. The backend persists each simulated event, engineers features, updates the graph, scores it, creates high-risk alerts/rings, publishes WebSocket events, and updates the dashboard. Pause and Stop are functional. Every generated event has source `SIMULATION` and the UI marks the stream `SIMULATED DATA`.

## Model pipeline

Without an activated trained model, online scoring uses a transparent causal heuristic. Model Lab trains Logistic Regression, XGBoost, static mean-message-passing GNN and time-decayed mean-message-passing GNN models on deterministic synthetic motifs or labelled workspace transactions. All use chronological train/validation/test splits, train-only scaling and validation-selected thresholds. Metrics and portable model weights are persisted. Administrators can activate one model per workspace for incoming transactions or restore heuristic scoring.

The compact graph models perform learned message passing over prior account/device/IP/merchant event neighborhoods with CPU NumPy backpropagation. They are not full TGN memory/TGAT attention implementations. Explanations expose stored context and measured feature/relation perturbations. See [docs/ML_PIPELINE.md](docs/ML_PIPELINE.md).

## Testing and quality

```powershell
# backend
cd backend
$env:DATABASE_URL='sqlite+aiosqlite:///./test_fraudmesh.db'
.\.venv\Scripts\python.exe -m pytest -q

# frontend
cd frontend
npm run test
npm run lint
npm run build
```

Backend tests cover registration/login/refresh/logout, transaction scoring, feature generation, graph construction, alert/ring creation, case/note workflow, AI fallback, WebSocket authentication, simulation controls, and executed model metrics. Frontend tests cover protected routing, important risk UI, and useful API error language.

## Docker

Create `backend/.env`, then:

```powershell
docker compose up --build
```

The frontend is served at `http://localhost:5173`, the backend at `http://localhost:8000`, and Neon remains external. For a fully local zero-config run, keep the SQLite development URL.

## Vercel deployment

1. Import this repository into Vercel.
2. Set the Root Directory to `frontend` and Framework Preset to Vite.
3. Add `VITE_API_URL=https://<railway>/api/v1` and `VITE_WS_URL=wss://<railway>/api/v1/ws`.
4. Deploy. `frontend/vercel.json` provides SPA route rewriting.
5. Add the final Vercel origin as `FRONTEND_URL` on Railway and redeploy the backend.

## Railway deployment

1. Create a Railway service from the repository and set Root Directory to `backend`.
2. Railway detects `backend/Dockerfile` and `backend/railway.toml`.
3. Add the production backend environment variables, including Neon `DATABASE_URL`, secure JWT secrets, Vercel `FRONTEND_URL`, `DEMO_SEED=false`, and optional AI configuration.
4. Deploy. The container runs migrations and then starts Uvicorn on `${PORT:-8000}`.
5. Confirm `/health`, then configure the Railway HTTPS/WSS origin in Vercel.

See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md).

## Screenshots

Add finalized portfolio captures under `docs/screenshots/` after deploying the chosen production environment. Recommended shots: cinematic hero, overview, live monitor with a critical event, graph explorer, XAI alert detail, fraud ring, case timeline, and Model Lab metrics.

## Research and deployment boundaries

This is an executable research and investigation platform, not a certified banking detector. Actual transaction streams must be supplied through the authenticated API; bundled simulation does not connect to a bank. Synthetic evaluation does not establish real-world accuracy. Graph networks use one-layer mean message passing (temporal decay in the temporal variant), not full TGN/TGAT. Risk scores are not probability-calibrated, and perturbation evidence is not a causal explanation.

The current runtime uses one process/replica with bounded simulation and request-bound model training. Recovery email requires optional SMTP; AI summaries require a provider. [The operating guide](docs/V2_UPGRADE.md) documents limits and setup. Existing deployed data is preserved by additive migrations.

## Documentation

- [Architecture](docs/ARCHITECTURE.md)
- [Database](docs/DATABASE.md)
- [API](docs/API.md)
- [ML pipeline](docs/ML_PIPELINE.md)
- [Graph model](docs/GRAPH_MODEL.md)
- [Deployment](docs/DEPLOYMENT.md)
- [Demonstration flow](docs/DEMO_FLOW.md)
