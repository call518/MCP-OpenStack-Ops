"""Tool implementation for get_load_balancer_l7_policies."""

import json
from datetime import datetime
from ..functions import get_load_balancer_l7_policies as _get_load_balancer_l7_policies
from ..mcp_main import (
    logger,
    mcp,
)

@mcp.tool()
async def get_load_balancer_l7_policies(listener_name_or_id: str = "") -> str:
    """
    Get L7 policies for a listener or all L7 policies.
    
    Args:
        listener_name_or_id: Optional listener name or ID to filter policies. If empty, shows all policies.
    
    Returns:
        JSON string containing L7 policies information including policy details, actions, and rules
    """
    try:
        logger.info(f"Getting L7 policies for listener: {listener_name_or_id}")
        
        result = _get_load_balancer_l7_policies(listener_name_or_id)
        
        response = {
            "timestamp": datetime.now().isoformat(),
            "result": result
        }
        
        return json.dumps(response, indent=2, ensure_ascii=False)
        
    except Exception as e:
        error_msg = f"Error: Failed to get L7 policies - {str(e)}"
        logger.error(error_msg)
        return json.dumps({
            "timestamp": datetime.now().isoformat(),
            "error": error_msg,
            "success": False
        }, indent=2)
