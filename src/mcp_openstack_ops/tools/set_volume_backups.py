"""Tool implementation for set_volume_backups."""

import json
from ..functions import set_volume_backups as _set_volume_backups
from ..mcp_main import (
    _is_modify_operation_allowed,
    _read_action_error,
    conditional_tool,
)

READ_ACTIONS = {'list': 'get_volume_backups', 'show': 'get_volume_backups'}


@conditional_tool
async def set_volume_backups(
    action: str,
    backup_name: str = "",
    volume_name: str = "",
    description: str = "",
    incremental: bool = False,
    force: bool = False,
    volume_id: str = ""
) -> str:
    """
    Create, delete or restore OpenStack volume backups. To list or show
    backups, use get_volume_backups.

    Args:
        action: Action to perform - create, delete, restore
        backup_name: Name or ID of the backup (required for delete/restore)
        volume_name: Optional name for a newly restored volume
        volume_id: Source volume ID for create, or target volume ID for restore
        description: Description for backup operations
        incremental: Create incremental backup (default: False)
        force: Force backup creation even if volume is attached
        
    Returns:
        JSON string with backup operation results
    """
    read_error = _read_action_error(action, READ_ACTIONS)
    if read_error:
        return read_error
    
    if not _is_modify_operation_allowed() and action.lower() in ['create', 'delete',
        'restore']:
        return json.dumps({
            'success': False,
            'message': f'Modify operations are not allowed in current environment for action: {action}',
            'error': f'MODIFY_OPERATIONS_DISABLED'
        })
    
    try:
        result = _set_volume_backups(
            action=action,
            backup_name=backup_name if backup_name else None,
            volume_name=volume_name,
            description=description,
            incremental=incremental,
            force=force,
            volume_id=volume_id or None
        )
        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({
            'success': False,
            'message': f'Failed to manage volume backup: {str(e)}',
            'error': str(e)
        }, indent=2)
