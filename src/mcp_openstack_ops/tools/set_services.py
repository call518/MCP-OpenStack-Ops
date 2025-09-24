"""Tool implementation for set_services."""

import json
from ..functions import set_services as _set_services
from ..mcp_main import conditional_tool

@conditional_tool
async def set_services(
    action: str,
    service_name: str = ""
) -> str:
    """
    Manage OpenStack services for service catalog and endpoint management
    
    Args:
        action: Action to perform - list
        service_name: Name or ID of the service
        
    Returns:
        JSON string with service management operation results
    """
    
    try:
        result = _set_services(
            action=action,
            service_name=service_name if service_name else None
        )
        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({
            'success': False,
            'message': f'Failed to manage service: {str(e)}',
            'error': str(e)
        }, indent=2)
