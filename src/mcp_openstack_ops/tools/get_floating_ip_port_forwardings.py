"""Tool implementation for get_floating_ip_port_forwardings."""

import json
from ..services.network import set_floating_ip_port_forwarding as _query
from ..mcp_main import mcp


@mcp.tool()
async def get_floating_ip_port_forwardings(
    floating_ip_id: str = "",
    floating_ip_address: str = "",
    port_forwarding_id: str = "",
) -> str:
    """List the port forwarding rules of a floating IP, or show one rule.

    Works only on floating IPs owned by the current project. Requires the
    Neutron port forwarding extension.

    Args:
        floating_ip_id: Floating IP ID (alternative to floating_ip_address)
        floating_ip_address: Floating IP address (alternative to floating_ip_id)
        port_forwarding_id: Optional rule ID. When provided, show that rule;
            otherwise list the floating IP's rules.

    Returns:
        JSON with port_forwardings (or port_forwarding): protocol,
        external_port, internal_port, internal_ip_address, internal_port_id
        and description.
    """
    kwargs = {
        'floating_ip_id': floating_ip_id.strip() or None,
        'floating_ip_address': floating_ip_address.strip() or None,
        'port_forwarding_id': port_forwarding_id.strip() or None,
    }
    action = "show" if kwargs['port_forwarding_id'] else "list"
    return json.dumps(_query(action, **kwargs), indent=2)
