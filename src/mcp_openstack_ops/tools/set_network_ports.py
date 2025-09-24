"""Tool implementation for set_network_ports."""

import json
from ..functions import set_network_ports as _set_network_ports
from ..mcp_main import (
    _is_modify_operation_allowed,
    conditional_tool,
)

@conditional_tool
async def set_network_ports(
    action: str,
    port_name: str = "",
    network_id: str = "",
    description: str = "",
    admin_state_up: bool = True,
    security_groups: str = "[]"
) -> str:
    """
    Manage OpenStack network ports for VM and network connectivity
    
    Args:
        action: Action to perform - list, create, delete
        port_name: Name or ID of the port
        network_id: Network ID for port creation (required for create)
        description: Description for the port
        admin_state_up: Administrative state (default: True)
        security_groups: JSON array of security group IDs (e.g., '["sg1", "sg2"]')
        
    Returns:
        JSON string with port management operation results
    """
    
    if not _is_modify_operation_allowed() and action.lower() in ['create', 'delete']:
        return json.dumps({
            'success': False,
            'message': f'Modify operations are not allowed in current environment for action: {action}',
            'error': f'MODIFY_OPERATIONS_DISABLED'
        })
    
    try:
        # Parse security groups from JSON string
        import json as json_lib
        parsed_security_groups = json_lib.loads(security_groups) if security_groups != "[]" else []
        
        result = _set_network_ports(
            action=action,
            port_name=port_name if port_name else None,
            network_id=network_id if network_id else None,
            description=description,
            admin_state_up=admin_state_up,
            security_groups=parsed_security_groups
        )
        return json.dumps(result, indent=2)
    except json_lib.JSONDecodeError as e:
        return json.dumps({
            'success': False,
            'message': f'Invalid JSON in security_groups parameter: {str(e)}',
            'error': str(e)
        }, indent=2)
    except Exception as e:
        return json.dumps({
            'success': False,
            'message': f'Failed to manage network port: {str(e)}',
            'error': str(e)
        }, indent=2)
