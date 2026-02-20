from __future__ import annotations

import heapq
import math
from typing import Any

from app.core.prediction_engine import PredictionEngine
from app.core.simulation_engine import SimulationEngine


def _distance_km(a_lat: float, a_lon: float, b_lat: float, b_lon: float) -> float:
    r = 6371.0
    x = math.radians(b_lon - a_lon) * math.cos(math.radians((a_lat + b_lat) / 2))
    y = math.radians(b_lat - a_lat)
    return math.sqrt(x * x + y * y) * r


class RoutingEngine:
    def __init__(self, simulation_engine: SimulationEngine, prediction_engine: PredictionEngine) -> None:
        self.simulation_engine = simulation_engine
        self.prediction_engine = prediction_engine
        self.graph: dict[int, list[tuple[int, int]]] = {}
        self.node_coords: dict[int, tuple[float, float]] = {}
        self.segment_nodes: dict[int, tuple[int, int]] = {}
        self._build_graph()

    def _build_graph(self) -> None:
        segments = self.simulation_engine.segments
        node_lookup: dict[tuple[float, float], int] = {}
        node_id = 1

        def get_node(lat: float, lon: float) -> int:
            nonlocal node_id
            key = (round(lat, 4), round(lon, 4))
            if key not in node_lookup:
                node_lookup[key] = node_id
                self.node_coords[node_id] = (lat, lon)
                self.graph[node_id] = []
                node_id += 1
            return node_lookup[key]

        for segment in segments:
            start_node = get_node(segment.start_lat, segment.start_lon)
            end_node = get_node(segment.end_lat, segment.end_lon)
            self.segment_nodes[segment.id] = (start_node, end_node)
            self.graph[start_node].append((end_node, segment.id))
            self.graph[end_node].append((start_node, segment.id))

    def _nearest_node(self, lat: float, lon: float) -> int:
        return min(
            self.node_coords,
            key=lambda n: _distance_km(lat, lon, self.node_coords[n][0], self.node_coords[n][1]),
        )

    def _segment_cost(self, segment_id: int, mode: str = "current") -> float:
        segment = self.simulation_engine.segment_by_id[segment_id]
        state = self.simulation_engine.live_state[segment_id]

        current_speed = max(float(state["avg_speed"]), 5.0)

        if mode == "predicted":
            feature_guess = {
                "hour": 0,
                "day_of_week": 0,
                "lag_1": state["congestion_index"],
                "lag_3": state["congestion_index"],
                "lag_6": state["congestion_index"],
                "rolling_mean_15": state["congestion_index"],
                "rolling_mean_60": state["congestion_index"],
                "rolling_std_15": 0.03,
                "capacity_ratio": state["vehicle_count"] / max(segment.capacity, 1),
                "incident_flag": state["incident_flag"],
                "rush_hour": 0,
            }
            predicted_congestion, _, _ = self.prediction_engine.predict(feature_guess)
            current_speed = max(segment.free_flow_speed * (1 - predicted_congestion), 5.0)

        return (segment.length_km / current_speed) * 60.0

    def _shortest_path(self, source: int, target: int, mode: str) -> tuple[list[int], float]:
        heap: list[tuple[float, int]] = [(0.0, source)]
        best = {source: 0.0}
        parent: dict[int, tuple[int, int]] = {}

        while heap:
            cost, node = heapq.heappop(heap)
            if node == target:
                break
            if cost > best.get(node, float("inf")):
                continue

            for nxt, segment_id in self.graph.get(node, []):
                nxt_cost = cost + self._segment_cost(segment_id, mode=mode)
                if nxt_cost < best.get(nxt, float("inf")):
                    best[nxt] = nxt_cost
                    parent[nxt] = (node, segment_id)
                    heapq.heappush(heap, (nxt_cost, nxt))

        if target not in parent and source != target:
            return [], float("inf")

        segment_path = []
        node_path = [target]
        cur = target
        while cur != source:
            prev, seg = parent[cur]
            node_path.append(prev)
            segment_path.append(seg)
            cur = prev
        node_path.reverse()
        segment_path.reverse()
        return segment_path, best.get(target, 0.0)

    def analyze_route(self, origin: tuple[float, float], destination: tuple[float, float]) -> dict[str, Any]:
        source = self._nearest_node(*origin)
        target = self._nearest_node(*destination)

        current_segments, current_time = self._shortest_path(source, target, mode="current")
        predicted_segments, predicted_time = self._shortest_path(source, target, mode="predicted")

        selected_segments = predicted_segments or current_segments
        route_geometry = []
        congestion_values = []

        for segment_id in selected_segments:
            segment = self.simulation_engine.segment_by_id[segment_id]
            state = self.simulation_engine.live_state[segment_id]
            route_geometry.append([[segment.start_lat, segment.start_lon], [segment.end_lat, segment.end_lon]])
            congestion_values.append(float(state["congestion_index"]))

        risk = sum(congestion_values) / len(congestion_values) if congestion_values else 0.0
        return {
            "current_travel_time": round(current_time, 2),
            "predicted_travel_time": round(predicted_time, 2),
            "route_geometry": route_geometry,
            "congestion_risk_score": round(risk, 4),
        }
