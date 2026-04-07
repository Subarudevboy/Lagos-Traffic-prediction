# OCI Services and SKU Sizing

## Architecture Recommendation

Use a two-VM application tier with a load balancer and private data services.

- Public edge: OCI Flexible Load Balancer
- App tier:
  - Backend VM (FastAPI + simulation + scheduler)
  - Frontend VM (Streamlit)
- Data tier (private subnet):
  - PostgreSQL (managed preferred)
  - Redis (managed if available in region, else self-managed)
- Security: NSGs + Vault + Logging/Monitoring

## Baseline SKU Plan (Production-MVP)

### Compute

1. Backend VM
- Shape: VM.Standard.A1.Flex
- OCPU: 4
- Memory: 24 GB
- Boot volume: 100 GB
- OS: Ubuntu 22.04 LTS

2. Frontend VM
- Shape: VM.Standard.A1.Flex
- OCPU: 2
- Memory: 12 GB
- Boot volume: 100 GB
- OS: Ubuntu 22.04 LTS

3. Optional Redis VM (if not managed)
- Shape: VM.Standard.A1.Flex
- OCPU: 1
- Memory: 6 GB
- Boot volume: 50 GB
- Bind private IP only

### Load Balancer

- Type: OCI Flexible Load Balancer
- Bandwidth: min 10 Mbps, max 100 Mbps
- TLS termination at LB
- Health checks:
  - Backend: GET /health on port 8000
  - Frontend: GET / on port 8501

### Database

- Preferred: OCI PostgreSQL managed service
- Initial size: 2 OCPU / 16 GB RAM / 100 GB storage
- Private endpoint only
- Automatic backups enabled

### Secrets and Ops

- OCI Vault for app secrets
- OCI Logging + Monitoring + Alarms
- OCI Object Storage for snapshots and exported logs

## Scale-Up Triggers

Scale backend first when any of the following hold for 15 minutes:

- CPU > 70%
- Memory > 80%
- p95 API latency > 300 ms
- Restart count increases

## Alternative: OKE

Adopt OKE when you need autoscaling and multi-node resilience.

- 2 worker nodes to start
- Shape: VM.Standard.E4.Flex
- Each node: 2 OCPU / 16 GB RAM
- OCI LB Ingress
- Keep PostgreSQL and Redis as managed services
