"""Tool implementation for set_load_balancer_listener."""

import json
from datetime import datetime
from typing import Optional
from ..functions import set_load_balancer_listener as _set_load_balancer_listener
from ..mcp_main import (
    _is_modify_operation_allowed,
    _read_action_error,
    conditional_tool,
    logger,
)

READ_ACTIONS = {
    'show': 'get_load_balancer_listeners', 'stats': 'get_load_balancer_status',
}


@conditional_tool
async def set_load_balancer_listener(
    action: str,
    listener_name_or_id: str = "",
    name: str = "",
    lb_name_or_id: str = "",
    protocol: str = "",
    protocol_port: int = 0,
    description: str = "",
    admin_state_up: Optional[bool] = None,
    connection_limit: int = 0,
    default_pool_id: str = "",
    default_tls_container_ref: str = "",
    sni_container_refs: str = ""
) -> str:
    """
    Comprehensive load balancer listener management (create, delete, set, unset).
    To list listeners, use get_load_balancer_listeners; for statistics, use
    get_load_balancer_status.
    
    Functions:
    - Create new listeners on load balancers with protocol configuration
    - Delete existing listeners
    - Set/update listener properties (name, description, connection limits)
    - Unset/clear listener settings (description, connection limits, default pool)
    
    Use when user requests:
    - "Create listener [name] on load balancer [lb_name] for HTTP on port 80"
    - "Add an HTTPS listener on port 443 to [lb_name] using certificate [secret]"
    - "Delete listener [name/id]"
    - "Update listener [name] connection limit to 1000"
    - "Clear listener [name] description"
    
    Args:
        action: Operation to perform (create, delete, set, unset)
        listener_name_or_id: Listener name or ID (required for delete/set/unset)
        name: Name for new listener (required for create)
        lb_name_or_id: Load balancer name or ID (required for create)
        protocol: Listener protocol - HTTP, HTTPS (non-terminated HTTPS, i.e. TLS
            passthrough), TERMINATED_HTTPS (TLS-terminated HTTPS: TLS ends on the
            load balancer), TCP, UDP, SCTP (required for create)
        protocol_port: Port number for listener (required for create)
        description: Description for listener. For unset, any non-empty value
            clears the description
        admin_state_up: Administrative state. create defaults to True; set
            changes it only when given
        connection_limit: Maximum number of connections. 0 leaves it out:
            create then uses Octavia's default (unlimited) and set keeps the
            current value. For unset, any value above 0 resets it to unlimited
        default_pool_id: Default pool ID for the listener. For unset, any
            non-empty value removes the default pool
        default_tls_container_ref: Default server certificate for TERMINATED_HTTPS
            (create/set). A Barbican secret holding a PKCS#12 bundle, or a
            certificate container, given as name, ID or href; names are resolved
            to hrefs. Required when protocol is TERMINATED_HTTPS. Octavia uses it
            when the client sends no SNI or no SNI certificate matches.
        sni_container_refs: Comma-separated SNI certificates (names, IDs or hrefs)
            that Octavia picks by requested host name (create/set). Optional.

    Returns:
        JSON string with operation results and listener details
    """
    read_error = _read_action_error(action, READ_ACTIONS)
    if read_error:
        return read_error
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
            'default_pool_id': default_pool_id if default_pool_id else None,
            'default_tls_container_ref': default_tls_container_ref or None,
            'sni_container_refs': [ref.strip() for ref in sni_container_refs.split(',')
                                   if ref.strip()] or None,
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
