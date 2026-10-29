"""Tool implementation for get_volume_backups."""

import json
from ..services.storage import set_volume_backups as _query
from ..mcp_main import mcp


@mcp.tool()
async def get_volume_backups() -> str:
    """List Cinder backups visible in the current project."""
    return json.dumps(_query(action="list"), indent=2)
