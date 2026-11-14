"""Tool implementation for get_routers."""

from fastmcp.exceptions import ToolError
import json
from datetime import datetime
from ..connection import CrossProjectReadError, shared_items_scope
from ..functions import get_routers as _get_routers
from ..mcp_main import (
    logger,
    mcp,
)

@mcp.tool()
async def get_routers(all_projects: bool = False) -> str:
    """
    Get list of routers with their configuration.

    Functions:
    - Query routers and their external gateway configurations
    - Display router interfaces and connected networks
    - Show routing table entries and static routes
    - Provide comprehensive network routing information

    Use when user requests router information, network connectivity queries, or routing configuration.

    Args:
        all_projects: If True, list every router Neutron shows the credential
            in any project (like 'openstack router list' as an administrator).
            Requires ALLOW_CROSS_PROJECT_READ=true on the server. Neutron
            returns only what the credential may see, so check scope.warning.

    Returns:
        List of routers with detailed configuration in JSON format.
    """
    try:
        logger.info("Fetching routers")
        routers = _get_routers(all_projects=all_projects)
        result = {
            "timestamp": datetime.now().isoformat(),
            "total_routers": len(routers),
            "routers": routers
        }
        if all_projects:
            result["scope"] = shared_items_scope(routers)
        return json.dumps(result, indent=2, ensure_ascii=False)
    except CrossProjectReadError as error:
        raise ToolError(f"OpenStack query failed: get_routers - {error}") from None
    except Exception as error:
        logger.error("get_routers failed error_type=%s", type(error).__name__)
        raise ToolError("OpenStack query failed: get_routers") from None
