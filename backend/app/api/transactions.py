import csv
import io
from datetime import datetime

from fastapi import APIRouter, File, HTTPException, Query, UploadFile
from sqlalchemy import select

from app.api.deps import CurrentUser, DB
from app.core.config import settings
from app.models.domain import FraudScore, GraphEdge, GraphNode, Transaction, TransactionFeature
from app.schemas.domain import TransactionCreate, TransactionOut
from app.services.transactions import ingest_transaction

router = APIRouter(tags=["transactions"])


@router.post("/transactions", response_model=TransactionOut, status_code=201)
async def create_transaction(payload: TransactionCreate, user: CurrentUser, db: DB) -> Transaction:
    try:
        transaction, _ = await ingest_transaction(db, user.workspace_id, payload)
        return transaction
    except Exception:
        await db.rollback()
        raise


@router.get("/transactions", response_model=list[TransactionOut])
async def list_transactions(user: CurrentUser, db: DB, risk: str | None = None, search: str | None = None, status: str | None = None, limit: int = Query(100, ge=1, le=500), offset: int = Query(0, ge=0)) -> list[Transaction]:
    query = select(Transaction).where(Transaction.workspace_id == user.workspace_id)
    if risk:
        query = query.where(Transaction.risk_level == risk.upper())
    if status:
        query = query.where(Transaction.status == status.upper())
    if search:
        term = f"%{search}%"
        query = query.where(Transaction.external_id.ilike(term) | Transaction.account_id.ilike(term) | Transaction.merchant_name.ilike(term))
    return list((await db.execute(query.order_by(Transaction.occurred_at.desc()).offset(offset).limit(limit))).scalars().all())


@router.get("/transactions/{transaction_id}")
async def get_transaction(transaction_id: str, user: CurrentUser, db: DB) -> dict:
    transaction = (await db.execute(select(Transaction).where(Transaction.id == transaction_id, Transaction.workspace_id == user.workspace_id))).scalar_one_or_none()
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    feature = (await db.execute(select(TransactionFeature).where(TransactionFeature.transaction_id == transaction.id))).scalar_one_or_none()
    score = (await db.execute(select(FraudScore).where(FraudScore.transaction_id == transaction.id).order_by(FraudScore.created_at.desc()))).scalars().first()
    return {**TransactionOut.model_validate(transaction).model_dump(), "features": feature.features if feature else {}, "evidence": score.evidence if score else {}, "model_version": score.model_version if score else None}


@router.post("/datasets/upload")
async def upload_dataset(user: CurrentUser, db: DB, file: UploadFile = File(...)) -> dict:
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV datasets are supported")
    content = await file.read(settings.upload_max_bytes + 1)
    if len(content) > settings.upload_max_bytes:
        raise HTTPException(status_code=413, detail="Dataset exceeds the configured size limit")
    try:
        text = content.decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(text))
        required = {"account_id", "merchant_id", "merchant_name", "amount", "device_id", "ip_address", "location"}
        if not reader.fieldnames or not required.issubset(reader.fieldnames):
            raise HTTPException(status_code=422, detail={"message": "Missing required columns", "required": sorted(required), "received": reader.fieldnames or []})
        imported, failed = 0, []
        for index, row in enumerate(reader):
            if imported >= 500:
                break
            try:
                payload = TransactionCreate(
                    external_id=row.get("external_id") or None, account_id=row["account_id"], customer_id=row.get("customer_id") or None,
                    merchant_id=row["merchant_id"], merchant_name=row["merchant_name"], amount=float(row["amount"]), currency=row.get("currency") or "USD",
                    device_id=row["device_id"], ip_address=row["ip_address"], location=row["location"], occurred_at=datetime.fromisoformat(row["occurred_at"]) if row.get("occurred_at") else None, source="CSV")
                await ingest_transaction(db, user.workspace_id, payload)
                imported += 1
            except Exception as exc:
                await db.rollback()
                failed.append({"row": index + 2, "error": str(exc)[:160]})
        return {"dataset": file.filename, "label": "SIMULATED DATA" if "synthetic" in file.filename.lower() else "USER PROVIDED DATA", "imported": imported, "failed": failed[:20]}
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=422, detail="CSV must use UTF-8 encoding") from exc

