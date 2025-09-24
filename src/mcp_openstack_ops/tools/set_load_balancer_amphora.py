"""Tool implementation for set_load_balancer_amphora."""

import json
from datetime import datetime
from ..functions import set_load_balancer_amphora as _set_load_balancer_amphora
from ..mcp_main import (
    _is_modify_operation_allowed,
    conditional_tool,
    logger,
)

@conditional_tool
async def set_load_balancer_amphora(
    action: str,
    amphora_id: str = ""
) -> str:
    """
    Manage amphora operations (configure, failover, show).
    
    NOTE: 'delete' and 'stats' operations are NOT supported by OpenStack SDK.
    Only configure, failover, and show operations are available.
    
    Args:
        action: Action to perform (configure, failover, show)
        amphora_id: Amphora ID (required)
    
    Returns:
        JSON string with operation results
    """
    if not _is_modify_operation_allowed() and action.lower() in ['configure', 'failover']:
        return json.dumps({
            'success': False,
            'message': f'Modify operations are not allowed in current environment for action: {action}',
            'error': f'MODIFY_OPERATIONS_DISABLED'
        })
    
    try:
        logger.info(f"Managing amphora with action: {action}")
        
        if action in ['delete', 'stats']:
            return json.dumps({
                'success': False,
                'message': f'Action "{action}" is not supported by OpenStack SDK. Available actions: configure, failover, show',
                'error': 'UNSUPPORTED_OPERATION'
            })
        
        result = _set_load_balancer_amphora(action, amphora_id=amphora_id)
        
        response = {
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "result": result
        }
        
        return json.dumps(response, indent=2, ensure_ascii=False)
        
    except Exception as e:
        error_msg = f"Error: Failed to manage amphora - {str(e)}"
        logger.error(error_msg)
        return json.dumps({
            "timestamp": datetime.now().isoformat(),
            "error": error_msg,
            "success": False
        }, indent=2)
