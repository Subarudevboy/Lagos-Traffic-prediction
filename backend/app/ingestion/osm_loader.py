from __future__ import annotations

import math
import random
from dataclasses import dataclass


@dataclass(slots=True)
class Segment:
    id: int
    start_lat: float
    start_lon: float
    end_lat: float
    end_lon: float
    length_km: float
    capacity: int
    free_flow_speed: float
    road_type: str


def _distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    x = math.radians(lon2 - lon1) * math.cos(math.radians((lat1 + lat2) / 2))
    y = math.radians(lat2 - lat1)
    return math.sqrt(x * x + y * y) * r


def generate_synthetic_lagos_segments(num_segments: int = 1200, seed: int = 42) -> list[Segment]:
    """Generate synthetic road segments centered around Lagos."""
    random.seed(seed)
    center_lat, center_lon = 6.5244, 3.3792

    road_types = ["motorway", "trunk", "primary", "secondary", "tertiary"]
    type_capacity = {
        "motorway": (2000, 2800, 70.0),
        "trunk": (1500, 2200, 60.0),
        "primary": (1000, 1600, 50.0),
        "secondary": (700, 1200, 40.0),
        "tertiary": (400, 900, 30.0),
    }

    segments: list[Segment] = []
    for segment_id in range(1, num_segments + 1):
        theta = random.uniform(0, 2 * math.pi)
        radius = random.uniform(0.0, 0.18)
        start_lat = center_lat + radius * math.cos(theta)
        start_lon = center_lon + radius * math.sin(theta)

        direction = random.uniform(0, 2 * math.pi)
        edge_len = random.uniform(0.001, 0.007)
        end_lat = start_lat + edge_len * math.cos(direction)
        end_lon = start_lon + edge_len * math.sin(direction)

        road_type = random.choice(road_types)
        cap_low, cap_high, ffs = type_capacity[road_type]
        capacity = random.randint(cap_low, cap_high)

        length_km = max(_distance_km(start_lat, start_lon, end_lat, end_lon), 0.08)
        segments.append(
            Segment(
                id=segment_id,
                start_lat=start_lat,
                start_lon=start_lon,
                end_lat=end_lat,
                end_lon=end_lon,
                length_km=length_km,
                capacity=capacity,
                free_flow_speed=ffs,
                road_type=road_type,
            )
        )

    return segments
