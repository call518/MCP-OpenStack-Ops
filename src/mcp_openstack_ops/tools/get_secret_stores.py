"""Tool implementation for get_secret_stores."""

import json
from ..services.key_manager import get_secret_stores as _query
from ..mcp_main import mcp


@mcp.tool()
async def get_secret_stores() -> str:
    """List Barbican secret store backends. Only clouds that enable multiple
    secret store backends serve this API; others return an error."""
    return json.dumps(_query(), indent=2, default=str)
