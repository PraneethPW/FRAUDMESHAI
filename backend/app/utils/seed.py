import asyncio
from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.core.database import SessionLocal, init_db
from app.core.security import hash_password
from app.models.domain import Alert, Case, CaseAlert, ModelVersion, Role, User, Workspace
from app.schemas.domain import TransactionCreate
from app.services.transactions import ingest_transaction


async def seed() -> None:
    await init_db()
    async with SessionLocal() as db:
        existing = await db.scalar(select(Workspace.id).where(Workspace.slug == "fraudmesh-demo"))
        if existing:
            print("Demo workspace already seeded")
            return
        workspace = Workspace(name="FraudMesh Demo Operations", slug="fraudmesh-demo")
        db.add(workspace)
        await db.flush()
        credentials = [
            ("admin@fraudmesh.dev", "Avery Chen", Role.ADMIN),
            ("analyst@fraudmesh.dev", "Maya Rao", Role.ANALYST),
            ("analyst2@fraudmesh.dev", "Noah Williams", Role.ANALYST),
            ("investigator@fraudmesh.dev", "Zara Khan", Role.INVESTIGATOR),
        ]
        users = []
        for email, name, role in credentials:
            user = User(workspace_id=workspace.id, email=email, full_name=name, role=role, password_hash=hash_password("FraudMesh!2026"))
            db.add(user)
            users.append(user)
        db.add(ModelVersion(name="Temporal Graph Ensemble", version="1.0.0-demo", model_type="TEMPORAL_GNN", active=True, config={"time_decay": .82, "window_hours": 24}))
        await db.commit()
        merchants = [("M-104", "Northstar Electronics"), ("M-221", "Orbit Travel"), ("M-390", "Meridian Market"), ("M-088", "Atlas Digital")]
        for index in range(36):
            coordinated = index in {6, 7, 8, 19, 20, 21}
            account = f"ACC-{701 + index % 3}" if coordinated else f"ACC-{301 + index % 14}"
            merchant_id, merchant = merchants[index % len(merchants)]
            payload = TransactionCreate(
                external_id=f"DEMO-{index + 1:06d}", account_id=account, customer_id=f"CUS-{account[-3:]}", merchant_id=merchant_id, merchant_name=merchant,
                amount=6200 + index * 37 if coordinated else 45 + (index * 179) % 2800, device_id="DEV-X104" if coordinated else f"DEV-{310 + index % 11}",
                ip_address="185.71.67.44" if coordinated else f"10.24.{index % 5}.{20 + index}", location="Dubai, AE" if coordinated else ["Mumbai, IN", "Bengaluru, IN", "Delhi, IN"][index % 3],
                occurred_at=datetime.now(UTC) - timedelta(minutes=(36 - index) * 8), source="SIMULATION")
            await ingest_transaction(db, workspace.id, payload)
        first_alert = (await db.execute(select(Alert).where(Alert.workspace_id == workspace.id))).scalars().first()
        if first_alert:
            case = Case(workspace_id=workspace.id, title="Coordinated device cluster DEV-X104", severity="HIGH", assigned_to=users[1].id, created_by=users[0].id, evidence={"alert_id": first_alert.id, "shared_device": "DEV-X104"})
            db.add(case)
            await db.flush()
            db.add(CaseAlert(case_id=case.id, alert_id=first_alert.id))
            await db.commit()
        print("Seed complete. Login: analyst@fraudmesh.dev / FraudMesh!2026")


if __name__ == "__main__":
    asyncio.run(seed())
