# Model pipeline — v2

## Causal inputs

Serving and evaluation use the same `ml/graph/context.py` encoder. Accounts, devices, IPs and merchants define transaction → entity → earlier-transaction neighborhoods. Each relation contributes at most 32 previous events from the preceding 24 hours, restricted to the same currency and workspace. Events at the prediction timestamp or later are excluded, including simultaneous batches. Labels, previous risk scores and future account activity never enter model input tensors.

The ten self features represent log amount, UTC hour sine/cosine, recent account/merchant counts, distinct device/IP accounts, recency, device novelty and location change. Neighbor messages encode raw event amount, time and shared relationships. Entity identifiers are used for adjacency, not as numeric features.

## Executed models

| Selection | Implementation | Persistence |
|---|---|---|
| Logistic Regression | Balanced scikit-learn logistic classifier | JSON coefficients and scaler |
| XGBoost | CPU boosted trees, one thread | XGBoost JSON model and scaler |
| Static GNN | Learned relation-specific mean message passing and transaction self projection | JSON neural weights and scaler |
| Temporal GNN | Same neural architecture with exponential edge-time decay (one-hour decay constant) | JSON neural weights and scaler |

The graph networks implement `h_r = tanh(mean_j(w_time * x_j) W_r + b_r)`. A learned readout combines the four relation embeddings with a learned transaction embedding. All weights are trained by backpropagation with Adam and class-weighted binary cross-entropy. The compact NumPy implementation needs no GPU/PyTorch installation and is inspectable in `ml/temporal/network.py`. This is a one-layer time-decayed GraphSAGE-style model, **not an implementation of full TGN recurrent memory or TGAT attention**.

No model is silently activated. An administrator can activate one saved run for the workspace or restore the heuristic scorer. Artifacts are stored in PostgreSQL/SQLite and survive process restarts and Railway redeploys. Historic predictions retain their original model version, threshold and evidence. Legacy v1 evaluation runs lack deployable weights and must be retrained.

## Datasets and evaluation

- Synthetic: deterministic seed-42 transaction motifs with coordinated shared-infrastructure activity, ordinary activity and label noise. Labels are generated separately and never used as input features.
- Workspace: earliest `samples` stored events in chronological order. Unlabelled events can supply prior graph context; only labelled events become supervised samples. Labels come from the optional CSV/API `is_fraud` field or analyst review. At least 100 labelled events and both classes in each split are required. Workspace data can contain simulation; source counts are recorded.
- Split: earliest 60% training, following 20% validation, latest 20% test. Timestamp ties are kept in one partition. Scalers fit only the training set; the decision threshold is selected using validation F1.
- Labels are evaluated retrospectively as currently known. This is **not** an online delayed-label backtest. Label-quality review is required before drawing research conclusions.
- Results: precision, recall, F1, ROC-AUC, PR-AUC, false-positive rate, confusion matrix, ROC/PR curves, sample/split sizes, threshold, event boundaries, dataset SHA-256, source counts, random seed and training duration.
- Graph models also record F1 after removal of graph messages and the mean absolute prediction change, demonstrating whether graph context affected the fitted model.
- Reported inference latency measures batch-amortized model execution only. It excludes database queries, feature assembly, explanations and network latency; it is not end-to-end throughput.

Scores are model outputs or heuristic risk indices, not calibrated probabilities, validated bank decisions or proven fraud. Synthetic metrics do not establish generalization to real financial data. Model comparisons require the same dataset hash and split.

## Explainability

Without an activated model, stored explanations expose weighted heuristic contributions and observable feature facts. With an activated model, explanations measure signed prediction changes after replacing a self feature with its training mean or removing one relation's messages. Positive values support the score; negative values oppose it. These are perturbation explanations, not SHAP values or causal effects. Stored neighbor identifiers, timestamps, relation types and decay weights let investigators follow the observed events.

References for the architecture and evaluation design: [GraphSAGE paper](https://arxiv.org/abs/1706.02216), [scikit-learn time-series cross-validation](https://scikit-learn.org/stable/modules/cross_validation.html#time-series-split).
