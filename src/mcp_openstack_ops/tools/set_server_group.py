"""Tool implementation for set_server_group."""

from typing import Optional
from ..functions import set_server_group as _set_server_group
from ..mcp_main import (
    _read_action_error,
    conditional_tool,
    handle_operation_result,
    logger,
)

READ_ACTIONS = {'list': 'get_server_groups', 'show': 'get_server_groups'}


@conditional_tool
async def set_server_group(
    group_name: str,
    action: str,
    policies: Optional[str] = None,
    metadata: Optional[str] = None
) -> str:
    """
    Create or delete server groups. To list or show server groups with
    their members, use get_server_groups.

    Args:
        group_name: Name of the server group
        action: Action to perform (create, delete)
        policies: Comma-separated list of policies for create (e.g., "affinity" or "anti-affinity")
        metadata: JSON string of metadata for create
    
    Returns:
        JSON string with server group operation result
    """
    read_error = _read_action_error(action, READ_ACTIONS)
    if read_error:
        return read_error
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
