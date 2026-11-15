"""Tool implementation for get_key_manager_quotas."""

import json
from ..services.key_manager import get_key_manager_quotas as _query
from ..mcp_main import mcp


@mcp.tool()
async def get_key_manager_quotas() -> str:
    """Show the effective Barbican quotas (secrets, orders, containers, consumers,
    CAs) of the current project; -1 means unlimited."""
    return json.dumps(_query(), indent=2, default=str)
