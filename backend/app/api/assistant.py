from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from app.ai import get_provider
from app.api.deps import CurrentUser, DB
from app.models.domain import AISummary, Alert, Case
from app.schemas.domain import AssistantRequest
from app.services.audit import audit

router = APIRouter(prefix="/assistant", tags=["grounded assistant"])


async def _summarize(payload: AssistantRequest, user: CurrentUser, db: DB) -> dict:
    evidence: dict
    subject_type: str
    subject_id: str
    if payload.alert_id:
        alert = (await db.execute(select(Alert).where(Alert.id == payload.alert_id, Alert.workspace_id == user.workspace_id))).scalar_one_or_none()
        if not alert:
            raise HTTPException(status_code=404, detail="Alert not found")
        evidence = {"risk_score": alert.risk_score, "severity": alert.severity, "status": alert.status.value, "explanation": alert.explanation, "structured_evidence": alert.evidence}
        subject_type, subject_id = "ALERT", alert.id
    elif payload.case_id:
        case = (await db.execute(select(Case).where(Case.id == payload.case_id, Case.workspace_id == user.workspace_id))).scalar_one_or_none()
        if not case:
            raise HTTPException(status_code=404, detail="Case not found")
        evidence = {"title": case.title, "severity": case.severity, "status": case.status.value, "decision": case.decision, "structured_evidence": case.evidence}
        subject_type, subject_id = "CASE", case.id
    else:
        raise HTTPException(status_code=422, detail="An alert_id or case_id is required")
    provider = get_provider()
    if not provider:
        return {"available": False, "message": "AI Investigation Assistant unavailable. Core fraud detection remains operational.", "evidence": evidence}
    content = await provider.summarize(evidence, payload.question)
    summary = AISummary(workspace_id=user.workspace_id, subject_type=subject_type, subject_id=subject_id, provider=provider.name, content=content, evidence_snapshot=evidence, created_by=user.id)
    db.add(summary)
    await audit(db, user.workspace_id, "AI_SUMMARY_GENERATED", user.id, subject_type.lower(), subject_id)
    await db.commit()
    return {"available": True, "summary": content, "provider": provider.name, "evidence": evidence}


@router.post("/summarize-alert")
async def summarize_alert(payload: AssistantRequest, user: CurrentUser, db: DB) -> dict:
    return await _summarize(payload, user, db)


@router.post("/summarize-case")
async def summarize_case(payload: AssistantRequest, user: CurrentUser, db: DB) -> dict:
    return await _summarize(payload, user, db)


@router.post("/chat")
async def chat(payload: AssistantRequest, user: CurrentUser, db: DB) -> dict:
    return await _summarize(payload, user, db)

