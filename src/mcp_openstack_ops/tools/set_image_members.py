"""Tool implementation for set_image_members."""

import json
from ..functions import set_image_members as _set_image_members
from ..mcp_main import (
    _is_modify_operation_allowed,
    _read_action_error,
    conditional_tool,
)

READ_ACTIONS = {'list': 'get_image_members'}


@conditional_tool
async def set_image_members(
    action: str,
    image_name: str,
    member_project: str = ""
) -> str:
    """
    Add or remove OpenStack image members for sharing images between
    projects. To list members, use get_image_members.

    Args:
        action: Action to perform - add, remove
        image_name: Name or ID of the image
        member_project: Project ID to add/remove as member (required for add/remove)
        
    Returns:
        JSON string with image member management operation results
    """
    read_error = _read_action_error(action, READ_ACTIONS)
    if read_error:
        return read_error
    
    if not _is_modify_operation_allowed() and action.lower() in ['add', 'remove']:
        return json.dumps({
            'success': False,
            'message': f'Modify operations are not allowed in current environment for action: {action}',
            'error': f'MODIFY_OPERATIONS_DISABLED'
        })
    
    try:
        result = _set_image_members(
            action=action,
            image_name=image_name,
            member_project=member_project if member_project else None
        )
        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({
            'success': False,
            'message': f'Failed to manage image members: {str(e)}',
            'error': str(e)
        }, indent=2)
