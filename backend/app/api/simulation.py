from fastapi import APIRouter, HTTPException

from app.api.deps import CurrentUser
from app.core.config import settings
from app.schemas.domain import SimulationRequest
from app.services.simulator import simulators

router = APIRouter(prefix="/simulation", tags=["simulation"])


@router.post("/start")
async def start(payload: SimulationRequest, user: CurrentUser) -> dict:
    if not settings.simulation_enabled:
        raise HTTPException(status_code=403, detail="Simulation is disabled")
    return await simulators.get(user.workspace_id).start(payload.speed)


@router.post("/pause")
async def pause(user: CurrentUser) -> dict:
    return await simulators.get(user.workspace_id).pause()


@router.post("/stop")
async def stop(user: CurrentUser) -> dict:
    return await simulators.get(user.workspace_id).stop()


@router.get("/status")
async def status(user: CurrentUser) -> dict:
    return simulators.get(user.workspace_id).status()
