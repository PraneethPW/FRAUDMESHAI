import asyncio
import time
import jwt
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.core.security import decode_token
from app.core.database import SessionLocal
from app.models.domain import User
from app.websocket.manager import manager

router = APIRouter(tags=["websocket"])
HEARTBEAT_SECONDS = 30


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str | None = None):
    try:
        if not token:
            raise ValueError()
        payload = decode_token(token)
        async with SessionLocal() as db:
            user = await db.get(User, payload["sub"])
            if not user or not user.is_active or user.workspace_id != payload["workspace_id"]:
                raise ValueError()
            workspace_id = user.workspace_id
    except (jwt.PyJWTError, ValueError, KeyError):
        await websocket.close(code=4401)
        return
    await manager.connect(workspace_id, websocket)
    try:
        await websocket.send_json({"event": "system.status", "data": {"state": "CONNECTED"}})
        while True:
            if time.time() >= payload["exp"]:
                await websocket.close(code=4401)
                return
            try:
                await asyncio.wait_for(websocket.receive_text(), timeout=min(HEARTBEAT_SECONDS, max(1, payload["exp"] - time.time())))
            except asyncio.TimeoutError:
                async with SessionLocal() as db:
                    user = await db.get(User, payload["sub"])
                    if not user or not user.is_active:
                        await websocket.close(code=4401)
                        return
                await websocket.send_json({"event": "heartbeat", "data": {}})
            # A pong is an acknowledgement, not another request for a heartbeat.
    except (WebSocketDisconnect, RuntimeError):
        pass
    finally:
        manager.disconnect(workspace_id, websocket)
