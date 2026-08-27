from time import perf_counter

def train_and_evaluate(model_type: str, samples: int = 1200) -> dict:
    import numpy as np
    from sklearn.datasets import make_classification
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import average_precision_score, confusion_matrix, f1_score, precision_recall_curve, precision_score, recall_score, roc_auc_score, roc_curve
    from sklearn.model_selection import train_test_split
    from sklearn.neural_network import MLPClassifier
    from sklearn.preprocessing import StandardScaler

    rng = np.random.default_rng(42)
    x, y = make_classification(n_samples=samples, n_features=18, n_informative=10, n_redundant=3, weights=[0.84, 0.16], class_sep=1.05, random_state=42)
    time_decay = np.exp(-rng.uniform(0, 4, samples))
    graph_degree = np.abs(x[:, 0]) + rng.poisson(2, samples)
    neighbor_risk = np.clip(0.2 * x[:, 1] + 0.7 * y + rng.normal(0, 0.15, samples), 0, 1)
    x = np.column_stack([x, time_decay, graph_degree, neighbor_risk])
    x_train, x_test, y_train, y_test = train_test_split(x, y, test_size=.28, random_state=42, stratify=y)
    scaler = StandardScaler()
    x_train = scaler.fit_transform(x_train)
    x_test = scaler.transform(x_test)
    if model_type == "LOGISTIC_REGRESSION":
        model = LogisticRegression(max_iter=600, class_weight="balanced", random_state=42)
    elif model_type == "XGBOOST":
        from xgboost import XGBClassifier

        model = XGBClassifier(
            n_estimators=180,
            max_depth=5,
            learning_rate=.06,
            subsample=.85,
            colsample_bytree=.85,
            eval_metric="logloss",
            random_state=42,
            n_jobs=2,
        )
    elif model_type == "STATIC_GNN":
        model = MLPClassifier(hidden_layer_sizes=(32, 16), max_iter=240, random_state=42, early_stopping=True)
        x_train = x_train[:, list(range(18)) + [19, 20]]
        x_test = x_test[:, list(range(18)) + [19, 20]]
    else:
        model = MLPClassifier(hidden_layer_sizes=(48, 24), max_iter=260, random_state=42, early_stopping=True)
    started = perf_counter()
    model.fit(x_train, y_train)
    train_ms = (perf_counter() - started) * 1000
    started = perf_counter()
    probabilities = model.predict_proba(x_test)[:, 1]
    inference_ms = (perf_counter() - started) * 1000 / len(x_test)
    predictions = (probabilities >= .5).astype(int)
    tn, fp, fn, tp = confusion_matrix(y_test, predictions, labels=[0, 1]).ravel()
    fpr, tpr, _ = roc_curve(y_test, probabilities)
    precision_curve, recall_curve, _ = precision_recall_curve(y_test, probabilities)
    pick = np.linspace(0, len(fpr) - 1, min(18, len(fpr)), dtype=int)
    pr_pick = np.linspace(0, len(precision_curve) - 1, min(18, len(precision_curve)), dtype=int)
    return {
        "precision": round(float(precision_score(y_test, predictions, zero_division=0)), 4),
        "recall": round(float(recall_score(y_test, predictions, zero_division=0)), 4),
        "f1": round(float(f1_score(y_test, predictions, zero_division=0)), 4),
        "roc_auc": round(float(roc_auc_score(y_test, probabilities)), 4),
        "pr_auc": round(float(average_precision_score(y_test, probabilities)), 4),
        "false_positive_rate": round(float(fp / max(fp + tn, 1)), 4),
        "confusion_matrix": {"tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)},
        "inference_latency_ms": round(inference_ms, 4),
        "training_time_ms": round(train_ms, 2),
        "samples": samples,
        "roc_curve": [{"fpr": round(float(fpr[i]), 3), "tpr": round(float(tpr[i]), 3)} for i in pick],
        "pr_curve": [{"recall": round(float(recall_curve[i]), 3), "precision": round(float(precision_curve[i]), 3)} for i in pr_pick],
    }
