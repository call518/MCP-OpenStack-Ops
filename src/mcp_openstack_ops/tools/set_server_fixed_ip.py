"""Tool implementation for set_server_fixed_ip."""

import json
from datetime import datetime
from ..functions import set_server_fixed_ip as _set_server_fixed_ip
from ..mcp_main import (
    conditional_tool,
    handle_operation_result,
    logger,
)

@conditional_tool
async def set_server_fixed_ip(
    instance_name: str,
    action: str,
    network: str = "",
    fixed_ip: str = ""
) -> str:
    """
    Manage server fixed IP operations (add/remove).
    
    Functions:
    - Add fixed IP to server on specified network
    - Remove specific fixed IP from server
    - Create new port with specified or auto-assigned fixed IP
    
    Use when user requests:
    - "Add fixed IP X to server Y on network Z"
    - "Remove fixed IP X from server Y"
    - "Assign fixed IP to server on network"
    
    Args:
        instance_name: Name or ID of the server
        action: Action to perform (add, remove)
        network: Network name or ID (required for add action)
        fixed_ip: Fixed IP address (optional for add, required for remove)
        
    Returns:
        JSON string containing operation results
    """
    try:
        logger.info(f"Managing server fixed IP: {instance_name}, action: {action}")
        
        kwargs = {
            'network': network,
            'fixed_ip': fixed_ip
        }
        
        result = _set_server_fixed_ip(instance_name.strip(), action.strip(), **kwargs)
        
        # Use centralized result handling
        return handle_operation_result(
            result,
            "Server Fixed IP Management",
            {
                "Action": action,
                "Instance": instance_name,
                "Network": network or "Not specified",
                "Fixed IP": fixed_ip or "Not specified"
            }
        )
        
    except Exception as e:
        error_msg = f"Error: Failed to manage server fixed IP - {str(e)}"
        logger.error(error_msg)
        return json.dumps({
            "timestamp": datetime.now().isoformat(),
            "error": error_msg,
            "success": False
        }, indent=2)
