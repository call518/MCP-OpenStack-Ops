"""Read-only Keystone group listing."""

import json
from ..functions import set_identity_groups
from ..mcp_main import mcp


@mcp.tool()
async def get_identity_groups() -> str:
    """List Keystone groups subject to cloud policy."""
    return json.dumps(set_identity_groups(action='list'), indent=2)
