import base64
from functools import lru_cache
import numpy as np
from app.ml.temporal.network import forward, sigmoid


@lru_cache(maxsize=4)
def booster(encoded):
    from xgboost import XGBClassifier

    model = XGBClassifier(n_jobs=1)
    model.load_model(bytearray(base64.b64decode(encoded)))
    return model


def predict(artifact, x, messages):
    x = np.atleast_2d(x)
    if messages.ndim == 2:
        messages = messages[None, :, :]
    x = (x - np.asarray(artifact["mean"])) / np.asarray(artifact["scale"])
    if artifact["model_type"] in ("STATIC_GNN", "TEMPORAL_GNN"):
        weights = {k: np.asarray(v) for k, v in artifact["weights"].items()}
        return forward(weights, x, messages)[0]
    if artifact["model_type"] == "XGBOOST":
        return booster(artifact["booster"]).predict_proba(x)[:, 1]
    return sigmoid(x @ np.asarray(artifact["coef"]) + artifact["intercept"])


def explain_prediction(artifact, x, messages):
    score = float(predict(artifact, x, messages)[0])
    factors = []
    from app.ml.graph.context import FEATURE_NAMES, RELATIONS

    for i, name in enumerate(FEATURE_NAMES):
        masked = x.copy()
        masked[i] = artifact["mean"][i]
        delta = score - float(predict(artifact, masked, messages)[0])
        factors.append({"key": name, "label": name.replace("_", " ").title(), "contribution": round(delta, 5)})
    if artifact["model_type"] in ("STATIC_GNN", "TEMPORAL_GNN"):
        for i, name in enumerate(RELATIONS):
            masked = messages.copy()
            masked[i] = 0
            factors.append(
                {
                    "key": name,
                    "label": name.replace("_id", "").title() + " neighborhood",
                    "contribution": round(score - float(predict(artifact, x, masked)[0]), 5),
                }
            )
    return score, sorted(factors, key=lambda v: abs(v["contribution"]), reverse=True)
