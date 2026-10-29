"""Tool implementation for get_domains."""

import json
from ..services.identity import set_domains as _query
from ..mcp_main import mcp


@mcp.tool()
async def get_domains() -> str:
    """List Keystone domains subject to cloud policy."""
    return json.dumps(_query(action="list"), indent=2)
