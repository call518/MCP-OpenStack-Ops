"""Tool implementation for set_load_balancer_quota."""

import json
from datetime import datetime
from ..functions import set_load_balancer_quota as _set_load_balancer_quota
from ..mcp_main import (
    conditional_tool,
    logger,
)

@conditional_tool
async def set_load_balancer_quota(
    action: str,
    project_id: str = "",
    load_balancer: int = -1,
    listener: int = -1,
    pool: int = -1,
    health_monitor: int = -1,
    member: int = -1
) -> str:
    """
    Manage quota operations (set, reset, unset).
    
    Args:
        action: Action to perform (set, reset, unset)
        project_id: Project ID (required)
        load_balancer: Load balancer quota limit
        listener: Listener quota limit
        pool: Pool quota limit
        health_monitor: Health monitor quota limit
        member: Member quota limit
    
    Returns:
        JSON string with operation results
    """
    try:
        logger.info(f"Managing quota with action: {action}")
        
        kwargs = {
            'project_id': project_id,
            'load_balancer': load_balancer if load_balancer >= 0 else None,
            'listener': listener if listener >= 0 else None,
            'pool': pool if pool >= 0 else None,
            'health_monitor': health_monitor if health_monitor >= 0 else None,
            'member': member if member >= 0 else None
        }
        
        # Remove None values
        kwargs = {k: v for k, v in kwargs.items() if v is not None}
        
        result = _set_load_balancer_quota(action, **kwargs)
        
        response = {
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "result": result
        }
        
        return json.dumps(response, indent=2, ensure_ascii=False)
        
    except Exception as e:
        error_msg = f"Error: Failed to manage quota - {str(e)}"
        logger.error(error_msg)
        return json.dumps({
            "timestamp": datetime.now().isoformat(),
            "error": error_msg,
            "success": False
        }, indent=2)
