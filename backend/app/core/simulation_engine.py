from __future__ import annotations

from collections import defaultdict, deque
from datetime import UTC, datetime, timedelta
import random

from app.core.congestion_model import compute_speed_and_congestion
from app.ingestion.osm_loader import Segment, generate_synthetic_lagos_segments


class SimulationEngine:
    def __init__(
        self,
        num_segments: int = 1200,
        total_vehicles: int = 120000,
        tick_interval_seconds: int = 1,
        seed: int = 42,
    ) -> None:
        random.seed(seed)
        self.tick_interval_seconds = tick_interval_seconds
        self.total_vehicles = total_vehicles
        self.segments: list[Segment] = generate_synthetic_lagos_segments(num_segments=num_segments, seed=seed)
        self.segment_by_id = {segment.id: segment for segment in self.segments}

        self.paused = False
        self.demand_multiplier = 1.0
        self.tick_count = 0
        self.current_time = datetime.now(UTC)

        self.incidents: dict[int, dict] = {}
        self.live_state: dict[int, dict] = {}
        self.congestion_history = defaultdict(lambda: deque(maxlen=3600))

        self._initialize_state()

    def _initialize_state(self) -> None:
        total_capacity = sum(s.capacity for s in self.segments)
        for segment in self.segments:
            initial_count = int(self.total_vehicles * (segment.capacity / max(total_capacity, 1)))
            avg_speed, congestion_index = compute_speed_and_congestion(
                vehicle_count=initial_count,
                capacity=segment.capacity,
                free_flow_speed=segment.free_flow_speed,
            )
            self.live_state[segment.id] = {
                "segment_id": segment.id,
                "timestamp": self.current_time.isoformat(),
                "vehicle_count": initial_count,
                "avg_speed": round(avg_speed, 2),
                "congestion_index": round(congestion_index, 4),
                "incident_flag": 0,
            }
            self.congestion_history[segment.id].append(congestion_index)

    def set_paused(self, paused: bool) -> None:
        self.paused = paused

    def set_demand_scenario(self, multiplier: float) -> None:
        self.demand_multiplier = max(0.2, min(multiplier, 2.5))

    def inject_incident(self, segment_id: int, severity: float, duration_ticks: int) -> bool:
        if segment_id not in self.segment_by_id:
            return False
        self.incidents[segment_id] = {
            "severity": max(0.0, min(1.0, severity)),
            "remaining": max(1, duration_ticks),
        }
        return True

    def _time_of_day_demand(self, timestamp: datetime) -> float:
        hour = timestamp.hour
        if 6 <= hour <= 10:
            return 1.3
        if 16 <= hour <= 20:
            return 1.35
        if 11 <= hour <= 15:
            return 1.0
        if 21 <= hour <= 23:
            return 0.75
        return 0.6

    def _active_incident_severity(self, segment_id: int) -> float:
        details = self.incidents.get(segment_id)
        if not details:
            return 0.0
        return float(details["severity"])

    def tick(self) -> dict[int, dict]:
        if self.paused:
            return self.live_state

        self.tick_count += 1
        self.current_time += timedelta(seconds=self.tick_interval_seconds)
        demand_factor = self._time_of_day_demand(self.current_time) * self.demand_multiplier

        for segment in self.segments:
            prev = self.live_state[segment.id]
            incident_severity = self._active_incident_severity(segment.id)
            effective_capacity = int(segment.capacity * (1 - 0.75 * incident_severity))
            effective_capacity = max(effective_capacity, 50)

            stochastic_noise = random.randint(-25, 25)
            inflow = int(demand_factor * segment.capacity * random.uniform(0.001, 0.006))
            outflow = int(max(prev["avg_speed"], 5.0) * random.uniform(0.03, 0.09))

            next_vehicle_count = max(0, int(prev["vehicle_count"] + inflow - outflow + stochastic_noise))
            avg_speed, congestion_index = compute_speed_and_congestion(
                vehicle_count=next_vehicle_count,
                capacity=effective_capacity,
                free_flow_speed=segment.free_flow_speed,
            )

            self.live_state[segment.id] = {
                "segment_id": segment.id,
                "timestamp": self.current_time.isoformat(),
                "vehicle_count": next_vehicle_count,
                "avg_speed": round(avg_speed, 2),
                "congestion_index": round(congestion_index, 4),
                "incident_flag": 1 if incident_severity > 0 else 0,
            }
            self.congestion_history[segment.id].append(congestion_index)

        to_delete = []
        for segment_id, details in self.incidents.items():
            details["remaining"] -= 1
            if details["remaining"] <= 0:
                to_delete.append(segment_id)
        for segment_id in to_delete:
            self.incidents.pop(segment_id, None)

        return self.live_state

    def get_live_segments(self) -> list[dict]:
        rows = []
        for segment in self.segments:
            state = self.live_state[segment.id]
            rows.append(
                {
                    **state,
                    "length": segment.length_km,
                    "capacity": segment.capacity,
                    "free_flow_speed": segment.free_flow_speed,
                    "road_type": segment.road_type,
                    "geometry": [
                        [segment.start_lat, segment.start_lon],
                        [segment.end_lat, segment.end_lon],
                    ],
                }
            )
        return rows
