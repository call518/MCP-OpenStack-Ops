"""Tool implementation for get_quota."""

import json
from datetime import datetime
from ..functions import get_quota as _get_quota
from ..mcp_main import (
    logger,
    mcp,
)

@mcp.tool()
async def get_quota(project_name: str = "") -> str:
    """
    Get quota information for projects (similar to 'openstack quota show').

    Each service reports limits, usage and usage_percent (percent of each
    limit in use). A usage value is null when it could not be determined, and
    usage_percent is null for unlimited (-1), zero or missing limits and for
    unknown usage.

    Args:
        project_name: Name of the project (optional, defaults to current project if empty)
    
    Returns:
        JSON string containing quota information for the specified project or current project
    """
    try:
        if not project_name.strip():
            logger.info("Getting quota for current project (no project name specified)")
        else:
            logger.info(f"Getting quota for project: {project_name}")
            
        quota_info = _get_quota(project_name=project_name)
        
        response = {
            "timestamp": datetime.now().isoformat(),
            "operation": "get_quota",
            "parameters": {
                "project_name": project_name or "current project"
            },
            "quota_data": quota_info
        }
        
        return json.dumps(response, indent=2, ensure_ascii=False)
        
    except Exception as e:
        error_msg = f"Error: Failed to get quota information - {str(e)}"
        logger.error(error_msg)
        return error_msg
