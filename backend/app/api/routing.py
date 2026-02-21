from __future__ import annotations

import time
from typing import Literal

from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException, Request


router = APIRouter(prefix="/route", tags=["routing"])


def _merged_control_state(request: Request, updates: dict) -> dict:
    simulation_engine = request.app.state.simulation_engine
    state_cache = request.app.state.state_cache
    current = state_cache.get_json("sim_control_state", simulation_engine.get_status())
    merged = {**current, **updates}
    state_cache.set_json("sim_control_state", merged)
    return merged


class Coordinate(BaseModel):
    lat: float = Field(..., ge=6.2, le=6.8)
    lon: float = Field(..., ge=3.0, le=3.7)


class RouteAnalyzeRequest(BaseModel):
    origin: Coordinate
    destination: Coordinate


@router.post("/analyze")
def analyze_route(payload: RouteAnalyzeRequest, request: Request):
    result = request.app.state.routing_engine.analyze_route(
        origin=(payload.origin.lat, payload.origin.lon),
        destination=(payload.destination.lat, payload.destination.lon),
    )
    if not result["route_geometry"]:
        raise HTTPException(status_code=404, detail="No route found for the given coordinates")
    return result


class ScenarioRequest(BaseModel):
    multiplier: float = Field(..., ge=0.2, le=2.5)


@router.post("/scenario")
def set_scenario(payload: ScenarioRequest, request: Request):
    request.app.state.simulation_engine.set_demand_scenario(payload.multiplier)
    _merged_control_state(request, {"demand_multiplier": payload.multiplier})
    return {"ok": True, "demand_multiplier": payload.multiplier}


class SimulationControlRequest(BaseModel):
    day_of_week: int = Field(..., ge=0, le=6)
    time_of_day_minutes: int = Field(..., ge=0, le=1439)
    scenario: Literal["Morning", "Midday", "Evening", "Night"]
    speed_multiplier: float = Field(...)


@router.post("/controls")
def set_simulation_controls(payload: SimulationControlRequest, request: Request):
    if payload.speed_multiplier not in {0.5, 1.0, 2.0, 5.0}:
        raise HTTPException(status_code=422, detail="speed_multiplier must be one of 0.5, 1, 2, 5")

    request.app.state.simulation_engine.set_temporal_controls(
        day_of_week=payload.day_of_week,
        time_of_day_minutes=payload.time_of_day_minutes,
        scenario=payload.scenario,
        speed_multiplier=payload.speed_multiplier,
    )
    _merged_control_state(
        request,
        {
            "day_of_week": payload.day_of_week,
            "time_of_day_minutes": payload.time_of_day_minutes,
            "scenario": payload.scenario,
            "simulation_speed_multiplier": payload.speed_multiplier,
        },
    )
    return {"ok": True, "status": request.app.state.simulation_engine.get_status()}


class IncidentRequest(BaseModel):
    segment_id: int
    severity: float = Field(..., ge=0.0, le=1.0)
    duration_ticks: int = Field(120, ge=1, le=3600)


@router.post("/incident")
def inject_incident(payload: IncidentRequest, request: Request):
    ok = request.app.state.simulation_engine.inject_incident(
        segment_id=payload.segment_id,
        severity=payload.severity,
        duration_ticks=payload.duration_ticks,
    )
    if not ok:
        raise HTTPException(status_code=404, detail="Invalid segment_id")
    return {"ok": True}


class PauseRequest(BaseModel):
    paused: bool


@router.post("/pause")
def pause_simulation(payload: PauseRequest, request: Request):
    request.app.state.simulation_engine.set_paused(payload.paused)
    _merged_control_state(request, {"paused": payload.paused})
    return {"ok": True, "paused": payload.paused, "status": request.app.state.simulation_engine.get_status()}


@router.post("/reset")
def reset_simulation(request: Request):
    request.app.state.simulation_engine.reset()
    _merged_control_state(request, {"reset_token": time.time_ns()})
    return {"ok": True, "status": request.app.state.simulation_engine.get_status()}
