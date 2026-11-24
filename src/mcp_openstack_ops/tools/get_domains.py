"""Tool implementation for get_domains."""

import json
from ..services.identity import set_domains as _query
from ..mcp_main import mcp


@mcp.tool()
async def get_domains(domain_name: str = "") -> str:
    """List Keystone domains subject to cloud policy, or show one domain.

    Args:
        domain_name: Optional domain name or ID. When provided, show that
            domain; otherwise list domains.
    """
    if domain_name:
        return json.dumps(_query(action="show", domain_name=domain_name), indent=2)
    return json.dumps(_query(action="list"), indent=2)
