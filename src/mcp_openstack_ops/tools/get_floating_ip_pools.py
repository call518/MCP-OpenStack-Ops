"""Tool implementation for get_floating_ip_pools."""

import json
from datetime import datetime
from ..functions import get_floating_ip_pools as _get_floating_ip_pools
from ..mcp_main import (
    logger,
    mcp,
)

@mcp.tool()
async def get_floating_ip_pools() -> str:
    """
    Get list of floating IP pools (external networks).
    
    Functions:
    - List all external networks that can provide floating IPs
    - Show available and used IP counts for each pool
    - Display network configuration for floating IP allocation
    - Provide pool capacity and utilization information
    
    Use when user requests:
    - "Show floating IP pools"
    - "List available floating IP networks"
    - "Check floating IP capacity"
    - "What external networks are available?"
    
    Returns:
        List of floating IP pools with capacity information in JSON format.
    """
    try:
        result_data = _get_floating_ip_pools()
        
        result = {
            "timestamp": datetime.now().isoformat(),
            "pools": result_data,
            "total_pools": len(result_data)
        }
        
        return json.dumps(result, indent=2)
        
    except Exception as e:
        error_msg = f"Error: Failed to get floating IP pools - {str(e)}"
        logger.error(error_msg)
        return error_msg
