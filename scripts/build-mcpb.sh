#!/bin/bash
# Build the Claude Desktop MCP Bundle (.mcpb).
# Usage: scripts/build-mcpb.sh <version> [output-dir]
# Only allowlisted files are copied, so local secrets such as .env are never packed.
set -euo pipefail

VERSION="${1:?usage: scripts/build-mcpb.sh <version> [output-dir]}"
OUT_DIR="${2:-dist}"
MCPB_CLI="@anthropic-ai/mcpb@2.1.2"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
STAGE="$(mktemp -d)"
trap 'rm -rf "$STAGE"' EXIT

cp "$ROOT/mcpb/server.py" "$ROOT/pyproject.toml" "$ROOT/uv.lock" \
   "$ROOT/README.md" "$ROOT/LICENSE" "$STAGE/"
cp "$ROOT/img/logo-openstack.png" "$STAGE/icon.png"
mkdir -p "$STAGE/src"
cp -R "$ROOT/src/mcp_openstack_ops" "$STAGE/src/"
find "$STAGE/src" -name '__pycache__' -type d -prune -exec rm -rf {} +

# The bundle has no Git metadata, so pass the release version to setuptools-scm.
# The manifest needs SemVer: 1.2.3rc1 becomes 1.2.3-rc.1.
python3 - "$ROOT/mcpb/manifest.json" "$STAGE/manifest.json" "$VERSION" <<'EOF'
import json, re, sys
source, target, version = sys.argv[1:]
manifest = json.load(open(source))
manifest["version"] = re.sub(r"(a|b|rc)(\d+)$", r"-\1.\2", version)
manifest["server"]["mcp_config"]["env"]["SETUPTOOLS_SCM_PRETEND_VERSION"] = version
json.dump(manifest, open(target, "w"), indent=2)
EOF

mkdir -p "$OUT_DIR"
OUTPUT="$(cd "$OUT_DIR" && pwd)/mcp-openstack-ops-$VERSION.mcpb"
npx -y "$MCPB_CLI" validate "$STAGE/manifest.json"
npx -y "$MCPB_CLI" pack "$STAGE" "$OUTPUT"
echo "Built $OUTPUT"
