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


def test_temporal_controls_apply_day_time_scenario_and_speed():
    engine = SimulationEngine(num_segments=20, total_vehicles=2000, tick_interval_seconds=2, seed=10)
    engine.set_temporal_controls(day_of_week=2, time_of_day_minutes=510, scenario="Morning", speed_multiplier=2.0)

    assert engine.day_of_week == 2
    assert engine.current_time.hour == 8
    assert engine.current_time.minute == 30
    assert engine.scenario == "Morning"
    assert engine.simulation_speed_multiplier == 2.0


def test_simulation_speed_multiplier_advances_time_faster():
    engine = SimulationEngine(num_segments=20, total_vehicles=2000, tick_interval_seconds=2, seed=10)
    engine.set_temporal_controls(day_of_week=1, time_of_day_minutes=360, scenario="Midday", speed_multiplier=5.0)
    before = engine.current_time

    engine.tick()

    delta = engine.current_time - before
    assert int(delta.total_seconds()) == 10


def test_early_morning_demand_lower_than_evening_peak():
    engine = SimulationEngine(num_segments=20, total_vehicles=2000, tick_interval_seconds=1, seed=10)
    engine.set_temporal_controls(day_of_week=0, time_of_day_minutes=120, scenario="Night", speed_multiplier=1.0)
    night_demand = engine._time_of_day_demand(engine.current_time)

    engine.set_temporal_controls(day_of_week=0, time_of_day_minutes=1080, scenario="Evening", speed_multiplier=1.0)
    evening_demand = engine._time_of_day_demand(engine.current_time)

    assert evening_demand > night_demand
