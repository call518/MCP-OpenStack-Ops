"""Tool implementation for get_load_balancer_availability_zones."""

import json
from datetime import datetime
from ..functions import get_load_balancer_availability_zones as _get_load_balancer_availability_zones
from ..mcp_main import (
    logger,
    mcp,
)

@mcp.tool()
async def get_load_balancer_availability_zones() -> str:
    """
    Get load balancer availability zones.
    
    Returns:
        JSON string containing availability zones information
    """
    try:
        logger.info("Getting load balancer availability zones")
        
        result = _get_load_balancer_availability_zones()
        
        response = {
            "timestamp": datetime.now().isoformat(),
            "result": result
        }
        
        return json.dumps(response, indent=2, ensure_ascii=False)
        
    except Exception as e:
        error_msg = f"Error: Failed to get availability zones - {str(e)}"
        logger.error(error_msg)
        return json.dumps({
            "timestamp": datetime.now().isoformat(),
            "error": error_msg,
            "success": False
        }, indent=2)
