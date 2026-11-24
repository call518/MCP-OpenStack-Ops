"""Tool implementation for set_subnets."""

import json
from ..functions import set_subnets as _set_subnets
from ..mcp_main import (
    _is_modify_operation_allowed,
    _read_action_error,
    conditional_tool,
)

READ_ACTIONS = {'list': 'get_subnets', 'show': 'get_subnets'}


@conditional_tool
async def set_subnets(
    action: str,
    subnet_name: str = "",
    network_id: str = "",
    cidr: str = "",
    description: str = "",
    ip_version: int = 4,
    enable_dhcp: bool = True,
    gateway_ip: str = "",
    dns_nameservers: str = "[]"
) -> str:
    """
    Create or delete OpenStack network subnets. To list or show subnets, use
    get_subnets.

    Args:
        action: Action to perform - create, delete
        subnet_name: Name or ID of the subnet
        network_id: Network ID for subnet creation (required for create)
        cidr: CIDR notation for subnet (required for create, e.g., '192.168.1.0/24')
        description: Description for the subnet
        ip_version: IP version 4 or 6 (default: 4)
        enable_dhcp: Enable DHCP for the subnet (default: True)
        gateway_ip: Gateway IP address (if omitted, Neutron assigns the first
            address of the CIDR)
        dns_nameservers: JSON array of DNS server IPs (e.g., '["8.8.8.8", "1.1.1.1"]')
        
    Returns:
        JSON string with subnet management operation results
    """
    read_error = _read_action_error(action, READ_ACTIONS)
    if read_error:
        return read_error

    if not _is_modify_operation_allowed() and action.lower() in ['create', 'delete']:
        return json.dumps({
            'success': False,
            'message': f'Modify operations are not allowed in current environment for action: {action}',
            'error': f'MODIFY_OPERATIONS_DISABLED'
        })
    
    try:
        # Parse DNS nameservers from JSON string
        import json as json_lib
        parsed_dns_nameservers = json_lib.loads(dns_nameservers) if dns_nameservers != "[]" else []
        # An explicit null gateway_ip creates a subnet without a gateway.
        optional = {'gateway_ip': gateway_ip} if gateway_ip else {}

        result = _set_subnets(
            action=action,
            subnet_name=subnet_name if subnet_name else None,
            network_id=network_id if network_id else None,
            cidr=cidr if cidr else None,
            description=description,
            ip_version=ip_version,
            enable_dhcp=enable_dhcp,
            dns_nameservers=parsed_dns_nameservers,
            **optional
        )
        return json.dumps(result, indent=2)
    except json_lib.JSONDecodeError as e:
        return json.dumps({
            'success': False,
            'message': f'Invalid JSON in dns_nameservers parameter: {str(e)}',
            'error': str(e)
        }, indent=2)
    except Exception as e:
        return json.dumps({
            'success': False,
            'message': f'Failed to manage subnet: {str(e)}',
            'error': str(e)
        }, indent=2)
