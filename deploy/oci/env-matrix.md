# Environment Variable Matrix

## Backend

| Variable | Required | Example | Notes |
|---|---|---|---|
| PORT | Yes | 8000 | Container listen port |
| PYTHONPATH | Yes | /app | App imports |
| DATABASE_URL | Recommended | postgresql://user:pass@db:5432/traffic | Persisted state |
| REDIS_URL | Yes | redis://:pass@redis.private:6379/0 | Shared simulation controls |
| SIM_NUM_SEGMENTS | Optional | 1200 | Tune memory/performance |
| SIM_TOTAL_VEHICLES | Optional | 120000 | Simulation load |
| SIM_TICK_INTERVAL_SECONDS | Optional | 1 | Tick cadence |
| LOG_LEVEL | Optional | INFO | Runtime logging |
| CORS_ALLOWED_ORIGINS | Recommended | https://app.yourdomain.com | API security |
| ENVIRONMENT | Recommended | production | Labeling |

## Frontend

| Variable | Required | Example | Notes |
|---|---|---|---|
| PORT | Yes | 8501 | Streamlit port |
| BACKEND_URL | Yes | https://api.yourdomain.com | API base URL |
| LOG_LEVEL | Optional | INFO | Frontend logging |
| ENVIRONMENT | Optional | production | Labeling |

## Redis (self-managed only)

| Variable | Required | Example | Notes |
|---|---|---|---|
| REDIS_PASSWORD | Yes | strong-password | Set in redis.conf and app REDIS_URL |

## Recommended Starting Values

- SIM_NUM_SEGMENTS=1200
- SIM_TOTAL_VEHICLES=120000
- SIM_TICK_INTERVAL_SECONDS=1
- LOG_LEVEL=INFO
