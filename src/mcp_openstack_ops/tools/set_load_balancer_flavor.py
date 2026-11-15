"""Tool implementation for set_load_balancer_flavor."""

import json
from datetime import datetime
from ..functions import set_load_balancer_flavor as _set_load_balancer_flavor
from ..mcp_main import (
    conditional_tool,
    logger,
)

@conditional_tool
async def set_load_balancer_flavor(
    action: str,
    flavor_name_or_id: str = "",
    name: str = "",
    flavor_profile_id: str = "",
    description: str = "",
    enabled: bool = True
) -> str:
    """
    Create or delete an Octavia flavor. set, unset and show are not implemented;
    list and show flavors with get_load_balancer_flavors.
    
    Args:
        action: Action to perform (create, delete)
        flavor_name_or_id: Flavor name or ID (required for delete)
        name: Name for new flavor (required for create)
        flavor_profile_id: Profile ID (required for create)
        description: Description
        enabled: Whether the flavor is enabled
    
    Returns:
        JSON string with operation results
    """
    try:
        logger.info(f"Managing flavor with action: {action}")
        
        kwargs = {
            'flavor_name_or_id': flavor_name_or_id,
            'name': name,
            'flavor_profile_id': flavor_profile_id,
            'description': description,
            'enabled': enabled
        }
        
        result = _set_load_balancer_flavor(action, **kwargs)
        
        response = {
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "result": result
        }
        
        return json.dumps(response, indent=2, ensure_ascii=False)
        
    except Exception as e:
        error_msg = f"Error: Failed to manage flavor - {str(e)}"
        logger.error(error_msg)
        return json.dumps({
            "timestamp": datetime.now().isoformat(),
            "error": error_msg,
            "success": False
        }, indent=2)
