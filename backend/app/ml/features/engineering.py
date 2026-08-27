from datetime import UTC, datetime


def build_features(*, amount: float, occurred_at: datetime, device_accounts: int, ip_accounts: int, recent_count: int, merchant_frequency: int, new_device: bool, location_changed: bool, seconds_since_previous: float | None) -> dict[str, float | int | bool]:
    hour = occurred_at.astimezone(UTC).hour
    time_gap = seconds_since_previous if seconds_since_previous is not None else 86400
    return {
        "amount": round(amount, 2),
        "hour": hour,
        "unusual_hour": hour < 5 or hour > 23,
        "device_sharing_count": max(0, device_accounts - 1),
        "ip_sharing_count": max(0, ip_accounts - 1),
        "rolling_transaction_count_1h": recent_count,
        "merchant_frequency_24h": merchant_frequency,
        "new_device": new_device,
        "location_changed": location_changed,
        "seconds_since_previous": round(time_gap, 2),
        "velocity": round(recent_count / max(time_gap / 3600, 0.1), 3),
    }

