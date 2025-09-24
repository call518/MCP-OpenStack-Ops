"""Tool implementation for set_server_security_group."""

import json
from datetime import datetime
from ..functions import set_server_security_group as _set_server_security_group
from ..mcp_main import (
    conditional_tool,
    handle_operation_result,
    logger,
)

@conditional_tool
async def set_server_security_group(
    instance_name: str,
    action: str,
    security_group: str
) -> str:
    """
    Manage server security group operations (add/remove).
    
    Functions:
    - Add security group to server
    - Remove security group from server
    - Manage server firewall rules and access control
    
    Use when user requests:
    - "Add security group X to server Y"
    - "Remove security group X from server Y"
    - "Apply security group to server"
    - "Remove firewall rules from server"
    
    Args:
        instance_name: Name or ID of the server
        action: Action to perform (add, remove)
        security_group: Security group name or ID
        
    Returns:
        JSON string containing operation results
    """
    try:
        logger.info(f"Managing server security group: {instance_name}, action: {action}")
        
        kwargs = {
            'security_group': security_group
        }
        
        result = _set_server_security_group(instance_name.strip(), action.strip(), **kwargs)
        
        # Use centralized result handling
        return handle_operation_result(
            result,
            "Server Security Group Management",
            {
                "Action": action,
                "Instance": instance_name,
                "Security Group": security_group or "Not specified"
            }
        )
        
    except Exception as e:
        error_msg = f"Error: Failed to manage server security group - {str(e)}"
        logger.error(error_msg)
        return json.dumps({
            "timestamp": datetime.now().isoformat(),
            "error": error_msg,
            "success": False
        }, indent=2)
