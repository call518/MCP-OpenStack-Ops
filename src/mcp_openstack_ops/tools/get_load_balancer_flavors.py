"""Tool implementation for get_load_balancer_flavors."""

import json
from datetime import datetime
from ..functions import get_load_balancer_flavors as _get_load_balancer_flavors
from ..mcp_main import (
    logger,
    mcp,
)

@mcp.tool()
async def get_load_balancer_flavors() -> str:
    """
    Get load balancer flavors.
    
    Returns:
        JSON string containing flavors information
    """
    try:
        logger.info("Getting load balancer flavors")
        
        result = _get_load_balancer_flavors()
        
        response = {
            "timestamp": datetime.now().isoformat(),
            "result": result
        }
        
        return json.dumps(response, indent=2, ensure_ascii=False)
        
    except Exception as e:
        error_msg = f"Error: Failed to get flavors - {str(e)}"
        logger.error(error_msg)
        return json.dumps({
            "timestamp": datetime.now().isoformat(),
            "error": error_msg,
            "success": False
        }, indent=2)
