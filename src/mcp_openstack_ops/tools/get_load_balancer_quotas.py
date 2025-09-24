"""Tool implementation for get_load_balancer_quotas."""

import json
from datetime import datetime
from ..functions import get_load_balancer_quotas as _get_load_balancer_quotas
from ..mcp_main import (
    logger,
    mcp,
)

@mcp.tool()
async def get_load_balancer_quotas(project_id: str = "") -> str:
    """
    Get load balancer quotas for a project or all projects.
    
    Args:
        project_id: Optional project ID. If empty, shows quotas for all projects.
    
    Returns:
        JSON string containing quota information
    """
    try:
        logger.info(f"Getting load balancer quotas for project: {project_id}")
        
        result = _get_load_balancer_quotas(project_id)
        
        response = {
            "timestamp": datetime.now().isoformat(),
            "result": result
        }
        
        return json.dumps(response, indent=2, ensure_ascii=False)
        
    except Exception as e:
        error_msg = f"Error: Failed to get quotas - {str(e)}"
        logger.error(error_msg)
        return json.dumps({
            "timestamp": datetime.now().isoformat(),
            "error": error_msg,
            "success": False
        }, indent=2)
