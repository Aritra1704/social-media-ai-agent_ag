#!/usr/bin/env bash
set -euo pipefail

# Start the repo-managed local services from one place.
# This script starts:
# - eCardFactory
# - content_engine_ui
# - ContentForge
# - ImageForge
# - n8n (Docker, detached)
#
# It does not start external prerequisites such as PostgreSQL or Ollama.
# It can start ComfyUI when either:
# - COMFYUI is already reachable at IMAGEFORGE's configured COMFYUI_BASE_URL, or
# - a local ComfyUI path/command can be detected or provided.

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ECARD_DIR="${ROOT_DIR}/ecard-factory"
CONTENT_ENGINE_UI_DIR="${ROOT_DIR}/content_engine_ui"
CONTENTFORGE_DIR="${ROOT_DIR}/contentforge"
IMAGEFORGE_DIR="${ROOT_DIR}/imageforge"
OPS_DIR="${ROOT_DIR}/.ops"
LOG_DIR="${OPS_DIR}/logs"
PID_DIR="${OPS_DIR}/pids"

mkdir -p "${LOG_DIR}" "${PID_DIR}"

read_env_var() {
  local file="$1"
  local key="$2"
  local default_value="$3"

  if [[ ! -f "${file}" ]]; then
    printf '%s\n' "${default_value}"
    return
  fi

  (
    set -a
    # shellcheck disable=SC1090
    source "${file}"
    set +a
    local value="${!key:-$default_value}"
    printf '%s\n' "${value}"
  )
}

require_file() {
  local path="$1"
  if [[ ! -f "${path}" ]]; then
    echo "Missing required file: ${path}" >&2
    exit 1
  fi
}

require_executable() {
  local path="$1"
  if [[ ! -x "${path}" ]]; then
    echo "Missing required executable: ${path}" >&2
    exit 1
  fi
}

ensure_command() {
  local name="$1"
  if ! command -v "${name}" >/dev/null 2>&1; then
    echo "Missing required command: ${name}" >&2
    exit 1
  fi
}

start_shell_process() {
  local service_name="$1"
  local workdir="$2"
  local command="$3"
  local pid_file="${PID_DIR}/${service_name}.pid"
  local log_file="${LOG_DIR}/${service_name}.log"

  if [[ -f "${pid_file}" ]]; then
    local existing_pid
    existing_pid="$(<"${pid_file}")"
    if [[ -n "${existing_pid}" ]] && kill -0 "${existing_pid}" 2>/dev/null; then
      echo "${service_name} already running with PID ${existing_pid}"
      return
    fi
    rm -f "${pid_file}"
  fi

  (
    cd "${workdir}"
    nohup bash -lc "${command}" >> "${log_file}" 2>&1 &
    echo $! > "${pid_file}"
  )

  echo "Started ${service_name}; log: ${log_file}"
}

http_is_responding() {
  local url="$1"
  local status_code
  status_code="$(curl -s -o /dev/null -w '%{http_code}' "${url}" || true)"
  [[ "${status_code}" != "000" ]]
}

wait_for_http() {
  local name="$1"
  local url="$2"
  local attempts="${3:-30}"
  local delay_seconds="${4:-1}"

  local i
  for ((i = 1; i <= attempts; i++)); do
    if http_is_responding "${url}"; then
      echo "${name} is responding at ${url}"
      return 0
    fi
    sleep "${delay_seconds}"
  done

  echo "Warning: ${name} did not respond at ${url} after ${attempts} attempts" >&2
  return 1
}

detect_comfyui_startup_value() {
  local pattern="$1"
  local startup_file="${ECARD_DIR}/startup.txt"

  if [[ ! -f "${startup_file}" ]]; then
    return
  fi

  awk -v target="${pattern}" '
    /^comfyui[[:space:]]*$/ { in_block=1; next }
    in_block && NF == 0 { next }
    in_block && $0 ~ target {
      print
      exit
    }
  ' "${startup_file}"
}

ensure_command curl
ensure_command docker
ensure_command npm
ensure_command psql

require_file "${ECARD_DIR}/config/local.ports.env"
require_executable "${ECARD_DIR}/scripts/run-ecard.sh"
require_file "${CONTENT_ENGINE_UI_DIR}/package.json"
require_file "${CONTENTFORGE_DIR}/.env"
require_executable "${CONTENTFORGE_DIR}/venv/bin/python"
require_executable "${IMAGEFORGE_DIR}/scripts/setup_db.sh"
require_executable "${IMAGEFORGE_DIR}/scripts/run_local.sh"

