import uuid
from datetime import UTC, datetime

from sqlalchemy import distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.domain import Alert, AlertEvidence, FraudRing, FraudRingMember, FraudScore, Notification, Transaction, TransactionFeature
from app.schemas.domain import TransactionCreate
from app.services.graph import update_graph
from app.services.scoring import score_transaction
from app.websocket.manager import manager


async def ingest_transaction(db: AsyncSession, workspace_id: str, payload: TransactionCreate) -> tuple[Transaction, Alert | None]:
    transaction = Transaction(
        workspace_id=workspace_id,
        external_id=payload.external_id or f"TX-{uuid.uuid4().hex[:10].upper()}",
        account_id=payload.account_id,
        customer_id=payload.customer_id,
        merchant_id=payload.merchant_id,
        merchant_name=payload.merchant_name,
        amount=payload.amount,
        currency=payload.currency.upper(),
        device_id=payload.device_id,
        ip_address=payload.ip_address,
        location=payload.location,
        occurred_at=payload.occurred_at or datetime.now(UTC),
        status=payload.status,
        source=payload.source,
    )
    db.add(transaction)
    await db.flush()
    score, level, evidence = await score_transaction(db, transaction)
    transaction.risk_score, transaction.risk_level = score, level
    db.add(TransactionFeature(transaction_id=transaction.id, features=evidence["features"]))
    db.add(FraudScore(transaction_id=transaction.id, probability=score, risk_level=level, model_version=evidence["model_version"], evidence=evidence))
    await update_graph(db, transaction)
    alert = None
    if level in {"HIGH", "CRITICAL"}:
        reason = "; ".join(evidence["reasons"][:3])
        alert = Alert(workspace_id=workspace_id, transaction_id=transaction.id, title=f"{level.title()} network risk · {transaction.external_id}", severity=level, risk_score=score, explanation=reason, evidence=evidence)
        db.add(alert)
        await db.flush()
        for factor in evidence["factors"][:5]:
            db.add(AlertEvidence(alert_id=alert.id, evidence_type=factor["key"], value=factor))
        db.add(Notification(workspace_id=workspace_id, title=f"{level.title()} fraud alert", message=f"{transaction.external_id} scored {score:.0%}", kind="FRAUD_ALERT"))

    shared_accounts = await db.scalar(select(func.count(distinct(Transaction.account_id))).where(Transaction.workspace_id == workspace_id, Transaction.device_id == transaction.device_id)) or 1
    if shared_accounts >= 3 and score >= 0.65:
        ring_name = f"Shared infrastructure · {transaction.device_id}"
        ring = (await db.execute(select(FraudRing).where(FraudRing.workspace_id == workspace_id, FraudRing.name == ring_name))).scalar_one_or_none()
        if not ring:
            amount = await db.scalar(select(func.sum(Transaction.amount)).where(Transaction.workspace_id == workspace_id, Transaction.device_id == transaction.device_id)) or transaction.amount
            ring = FraudRing(workspace_id=workspace_id, name=ring_name, risk_score=score, reason=f"{shared_accounts} accounts share device {transaction.device_id} and related network infrastructure.", estimated_amount=float(amount), properties={"shared_device": transaction.device_id, "shared_ip": transaction.ip_address, "accounts": shared_accounts})
            db.add(ring)
            await db.flush()
            members = (await db.execute(select(distinct(Transaction.account_id)).where(Transaction.workspace_id == workspace_id, Transaction.device_id == transaction.device_id))).scalars().all()
            for account in members:
                db.add(FraudRingMember(ring_id=ring.id, entity_id=account, entity_type="ACCOUNT"))
            db.add(FraudRingMember(ring_id=ring.id, entity_id=transaction.device_id, entity_type="DEVICE"))
            db.add(Notification(workspace_id=workspace_id, title="Fraud ring detected", message=ring_name, kind="FRAUD_RING"))
    await db.commit()
    await db.refresh(transaction)
    await manager.broadcast(workspace_id, "transaction.created", transaction_payload(transaction))
    if alert:
        await db.refresh(alert)
        await manager.broadcast(workspace_id, "fraud.alert.created", alert_payload(alert))
    return transaction, alert


def transaction_payload(item: Transaction) -> dict:
    return {"id": item.id, "external_id": item.external_id, "account_id": item.account_id, "merchant_name": item.merchant_name, "merchant_id": item.merchant_id, "amount": item.amount, "currency": item.currency, "device_id": item.device_id, "ip_address": item.ip_address, "location": item.location, "occurred_at": item.occurred_at.isoformat(), "status": item.status, "source": item.source, "risk_score": item.risk_score, "risk_level": item.risk_level}


def alert_payload(item: Alert) -> dict:
    return {"id": item.id, "transaction_id": item.transaction_id, "title": item.title, "severity": item.severity, "risk_score": item.risk_score, "status": item.status.value, "explanation": item.explanation, "created_at": item.created_at.isoformat()}

