#!/usr/bin/env bash
set -euo pipefail

# Stop only the local services started by ./start-all.sh.
# This script uses PID files for Python services and the fixed Docker
# container name "n8n" for the automation service.

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_DIR="${ROOT_DIR}/.ops/pids"

stop_pid_service() {
  local service_name="$1"
  local pid_file="${PID_DIR}/${service_name}.pid"

  if [[ ! -f "${pid_file}" ]]; then
    echo "${service_name}: no PID file"
    return
  fi

  local pid
  pid="$(<"${pid_file}")"

  if [[ -z "${pid}" ]]; then
    echo "${service_name}: empty PID file"
    rm -f "${pid_file}"
    return
  fi

  if ! kill -0 "${pid}" 2>/dev/null; then
    echo "${service_name}: process ${pid} not running"
    rm -f "${pid_file}"
    return
  fi

  echo "Stopping ${service_name} (PID ${pid})"
  kill "${pid}"

  local i
  for ((i = 1; i <= 10; i++)); do
    if ! kill -0 "${pid}" 2>/dev/null; then
      rm -f "${pid_file}"
      echo "${service_name}: stopped"
      return
    fi
    sleep 1
  done

  echo "${service_name}: forcing stop"
  kill -9 "${pid}" 2>/dev/null || true
  rm -f "${pid_file}"
}

stop_pid_service "comfyui"
stop_pid_service "ecard-factory"
stop_pid_service "content-engine-ui"
stop_pid_service "contentforge"
stop_pid_service "imageforge"

if command -v docker >/dev/null 2>&1; then
  if docker ps --format '{{.Names}}' | grep -Fxq "n8n"; then
    echo "Stopping n8n container"
    docker stop n8n >/dev/null
  else
    echo "n8n: container not running"
  fi
else
  echo "docker not found; skipping n8n shutdown"
fi
