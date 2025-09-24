"""Tool implementation for set_project."""

from ..functions import set_project as _set_project
from ..mcp_main import (
    conditional_tool,
    handle_operation_result,
    logger,
)

@conditional_tool
async def set_project(
    project_name: str, 
    action: str, 
    description: str = "",
    enable: bool = None,
    disable: bool = None,
    domain: str = "",
    parent: str = "",
    tags: str = ""
) -> str:
    """
    Manage OpenStack projects (create, delete, set, cleanup).
    
    Args:
        project_name: Name of the project (required)
        action: Action to perform (create, delete, set, cleanup)
        description: Project description (optional, for create/set)
        enable: Enable project (optional, for set action)
        disable: Disable project (optional, for set action)
        domain: Domain name or ID (optional, for create)
        parent: Parent project name or ID (optional, for create)
        tags: Comma-separated list of tags (optional, for create/set)
    
    Returns:
        JSON string containing the result of the project management operation
    """
    try:
        logger.info(f"Managing project - Action: {action}, Project: {project_name}")
        
        # Build project parameters
        project_params = {}
        if description:
            project_params['description'] = description
        if enable is not None:
            project_params['enable'] = enable
        if disable is not None:
            project_params['disable'] = disable
        if domain:
            project_params['domain'] = domain
        if parent:
            project_params['parent'] = parent
        if tags:
            project_params['tags'] = [tag.strip() for tag in tags.split(',')]
        
        project_result = _set_project(project_name=project_name, action=action, **project_params)
        
        # Use centralized result handling
        return handle_operation_result(
            project_result,
            "Project Management",
            {
                "Action": action,
                "Project Name": project_name,
                "Description": description or "Not specified",
                "Domain": domain or "Default"
            }
        )
        
    except Exception as e:
        error_msg = f"Error: Failed to manage project - {str(e)}"
        logger.error(error_msg)
        return error_msg
