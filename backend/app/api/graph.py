from datetime import UTC, datetime, timedelta
import networkx as nx
from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import or_, select
from app.api.deps import CurrentUser, DB
from app.models.domain import FraudRing, FraudRingMember, GraphEdge, GraphNode, Transaction

router = APIRouter(tags=["graph intelligence"])


def serialize(nodes, edges):
    g = nx.Graph()
    g.add_nodes_from(n.id for n in nodes)
    g.add_edges_from((e.source_node_id, e.target_node_id) for e in edges)
    communities = {}
    if g.number_of_edges():
        for i, group in enumerate(nx.community.greedy_modularity_communities(g)):
            for nid in group:
                communities[nid] = i
    return {
        "nodes": [
            {
                "data": {
                    **n.properties,
                    "id": n.id,
                    "entity_id": n.entity_id,
                    "label": n.label,
                    "type": n.node_type,
                    "risk": n.risk_score,
                    "community": communities.get(n.id, -1),
                }
            }
            for n in nodes
        ],
        "edges": [
            {
                "data": {
                    "id": e.id,
                    "source": e.source_node_id,
                    "target": e.target_node_id,
                    "type": e.edge_type,
                    "weight": e.weight,
                    "occurred_at": e.occurred_at.isoformat(),
                }
            }
            for e in edges
        ],
        "meta": {
            "nodes": len(nodes),
            "edges": len(edges),
            "communities": len(set(communities.values())),
            "generated_at": datetime.now(UTC).isoformat(),
        },
    }


@router.get("/graph")
async def get_graph(
    user: CurrentUser,
    db: DB,
    node_type: str | None = None,
    min_risk: float = Query(0, ge=0, le=1),
    hours: int = Query(168, ge=1, le=8760),
    limit: int = Query(250, ge=10, le=1000),
):
    since = datetime.now(UTC) - timedelta(hours=hours)
    # Only nodes incident to edges in the requested time window are selected.
    recent = (
        select(GraphEdge.source_node_id)
        .where(GraphEdge.workspace_id == user.workspace_id, GraphEdge.occurred_at >= since)
        .union(select(GraphEdge.target_node_id).where(GraphEdge.workspace_id == user.workspace_id, GraphEdge.occurred_at >= since))
    )
    query = select(GraphNode).where(GraphNode.workspace_id == user.workspace_id, GraphNode.risk_score >= min_risk, GraphNode.id.in_(recent))
    if node_type:
        query = query.where(GraphNode.node_type == node_type.upper())
    nodes = (await db.execute(query.order_by(GraphNode.risk_score.desc()).limit(limit))).scalars().all()
    ids = [n.id for n in nodes]
    edges = (
        (
            await db.execute(
                select(GraphEdge)
                .where(
                    GraphEdge.workspace_id == user.workspace_id,
                    GraphEdge.source_node_id.in_(ids),
                    GraphEdge.target_node_id.in_(ids),
                    GraphEdge.occurred_at >= since,
                )
                .order_by(GraphEdge.occurred_at.desc())
                .limit(limit * 4)
            )
        )
        .scalars()
        .all()
        if ids
        else []
    )
    return serialize(nodes, edges)


@router.get("/graph/node/{node_id}")
async def graph_node(node_id: str, user: CurrentUser, db: DB):
    node = await db.scalar(select(GraphNode).where(GraphNode.id == node_id, GraphNode.workspace_id == user.workspace_id))
    if not node:
        raise HTTPException(404, "Node not found")
    edges = (
        (
            await db.execute(
                select(GraphEdge)
                .where(
                    GraphEdge.workspace_id == user.workspace_id,
                    or_(GraphEdge.source_node_id == node_id, GraphEdge.target_node_id == node_id),
                )
                .order_by(GraphEdge.occurred_at.desc())
                .limit(100)
            )
        )
        .scalars()
        .all()
    )
    ids = {node_id, *[e.source_node_id for e in edges], *[e.target_node_id for e in edges]}
    nodes = (await db.execute(select(GraphNode).where(GraphNode.workspace_id == user.workspace_id, GraphNode.id.in_(ids)))).scalars().all()
    return {
        **serialize(nodes, edges),
        "id": node.id,
        "entity_id": node.entity_id,
        "type": node.node_type,
        "label": node.label,
        "risk": node.risk_score,
        "properties": node.properties,
    }


@router.get("/graph/transaction/{transaction_id}")
async def transaction_graph(transaction_id: str, user: CurrentUser, db: DB):
    tx = await db.scalar(select(Transaction).where(Transaction.id == transaction_id, Transaction.workspace_id == user.workspace_id))
    if not tx:
        raise HTTPException(404, "Transaction graph not found")
    # Include device/IP/customer edges, which do not directly touch the transaction node.
    edges = (
        (
            await db.execute(
                select(GraphEdge).where(
                    GraphEdge.workspace_id == user.workspace_id, GraphEdge.properties["transaction_id"].as_string() == tx.id
                )
            )
        )
        .scalars()
        .all()
    )
    ids = {*[e.source_node_id for e in edges], *[e.target_node_id for e in edges]}
    nodes = (await db.execute(select(GraphNode).where(GraphNode.workspace_id == user.workspace_id, GraphNode.id.in_(ids)))).scalars().all()
    return serialize(nodes, edges)


@router.get("/fraud-rings")
async def list_rings(user: CurrentUser, db: DB):
    rings = (
        (
            await db.execute(
                select(FraudRing).where(FraudRing.workspace_id == user.workspace_id).order_by(FraudRing.updated_at.desc()).limit(200)
            )
        )
        .scalars()
        .all()
    )
    members = (
        (await db.execute(select(FraudRingMember).where(FraudRingMember.ring_id.in_([r.id for r in rings])))).scalars().all()
        if rings
        else []
    )
    grouped = {r.id: [] for r in rings}
    for m in members:
        grouped[m.ring_id].append({"id": m.entity_id, "type": m.entity_type})
    return [
        {
            "id": r.id,
            "name": r.name,
            "risk_score": r.risk_score,
            "risk_level": "CRITICAL" if r.risk_score >= 0.9 else "HIGH",
            "reason": r.reason,
            "estimated_amount": r.estimated_amount,
            "properties": r.properties,
            "members": grouped[r.id],
            "created_at": r.created_at,
            "updated_at": r.updated_at,
        }
        for r in rings
    ]


@router.get("/fraud-rings/{ring_id}")
async def get_ring(ring_id: str, user: CurrentUser, db: DB):
    ring = next((r for r in await list_rings(user, db) if r["id"] == ring_id), None)
    if not ring:
        raise HTTPException(404, "Fraud ring not found")
    return ring
