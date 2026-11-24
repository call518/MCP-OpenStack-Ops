"""Tool implementation for set_load_balancer_pool_member."""

import json
from datetime import datetime
from typing import Optional
from ..mcp_main import (
    _read_action_error,
    conditional_tool,
    logger,
)

READ_ACTIONS = {'show': 'get_load_balancer_pool_members'}


@conditional_tool
async def set_load_balancer_pool_member(
    action: str,
    pool_name_or_id: str,
    member_id: str = "",
    name: str = "",
    address: str = "",
    protocol_port: int = 0,
    weight: Optional[int] = None,
    admin_state_up: Optional[bool] = None,
    backup: Optional[bool] = None,
    monitor_address: str = "",
    monitor_port: int = 0
) -> str:
    """
    Manage OpenStack load balancer pool member operations (create, delete, set).
    To list members, use get_load_balancer_pool_members.

    Functions:
    - Add new members to pools with IP address and port
    - Remove existing members from pools
    - Update member properties (weight, admin state, backup status)

    Use when user requests:
    - "Add member 192.168.1.10:80 to pool [name] with weight 5"
    - "Remove member [id] from pool [name]"
    - "Set member [id] as backup in pool [name]"

    Args:
        action: Operation to perform (create, delete, set)
        pool_name_or_id: Pool name or ID (required)
        member_id: Member ID (required for delete/set)
        name: Name for the member
        address: IP address of the member (required for create)
        protocol_port: Port number (required for create)
        weight: Member weight (0-256; 0 stops new traffic). create defaults
            to 1
        admin_state_up: Administrative state. create defaults to True
        backup: Backup member flag. create defaults to False
        set changes weight, admin_state_up and backup only when given.
        monitor_address: Monitor IP address
        monitor_port: Monitor port
        
    Returns:
        JSON string with operation results and member details
    """
    read_error = _read_action_error(action, READ_ACTIONS)
    if read_error:
        return read_error
    try:
        from ..functions import set_load_balancer_pool_member
        
        result = set_load_balancer_pool_member(
            action=action,
            pool_name_or_id=pool_name_or_id,
            member_id=member_id,
            name=name,
            address=address,
            protocol_port=protocol_port,
            weight=weight,
            admin_state_up=admin_state_up,
            backup=backup,
            monitor_address=monitor_address,
            monitor_port=monitor_port
        )
        
        response = {
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "pool": pool_name_or_id,
            "result": result
        }
        
        return json.dumps(response, indent=2, ensure_ascii=False)
        
    except Exception as e:
        error_msg = f"Error: Failed to manage pool member - {str(e)}"
        logger.error(error_msg)
        return json.dumps({
            "timestamp": datetime.now().isoformat(),
            "error": error_msg,
            "success": False
        }, indent=2)
