"""Tool implementation for get_load_balancer_pool_members."""

import json
from datetime import datetime
from ..mcp_main import (
    logger,
    mcp,
)

@mcp.tool()
async def get_load_balancer_pool_members(pool_name_or_id: str) -> str:
    """
    Get members for a specific OpenStack load balancer pool.

    Functions:
    - Lists all members in a specific pool
    - Shows member addresses, ports, weights, and health status
    - Displays member admin state and operational status
    - Provides monitor configuration for each member

    Use when user requests:
    - "Show members for pool [name/id]"
    - "List pool members"
    - "What members are in pool [name]?"
    - "Show pool member status"

    Args:
        pool_name_or_id: Pool name or ID to query members for
        
    Returns:
        JSON string containing member details for the pool
    """
    try:
        from .functions import get_load_balancer_pool_members
        
        result = get_load_balancer_pool_members(pool_name_or_id)
        
        response = {
            "timestamp": datetime.now().isoformat(),
            "pool": pool_name_or_id,
            "result": result
        }
        
        return json.dumps(response, indent=2, ensure_ascii=False)
        
    except Exception as e:
        error_msg = f"Error: Failed to get pool members - {str(e)}"
        logger.error(error_msg)
        return json.dumps({
            "timestamp": datetime.now().isoformat(),
            "error": error_msg,
            "success": False
        }, indent=2)
