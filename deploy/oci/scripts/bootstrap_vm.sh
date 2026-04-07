#!/usr/bin/env bash
set -euo pipefail

sudo apt-get update
sudo apt-get install -y ca-certificates curl git jq
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker "$USER"
sudo systemctl enable docker
sudo systemctl start docker

echo "Bootstrap complete. Log out and back in so docker group membership applies."
