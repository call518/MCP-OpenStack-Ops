"""Tool implementation for get_server_events."""

import json
from datetime import datetime
from ..functions import get_server_events as _get_server_events
from ..mcp_main import (
    logger,
    mcp,
)

@mcp.tool()
async def get_server_events(
    instance_name: str,
    limit: int = 50
) -> str:
    """
    Get recent events for a specific server
    
    Args:
        instance_name: Name or ID of the server instance
        limit: Maximum number of events to return (default: 50)
    
    Returns:
        JSON string with server events information
    """
    try:
        logger.info(f"Getting events for server: {instance_name}")
        
        events_result = _get_server_events(instance_name=instance_name, limit=limit)
        
        response = {
            "timestamp": datetime.now().isoformat(),
            "operation": "get_server_events",
            "parameters": {
                "instance_name": instance_name,
                "limit": limit
            },
            "result": events_result
        }
        
        return json.dumps(response, indent=2, ensure_ascii=False)
        
    except Exception as e:
        error_msg = f"Error: Failed to get server events - {str(e)}"
        logger.error(error_msg)
        return error_msg
