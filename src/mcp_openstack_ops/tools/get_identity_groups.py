"""Read-only Keystone group listing."""

import json
from ..functions import set_identity_groups
from ..mcp_main import mcp


@mcp.tool()
async def get_identity_groups(group_name: str = "", domain_id: str = "default") -> str:
    """List Keystone groups subject to cloud policy, or show one group.

    Args:
        group_name: Optional group name or ID. When provided, show that group;
            otherwise list groups.
        domain_id: Domain ID used to find group_name (default: 'default');
            ignored for the list.
    """
    if group_name:
        return json.dumps(set_identity_groups(
            action='show', group_name=group_name, domain_id=domain_id), indent=2)
    return json.dumps(set_identity_groups(action='list'), indent=2)
