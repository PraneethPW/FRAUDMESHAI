from datetime import UTC, datetime, timedelta
from fastapi import APIRouter
from sqlalchemy import case as sql_case, func, select
from app.api.deps import CurrentUser, DB
from app.models.domain import Alert, Case, FraudRing, GraphNode, ModelArtifact, Transaction

router = APIRouter(tags=["analytics"])


@router.get("/dashboard/overview")
async def overview(user: CurrentUser, db: DB):
    w = user.workspace_id
    tx_scope = Transaction.workspace_id == w
    alert_scope = Alert.workspace_id == w
    total, high, average = (
        await db.execute(
            select(
                func.count(Transaction.id),
                func.sum(sql_case((Transaction.risk_level.in_(["HIGH", "CRITICAL"]), 1), else_=0)),
                func.avg(Transaction.risk_score),
            ).where(tx_scope)
        )
    ).one()
    cases = (
        await db.scalar(select(func.count(Case.id)).where(Case.workspace_id == w, Case.status.notin_(["CLOSED", "FALSE_POSITIVE"]))) or 0
    )
    nodes = await db.scalar(select(func.count(GraphNode.id)).where(GraphNode.workspace_id == w, GraphNode.risk_score >= 0.5)) or 0
    rings = await db.scalar(select(func.count(FraudRing.id)).where(FraudRing.workspace_id == w)) or 0
    today = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    today_alerts = await db.scalar(select(func.count(Alert.id)).where(alert_scope, Alert.created_at >= today)) or 0
    fp = await db.scalar(select(func.count(Alert.id)).where(alert_scope, Alert.status == "FALSE_POSITIVE")) or 0
    risk = dict(
        (
            await db.execute(select(Transaction.risk_level, func.count(Transaction.id)).where(tx_scope).group_by(Transaction.risk_level))
        ).all()
    )
    severity = dict((await db.execute(select(Alert.severity, func.count(Alert.id)).where(alert_scope).group_by(Alert.severity))).all())
    sources = dict(
        (await db.execute(select(Transaction.source, func.count(Transaction.id)).where(tx_scope).group_by(Transaction.source))).all()
    )
    date = func.date(Transaction.occurred_at)
    trend = (
        await db.execute(
            select(date, func.count(Transaction.id), func.sum(sql_case((Transaction.risk_level.in_(["HIGH", "CRITICAL"]), 1), else_=0)))
            .where(tx_scope, Transaction.occurred_at >= today - timedelta(days=13))
            .group_by(date)
            .order_by(date)
        )
    ).all()
    hour = func.extract("hour", Transaction.occurred_at)
    hours = dict(
        (
            await db.execute(
                select(hour, func.count(Transaction.id)).where(tx_scope, Transaction.risk_level.in_(["HIGH", "CRITICAL"])).group_by(hour)
            )
        ).all()
    )

    async def top(column):
        rows = (
            await db.execute(
                select(column, func.avg(Transaction.risk_score), func.count(Transaction.id))
                .where(tx_scope)
                .group_by(column)
                .order_by(func.avg(Transaction.risk_score).desc())
                .limit(6)
            )
        ).all()
        return [{"name": name, "risk": round(float(score), 3), "volume": count} for name, score, count in rows]

    active = (
        (await db.execute(select(ModelArtifact).where(ModelArtifact.workspace_id == w, ModelArtifact.active.is_(True)))).scalars().first()
    )
    mode = (
        "NO DATA"
        if not sources
        else "SIMULATED DATA" if set(sources) == {"SIMULATION"} else "MIXED SOURCES" if "SIMULATION" in sources else "USER PROVIDED DATA"
    )
    return {
        "metrics": {
            "transactions_processed": total,
            "high_risk_transactions": high or 0,
            "active_investigations": cases,
            "suspicious_entities": nodes,
            "fraud_clusters": rings,
            "alerts_today": today_alerts,
            "average_risk_score": round(float(average or 0), 4),
            "false_positive_reviews": fp,
            "model_state": active.artifact["model_type"] if active else "HEURISTIC",
            "system_status": "OPERATIONAL",
        },
        "trend": [{"date": str(day), "transactions": count, "alerts": alerts or 0} for day, count, alerts in trend],
        "fraud_by_hour": [{"hour": f"{h:02d}:00", "count": hours.get(h, 0)} for h in range(24)],
        "risk_distribution": [{"name": level, "value": risk.get(level, 0)} for level in ["LOW", "MEDIUM", "HIGH", "CRITICAL"]],
        "alerts_by_severity": [{"name": level, "value": severity.get(level, 0)} for level in ["LOW", "MEDIUM", "HIGH", "CRITICAL"]],
        "top_merchants": await top(Transaction.merchant_name),
        "top_devices": await top(Transaction.device_id),
        "mode": mode,
        "sources": sources,
        "active_model": (
            {"run_id": active.run_id, "type": active.artifact["model_type"], "dataset": active.artifact["dataset"]} if active else None
        ),
    }
