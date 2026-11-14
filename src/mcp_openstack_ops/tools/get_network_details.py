"""Tool implementation for get_network_details."""

from functools import partial

from anyio import to_thread

from fastmcp.exceptions import ToolError

import json
from datetime import datetime
from ..connection import CrossProjectReadError, shared_items_scope
from ..functions import get_network_details as _get_network_details
from ..mcp_main import (
    logger,
    mcp,
)

@mcp.tool()
async def get_network_details(network_name: str = "all", all_projects: bool = False) -> str:
    """
    Provides detailed information for OpenStack networks, subnets, routers, and security groups.
    
    Functions:
    - Query configuration information for specified network or all networks
    - Check subnet configuration and IP allocation status per network
    - Collect router connection status and gateway configuration
    - Analyze security group rules and port information
    
    Use when user requests network information, subnet details, router configuration, or network troubleshooting.
    
    Args:
        network_name: Name of network to query or "all" for all networks (default: "all")
        all_projects: If True, list every network Neutron shows the credential
            in any project (like 'openstack network list' as an administrator);
            use only with network_name "all". Requires
            ALLOW_CROSS_PROJECT_READ=true on the server. Neutron returns only
            what the credential may see, so check scope.warning.

    Returns:
        Network detailed information in JSON format with networks, subnets, routers, and security groups.
    """
    if all_projects and network_name.lower() != "all":
        raise ToolError("get_network_details: all_projects=true lists every "
                        "network; omit network_name")
    try:
        logger.info(f"Fetching network details: {network_name}")
        # The default call keeps its original arguments.
        cross_project = {'all_projects': True} if all_projects else {}
        details = await to_thread.run_sync(
            partial(_get_network_details, network_name, **cross_project))
        if network_name.lower() != "all" and not details:
            # A specific lookup that matched nothing is an error, not an
            # empty inventory.
            return (f"Error: Network '{network_name}' not found or not "
                    "accessible in the current project")

        result = {
            "timestamp": datetime.now().isoformat(), 
            "requested_network": network_name,
            "network_details": details
        }
        if all_projects:
            result["scope"] = await to_thread.run_sync(
                partial(shared_items_scope, details))

        return json.dumps(result, indent=2, ensure_ascii=False)

    except CrossProjectReadError as error:
        raise ToolError(f"OpenStack query failed: get_network_details - {error}") from None
    except Exception as error:
        logger.error("get_network_details failed error_type=%s", type(error).__name__)
        raise ToolError("OpenStack query failed: get_network_details") from None
