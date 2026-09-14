#!/bin/sh
# Checks only. Does not install/remove packages, change swap or restart services.
set -eu
docker --version
case "$(docker --version)" in
    *[Pp]odman*) echo 'Podman compatibility CLI detected. Follow deploy/README.md; Docker Engine + Compose are required.'; exit 1 ;;
esac
docker info >/dev/null
docker compose version
memory_kb=$(awk '/^MemTotal:/ {print $2}' /proc/meminfo)
swap_kb=$(awk '/^SwapTotal:/ {print $2}' /proc/meminfo)
if [ "$memory_kb" -lt 3000000 ] && [ "$swap_kb" -lt 2000000 ]; then
    echo 'Less than 3 GB RAM and 2 GB swap: prepare swap before building/loading both models. See deploy/README.md.'
    exit 1
fi
disk_kb=$(df -Pk . | awk 'NR==2 {print $4}')
if [ "$disk_kb" -lt 10000000 ]; then
    echo 'Reserve at least 10 GB free disk for build layers, CPU wheels and media.'
    exit 1
fi
echo 'Resource preflight passed; this is not a guarantee of video throughput or model memory headroom.'
