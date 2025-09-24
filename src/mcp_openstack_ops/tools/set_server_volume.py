"""Tool implementation for set_server_volume."""

from typing import Optional
from ..functions import set_server_volume as _set_server_volume
from ..mcp_main import (
    conditional_tool,
    handle_operation_result,
    logger,
)

@conditional_tool
async def set_server_volume(
    instance_name: str,
    action: str,
    volume_id: Optional[str] = None,
    volume_name: Optional[str] = None,
    device: Optional[str] = None,
    attachment_id: Optional[str] = None
) -> str:
    """
    Manage server volume attachments (attach, detach, list)
    
    Args:
        instance_name: Name or ID of the server instance
        action: Action to perform (attach, detach, list)
        volume_id: Volume ID for attach/detach operations
        volume_name: Volume name for attach/detach operations (alternative to volume_id)
        device: Device path for attach operation (optional, e.g., /dev/vdb)
        attachment_id: Attachment ID for detach operation (alternative to volume_id/name)
    
    Returns:
        JSON string with server volume operation result
    """
    try:
        logger.info(f"Managing server volume: {instance_name}, action: {action}")
        
        volume_params = {}
        
        if volume_id:
            volume_params['volume_id'] = volume_id
        if volume_name:
            volume_params['volume_name'] = volume_name
        if device:
            volume_params['device'] = device
        if attachment_id:
            volume_params['attachment_id'] = attachment_id
        
        volume_result = _set_server_volume(
            instance_name=instance_name, 
            action=action, 
            **volume_params
        )
        
        # Use centralized result handling
        return handle_operation_result(
            volume_result,
            "Server Volume Management",
            {
                "Action": action,
                "Instance Name": instance_name,
                "Volume Name": volume_name or "Not specified",
                "Device": device or "Not specified"
            }
        )
        
    except Exception as e:
        error_msg = f"Error: Failed to manage server volume - {str(e)}"
        logger.error(error_msg)
        return error_msg
