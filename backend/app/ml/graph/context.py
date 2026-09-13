"""Causal transaction->entity->transaction message neighborhoods, shared by training and serving."""

import math
from datetime import UTC, datetime, timedelta
import numpy as np
from sqlalchemy import select
from app.models.domain import Transaction

RELATIONS = ("account_id", "device_id", "ip_address", "merchant_id")
FEATURE_NAMES = (
    "log_amount",
    "hour_sin",
    "hour_cos",
    "account_count",
    "device_accounts",
    "ip_accounts",
    "merchant_count",
    "recency",
    "new_device",
    "location_change",
)
WINDOW_HOURS = 24
NEIGHBORS = 32


def utc(value):
    if isinstance(value, str):
        value = datetime.fromisoformat(value)
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def record(tx):
    return {key: getattr(tx, key) for key in ("id", "amount", "currency", "occurred_at", "location", "source", *RELATIONS)}


def basic(row):
    hour = utc(row["occurred_at"]).hour
    return [math.log1p(row["amount"]) / 10, math.sin(hour * math.pi / 12), math.cos(hour * math.pi / 12)]


def encode(row, groups, temporal=True):
    """Only earlier event times enter any feature; labels and risk scores are never inputs."""
    at = utc(row["occurred_at"])
    groups = [[r for r in group if at - timedelta(hours=24) <= utc(r["occurred_at"]) < at] for group in groups]
    account, device, ip, merchant = groups
    previous = account[-1] if account else None
    gap = (at - utc(previous["occurred_at"])).total_seconds() if previous else 86400
    features = basic(row) + [
        len(account) / 32,
        len({r["account_id"] for r in device}) / 8,
        len({r["account_id"] for r in ip}) / 8,
        len(merchant) / 32,
        math.exp(-gap / 3600),
        float(not any(r["device_id"] == row["device_id"] for r in account)),
        float(bool(previous and previous["location"] != row["location"])),
    ]
    messages, neighbors = [], []
    for relation, group in zip(RELATIONS, groups):
        group = group[-NEIGHBORS:]
        vectors = []
        for r in group:
            # A raw event message; no label-derived neighborhood risk.
            age = (at - utc(r["occurred_at"])).total_seconds()
            weight = math.exp(-age / 3600) if temporal else 1.0
            vector = basic(r) + [
                float(r["account_id"] == row["account_id"]),
                float(r["device_id"] == row["device_id"]),
                float(r["ip_address"] == row["ip_address"]),
                float(r["merchant_id"] == row["merchant_id"]),
                math.exp(-age / 3600) if temporal else 0.0,
                float(r["location"] == row["location"]),
                1.0,
            ]
            vectors.append(np.asarray(vector) * weight)
            neighbors.append(
                {
                    "transaction_id": r.get("id"),
                    "relation": relation,
                    "entity_id": row[relation],
                    "occurred_at": utc(r["occurred_at"]).isoformat(),
                    "weight": round(weight, 5),
                }
            )
        messages.append(np.mean(vectors, axis=0) if vectors else np.zeros(10))
    return np.asarray(features, dtype=float), np.asarray(messages), neighbors


async def load_groups(db, tx):
    groups = []
    for relation in RELATIONS:
        rows = (
            (
                await db.execute(
                    select(Transaction)
                    .where(
                        Transaction.workspace_id == tx.workspace_id,
                        getattr(Transaction, relation) == getattr(tx, relation),
                        Transaction.occurred_at < tx.occurred_at,
                        Transaction.occurred_at >= tx.occurred_at - timedelta(hours=24),
                        Transaction.currency == tx.currency,
                        Transaction.id != tx.id,
                    )
                    .order_by(Transaction.occurred_at.desc(), Transaction.id.desc())
                    .limit(NEIGHBORS)
                )
            )
            .scalars()
            .all()
        )
        groups.append([record(row) for row in reversed(rows)])
    return groups


def encode_dataset(rows, temporal=True):
    from collections import defaultdict, deque

    history = [defaultdict(lambda: deque(maxlen=NEIGHBORS)) for _ in RELATIONS]
    features, messages = [], []
    from itertools import groupby

    for _, simultaneous in groupby(rows, key=lambda r: utc(r["occurred_at"])):
        batch = list(simultaneous)
        for row in batch:
            groups = [list(index[(row["currency"], row[key])]) for index, key in zip(history, RELATIONS)]
            x, m, _ = encode(row, groups, temporal)
            features.append(x)
            messages.append(m)
        for row in batch:
            for index, key in zip(history, RELATIONS):
                index[(row["currency"], row[key])].append(row)
    return np.asarray(features), np.asarray(messages)
