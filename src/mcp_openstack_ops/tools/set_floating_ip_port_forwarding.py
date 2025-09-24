"""Tool implementation for set_floating_ip_port_forwarding."""

import json
from datetime import datetime
from ..functions import set_floating_ip_port_forwarding as _set_floating_ip_port_forwarding
from ..mcp_main import (
    conditional_tool,
    logger,
)

@conditional_tool
async def set_floating_ip_port_forwarding(
    action: str,
    floating_ip_id: str = "",
    floating_ip_address: str = "",
    port_forwarding_id: str = "",
    protocol: str = "tcp",
    external_port: int = 0,
    internal_port: int = 0,
    internal_ip_address: str = "",
    internal_port_id: str = "",
    description: str = ""
) -> str:
    """
    Manage floating IP port forwarding rules for NAT translation.
    
    Functions:
    - Create port forwarding rules to redirect external traffic to internal IPs
    - Delete existing port forwarding rules
    - List all port forwarding rules for a floating IP
    - Show detailed configuration of specific port forwarding rule
    - Update port forwarding settings (description, internal target)
    
    Use when user requests:
    - "Create port forwarding rule for floating IP [ip] from port [ext] to [int:internal]"
    - "Delete port forwarding rule [id] from floating IP [ip]"
    - "List port forwarding rules for floating IP [ip]"
    - "Show port forwarding rule [id] details"
    - "Update port forwarding rule [id] description to [text]"
    
    Args:
        action: Action to perform (create, delete, list, show, set)
        floating_ip_id: Floating IP ID (alternative to floating_ip_address)
        floating_ip_address: Floating IP address (alternative to floating_ip_id)
        port_forwarding_id: Port forwarding rule ID (for delete/show/set actions)
        protocol: Protocol for port forwarding (tcp, udp, icmp) - default: tcp
        external_port: External port number (for create action)
        internal_port: Internal port number (for create action)
        internal_ip_address: Internal IP address target (for create/set actions)
        internal_port_id: Internal port ID target (optional)
        description: Description for the port forwarding rule
        
    Returns:
        Result of port forwarding management operation in JSON format.
    """
    try:
        logger.info(f"Managing floating IP port forwarding with action '{action}'")
        
        kwargs = {
            'floating_ip_id': floating_ip_id.strip() if floating_ip_id.strip() else None,
            'floating_ip_address': floating_ip_address.strip() if floating_ip_address.strip() else None,
            'port_forwarding_id': port_forwarding_id.strip() if port_forwarding_id.strip() else None,
            'protocol': protocol.lower() if protocol.strip() else 'tcp',
            'description': description.strip() if description.strip() else None
        }
        
        if external_port > 0:
            kwargs['external_port'] = external_port
        if internal_port > 0:
            kwargs['internal_port'] = internal_port
        if internal_ip_address.strip():
            kwargs['internal_ip_address'] = internal_ip_address.strip()
        if internal_port_id.strip():
            kwargs['internal_port_id'] = internal_port_id.strip()
        
        result_data = _set_floating_ip_port_forwarding(action, **kwargs)
        
        result = {
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "parameters": kwargs,
            "result": result_data
        }
        
        return json.dumps(result, indent=2)
        
    except Exception as e:
        error_msg = f"Error: Failed to manage floating IP port forwarding - {str(e)}"
        logger.error(error_msg)
        return error_msg
