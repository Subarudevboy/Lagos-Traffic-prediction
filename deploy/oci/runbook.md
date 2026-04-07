# OCI Deployment Runbook

## 1) Prerequisites

- OCI account with IAM permissions for Compute, Networking, LB, Vault, Logging
- Domain name access (optional but recommended)
- SSH key pair
- Git access to this repository

## 2) Network and Security

1. Create a compartment for this project.
2. Create a VCN with:
- Public subnet (load balancer)
- Private subnet (app/data VMs)
3. Configure NSGs:
- Allow inbound 443 to LB
- Allow LB to backend:8000 and frontend:8501
- Allow backend to Redis:6379 and Postgres:5432 in private subnet
- Deny broad public ingress to app/data

## 3) Provision Infrastructure

1. Launch backend VM (A1 Flex 4 OCPU / 24 GB)
2. Launch frontend VM (A1 Flex 2 OCPU / 12 GB)
3. Launch Redis VM if needed (A1 Flex 1 OCPU / 6 GB)
4. Create PostgreSQL service (or use existing)

## 4) Bootstrap App VMs

Run on each app VM:

```bash
sudo apt-get update
sudo apt-get install -y ca-certificates curl git jq
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
newgrp docker
sudo systemctl enable docker
sudo systemctl start docker
```

## 5) Deploy Application

1. Clone repository on backend and frontend VM.
2. Copy env files from this folder templates.
3. Start services using docker compose:

```bash
docker compose -f deploy/oci/docker-compose.oci.yml --env-file deploy/oci/env/backend.env up -d backend
```

```bash
docker compose -f deploy/oci/docker-compose.oci.yml --env-file deploy/oci/env/frontend.env up -d frontend
```

## 6) Configure Load Balancer

- Backend set A: target backend VM:8000
- Backend set B: target frontend VM:8501
- Listener: 443 with cert
- Routing policy:
  - /api, /live, /route, /prediction -> backend set A
  - / -> backend set B

## 7) DNS

- app.yourdomain.com -> LB public IP (A record)
- api.yourdomain.com -> LB public IP (A record) or path-based only

## 8) Verification

Run smoke tests:

```bash
bash deploy/oci/scripts/smoke_test.sh https://api.yourdomain.com https://app.yourdomain.com
```

Expected:
- /health returns 200
- /live/heatmap returns 200
- frontend root returns 200

## 9) Post-Deploy Hardening

- Rotate secrets in Vault
- Enable alarms
- Restrict CORS to frontend origin
- Set backup retention for DB
