from app.core.simulation_engine import SimulationEngine


def test_simulation_tick_updates_state():
    engine = SimulationEngine(num_segments=30, total_vehicles=3000, tick_interval_seconds=1, seed=10)
    before_tick = engine.tick_count
    initial = engine.live_state[1]["vehicle_count"]

    engine.tick()

    assert engine.tick_count == before_tick + 1
    assert 1 in engine.live_state
    assert engine.live_state[1]["vehicle_count"] != initial or engine.live_state[1]["avg_speed"] >= 1.0


def test_inject_incident_for_valid_segment():
    engine = SimulationEngine(num_segments=20, total_vehicles=2000, tick_interval_seconds=1, seed=10)
    assert engine.inject_incident(segment_id=1, severity=0.7, duration_ticks=20) is True
    assert 1 in engine.incidents


def test_inject_incident_invalid_segment_returns_false():
    engine = SimulationEngine(num_segments=20, total_vehicles=2000, tick_interval_seconds=1, seed=10)
    assert engine.inject_incident(segment_id=99999, severity=0.5, duration_ticks=20) is False
