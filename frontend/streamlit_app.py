from __future__ import annotations

import os

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
    view_state = pdk.ViewState(latitude=6.5244, longitude=3.3792, zoom=10)
    st.pydeck_chart(pdk.Deck(layers=[layer], initial_view_state=view_state, tooltip={"text": "Congestion: {congestion}\nPredicted: {predicted}"}))

st.subheader("Simulation Controls")
ctrl_col1, ctrl_col2, ctrl_col3 = st.columns(3)

with ctrl_col1:
    paused = st.toggle("Pause Simulation", value=False)
    if st.button("Apply Pause"):
        requests.post(f"{API_BASE}/route/pause", json={"paused": paused}, timeout=5)

with ctrl_col2:
    demand = st.slider("Demand Multiplier", min_value=0.2, max_value=2.5, value=1.0, step=0.1)
    if st.button("Apply Demand"):
        requests.post(f"{API_BASE}/route/scenario", json={"multiplier": demand}, timeout=5)

with ctrl_col3:
    incident_segment = st.number_input("Incident Segment ID", min_value=1, max_value=5000, value=10)
    incident_severity = st.slider("Incident Severity", 0.0, 1.0, 0.5, 0.1)
    if st.button("Inject Incident"):
        requests.post(
            f"{API_BASE}/route/incident",
            json={"segment_id": int(incident_segment), "severity": incident_severity, "duration_ticks": 180},
            timeout=5,
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
        route_result = requests.post(f"{API_BASE}/route/analyze", json=payload, timeout=8).json()
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
