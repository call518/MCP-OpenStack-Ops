"""Tool implementation for get_volume_qos."""

import json
from ..services.storage import set_volume_qos as _query
from ..mcp_main import mcp


@mcp.tool()
async def get_volume_qos() -> str:
    """List Cinder QoS specifications. Cloud policy may require admin rights."""
    return json.dumps(_query(action="list"), indent=2)
