"""Tool implementation for set_volume_groups."""

import json
from ..functions import set_volume_groups as _set_volume_groups
from ..mcp_main import (
    _is_modify_operation_allowed,
    _read_action_error,
    conditional_tool,
)

READ_ACTIONS = {'list': 'get_volume_groups', 'show': 'get_volume_groups'}


@conditional_tool
async def set_volume_groups(
    action: str,
    group_name: str = "",
    description: str = "",
    group_type: str = "default",
    availability_zone: str = "",
    delete_volumes: bool = False,
    volume_types: str = ""
) -> str:
    """
    Create or delete OpenStack volume groups for consistent group operations.
    To list or show groups, use get_volume_groups.

    Args:
        action: Action to perform - create, delete
        group_name: Name or ID of the volume group
        description: Description for the volume group
        group_type: Type of volume group (default: 'default')
        availability_zone: Availability zone for the group
        delete_volumes: Delete volumes when deleting group (default: False)
        volume_types: Comma-delimited volume type names/IDs, required for create

    Requires Cinder generic groups, a group type and API microversion >= 3.13.
        
    Returns:
        JSON string with volume group operation results
    """
    read_error = _read_action_error(action, READ_ACTIONS)
    if read_error:
        return read_error
    
    if not _is_modify_operation_allowed() and action.lower() in ['create', 'delete']:
        return json.dumps({
            'success': False,
            'message': f'Modify operations are not allowed in current environment for action: {action}',
            'error': f'MODIFY_OPERATIONS_DISABLED'
        })
    
    try:
        result = _set_volume_groups(
            action=action,
            group_name=group_name if group_name else None,
            description=description,
            group_type=group_type,
            availability_zone=availability_zone if availability_zone else None,
            delete_volumes=delete_volumes,
            volume_types=[v.strip() for v in volume_types.split(",") if v.strip()]
        )
        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({
            'success': False,
            'message': f'Failed to manage volume group: {str(e)}',
            'error': str(e)
        }, indent=2)
