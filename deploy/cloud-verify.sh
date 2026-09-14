#!/bin/sh
set -eu
cd "$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
docker compose --env-file .env.cloud -f docker-compose.cloud.yml exec -T backend python -m app.cloud_admin verify
