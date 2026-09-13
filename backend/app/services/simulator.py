import asyncio
import logging
import random
import uuid
from datetime import UTC, datetime
from app.core.database import SessionLocal
from app.schemas.domain import TransactionCreate
from app.services.transactions import ingest_transaction
from app.websocket.manager import manager


class Simulator:
    def __init__(self, workspace_id):
        self.workspace_id = workspace_id
        self.state = "STOPPED"
        self.speed = 1
        self.sequence = 0
        self.task = None
        self.run_id = uuid.uuid4().hex[:10]
        self.error = None

    def status(self):
        return {"state": self.state, "speed": self.speed, "sequence": self.sequence, "mode": "SIMULATED DATA", "error": self.error}

    async def start(self, speed):
        self.speed = speed
        self.state = "RUNNING"
        self.error = None
        if not self.task or self.task.done():
            self.task = asyncio.create_task(self._run())
        await manager.broadcast(self.workspace_id, "simulation.status", self.status())
        return self.status()

    async def pause(self):
        self.state = "PAUSED"
        await manager.broadcast(self.workspace_id, "simulation.status", self.status())
        return self.status()

    async def stop(self):
        self.state = "STOPPED"
        if self.task:
            try:
                await asyncio.wait_for(asyncio.shield(self.task), timeout=10)
            except asyncio.TimeoutError:
                self.task.cancel()
                try:
                    await self.task
                except asyncio.CancelledError:
                    pass
            self.task = None
        await manager.broadcast(self.workspace_id, "simulation.status", self.status())
        return self.status()

    async def _run(self):
        # Explicit, finite runs prevent a forgotten browser tab generating unbounded cost.
        generated = 0
        try:
            while self.state != "STOPPED":
                if self.state == "PAUSED":
                    await asyncio.sleep(0.5)
                    continue
                self.sequence += 1
                coordinated = self.sequence % 10 in (0, 1, 2, 3)
                account = f"ACC-{701+self.sequence%4}" if coordinated else f"ACC-{random.randint(100,699)}"
                async with SessionLocal() as db:
                    await ingest_transaction(
                        db,
                        self.workspace_id,
                        TransactionCreate(
                            external_id=f"SIM-{self.run_id}-{self.sequence:07d}",
                            account_id=account,
                            customer_id=f"CUS-{account}",
                            merchant_id="M-104",
                            merchant_name="Northstar Electronics",
                            amount=round(random.uniform(4800, 9200) if coordinated else random.uniform(18, 2600), 2),
                            device_id="DEV-X104" if coordinated else f"DEV-{account}",
                            ip_address="198.51.100.44" if coordinated else f"10.24.1.{random.randint(2,240)}",
                            location=random.choice(["Mumbai, IN", "Dubai, AE"]) if coordinated else "Mumbai, IN",
                            occurred_at=datetime.now(UTC),
                            source="SIMULATION",
                            is_fraud=coordinated,
                        ),
                    )
                generated += 1
                if generated >= 500:
                    self.state = "STOPPED"
                    break
                await asyncio.sleep(1 / self.speed)
        except asyncio.CancelledError:
            raise
        except Exception:
            logging.getLogger(__name__).exception("Simulation failed")
            self.state = "ERROR"
            self.error = "Ingestion failed. Check service health before restarting."
        finally:
            await manager.broadcast(self.workspace_id, "simulation.status", self.status())


class SimulatorRegistry:
    def __init__(self):
        self.items = {}

    def get(self, workspace_id):
        return self.items.setdefault(workspace_id, Simulator(workspace_id))

    async def shutdown(self):
        for item in list(self.items.values()):
            await item.stop()
        self.items.clear()


simulators = SimulatorRegistry()
