from sqlalchemy import select
from app.models.domain import TransactionLabel


async def set_label(db, workspace_id, transaction_id, is_fraud, source, reason, author_id):
    item = (await db.execute(select(TransactionLabel).where(TransactionLabel.transaction_id == transaction_id))).scalar_one_or_none()
    if not item:
        item = TransactionLabel(
            transaction_id=transaction_id, workspace_id=workspace_id, is_fraud=is_fraud, source=source, reason=reason, author_id=author_id
        )
        db.add(item)
    else:
        item.is_fraud = is_fraud
        item.source = source
        item.reason = reason
        item.author_id = author_id
    return item
