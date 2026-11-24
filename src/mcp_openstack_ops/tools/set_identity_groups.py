"""Tool implementation for set_identity_groups."""

import json
from ..functions import set_identity_groups as _set_identity_groups
from ..mcp_main import (
    _is_modify_operation_allowed,
    _read_action_error,
    conditional_tool,
)

READ_ACTIONS = {'list': 'get_identity_groups', 'show': 'get_identity_groups'}


@conditional_tool
async def set_identity_groups(
    action: str,
    group_name: str = "",
    description: str = "",
    domain_id: str = "default"
) -> str:
    """
    Create, delete or update OpenStack identity groups for user
    organization. To list or show groups, use get_identity_groups.

    Args:
        action: Action to perform - create, delete, update
        group_name: Name of the group (required for create)
        description: Description for the group
        domain_id: Domain ID for the group (default: 'default')
        
    Returns:
        JSON string with identity group management operation results
    """
    read_error = _read_action_error(action, READ_ACTIONS)
    if read_error:
        return read_error
    
    if not _is_modify_operation_allowed() and action.lower() in ['create', 'delete',
        'update']:
        return json.dumps({
            'success': False,
            'message': f'Modify operations are not allowed in current environment for action: {action}',
            'error': f'MODIFY_OPERATIONS_DISABLED'
        })
    
    try:
        result = _set_identity_groups(
            action=action,
            group_name=group_name if group_name else None,
            description=description,
            domain_id=domain_id
        )
        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({
            'success': False,
            'message': f'Failed to manage identity group: {str(e)}',
            'error': str(e)
        }, indent=2)
