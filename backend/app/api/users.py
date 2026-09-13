from fastapi import APIRouter, HTTPException
from sqlalchemy import select, or_, update

from app.api.deps import CurrentUser, DB
from app.models.domain import AuditLog, Notification, User
from app.schemas.domain import UserOut

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserOut)
async def me(user: CurrentUser) -> User:
    return user


@router.get("/notifications")
async def notifications(user: CurrentUser, db: DB) -> list[dict]:
    items = (
        (
            await db.execute(
                select(Notification)
                .where(Notification.workspace_id == user.workspace_id, or_(Notification.user_id == user.id, Notification.user_id.is_(None)))
                .order_by(Notification.created_at.desc())
                .limit(30)
            )
        )
        .scalars()
        .all()
    )
    return [
        {"id": item.id, "title": item.title, "message": item.message, "kind": item.kind, "read": item.read, "created_at": item.created_at}
        for item in items
    ]


@router.get("/audit")
async def audit_history(user: CurrentUser, db: DB) -> list[dict]:
    items = (
        (
            await db.execute(
                select(AuditLog).where(AuditLog.workspace_id == user.workspace_id).order_by(AuditLog.created_at.desc()).limit(100)
            )
        )
        .scalars()
        .all()
    )
    return [
        {
            "id": item.id,
            "action": item.action,
            "resource_type": item.resource_type,
            "resource_id": item.resource_id,
            "details": item.details,
            "created_at": item.created_at,
        }
        for item in items
    ]


@router.get("/workspace", response_model=list[UserOut])
async def workspace_users(user: CurrentUser, db: DB):
    return (
        (await db.execute(select(User).where(User.workspace_id == user.workspace_id, User.is_active.is_(True)).order_by(User.full_name)))
        .scalars()
        .all()
    )


@router.patch("/notifications/{notification_id}/read")
async def read_notification(notification_id: str, user: CurrentUser, db: DB):
    item = await db.scalar(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.workspace_id == user.workspace_id,
            or_(Notification.user_id == user.id, Notification.user_id.is_(None)),
        )
    )
    if not item:
        raise HTTPException(404, "Notification not found")
    item.read = True
    await db.commit()
    return {"id": item.id, "read": True}


@router.get("/search")
async def search_workspace(q: str, user: CurrentUser, db: DB):
    from app.models.domain import Transaction, Alert, Case, GraphNode

    if len(q.strip()) < 2:
        return []
    term = f"%{q.strip()[:100]}%"
    result = []
    for model, fields, kind, path in [
        (Transaction, [Transaction.external_id, Transaction.account_id, Transaction.merchant_name], "Transaction", "transactions"),
        (Alert, [Alert.title], "Alert", "alerts"),
        (Case, [Case.title], "Case", "cases"),
        (GraphNode, [GraphNode.label, GraphNode.entity_id], "Entity", "graph"),
    ]:
        items = (
            (await db.execute(select(model).where(model.workspace_id == user.workspace_id, or_(*[f.ilike(term) for f in fields])).limit(5)))
            .scalars()
            .all()
        )
        for item in items:
            result.append(
                {
                    "id": item.id,
                    "label": getattr(item, "title", None) or getattr(item, "external_id", None) or item.label,
                    "kind": kind,
                    "url": f"/app/{path}/{item.id}" if path != "graph" else f"/app/graph?node={item.id}",
                }
            )
    return result
