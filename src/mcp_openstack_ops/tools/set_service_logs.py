"""Tool implementation for set_service_logs."""

import json
from ..functions import set_service_logs as _set_service_logs
from ..mcp_main import conditional_tool

@conditional_tool
async def set_service_logs(
    action: str,
    service_name: str = "",
    log_level: str = "INFO"
) -> str:
    """
    Manage OpenStack service logs and logging configuration
    
    Args:
        action: Action to perform - list, show
        service_name: Name of the service to get logs for
        log_level: Log level filter (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        
    Returns:
        JSON string with service logs management operation results
    """
    
    try:
        result = _set_service_logs(
            action=action,
            service_name=service_name if service_name else None,
            log_level=log_level
        )
        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({
            'success': False,
            'message': f'Failed to manage service logs: {str(e)}',
            'error': str(e)
        }, indent=2)
