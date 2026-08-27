from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import select

from app.api.deps import CurrentUser, DB
from app.models.domain import Alert
from app.schemas.domain import AlertOut, AlertUpdate
from app.services.audit import audit
from app.websocket.manager import manager

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.get("", response_model=list[AlertOut])
async def list_alerts(user: CurrentUser, db: DB, severity: str | None = None, status: str | None = None, limit: int = Query(100, ge=1, le=500)) -> list[Alert]:
    query = select(Alert).where(Alert.workspace_id == user.workspace_id)
    if severity:
        query = query.where(Alert.severity == severity.upper())
    if status:
        query = query.where(Alert.status == status.upper())
    return list((await db.execute(query.order_by(Alert.created_at.desc()).limit(limit))).scalars().all())


@router.get("/{alert_id}", response_model=AlertOut)
async def get_alert(alert_id: str, user: CurrentUser, db: DB) -> Alert:
    alert = (await db.execute(select(Alert).where(Alert.id == alert_id, Alert.workspace_id == user.workspace_id))).scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    return alert


@router.patch("/{alert_id}", response_model=AlertOut)
async def update_alert(alert_id: str, payload: AlertUpdate, user: CurrentUser, db: DB) -> Alert:
    alert = (await db.execute(select(Alert).where(Alert.id == alert_id, Alert.workspace_id == user.workspace_id))).scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    changes = payload.model_dump(exclude_none=True)
    for field, value in changes.items():
        setattr(alert, field, value)
    await audit(db, user.workspace_id, "ALERT_REVIEWED", user.id, "alert", alert.id, changes)
    await db.commit()
    await db.refresh(alert)
    await manager.broadcast(user.workspace_id, "fraud.alert.updated", AlertOut.model_validate(alert).model_dump(mode="json"))
    return alert

