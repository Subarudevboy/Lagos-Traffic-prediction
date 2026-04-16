from __future__ import annotations

import os
import sys
import importlib
from datetime import time
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
import pydeck as pdk
import streamlit as st
from streamlit_autorefresh import st_autorefresh


ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

build_feature_row = importlib.import_module("app.core.feature_engineering").build_feature_row
PredictionEngine = importlib.import_module("app.core.prediction_engine").PredictionEngine
RoutingEngine = importlib.import_module("app.core.routing_engine").RoutingEngine
SimulationEngine = importlib.import_module("app.core.simulation_engine").SimulationEngine


def get_runtime_state() -> dict:
    # Keep simulation and model state alive per Streamlit user session.
    if "runtime" in st.session_state:
        return st.session_state["runtime"]

    sim_segments = int(os.getenv("SIM_NUM_SEGMENTS", "700"))
    sim_vehicles = int(os.getenv("SIM_TOTAL_VEHICLES", "70000"))
    sim_tick = int(os.getenv("SIM_TICK_INTERVAL_SECONDS", "1"))

    simulation_engine = SimulationEngine(
        num_segments=sim_segments,
        total_vehicles=sim_vehicles,
        tick_interval_seconds=sim_tick,
    )
    prediction_engine = PredictionEngine()
    routing_engine = RoutingEngine(simulation_engine, prediction_engine)

    st.session_state["runtime"] = {
        "simulation_engine": simulation_engine,
        "prediction_engine": prediction_engine,
        "routing_engine": routing_engine,
        "heatmap_rows": [],
        "model_metrics": {},
    }
    return st.session_state["runtime"]


def run_step(runtime: dict) -> tuple[list[dict], dict, dict]:
    simulation_engine = runtime["simulation_engine"]
    prediction_engine = runtime["prediction_engine"]

    simulation_engine.tick()
    live_segments = simulation_engine.get_live_segments()

    heatmap_rows = []
    for row in live_segments:
        history = list(simulation_engine.congestion_history[row["segment_id"]])
        features = build_feature_row(
            segment_id=row["segment_id"],
            timestamp=simulation_engine.current_time,
            congestion_history=history,
            capacity=row["capacity"],
            vehicle_count=row["vehicle_count"],
            incident_flag=row["incident_flag"],
        )
        prediction_engine.add_observation(
            features=features,
            target=row["congestion_index"],
            tick=simulation_engine.tick_count,
        )

        if len(prediction_engine.rows) >= 500 and simulation_engine.tick_count % prediction_engine.retrain_interval_ticks == 0:
            prediction_engine.train()

        predicted, lower, upper = prediction_engine.predict(features)
        predicted_speed = max(float(row["free_flow_speed"]) * (1 - predicted), 5.0)
        estimated_travel_time_min = (float(row["length"]) / max(float(row["avg_speed"]), 5.0)) * 60.0
        predicted_travel_time_min = (float(row["length"]) / predicted_speed) * 60.0

        heatmap_rows.append(
            {
                **row,
                "predicted_congestion": round(predicted, 4),
                "confidence_lower": round(lower, 4),
                "confidence_upper": round(upper, 4),
                "estimated_segment_travel_time_min": round(estimated_travel_time_min, 3),
                "predicted_segment_travel_time_min": round(predicted_travel_time_min, 3),
            }
        )

    runtime["heatmap_rows"] = heatmap_rows
    runtime["model_metrics"] = prediction_engine.metrics
    status = {
        **simulation_engine.get_status(),
        "model": prediction_engine.model_name,
    }
    return heatmap_rows, runtime["model_metrics"], status


def minutes_to_time(value: int) -> time:
    # Converts slider minutes [0..1439] to display-friendly time object.
    hours = value // 60
    mins = value % 60
    return time(hour=hours, minute=mins)


st.set_page_config(page_title="Lagos Traffic Platform", layout="wide")
st.title("Lagos Traffic Demo")
st.caption("This demo runs simulation, prediction, and routing in-process without external backend APIs.")

st_autorefresh(interval=3000, key="live_refresh")


