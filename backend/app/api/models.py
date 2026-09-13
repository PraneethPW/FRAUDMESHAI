import asyncio
from fastapi import APIRouter, HTTPException
from sqlalchemy import select, update
from app.api.deps import CurrentUser, DB
from app.api.admin import AdminUser
from app.ml.baselines.training import train_model
from app.ml.graph.context import record
from app.models.domain import ModelArtifact, TrainingRun, Transaction, TransactionLabel, Notification
from app.schemas.domain import ModelTrainRequest
from app.services.audit import audit
from app.services.locking import workspace_lock
from app.websocket.manager import manager

router = APIRouter(prefix="/models", tags=["model lab"])
_training = False


@router.post("/train", status_code=201)
async def train(payload: ModelTrainRequest, user: CurrentUser, db: DB):
    global _training
    if _training:
        raise HTTPException(409, "A training run is already in progress. Try again after it completes.")
    _training = True
    try:
        rows = None
        if payload.dataset == "WORKSPACE":
            data = (
                await db.execute(
                    select(Transaction, TransactionLabel.is_fraud)
                    .outerjoin(TransactionLabel, TransactionLabel.transaction_id == Transaction.id)
                    .where(Transaction.workspace_id == user.workspace_id)
                    .order_by(Transaction.occurred_at, Transaction.id)
                    .limit(payload.samples)
                )
            ).all()
            rows = [{**record(tx), "is_fraud": label} for tx, label in data]
        metrics, artifact = await asyncio.to_thread(train_model, payload.model_type, payload.samples, rows)
        run = TrainingRun(
            workspace_id=user.workspace_id,
            model_type=payload.model_type,
            metrics=metrics,
            created_by=user.id,
            dataset_name="Synthetic motif benchmark v2" if rows is None else "Workspace labelled transactions",
        )
        db.add(run)
        await db.flush()
        db.add(ModelArtifact(run_id=run.id, workspace_id=user.workspace_id, artifact=artifact))
        db.add(
            Notification(
                workspace_id=user.workspace_id,
                user_id=user.id,
                title="Model training completed",
                message=f'{payload.model_type} · held-out F1 {metrics["f1"]:.3f}',
                kind="MODEL_TRAINED",
            )
        )
        await audit(
            db,
            user.workspace_id,
            "MODEL_TRAINED",
            user.id,
            "training_run",
            run.id,
            {"model_type": payload.model_type, "dataset": payload.dataset, "dataset_sha256": metrics["dataset_sha256"]},
        )
        await db.commit()
        result = {
            "id": run.id,
            "model_type": run.model_type,
            "status": run.status,
            "dataset_name": run.dataset_name,
            "metrics": metrics,
            "created_at": run.created_at,
            "active": False,
            "can_activate": True,
        }
        await manager.broadcast(user.workspace_id, "model.training.completed", {"id": run.id})
        return result
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    finally:
        _training = False


@router.get("/runs")
async def runs(user: CurrentUser, db: DB):
    items = (
        await db.execute(
            select(TrainingRun, ModelArtifact.id, ModelArtifact.active)
            .outerjoin(ModelArtifact, ModelArtifact.run_id == TrainingRun.id)
            .where(TrainingRun.workspace_id == user.workspace_id)
            .order_by(TrainingRun.created_at.desc())
            .limit(50)
        )
    ).all()
    return [
        {
            "id": r.id,
            "model_type": r.model_type,
            "status": r.status,
            "dataset_name": r.dataset_name,
            "metrics": r.metrics,
            "created_at": r.created_at,
            "active": bool(active),
            "can_activate": bool(aid),
        }
        for r, aid, active in items
    ]


@router.get("/metrics")
async def metrics(user: CurrentUser, db: DB):
    return await runs(user, db)


@router.post("/runs/{run_id}/activate")
async def activate(run_id: str, user: AdminUser, db: DB):
    async with workspace_lock(db, user.workspace_id):
        item = (
            await db.execute(select(ModelArtifact).where(ModelArtifact.run_id == run_id, ModelArtifact.workspace_id == user.workspace_id))
        ).scalar_one_or_none()
        if not item:
            raise HTTPException(404, "Trained artifact not found; legacy runs must be retrained.")
        await db.execute(update(ModelArtifact).where(ModelArtifact.workspace_id == user.workspace_id).values(active=False))
        item.active = True
        await audit(
            db, user.workspace_id, "MODEL_ACTIVATED", user.id, "training_run", run_id, {"training_source": item.artifact["dataset"]}
        )
        await db.commit()
    await manager.broadcast(user.workspace_id, "model.activated", {"run_id": run_id})
    return {"active_run_id": run_id, "dataset": item.artifact["dataset"]}


@router.post("/deactivate")
async def deactivate(user: AdminUser, db: DB):
    async with workspace_lock(db, user.workspace_id):
        await db.execute(update(ModelArtifact).where(ModelArtifact.workspace_id == user.workspace_id).values(active=False))
        await audit(db, user.workspace_id, "MODEL_DEACTIVATED", user.id, "model")
        await db.commit()
    await manager.broadcast(user.workspace_id, "model.activated", {"run_id": None})
    return {"active_run_id": None, "fallback": "time-aware-graph-ensemble-v2"}


@router.get("/runs/{run_id}/export")
async def export(run_id: str, user: CurrentUser, db: DB):
    run = (
        await db.execute(select(TrainingRun).where(TrainingRun.id == run_id, TrainingRun.workspace_id == user.workspace_id))
    ).scalar_one_or_none()
    if not run:
        raise HTTPException(404, "Model run not found")
    return {
        "id": run.id,
        "model_type": run.model_type,
        "dataset_name": run.dataset_name,
        "metrics": run.metrics,
        "created_at": run.created_at,
    }
