"""Tool implementation for get_server_groups."""

import json
from datetime import datetime
from ..functions import get_server_groups as _get_server_groups
from ..mcp_main import (
    logger,
    mcp,
)

@mcp.tool()
async def get_server_groups() -> str:
    """
    List all server groups with their details
    
    Returns:
        JSON string with server groups information
    """
    try:
        logger.info("Getting server groups list")
        
        groups_result = _get_server_groups()
        
        response = {
            "timestamp": datetime.now().isoformat(),
            "operation": "get_server_groups",
            "result": {
                "server_groups_count": len(groups_result),
                "server_groups": groups_result
            }
        }
        
        return json.dumps(response, indent=2, ensure_ascii=False)
        
    except Exception as e:
        error_msg = f"Error: Failed to get server groups - {str(e)}"
        logger.error(error_msg)
        return error_msg
