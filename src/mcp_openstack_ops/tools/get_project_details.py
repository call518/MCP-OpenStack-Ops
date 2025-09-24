"""Tool implementation for get_project_details."""

import json
from datetime import datetime
from ..functions import get_project_details as _get_project_details
from ..mcp_main import (
    logger,
    mcp,
)

@mcp.tool()
async def get_project_details(project_name: str = "") -> str:
    """
    Get OpenStack project details (similar to 'openstack project list/show').
    
    Args:
        project_name: Name of specific project to show details for (optional, lists all if empty)
    
    Returns:
        JSON string containing project information including details, roles, and quotas
    """
    try:
        if not project_name.strip():
            logger.info("Getting list of all projects")
        else:
            logger.info(f"Getting project details for: {project_name}")
            
        project_info = _get_project_details(project_name=project_name)
        
        response = {
            "timestamp": datetime.now().isoformat(),
            "operation": "get_project_details",
            "parameters": {
                "project_name": project_name or "all projects"
            },
            "project_data": project_info
        }
        
        return json.dumps(response, indent=2, ensure_ascii=False)
        
    except Exception as e:
        error_msg = f"Error: Failed to get project details - {str(e)}"
        logger.error(error_msg)
        return error_msg
