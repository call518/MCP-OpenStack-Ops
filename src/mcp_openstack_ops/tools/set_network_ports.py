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
    security_groups: str = "[]",
    all_projects: bool = False
) -> str:
    """
    Manage OpenStack network ports for VM and network connectivity
    
    Args:
        action: Action to perform - list, show, create, delete
        port_name: Name or ID of the port
        network_id: Network ID for port creation (required for create)
        description: Description for the port
        admin_state_up: Administrative state (default: True)
        security_groups: JSON array of security group IDs (e.g., '["sg1", "sg2"]');
            if omitted or empty, Neutron applies the project's default group
        all_projects: list only. list and show return only ports owned by
            the current project. If True, list every port Neutron shows the
            credential in any project, such as Octavia amphora VRRP ports,
            which belong to the project Octavia uses for its Neutron calls,
            not to the load balancer's project. Requires
            ALLOW_CROSS_PROJECT_READ=true on the server; rows then carry
            project_name, and the result has a scope (check scope.warning).
        
    Returns:
        JSON string with port management operation results. list and show
        include project_id, qos_policy_id (the policy attached to the port) and
        qos_network_policy_id (the policy inherited from its network); a
        null value means no policy.
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
        # An explicit empty list creates a port without any security group.
        optional = ({'security_groups': parsed_security_groups}
                    if parsed_security_groups else {})

        result = _set_network_ports(
            action=action,
            port_name=port_name if port_name else None,
            network_id=network_id if network_id else None,
            description=description,
            admin_state_up=admin_state_up,
            all_projects=all_projects,
            **optional
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
