"""Tool implementation for set_load_balancer_health_monitor."""

import json
from datetime import datetime
from ..functions import set_load_balancer_health_monitor as _set_load_balancer_health_monitor
from ..mcp_main import (
    _is_modify_operation_allowed,
    conditional_tool,
    logger,
)

@conditional_tool
async def set_load_balancer_health_monitor(
    action: str,
    monitor_name_or_id: str = "",
    name: str = "",
    pool_name_or_id: str = "",
    monitor_type: str = "HTTP",
    delay: int = 10,
    timeout: int = 5,
    max_retries: int = 3,
    max_retries_down: int = 3,
    admin_state_up: bool = True,
    http_method: str = "GET",
    url_path: str = "/",
    expected_codes: str = "200"
) -> str:
    """
    Comprehensive health monitor management operations (create, delete, set, unset, show).

    Functions:
    - Create new health monitors for pools with various protocols (HTTP, HTTPS, TCP, UDP, PING)
    - Delete existing health monitors
    - Set/update monitor settings (timing, HTTP parameters, admin state)
    - Unset/clear monitor settings (HTTP parameters, expected codes)
    - Show detailed health monitor configuration and status

    Use when user requests:
    - "Create HTTP health monitor for pool [name] checking /health every 30 seconds"
    - "Delete health monitor [name/id]"
    - "Update health monitor [name] timeout to 10 seconds"
    - "Clear health monitor [name] expected codes"
    - "Show health monitor [name/id] details"

    Args:
        action: Operation to perform (create, delete, set, unset, show)
        monitor_name_or_id: Monitor name or ID (required for delete/set/unset/show)
        name: Name for the monitor
        pool_name_or_id: Pool name or ID (required for create)
        monitor_type: Monitor type (HTTP, HTTPS, TCP, PING, UDP-CONNECT, SCTP)
        delay: Delay between health checks in seconds (default: 10)
        timeout: Timeout for health check in seconds (default: 5)
        max_retries: Maximum retries before marking unhealthy (default: 3)
        max_retries_down: Maximum retries before marking down (default: 3)
        admin_state_up: Administrative state (default: True)
        http_method: HTTP method for HTTP/HTTPS monitors (default: GET)
        url_path: URL path for HTTP/HTTPS monitors (default: /)
        expected_codes: Expected HTTP status codes (default: 200)
        
    Returns:
        JSON string with operation results and health monitor details
    """
    if not _is_modify_operation_allowed() and action.lower() in ['create', 'delete', 'set', 'unset']:
        return json.dumps({
            'success': False,
            'message': f'Modify operations are not allowed in current environment for action: {action}',
            'error': f'MODIFY_OPERATIONS_DISABLED'
        })
    
    try:
        logger.info(f"Managing health monitor with action: {action}")
        
        result = _set_load_balancer_health_monitor(
            action=action,
            monitor_name_or_id=monitor_name_or_id,
            name=name,
            pool_name_or_id=pool_name_or_id,
            monitor_type=monitor_type,
            delay=delay,
            timeout=timeout,
            max_retries=max_retries,
            max_retries_down=max_retries_down,
            admin_state_up=admin_state_up,
            http_method=http_method,
            url_path=url_path,
            expected_codes=expected_codes
        )
        
        response = {
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "result": result
        }
        
        return json.dumps(response, indent=2, ensure_ascii=False)
        
    except Exception as e:
        error_msg = f"Error: Failed to manage health monitor - {str(e)}"
        logger.error(error_msg)
        return json.dumps({
            "timestamp": datetime.now().isoformat(),
            "error": error_msg,
            "success": False
        }, indent=2)
