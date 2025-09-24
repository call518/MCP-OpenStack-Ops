"""Tool implementation for get_load_balancer_list."""

import json
from datetime import datetime
from ..functions import get_load_balancer_list as _get_load_balancer_list
from ..mcp_main import (
    logger,
    mcp,
)

@mcp.tool()
async def get_load_balancer_list(
    limit: int = 50,
    offset: int = 0,
    include_all: bool = False
) -> str:
    """
    Retrieve comprehensive list of OpenStack load balancers with detailed information.
    
    Functions:
    - Lists all load balancers in the OpenStack cluster
    - Provides detailed load balancer information including VIP, status, listeners
    - Supports pagination for large environments (limit/offset)
    - Shows listener count and basic listener information for each load balancer
    - Displays provisioning and operating status for troubleshooting
    
    Use when user requests:
    - "Show me all load balancers"
    - "List load balancers with details"
    - "What load balancers are available?"
    - "Show load balancer status"
    
    Args:
        limit: Maximum load balancers to return (1-200, default: 50)
        offset: Number of load balancers to skip for pagination (default: 0)  
        include_all: Return all load balancers ignoring limit/offset (default: False)
        
    Returns:
        JSON string containing load balancer details with summary statistics
    """
    try:
        logger.info(f"Getting load balancer list (limit={limit}, offset={offset}, include_all={include_all})")
        result = _get_load_balancer_list(
            limit=limit,
            offset=offset, 
            include_all=include_all
        )
        
        response = {
            "timestamp": datetime.now().isoformat(),
            "result": result
        }
        
        return json.dumps(response, indent=2, ensure_ascii=False)
        
    except Exception as e:
        error_msg = f"Error: Failed to get load balancer list - {str(e)}"
        logger.error(error_msg)
        return json.dumps({
            "timestamp": datetime.now().isoformat(),
            "error": error_msg,
            "success": False
        }, indent=2)
