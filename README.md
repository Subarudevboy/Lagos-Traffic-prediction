# Lagos Real-Time Traffic Simulation & Predictive Congestion Platform

![Python](https://img.shields.io/badge/Python-3.14-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-Backend-009688)
![Streamlit](https://img.shields.io/badge/Streamlit-Frontend-FF4B4B)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED)
![Status](https://img.shields.io/badge/Status-MVP-success)

This project implements a modular MVP for real-time synthetic traffic simulation, congestion forecasting, dynamic routing, and live dashboard monitoring for Lagos.

## Quick Start

1) Start backend

```bash
cd backend
set PYTHONPATH=%cd%
..\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

2) Start frontend (new terminal)

```bash
cd frontend
..\.venv\Scripts\python.exe -m streamlit run streamlit_app.py --server.address 127.0.0.1 --server.port 8501
```

3) Open dashboard

- http://127.0.0.1:8501
- In sidebar, ensure `Backend URL` is `http://127.0.0.1:8000`

## Architecture

Road Network (Synthetic OSM-style)
-> Simulation Engine (1s ticks)
-> Feature Engineering Layer
-> Prediction Engine
-> Redis cache
-> FastAPI
-> Streamlit dashboard

PostgreSQL + PostGIS schema is included via SQLAlchemy models and Docker service.

## Implemented Scope

- Synthetic ingestion for **1200 segments** and **120,000 vehicles** defaults
- Real-time congestion updates every second
- Feature generation (lags, rolling stats, rush hour, incident flag)
- Forecasting (baselines + linear/rf/gradient boosting)
- Dynamic route analysis with congestion-aware travel-time weighting
- Live heatmap and predictive panel in Streamlit
- API endpoints:
  - `GET /live/segments`
  - `GET /live/heatmap`
  - `POST /route/analyze`
  - `POST /route/pause`
  - `POST /route/scenario`
  - `POST /route/incident`
  - `GET /prediction/segment/{id}`
  - `GET /prediction/metrics`

## Project Structure

- `backend/app/main.py`
- `backend/app/api/`
- `backend/app/core/`
- `backend/app/db/`
- `backend/app/services/`
- `backend/app/ingestion/`
- `backend/experiments/modeling_notebook.ipynb`
- `frontend/streamlit_app.py`

## Run with Docker

```bash
docker compose up --build
```

- API: http://localhost:8000
- API docs: http://localhost:8000/docs
- Dashboard: http://localhost:8501

## Local Development

Backend:

```bash
cd backend
..\.venv\Scripts\python.exe -m pip install -r requirements.txt
set PYTHONPATH=%cd%
..\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

Frontend:

```bash
cd frontend
..\.venv\Scripts\python.exe -m pip install -r requirements.txt
..\.venv\Scripts\python.exe -m streamlit run streamlit_app.py
```

## Tests

```bash
cd backend
set PYTHONPATH=%cd%
..\.venv\Scripts\python.exe -m pytest
```

## Notes

- The current implementation is synthetic and does not ingest live traffic feeds.
- Redis and Postgres are optional for development; cache falls back to in-memory when Redis is unavailable.
- Model retraining is periodic based on simulation ticks.