def congestion_to_color(value: float) -> list[int]:
    value = max(0.0, min(value, 1.0))
    red = int(255 * value)
    green = int(255 * (1 - value))
    return [red, green, 50, 180]


runtime = get_runtime_state()
items, metrics, status = run_step(runtime)

col1, col2, col3 = st.columns(3)
if items:
    mean_congestion = sum(x["congestion_index"] for x in items) / len(items)
    col1.metric("Active Segments", len(items))
    col2.metric("Avg Congestion", f"{mean_congestion:.3f}")
    col3.metric("Sim Tick", status.get("tick", 0))

    map_rows = []
    for item in items:
        map_rows.append(
            {
                "path": [[item["geometry"][0][1], item["geometry"][0][0]], [item["geometry"][1][1], item["geometry"][1][0]]],
                "segment_id": item["segment_id"],
                "avg_speed": item["avg_speed"],
                "vehicle_count": item["vehicle_count"],
                "congestion": item["congestion_index"],
                "predicted": item["predicted_congestion"],
                "color": congestion_to_color(item["congestion_index"]),
            }
        )

    df_map = pd.DataFrame(map_rows)
    layer = pdk.Layer(
        "PathLayer",
        df_map,
        get_path="path",
        get_color="color",
        width_scale=15,
        width_min_pixels=2,
        pickable=True,
    )

    layers = [layer]
    if st.session_state.get("route_geometry"):
        route_rows = [{"path": [[seg[0][1], seg[0][0]], [seg[1][1], seg[1][0]]]} for seg in st.session_state["route_geometry"]]
        route_df = pd.DataFrame(route_rows)
        layers.append(
            pdk.Layer(
                "PathLayer",
                route_df,
                get_path="path",
                get_color=[30, 144, 255, 230],
                width_scale=25,
                width_min_pixels=4,
                pickable=False,
            )
        )

    view_state = pdk.ViewState(latitude=6.5244, longitude=3.3792, zoom=10)
    tooltip_config: Any = {
        "text": (
            "Segment ID: {segment_id}\n"
            "Avg Speed: {avg_speed} km/h\n"
            "Vehicle Count: {vehicle_count}\n"
            "Congestion Index: {congestion}"
        )
    }
    st.pydeck_chart(
        pdk.Deck(
            layers=layers,
            initial_view_state=view_state,
            tooltip=tooltip_config,
        )
    )

st.subheader("Simulation Controls")
days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
scenarios = ["Morning", "Midday", "Evening", "Night"]
speed_options = [0.5, 1.0, 2.0, 5.0]

ctrl_col1, ctrl_col2, ctrl_col3, ctrl_col4 = st.columns(4)
with ctrl_col1:
    day_choice = st.selectbox("Day of Week", options=list(range(7)), format_func=lambda idx: days[idx], index=int(status.get("day_of_week", 0)))
with ctrl_col2:
    time_choice = st.slider("Time of Day", min_value=0, max_value=1439, value=int(status.get("time_of_day_minutes", 8 * 60)), format="%d")
    st.caption(f"Selected time: {minutes_to_time(time_choice).strftime('%H:%M')}")
with ctrl_col3:
    scenario_default = status.get("scenario", "Midday")
    scenario_choice = st.selectbox("Scenario", scenarios, index=scenarios.index(scenario_default) if scenario_default in scenarios else 1)
with ctrl_col4:
    speed_default = float(status.get("simulation_speed_multiplier", 1.0))
    speed_choice = st.selectbox("Simulation Speed", speed_options, index=speed_options.index(speed_default) if speed_default in speed_options else 1, format_func=lambda x: f"{x}×")

control_btn_col1, control_btn_col2, control_btn_col3, control_btn_col4 = st.columns(4)
with control_btn_col1:
    if st.button("Start"):
        runtime["simulation_engine"].set_paused(False)
        runtime["simulation_engine"].set_temporal_controls(
            day_of_week=int(day_choice),
            time_of_day_minutes=int(time_choice),
            scenario=scenario_choice,
            speed_multiplier=float(speed_choice),
        )
        st.rerun()
with control_btn_col2:
    if st.button("Pause"):
        runtime["simulation_engine"].set_paused(True)
        st.rerun()
