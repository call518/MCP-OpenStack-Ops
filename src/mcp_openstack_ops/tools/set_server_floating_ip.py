"""Tool implementation for set_server_floating_ip."""

import json
from datetime import datetime
from ..functions import set_server_floating_ip as _set_server_floating_ip
from ..mcp_main import (
    conditional_tool,
    handle_operation_result,
    logger,
)

@conditional_tool
async def set_server_floating_ip(
    instance_name: str,
    action: str,
    floating_ip: str,
    fixed_ip: str = ""
) -> str:
    """
    Manage server floating IP operations (add/remove).
    
    Functions:
    - Associate floating IP to server
    - Disassociate floating IP from server
    - Automatically find target fixed IP if not specified
    
    Use when user requests:
    - "Add floating IP X to server Y"
    - "Remove floating IP X from server Y"
    - "Associate floating IP X with server Y"
    - "Disassociate floating IP X from server Y"
    
    Args:
        instance_name: Name or ID of the server
        action: Action to perform (add, remove)
        floating_ip: Floating IP address or ID
        fixed_ip: Target fixed IP address (auto-detected if not specified)
        
    Returns:
        JSON string containing operation results
    """
    try:
        logger.info(f"Managing server floating IP: {instance_name}, action: {action}")
        
        kwargs = {
            'floating_ip': floating_ip,
            'fixed_ip': fixed_ip
        }
        
        result = _set_server_floating_ip(instance_name.strip(), action.strip(), **kwargs)
        
        # Use centralized result handling
        return handle_operation_result(
            result,
            "Server Floating IP Management",
            {
                "Action": action,
                "Instance": instance_name,
                "Floating IP": floating_ip or "Not specified",
                "Fixed IP": fixed_ip or "Not specified"
            }
        )
        
    except Exception as e:
        error_msg = f"Error: Failed to manage server floating IP - {str(e)}"
        logger.error(error_msg)
        return json.dumps({
            "timestamp": datetime.now().isoformat(),
            "error": error_msg,
            "success": False
        }, indent=2)
