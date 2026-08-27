from datetime import UTC, datetime, timedelta

import networkx as nx
from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import or_, select

from app.api.deps import CurrentUser, DB
from app.models.domain import FraudRing, FraudRingMember, GraphEdge, GraphNode

router = APIRouter(tags=["graph intelligence"])


@router.get("/graph")
async def get_graph(user: CurrentUser, db: DB, node_type: str | None = None, min_risk: float = Query(0, ge=0, le=1), hours: int = Query(168, ge=1, le=8760), limit: int = Query(250, ge=10, le=1000)) -> dict:
    nodes_query = select(GraphNode).where(GraphNode.workspace_id == user.workspace_id, GraphNode.risk_score >= min_risk)
    if node_type:
        nodes_query = nodes_query.where(GraphNode.node_type == node_type.upper())
    nodes = list((await db.execute(nodes_query.order_by(GraphNode.risk_score.desc()).limit(limit))).scalars().all())
    ids = {node.id for node in nodes}
    edges = []
    if ids:
        edges = list((await db.execute(select(GraphEdge).where(GraphEdge.workspace_id == user.workspace_id, GraphEdge.source_node_id.in_(ids), GraphEdge.target_node_id.in_(ids), GraphEdge.occurred_at >= datetime.now(UTC) - timedelta(hours=hours)).limit(limit * 4))).scalars().all())
    graph = nx.Graph()
    graph.add_edges_from((edge.source_node_id, edge.target_node_id) for edge in edges)
    communities: dict[str, int] = {}
    if graph.number_of_edges():
        for index, group in enumerate(nx.community.greedy_modularity_communities(graph)):
            for node_id in group:
                communities[node_id] = index
    return {
        "nodes": [{"data": {"id": node.id, "entity_id": node.entity_id, "label": node.label, "type": node.node_type, "risk": node.risk_score, "community": communities.get(node.id, -1), **node.properties}} for node in nodes],
        "edges": [{"data": {"id": edge.id, "source": edge.source_node_id, "target": edge.target_node_id, "type": edge.edge_type, "weight": edge.weight, "occurred_at": edge.occurred_at.isoformat()}} for edge in edges],
        "meta": {"nodes": len(nodes), "edges": len(edges), "communities": len(set(communities.values())), "generated_at": datetime.now(UTC).isoformat()},
    }


@router.get("/graph/node/{node_id}")
async def graph_node(node_id: str, user: CurrentUser, db: DB) -> dict:
    node = (await db.execute(select(GraphNode).where(GraphNode.id == node_id, GraphNode.workspace_id == user.workspace_id))).scalar_one_or_none()
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    edges = (await db.execute(select(GraphEdge).where(GraphEdge.workspace_id == user.workspace_id, or_(GraphEdge.source_node_id == node.id, GraphEdge.target_node_id == node.id)).limit(100))).scalars().all()
    return {"id": node.id, "entity_id": node.entity_id, "type": node.node_type, "label": node.label, "risk": node.risk_score, "properties": node.properties, "edges": [{"id": edge.id, "source": edge.source_node_id, "target": edge.target_node_id, "type": edge.edge_type} for edge in edges]}


@router.get("/graph/transaction/{transaction_id}")
async def transaction_graph(transaction_id: str, user: CurrentUser, db: DB) -> dict:
    node = (await db.execute(select(GraphNode).where(GraphNode.workspace_id == user.workspace_id, GraphNode.entity_id == transaction_id, GraphNode.node_type == "TRANSACTION"))).scalar_one_or_none()
    if not node:
        raise HTTPException(status_code=404, detail="Transaction graph not found")
    edge_rows = list((await db.execute(select(GraphEdge).where(GraphEdge.workspace_id == user.workspace_id, or_(GraphEdge.source_node_id == node.id, GraphEdge.target_node_id == node.id)))).scalars().all())
    ids = {node.id, *[edge.source_node_id for edge in edge_rows], *[edge.target_node_id for edge in edge_rows]}
    nodes = list((await db.execute(select(GraphNode).where(GraphNode.id.in_(ids)))).scalars().all())
    return {"nodes": [{"data": {"id": item.id, "label": item.label, "type": item.node_type, "risk": item.risk_score}} for item in nodes], "edges": [{"data": {"id": edge.id, "source": edge.source_node_id, "target": edge.target_node_id, "type": edge.edge_type}} for edge in edge_rows]}


@router.get("/fraud-rings")
async def list_rings(user: CurrentUser, db: DB) -> list[dict]:
    rings = (await db.execute(select(FraudRing).where(FraudRing.workspace_id == user.workspace_id).order_by(FraudRing.risk_score.desc()))).scalars().all()
    output = []
    for ring in rings:
        members = (await db.execute(select(FraudRingMember).where(FraudRingMember.ring_id == ring.id))).scalars().all()
        output.append({"id": ring.id, "name": ring.name, "risk_score": ring.risk_score, "risk_level": "CRITICAL" if ring.risk_score >= .9 else "HIGH", "reason": ring.reason, "estimated_amount": ring.estimated_amount, "properties": ring.properties, "members": [{"id": member.entity_id, "type": member.entity_type} for member in members], "created_at": ring.created_at})
    return output


@router.get("/fraud-rings/{ring_id}")
async def get_ring(ring_id: str, user: CurrentUser, db: DB) -> dict:
    rings = await list_rings(user, db)
    ring = next((item for item in rings if item["id"] == ring_id), None)
    if not ring:
        raise HTTPException(status_code=404, detail="Fraud ring not found")
    return ring

