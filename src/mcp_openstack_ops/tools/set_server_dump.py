"""Tool implementation for set_server_dump."""

import json
from datetime import datetime
from ..functions import create_server_dump as _set_server_dump
from ..mcp_main import (
    conditional_tool,
    handle_operation_result,
    logger,
)

@conditional_tool
async def set_server_dump(instance_name: str) -> str:
    """
    Create a dump file for a server (vendor-specific feature).
    
    Functions:
    - Attempt to create server memory/disk dump
    - Provide alternative backup suggestions
    - Explain dump limitations
    
    Use when user requests:
    - "Create dump of server X"
    - "Generate server dump file"
    - "Create server core dump"
    
    Args:
        instance_name: Name or ID of the server
        
    Returns:
        JSON string containing dump operation results or alternatives
    """
    try:
        logger.info(f"Attempting to create server dump: {instance_name}")
        
        result = _set_server_dump(instance_name.strip())
        
        # Use centralized result handling
        return handle_operation_result(
            result,
            "Server Dump Creation",
            {
                "Instance": instance_name
            }
        )
        
    except Exception as e:
        error_msg = f"Error: Failed to create server dump - {str(e)}"
        logger.error(error_msg)
        return json.dumps({
            "timestamp": datetime.now().isoformat(),
            "error": error_msg,
            "success": False
        }, indent=2)
