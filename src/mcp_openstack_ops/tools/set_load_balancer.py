"""Tool implementation for set_load_balancer."""

import json
from datetime import datetime
from typing import Optional
from ..functions import set_load_balancer as _set_load_balancer
from ..mcp_main import (
    _is_modify_operation_allowed,
    _read_action_error,
    conditional_tool,
    logger,
)

READ_ACTIONS = {
    'stats': 'get_load_balancer_status', 'status': 'get_load_balancer_status',
}


@conditional_tool
async def set_load_balancer(
    action: str,
    lb_name_or_id: str = "",
    name: str = "",
    vip_subnet_id: str = "",
    description: str = "",
    admin_state_up: Optional[bool] = None,
    provider: str = "",
    flavor_id: str = "",
    availability_zone: str = "",
    cascade: bool = False,
    vip_qos_policy: str = ""
) -> str:
    """
    Comprehensive load balancer management operations (create, delete, set, unset, failover).
    For the status tree and statistics, use get_load_balancer_status.
    
    Functions:
    - Create new load balancers with VIP configuration, flavor/AZ options and
      an optional VIP QoS policy
    - Delete existing load balancers (with optional cascade delete)
    - Update/set load balancer properties (name, description, admin state,
      VIP QoS policy)
    - Clear/unset load balancer settings (description, VIP QoS policy)
    - Trigger load balancer failover operations
    
    Use when user requests:
    - "Create a load balancer named [name] on subnet [id]"
    - "Delete load balancer [name/id] with cascade"
    - "Update load balancer [name] description to [text]"
    - "Clear load balancer [name] description"
    - "Apply QoS policy [policy] to load balancer [name]'s VIP"
    - "Failover load balancer [name/id]"
    
    Args:
        action: Operation to perform (create, delete, set, unset, failover)
        lb_name_or_id: Load balancer name or ID (required for most operations)
        name: Name for new load balancer (required for create)
        vip_subnet_id: VIP subnet ID (required for create)
        description: Description for load balancer
        admin_state_up: Administrative state. create defaults to True; set
            changes it only when given
        provider: Load balancer provider (optional)
        flavor_id: Flavor ID for load balancer (optional)
        availability_zone: Availability zone (optional)
        cascade: Whether to cascade delete (for delete action)
        vip_qos_policy: Neutron QoS policy name or ID owned by or shared with
            the current project. create/set send it as Octavia's
            vip_qos_policy_id; with the amphora provider, Octavia applies it
            asynchronously to the amphora VRRP ports that carry VIP traffic. unset clears the VIP QoS
            policy only when this matches the policy currently attached and
            returns a warning: the amphora provider (observed in Octavia
            16.1.1) can keep the previous policy on the VRRP ports.
            Octavia does not check rule types; whether a rule takes effect
            depends on the Neutron ML2 driver. The VRRP ports belong to the
            project Octavia uses for its Neutron calls, not to the load
            balancer's project, so checking their qos_policy_id needs
            get_network_ports with all_projects=true.

    Returns:
        JSON string with operation results and load balancer details
    """
    read_error = _read_action_error(action, READ_ACTIONS)
    if read_error:
        return read_error
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
            'vip_qos_policy': vip_qos_policy if vip_qos_policy else None,
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
