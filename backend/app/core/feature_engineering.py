from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
import statistics


def _safe_value(values: Sequence[float], idx_from_end: int) -> float:
    if len(values) >= idx_from_end:
        return float(values[-idx_from_end])
    return float(values[-1]) if values else 0.0


def build_feature_row(
    segment_id: int,
    timestamp: datetime,
    congestion_history: Sequence[float],
    capacity: int,
    vehicle_count: int,
    incident_flag: int,
) -> dict:
    """Create feature row for a segment at a point in time."""
    history = [float(x) for x in congestion_history if x is not None]

    window_15 = history[-15:] if history else [0.0]
    window_60 = history[-60:] if history else [0.0]

    hour = timestamp.hour
    rush_hour = 1 if hour in {7, 8, 9, 17, 18, 19} else 0
    capacity_ratio = vehicle_count / max(capacity, 1)

    return {
        "segment_id": segment_id,
        "timestamp": timestamp,
        "hour": hour,
        "day_of_week": timestamp.weekday(),
        "lag_1": _safe_value(history, 1),
        "lag_3": _safe_value(history, 3),
        "lag_6": _safe_value(history, 6),
        "rolling_mean_15": float(statistics.fmean(window_15)),
        "rolling_mean_60": float(statistics.fmean(window_60)),
        "rolling_std_15": float(statistics.pstdev(window_15)) if len(window_15) > 1 else 0.0,
        "capacity_ratio": capacity_ratio,
        "incident_flag": incident_flag,
        "rush_hour": rush_hour,
    }
