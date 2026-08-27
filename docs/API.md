# API

Base path: `/api/v1`. Interactive OpenAPI documentation: `/docs`.

## Authentication

| Method | Path | Purpose |
|---|---|---|
| POST | `/auth/register` | Create workspace and first admin |
| POST | `/auth/login` | Issue access + refresh tokens |
| POST | `/auth/refresh` | Rotate refresh token and issue a new pair |
| POST | `/auth/logout` | Revoke refresh token |
| POST | `/auth/forgot-password` | Provider-ready generic recovery response |
| GET | `/users/me` | Current user |

Use `Authorization: Bearer <access_token>` for protected REST calls. The WebSocket uses `/ws?token=<access_token>` and immediately returns `system.status` when accepted.

## Product endpoints

- Transactions: `POST/GET /transactions`, `GET /transactions/{id}`, `POST /datasets/upload`.
- Dashboard: `GET /dashboard/overview`.
- Alerts: `GET /alerts`, `GET/PATCH /alerts/{id}`.
- Graph: `GET /graph`, `GET /graph/node/{id}`, `GET /graph/transaction/{id}`.
- Rings: `GET /fraud-rings`, `GET /fraud-rings/{id}`.
- Cases: `POST/GET /cases`, `GET/PATCH /cases/{id}`, `POST /cases/{id}/notes`.
- Models: `POST /models/train`, `GET /models/runs`, `GET /models/metrics`.
- Assistant: `POST /assistant/summarize-alert`, `/summarize-case`, `/chat`.
- Simulation: `POST /simulation/start|pause|stop`, `GET /simulation/status`.
- Administration: `GET /admin/overview` (ADMIN only).
- Governance: `GET /users/notifications`, `GET /users/audit`.

## WebSocket events

`transaction.created`, `fraud.alert.created`, `fraud.alert.updated`, `case.updated`, `model.training.completed`, and `system.status`. The frontend reconnects automatically and invalidates related queries where needed.

Error responses use FastAPI/Pydantic status codes and a useful `detail`. The UI distinguishes offline, unauthorized, invalid dataset, provider unavailable, and training failure states.

