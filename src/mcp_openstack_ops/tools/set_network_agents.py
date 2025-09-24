"""Tool implementation for set_network_agents."""

import json
from ..functions import set_network_agents as _set_network_agents
from ..mcp_main import (
    _is_modify_operation_allowed,
    conditional_tool,
)

@conditional_tool
async def set_network_agents(
    action: str,
    agent_id: str = ""
) -> str:
    """
    Manage OpenStack network agents for network service monitoring and control
    
    Args:
        action: Action to perform - list, enable, disable
        agent_id: ID of the network agent (required for enable/disable)
        
    Returns:
        JSON string with network agent management operation results
    """
    
    if not _is_modify_operation_allowed() and action.lower() in ['enable', 'disable']:
        return json.dumps({
            'success': False,
            'message': f'Modify operations are not allowed in current environment for action: {action}',
            'error': f'MODIFY_OPERATIONS_DISABLED'
        })
    
    try:
        result = _set_network_agents(
            action=action,
            agent_id=agent_id if agent_id else None
        )
        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({
            'success': False,
            'message': f'Failed to manage network agent: {str(e)}',
            'error': str(e)
        }, indent=2)
