from collections import Counter, defaultdict
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter
from sqlalchemy import func, select

from app.api.deps import CurrentUser, DB
from app.models.domain import Alert, Case, FraudRing, GraphNode, TrainingRun, Transaction

router = APIRouter(tags=["analytics"])


@router.get("/dashboard/overview")
async def overview(user: CurrentUser, db: DB) -> dict:
    workspace = user.workspace_id
    transactions = list((await db.execute(select(Transaction).where(Transaction.workspace_id == workspace).order_by(Transaction.occurred_at.desc()).limit(1500))).scalars().all())
    alerts = list((await db.execute(select(Alert).where(Alert.workspace_id == workspace).order_by(Alert.created_at.desc()).limit(500))).scalars().all())
    active_cases = await db.scalar(select(func.count(Case.id)).where(Case.workspace_id == workspace, Case.status.notin_(["CLOSED", "FALSE_POSITIVE"]))) or 0
    nodes = await db.scalar(select(func.count(GraphNode.id)).where(GraphNode.workspace_id == workspace, GraphNode.risk_score >= .5)) or 0
    rings = await db.scalar(select(func.count(FraudRing.id)).where(FraudRing.workspace_id == workspace)) or 0
    now = datetime.now(UTC)
    today_alerts = sum(1 for alert in alerts if alert.created_at.date() == now.date())
    avg_risk = sum(tx.risk_score for tx in transactions) / len(transactions) if transactions else 0
    false_positive = sum(1 for alert in alerts if alert.status.value == "FALSE_POSITIVE")
    by_hour = Counter(tx.occurred_at.hour for tx in transactions)
    by_day = defaultdict(lambda: {"transactions": 0, "alerts": 0})
    for tx in transactions:
        by_day[tx.occurred_at.date().isoformat()]["transactions"] += 1
        if tx.risk_level in {"HIGH", "CRITICAL"}:
            by_day[tx.occurred_at.date().isoformat()]["alerts"] += 1
    merchant_risk: dict[str, list[float]] = defaultdict(list)
    device_risk: dict[str, list[float]] = defaultdict(list)
    for tx in transactions:
        merchant_risk[tx.merchant_name].append(tx.risk_score)
        device_risk[tx.device_id].append(tx.risk_score)
    risk_distribution = Counter(tx.risk_level for tx in transactions)
    severities = Counter(alert.severity for alert in alerts)
    return {
        "metrics": {"transactions_processed": len(transactions), "high_risk_transactions": sum(1 for tx in transactions if tx.risk_level in {"HIGH", "CRITICAL"}), "active_investigations": active_cases, "suspicious_entities": nodes, "fraud_clusters": rings, "alerts_today": today_alerts, "average_risk_score": round(avg_risk, 4), "false_positive_reviews": false_positive, "model_state": "ONLINE", "system_status": "SIMULATION READY"},
        "trend": [{"date": day, **values} for day, values in sorted(by_day.items())[-14:]],
        "fraud_by_hour": [{"hour": f"{hour:02d}:00", "count": by_hour.get(hour, 0)} for hour in range(24)],
        "risk_distribution": [{"name": key, "value": risk_distribution.get(key, 0)} for key in ["LOW", "MEDIUM", "HIGH", "CRITICAL"]],
        "alerts_by_severity": [{"name": key, "value": severities.get(key, 0)} for key in ["LOW", "MEDIUM", "HIGH", "CRITICAL"]],
        "top_merchants": sorted(({"name": key, "risk": round(sum(values) / len(values), 3), "volume": len(values)} for key, values in merchant_risk.items()), key=lambda item: item["risk"], reverse=True)[:6],
        "top_devices": sorted(({"name": key, "risk": round(sum(values) / len(values), 3), "volume": len(values)} for key, values in device_risk.items()), key=lambda item: item["risk"], reverse=True)[:6],
        "mode": "SIMULATED DATA",
    }

