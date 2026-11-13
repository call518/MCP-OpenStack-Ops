"""Tool implementation for get_project_details."""

import json
from datetime import datetime
from ..functions import get_project_details as _get_project_details
from ..mcp_main import (
    logger,
    mcp,
)

@mcp.tool()
async def get_project_details(project_name: str = "", all_projects: bool = False) -> str:
    """
    Get OpenStack project details (similar to 'openstack project list/show').
    
    Args:
        project_name: Name of specific project to show details for (optional).
            Without all_projects only the current project is available.
        all_projects: If True, return a summary (id, name, domain, enabled) of
            every project the credential's Keystone policy allows (like
            'openstack project list'). With a project_name or ID that matches
            exactly one project, return that project's details and resource
            counts instead, even for another project; a name shared by several
            projects returns their summaries, so retry with the ID. Requires
            ALLOW_CROSS_PROJECT_READ=true on the server; a disabled or denied
            request is reported as a failure.
    
    Returns:
        JSON string containing project information including details, roles, and quotas
    """
    try:
        if not project_name.strip():
            logger.info("Getting list of all projects")
        else:
            logger.info(f"Getting project details for: {project_name}")
            
        project_info = _get_project_details(project_name=project_name,
                                            all_projects=all_projects)
        
        response = {
            "timestamp": datetime.now().isoformat(),
            "operation": "get_project_details",
            "parameters": {
                "project_name": project_name or "all projects",
                "all_projects": all_projects
            },
            "project_data": project_info
        }
        
        return json.dumps(response, indent=2, ensure_ascii=False)
        
    except Exception as e:
        error_msg = f"Error: Failed to get project details - {str(e)}"
        logger.error(error_msg)
        return error_msg
