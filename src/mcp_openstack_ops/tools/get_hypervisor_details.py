"""Tool implementation for get_hypervisor_details."""

import json
from datetime import datetime
from ..functions import get_hypervisor_details as _get_hypervisor_details
from ..mcp_main import (
    logger,
    mcp,
)

@mcp.tool()
async def get_hypervisor_details(
    hypervisor_name: str = "all"
) -> str:
    """
    Get detailed information about hypervisors
    
    Args:
        hypervisor_name: Name/ID of specific hypervisor or "all" for all hypervisors
    
    Returns:
        JSON string with hypervisor details and statistics
    """
    try:
        logger.info(f"Getting hypervisor details for: {hypervisor_name}")
        
        hypervisor_result = _get_hypervisor_details(hypervisor_name=hypervisor_name)
        
        response = {
            "timestamp": datetime.now().isoformat(),
            "operation": "get_hypervisor_details",
            "parameters": {
                "hypervisor_name": hypervisor_name
            },
            "result": hypervisor_result
        }
        
        return json.dumps(response, indent=2, ensure_ascii=False)
        
    except Exception as e:
        error_msg = f"Error: Failed to get hypervisor details - {str(e)}"
        logger.error(error_msg)
        return error_msg
