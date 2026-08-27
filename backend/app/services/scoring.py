import math
from datetime import UTC, datetime, timedelta

from sqlalchemy import distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.ml.explainability import explain_score
from app.ml.features import build_features
from app.models.domain import Transaction


def risk_level(score: float) -> str:
    if score >= settings.risk_critical_threshold:
        return "CRITICAL"
    if score >= settings.risk_high_threshold:
        return "HIGH"
    if score >= settings.risk_medium_threshold:
        return "MEDIUM"
    return "LOW"


async def score_transaction(db: AsyncSession, transaction: Transaction) -> tuple[float, str, dict]:
    since = transaction.occurred_at - timedelta(hours=1)
    day_since = transaction.occurred_at - timedelta(hours=24)
    device_accounts = await db.scalar(select(func.count(distinct(Transaction.account_id))).where(Transaction.workspace_id == transaction.workspace_id, Transaction.device_id == transaction.device_id)) or 1
    ip_accounts = await db.scalar(select(func.count(distinct(Transaction.account_id))).where(Transaction.workspace_id == transaction.workspace_id, Transaction.ip_address == transaction.ip_address)) or 1
    recent_count = await db.scalar(select(func.count(Transaction.id)).where(Transaction.workspace_id == transaction.workspace_id, Transaction.account_id == transaction.account_id, Transaction.occurred_at >= since)) or 1
    merchant_frequency = await db.scalar(select(func.count(Transaction.id)).where(Transaction.workspace_id == transaction.workspace_id, Transaction.merchant_id == transaction.merchant_id, Transaction.occurred_at >= day_since)) or 1
    previous = (await db.execute(select(Transaction).where(Transaction.workspace_id == transaction.workspace_id, Transaction.account_id == transaction.account_id, Transaction.id != transaction.id).order_by(Transaction.occurred_at.desc()).limit(1))).scalar_one_or_none()
    device_seen = await db.scalar(select(func.count(Transaction.id)).where(Transaction.workspace_id == transaction.workspace_id, Transaction.account_id == transaction.account_id, Transaction.device_id == transaction.device_id, Transaction.id != transaction.id)) or 0
    current_time = transaction.occurred_at if transaction.occurred_at.tzinfo else transaction.occurred_at.replace(tzinfo=UTC)
    previous_time = previous.occurred_at if previous and previous.occurred_at.tzinfo else previous.occurred_at.replace(tzinfo=UTC) if previous else None
    seconds_since = max((current_time - previous_time).total_seconds(), 1) if previous_time else None
    features = build_features(amount=transaction.amount, occurred_at=transaction.occurred_at, device_accounts=device_accounts, ip_accounts=ip_accounts, recent_count=recent_count, merchant_frequency=merchant_frequency, new_device=device_seen == 0, location_changed=bool(previous and previous.location != transaction.location), seconds_since_previous=seconds_since)

    behavioral = min(1.0, math.log1p(transaction.amount) / 10 + (0.16 if features["unusual_hour"] else 0) + (0.12 if features["new_device"] else 0))
    graph = min(1.0, features["device_sharing_count"] * 0.22 + features["ip_sharing_count"] * 0.18)
    velocity = min(1.0, max(0, recent_count - 1) / 6 + (0.18 if seconds_since and seconds_since < 90 else 0))
    device = min(1.0, features["device_sharing_count"] / 4)
    location = 0.8 if features["location_changed"] else 0.05
    contributions = {
        "behavioral_anomaly": behavioral * 0.29,
        "graph_relationship_risk": graph * 0.31,
        "velocity_anomaly": velocity * 0.22,
        "device_sharing_risk": device * 0.12,
        "location_anomaly": location * 0.06,
    }
    raw = sum(contributions.values())
    score = min(0.995, max(0.01, 1 / (1 + math.exp(-7.5 * (raw - 0.38)))))
    explanation = explain_score(features, contributions)
    explanation.update({"risk_probability": round(score, 4), "model_version": "time-aware-graph-ensemble-v1", "prediction_timestamp": datetime.now(UTC).isoformat()})
    return round(score, 4), risk_level(score), explanation
