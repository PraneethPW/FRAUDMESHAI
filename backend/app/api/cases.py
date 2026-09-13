from datetime import UTC, datetime
from fastapi import APIRouter, HTTPException
from sqlalchemy import select
from app.api.deps import CurrentUser, DB
from app.models.domain import (
    Alert,
    Case,
    CaseAlert,
    CaseNote,
    Notification,
    User,
    AuditLog,
    FraudRing,
    FraudRingMember,
    CaseTransaction,
    CaseEntity,
    Transaction,
    AlertStatus,
)
from app.schemas.domain import CaseCreate, CaseOut, CaseUpdate, NoteCreate, AlertOut
from app.services.audit import audit
from app.services.labels import set_label
from app.websocket.manager import manager

router = APIRouter(prefix="/cases", tags=["cases"])


async def validate_assignee(db, workspace_id, user_id):
    if user_id is not None and not await db.scalar(
        select(User.id).where(User.id == user_id, User.workspace_id == workspace_id, User.is_active.is_(True))
    ):
        raise HTTPException(422, "Assignee must be an active user in this workspace")


async def load_case(case_id, user, db):
    case = await db.scalar(select(Case).where(Case.id == case_id, Case.workspace_id == user.workspace_id))
    if not case:
        raise HTTPException(404, "Case not found")
    return case


@router.post("", response_model=CaseOut, status_code=201)
async def create_case(payload: CaseCreate, user: CurrentUser, db: DB):
    await validate_assignee(db, user.workspace_id, payload.assigned_to)
    alert_ids = set(payload.alert_ids)
    alerts = (
        list((await db.execute(select(Alert).where(Alert.workspace_id == user.workspace_id, Alert.id.in_(alert_ids)))).scalars().all())
        if alert_ids
        else []
    )
    if len(alerts) != len(alert_ids):
        raise HTTPException(403, "One or more alerts are unavailable in this workspace")
    evidence = {
        "alerts": [AlertOut.model_validate(a).model_dump(mode="json") for a in alerts],
        "captured_at": datetime.now(UTC).isoformat(),
    }
    entities = []
    ring_id = payload.evidence.get("ring_id")
    if ring_id:
        ring = await db.scalar(select(FraudRing).where(FraudRing.id == ring_id, FraudRing.workspace_id == user.workspace_id))
        if not ring:
            raise HTTPException(404, "Fraud ring not found in this workspace")
        members = (await db.execute(select(FraudRingMember).where(FraudRingMember.ring_id == ring.id))).scalars().all()
        evidence["ring"] = {
            "id": ring.id,
            "name": ring.name,
            "risk_score": ring.risk_score,
            "reason": ring.reason,
            "properties": ring.properties,
            "members": [{"entity_id": m.entity_id, "type": m.entity_type} for m in members],
        }
        entities = [(m.entity_id, m.entity_type) for m in members]
    elif payload.evidence:
        evidence["analyst_supplied_context"] = payload.evidence
    case = Case(
        workspace_id=user.workspace_id,
        title=payload.title,
        severity=payload.severity,
        assigned_to=payload.assigned_to,
        created_by=user.id,
        evidence=evidence,
    )
    db.add(case)
    await db.flush()
    for alert in alerts:
        db.add(CaseAlert(case_id=case.id, alert_id=alert.id))
        if alert.transaction_id:
            db.add(CaseTransaction(case_id=case.id, transaction_id=alert.transaction_id))
    for entity_id, kind in set(entities):
        db.add(CaseEntity(case_id=case.id, entity_id=entity_id, entity_type=kind))
    db.add(
        Notification(
            workspace_id=user.workspace_id,
            user_id=payload.assigned_to,
            title="Investigation case created",
            message=case.title,
            kind="CASE_ASSIGNED",
        )
    )
    await audit(db, user.workspace_id, "CASE_CREATED", user.id, "case", case.id, {"alerts": sorted(alert_ids), "ring_id": ring_id})
    await db.commit()
    await db.refresh(case)
    await manager.broadcast(user.workspace_id, "case.updated", {"id": case.id})
    return case


@router.get("", response_model=list[CaseOut])
async def list_cases(user: CurrentUser, db: DB):
    return list(
        (await db.execute(select(Case).where(Case.workspace_id == user.workspace_id).order_by(Case.updated_at.desc()).limit(500)))
        .scalars()
        .all()
    )


