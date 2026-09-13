import asyncio
from fastapi import WebSocket


class ConnectionManager:
    def __init__(self) -> None:
        self.connections: dict[str, set[WebSocket]] = {}

    async def connect(self, workspace_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        self.connections.setdefault(workspace_id, set()).add(websocket)

    def disconnect(self, workspace_id: str, websocket: WebSocket) -> None:
        self.connections.get(workspace_id, set()).discard(websocket)
        if not self.connections.get(workspace_id):
            self.connections.pop(workspace_id, None)

    async def broadcast(self, workspace_id: str, event: str, data: dict) -> None:
        stale: list[WebSocket] = []
        for connection in self.connections.get(workspace_id, set()).copy():
            try:
                await asyncio.wait_for(connection.send_json({"event": event, "data": data}), timeout=1)
            except Exception:
                stale.append(connection)
        for connection in stale:
            self.disconnect(workspace_id, connection)


manager = ConnectionManager()
