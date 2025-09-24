"""Tool implementation for set_load_balancer."""

import json
from datetime import datetime
from ..functions import set_load_balancer as _set_load_balancer
from ..mcp_main import (
    _is_modify_operation_allowed,
    conditional_tool,
    logger,
)

@conditional_tool
async def set_load_balancer(
    action: str,
    lb_name_or_id: str = "",
    name: str = "",
    vip_subnet_id: str = "",
    description: str = "",
    admin_state_up: bool = True,
    provider: str = "",
    flavor_id: str = "",
    availability_zone: str = "",
    cascade: bool = False
) -> str:
    """
    Comprehensive load balancer management operations (create, delete, set, unset, failover, stats, status).
    
    Functions:
    - Create new load balancers with VIP configuration and flavor/AZ options
    - Delete existing load balancers (with optional cascade delete)
    - Update/set load balancer properties (name, description, admin state)
    - Clear/unset load balancer settings (description)
    - Trigger load balancer failover operations
    - Get load balancer statistics (bytes in/out, connections)
    - Get load balancer status tree (detailed operational status)
    
    Use when user requests:
    - "Create a load balancer named [name] on subnet [id]"
    - "Delete load balancer [name/id] with cascade"
    - "Update load balancer [name] description to [text]"
    - "Clear load balancer [name] description"
    - "Failover load balancer [name/id]"
    - "Show load balancer [name] statistics"
    - "Get load balancer [name] status tree"
    
    Args:
        action: Operation to perform (create, delete, set, unset, failover, stats, status)
        lb_name_or_id: Load balancer name or ID (required for most operations)
        name: Name for new load balancer (required for create)
        vip_subnet_id: VIP subnet ID (required for create)
        description: Description for load balancer
        admin_state_up: Administrative state (default: True)
        provider: Load balancer provider (optional)
        flavor_id: Flavor ID for load balancer (optional)
        availability_zone: Availability zone (optional)
        cascade: Whether to cascade delete (for delete action)
        
    Returns:
        JSON string with operation results and load balancer details
    """
    if not _is_modify_operation_allowed() and action.lower() in ['create', 'delete', 'set', 'unset', 'failover']:
        return json.dumps({
            'success': False,
            'message': f'Modify operations are not allowed in current environment for action: {action}',
            'error': f'MODIFY_OPERATIONS_DISABLED'
        })
    
    try:
        logger.info(f"Managing load balancer with action: {action}")
        
        kwargs = {
            'lb_name_or_id': lb_name_or_id if lb_name_or_id else None,
            'name': name if name else None,
            'vip_subnet_id': vip_subnet_id if vip_subnet_id else None,
            'description': description if description else None,
            'admin_state_up': admin_state_up,
            'provider': provider if provider else None,
            'flavor_id': flavor_id if flavor_id else None,
            'availability_zone': availability_zone if availability_zone else None,
            'cascade': cascade
        }
        
        # Remove None values
        kwargs = {k: v for k, v in kwargs.items() if v is not None}
        
        result = _set_load_balancer(action=action, **kwargs)
        
        response = {
            "timestamp": datetime.now().isoformat(),
            "result": result
        }
        
        return json.dumps(response, indent=2, ensure_ascii=False)
        
    except Exception as e:
        error_msg = f"Error: Failed to manage load balancer - {str(e)}"
        logger.error(error_msg)
        return json.dumps({
            "timestamp": datetime.now().isoformat(),
            "error": error_msg,
            "success": False
        }, indent=2)
