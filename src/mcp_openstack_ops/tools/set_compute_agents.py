"""Tool implementation for set_compute_agents."""

import json
from ..functions import set_compute_agents as _set_compute_agents
from ..mcp_main import conditional_tool

@conditional_tool
async def set_compute_agents(
    action: str,
    agent_id: str = "",
    host: str = ""
) -> str:
    """
    Manage OpenStack compute agents and hypervisor monitoring
    
    Args:
        action: Action to perform - list, show
        agent_id: ID of specific agent
        host: Host name to filter agents
        
    Returns:
        JSON string with compute agent management operation results
    """
    
    try:
        result = _set_compute_agents(
            action=action,
            agent_id=agent_id if agent_id else None,
            host=host if host else None
        )
        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({
            'success': False,
            'message': f'Failed to manage compute agents: {str(e)}',
            'error': str(e)
        }, indent=2)
