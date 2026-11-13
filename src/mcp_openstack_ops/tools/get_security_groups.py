"""Tool implementation for get_security_groups."""

from functools import partial

from anyio import to_thread

import json
from datetime import datetime
from ..connection import neutron_items_scope
from ..functions import get_security_groups as _get_security_groups
from ..mcp_main import (
    logger,
    mcp,
)

@mcp.tool()
async def get_security_groups(all_projects: bool = False) -> str:
    """
    Get list of security groups with their rules.
    
    Functions:
    - Query security groups and their rule configurations
    - Display ingress and egress rules with protocols and ports
    - Show remote IP prefixes and security group references
    - Provide comprehensive network security information
    
    Use when user requests security group information, firewall rules, or network security queries.

    Args:
        all_projects: If True, list every security group Neutron shows the
            credential in any project (like 'openstack security group list
            --all-projects'). Requires ALLOW_CROSS_PROJECT_READ=true on the
            server. Neutron returns only what the credential may see, so check
            scope.warning.

    Returns:
        List of security groups with detailed rules in JSON format.
    """
    try:
        logger.info("Fetching security groups")
        security_groups = await to_thread.run_sync(
            partial(_get_security_groups, all_projects=all_projects))

        result = {
            "timestamp": datetime.now().isoformat(),
            "total_security_groups": len(security_groups),
            "security_groups": security_groups
        }
        if all_projects:
            result["scope"] = await to_thread.run_sync(
                partial(neutron_items_scope, security_groups))

        return json.dumps(result, indent=2, ensure_ascii=False)
        
    except Exception as e:
        error_msg = f"Error: Failed to fetch security groups - {str(e)}"
        logger.error(error_msg)
        return error_msg
