"""Tool implementation for get_network_agents."""

import json
from ..services.network import set_network_agents as _query
from ..mcp_main import mcp


@mcp.tool()
async def get_network_agents() -> str:
    """List Neutron agents (like 'openstack network agent list').

    This is a cloud-wide administrative API; cloud policy usually restricts it
    to administrators, and a denial is returned as a failure.

    Returns:
        JSON with agents, each as Neutron returns it (agent_type, host,
        is_alive, is_admin_state_up, ...).
    """
    return json.dumps(_query(action="list"), indent=2)
