#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 2 ]]; then
  echo "Usage: $0 <backend-url> <frontend-url>"
  echo "Example: $0 https://api.example.com https://app.example.com"
  exit 1
fi

BACKEND_URL="${1%/}"
FRONTEND_URL="${2%/}"

echo "Checking backend health..."
curl -fsS "$BACKEND_URL/health" >/dev/null

echo "Checking live heatmap..."
curl -fsS "$BACKEND_URL/live/heatmap" >/dev/null

echo "Checking prediction metrics..."
curl -fsS "$BACKEND_URL/prediction/metrics" >/dev/null

echo "Checking frontend..."
curl -fsS "$FRONTEND_URL" >/dev/null

echo "Smoke test passed."
