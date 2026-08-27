# ML pipeline

## Online feature generation

The online scorer derives its evidence from persisted workspace data at ingestion time:

- amount, UTC hour, unusual-hour flag;
- time since the previous account event;
- rolling account count and velocity;
- 24-hour merchant frequency;
- new-device and location-change flags;
- distinct accounts sharing the device and IP;
- graph relationship, neighborhood, device-sharing, and location contributions.

Contributions are normalized into a bounded probability and mapped through configurable medium/high/critical thresholds. Each `fraud_scores` row stores the probability, risk level, model version, prediction time, feature values, ordered contributions, and human-readable reasons. Transaction detail and alert XAI use that stored object instead of generating random UI scores.

## Model Lab

Every training action executes an estimator over a reproducible, imbalanced classification dataset augmented with time decay, graph degree, and neighbor-risk fields. Train/test splitting is stratified. Persisted metrics include precision, recall, F1, ROC-AUC, PR-AUC, false-positive rate, confusion matrix, ROC/PR curve samples, training time, and inference latency.

| Model selection | Executed implementation |
|---|---|
| Logistic Regression | Balanced scikit-learn LogisticRegression |
| XGBoost | XGBClassifier |
| Static GNN | MLP neural surrogate over graph/neighborhood features |
| Temporal GNN | MLP neural surrogate over graph + time-decay/rolling features |

The last two are deliberately identified as practical surrogates, not full message-memory TGN training. `ml/graph` and `ml/temporal` are the replacement boundary for GraphSAGE/GAT/TGN/TGAT implementations using optional `requirements-gnn.txt`.

## Explainability

Baseline/online explanations use traceable feature contributions. Graph explanations include important shared infrastructure, suspicious paths, connected high-risk entities, temporal velocity, and neighborhood risk. GNNExplainer and SHAP are deferred optional research integrations; application correctness does not depend on their native build stability.
