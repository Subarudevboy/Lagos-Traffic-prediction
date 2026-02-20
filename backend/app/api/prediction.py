from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, HTTPException, Request

from app.core.feature_engineering import build_feature_row


router = APIRouter(prefix="/prediction", tags=["prediction"])


@router.get("/segment/{segment_id}")
def prediction_for_segment(segment_id: int, request: Request):
    simulation_engine = request.app.state.simulation_engine
    prediction_engine = request.app.state.prediction_engine

    if segment_id not in simulation_engine.segment_by_id:
        raise HTTPException(status_code=404, detail="segment not found")

    segment = simulation_engine.segment_by_id[segment_id]
    state = simulation_engine.live_state[segment_id]
    history = list(simulation_engine.congestion_history[segment_id])
    features = build_feature_row(
        segment_id=segment_id,
        timestamp=datetime.fromisoformat(state["timestamp"]),
        congestion_history=history,
        capacity=segment.capacity,
        vehicle_count=state["vehicle_count"],
        incident_flag=state["incident_flag"],
    )
    pred, low, high = prediction_engine.predict(features)

    return {
        "segment_id": segment_id,
        "historical_congestion": prediction_engine.get_segment_history(segment_id),
        "predicted_congestion": round(pred, 4),
        "confidence_lower": round(low, 4),
        "confidence_upper": round(high, 4),
        "model": prediction_engine.model_name,
        "metrics": prediction_engine.metrics,
    }


@router.get("/metrics")
def model_metrics(request: Request):
    return request.app.state.state_cache.get_json("model_metrics", {})
