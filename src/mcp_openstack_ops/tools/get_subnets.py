"""Tool implementation for get_subnets."""

import json
from ..services.network import set_subnets as _query
from ..mcp_main import mcp


@mcp.tool()
async def get_subnets(subnet_name: str = "", all_projects: bool = False) -> str:
    """List the current project's Neutron subnets, plus the subnets of shared
    and external networks, or show one subnet.

    For subnets grouped under their networks, use get_network_details.

    Args:
        subnet_name: Optional subnet name or ID. When provided, show that
            subnet (with host_routes, created_at and updated_at); otherwise
            list subnets.
        all_projects: List only. If True, list every subnet Neutron shows the
            credential in any project (like 'openstack subnet list' as an
            administrator). Requires ALLOW_CROSS_PROJECT_READ=true on the
            server; rows then carry project_name and shared, and the result
            has a scope (check scope.warning).

    Returns:
        JSON with subnets (or subnet), each with description, project_id,
        network_id, cidr, gateway_ip, allocation_pools and dns_nameservers.
    """
    if subnet_name:
        return json.dumps(_query(action="show", subnet_name=subnet_name,
                                 all_projects=all_projects), indent=2)
    return json.dumps(_query(action="list", all_projects=all_projects), indent=2)
