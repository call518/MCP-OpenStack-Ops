"""Tool implementation for set_load_balancer_listener."""

import json
from datetime import datetime
from ..functions import set_load_balancer_listener as _set_load_balancer_listener
from ..mcp_main import (
    _is_modify_operation_allowed,
    conditional_tool,
    logger,
)

@conditional_tool
async def set_load_balancer_listener(
    action: str,
    listener_name_or_id: str = "",
    name: str = "",
    lb_name_or_id: str = "",
    protocol: str = "",
    protocol_port: int = 0,
    description: str = "",
    admin_state_up: bool = True,
    connection_limit: int = 0,
    default_pool_id: str = ""
) -> str:
    """
    Comprehensive load balancer listener management (create, delete, set, unset, show, stats).
    
    Functions:
    - Create new listeners on load balancers with protocol configuration
    - Delete existing listeners
    - Set/update listener properties (name, description, connection limits)
    - Unset/clear listener settings (description, connection limits, default pool)
    - Show detailed listener information
    - Get listener statistics (traffic and connection metrics)
    
    Use when user requests:
    - "Create listener [name] on load balancer [lb_name] for HTTP on port 80"
    - "Delete listener [name/id]"
    - "Update listener [name] connection limit to 1000"
    - "Clear listener [name] description"
    - "Show listener [name/id] details"
    - "Get listener [name] statistics"
    
    Args:
        action: Operation to perform (create, delete, set, unset, show, stats)
        listener_name_or_id: Listener name or ID (required for delete/set/unset/show/stats)
        name: Name for new listener (required for create)
        lb_name_or_id: Load balancer name or ID (required for create)
        protocol: Listener protocol - HTTP, HTTPS, TCP, UDP (required for create)
        protocol_port: Port number for listener (required for create)
        description: Description for listener
        admin_state_up: Administrative state (default: True)
        connection_limit: Maximum number of connections (0 = unlimited)
        default_pool_id: Default pool ID for the listener
        
    Returns:
        JSON string with operation results and listener details
    """
    if not _is_modify_operation_allowed() and action.lower() in ['create', 'delete', 'set', 'unset']:
        return json.dumps({
            'success': False,
            'message': f'Modify operations are not allowed in current environment for action: {action}',
            'error': f'MODIFY_OPERATIONS_DISABLED'
        })
    
    try:
        logger.info(f"Managing load balancer listener with action: {action}")
        
        kwargs = {
            'listener_name_or_id': listener_name_or_id if listener_name_or_id else None,
            'name': name if name else None,
            'lb_name_or_id': lb_name_or_id if lb_name_or_id else None,
            'protocol': protocol.upper() if protocol else None,
            'protocol_port': protocol_port if protocol_port > 0 else None,
            'description': description if description else None,
            'admin_state_up': admin_state_up,
            'connection_limit': connection_limit if connection_limit > 0 else None,
            'default_pool_id': default_pool_id if default_pool_id else None
        }
        
        # Remove None values
        kwargs = {k: v for k, v in kwargs.items() if v is not None}
        
        result = _set_load_balancer_listener(action=action, **kwargs)
        
        response = {
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "result": result
        }
        
        return json.dumps(response, indent=2, ensure_ascii=False)
        
    except Exception as e:
        error_msg = f"Error: Failed to manage load balancer listener - {str(e)}"
        logger.error(error_msg)
        return json.dumps({
            "timestamp": datetime.now().isoformat(),
            "error": error_msg,
            "success": False
        }, indent=2)
