from app.core.prediction_engine import PredictionEngine
from app.core.routing_engine import RoutingEngine
from app.core.simulation_engine import SimulationEngine


def test_predicted_segment_cost_uses_prediction_signal():
    simulation_engine = SimulationEngine(num_segments=40, total_vehicles=4000, tick_interval_seconds=1, seed=22)
    prediction_engine = PredictionEngine()
    routing_engine = RoutingEngine(simulation_engine, prediction_engine)

    segment_id = simulation_engine.segments[0].id

    def high_congestion_predict(features):
        return 0.9, 0.8, 1.0

    prediction_engine.predict = high_congestion_predict

    current_cost = routing_engine._segment_cost(segment_id, mode="current")
    predicted_cost = routing_engine._segment_cost(segment_id, mode="predicted")

    assert predicted_cost > current_cost


def test_analyze_route_returns_current_and_predicted_times():
    simulation_engine = SimulationEngine(num_segments=60, total_vehicles=6000, tick_interval_seconds=1, seed=19)
    prediction_engine = PredictionEngine()
    routing_engine = RoutingEngine(simulation_engine, prediction_engine)

    result = routing_engine.analyze_route(origin=(6.52, 3.36), destination=(6.60, 3.45))

    assert "estimated_current_travel_time_min" in result
    assert "predicted_travel_time_10_15_min" in result
    assert "route_geometry" in result
    assert result["estimated_current_travel_time_min"] >= 0
    assert result["predicted_travel_time_10_15_min"] >= 0
