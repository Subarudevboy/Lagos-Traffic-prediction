from __future__ import annotations

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.heatmap import router as heatmap_router
from app.api.prediction import router as prediction_router
from app.api.routing import router as routing_router
from app.core.prediction_engine import PredictionEngine
from app.core.routing_engine import RoutingEngine
from app.core.simulation_engine import SimulationEngine
from app.services.scheduler import SimulationScheduler
from app.services.state_cache import StateCache


@asynccontextmanager
async def lifespan(app: FastAPI):
    num_segments = int(os.getenv("SIM_NUM_SEGMENTS", "1200"))
    total_vehicles = int(os.getenv("SIM_TOTAL_VEHICLES", "120000"))
    tick_interval_seconds = int(os.getenv("SIM_TICK_INTERVAL_SECONDS", "1"))

    simulation_engine = SimulationEngine(
        num_segments=num_segments,
        total_vehicles=total_vehicles,
        tick_interval_seconds=tick_interval_seconds,
    )
    prediction_engine = PredictionEngine()
    state_cache = StateCache()
    routing_engine = RoutingEngine(simulation_engine, prediction_engine)
    scheduler = SimulationScheduler(simulation_engine, prediction_engine, state_cache)

    app.state.simulation_engine = simulation_engine
    app.state.prediction_engine = prediction_engine
    app.state.state_cache = state_cache
    app.state.routing_engine = routing_engine
    app.state.scheduler = scheduler

    state_cache.set_json(
        "sim_control_state",
        {
            **simulation_engine.get_status(),
            "reset_token": None,
        },
    )

    await scheduler.start()
    yield
    await scheduler.stop()


app = FastAPI(
    title="Lagos Real-Time Traffic Simulation & Predictive Congestion Platform",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(heatmap_router)
app.include_router(routing_router)
app.include_router(prediction_router)


@app.get("/health")
def health_check():
    return {"status": "ok"}
