"""Tool implementation for set_volume_backups."""

import json
from ..functions import set_volume_backups as _set_volume_backups
from ..mcp_main import (
    _is_modify_operation_allowed,
    conditional_tool,
)

@conditional_tool
async def set_volume_backups(
    action: str,
    backup_name: str = "",
    volume_name: str = "",
    description: str = "",
    incremental: bool = False,
    force: bool = False
) -> str:
    """
    Manage OpenStack volume backups with comprehensive backup operations
    
    Args:
        action: Action to perform - list, show, delete, restore
        backup_name: Name or ID of the backup (required for show/delete/restore)
        volume_name: Name for restored volume (required for restore action)
        description: Description for backup operations
        incremental: Create incremental backup (default: False)
        force: Force backup creation even if volume is attached
        
    Returns:
        JSON string with backup operation results
    """
    
    if not _is_modify_operation_allowed() and action.lower() in ['delete', 'restore']:
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
            force=force
        )
        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({
            'success': False,
            'message': f'Failed to manage volume backup: {str(e)}',
            'error': str(e)
        }, indent=2)
