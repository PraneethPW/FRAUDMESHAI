from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select

from app.api.deps import DB, roles
from app.core.config import settings
from app.models.domain import AuditLog, ModelVersion, Role, User

router = APIRouter(prefix="/admin", tags=["administration"])
AdminUser = Annotated[User, Depends(roles(Role.ADMIN))]


@router.get("/overview")
async def admin_overview(user: AdminUser, db: DB) -> dict:
    users = (await db.execute(select(User).where(User.workspace_id == user.workspace_id).order_by(User.created_at))).scalars().all()
    models = (await db.execute(select(ModelVersion).order_by(ModelVersion.created_at.desc()))).scalars().all()
    logs = (await db.execute(select(AuditLog).where(AuditLog.workspace_id == user.workspace_id).order_by(AuditLog.created_at.desc()).limit(80))).scalars().all()
    return {
        "users": [{"id": item.id, "email": item.email, "full_name": item.full_name, "role": item.role.value, "is_active": item.is_active} for item in users],
        "models": [{"id": item.id, "name": item.name, "version": item.version, "type": item.model_type, "active": item.active} for item in models],
        "risk_thresholds": {"medium": settings.risk_medium_threshold, "high": settings.risk_high_threshold, "critical": settings.risk_critical_threshold},
        "ai_provider": {"configured": bool((settings.openrouter_api_key and settings.openrouter_model) or (settings.openai_api_key and settings.openai_model)), "provider": "OpenRouter" if settings.openrouter_api_key else "OpenAI" if settings.openai_api_key else "Unavailable"},
        "audit_logs": [{"id": item.id, "action": item.action, "resource_type": item.resource_type, "created_at": item.created_at} for item in logs],
    }
