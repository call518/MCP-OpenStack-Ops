"""Tool implementation for get_network_qos_policies."""

import json
from ..services.network import set_network_qos_policies as _query
from ..mcp_main import mcp


@mcp.tool()
async def get_network_qos_policies() -> str:
    """List project-owned Neutron QoS policy containers; no bandwidth rules are
    created.
    """
    return json.dumps(_query(action="list"), indent=2)
