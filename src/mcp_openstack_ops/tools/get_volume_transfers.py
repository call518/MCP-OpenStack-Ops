"""Tool implementation for get_volume_transfers."""

import json
from ..services.storage import get_volume_transfers as _query
from ..mcp_main import mcp


@mcp.tool()
async def get_volume_transfers() -> str:
    """List current-project Cinder volume transfer requests without authorization keys.
    """
    return json.dumps(_query(), indent=2)