@router.get("/{case_id}")
async def get_case(case_id: str, user: CurrentUser, db: DB):
    case = await load_case(case_id, user, db)
    notes = (
        await db.execute(
            select(CaseNote, User.full_name)
            .join(User, User.id == CaseNote.author_id)
            .where(CaseNote.case_id == case.id)
            .order_by(CaseNote.created_at.desc())
        )
    ).all()
    alert_ids = (await db.execute(select(CaseAlert.alert_id).where(CaseAlert.case_id == case.id))).scalars().all()
    logs = (
        (
            await db.execute(
                select(AuditLog)
                .where(AuditLog.workspace_id == user.workspace_id, AuditLog.resource_type == "case", AuditLog.resource_id == case.id)
                .order_by(AuditLog.created_at)
            )
        )
        .scalars()
        .all()
    )
    return {
        **CaseOut.model_validate(case).model_dump(),
        "alert_ids": list(alert_ids),
        "notes": [
            {"id": n.id, "body": n.body, "author_id": n.author_id, "author_name": name, "created_at": n.created_at} for n, name in notes
        ],
        "timeline": [
            {"id": l.id, "action": l.action, "user_id": l.user_id, "details": l.details, "created_at": l.created_at} for l in logs
        ],
    }


@router.get("/{case_id}/export")
async def export_case(case_id: str, user: CurrentUser, db: DB):
    return await get_case(case_id, user, db)


@router.patch("/{case_id}", response_model=CaseOut)
async def update_case(case_id: str, payload: CaseUpdate, user: CurrentUser, db: DB):
    case = await load_case(case_id, user, db)
    changes = payload.model_dump(exclude_unset=True)
    if any(value is None for key, value in changes.items() if key not in ("assigned_to", "decision")):
        raise HTTPException(422, "Title, severity and status cannot be null")
    await validate_assignee(db, user.workspace_id, payload.assigned_to)
    before = {key: getattr(getattr(case, key), "value", getattr(case, key)) for key in changes}
    for field, value in changes.items():
        setattr(case, field, value)
    await audit(
        db,
        user.workspace_id,
        "CASE_STATUS_CHANGED" if "status" in changes else "CASE_UPDATED",
        user.id,
        "case",
        case.id,
        {"before": before, "after": changes},
    )
    if getattr(case.status, "value", case.status) in ("CONFIRMED", "FALSE_POSITIVE") and "status" in changes:
        linked = (
            (
                await db.execute(
                    select(Alert)
                    .join(CaseAlert, CaseAlert.alert_id == Alert.id)
                    .where(CaseAlert.case_id == case.id, Alert.workspace_id == user.workspace_id)
                )
            )
            .scalars()
            .all()
        )
        for alert in linked:
            fraud = case.status == "CONFIRMED"
            alert.status = AlertStatus.CONFIRMED_FRAUD if fraud else AlertStatus.FALSE_POSITIVE
            if alert.transaction_id:
                await set_label(
                    db,
                    user.workspace_id,
                    alert.transaction_id,
                    fraud,
                    "CASE_REVIEW",
                    case.decision or f"Case {case.id} disposition",
                    user.id,
                )
            await audit(
                db, user.workspace_id, "ALERT_REVIEWED", user.id, "alert", alert.id, {"case_id": case.id, "status": alert.status.value}
            )
    await db.commit()
    await db.refresh(case)
    await manager.broadcast(user.workspace_id, "case.updated", {"id": case.id})
    return case


@router.post("/{case_id}/notes", status_code=201)
async def add_note(case_id: str, payload: NoteCreate, user: CurrentUser, db: DB):
    case = await load_case(case_id, user, db)
    if not payload.body.strip():
        raise HTTPException(422, "Note cannot be blank")
    note = CaseNote(case_id=case.id, author_id=user.id, body=payload.body.strip())
    db.add(note)
    await db.flush()
    case.updated_at = datetime.now(UTC)
    await audit(db, user.workspace_id, "NOTE_ADDED", user.id, "case", case.id, {"note_id": note.id})
    await db.commit()
    await manager.broadcast(user.workspace_id, "case.updated", {"id": case.id})
    return {"id": note.id, "body": note.body, "created_at": note.created_at}
