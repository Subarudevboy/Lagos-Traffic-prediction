from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.api.heatmap import get_live_segments
from app.api.routing import Coordinate, RouteAnalyzeRequest, SimulationControlRequest, analyze_route, set_simulation_controls
from app.core.prediction_engine import PredictionEngine
from app.core.routing_engine import RoutingEngine
from app.core.simulation_engine import SimulationEngine
from app.services.state_cache import StateCache

def _build_request_context():
    simulation_engine = SimulationEngine(num_segments=80, total_vehicles=8000, tick_interval_seconds=1, seed=30)
    prediction_engine = PredictionEngine()
    routing_engine = RoutingEngine(simulation_engine, prediction_engine)
    state_cache = StateCache()

    live_rows = simulation_engine.get_live_segments()[:5]
    enriched_rows = []
    for row in live_rows:
        enriched_rows.append(
            {
                **row,
                "predicted_congestion": row["congestion_index"],
                "estimated_segment_travel_time_min": 1.0,
                "predicted_segment_travel_time_min": 1.2,
            }
        )

    state_cache.set_json("live_segments", enriched_rows)
    state_cache.set_json("sim_status", simulation_engine.get_status())

    app_state = SimpleNamespace(
        simulation_engine=simulation_engine,
        prediction_engine=prediction_engine,
        routing_engine=routing_engine,
        state_cache=state_cache,
    )
    request = SimpleNamespace(app=SimpleNamespace(state=app_state))
    return request


def test_live_segments_returns_extended_fields_and_status():
    request = _build_request_context()
    payload = get_live_segments(request=request, limit=5)

    assert "items" in payload
    assert "status" in payload

    if payload["items"]:
        first = payload["items"][0]
        assert "avg_speed" in first
        assert "vehicle_count" in first
        assert "estimated_segment_travel_time_min" in first
        assert "predicted_segment_travel_time_min" in first

    status = payload["status"]
    assert "day_of_week" in status
    assert "time_of_day_minutes" in status
    assert "scenario" in status
    assert "simulation_speed_multiplier" in status


def test_simulation_controls_update_state():
    request = _build_request_context()
    response = set_simulation_controls(
        payload=SimulationControlRequest(
            day_of_week=4,
            time_of_day_minutes=1020,
            scenario="Evening",
            speed_multiplier=2.0,
        ),
        request=request,
    )

    assert response["ok"] is True
    assert response["status"]["day_of_week"] == 4
    assert response["status"]["scenario"] == "Evening"
    assert response["status"]["simulation_speed_multiplier"] == 2.0


def test_simulation_controls_reject_invalid_speed():
    request = _build_request_context()

    with pytest.raises(HTTPException):
        set_simulation_controls(
            payload=SimulationControlRequest(
                day_of_week=2,
                time_of_day_minutes=480,
                scenario="Morning",
                speed_multiplier=3.0,
            ),
            request=request,
        )


def test_route_analyze_returns_current_and_predicted_travel_times():
    request = _build_request_context()
    payload = RouteAnalyzeRequest(
        origin=Coordinate(lat=6.52, lon=3.36),
        destination=Coordinate(lat=6.60, lon=3.45),
    )
    try:
        result = analyze_route(payload=payload, request=request)
    except HTTPException as exc:
        assert exc.status_code == 404
        return

    assert "estimated_current_travel_time_min" in result
    assert "predicted_travel_time_10_15_min" in result
