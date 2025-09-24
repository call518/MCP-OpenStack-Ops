"""Tool implementation for get_load_balancer_health_monitors."""

import json
from datetime import datetime
from ..mcp_main import (
    logger,
    mcp,
)

@mcp.tool()
async def get_load_balancer_health_monitors(pool_name_or_id: str = "") -> str:
    """
    Get health monitors, optionally filtered by pool.

    Functions:
    - Lists all health monitors or monitors for a specific pool
    - Shows monitor types (HTTP, HTTPS, TCP, PING, UDP-CONNECT)
    - Displays health check intervals, timeouts, and retry settings
    - Provides HTTP-specific settings (method, URL path, expected codes)

    Use when user requests:
    - "Show all health monitors"
    - "List health monitors for pool [name/id]"
    - "What health checks are configured?"
    - "Show health monitor configuration"

    Args:
        pool_name_or_id: Optional pool name or ID to filter monitors (empty for all)
        
    Returns:
        JSON string containing health monitor details
    """
    try:
        from .functions import get_load_balancer_health_monitors
        
        result = get_load_balancer_health_monitors(pool_name_or_id)
        
        response = {
            "timestamp": datetime.now().isoformat(),
            "filter": pool_name_or_id if pool_name_or_id else "all monitors",
            "result": result
        }
        
        return json.dumps(response, indent=2, ensure_ascii=False)
        
    except Exception as e:
        error_msg = f"Error: Failed to get health monitors - {str(e)}"
        logger.error(error_msg)
        return json.dumps({
            "timestamp": datetime.now().isoformat(),
            "error": error_msg,
            "success": False
        }, indent=2)
