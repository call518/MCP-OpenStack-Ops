"""Tool implementation for get_network_qos_policies."""

import json
from ..services.network import set_network_qos_policies as _query
from ..mcp_main import mcp


@mcp.tool()
async def get_network_qos_policies(policy_name: str = "") -> str:
    """List project-owned Neutron QoS policies with their rules, plus policies
    other projects share, or show one policy by name or ID.

    Args:
        policy_name: Optional QoS policy name or ID. When provided, show that
            policy and its rules; otherwise list policies.
    """
    if policy_name:
        return json.dumps(_query(action="show", policy_name=policy_name), indent=2)
    return json.dumps(_query(action="list"), indent=2)
