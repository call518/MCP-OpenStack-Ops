"""Tool implementation for set_alarms."""

import json
from ..functions import set_alarms as _set_alarms
from ..mcp_main import (
    _is_modify_operation_allowed,
    conditional_tool,
)

@conditional_tool
async def set_alarms(
    action: str,
    alarm_name: str = "",
    resource_id: str = "",
    threshold: float = 0.0,
    comparison: str = "gt"
) -> str:
    """
    Manage OpenStack alarms and alerting (requires Aodh service)
    
    Args:
        action: Action to perform - list, create, show, delete
        alarm_name: Name of the alarm
        resource_id: Resource ID to monitor
        threshold: Threshold value for alarm
        comparison: Comparison operator (gt, lt, eq, ne, ge, le)
        
    Returns:
        JSON string with alarm management operation results
    """
    
    if not _is_modify_operation_allowed() and action.lower() in ['create', 'delete']:
        return json.dumps({
            'success': False,
            'message': f'Modify operations are not allowed in current environment for action: {action}',
            'error': f'MODIFY_OPERATIONS_DISABLED'
        })
    
    try:
        result = _set_alarms(
            action=action,
            alarm_name=alarm_name if alarm_name else None,
            resource_id=resource_id if resource_id else None,
            threshold=threshold if threshold > 0.0 else None,
            comparison=comparison
        )
        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({
            'success': False,
            'message': f'Failed to manage alarms: {str(e)}',
            'error': str(e)
        }, indent=2)
