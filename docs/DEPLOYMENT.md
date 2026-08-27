# Deployment

## Neon

Create a Neon database, copy its pooled TLS URL, use the `postgresql+asyncpg` scheme, and store it as Railway `DATABASE_URL`. Do not expose this value to Vite. Run Alembic during backend startup.

## Railway backend

1. Import the repository and choose `backend` as Root Directory.
2. The Dockerfile installs `requirements.txt`, runs `alembic upgrade head`, and starts `uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}`.
3. Set `DATABASE_URL`, strong separate JWT secrets, `FRONTEND_URL`, `DEMO_SEED=false`, simulation policy, thresholds, and optional provider values.
4. Confirm `GET /health` and the OpenAPI document.
5. Use the Railway `https://` hostname for REST and its `wss://` equivalent for the WebSocket.

## Vercel frontend

1. Choose `frontend` as Root Directory and Vite as framework.
2. Set `VITE_API_URL=https://<railway>/api/v1`.
3. Set `VITE_WS_URL=wss://<railway>/api/v1/ws`.
4. Deploy, then set the final Vercel origin as Railway `FRONTEND_URL` and redeploy the backend.

`vercel.json` rewrites client-side routes to `index.html`.

## Docker Compose

`docker compose up --build` builds the separate frontend and backend images. Neon remains external by design. The local SQLite default is useful outside Docker; for Compose persistence, set an explicit SQLite file under the mounted `/app/data` volume or use Neon.

## Production hardening checklist

- Disable demo seed and rotate all default secrets/credentials.
- Configure Railway/Vercel origins exactly; never use wildcard credentialed CORS.
- Add an email provider and signed, one-time password-reset tokens.
- Add Redis/NATS WebSocket fan-out and a durable job queue for multi-replica operation.
- Add object storage plus malware/content inspection for large data imports.
- Add edge rate limiting/WAF, structured log export, tracing, backups, and alerting.
- Calibrate thresholds and models on governed institution-specific data before operational use.

