from app.core.congestion_model import compute_speed_and_congestion


def test_zero_vehicles_has_low_congestion():
    avg_speed, congestion = compute_speed_and_congestion(vehicle_count=0, capacity=1000, free_flow_speed=60)
    assert avg_speed == 60
    assert congestion == 0.0


def test_capacity_overload_increases_congestion():
    avg_speed, congestion = compute_speed_and_congestion(vehicle_count=2000, capacity=1000, free_flow_speed=60)
    assert avg_speed >= 1.0
    assert 0.0 <= congestion <= 1.0
    assert congestion > 0.8


def test_safe_behavior_with_zero_capacity():
    avg_speed, congestion = compute_speed_and_congestion(vehicle_count=10, capacity=0, free_flow_speed=50)
    assert avg_speed >= 1.0
    assert 0.0 <= congestion <= 1.0
