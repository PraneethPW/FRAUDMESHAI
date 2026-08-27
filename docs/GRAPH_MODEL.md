# Graph model

FraudMesh stores graph state inside PostgreSQL rather than requiring Neo4j.

## Node types

`CUSTOMER`, `ACCOUNT`, `TRANSACTION`, `MERCHANT`, `DEVICE`, `IP`, and `LOCATION`.

## Edge types

`OWNS`, `SENDS`, `RECEIVES`, `PAID_TO`, `USES_DEVICE`, `SEEN_FROM_IP`, `LOCATED_AT`, and `INTERACTED_WITH`. Current ingestion creates the applicable ownership, sender, payment, device, IP, and location edges with timestamps and transaction references.

## Projection and ring detection

The graph API fetches a bounded, workspace-scoped, time-windowed subgraph. NetworkX projects it for greedy modularity communities. The ring detector also inspects high-risk shared-device clusters: three or more distinct accounts on the same device with elevated risk create a persisted ring, evidence properties, members, estimated amount, and a notification.

The React Cytoscape explorer receives `{nodes, edges, meta}`, limits the visible graph, and provides pan, zoom, drag, focus, type/risk filters, fit, layout reset, neighborhood expansion, community labels, and suspicious-edge highlighting.

## Temporal upgrade path

A PyTorch Geometric projection should map entity types to node feature matrices, relational edge types to edge indices, and `occurred_at` to time encodings. A production TGN memory can then consume the same ordered edge stream. The current time-aware ensemble and temporal neural surrogate preserve the product and persistence interfaces for this replacement.

