"""Tool implementation for get_volume_groups."""

import json
from ..services.storage import set_volume_groups as _query
from ..mcp_main import mcp


@mcp.tool()
async def get_volume_groups() -> str:
    """List current-project Cinder generic groups. Requires API microversion >= 3.13."""
    return json.dumps(_query(action="list"), indent=2)