with control_btn_col3:
    if st.button("Reset"):
        runtime["simulation_engine"].reset()
        runtime["prediction_engine"] = PredictionEngine()
        runtime["routing_engine"] = RoutingEngine(runtime["simulation_engine"], runtime["prediction_engine"])
        st.session_state["route_geometry"] = []
        st.rerun()
with control_btn_col4:
    demand = st.slider("Demand Multiplier", min_value=0.2, max_value=2.5, value=float(status.get("demand_multiplier", 1.0)), step=0.1)
    if st.button("Apply Demand"):
        runtime["simulation_engine"].set_demand_scenario(demand)
        st.rerun()

st.caption(
    f"Simulation status — tick: {status.get('tick', 0)}, paused: {status.get('paused', False)}, model: {status.get('model', 'n/a')}"
)

st.subheader("Incidents")
incident_col1, incident_col2, incident_col3 = st.columns(3)
with incident_col1:
    incident_segment = st.number_input("Incident Segment ID", min_value=1, max_value=5000, value=10)
with incident_col2:
    incident_severity = st.slider("Incident Severity", 0.0, 1.0, 0.5, 0.1)
with incident_col3:
    if st.button("Inject Incident"):
        ok = runtime["simulation_engine"].inject_incident(
            segment_id=int(incident_segment),
            severity=float(incident_severity),
            duration_ticks=180,
        )
        if not ok:
            st.error("Invalid segment id for incident injection.")
        else:
            st.rerun()

st.subheader("Route Query")
default_origin = "6.52,3.36"
default_destination = "6.60,3.45"
origin_raw = st.text_input("Origin (lat,lon)", default_origin)
destination_raw = st.text_input("Destination (lat,lon)", default_destination)

if st.button("Analyze"):
    try:
        o_lat, o_lon = [float(v.strip()) for v in origin_raw.split(",")]
        d_lat, d_lon = [float(v.strip()) for v in destination_raw.split(",")]
        route_result = runtime["routing_engine"].analyze_route(
            origin=(o_lat, o_lon),
            destination=(d_lat, d_lon),
        )
        if not route_result.get("route_geometry"):
            st.error("Route not found for the selected coordinates.")
            st.session_state["route_geometry"] = []
        else:
            st.session_state["route_geometry"] = route_result.get("route_geometry", [])
            rt_col1, rt_col2 = st.columns(2)
            rt_col1.metric(
                "Estimated Current Travel Time",
                f"{route_result.get('estimated_current_travel_time_min', route_result.get('current_travel_time', 0)):.2f} min",
            )
            rt_col2.metric(
                "Predicted Travel Time (next 10–15 min)",
                f"{route_result.get('predicted_travel_time_10_15_min', route_result.get('predicted_travel_time', 0)):.2f} min",
            )
            st.json(route_result)
    except Exception as exc:
        st.error(f"Route analysis failed: {exc}")

st.subheader("Predictive Analytics Panel")
segment_id = st.number_input("Segment ID", min_value=1, max_value=5000, value=1)
if st.button("Load Segment Prediction"):
    engine = runtime["simulation_engine"]
    predictor = runtime["prediction_engine"]
    sid = int(segment_id)
    if sid not in engine.segment_by_id:
        st.error("segment not found")
    else:
        segment = engine.segment_by_id[sid]
        state = engine.live_state[sid]
        history = list(engine.congestion_history[sid])
        features = build_feature_row(
            segment_id=sid,
            timestamp=datetime.fromisoformat(state["timestamp"]),
            congestion_history=history,
            capacity=segment.capacity,
            vehicle_count=state["vehicle_count"],
            incident_flag=state["incident_flag"],
        )
        pred, low, high = predictor.predict(features)
        st.write(
            {
                "predicted_congestion": round(pred, 4),
                "confidence_interval": [round(low, 4), round(high, 4)],
                "model": predictor.model_name,
            }
        )
        hist = predictor.get_segment_history(sid)
        if hist:
            st.line_chart(pd.DataFrame({"historical_congestion": hist}))

st.subheader("Model Evaluation")
st.json(metrics or {})
