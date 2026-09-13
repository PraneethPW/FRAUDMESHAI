from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from app.api.deps import DB, roles
from app.core.config import settings
from app.models.domain import AuditLog, ModelVersion, Role, User, ModelArtifact, TrainingRun

router = APIRouter(prefix="/admin", tags=["administration"])
AdminUser = Annotated[User, Depends(roles(Role.ADMIN))]


@router.get("/overview")
async def admin_overview(user: AdminUser, db: DB) -> dict:
    users = (await db.execute(select(User).where(User.workspace_id == user.workspace_id).order_by(User.created_at))).scalars().all()
    models = (
        await db.execute(
            select(TrainingRun, ModelArtifact.active)
            .join(ModelArtifact, ModelArtifact.run_id == TrainingRun.id)
            .where(TrainingRun.workspace_id == user.workspace_id)
            .order_by(TrainingRun.created_at.desc())
        )
    ).all()
    logs = (
        (
            await db.execute(
                select(AuditLog).where(AuditLog.workspace_id == user.workspace_id).order_by(AuditLog.created_at.desc()).limit(80)
            )
        )
        .scalars()
        .all()
    )
    return {
        "users": [
            {"id": item.id, "email": item.email, "full_name": item.full_name, "role": item.role.value, "is_active": item.is_active}
            for item in users
        ],
        "models": [
            {"id": item.id, "name": item.model_type, "version": item.id[:12], "type": item.model_type, "active": active}
            for item, active in models
        ],
        "risk_thresholds": {
            "medium": settings.risk_medium_threshold,
            "high": settings.risk_high_threshold,
            "critical": settings.risk_critical_threshold,
        },
        "ai_provider": {
            "configured": bool(
                (settings.openrouter_api_key and settings.openrouter_model) or (settings.openai_api_key and settings.openai_model)
            ),
            "provider": "OpenRouter" if settings.openrouter_api_key else "OpenAI" if settings.openai_api_key else "Unavailable",
        },
        "audit_logs": [
            {"id": item.id, "action": item.action, "resource_type": item.resource_type, "created_at": item.created_at} for item in logs
        ],
    }


from app.schemas.domain import WorkspaceUserCreate, WorkspaceUserUpdate, UserOut
from app.core.security import hash_password
from app.services.audit import audit


@router.post("/users", response_model=UserOut, status_code=201)
async def create_user(payload: WorkspaceUserCreate, user: AdminUser, db: DB):
    if await db.scalar(select(User.id).where(User.email == payload.email.lower())):
        raise HTTPException(409, "Email already registered")
    item = User(
        workspace_id=user.workspace_id,
        email=payload.email.lower(),
        full_name=payload.full_name,
        role=payload.role,
        password_hash=hash_password(payload.password),
    )
    db.add(item)
    await db.flush()
    await audit(db, user.workspace_id, "USER_CREATED", user.id, "user", item.id, {"role": payload.role.value})
    await db.commit()
    return item


@router.patch("/users/{user_id}", response_model=UserOut)
async def update_user(user_id: str, payload: WorkspaceUserUpdate, user: AdminUser, db: DB):
    item = await db.scalar(select(User).where(User.id == user_id, User.workspace_id == user.workspace_id))
    if not item:
        raise HTTPException(404, "User not found")
    if item.id == user.id and (payload.is_active is False or (payload.role and payload.role != Role.ADMIN)):
        raise HTTPException(422, "You cannot disable or demote your own administrator account")
    for key, value in payload.model_dump(exclude_none=True).items():
        setattr(item, key, value)
    await audit(db, user.workspace_id, "USER_UPDATED", user.id, "user", item.id, payload.model_dump(mode="json", exclude_none=True))
    await db.commit()
    return item
