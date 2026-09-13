"""Serialize workspace mutations; PostgreSQL lock also covers multiple workers."""

import asyncio
from contextlib import asynccontextmanager
from weakref import WeakValueDictionary
from sqlalchemy import select
from app.models.domain import Workspace

_locks = WeakValueDictionary()


@asynccontextmanager
async def workspace_lock(db, workspace_id):
    key = (id(asyncio.get_running_loop()), workspace_id)
    lock = _locks.setdefault(key, asyncio.Lock())
    async with lock:
        await db.execute(select(Workspace.id).where(Workspace.id == workspace_id).with_for_update())
        yield
