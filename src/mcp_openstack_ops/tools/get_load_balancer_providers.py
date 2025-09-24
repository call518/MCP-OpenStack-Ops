"""Tool implementation for get_load_balancer_providers."""

import json
from datetime import datetime
from ..functions import get_load_balancer_providers as _get_load_balancer_providers
from ..mcp_main import (
    logger,
    mcp,
)

@mcp.tool()
async def get_load_balancer_providers() -> str:
    """
    Get load balancer providers.
    
    Returns:
        JSON string containing providers information
    """
    try:
        logger.info("Getting load balancer providers")
        
        result = _get_load_balancer_providers()
        
        response = {
            "timestamp": datetime.now().isoformat(),
            "result": result
        }
        
        return json.dumps(response, indent=2, ensure_ascii=False)
        
    except Exception as e:
        error_msg = f"Error: Failed to get providers - {str(e)}"
        logger.error(error_msg)
        return json.dumps({
            "timestamp": datetime.now().isoformat(),
            "error": error_msg,
            "success": False
        }, indent=2)
