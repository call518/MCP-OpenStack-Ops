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
    limit: int = 50,
    include_event_details: bool = False,
) -> str:
    """
    Get recent events for a server by name or UUID.

    Pass either value using instance_name, for example
    get_server_events(instance_name="<server UUID>"). There is no server_id
    parameter; do not use server_id or instance_id as argument names.
    
    Args:
        instance_name: Name or ID of the server instance
        limit: Maximum number of events to return (default: 50)
        include_event_details: Fetch per-action event details to report
            completion times and results. This makes one additional Nova API
            request per returned action and caps the effective limit at 10.
    
    Returns:
        JSON string with server events information
    """
    try:
        logger.info(f"Getting events for server: {instance_name}")
        
        events_result = _get_server_events(
            instance_name=instance_name,
            limit=limit,
            include_event_details=include_event_details,
        )
        
        response = {
            "timestamp": datetime.now().isoformat(),
            "operation": "get_server_events",
            "parameters": {
                "instance_name": instance_name,
                "limit": limit,
                "include_event_details": include_event_details,
            },
            "result": events_result
        }
        
        return json.dumps(response, indent=2, ensure_ascii=False)
        
    except Exception as e:
        error_msg = f"Error: Failed to get server events - {str(e)}"
        logger.error(error_msg)
        return error_msg
