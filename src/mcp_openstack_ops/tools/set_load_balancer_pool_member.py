"""Tool implementation for set_load_balancer_pool_member."""

import json
from datetime import datetime
from ..mcp_main import (
    conditional_tool,
    logger,
)

@conditional_tool
async def set_load_balancer_pool_member(
    action: str,
    pool_name_or_id: str,
    member_id: str = "",
    name: str = "",
    address: str = "",
    protocol_port: int = 0,
    weight: int = 1,
    admin_state_up: bool = True,
    backup: bool = False,
    monitor_address: str = "",
    monitor_port: int = 0
) -> str:
    """
    Manage OpenStack load balancer pool member operations (create, delete, show, set).

    Functions:
    - Add new members to pools with IP address and port
    - Remove existing members from pools
    - Show detailed member information
    - Update member properties (weight, admin state, backup status)

    Use when user requests:
    - "Add member 192.168.1.10:80 to pool [name] with weight 5"
    - "Remove member [id] from pool [name]"
    - "Show member [id] details in pool [name]"
    - "Set member [id] as backup in pool [name]"

    Args:
        action: Operation to perform (create, delete, show, set)
        pool_name_or_id: Pool name or ID (required)
        member_id: Member ID (required for delete/show/set)
        name: Name for the member
        address: IP address of the member (required for create)
        protocol_port: Port number (required for create)
        weight: Member weight (1-256, default: 1)
        admin_state_up: Administrative state (default: True)
        backup: Backup member flag (default: False)
        monitor_address: Monitor IP address
        monitor_port: Monitor port
        
    Returns:
        JSON string with operation results and member details
    """
    try:
        from .functions import set_load_balancer_pool_member
        
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
