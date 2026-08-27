import asyncio
import random
from datetime import UTC, datetime

from app.core.database import SessionLocal
from app.schemas.domain import TransactionCreate
from app.services.transactions import ingest_transaction
from app.websocket.manager import manager


class Simulator:
    def __init__(self) -> None:
        self.state = "STOPPED"
        self.speed = 1
        self.workspace_id: str | None = None
        self.task: asyncio.Task | None = None
        self.sequence = 0

    async def start(self, workspace_id: str, speed: int) -> dict:
        self.workspace_id, self.speed, self.state = workspace_id, speed, "RUNNING"
        if not self.task or self.task.done():
            self.task = asyncio.create_task(self._run())
        await manager.broadcast(workspace_id, "system.status", self.status())
        return self.status()

    async def pause(self) -> dict:
        self.state = "PAUSED"
        if self.workspace_id:
            await manager.broadcast(self.workspace_id, "system.status", self.status())
        return self.status()

    async def stop(self) -> dict:
        self.state = "STOPPED"
        if self.task:
            self.task.cancel()
            self.task = None
        if self.workspace_id:
            await manager.broadcast(self.workspace_id, "system.status", self.status())
        return self.status()

    def status(self) -> dict:
        return {"state": self.state, "speed": self.speed, "sequence": self.sequence, "mode": "SIMULATED DATA"}

    async def _run(self) -> None:
        merchants = [("M-104", "Northstar Electronics"), ("M-221", "Orbit Travel"), ("M-390", "Meridian Market"), ("M-088", "Atlas Digital")]
        locations = ["Mumbai, IN", "Bengaluru, IN", "Delhi, IN", "Singapore, SG", "Dubai, AE"]
        while self.state != "STOPPED":
            if self.state == "PAUSED":
                await asyncio.sleep(.2)
                continue
            self.sequence += 1
            coordinated = self.sequence % 5 in {0, 1, 2}
            account = f"ACC-{(self.sequence % 3) + 701}" if coordinated else f"ACC-{random.randint(100, 699)}"
            merchant_id, merchant_name = merchants[self.sequence % len(merchants)]
            payload = TransactionCreate(
                external_id=f"SIM-{self.sequence:07d}", account_id=account, customer_id=f"CUS-{account[-3:]}", merchant_id=merchant_id,
                merchant_name=merchant_name, amount=round(random.uniform(4800, 9200) if coordinated else random.uniform(18, 2600), 2),
                device_id="DEV-X104" if coordinated else f"DEV-{random.randint(200, 950)}", ip_address="185.71.67.44" if coordinated else f"10.24.{random.randint(1, 20)}.{random.randint(2, 240)}",
                location=locations[(self.sequence + (2 if coordinated else 0)) % len(locations)], occurred_at=datetime.now(UTC), source="SIMULATION")
            if self.workspace_id:
                async with SessionLocal() as db:
                    try:
                        await ingest_transaction(db, self.workspace_id, payload)
                    except Exception:
                        await db.rollback()
            await asyncio.sleep(1 / self.speed)


simulator = Simulator()

