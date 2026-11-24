"""Tool implementation for set_roles."""

import json
from ..functions import set_roles as _set_roles
from ..mcp_main import (
    _is_modify_operation_allowed,
    _read_action_error,
    conditional_tool,
)

READ_ACTIONS = {'list': 'get_roles'}


@conditional_tool
async def set_roles(
    action: str,
    role_name: str = "",
    description: str = "",
    domain_id: str = ""
) -> str:
    """
    Create OpenStack roles for access control and permissions. To list
    roles, use get_roles.

    Args:
        action: Action to perform - create
        role_name: Name of the role (required for create)
        description: Description for the role
        domain_id: Domain ID for domain-scoped roles (optional)
        
    Returns:
        JSON string with role management operation results
    """
    read_error = _read_action_error(action, READ_ACTIONS)
    if read_error:
        return read_error
    
    if not _is_modify_operation_allowed() and action.lower() in ['create']:
        return json.dumps({
            'success': False,
            'message': f'Modify operations are not allowed in current environment for action: {action}',
            'error': f'MODIFY_OPERATIONS_DISABLED'
        })
    
    try:
        result = _set_roles(
            action=action,
            role_name=role_name if role_name else None,
            description=description,
            domain_id=domain_id if domain_id else None
        )
        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({
            'success': False,
            'message': f'Failed to manage role: {str(e)}',
            'error': str(e)
        }, indent=2)
