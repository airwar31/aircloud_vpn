#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${ROOT_DIR}/.env"

if [[ ! -f "${ENV_FILE}" ]]; then
  echo "ERROR: .env not found at ${ENV_FILE}" >&2
  exit 1
fi

set -a
# shellcheck disable=SC1090
source "${ENV_FILE}"
set +a

CONTAINER_NAME="${XUI_SYNC_CONTAINER:-nl-xray-panel}"
XRAY_USER="${XRAY_USERNAME:-}"
XRAY_PASS="${XRAY_PASSWORD:-}"

if [[ -z "${XRAY_USER}" || -z "${XRAY_PASS}" ]]; then
  echo "ERROR: XRAY_USERNAME/XRAY_PASSWORD must be set in .env" >&2
  exit 1
fi

resolve_container_name() {
  local requested_name="$1"
  local resolved_name=""

  # 1) exact name from env
  if docker ps -a --format '{{.Names}}' | grep -qx "${requested_name}"; then
    echo "${requested_name}"
    return 0
  fi

  # 2) compose service label (works even when project prefix is used)
  resolved_name="$(docker ps -a --filter 'label=com.docker.compose.service=xray-panel' --format '{{.Names}}' | head -n 1 || true)"
  if [[ -n "${resolved_name}" ]]; then
    echo "${resolved_name}"
    return 0
  fi

  # 3) loose fallback by common suffix/pattern
  resolved_name="$(docker ps -a --format '{{.Names}}' | grep -E '(^|_)xray-panel$|nl-xray-panel' | head -n 1 || true)"
  if [[ -n "${resolved_name}" ]]; then
    echo "${resolved_name}"
    return 0
  fi

  return 1
}

if ! CONTAINER_NAME="$(resolve_container_name "${CONTAINER_NAME}")"; then
  echo "ERROR: xray panel container not found (tried '${XUI_SYNC_CONTAINER:-nl-xray-panel}', compose label, and name patterns)" >&2
  exit 1
fi

if ! docker ps --format '{{.Names}}' | grep -qx "${CONTAINER_NAME}"; then
  docker start "${CONTAINER_NAME}" >/dev/null
fi

run_setting() {
  local bin_path="$1"
  docker exec \
    -e XUI_USER="${XRAY_USER}" \
    -e XUI_PASS="${XRAY_PASS}" \
    "${CONTAINER_NAME}" \
    sh -lc "${bin_path} setting -username \"\$XUI_USER\" -password \"\$XUI_PASS\""
}

if run_setting "x-ui"; then
  echo "Applied credentials using: x-ui"
elif run_setting "/usr/local/x-ui/x-ui"; then
  echo "Applied credentials using: /usr/local/x-ui/x-ui"
elif run_setting "/app/x-ui"; then
  echo "Applied credentials using: /app/x-ui"
else
  echo "ERROR: failed to apply 3x-ui credentials inside ${CONTAINER_NAME}" >&2
  exit 1
fi

docker restart "${CONTAINER_NAME}" >/dev/null
echo "3x-ui credentials synchronized and container restarted."
