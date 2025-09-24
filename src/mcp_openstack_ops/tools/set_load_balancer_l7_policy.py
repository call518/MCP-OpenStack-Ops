"""Tool implementation for set_load_balancer_l7_policy."""

import json
from datetime import datetime
from ..functions import set_load_balancer_l7_policy as _set_load_balancer_l7_policy
from ..mcp_main import (
    conditional_tool,
    logger,
)

@conditional_tool
async def set_load_balancer_l7_policy(
    action: str,
    listener_name_or_id: str = "",
    policy_name_or_id: str = "",
    name: str = "",
    action_type: str = "REJECT",
    description: str = "",
    position: int = 1,
    redirect_pool_id: str = "",
    redirect_url: str = "",
    admin_state_up: bool = True
) -> str:
    """
    Manage L7 policy operations (create, delete, set, unset, show).
    
    Args:
        action: Action to perform (create, delete, set, unset, show)
        listener_name_or_id: Listener name or ID (required for create)
        policy_name_or_id: Policy name or ID (required for delete/update operations)
        name: Policy name (for create)
        action_type: Policy action (REJECT, REDIRECT_TO_POOL, REDIRECT_TO_URL)
        description: Policy description
        position: Policy position in the list (1-based)
        redirect_pool_id: Pool ID for REDIRECT_TO_POOL action
        redirect_url: URL for REDIRECT_TO_URL action
        admin_state_up: Administrative state
    
    Returns:
        JSON string with operation results
    """
    try:
        logger.info(f"Managing L7 policy with action: {action}")
        
        kwargs = {
            'listener_name_or_id': listener_name_or_id,
            'policy_name_or_id': policy_name_or_id,
            'name': name,
            'action_type': action_type,
            'description': description,
            'position': position,
            'redirect_pool_id': redirect_pool_id if redirect_pool_id else None,
            'redirect_url': redirect_url if redirect_url else None,
            'admin_state_up': admin_state_up
        }
        
        result = _set_load_balancer_l7_policy(action, **kwargs)
        
        response = {
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "result": result
        }
        
        return json.dumps(response, indent=2, ensure_ascii=False)
        
    except Exception as e:
        error_msg = f"Error: Failed to manage L7 policy - {str(e)}"
        logger.error(error_msg)
        return json.dumps({
            "timestamp": datetime.now().isoformat(),
            "error": error_msg,
            "success": False
        }, indent=2)
