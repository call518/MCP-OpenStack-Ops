"""Tool implementation for set_server_properties."""

import json
from datetime import datetime
from ..functions import set_server_properties as _set_server_properties
from ..mcp_main import (
    conditional_tool,
    handle_operation_result,
    logger,
)

@conditional_tool
async def set_server_properties(
    instance_name: str,
    action: str,
    name: str = "",
    description: str = "",
    metadata: dict = {},
    properties: list = []
) -> str:
    """
    Manage server properties and metadata (set/unset).
    
    Functions:
    - Set server name and description
    - Add/update server metadata properties
    - Remove server metadata properties
    - Manage server tags and labels
    
    Use when user requests:
    - "Set server X name to Y"
    - "Update server X description"
    - "Add metadata to server X"
    - "Remove property Y from server X"
    - "Set server property"
    
    Args:
        instance_name: Name or ID of the server
        action: Action to perform (set, unset)
        name: New server name
        description: Server description
        metadata: Dictionary of metadata properties to set
        properties: List of property names to unset
        
    Returns:
        JSON string containing operation results
    """
    try:
        logger.info(f"Managing server properties: {instance_name}, action: {action}")
        
        kwargs = {
            'name': name,
            'description': description,
            'metadata': metadata,
            'properties': properties
        }
        
        result = _set_server_properties(instance_name.strip(), action.strip(), **kwargs)
        
        # Use centralized result handling
        return handle_operation_result(
            result,
            "Server Properties Management",
            {
                "Action": action,
                "Instance": instance_name,
                "Name": name or "Not specified",
                "Description": description or "Not specified"
            }
        )
        
    except Exception as e:
        error_msg = f"Error: Failed to manage server properties - {str(e)}"
        logger.error(error_msg)
        return json.dumps({
            "timestamp": datetime.now().isoformat(),
            "error": error_msg,
            "success": False
        }, indent=2)
