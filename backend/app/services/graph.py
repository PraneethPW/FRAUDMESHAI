from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.domain import GraphEdge, GraphNode, Transaction


async def _node(db: AsyncSession, transaction: Transaction, entity_id: str, node_type: str, label: str, risk: float = 0, properties: dict | None = None) -> GraphNode:
    node = (await db.execute(select(GraphNode).where(GraphNode.workspace_id == transaction.workspace_id, GraphNode.entity_id == entity_id, GraphNode.node_type == node_type))).scalar_one_or_none()
    if not node:
        node = GraphNode(workspace_id=transaction.workspace_id, entity_id=entity_id, node_type=node_type, label=label, risk_score=risk, properties=properties or {})
        db.add(node)
        await db.flush()
    elif risk > node.risk_score:
        node.risk_score = risk
    return node


async def update_graph(db: AsyncSession, transaction: Transaction) -> None:
    tx = await _node(db, transaction, transaction.id, "TRANSACTION", transaction.external_id, transaction.risk_score, {"amount": transaction.amount})
    account = await _node(db, transaction, transaction.account_id, "ACCOUNT", transaction.account_id, transaction.risk_score * 0.8)
    merchant = await _node(db, transaction, transaction.merchant_id, "MERCHANT", transaction.merchant_name, transaction.risk_score * 0.5)
    device = await _node(db, transaction, transaction.device_id, "DEVICE", transaction.device_id, transaction.risk_score * 0.7)
    ip = await _node(db, transaction, transaction.ip_address, "IP", transaction.ip_address, transaction.risk_score * 0.65)
    location = await _node(db, transaction, transaction.location, "LOCATION", transaction.location, transaction.risk_score * 0.25)
    nodes = [(account, tx, "SENDS"), (tx, merchant, "PAID_TO"), (account, device, "USES_DEVICE"), (account, ip, "SEEN_FROM_IP"), (tx, location, "LOCATED_AT")]
    if transaction.customer_id:
        customer = await _node(db, transaction, transaction.customer_id, "CUSTOMER", transaction.customer_id, transaction.risk_score * 0.6)
        nodes.append((customer, account, "OWNS"))
    for source, target, edge_type in nodes:
        db.add(GraphEdge(workspace_id=transaction.workspace_id, source_node_id=source.id, target_node_id=target.id, edge_type=edge_type, occurred_at=transaction.occurred_at, weight=max(0.1, transaction.risk_score), properties={"transaction_id": transaction.id}))

