"""Tool implementation for get_resource_monitoring."""

import json
from datetime import datetime
from ..functions import get_resource_monitoring as _get_resource_monitoring
from ..mcp_main import (
    logger,
    mcp,
)

@mcp.tool()
async def get_resource_monitoring() -> str:
    """
    Read current project allocations and visible hypervisor capacity.
    
    Functions:
    - Report project flavor allocations, not live CPU or memory utilization
    - Collect hypervisor statistics and resource allocation
    - Separate project quota limits from visible physical capacity
    - Return null for unavailable capacity or incomplete flavor allocations
    
    Use for current inventory and capacity planning. No historical trends or
    telemetry samples are collected. Physical totals and project allocations
    have different scopes and should not be divided into a utilization rate.
    
    Returns:
        Resource monitoring data in JSON format with cluster summary, hypervisor details, and usage statistics.
    """
    try:
        logger.info("Monitoring OpenStack cluster resources")
        monitoring_data = _get_resource_monitoring()
        
        result = {
            "timestamp": datetime.now().isoformat(),
            "resource_monitoring": monitoring_data
        }
        
        return json.dumps(result, indent=2, ensure_ascii=False)
        
    except Exception as e:
        error_msg = f"Error: Failed to monitor OpenStack resources - {str(e)}"
        logger.error(error_msg)
        return error_msg
