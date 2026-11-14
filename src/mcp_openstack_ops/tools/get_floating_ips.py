"""Tool implementation for get_floating_ips."""

import json
from datetime import datetime
from ..connection import shared_items_scope
from ..functions import get_floating_ips as _get_floating_ips
from ..mcp_main import (
    logger,
    mcp,
)

@mcp.tool()
async def get_floating_ips(all_projects: bool = False) -> str:
    """
    Get list of floating IPs with their associations.
    
    Functions:
    - Query floating IPs and their current status
    - Display associated fixed IPs and ports
    - Show floating IP pool and router associations
    - Provide floating IP allocation and usage information
    
    Use when user requests floating IP information, external connectivity queries, or IP management tasks.

    Args:
        all_projects: If True, list every floating IP Neutron shows the
            credential in any project (like 'openstack floating ip list' as an
            administrator). Requires ALLOW_CROSS_PROJECT_READ=true on the
            server. Neutron returns only what the credential may see, so check
            scope.warning.

    Returns:
        List of floating IPs with detailed association information in JSON format.
    """
    try:
        logger.info("Fetching floating IPs")
        floating_ips = _get_floating_ips(all_projects=all_projects)

        result = {
            "timestamp": datetime.now().isoformat(),
            "total_floating_ips": len(floating_ips),
            "floating_ips": floating_ips
        }
        if all_projects:
            result["scope"] = shared_items_scope(floating_ips)

        return json.dumps(result, indent=2, ensure_ascii=False)
        
    except Exception as e:
        error_msg = f"Error: Failed to fetch floating IPs - {str(e)}"
        logger.error(error_msg)
        return error_msg
