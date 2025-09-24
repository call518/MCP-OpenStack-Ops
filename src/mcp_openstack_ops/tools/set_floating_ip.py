"""Tool implementation for set_floating_ip."""

from ..functions import set_floating_ip as _set_floating_ip
from ..mcp_main import (
    conditional_tool,
    handle_operation_result,
    logger,
)

@conditional_tool
async def set_floating_ip(action: str, floating_network_id: str = "", port_id: str = "", floating_ip_id: str = "", 
                         floating_ip_address: str = "", description: str = "") -> str:
    """
    Manage floating IPs (create, delete, associate, disassociate, set, show, unset, list).
    
    Functions:
    - Create new floating IPs from external networks (allocate)
    - Delete existing floating IPs (release)
    - Associate floating IPs with instance ports
    - Disassociate floating IPs from instances
    - Set floating IP properties (description, fixed IP)
    - Show detailed floating IP information
    - Unset floating IP properties (clear description)
    - List all floating IPs
    
    Use when user requests floating IP management, external connectivity setup, or IP allocation tasks.
    
    Args:
        action: Action to perform (create/allocate, delete/release, associate, disassociate, set, show, unset, list)
        floating_network_id: ID of external network for create action
        port_id: Port ID for association operations
        floating_ip_id: Floating IP ID for operations
        floating_ip_address: Floating IP address (alternative to floating_ip_id)
        description: Description for the floating IP (for set action)
        
    Returns:
        Result of floating IP management operation in JSON format.
    """
    try:
        logger.info(f"Managing floating IP with action '{action}'")
        
        # Map CLI-style actions to internal actions
        action_map = {
            'create': 'allocate',
            'delete': 'release',
            'allocate': 'allocate',
            'release': 'release'
        }
        internal_action = action_map.get(action.lower(), action.lower())
        
        kwargs = {}
        if floating_network_id.strip():
            kwargs['floating_network_id'] = floating_network_id.strip()
        if port_id.strip():
            kwargs['port_id'] = port_id.strip()
        if floating_ip_id.strip():
            kwargs['floating_ip_id'] = floating_ip_id.strip()
        if floating_ip_address.strip():
            kwargs['floating_ip_address'] = floating_ip_address.strip()
        if description.strip():
            kwargs['description'] = description.strip()
            
        result_data = _set_floating_ip(internal_action, **kwargs)
        
        # Use centralized result handling
        return handle_operation_result(
            result_data,
            "Floating IP Management",
            {
                "Action": action,
                "Network ID": floating_network_id or "Not specified",
                "Port ID": port_id or "Not specified",
                "IP Address": floating_ip_address or "Not specified"
            }
        )
        
    except Exception as e:
        error_msg = f"Error: Failed to manage floating IP - {str(e)}"
        logger.error(error_msg)
        return error_msg
