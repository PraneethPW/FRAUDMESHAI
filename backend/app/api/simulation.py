from fastapi import APIRouter, HTTPException

from app.api.deps import CurrentUser
from app.core.config import settings
from app.schemas.domain import SimulationRequest
from app.services.simulator import simulator

router = APIRouter(prefix="/simulation", tags=["simulation"])


@router.post("/start")
async def start(payload: SimulationRequest, user: CurrentUser) -> dict:
    if not settings.simulation_enabled:
        raise HTTPException(status_code=403, detail="Simulation is disabled")
    return await simulator.start(user.workspace_id, payload.speed)


@router.post("/pause")
async def pause(user: CurrentUser) -> dict:
    if simulator.workspace_id and simulator.workspace_id != user.workspace_id:
        raise HTTPException(status_code=403, detail="Simulation belongs to another workspace")
    return await simulator.pause()


@router.post("/stop")
async def stop(user: CurrentUser) -> dict:
    if simulator.workspace_id and simulator.workspace_id != user.workspace_id:
        raise HTTPException(status_code=403, detail="Simulation belongs to another workspace")
    return await simulator.stop()


@router.get("/status")
async def status(user: CurrentUser) -> dict:
    return simulator.status()

