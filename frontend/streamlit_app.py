from __future__ import annotations

import os
from datetime import time

import pandas as pd
import pydeck as pdk
import requests
import streamlit as st
from streamlit_autorefresh import st_autorefresh


def normalize_api_base(url: str) -> str:
    cleaned = (url or "").strip().rstrip("/")
    if not cleaned:
        return "http://127.0.0.1:8000"
    if not cleaned.startswith(("http://", "https://")):
        cleaned = f"https://{cleaned}"
    return cleaned


def post_json(path: str, payload: dict | None = None) -> dict | None:
    # Wrapper for backend POST calls with consistent error handling.
    try:
        response = requests.post(f"{API_BASE}{path}", json=payload or {}, timeout=12)
        response.raise_for_status()
        return response.json()
    except Exception as exc:
        st.error(f"Failed to post {path}: {exc}")
        return None


def minutes_to_time(value: int) -> time:
    # Converts slider minutes [0..1439] to display-friendly time object.
    hours = value // 60
    mins = value % 60
    return time(hour=hours, minute=mins)


default_backend_url = normalize_api_base(os.getenv("BACKEND_URL", "https://backend-api-production-0277.up.railway.app"))
API_BASE = normalize_api_base(st.sidebar.text_input("Backend URL", default_backend_url))

st.set_page_config(page_title="Lagos Traffic Platform", layout="wide")
st.title("Lagos Real-Time Traffic Simulation & Predictive Congestion Platform")

st_autorefresh(interval=3000, key="live_refresh")


def fetch_json(path: str):
    try:
        response = requests.get(f"{API_BASE}{path}", timeout=15)
        response.raise_for_status()
        return response.json()
    except Exception as exc:
        st.error(f"Failed to fetch {path}: {exc}")
        return None


def congestion_to_color(value: float) -> list[int]:
    value = max(0.0, min(value, 1.0))
    red = int(255 * value)
    green = int(255 * (1 - value))
    return [red, green, 50, 180]


live = fetch_json("/live/heatmap")
metrics = fetch_json("/prediction/metrics")
status = (live or {}).get("status", {})

col1, col2, col3 = st.columns(3)
if live and live.get("items"):
    items = live["items"]
    mean_congestion = sum(x["congestion_index"] for x in items) / len(items)
    col1.metric("Active Segments", len(items))
    col2.metric("Avg Congestion", f"{mean_congestion:.3f}")
    col3.metric("Sim Tick", live.get("status", {}).get("tick", 0))

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
    st.pydeck_chart(
        pdk.Deck(
            layers=layers,
            initial_view_state=view_state,
            tooltip={
                "text": (
                    "Segment ID: {segment_id}\n"
                    "Avg Speed: {avg_speed} km/h\n"
                    "Vehicle Count: {vehicle_count}\n"
                    "Congestion Index: {congestion}"
                )
            },
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
        post_json("/route/pause", {"paused": False})
        post_json(
            "/route/controls",
            {
                "day_of_week": int(day_choice),
                "time_of_day_minutes": int(time_choice),
                "scenario": scenario_choice,
                "speed_multiplier": float(speed_choice),
            },
        )
with control_btn_col2:
    if st.button("Pause"):
        post_json("/route/pause", {"paused": True})
with control_btn_col3:
    if st.button("Reset"):
        post_json("/route/reset")
with control_btn_col4:
    demand = st.slider("Demand Multiplier", min_value=0.2, max_value=2.5, value=float(status.get("demand_multiplier", 1.0)), step=0.1)
    if st.button("Apply Demand"):
        post_json("/route/scenario", {"multiplier": demand})

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
        post_json(
            "/route/incident",
            {"segment_id": int(incident_segment), "severity": incident_severity, "duration_ticks": 180},
        )

st.subheader("Route Query")
default_origin = "6.52,3.36"
default_destination = "6.60,3.45"
origin_raw = st.text_input("Origin (lat,lon)", default_origin)
destination_raw = st.text_input("Destination (lat,lon)", default_destination)

if st.button("Analyze"):
    try:
        o_lat, o_lon = [float(v.strip()) for v in origin_raw.split(",")]
        d_lat, d_lon = [float(v.strip()) for v in destination_raw.split(",")]
        payload = {
            "origin": {"lat": o_lat, "lon": o_lon},
            "destination": {"lat": d_lat, "lon": d_lon},
        }
        response = requests.post(f"{API_BASE}/route/analyze", json=payload, timeout=10)
        if response.status_code == 404:
            st.error("Route not found for the selected coordinates.")
            st.session_state["route_geometry"] = []
        else:
            response.raise_for_status()
            route_result = response.json()
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
    pred = fetch_json(f"/prediction/segment/{segment_id}")
    if pred:
        st.write(
            {
                "predicted_congestion": pred["predicted_congestion"],
                "confidence_interval": [pred["confidence_lower"], pred["confidence_upper"]],
                "model": pred["model"],
            }
        )
        hist = pred.get("historical_congestion", [])
        if hist:
            st.line_chart(pd.DataFrame({"historical_congestion": hist}))

st.subheader("Model Evaluation")
st.json(metrics or {})
