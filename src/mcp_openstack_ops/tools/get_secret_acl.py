"""Tool implementation for get_secret_acl."""

import json
from ..services.key_manager import get_secret_acl as _query
from ..mcp_main import mcp


@mcp.tool()
async def get_secret_acl(name_or_ref: str, target_type: str = "secret") -> str:
    """Show the read ACL of a Barbican secret or container.

    The ACL lists users outside the owning project allowed to read it and
    whether project-wide access (project-access) is enabled.

    Args:
        name_or_ref: Secret or container name, ID or href.
        target_type: secret or container.
    """
    return json.dumps(_query(name_or_ref=name_or_ref, target_type=target_type),
                      indent=2, default=str)
