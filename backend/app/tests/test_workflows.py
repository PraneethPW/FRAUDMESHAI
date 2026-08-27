import time
import uuid
from datetime import UTC, datetime

from fastapi.testclient import TestClient

from app.main import app
from app.core.config import Settings
from app.ml.features import build_features


def register(client: TestClient) -> tuple[dict, dict]:
    response = client.post("/api/v1/auth/register", json={"email": f"qa-{uuid.uuid4().hex[:8]}@fraudmesh.dev", "full_name": "QA Analyst", "password": "SecurePass!2026", "workspace_name": f"QA {uuid.uuid4().hex[:6]}"})
    assert response.status_code == 201, response.text
    body = response.json()
    return body, {"Authorization": f"Bearer {body['access_token']}"}


def test_complete_investigation_workflow() -> None:
    with TestClient(app) as client:
        tokens, headers = register(client)
        me = client.get("/api/v1/users/me", headers=headers)
        assert me.status_code == 200
        assert me.json()["role"] == "ADMIN"

        last_tx = None
        for i in range(3):
            response = client.post("/api/v1/transactions", headers=headers, json={"external_id": f"QA-TX-{uuid.uuid4().hex[:8]}", "account_id": f"QA-ACC-{i}", "customer_id": f"QA-CUS-{i}", "merchant_id": "QA-M-1", "merchant_name": "QA Merchant", "amount": 8800 + i * 200, "device_id": "QA-SHARED-DEVICE", "ip_address": "198.51.100.44", "location": "Dubai, AE", "occurred_at": datetime.now(UTC).isoformat()})
            assert response.status_code == 201, response.text
            last_tx = response.json()
        assert last_tx and 0 <= last_tx["risk_score"] <= 1

        detail = client.get(f"/api/v1/transactions/{last_tx['id']}", headers=headers)
        assert detail.status_code == 200
        assert detail.json()["features"]["device_sharing_count"] >= 2

        graph = client.get("/api/v1/graph", headers=headers)
        assert graph.status_code == 200
        assert graph.json()["meta"]["nodes"] >= 6
        rings = client.get("/api/v1/fraud-rings", headers=headers)
        assert rings.status_code == 200

        alerts = client.get("/api/v1/alerts", headers=headers).json()
        assert alerts
        alert = alerts[0]
        updated = client.patch(f"/api/v1/alerts/{alert['id']}", headers=headers, json={"status": "UNDER_REVIEW"})
        assert updated.status_code == 200

        case = client.post("/api/v1/cases", headers=headers, json={"title": "QA coordinated infrastructure review", "severity": "HIGH", "alert_ids": [alert["id"]]})
        assert case.status_code == 201, case.text
        case_id = case.json()["id"]
        assert client.post(f"/api/v1/cases/{case_id}/notes", headers=headers, json={"body": "Verified shared device evidence."}).status_code == 201
        assert client.patch(f"/api/v1/cases/{case_id}", headers=headers, json={"status": "INVESTIGATING"}).status_code == 200

        fallback = client.post("/api/v1/assistant/summarize-alert", headers=headers, json={"alert_id": alert["id"]})
        assert fallback.status_code == 200
        assert fallback.json()["available"] is False

        run = client.post("/api/v1/models/train", headers=headers, json={"model_type": "LOGISTIC_REGRESSION", "samples": 300})
        assert run.status_code == 201, run.text
        assert run.json()["metrics"]["roc_auc"] > 0

        refreshed = client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
        assert refreshed.status_code == 200
        assert client.post("/api/v1/auth/logout", headers={"Authorization": f"Bearer {refreshed.json()['access_token']}"}, json={"refresh_token": refreshed.json()["refresh_token"]}).status_code == 204


def test_websocket_and_simulator_controls() -> None:
    with TestClient(app) as client:
        tokens, headers = register(client)
        with client.websocket_connect(f"/api/v1/ws?token={tokens['access_token']}") as socket:
            assert socket.receive_json()["event"] == "system.status"
        assert client.post("/api/v1/simulation/start", headers=headers, json={"speed": 10}).status_code == 200
        time.sleep(.2)
        assert client.post("/api/v1/simulation/pause", headers=headers).json()["state"] == "PAUSED"
        assert client.post("/api/v1/simulation/stop", headers=headers).json()["state"] == "STOPPED"


def test_feature_engineering_is_data_driven() -> None:
    features = build_features(amount=9000, occurred_at=datetime.now(UTC), device_accounts=4, ip_accounts=3, recent_count=7, merchant_frequency=8, new_device=True, location_changed=True, seconds_since_previous=22)
    assert features["device_sharing_count"] == 3
    assert features["velocity"] > 0


def test_development_cors_accepts_vite_fallback_ports() -> None:
    with TestClient(app) as client:
        response = client.options(
            "/api/v1/auth/login",
            headers={
                "Origin": "http://localhost:5174",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type",
            },
        )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5174"


def test_neon_url_is_normalized_for_asyncpg() -> None:
    configured = Settings(
        database_url="postgresql://user:pass@example.neon.tech/db?sslmode=require&channel_binding=require"
    )
    assert configured.database_url.startswith("postgresql+asyncpg://")
    assert "ssl=require" in configured.database_url
    assert "sslmode" not in configured.database_url
    assert "channel_binding" not in configured.database_url
