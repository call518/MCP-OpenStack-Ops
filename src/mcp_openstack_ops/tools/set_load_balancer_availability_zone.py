"""Tool implementation for set_load_balancer_availability_zone."""

import json
from datetime import datetime
from ..functions import set_load_balancer_availability_zone as _set_load_balancer_availability_zone
from ..mcp_main import (
    conditional_tool,
    logger,
)

@conditional_tool
async def set_load_balancer_availability_zone(
    action: str,
    az_name: str = "",
    name: str = "",
    availability_zone_profile_id: str = "",
    description: str = "",
    enabled: bool = True
) -> str:
    """
    Manage availability zone operations (create, delete, set, unset, show).
    
    Args:
        action: Action to perform (create, delete, set, unset, show)
        az_name: Availability zone name (required for delete/update)
        name: Name for new availability zone (required for create)
        availability_zone_profile_id: Profile ID (required for create)
        description: Description
        enabled: Whether the availability zone is enabled
    
    Returns:
        JSON string with operation results
    """
    try:
        logger.info(f"Managing availability zone with action: {action}")
        
        kwargs = {
            'az_name': az_name,
            'name': name,
            'availability_zone_profile_id': availability_zone_profile_id,
            'description': description,
            'enabled': enabled
        }
        
        result = _set_load_balancer_availability_zone(action, **kwargs)
        
        response = {
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "result": result
        }
        
        return json.dumps(response, indent=2, ensure_ascii=False)
        
    except Exception as e:
        error_msg = f"Error: Failed to manage availability zone - {str(e)}"
        logger.error(error_msg)
        return json.dumps({
            "timestamp": datetime.now().isoformat(),
            "error": error_msg,
            "success": False
        }, indent=2)
