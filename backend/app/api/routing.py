from __future__ import annotations

from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException, Request


router = APIRouter(prefix="/route", tags=["routing"])


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
    return {"ok": True, "demand_multiplier": payload.multiplier}


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
    return {"ok": True, "paused": payload.paused}
