from fastapi import APIRouter
from sqlalchemy import select

from app.api.deps import CurrentUser, DB
from app.models.domain import AuditLog, Notification, User
from app.schemas.domain import UserOut

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserOut)
async def me(user: CurrentUser) -> User:
    return user


@router.get("/notifications")
async def notifications(user: CurrentUser, db: DB) -> list[dict]:
    items = (await db.execute(select(Notification).where(Notification.workspace_id == user.workspace_id).order_by(Notification.created_at.desc()).limit(30))).scalars().all()
    return [{"id": item.id, "title": item.title, "message": item.message, "kind": item.kind, "read": item.read, "created_at": item.created_at} for item in items]


@router.get("/audit")
async def audit_history(user: CurrentUser, db: DB) -> list[dict]:
    items = (await db.execute(select(AuditLog).where(AuditLog.workspace_id == user.workspace_id).order_by(AuditLog.created_at.desc()).limit(100))).scalars().all()
    return [{"id": item.id, "action": item.action, "resource_type": item.resource_type, "resource_id": item.resource_id, "details": item.details, "created_at": item.created_at} for item in items]

