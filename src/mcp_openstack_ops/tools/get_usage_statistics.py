"""Tool implementation for get_usage_statistics."""

import json
from datetime import datetime
from ..functions import get_usage_statistics as _get_usage_statistics
from ..mcp_main import (
    logger,
    mcp,
)

@mcp.tool()
async def get_usage_statistics(start_date: str = "", end_date: str = "") -> str:
    """
    Get current-project Nova allocation-hours and separate current snapshots.
    
    Functions:
    - Show project usage statistics over a specified time period
    - Display servers, RAM MB-Hours, CPU Hours, and Disk GB-Hours
    - Provide detailed server usage breakdown when available
    - Keep current compute/network/storage snapshots separate from period data
    
    Use for project usage reports. Period data comes from Nova simple tenant usage.
    It measures allocation-hours, not live utilization or monetary charges.
    Missing or denied usage API returns failure without synthetic fallback.
    
    Args:
        start_date: Inclusive start date at UTC midnight (YYYY-MM-DD; defaults to 30 days ago)
        end_date: Exclusive end date at UTC midnight (YYYY-MM-DD; defaults to today)
        
    Returns:
        Usage statistics in JSON format with project usage data, server details, and summary information.
    """
    try:
        logger.info(f"Fetching usage statistics from {start_date or 'default'} to {end_date or 'default'}")
        usage_stats = _get_usage_statistics(start_date=start_date, end_date=end_date)
        
        response = {
            "timestamp": datetime.now().isoformat(),
            "operation": "get_usage_statistics",
            "parameters": {
                "start_date": start_date or "auto (30 days ago)",
                "end_date": end_date or "auto (today)"
            },
            "usage_data": usage_stats
        }
        
        return json.dumps(response, indent=2, ensure_ascii=False)
        
    except Exception as e:
        error_msg = f"Error: Failed to fetch usage statistics - {str(e)}"
        logger.error(error_msg)
        return error_msg
