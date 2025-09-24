"""Tool implementation for get_load_balancer_details."""

import json
from datetime import datetime
from ..functions import get_load_balancer_details as _get_load_balancer_details
from ..mcp_main import (
    logger,
    mcp,
)

@mcp.tool()
async def get_load_balancer_details(lb_name_or_id: str) -> str:
    """
    Get detailed information about a specific OpenStack load balancer.
    
    Functions:
    - Shows comprehensive load balancer details including VIP configuration
    - Lists all listeners with their protocols and ports
    - Shows pools and members for each listener
    - Displays health monitor information if configured
    - Provides provisioning and operating status
    
    Use when user requests:
    - "Show details for load balancer [name/id]"
    - "Get load balancer configuration"
    - "Show load balancer listeners and pools"
    - "What's the status of load balancer [name]?"
    
    Args:
        lb_name_or_id: Load balancer name or ID to query
        
    Returns:
        JSON string containing detailed load balancer information
    """
    try:
        logger.info(f"Getting load balancer details for: {lb_name_or_id}")
        result = _get_load_balancer_details(lb_name_or_id)
        
        response = {
            "timestamp": datetime.now().isoformat(),
            "result": result
        }
        
        return json.dumps(response, indent=2, ensure_ascii=False)
        
    except Exception as e:
        error_msg = f"Error: Failed to get load balancer details - {str(e)}"
        logger.error(error_msg)
        return json.dumps({
            "timestamp": datetime.now().isoformat(),
            "error": error_msg,
            "success": False
        }, indent=2)
