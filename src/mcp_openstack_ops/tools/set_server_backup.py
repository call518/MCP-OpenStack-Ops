"""Tool implementation for set_server_backup."""

import json
from datetime import datetime
from ..functions import create_server_backup as _set_server_backup
from ..mcp_main import (
    conditional_tool,
    handle_operation_result,
    logger,
)

@conditional_tool
async def set_server_backup(
    instance_name: str,
    backup_name: str,
    backup_type: str = "daily",
    rotation: int = 1,
    metadata: dict = {}
) -> str:
    """
    Create a backup image of a server.
    
    Functions:
    - Create server backup with rotation policy
    - Set backup type (daily, weekly, etc.)
    - Add backup metadata and labels
    - Manage backup lifecycle
    
    Use when user requests:
    - "Create backup of server X"
    - "Backup server X as Y"
    - "Create daily backup of server"
    - "Backup server with rotation policy"
    
    Args:
        instance_name: Name or ID of the server
        backup_name: Name for the backup image
        backup_type: Type of backup (daily, weekly, monthly)
        rotation: Number of backups to keep
        metadata: Additional metadata for the backup
        
    Returns:
        JSON string containing backup operation results
    """
    try:
        logger.info(f"Creating server backup: {instance_name} -> {backup_name}")
        
        kwargs = {
            'backup_type': backup_type,
            'rotation': rotation,
            'metadata': metadata
        }
        
        result = _set_server_backup(instance_name.strip(), backup_name.strip(), **kwargs)
        
        # Use centralized result handling
        return handle_operation_result(
            result,
            "Server Backup Creation",
            {
                "Instance": instance_name,
                "Backup Name": backup_name,
                "Backup Type": backup_type or "Not specified",
                "Rotation": str(rotation) if rotation else "Not specified"
            }
        )
        
    except Exception as e:
        error_msg = f"Error: Failed to create server backup - {str(e)}"
        logger.error(error_msg)
        return json.dumps({
            "timestamp": datetime.now().isoformat(),
            "error": error_msg,
            "success": False
        }, indent=2)
