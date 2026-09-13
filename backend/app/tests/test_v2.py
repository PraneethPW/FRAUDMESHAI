import asyncio
import csv
import io
import uuid
from datetime import UTC, datetime, timedelta
import numpy as np
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from app.main import app
from app.core.database import SessionLocal
from app.models.domain import Transaction, GraphNode, ModelArtifact, TransactionLabel
from app.ml.baselines.training import train_model, synthetic_events
from app.ml.graph.context import encode_dataset, encode, load_groups, record
from app.ml.inference.predict import predict
from app.tests.test_workflows import register


def payload(i=0, **kw):
    return {
        "external_id": f"V2-{uuid.uuid4().hex[:12]}",
        "account_id": f"A-{i}",
        "merchant_id": "M-1",
        "merchant_name": "Test merchant",
        "amount": 8900,
        "currency": "USD",
        "device_id": "shared-device",
        "ip_address": "198.51.100.1",
        "location": "London",
        "occurred_at": (datetime(2026, 9, 1, 2, tzinfo=UTC) + timedelta(seconds=i * 20)).isoformat(),
        **kw,
    }


def test_idempotency_conflicts_causal_scoring_and_graph():
    with TestClient(app) as c:
        _, h = register(c)
        future = payload(3)
        assert c.post("/api/v1/transactions", headers=h, json=future).status_code == 201
        early = payload(0)
        r = c.post("/api/v1/transactions", headers=h, json=early)
        assert r.status_code == 201, r.text
        tx = r.json()
        details = c.get(f'/api/v1/transactions/{tx["id"]}', headers=h).json()
        assert details["features"]["device_sharing_count"] == 0
        assert details["features"]["ip_sharing_count"] == 0
        assert details["evidence"]["neighbors"] == []
        repeated = c.post("/api/v1/transactions", headers=h, json=early)
        assert repeated.status_code == 201 and repeated.json()["id"] == tx["id"]
        assert c.post("/api/v1/transactions", headers=h, json={**early, "amount": 10}).status_code == 409
        assert len(c.get("/api/v1/transactions", headers=h).json()) == 2
        graph = c.get(f'/api/v1/graph/transaction/{tx["id"]}', headers=h).json()
        assert {"ACCOUNT", "DEVICE", "IP", "MERCHANT", "LOCATION", "TRANSACTION"} <= {n["data"]["type"] for n in graph["nodes"]}
        assert c.post("/api/v1/transactions", headers=h, json=payload(amount=-1)).status_code == 422
        assert c.post("/api/v1/transactions", headers=h, json=payload(account_id=" ")).status_code == 422


