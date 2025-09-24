"""Tool implementation for get_server_volumes."""

import json
from datetime import datetime
from ..functions import get_server_volumes as _get_server_volumes
from ..mcp_main import (
    logger,
    mcp,
)

@mcp.tool()
async def get_server_volumes(
    instance_name: str
) -> str:
    """
    Get all volumes attached to a specific server
    
    Args:
        instance_name: Name or ID of the server instance
    
    Returns:
        JSON string with server volumes information
    """
    try:
        logger.info(f"Getting volumes for server: {instance_name}")
        
        volumes_result = _get_server_volumes(instance_name=instance_name)
        
        response = {
            "timestamp": datetime.now().isoformat(),
            "operation": "get_server_volumes",
            "parameters": {
                "instance_name": instance_name
            },
            "result": volumes_result
        }
        
        return json.dumps(response, indent=2, ensure_ascii=False)
        
    except Exception as e:
        error_msg = f"Error: Failed to get server volumes - {str(e)}"
        logger.error(error_msg)
        return error_msg
