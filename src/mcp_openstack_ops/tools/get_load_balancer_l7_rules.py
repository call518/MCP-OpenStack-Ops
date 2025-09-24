"""Tool implementation for get_load_balancer_l7_rules."""

import json
from datetime import datetime
from ..functions import get_load_balancer_l7_rules as _get_load_balancer_l7_rules
from ..mcp_main import (
    logger,
    mcp,
)

@mcp.tool()
async def get_load_balancer_l7_rules(policy_name_or_id: str) -> str:
    """
    Get L7 rules for a specific L7 policy.
    
    Args:
        policy_name_or_id: L7 policy name or ID (required)
    
    Returns:
        JSON string containing L7 rules information including rule types, values, and conditions
    """
    try:
        logger.info(f"Getting L7 rules for policy: {policy_name_or_id}")
        
        result = _get_load_balancer_l7_rules(policy_name_or_id)
        
        response = {
            "timestamp": datetime.now().isoformat(),
            "result": result
        }
        
        return json.dumps(response, indent=2, ensure_ascii=False)
        
    except Exception as e:
        error_msg = f"Error: Failed to get L7 rules - {str(e)}"
        logger.error(error_msg)
        return json.dumps({
            "timestamp": datetime.now().isoformat(),
            "error": error_msg,
            "success": False
        }, indent=2)
