"""Tool implementation for set_metrics."""

import json
from ..functions import set_metrics as _set_metrics
from ..mcp_main import conditional_tool

@conditional_tool
async def set_metrics(
    action: str,
    resource_type: str = "compute",
    resource_id: str = ""
) -> str:
    """
    Manage OpenStack metrics collection and monitoring
    
    Args:
        action: Action to perform - list, show, summary
        resource_type: Type of resource (compute, network, storage, identity)
        resource_id: Specific resource ID to get metrics for
        
    Returns:
        JSON string with metrics management operation results
    """
    
    try:
        result = _set_metrics(
            action=action,
            resource_type=resource_type,
            resource_id=resource_id if resource_id else None
        )
        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({
            'success': False,
            'message': f'Failed to manage metrics: {str(e)}',
            'error': str(e)
        }, indent=2)
