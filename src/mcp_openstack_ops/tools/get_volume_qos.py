"""Tool implementation for get_volume_qos."""

import json
from ..services.storage import set_volume_qos as _query
from ..mcp_main import mcp


@mcp.tool()
async def get_volume_qos(qos_name: str = "") -> str:
    """List Cinder QoS specifications, or show one specification's volume type
    associations by name or ID. Cloud policy may require admin rights.

    Args:
        qos_name: Optional QoS specification name or ID. When provided, return
            its current volume type associations; otherwise list specifications.
    """
    action = "associations" if qos_name else "list"
    return json.dumps(_query(action=action, qos_name=qos_name or None), indent=2)
