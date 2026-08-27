# Architecture

## Runtime flow

```text
Transaction API / CSV / Simulator
  → SQL transaction record
  → rolling and temporal feature engineering
  → transparent time-aware graph ensemble
  → fraud score + immutable evidence snapshot
  → relational graph nodes and timestamped edges
  → alert and optional ring creation
  → WebSocket event fan-out
  → analyst case, decision, and audit history
```

The React frontend is a separate Vite application. It communicates only through the versioned REST and WebSocket contracts. TanStack Query owns server state, Zustand holds the authenticated session, Cytoscape renders graph responses, and Recharts renders persisted analytics/model metrics.

The FastAPI backend is split into route, schema, persistence, service, ML, AI, and WebSocket layers. Domain rows are always filtered by the authenticated `workspace_id`. Admin is a role capability inside a workspace; it is not permission to read another workspace.

## Trust boundaries

- Passwords are Argon2 hashes; plaintext passwords are never stored.
- Access and refresh JWTs use different secrets and lifetimes.
- Refresh tokens are stored only as SHA-256 digests, rotated on refresh, and revoked on logout.
- The WebSocket validates an access token before accepting the connection.
- CSV files are extension-, size-, UTF-8-, schema-, and Pydantic-validated.
- SQLAlchemy parameterizes persistence access.
- AI providers receive a stored structured evidence snapshot, not unrestricted database access.
- The optional assistant cannot change scores, alerts, cases, or decisions.

## Scalability boundary

For a production scale-out, move simulation and training jobs to a durable queue, replace the in-memory WebSocket manager with Redis/NATS fan-out, store large datasets in object storage, add an async job table, and use a dedicated model-serving process. The API and UI contracts already isolate these concerns.

