"""Tool implementation for set_network_qos_policies."""

import json
from ..functions import set_network_qos_policies as _set_network_qos_policies
from ..mcp_main import (
    _is_modify_operation_allowed,
    conditional_tool,
)

@conditional_tool
async def set_network_qos_policies(
    action: str,
    policy_name: str = "",
    description: str = "",
    shared: bool = False
) -> str:
    """
    Manage OpenStack network QoS policies for bandwidth and traffic control
    
    Args:
        action: Action to perform - list, create, delete
        policy_name: Name or ID of the QoS policy
        description: Description for the QoS policy
        shared: Make policy available to other projects (default: False)
        
    Returns:
        JSON string with network QoS policy management operation results
    """
    
    if not _is_modify_operation_allowed() and action.lower() in ['create', 'delete']:
        return json.dumps({
            'success': False,
            'message': f'Modify operations are not allowed in current environment for action: {action}',
            'error': f'MODIFY_OPERATIONS_DISABLED'
        })
    
    try:
        result = _set_network_qos_policies(
            action=action,
            policy_name=policy_name if policy_name else None,
            description=description,
            shared=shared
        )
        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({
            'success': False,
            'message': f'Failed to manage network QoS policy: {str(e)}',
            'error': str(e)
        }, indent=2)
