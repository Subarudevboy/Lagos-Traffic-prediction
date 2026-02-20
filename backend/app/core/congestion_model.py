from __future__ import annotations


def compute_speed_and_congestion(
    vehicle_count: int,
    capacity: int,
    free_flow_speed: float,
) -> tuple[float, float]:
    """Compute average speed and congestion index using the project formula."""
    safe_capacity = max(capacity, 1)
    safe_free_flow = max(free_flow_speed, 1.0)

    load_factor = max(vehicle_count, 0) / safe_capacity
    avg_speed = safe_free_flow * (1 - load_factor**2)
    avg_speed = max(avg_speed, 1.0)

    congestion_index = 1 - (avg_speed / safe_free_flow)
    congestion_index = min(max(congestion_index, 0.0), 1.0)
    return avg_speed, congestion_index
