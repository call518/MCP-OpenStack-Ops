"""Tool implementation for set_volume_groups."""

import json
from ..functions import set_volume_groups as _set_volume_groups
from ..mcp_main import (
    _is_modify_operation_allowed,
    conditional_tool,
)

@conditional_tool
async def set_volume_groups(
    action: str,
    group_name: str = "",
    description: str = "",
    group_type: str = "default",
    availability_zone: str = "",
    delete_volumes: bool = False
) -> str:
    """
    Manage OpenStack volume groups for consistent group operations
    
    Args:
        action: Action to perform - list, create, delete, show
        group_name: Name or ID of the volume group
        description: Description for the volume group
        group_type: Type of volume group (default: 'default')
        availability_zone: Availability zone for the group
        delete_volumes: Delete volumes when deleting group (default: False)
        
    Returns:
        JSON string with volume group operation results
    """
    
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
            delete_volumes=delete_volumes
        )
        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({
            'success': False,
            'message': f'Failed to manage volume group: {str(e)}',
            'error': str(e)
        }, indent=2)
