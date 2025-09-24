"""Tool implementation for set_flavor."""

from typing import Optional
from ..functions import set_flavor as _set_flavor
from ..mcp_main import (
    conditional_tool,
    handle_operation_result,
    logger,
)

@conditional_tool
async def set_flavor(
    flavor_name: str,
    action: str,
    vcpus: Optional[int] = None,
    ram: Optional[int] = None,
    disk: Optional[int] = None,
    ephemeral: Optional[int] = None,
    swap: Optional[int] = None,
    rxtx_factor: Optional[float] = None,
    is_public: Optional[bool] = None,
    properties: Optional[str] = None
) -> str:
    """
    Manage OpenStack flavors (create, delete, set properties, list)
    
    Args:
        flavor_name: Name of the flavor
        action: Action to perform (create, delete, show, list, set)
        vcpus: Number of virtual CPUs (for create)
        ram: Amount of RAM in MB (for create)
        disk: Disk size in GB (for create)
        ephemeral: Ephemeral disk size in GB (for create)
        swap: Swap size in MB (for create)
        rxtx_factor: RX/TX factor (for create)
        is_public: Whether flavor is public (for create)
        properties: JSON string of extra properties (for create/set)
    
    Returns:
        JSON string with flavor operation result
    """
    try:
        logger.info(f"Managing flavor: {flavor_name}, action: {action}")
        
        flavor_params = {}
        
        if vcpus is not None:
            flavor_params['vcpus'] = vcpus
        if ram is not None:
            flavor_params['ram'] = ram
        if disk is not None:
            flavor_params['disk'] = disk
        if ephemeral is not None:
            flavor_params['ephemeral'] = ephemeral
        if swap is not None:
            flavor_params['swap'] = swap
        if rxtx_factor is not None:
            flavor_params['rxtx_factor'] = rxtx_factor
        if is_public is not None:
            flavor_params['is_public'] = is_public
            
        if properties:
            import json as json_module
            flavor_params['properties'] = json_module.loads(properties)
        
        flavor_result = _set_flavor(flavor_name=flavor_name, action=action, **flavor_params)
        
        # Use centralized result handling
        return handle_operation_result(
            flavor_result,
            "Flavor Management",
            {
                "Action": action,
                "Flavor Name": flavor_name,
                "vCPUs": vcpus or "Not specified",
                "RAM": ram or "Not specified",
                "Disk": disk or "Not specified"
            }
        )
        
    except Exception as e:
        error_msg = f"Error: Failed to manage flavor - {str(e)}"
        logger.error(error_msg)
        return error_msg
