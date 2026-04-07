#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 2 ]]; then
  echo "Usage: $0 <backend|frontend|all> <path-to-env-file>"
  exit 1
fi

TARGET="$1"
ENV_FILE="$2"
COMPOSE_FILE="deploy/oci/docker-compose.oci.yml"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Env file not found: $ENV_FILE"
  exit 1
fi

case "$TARGET" in
  backend)
    docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" up -d --build backend
    ;;
  frontend)
    docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" up -d --build frontend
    ;;
  all)
    docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" up -d --build backend frontend
    ;;
  *)
    echo "Invalid target: $TARGET"
    exit 1
    ;;
esac

docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
