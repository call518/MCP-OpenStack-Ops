"""Tool implementation for get_network_details."""

from functools import partial

from anyio import to_thread

from fastmcp.exceptions import ToolError

import json
from datetime import datetime
from ..functions import get_network_details as _get_network_details
from ..mcp_main import (
    logger,
    mcp,
)

@mcp.tool()
async def get_network_details(network_name: str = "all") -> str:
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
        
    Returns:
        Network detailed information in JSON format with networks, subnets, routers, and security groups.
    """
    try:
        logger.info(f"Fetching network details: {network_name}")
        details = await to_thread.run_sync(partial(_get_network_details, network_name))
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
        
        return json.dumps(result, indent=2, ensure_ascii=False)
        
    except Exception as error:
        logger.error("get_network_details failed error_type=%s", type(error).__name__)
        raise ToolError("OpenStack query failed: get_network_details") from None
