"""Tool implementation for get_network_ports."""

import json
from ..services.network import set_network_ports as _query
from ..mcp_main import mcp


@mcp.tool()
async def get_network_ports(port_name: str = "", all_projects: bool = False) -> str:
    """List Neutron ports owned by the current project, or show one port.

    Args:
        port_name: Optional port name or ID. When provided, show that port
            (with created_at and updated_at); otherwise list ports.
        all_projects: List only. If True, list every port Neutron shows the
            credential in any project, such as Octavia amphora VRRP ports,
            which belong to the project Octavia uses for its Neutron calls,
            not to the load balancer's project. Requires
            ALLOW_CROSS_PROJECT_READ=true on the server; rows then carry
            project_name, and the result has a scope (check scope.warning).

    Returns:
        JSON with ports (or port). Rows include project_id, qos_policy_id
        (the policy attached to the port) and qos_network_policy_id (the
        policy inherited from its network); a null value means no policy.
    """
    if port_name:
        return json.dumps(_query(action="show", port_name=port_name,
                                 all_projects=all_projects), indent=2)
    return json.dumps(_query(action="list", all_projects=all_projects), indent=2)