# Local ports used by the repo wrappers.
# shellcheck disable=SC1091
source "${ECARD_DIR}/config/local.ports.env"

ECARD_HOST_BIND="${ECARD_HOST_BIND:-0.0.0.0}"
ECARD_PORT="${ECARD_PORT:-8080}"
CONTENT_ENGINE_UI_HOST_BIND="${CONTENT_ENGINE_UI_HOST_BIND:-127.0.0.1}"
CONTENT_ENGINE_UI_PORT="${CONTENT_ENGINE_UI_PORT:-4173}"
CONTENTFORGE_HOST_BIND="${CONTENTFORGE_HOST_BIND:-0.0.0.0}"
CONTENTFORGE_PORT="${CONTENTFORGE_PORT:-8001}"
N8N_PORT="${N8N_PORT:-5678}"
N8N_TIMEZONE="${N8N_TIMEZONE:-Asia/Kolkata}"
N8N_DATA_DIR="${N8N_DATA_DIR:-$HOME/.n8n}"
ECARD_BASE_URL="${ECARD_BASE_URL:-http://host.docker.internal:${ECARD_PORT}}"
IMAGEFORGE_PORT="$(read_env_var "${IMAGEFORGE_DIR}/.env" PORT "8090")"
OLLAMA_URL="$(read_env_var "${CONTENTFORGE_DIR}/.env" OLLAMA_URL "http://127.0.0.1:11434")"
COMFYUI_BASE_URL="$(read_env_var "${IMAGEFORGE_DIR}/.env" COMFYUI_BASE_URL "http://127.0.0.1:8188")"
DETECTED_COMFYUI_CD_LINE="$(detect_comfyui_startup_value "^cd[[:space:]]+")"
DETECTED_COMFYUI_SOURCE_LINE="$(detect_comfyui_startup_value "^source[[:space:]]+")"
DETECTED_COMFYUI_PYTHON_LINE="$(detect_comfyui_startup_value "^python[[:space:]]+")"

if [[ -n "${DETECTED_COMFYUI_CD_LINE}" ]]; then
  DETECTED_COMFYUI_DIR="${DETECTED_COMFYUI_CD_LINE#cd }"
else
  DETECTED_COMFYUI_DIR=""
fi

if [[ -n "${DETECTED_COMFYUI_SOURCE_LINE}" ]]; then
  DETECTED_COMFYUI_ACTIVATE="${DETECTED_COMFYUI_SOURCE_LINE#source }"
else
  DETECTED_COMFYUI_ACTIVATE=".venv/bin/activate"
fi

COMFYUI_DIR="${COMFYUI_DIR:-$DETECTED_COMFYUI_DIR}"
COMFYUI_ACTIVATE="${COMFYUI_ACTIVATE:-$DETECTED_COMFYUI_ACTIVATE}"
COMFYUI_START_CMD="${COMFYUI_START_CMD:-${DETECTED_COMFYUI_PYTHON_LINE:-python main.py --force-fp16}}"
START_COMFYUI="${START_COMFYUI:-auto}"
CONTENT_ENGINE_UI_API_BASE_URL="${CONTENT_ENGINE_UI_API_BASE_URL:-http://127.0.0.1:${ECARD_PORT}}"
CONTENT_ENGINE_UI_ASSET_BASE_URL="${CONTENT_ENGINE_UI_ASSET_BASE_URL:-${CONTENT_ENGINE_UI_API_BASE_URL}}"

printf -v content_engine_ui_command \
  'export CONTENT_ENGINE_UI_API_BASE_URL=%q CONTENT_ENGINE_UI_ASSET_BASE_URL=%q && exec npm run dev -- --host %q --port %q' \
  "${CONTENT_ENGINE_UI_API_BASE_URL}" \
  "${CONTENT_ENGINE_UI_ASSET_BASE_URL}" \
  "${CONTENT_ENGINE_UI_HOST_BIND}" \
  "${CONTENT_ENGINE_UI_PORT}"

mkdir -p "${N8N_DATA_DIR}"

