import jwt
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.security import decode_token
from app.websocket.manager import manager

router = APIRouter(tags=["websocket"])


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str | None = None) -> None:
    if not token:
        await websocket.close(code=4401)
        return
    try:
        payload = decode_token(token)
    except jwt.PyJWTError:
        await websocket.close(code=4401)
        return
    workspace_id = payload["workspace_id"]
    await manager.connect(workspace_id, websocket)
    await websocket.send_json({"event": "system.status", "data": {"state": "CONNECTED", "mode": "SIMULATED DATA"}})
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(workspace_id, websocket)

