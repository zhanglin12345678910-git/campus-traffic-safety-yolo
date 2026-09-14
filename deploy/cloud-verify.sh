#!/bin/sh
set -eu
cd "$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
[ -s test-data/acceptance.jpg ] || { echo 'Provide an authorized, de-identified test-data/acceptance.jpg first.'; exit 1; }
docker compose --env-file .env.cloud -f docker-compose.cloud.yml run --rm --no-deps --volume ./test-data:/app/acceptance-data:ro backend python -m app.cloud_admin verify
