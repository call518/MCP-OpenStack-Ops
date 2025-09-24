"""Tool implementation for get_load_balancer_listeners."""

import json
from datetime import datetime
from ..functions import get_load_balancer_listeners as _get_load_balancer_listeners
from ..mcp_main import (
    logger,
    mcp,
)

@mcp.tool()
async def get_load_balancer_listeners(lb_name_or_id: str) -> str:
    """
    Get listeners for a specific OpenStack load balancer.
    
    Functions:
    - Lists all listeners attached to a load balancer
    - Shows listener protocols, ports, and configurations
    - Displays admin state and default pool associations
    - Provides creation and update timestamps
    
    Use when user requests:
    - "Show listeners for load balancer [name/id]"
    - "List load balancer listeners"
    - "What ports are configured on load balancer [name]?"
    - "Show listener configuration for [lb_name]"
    
    Args:
        lb_name_or_id: Load balancer name or ID
        
    Returns:
        JSON string containing listener details for the load balancer
    """
    try:
        logger.info(f"Getting listeners for load balancer: {lb_name_or_id}")
        result = _get_load_balancer_listeners(lb_name_or_id)
        
        response = {
            "timestamp": datetime.now().isoformat(),
            "result": result
        }
        
        return json.dumps(response, indent=2, ensure_ascii=False)
        
    except Exception as e:
        error_msg = f"Error: Failed to get load balancer listeners - {str(e)}"
        logger.error(error_msg)
        return json.dumps({
            "timestamp": datetime.now().isoformat(),
            "error": error_msg,
            "success": False
        }, indent=2)
