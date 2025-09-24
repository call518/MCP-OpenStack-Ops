"""Tool implementation for get_load_balancer_pools."""

import json
from datetime import datetime
from ..functions import get_load_balancer_pools as _get_load_balancer_pools
from ..mcp_main import (
    logger,
    mcp,
)

@mcp.tool()
async def get_load_balancer_pools(listener_name_or_id: str = "") -> str:
    """
    Get load balancer pools, optionally filtered by listener.
    
    Functions:
    - Lists all pools or pools for a specific listener
    - Shows pool protocols, load balancing algorithms
    - Displays members in each pool with their status
    - Provides health monitor associations
    
    Use when user requests:
    - "Show all load balancer pools"
    - "List pools for listener [name/id]"
    - "What pools are configured on [listener_name]?"
    - "Show pool members and their status"
    
    Args:
        listener_name_or_id: Optional listener name or ID to filter pools
        
    Returns:
        JSON string containing pool details with member information
    """
    try:
        logger.info(f"Getting load balancer pools (listener filter: {listener_name_or_id if listener_name_or_id else 'none'})")
        result = _get_load_balancer_pools(
            listener_name_or_id=listener_name_or_id if listener_name_or_id else None
        )
        
        response = {
            "timestamp": datetime.now().isoformat(),
            "result": result
        }
        
        return json.dumps(response, indent=2, ensure_ascii=False)
        
    except Exception as e:
        error_msg = f"Error: Failed to get load balancer pools - {str(e)}"
        logger.error(error_msg)
        return json.dumps({
            "timestamp": datetime.now().isoformat(),
            "error": error_msg,
            "success": False
        }, indent=2)
