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
    threshold: float | None = None,
    comparison: str = "gt",
    metric: str = "cpu_util",
    resource_type: str = "instance",
    aggregation_method: str = "mean",
    granularity: int = 300,
    evaluation_periods: int = 1,
    alarm_actions: list[str] | None = None
) -> str:
    """
    Manage real project-scoped Aodh Gnocchi resource threshold alarms
    
    Args:
        action: Action to perform - list, create, show, delete
        alarm_name: Name of the alarm
        resource_id: Resource ID to monitor
        threshold: Required for create; zero and negative thresholds are valid
        comparison: Comparison operator (gt, lt, eq, ne, ge, le)
        metric: Existing Gnocchi metric name (default cpu_util; cloud must collect it)
        resource_type: Gnocchi resource type (default instance)
        aggregation_method: Aggregation supported by the metric archive policy
        granularity: Evaluation window in seconds (default 300)
        evaluation_periods: Number of windows (default 1)
        alarm_actions: Notification URLs; empty means no notification actions

    Requires an alarming endpoint in the Keystone catalog, Aodh, and Gnocchi.
    Missing services or denied API calls return failure; no simulation is used.
        
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
            threshold=threshold,
            comparison=comparison, metric=metric, resource_type=resource_type,
            aggregation_method=aggregation_method, granularity=granularity,
            evaluation_periods=evaluation_periods, alarm_actions=alarm_actions,
        )
        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({
            'success': False,
            'message': f'Failed to manage alarms: {str(e)}',
            'error': str(e)
        }, indent=2)
