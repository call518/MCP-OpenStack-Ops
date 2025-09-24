"""Tool implementation for get_routers."""

import json
from datetime import datetime
from ..functions import get_routers as _get_routers
from ..mcp_main import (
    logger,
    mcp,
)

@mcp.tool()
async def get_routers() -> str:
    """
    Get list of routers with their configuration.
    
    Functions:
    - Query routers and their external gateway configurations
    - Display router interfaces and connected networks
    - Show routing table entries and static routes
    - Provide comprehensive network routing information
    
    Use when user requests router information, network connectivity queries, or routing configuration.
    
    Returns:
        List of routers with detailed configuration in JSON format.
    """
    try:
        logger.info("Fetching routers")
        routers = _get_routers()
        
        result = {
            "timestamp": datetime.now().isoformat(),
            "total_routers": len(routers),
            "routers": routers
        }
        
        return json.dumps(result, indent=2, ensure_ascii=False)
        
    except Exception as e:
        error_msg = f"Error: Failed to fetch routers - {str(e)}"
        logger.error(error_msg)
        return error_msg
