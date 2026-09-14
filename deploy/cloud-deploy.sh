#!/bin/sh
set -eu
cd "$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
if [ ! -f .env.cloud ]; then
    cp deploy/cloud.env.example .env.cloud
    chmod 600 .env.cloud
    echo 'Created .env.cloud. Fill DEMO_PASSWORD and the three provider keys, then rerun.'
    exit 1
fi
docker info >/dev/null
docker compose version >/dev/null
sh deploy/cloud-preflight.sh
case "$(uname -m)" in
    x86_64|amd64) ;;
    *) echo 'This package targets Linux x86_64/amd64. Do not silently emulate it on a small ARM server.'; exit 1 ;;
esac
for model in models/yolo26-tt100k-best.pt models/yolo26m.pt; do
    [ -s "$model" ] || { echo "Missing model: $model"; exit 1; }
done
mkdir -p cloud-data uploads outputs .cloud-runtime
chmod 700 .cloud-runtime
chmod 600 .env.cloud
docker compose --env-file .env.cloud -f docker-compose.cloud.yml config --quiet
docker compose --env-file .env.cloud -f docker-compose.cloud.yml build
docker compose --env-file .env.cloud -f docker-compose.cloud.yml run --rm --no-deps backend python -m app.cloud_admin setup
docker compose --env-file .env.cloud -f docker-compose.cloud.yml up -d --wait --wait-timeout 240
docker compose --env-file .env.cloud -f docker-compose.cloud.yml exec -T backend python -m app.cloud_admin seed
docker compose --env-file .env.cloud -f docker-compose.cloud.yml exec -T backend python -m app.cloud_admin check
docker compose --env-file .env.cloud -f docker-compose.cloud.yml ps
echo 'Containers started and basic checks passed. Verify browser access via the public IP; do not open backend/vector/database ports.'
echo 'Run deploy/cloud-verify.sh for the actual CPU image/report/review and public-gateway authentication acceptance.'
