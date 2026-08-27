# Database

Neon PostgreSQL is the production system of record. SQLite is a development/test fallback only.

## Core domains

| Domain | Tables |
|---|---|
| Identity | `workspaces`, `users`, `refresh_tokens` |
| Financial entities | `customers`, `accounts`, `merchants`, `devices`, `ip_addresses`, `locations` |
| Ingestion and inference | `transactions`, `transaction_features`, `fraud_scores` |
| Graph | `graph_nodes`, `graph_edges` |
| Detection | `alerts`, `alert_evidence`, `fraud_rings`, `fraud_ring_members` |
| Investigation | `cases`, `case_alerts`, `case_transactions`, `case_entities`, `case_notes` |
| Model operations | `model_versions`, `training_runs`, `model_metrics` |
| Governance | `ai_summaries`, `audit_logs`, `notifications` |

UUID-compatible string primary keys keep the same identifiers across SQLite tests and PostgreSQL. Workspace-owned tables have an indexed `workspace_id`. Natural external identifiers use workspace-scoped unique constraints where relevant. Graph edges preserve `occurred_at`, `weight`, edge type, and transaction properties.

## Neon connection

Use a pooled connection string with TLS, for example:

```env
DATABASE_URL=postgresql+asyncpg://user:password@ep-name-pooler.region.aws.neon.tech/neondb?ssl=require
```

The configuration normalizes `postgres://` and plain `postgresql://` to the SQLAlchemy asyncpg dialect. Run `python -m alembic upgrade head` for every deployment. The first migration constructs the complete SQLAlchemy metadata; future schema changes should use Alembic revisions generated and reviewed normally.

## Isolation rule

Every resource lookup combines its identifier with the authenticated workspace. Cross-workspace alert IDs cannot be attached to a case. Admin queries remain workspace-scoped. This is enforced server-side and never delegated to frontend filtering.

