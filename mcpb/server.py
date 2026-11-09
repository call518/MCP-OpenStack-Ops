"""MCPB entry point: run the MCP-OpenStack-Ops server over stdio.

The bundle host runs this file with uv from the bundle root, after installing
the project and its locked dependencies from pyproject.toml and uv.lock.
"""

from mcp_openstack_ops.mcp_main import main

if __name__ == "__main__":
    main(["--type", "stdio"])
