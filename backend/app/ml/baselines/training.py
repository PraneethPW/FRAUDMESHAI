"""Reproducible, chronological evaluation with persisted portable model weights."""

import base64
import hashlib
import json
from datetime import UTC, datetime, timedelta
from time import perf_counter
import numpy as np
from app.ml.graph.context import encode_dataset, utc
from app.ml.inference.predict import predict


def synthetic_events(samples=1200):
    rng = np.random.default_rng(42)
    rows = []
    start = datetime(2026, 1, 1, tzinfo=UTC)
    for i in range(samples):
        coordinated = i % 40 in range(24, 32)
        account = f"A-{700+i%4}" if coordinated else f"A-{rng.integers(1,150)}"
        rows.append(
            {
                "id": f"BENCH-{i}",
                "source": "SIMULATION",
                "account_id": account,
                "merchant_id": f"M-{rng.integers(1,15)}",
                "device_id": f"RING-{i//200}" if coordinated else f"D-{account}",
                "ip_address": f"RING-IP-{i//200}" if coordinated else f"IP-{rng.integers(1,80)}",
                "location": str(rng.integers(1, 6)) if coordinated else "1",
                "currency": "USD",
                "amount": float(rng.lognormal(7.2 if coordinated else 5.8, 0.8)),
                "occurred_at": start + timedelta(seconds=i * 75),
                "is_fraud": bool(coordinated if rng.random() > 0.035 else not coordinated),
            }
        )
    return rows