def test_csv_reports_order_labels_size_and_export():
    with TestClient(app) as c:
        _, h = register(c)
        rows = [payload(2, is_fraud="1"), payload(0, is_fraud="0"), payload(1, amount="bad", is_fraud="0")]
        buffer = io.StringIO()
        writer = csv.DictWriter(buffer, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
        res = c.post("/api/v1/datasets/upload", headers=h, files={"file": ("example.csv", buffer.getvalue(), "text/csv")})
        assert res.status_code == 200, res.text
        assert res.json()["imported"] == 2 and res.json()["failed_count"] == 1
        transactions = c.get("/api/v1/transactions", headers=h).json()
        older = min(transactions, key=lambda t: t["occurred_at"])
        assert c.get(f'/api/v1/transactions/{older["id"]}', headers=h).json()["features"]["device_sharing_count"] == 0
        again = c.post("/api/v1/datasets/upload", headers=h, files={"file": ("example.csv", buffer.getvalue(), "text/csv")}).json()
        assert again["duplicates"] == 2 and again["imported"] == 0
        assert c.get("/api/v1/datasets/template", headers=h).status_code == 200
        assert c.get("/api/v1/transactions/export", headers=h).headers["content-type"].startswith("text/csv")
        many = buffer.getvalue().splitlines()[0] + "\n" + ("\n".join([buffer.getvalue().splitlines()[1]] * 501))
        assert c.post("/api/v1/datasets/upload", headers=h, files={"file": ("too-many.csv", many, "text/csv")}).status_code == 422
        assert len(c.get("/api/v1/transactions", headers=h).json()) == 2


def test_workspace_isolation_assignments_cases_and_research_labels():
    with TestClient(app) as c:
        one, h = register(c)
        two, h2 = register(c)
        for i in range(5):
            assert c.post("/api/v1/transactions", headers=h, json=payload(i)).status_code == 201
        alerts = c.get("/api/v1/alerts", headers=h).json()
        assert alerts
        alert = alerts[0]
        assert c.get("/api/v1/alerts", headers=h2).json() == []
        assert c.get(f'/api/v1/alerts/{alert["id"]}', headers=h2).status_code == 404
        assert c.patch(f'/api/v1/alerts/{alert["id"]}', headers=h, json={"assigned_to": two["user"]["id"]}).status_code == 422
        res = c.post(
            "/api/v1/cases",
            headers=h,
            json={"title": "Evidence case", "alert_ids": [alert["id"], alert["id"]], "evidence": {"risk_score": 0}},
        )
        assert res.status_code == 201, res.text
        case = res.json()
        snap = case["evidence"]["alerts"][0]
        assert snap["risk_score"] == alert["risk_score"]
        assert c.patch(f'/api/v1/cases/{case["id"]}', headers=h, json={"assigned_to": two["user"]["id"]}).status_code == 422
        assert c.patch(f'/api/v1/cases/{case["id"]}', headers=h, json={"assigned_to": one["user"]["id"]}).status_code == 200
        assert c.patch(f'/api/v1/cases/{case["id"]}', headers=h, json={"assigned_to": None}).json()["assigned_to"] is None
        assert (
            c.patch(
                f'/api/v1/cases/{case["id"]}', headers=h, json={"status": "FALSE_POSITIVE", "decision": "Verified legitimate activity"}
            ).status_code
            == 200
        )
        assert c.get(f'/api/v1/alerts/{alert["id"]}', headers=h).json()["status"] == "FALSE_POSITIVE"
        assert c.post(f'/api/v1/cases/{case["id"]}/notes', headers=h, json={"body": "Reviewed source evidence."}).status_code == 201
        exported = c.get(f'/api/v1/cases/{case["id"]}/export', headers=h).json()
        assert len(exported["timeline"]) >= 4 and len(exported["notes"]) == 1
        assert exported["evidence"]["alerts"][0] == snap
        assert c.get(f'/api/v1/cases/{case["id"]}/export', headers=h2).status_code == 404
        assert c.get("/api/v1/users/search?q=Evidence", headers=h).json()
        assert c.get("/api/v1/users/search?q=Evidence", headers=h2).json() == []
        rings = c.get("/api/v1/fraud-rings", headers=h).json()
        assert rings
        assert len([m for m in rings[0]["members"] if m["type"] == "ACCOUNT"]) == 5
        overview = c.get("/api/v1/dashboard/overview", headers=h).json()
        assert overview["metrics"]["transactions_processed"] == 5 and overview["mode"] == "USER PROVIDED DATA"


@pytest.mark.parametrize("model_type", ["LOGISTIC_REGRESSION", "XGBOOST", "STATIC_GNN", "TEMPORAL_GNN"])
def test_training_chronology_artifact_and_graph_dependency(model_type):
    import json

    metrics, artifact = train_model(model_type, 300)
    assert metrics["split"] == {"train": 180, "validation": 60, "test": 60}
    assert metrics["train_end"] < metrics["test_start"]
    assert sum(metrics["confusion_matrix"].values()) == 60
    x, m = encode_dataset(synthetic_events(300), temporal=model_type != "STATIC_GNN")
    restored = json.loads(json.dumps(artifact))
    np.testing.assert_allclose(predict(artifact, x, m), predict(restored, x, m))
    if model_type.endswith("GNN"):
        assert np.mean(np.abs(predict(artifact, x, m) - predict(artifact, x, np.zeros_like(m)))) > 1e-5
    # Labels must never change any input tensor.
    rows = synthetic_events(300)
    for row in rows:
        row["is_fraud"] = not row["is_fraud"]
    xx, mm = encode_dataset(rows, temporal=model_type != "STATIC_GNN")
    np.testing.assert_array_equal(x, xx)
    np.testing.assert_array_equal(m, mm)


def test_model_activation_inference_and_workspace_permissions():
    with TestClient(app) as c:
        _, h = register(c)
        _, h2 = register(c)
        run = c.post("/api/v1/models/train", headers=h, json={"model_type": "TEMPORAL_GNN", "samples": 300})
        assert run.status_code == 201, run.text
        rid = run.json()["id"]
        assert c.post(f"/api/v1/models/runs/{rid}/activate", headers=h2).status_code == 404
        assert c.post(f"/api/v1/models/runs/{rid}/activate", headers=h).status_code == 200
        tx = c.post("/api/v1/transactions", headers=h, json=payload(0)).json()
        detail = c.get(f'/api/v1/transactions/{tx["id"]}', headers=h).json()
        assert detail["evidence"]["model_run_id"] == rid and detail["evidence"]["training_source"] == "SYNTHETIC"
        assert detail["evidence"]["explanation_method"].startswith("feature mean")
        assert c.post("/api/v1/models/deactivate", headers=h).status_code == 200
        tx = c.post("/api/v1/transactions", headers=h, json=payload(1)).json()
        assert c.get(f'/api/v1/transactions/{tx["id"]}', headers=h).json()["model_version"] == "time-aware-graph-ensemble-v2"
        assert (
            c.post(
                "/api/v1/models/train", headers=h, json={"model_type": "TEMPORAL_GNN", "dataset": "WORKSPACE", "samples": 300}
            ).status_code
            == 422
        )


def test_disabled_users_refresh_notifications_and_simulation_isolation():
    with TestClient(app) as c:
        one, h = register(c)
        _, h2 = register(c)
        email = f"user-{uuid.uuid4().hex[:8]}@fraudmesh.dev"
        user = c.post(
            "/api/v1/admin/users",
            headers=h,
            json={"email": email, "full_name": "New Analyst", "password": "SecurePass!2026", "role": "ANALYST"},
        ).json()
        login = c.post("/api/v1/auth/login", json={"email": email, "password": "SecurePass!2026"}).json()
        analyst = {"Authorization": f'Bearer {login["access_token"]}'}
        assert (
            c.post(
                "/api/v1/admin/users",
                headers=analyst,
                json={"email": "no@example.com", "full_name": "No User", "password": "SecurePass!2026"},
            ).status_code
            == 403
        )
        assert c.patch(f'/api/v1/admin/users/{user["id"]}', headers=h, json={"is_active": False}).status_code == 200
        assert c.get("/api/v1/users/me", headers=analyst).status_code == 401
        assert c.post("/api/v1/auth/login", json={"email": email, "password": "SecurePass!2026"}).status_code == 401
        assert c.post("/api/v1/auth/refresh", json={"refresh_token": login["refresh_token"]}).status_code == 401
        with pytest.raises(Exception):
            with c.websocket_connect(f'/api/v1/ws?token={login["access_token"]}'):
                pass
        rotated = c.post("/api/v1/auth/refresh", json={"refresh_token": one["refresh_token"]})
        assert rotated.status_code == 200
        assert c.post("/api/v1/auth/refresh", json={"refresh_token": one["refresh_token"]}).status_code == 401
        assert c.post("/api/v1/simulation/start", headers=h, json={"speed": 1}).status_code == 200
        assert c.get("/api/v1/simulation/status", headers=h2).json()["state"] == "STOPPED"
        assert c.post("/api/v1/simulation/stop", headers=h2).status_code == 200
        assert c.get("/api/v1/simulation/status", headers=h).json()["state"] == "RUNNING"
        c.post("/api/v1/simulation/stop", headers=h)


def test_ai_provider_failure_preserves_evidence(monkeypatch):
    class Broken:
        name = "test"

        async def summarize(self, *args):
            raise RuntimeError("provider unavailable")

    monkeypatch.setattr("app.api.assistant.get_provider", lambda: Broken())
    with TestClient(app) as c:
        _, h = register(c)
        for i in range(5):
            c.post("/api/v1/transactions", headers=h, json=payload(i))
        alert = c.get("/api/v1/alerts", headers=h).json()[0]
        r = c.post("/api/v1/assistant/chat", headers=h, json={"alert_id": alert["id"]})
        assert r.status_code == 200 and r.json()["available"] is False
        assert r.json()["evidence"]["risk_score"] == alert["risk_score"]


def test_simultaneous_ingestion_has_one_event_and_no_duplicate_graph():
    from concurrent.futures import ThreadPoolExecutor
    with TestClient(app) as c:
        _,h=register(c); event=payload(0)
        with ThreadPoolExecutor(max_workers=3) as pool:
            results=list(pool.map(lambda _:c.post('/api/v1/transactions',headers=h,json=event),range(3)))
        assert all(r.status_code==201 for r in results),[r.text for r in results]
        assert len({r.json()['id'] for r in results})==1
        assert len(c.get('/api/v1/transactions',headers=h).json())==1


def test_password_reset_single_use_and_refresh_revocation(monkeypatch):
    from app.core.config import settings
    sent=[]
    monkeypatch.setattr(settings,'smtp_host','test.invalid')
    monkeypatch.setattr(settings,'smtp_sender','test@fraudmesh.dev')
    monkeypatch.setattr('app.services.mail.send_reset',lambda email,token:sent.append((email,token)))
    with TestClient(app) as c:
        tokens,h=register(c)
        r=c.post('/api/v1/auth/forgot-password',json={'email':tokens['user']['email']})
        assert r.status_code==200 and len(sent)==1
        data={'token':sent[0][1],'new_password':'ReplacementPass!2026'}
        assert c.post('/api/v1/auth/reset-password',json=data).status_code==200
        assert c.post('/api/v1/auth/reset-password',json=data).status_code==400
        assert c.post('/api/v1/auth/refresh',json={'refresh_token':tokens['refresh_token']}).status_code==401
        assert c.post('/api/v1/auth/login',json={'email':tokens['user']['email'],'password':data['new_password']}).status_code==200


def test_upgrade_preserves_legacy_records(tmp_path):
    import os
    import subprocess
    import sys
    from pathlib import Path
    from sqlalchemy import create_engine,text,inspect
    from app.core.database import Base
    db_path=tmp_path/'legacy.db'
    engine=create_engine(f'sqlite:///{db_path}')
    tables=[t for t in Base.metadata.sorted_tables if t.name not in {'model_artifacts','transaction_labels','password_resets'}]
    Base.metadata.create_all(engine,tables=tables)
    with engine.begin() as db:
        db.execute(text('CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL PRIMARY KEY)'))
        db.execute(text("INSERT INTO alembic_version VALUES ('20260827_0001')"))
        from app.models.domain import Workspace
        db.execute(Workspace.__table__.insert().values(id='legacy-workspace',name='Preserve Me',slug='preserve-me'))
    backend=Path(__file__).resolve().parents[2]
    result=subprocess.run([sys.executable,'-m','alembic','upgrade','head'],cwd=backend,env={**os.environ,'DATABASE_URL':f'sqlite+aiosqlite:///{db_path}'},capture_output=True,text=True)
    assert result.returncode==0,result.stderr
    with engine.connect() as db:
        assert db.scalar(text("SELECT name FROM workspaces WHERE id='legacy-workspace'"))=='Preserve Me'
        assert db.scalar(text('SELECT version_num FROM alembic_version'))=='20260913_0002'
    assert {'model_artifacts','transaction_labels','password_resets'}<=set(inspect(engine).get_table_names())
    engine.dispose()


def test_equal_timestamp_training_serving_neighborhoods_match():
    rows=synthetic_events(80)
    for row in rows[35:70]: row['occurred_at']=rows[35]['occurred_at']
    x,m=encode_dataset(rows)
    for i in (35,36,50,69,70):
        from app.ml.graph.context import RELATIONS,utc
        event=rows[i]
        groups=[[r for r in rows[:i] if r[key]==event[key] and r['currency']==event['currency'] and utc(r['occurred_at'])<utc(event['occurred_at'])][-32:] for key in RELATIONS]
        expected_x,expected_m,_=encode(event,groups)
        np.testing.assert_allclose(x[i],expected_x);np.testing.assert_allclose(m[i],expected_m)


def test_websocket_pong_does_not_create_a_busy_heartbeat_loop(monkeypatch):
    import time
    monkeypatch.setattr('app.api.websocket.HEARTBEAT_SECONDS',.04)
    with TestClient(app) as c:
        tokens,h=register(c)
        with c.websocket_connect(f'/api/v1/ws?token={tokens["access_token"]}') as ws:
            assert ws.receive_json()['event']=='system.status'
            assert ws.receive_json()['event']=='heartbeat'
            started=time.monotonic();ws.send_text('pong')
            assert ws.receive_json()['event']=='heartbeat'
            assert time.monotonic()-started>=.03
