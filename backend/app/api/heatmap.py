from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request


router = APIRouter(prefix="/live", tags=["live"])


def get_state(request: Request):
    return request.app.state


@router.get("/segments")
def get_live_segments(
    request: Request,
    limit: int = Query(300, ge=1, le=5000),
):
    state = get_state(request)
    rows = state.state_cache.get_json("live_segments", [])
    return {
        "count": len(rows),
        "items": rows[:limit],
        "status": state.state_cache.get_json("sim_status", {}),
    }


@router.get("/heatmap")
def get_live_heatmap(request: Request):
    state = get_state(request)
    rows = state.state_cache.get_json("live_heatmap", [])
    return {
        "count": len(rows),
        "items": rows,
        "status": state.state_cache.get_json("sim_status", {}),
    }
