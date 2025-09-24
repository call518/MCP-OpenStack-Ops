"""Tool implementation for get_instances_by_status."""

import json
from datetime import datetime
from ..functions import get_instances_by_status as _get_instances_by_status
from ..mcp_main import (
    logger,
    mcp,
)

@mcp.tool()
async def get_instances_by_status(status: str) -> str:
    """
    Get instances filtered by status.
    
    Args:
        status: Instance status to filter by (ACTIVE, SHUTOFF, ERROR, BUILDING, etc.)
        
    Returns:
        List of instances with the specified status
    """
    try:
        logger.info(f"Getting instances with status: {status}")
        
        instances = _get_instances_by_status(status.upper())
        
        result = {
            "timestamp": datetime.now().isoformat(),
            "status_filter": status.upper(),
            "instances_found": len(instances),
            "instances": instances
        }
        
        return json.dumps(result, indent=2, ensure_ascii=False)
        
    except Exception as e:
        error_msg = f"Error: Failed to get instances with status '{status}' - {str(e)}"
        logger.error(error_msg)
        return error_msg
