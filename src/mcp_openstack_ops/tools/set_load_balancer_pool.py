"""Tool implementation for set_load_balancer_pool."""

import json
from datetime import datetime
from ..mcp_main import (
    conditional_tool,
    logger,
)

@conditional_tool
async def set_load_balancer_pool(
    action: str,
    pool_name_or_id: str = "",
    name: str = "",
    listener_name_or_id: str = "",
    protocol: str = "",
    lb_algorithm: str = "ROUND_ROBIN",
    description: str = "",
    admin_state_up: bool = True
) -> str:
    """
    Manage OpenStack load balancer pool operations (create, delete, show, set).

    Functions:
    - Create new pools for listeners with specified protocols
    - Delete existing pools
    - Show detailed pool information including members
    - Update pool properties (name, description, algorithm, admin state)

    Use when user requests:
    - "Create pool [name] for listener [listener] using HTTP"
    - "Delete pool [name/id]"
    - "Show pool [name/id] details"
    - "Update pool [name] algorithm to LEAST_CONNECTIONS"

    Args:
        action: Operation to perform (create, delete, show, set)
        pool_name_or_id: Pool name or ID (required for delete/show/set)
        name: Name for new pool (required for create)
        listener_name_or_id: Listener name or ID (required for create)
        protocol: Pool protocol - HTTP, HTTPS, TCP, UDP (required for create)
        lb_algorithm: Load balancing algorithm (ROUND_ROBIN, LEAST_CONNECTIONS, SOURCE_IP)
        description: Description for the pool
        admin_state_up: Administrative state (default: True)
        
    Returns:
        JSON string with operation results and pool details
    """
    try:
        from .functions import set_load_balancer_pool
        
        result = set_load_balancer_pool(
            action=action,
            pool_name_or_id=pool_name_or_id,
            name=name,
            listener_name_or_id=listener_name_or_id,
            protocol=protocol,
            lb_algorithm=lb_algorithm,
            description=description,
            admin_state_up=admin_state_up
        )
        
        response = {
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "result": result
        }
        
        return json.dumps(response, indent=2, ensure_ascii=False)
        
    except Exception as e:
        error_msg = f"Error: Failed to manage load balancer pool - {str(e)}"
        logger.error(error_msg)
        return json.dumps({
            "timestamp": datetime.now().isoformat(),
            "error": error_msg,
            "success": False
        }, indent=2)
