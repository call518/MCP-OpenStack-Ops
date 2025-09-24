"""Tool implementation for get_load_balancer_amphorae."""

import json
from datetime import datetime
from ..functions import get_load_balancer_amphorae as _get_load_balancer_amphorae
from ..mcp_main import (
    logger,
    mcp,
)

@mcp.tool()
async def get_load_balancer_amphorae(lb_name_or_id: str = "") -> str:
    """
    Get amphora instances for a load balancer or all amphorae.
    
    Args:
        lb_name_or_id: Optional load balancer name or ID. If empty, shows all amphorae.
    
    Returns:
        JSON string containing amphora information including compute instances and network details
    """
    try:
        logger.info(f"Getting amphorae for load balancer: {lb_name_or_id}")
        
        result = _get_load_balancer_amphorae(lb_name_or_id)
        
        response = {
            "timestamp": datetime.now().isoformat(),
            "result": result
        }
        
        return json.dumps(response, indent=2, ensure_ascii=False)
        
    except Exception as e:
        error_msg = f"Error: Failed to get amphorae - {str(e)}"
        logger.error(error_msg)
        return json.dumps({
            "timestamp": datetime.now().isoformat(),
            "error": error_msg,
            "success": False
        }, indent=2)
