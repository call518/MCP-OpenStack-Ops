"""Tool implementation for get_compute_agents."""

import json
from ..functions import get_compute_agents as _get_compute_agents
from ..mcp_main import mcp


@mcp.tool()
async def get_compute_agents(agent_id: str = "", host: str = "") -> str:
    """List Nova compute services with their hypervisors, or show one service
    (like 'openstack compute service list' and 'openstack hypervisor list').

    This is a cloud-wide administrative API; cloud policy usually restricts it
    to administrators. Hypervisor capacity is capacity, not measured usage.

    Args:
        agent_id: Optional compute service ID. When provided, show that
            service; otherwise list services and hypervisors.
        host: Optional host name that filters the list.

    Returns:
        JSON with compute_services and hypervisors (or agent_details). When
        only the hypervisor listing fails, hypervisors_error carries the error.
    """
    return json.dumps(_get_compute_agents(agent_id=agent_id or None,
                                          host=host or None), indent=2)
