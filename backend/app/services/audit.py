from sqlalchemy.ext.asyncio import AsyncSession

from app.models.domain import AuditLog


async def audit(db: AsyncSession, workspace_id: str, action: str, user_id: str | None = None, resource_type: str | None = None, resource_id: str | None = None, details: dict | None = None) -> None:
    db.add(AuditLog(workspace_id=workspace_id, user_id=user_id, action=action, resource_type=resource_type, resource_id=resource_id, details=details or {}))

