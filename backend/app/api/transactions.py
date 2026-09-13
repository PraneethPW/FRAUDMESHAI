import csv
import io
from datetime import datetime

from fastapi import APIRouter, File, HTTPException, Query, UploadFile
from fastapi.responses import Response
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.api.deps import CurrentUser, DB
from app.core.config import settings
from app.models.domain import FraudScore, GraphEdge, GraphNode, Transaction, TransactionFeature
from app.schemas.domain import TransactionCreate, TransactionOut, LabelRequest
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
async def list_transactions(
    user: CurrentUser,
    db: DB,
    risk: str | None = None,
    search: str | None = None,
    status: str | None = None,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> list[Transaction]:
    query = select(Transaction).where(Transaction.workspace_id == user.workspace_id)
    if risk:
        query = query.where(Transaction.risk_level == risk.upper())
    if status:
        query = query.where(Transaction.status == status.upper())
    if search:
        term = f"%{search}%"
        query = query.where(
            Transaction.external_id.ilike(term)
            | Transaction.account_id.ilike(term)
            | Transaction.merchant_name.ilike(term)
            | Transaction.device_id.ilike(term)
            | Transaction.ip_address.ilike(term)
            | Transaction.location.ilike(term)
        )
    return list((await db.execute(query.order_by(Transaction.occurred_at.desc()).offset(offset).limit(limit))).scalars().all())


@router.get("/transactions/export")
async def export_transactions(user: CurrentUser, db: DB, risk: str | None = None, search: str | None = None, offset: int = Query(0, ge=0)):
    rows = await list_transactions(user, db, risk=risk, search=search, limit=500, offset=offset)
    output = io.StringIO()
    fields = list(TransactionOut.model_fields)
    writer = csv.DictWriter(output, fieldnames=fields)
    writer.writeheader()
    for item in rows:
        values = TransactionOut.model_validate(item).model_dump(mode="json")
        writer.writerow(
            {k: ("'" + v if isinstance(v, str) and v.startswith(("=", "+", "-", "@", "\t", "\r")) else v) for k, v in values.items()}
        )
    return Response(
        output.getvalue(), media_type="text/csv", headers={"Content-Disposition": 'attachment; filename="fraudmesh_transactions.csv"'}
    )


@router.get("/transactions/{transaction_id}")
async def get_transaction(transaction_id: str, user: CurrentUser, db: DB) -> dict:
    transaction = (
        await db.execute(select(Transaction).where(Transaction.id == transaction_id, Transaction.workspace_id == user.workspace_id))
    ).scalar_one_or_none()
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    feature = (await db.execute(select(TransactionFeature).where(TransactionFeature.transaction_id == transaction.id))).scalar_one_or_none()
    score = (
        (await db.execute(select(FraudScore).where(FraudScore.transaction_id == transaction.id).order_by(FraudScore.created_at.desc())))
        .scalars()
        .first()
    )
    return {
        **TransactionOut.model_validate(transaction).model_dump(),
        "features": feature.features if feature else {},
        "evidence": score.evidence if score else {},
        "model_version": score.model_version if score else None,
    }


@router.get("/datasets/template")
async def template(user: CurrentUser):
    content = "external_id,account_id,customer_id,merchant_id,merchant_name,amount,currency,device_id,ip_address,location,occurred_at,is_fraud\nEXAMPLE-001,ACC-1,CUS-1,M-1,Example Merchant,125.50,USD,DEV-1,198.51.100.1,London,2026-01-01T12:00:00Z,0\n"
    return Response(content, media_type="text/csv", headers={"Content-Disposition": 'attachment; filename="fraudmesh_template.csv"'})


@router.post("/transactions/{transaction_id}/label")
async def label_transaction(transaction_id: str, payload: LabelRequest, user: CurrentUser, db: DB):
    tx = await db.scalar(select(Transaction).where(Transaction.id == transaction_id, Transaction.workspace_id == user.workspace_id))
    if not tx:
        raise HTTPException(404, "Transaction not found")
    from app.services.labels import set_label
    from app.services.audit import audit

    await set_label(db, user.workspace_id, tx.id, payload.is_fraud, "ANALYST", payload.reason, user.id)
    await audit(db, user.workspace_id, "TRANSACTION_LABELLED", user.id, "transaction", tx.id, payload.model_dump())
    await db.commit()
    return {"transaction_id": tx.id, **payload.model_dump()}


@router.post("/datasets/upload")
async def upload_dataset(user: CurrentUser, db: DB, file: UploadFile = File(...)) -> dict:
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(400, "Only CSV datasets are supported")
    content = await file.read(settings.upload_max_bytes + 1)
    if len(content) > settings.upload_max_bytes:
        raise HTTPException(413, "Dataset exceeds the configured size limit")
    try:
        reader = csv.DictReader(io.StringIO(content.decode("utf-8-sig")), strict=True)
        required = {"account_id", "merchant_id", "merchant_name", "amount", "device_id", "ip_address", "location"}
        if not reader.fieldnames or not required.issubset(reader.fieldnames):
            raise HTTPException(422, {"message": "Missing required columns", "required": sorted(required)})
        parsed = []
        failed = []
        for index, row in enumerate(reader):
            if index >= 500:
                raise HTTPException(422, "Maximum 500 rows per upload; split the file. No rows imported.")
            try:
                values = {k: v for k, v in row.items() if k in TransactionCreate.model_fields and v not in ("", None)}
                values["source"] = "CSV"
                parsed.append((index + 2, TransactionCreate.model_validate(values)))
            except ValidationError as exc:
                failed.append({"row": index + 2, "error": "; ".join(f"{e['loc'][0]}: {e['msg']}" for e in exc.errors())})
        if not parsed and not failed:
            raise HTTPException(422, "CSV contains no data rows")
        # Process historical files in causal order even when uploaded unsorted.
        from datetime import UTC
        from sqlalchemy import func
        from app.services.audit import audit

        cutoff = datetime.now(UTC)
        parsed.sort(key=lambda item: item[1].occurred_at or cutoff)
        imported = 0
        duplicates = 0
        workspace_id = user.workspace_id
        user_id = user.id
        for row_number, payload in parsed:
            try:
                exists = bool(
                    payload.external_id
                    and await db.scalar(
                        select(Transaction.id).where(
                            Transaction.workspace_id == workspace_id, Transaction.external_id == payload.external_id
                        )
                    )
                )
                await ingest_transaction(db, workspace_id, payload)
                if exists:
                    duplicates += 1
                else:
                    imported += 1
            except HTTPException as exc:
                await db.rollback()
                failed.append({"row": row_number, "error": str(exc.detail)})
            except SQLAlchemyError:
                await db.rollback()
                failed.append({"row": row_number, "error": "Database rejected this row. Check field lengths and retry."})
        await audit(
            db,
            workspace_id,
            "DATASET_IMPORTED",
            user_id,
            "dataset",
            details={"filename": file.filename, "imported": imported, "duplicates": duplicates, "failed": len(failed)},
        )
        await db.commit()
        return {
            "dataset": file.filename,
            "label": "USER PROVIDED DATA",
            "imported": imported,
            "duplicates": duplicates,
            "failed_count": len(failed),
            "failed": failed,
            "total_rows": len(parsed) + len([e for e in failed if e["row"] not in {r for r, _ in parsed}]),
        }
    except (UnicodeDecodeError, csv.Error) as exc:
        raise HTTPException(422, "CSV must be valid UTF-8 with consistent quoting") from exc
