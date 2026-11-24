"""Tool implementation for get_roles."""

import json
from ..functions import set_roles as _query
from ..mcp_main import mcp


@mcp.tool()
async def get_roles() -> str:
    """List Keystone roles (like 'openstack role list'), subject to cloud policy.

    For which users or groups hold a role on which project, use
    get_role_assignments.

    Returns:
        JSON with roles, each with id, name, description and domain_id.
    """
    return json.dumps(_query(action='list'), indent=2)
