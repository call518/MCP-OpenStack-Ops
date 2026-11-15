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
    Not implemented: always returns an unsupported result and creates no dump.

    `openstack server dump create` maps to Nova's trigger-crash-dump action
    (API microversion 2.17), which injects an NMI into the guest; this server
    does not implement it. Report the unsupported result instead of claiming a
    dump was created; snapshots or backups are the available alternatives.

    Args:
        instance_name: Name or ID of the server

    Returns:
        JSON string with the unsupported result
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
