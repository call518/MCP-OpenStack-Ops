"""Tool implementation for set_server_group."""

from typing import Optional
from ..functions import set_server_group as _set_server_group
from ..mcp_main import (
    conditional_tool,
    handle_operation_result,
    logger,
)

@conditional_tool
async def set_server_group(
    group_name: str,
    action: str,
    policies: Optional[str] = None,
    metadata: Optional[str] = None
) -> str:
    """
    Manage server groups (create, delete, show)
    
    Args:
        group_name: Name of the server group
        action: Action to perform (create, delete, show)
        policies: Comma-separated list of policies for create (e.g., "affinity" or "anti-affinity")
        metadata: JSON string of metadata for create
    
    Returns:
        JSON string with server group operation result
    """
    try:
        logger.info(f"Managing server group: {group_name}, action: {action}")
        
        group_params = {}
        
        if policies:
            group_params['policies'] = [p.strip() for p in policies.split(',')]
            
        if metadata:
            import json as json_module
            group_params['metadata'] = json_module.loads(metadata)
        
        group_result = _set_server_group(group_name=group_name, action=action, **group_params)
        
        # Use centralized result handling
        return handle_operation_result(
            group_result,
            "Server Group Management",
            {
                "Action": action,
                "Group Name": group_name,
                "Policies": policies or "Not specified"
            }
        )
        
    except Exception as e:
        error_msg = f"Error: Failed to manage server group - {str(e)}"
        logger.error(error_msg)
        return error_msg