echo "Using local ports:"
echo "  eCardFactory: ${ECARD_HOST_BIND}:${ECARD_PORT}"
echo "  content_engine_ui: ${CONTENT_ENGINE_UI_HOST_BIND}:${CONTENT_ENGINE_UI_PORT}"
echo "  ContentForge: ${CONTENTFORGE_HOST_BIND}:${CONTENTFORGE_PORT}"
echo "  ImageForge: 0.0.0.0:${IMAGEFORGE_PORT}"
echo "  n8n: 0.0.0.0:${N8N_PORT}"
echo
echo "External prerequisites expected to already be running:"
echo "  Ollama: ${OLLAMA_URL}"
echo "  ComfyUI: ${COMFYUI_BASE_URL}"
echo "  PostgreSQL: from service .env files"
echo

if http_is_responding "${COMFYUI_BASE_URL}"; then
  echo "ComfyUI already responding at ${COMFYUI_BASE_URL}"
else
  if [[ "${START_COMFYUI}" == "false" ]]; then
    echo "ComfyUI is not responding and START_COMFYUI=false; continuing without auto-start" >&2
  else
    if [[ -z "${COMFYUI_DIR}" ]]; then
      echo "ComfyUI is not responding and no COMFYUI_DIR was provided or detected." >&2
      echo "Set COMFYUI_DIR or start ComfyUI manually before ImageForge." >&2
      exit 1
    fi

    if [[ ! -d "${COMFYUI_DIR}" ]]; then
      echo "Detected COMFYUI_DIR does not exist: ${COMFYUI_DIR}" >&2
      exit 1
    fi

    printf -v comfyui_command 'source %q && exec %s' "${COMFYUI_ACTIVATE}" "${COMFYUI_START_CMD}"
    start_shell_process "comfyui" "${COMFYUI_DIR}" "${comfyui_command}"
    wait_for_http "ComfyUI" "${COMFYUI_BASE_URL}" 60 2
  fi
fi

start_shell_process "ecard-factory" "${ECARD_DIR}" "exec ./scripts/run-ecard.sh"
start_shell_process \
  "content-engine-ui" \
  "${CONTENT_ENGINE_UI_DIR}" \
  "${content_engine_ui_command}"
start_shell_process \
  "contentforge" \
  "${CONTENTFORGE_DIR}" \
  "exec ./venv/bin/python -m uvicorn app.main:app --host ${CONTENTFORGE_HOST_BIND} --port ${CONTENTFORGE_PORT} --reload"

echo "Ensuring ImageForge database schema exists..."
(
  cd "${IMAGEFORGE_DIR}"
  ./scripts/setup_db.sh
)

start_shell_process "imageforge" "${IMAGEFORGE_DIR}" "exec ./scripts/run_local.sh"

if docker ps --format '{{.Names}}' | grep -Fxq "n8n"; then
  echo "n8n container already running"
else
  echo "Starting n8n Docker container..."
  docker run -d --rm \
    --name n8n \
    -p "${N8N_PORT}:5678" \
    -e N8N_SECURE_COOKIE=false \
    -e GENERIC_TIMEZONE="${N8N_TIMEZONE}" \
    -e ECARDFACTORY_BASE_URL="${ECARD_BASE_URL}" \
    -v "${N8N_DATA_DIR}:/home/node/.n8n" \
    n8nio/n8n >/dev/null
fi

wait_for_http "ContentForge" "http://127.0.0.1:${CONTENTFORGE_PORT}/health" || true
wait_for_http "ImageForge" "http://127.0.0.1:${IMAGEFORGE_PORT}/health" || true
wait_for_http "eCardFactory" "http://127.0.0.1:${ECARD_PORT}/health" || true
wait_for_http "content_engine_ui" "http://127.0.0.1:${CONTENT_ENGINE_UI_PORT}" || true
wait_for_http "n8n" "http://127.0.0.1:${N8N_PORT}" || true

echo
echo "Logs:"
echo "  ${LOG_DIR}/comfyui.log"
echo "  ${LOG_DIR}/ecard-factory.log"
echo "  ${LOG_DIR}/content-engine-ui.log"
echo "  ${LOG_DIR}/contentforge.log"
echo "  ${LOG_DIR}/imageforge.log"
echo
echo "Recommended verification:"
echo "  curl -s -o /dev/null -w '%{http_code}\n' ${COMFYUI_BASE_URL}"
echo "  curl -s http://localhost:${CONTENTFORGE_PORT}/health"
echo "  curl -i http://127.0.0.1:${IMAGEFORGE_PORT}/ready"
echo "  curl -s http://localhost:${ECARD_PORT}/health"
echo "  curl -I http://127.0.0.1:${CONTENT_ENGINE_UI_PORT}"
echo "  curl -I http://localhost:${N8N_PORT}"
