# Demonstration flow

1. Run migrations and the development seed.
2. Sign in as `analyst@fraudmesh.dev` with `FraudMesh!2026`.
3. Open **Live monitor** and confirm the `SIMULATED DATA` label and connected WebSocket.
4. Set 5 events/second and start simulation.
5. Watch ordinary events and a coordinated DEV-X104 sequence arrive without refresh.
6. Open a high-risk event to inspect computed factors, reasons, model version, and its graph neighborhood.
7. Open **Alert center**, select the generated alert, and begin review.
8. Inspect the XAI contributions, evidence list, suspicious timeline, and human decision controls.
9. Select **Generate briefing**. With no key, show the graceful unavailable message; with a provider configured, show the grounded summary.
10. Open **Graph explorer**, search for `DEV-X104`, expand its neighborhood, filter to high risk, and highlight suspicious paths.
11. Open **Fraud rings** and review the shared-device cluster, members, estimated amount, and detection reason.
12. Create a case from the ring or alert.
13. Open **Cases**, change the status to Investigating, add an analyst note, and record a decision.
14. Show the case timeline and preserved evidence snapshot.
15. Open **Model Lab**, execute Logistic Regression, then Temporal GNN, and compare generated metrics/curves.
16. Sign in as `admin@fraudmesh.dev` to show users, thresholds, model version, provider status, and audit actions.
17. Return to **Overview** to show updated transaction, alert, ring, and case totals.

Narrative: several individually plausible transfers converge on one device and IP across multiple accounts. FraudMesh detects the coordinated infrastructure, explains the temporal/graph factors, preserves the evidence, and accelerates—but never replaces—the analyst's decision.

