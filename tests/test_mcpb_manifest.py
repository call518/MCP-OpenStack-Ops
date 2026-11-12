"""Check the Claude Desktop bundle manifest against the server's settings."""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = json.loads((ROOT / "mcpb" / "manifest.json").read_text())
ENV = MANIFEST["server"]["mcp_config"]["env"]
CONFIG = MANIFEST["user_config"]


def test_every_user_config_value_is_passed_and_defined():
    used = {m for value in ENV.values()
            for m in re.findall(r"\$\{user_config\.(\w+)\}", value)}
    assert used == set(CONFIG)


def test_optional_service_settings_have_server_defaults():
    # An empty value would replace the server's own default and break endpoints.
    for key, item in CONFIG.items():
        if key not in {"os_cacert", "allow_modify_operations",
                       "allow_cross_project_read"}:
            assert item["required"] or item.get("default"), key
    assert CONFIG["os_password"]["sensitive"] is True
    assert CONFIG["allow_modify_operations"]["default"] is False
    assert CONFIG["allow_cross_project_read"]["default"] is False


def test_titles_name_the_environment_variable_they_set():
    for name, value in ENV.items():
        match = re.fullmatch(r"\$\{user_config\.(\w+)\}", value)
        if match:
            assert f"({name}" in CONFIG[match[1]]["title"], name
    assert "optional" in CONFIG["os_cacert"]["title"]


def test_bundle_runs_the_stdio_entry_point_with_uv():
    server = MANIFEST["server"]
    assert server["type"] == "uv" and server["entry_point"] == "server.py"
    assert (ROOT / "mcpb" / "server.py").is_file()
    assert server["mcp_config"]["args"][-1] == "server.py"
