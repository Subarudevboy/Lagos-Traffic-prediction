# Rollback Plan

## Objective

Restore stable service within 20 minutes if a deployment introduces failures.

## Rollback Triggers

Initiate rollback when any condition persists for 5 minutes:

- API /health non-200
- 5xx error rate > 5%
- p95 latency > 300 ms
- Backend container restart loop
- Frontend unavailable

## Pre-Deploy Safeguards

1. Capture current image tags and commit hash.
2. Snapshot PostgreSQL (or verify latest backup).
3. Export active environment variables.
4. Lower DNS TTL to 60 seconds before cutover.

## Rollback Procedure

1. Stop traffic to new targets at LB.
2. Repoint LB to previous backend and frontend targets/images.
3. Reapply previous env files.
4. Restart prior containers:

```bash
docker compose -f deploy/oci/docker-compose.oci.yml --env-file deploy/oci/env/backend.env up -d backend
```

```bash
docker compose -f deploy/oci/docker-compose.oci.yml --env-file deploy/oci/env/frontend.env up -d frontend
```

5. If schema/data change failed, restore DB snapshot.
6. Run smoke tests and confirm recovery.

## Validation Checklist

- API /health is 200
- /live/heatmap is 200
- /prediction/metrics is 200
- /route/controls persists state
- Frontend root is 200 and map loads

## Communication

- Record start/end time
- Record trigger and root symptom
- Record recovered version
- Share incident summary and next prevention action
