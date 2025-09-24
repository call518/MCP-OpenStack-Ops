"""Tool implementation for set_server_migration."""

import json
from datetime import datetime
from ..functions import set_server_migration as _set_server_migration
from ..mcp_main import (
    conditional_tool,
    handle_operation_result,
    logger,
)

@conditional_tool
async def set_server_migration(
    instance_name: str,
    action: str,
    host: str = "",
    migration_id: str = "",
    block_migration: str = "auto",
    admin_pass: str = "",
    on_shared_storage: bool = False
) -> str:
    """
    Manage server migration and evacuation operations.
    
    Functions:
    - Live migrate server to different host
    - Evacuate server from failed host
    - Confirm/revert migration operations
    - List server migrations
    - Show migration details
    - Abort ongoing migrations
    - Force complete migrations
    
    Use when user requests:
    - "Migrate server X to host Y"
    - "Evacuate server X"
    - "List migrations for server X"
    - "Abort migration Y for server X"
    - "Confirm migration for server X"
    
    Args:
        instance_name: Name or ID of the server
        action: Action to perform (migrate, evacuate, confirm, revert, list, show, abort, force_complete)
        host: Target host for migration/evacuation
        migration_id: Migration ID for show/abort/force_complete actions
        block_migration: Block migration mode (auto, true, false)
        admin_pass: Admin password for evacuation
        on_shared_storage: Whether using shared storage for evacuation
        
    Returns:
        JSON string containing operation results
    """
    try:
        logger.info(f"Managing server migration: {instance_name}, action: {action}")
        
        kwargs = {
            'host': host,
            'migration_id': migration_id,
            'block_migration': block_migration,
            'admin_pass': admin_pass,
            'on_shared_storage': on_shared_storage
        }
        
        result = _set_server_migration(instance_name.strip(), action.strip(), **kwargs)
        
        # Use centralized result handling
        return handle_operation_result(
            result,
            "Server Migration Management",
            {
                "Action": action,
                "Instance": instance_name,
                "Host": host or "Not specified",
                "Migration ID": migration_id or "Not specified"
            }
        )
        
    except Exception as e:
        error_msg = f"Error: Failed to manage server migration - {str(e)}"
        logger.error(error_msg)
        return json.dumps({
            "timestamp": datetime.now().isoformat(),
            "error": error_msg,
            "success": False
        }, indent=2)
