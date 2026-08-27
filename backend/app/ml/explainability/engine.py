def explain_score(features: dict, contributions: dict[str, float]) -> dict:
    ordered = sorted(contributions.items(), key=lambda item: item[1], reverse=True)
    labels = {
        "behavioral_anomaly": "Behavioral anomaly",
        "graph_relationship_risk": "Graph relationship risk",
        "velocity_anomaly": "Velocity anomaly",
        "device_sharing_risk": "Device sharing risk",
        "location_anomaly": "Location anomaly",
    }
    factors = [{"key": key, "label": labels[key], "contribution": round(value, 4)} for key, value in ordered]
    reasons = []
    if features["device_sharing_count"]:
        reasons.append(f"Device shared across {features['device_sharing_count'] + 1} accounts")
    if features["ip_sharing_count"]:
        reasons.append(f"IP observed across {features['ip_sharing_count'] + 1} accounts")
    if features["rolling_transaction_count_1h"] >= 4:
        reasons.append(f"{features['rolling_transaction_count_1h']} transactions within the rolling hour")
    if features["unusual_hour"]:
        reasons.append("Activity occurred outside the account's typical operating window")
    if features["location_changed"]:
        reasons.append("Location changed since the previous account event")
    if features["amount"] >= 5000:
        reasons.append("Amount is elevated relative to the simulated operating baseline")
    return {"factors": factors, "reasons": reasons or ["No dominant anomaly; score reflects combined weak signals"], "features": features}

