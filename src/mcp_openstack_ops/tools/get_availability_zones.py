"""Tool implementation for get_availability_zones."""

import json
from datetime import datetime
from ..functions import get_availability_zones as _get_availability_zones
from ..mcp_main import (
    logger,
    mcp,
)

@mcp.tool()
async def get_availability_zones() -> str:
    """
    List availability zones and their status
    
    Returns:
        JSON string with availability zones information
    """
    try:
        logger.info("Getting availability zones")
        
        zones_result = _get_availability_zones()
        
        response = {
            "timestamp": datetime.now().isoformat(),
            "operation": "get_availability_zones",
            "result": zones_result
        }
        
        return json.dumps(response, indent=2, ensure_ascii=False)
        
    except Exception as e:
        error_msg = f"Error: Failed to get availability zones - {str(e)}"
        logger.error(error_msg)
        return error_msg
