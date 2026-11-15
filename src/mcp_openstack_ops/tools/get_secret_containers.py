"""Tool implementation for get_secret_containers."""

import json
from ..services.key_manager import get_secret_containers as _query
from ..mcp_main import mcp


@mcp.tool()
async def get_secret_containers(name: str = "", limit: int = 100) -> str:
    """List or show Barbican secret containers of the current project.

    A container groups secret hrefs, e.g. a certificate container with
    certificate, private_key and intermediates entries. Payloads are never
    returned.

    Args:
        name: Container name, ID or href to show one container. Empty lists
            containers.
        limit: Maximum number of containers to list (1-1000).
    """
    return json.dumps(_query(name=name, limit=limit), indent=2, default=str)
