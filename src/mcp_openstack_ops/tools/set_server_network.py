"""Tool implementation for set_server_network."""

import json
from datetime import datetime
from ..functions import set_server_network as _set_server_network
from ..mcp_main import (
    conditional_tool,
    handle_operation_result,
    logger,
)

@conditional_tool
async def set_server_network(
    instance_name: str,
    action: str,
    network: str = "",
    port: str = "",
    fixed_ip: str = ""
) -> str:
    """
    Manage server network operations (add/remove networks and ports).
    
    Functions:
    - Add network to server with optional fixed IP
    - Remove network from server (removes all ports on that network)
    - Add specific port to server
    - Remove specific port from server
    
    Use when user requests:
    - "Add network X to server Y"
    - "Remove network X from server Y"
    - "Attach port X to server Y"
    - "Detach port X from server Y"
    
    Args:
        instance_name: Name or ID of the server
        action: Action to perform (add_network, remove_network, add_port, remove_port)
        network: Network name or ID (for network operations)
        port: Port ID (for port operations)
        fixed_ip: Optional fixed IP address when adding network
        
    Returns:
        JSON string containing operation results
    """
    try:
        logger.info(f"Managing server network: {instance_name}, action: {action}")
        
        kwargs = {
            'network': network,
            'port': port,
            'fixed_ip': fixed_ip
        }
        
        result = _set_server_network(instance_name.strip(), action.strip(), **kwargs)
        
        # Use centralized result handling
        return handle_operation_result(
            result,
            "Server Network Management", 
            {
                "Action": action,
                "Instance": instance_name,
                "Network": network or "Not specified",
                "Port": port or "Not specified"
            }
        )
        
    except Exception as e:
        error_msg = f"Error: Failed to manage server network - {str(e)}"
        logger.error(error_msg)
        return json.dumps({
            "timestamp": datetime.now().isoformat(),
            "error": error_msg,
            "success": False
        }, indent=2)