def train_model(model_type, samples=1200, rows=None):
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import (
        average_precision_score,
        confusion_matrix,
        f1_score,
        precision_recall_curve,
        precision_score,
        recall_score,
        roc_auc_score,
        roc_curve,
    )
    from sklearn.preprocessing import StandardScaler
    from threadpoolctl import threadpool_limits

    synthetic = rows is None
    rows = synthetic_events(samples) if synthetic else sorted(rows, key=lambda r: (utc(r["occurred_at"]), r["id"]))
    # Keep unlabelled events for causal graph context; never manufacture training labels.
    x, m = encode_dataset(rows, temporal=model_type != "STATIC_GNN")
    labelled = [i for i, r in enumerate(rows) if r.get("is_fraud") is not None]
    if len(labelled) < 100:
        raise ValueError("At least 100 labelled transactions are required; import is_fraud or review alerts.")
    x, m = x[labelled], m[labelled]
    selected = [rows[i] for i in labelled]
    y = np.array([int(r["is_fraud"]) for r in selected])
    n = len(y)
    a, b = int(n * 0.6), int(n * 0.8)
    # Move boundaries to timestamp changes so equal-time events never cross partitions.
    while a < n and utc(selected[a]["occurred_at"]) == utc(selected[a - 1]["occurred_at"]):
        a += 1
    b = max(b, a + 1)
    while b < n and utc(selected[b]["occurred_at"]) == utc(selected[b - 1]["occurred_at"]):
        b += 1
    if a >= b or b >= n:
        raise ValueError("Dataset needs distinct event times across train, validation and test windows.")
    for part in (y[:a], y[a:b], y[b:]):
        if len(np.unique(part)) < 2:
            raise ValueError("Each chronological split must contain both fraud and legitimate labels.")
    # Historical labels imported today may be used in a retrospective benchmark; this is explicit in metadata.
    scaler = StandardScaler().fit(x[:a])
    xt = scaler.transform(x[:a])
    artifact = {
        "schema_version": 2,
        "model_type": model_type,
        "mean": scaler.mean_.tolist(),
        "scale": scaler.scale_.tolist(),
        "dataset": "SYNTHETIC" if synthetic else "WORKSPACE",
        "window_hours": 24,
        "max_neighbors": 32,
    }
    started = perf_counter()
    with threadpool_limits(limits=1):
        if model_type in ("STATIC_GNN", "TEMPORAL_GNN"):
            from app.ml.temporal.network import fit

            artifact["weights"] = fit(xt, m[:a], y[:a])
        elif model_type == "XGBOOST":
            from xgboost import XGBClassifier

            model = XGBClassifier(
                n_estimators=100,
                max_depth=4,
                learning_rate=0.07,
                n_jobs=1,
                random_state=42,
                scale_pos_weight=float((1 - y[:a]).sum() / y[:a].sum()),
                eval_metric="logloss",
            )
            model.fit(xt, y[:a])
            artifact["booster"] = base64.b64encode(model.get_booster().save_raw(raw_format="json")).decode()
        else:
            model = LogisticRegression(max_iter=500, class_weight="balanced", random_state=42).fit(xt, y[:a])
            artifact["coef"] = model.coef_[0].tolist()
            artifact["intercept"] = float(model.intercept_[0])
        training_ms = (perf_counter() - started) * 1000
        validation = predict(artifact, x[a:b], m[a:b])
        thresholds = np.linspace(0.05, 0.95, 91)
        threshold = float(max(thresholds, key=lambda t: f1_score(y[a:b], validation >= t, zero_division=0)))
        artifact["threshold"] = threshold
        started = perf_counter()
        probs = predict(artifact, x[b:], m[b:])
        latency = (perf_counter() - started) * 1000 / len(probs)
    predicted = probs >= threshold
    truth = y[b:]
    tn, fp, fn, tp = confusion_matrix(truth, predicted, labels=[0, 1]).ravel()
    fpr, tpr, _ = roc_curve(truth, probs)
    precision, recall, _ = precision_recall_curve(truth, probs)
    from collections import Counter
    source_counts = dict(Counter(row.get("source", "UNSPECIFIED") for row in selected))
    artifact["source_counts"] = source_counts
    digest = hashlib.sha256(json.dumps(rows, default=str, sort_keys=True).encode()).hexdigest()
    metrics = {
        "precision": float(precision_score(truth, predicted, zero_division=0)),
        "recall": float(recall_score(truth, predicted, zero_division=0)),
        "f1": float(f1_score(truth, predicted, zero_division=0)),
        "roc_auc": float(roc_auc_score(truth, probs)),
        "pr_auc": float(average_precision_score(truth, probs)),
        "false_positive_rate": float(fp / max(fp + tn, 1)),
        "confusion_matrix": dict(zip(("tn", "fp", "fn", "tp"), map(int, (tn, fp, fn, tp)))),
        "inference_latency_ms": latency,
        "training_time_ms": training_ms,
        "samples": n,
        "threshold": threshold,
        "split": {"train": a, "validation": b - a, "test": n - b},
        "roc_curve": [{"fpr": float(fpr[i]), "tpr": float(tpr[i])} for i in np.linspace(0, len(fpr) - 1, min(40, len(fpr)), dtype=int)],
        "pr_curve": [
            {"recall": float(recall[i]), "precision": float(precision[i])}
            for i in np.linspace(0, len(precision) - 1, min(40, len(precision)), dtype=int)
        ],
        "dataset_sha256": digest,
        "seed": 42,
        "evaluation": "chronological 60/20/20; retrospective labels; threshold fitted on validation only",
        "dataset_source": artifact["dataset"],
        "source_counts": source_counts,
        "architecture": (
            "time-decayed mean message passing"
            if model_type == "TEMPORAL_GNN"
            else "mean message passing" if model_type == "STATIC_GNN" else model_type
        ),
        "train_end": utc(selected[a - 1]["occurred_at"]).isoformat(),
        "test_start": utc(selected[b]["occurred_at"]).isoformat(),
        "latency_scope": "model only, batch amortized; excludes database, graph assembly and network",
    }
    if model_type in ("STATIC_GNN", "TEMPORAL_GNN"):
        removed = predict(artifact, x[b:], np.zeros_like(m[b:]))
        metrics["graph_ablation_mean_abs_delta"] = float(np.mean(np.abs(probs - removed)))
        metrics["graph_ablation_f1"] = float(f1_score(truth, removed >= threshold, zero_division=0))
    return metrics, artifact


def train_and_evaluate(model_type, samples=1200):
    return train_model(model_type, samples)[0]
