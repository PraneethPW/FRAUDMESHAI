import asyncio

from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from app.api.deps import CurrentUser, DB
from app.ml.baselines import train_and_evaluate
from app.models.domain import ModelMetric, Notification, TrainingRun
from app.schemas.domain import ModelTrainRequest
from app.services.audit import audit
from app.websocket.manager import manager

router = APIRouter(prefix="/models", tags=["model lab"])


@router.post("/train", status_code=201)
async def train(payload: ModelTrainRequest, user: CurrentUser, db: DB) -> dict:
    try:
        metrics = await asyncio.to_thread(train_and_evaluate, payload.model_type, payload.samples)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Training failed: {exc}") from exc
    run = TrainingRun(workspace_id=user.workspace_id, model_type=payload.model_type, metrics=metrics, created_by=user.id)
    db.add(run)
    await db.flush()
    for name in ["precision", "recall", "f1", "roc_auc", "pr_auc", "false_positive_rate", "inference_latency_ms"]:
        db.add(ModelMetric(run_id=run.id, name=name, value=float(metrics[name])))
    db.add(Notification(workspace_id=user.workspace_id, user_id=user.id, title="Model training completed", message=f"{payload.model_type} · F1 {metrics['f1']:.3f}", kind="MODEL_TRAINED"))
    await audit(db, user.workspace_id, "MODEL_TRAINED", user.id, "training_run", run.id, {"model_type": payload.model_type, "samples": payload.samples})
    await db.commit()
    await manager.broadcast(user.workspace_id, "model.training.completed", {"id": run.id, "model_type": run.model_type, "metrics": metrics})
    return {"id": run.id, "model_type": run.model_type, "status": run.status, "metrics": metrics, "created_at": run.created_at}


@router.get("/runs")
async def runs(user: CurrentUser, db: DB) -> list[dict]:
    items = (await db.execute(select(TrainingRun).where(TrainingRun.workspace_id == user.workspace_id).order_by(TrainingRun.created_at.desc()).limit(50))).scalars().all()
    return [{"id": item.id, "model_type": item.model_type, "status": item.status, "dataset_name": item.dataset_name, "metrics": item.metrics, "created_at": item.created_at} for item in items]


@router.get("/metrics")
async def metrics(user: CurrentUser, db: DB) -> list[dict]:
    return await runs(user, db)

