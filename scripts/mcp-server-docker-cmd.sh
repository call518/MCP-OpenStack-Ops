#!/bin/bash
set -eo pipefail

# Load .env file from parent directory of script location
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd -P)"
env_file="${script_dir%/*}/.env"
if [[ -f "$env_file" ]]; then
  set -o allexport
  . "$env_file"
  set +o allexport
else
  echo "error: .env not found: $env_file" >&2
  return 1 2>/dev/null || exit 1
fi

echo "Starting OpenStack MCP server with:"
echo "  PYTHONPATH: ${PYTHONPATH}"
echo "  FASTMCP_TYPE: ${FASTMCP_TYPE}"
echo "  FASTMCP_HOST: ${FASTMCP_HOST}"
echo "  FASTMCP_PORT: ${FASTMCP_PORT}"
echo "  MCP_LOG_LEVEL: ${MCP_LOG_LEVEL}"
echo "  OS_AUTH_URL: ${OS_AUTH_URL}"
echo "  OS_PROJECT_NAME: ${OS_PROJECT_NAME}"
echo "  OS_USERNAME: ${OS_USERNAME}"
echo "  OS_REGION_NAME: ${OS_REGION_NAME}"

python -m mcp_openstack_ops --type ${FASTMCP_TYPE} --host ${FASTMCP_HOST} --port ${FASTMCP_PORT}
