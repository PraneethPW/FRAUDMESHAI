from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from app.api.deps import CurrentUser, DB
from app.models.domain import Alert, Case, CaseAlert, CaseNote, Notification
from app.schemas.domain import CaseCreate, CaseOut, CaseUpdate, NoteCreate
from app.services.audit import audit
from app.websocket.manager import manager

router = APIRouter(prefix="/cases", tags=["cases"])


@router.post("", response_model=CaseOut, status_code=201)
async def create_case(payload: CaseCreate, user: CurrentUser, db: DB) -> Case:
    if payload.alert_ids:
        valid = (await db.execute(select(Alert.id).where(Alert.workspace_id == user.workspace_id, Alert.id.in_(payload.alert_ids)))).scalars().all()
        if len(valid) != len(set(payload.alert_ids)):
            raise HTTPException(status_code=403, detail="One or more alerts are unavailable in this workspace")
    case = Case(workspace_id=user.workspace_id, title=payload.title, severity=payload.severity, assigned_to=payload.assigned_to, created_by=user.id, evidence=payload.evidence)
    db.add(case)
    await db.flush()
    for alert_id in payload.alert_ids:
        db.add(CaseAlert(case_id=case.id, alert_id=alert_id))
    db.add(Notification(workspace_id=user.workspace_id, user_id=payload.assigned_to, title="Investigation case created", message=case.title, kind="CASE_ASSIGNED"))
    await audit(db, user.workspace_id, "CASE_CREATED", user.id, "case", case.id, {"alerts": payload.alert_ids})
    await db.commit()
    await db.refresh(case)
    await manager.broadcast(user.workspace_id, "case.updated", CaseOut.model_validate(case).model_dump(mode="json"))
    return case


@router.get("", response_model=list[CaseOut])
async def list_cases(user: CurrentUser, db: DB) -> list[Case]:
    return list((await db.execute(select(Case).where(Case.workspace_id == user.workspace_id).order_by(Case.updated_at.desc()))).scalars().all())


@router.get("/{case_id}")
async def get_case(case_id: str, user: CurrentUser, db: DB) -> dict:
    case = (await db.execute(select(Case).where(Case.id == case_id, Case.workspace_id == user.workspace_id))).scalar_one_or_none()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    notes = (await db.execute(select(CaseNote).where(CaseNote.case_id == case.id).order_by(CaseNote.created_at.desc()))).scalars().all()
    alert_ids = (await db.execute(select(CaseAlert.alert_id).where(CaseAlert.case_id == case.id))).scalars().all()
    return {**CaseOut.model_validate(case).model_dump(), "alert_ids": list(alert_ids), "notes": [{"id": note.id, "body": note.body, "author_id": note.author_id, "created_at": note.created_at} for note in notes]}


@router.patch("/{case_id}", response_model=CaseOut)
async def update_case(case_id: str, payload: CaseUpdate, user: CurrentUser, db: DB) -> Case:
    case = (await db.execute(select(Case).where(Case.id == case_id, Case.workspace_id == user.workspace_id))).scalar_one_or_none()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    changes = payload.model_dump(exclude_none=True)
    for field, value in changes.items():
        setattr(case, field, value)
    action = "CASE_STATUS_CHANGED" if "status" in changes else "CASE_ASSIGNED" if "assigned_to" in changes else "CASE_UPDATED"
    await audit(db, user.workspace_id, action, user.id, "case", case.id, {key: getattr(value, "value", value) for key, value in changes.items()})
    await db.commit()
    await db.refresh(case)
    await manager.broadcast(user.workspace_id, "case.updated", CaseOut.model_validate(case).model_dump(mode="json"))
    return case


@router.post("/{case_id}/notes", status_code=201)
async def add_note(case_id: str, payload: NoteCreate, user: CurrentUser, db: DB) -> dict:
    case = (await db.execute(select(Case).where(Case.id == case_id, Case.workspace_id == user.workspace_id))).scalar_one_or_none()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    note = CaseNote(case_id=case.id, author_id=user.id, body=payload.body)
    db.add(note)
    await db.flush()
    await audit(db, user.workspace_id, "NOTE_ADDED", user.id, "case", case.id)
    await db.commit()
    return {"id": note.id, "body": note.body, "created_at": note.created_at}

