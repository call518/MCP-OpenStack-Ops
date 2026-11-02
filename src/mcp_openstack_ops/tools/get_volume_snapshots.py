"""Tool implementation for get_volume_snapshots."""

from fastmcp.exceptions import ToolError

import json
from datetime import datetime
from ..functions import get_volume_snapshots as _get_volume_snapshots
from ..mcp_main import (
    logger,
    mcp,
)

@mcp.tool()
async def get_volume_snapshots() -> str:
    """
    Get list of volume snapshots.
    
    Functions:
    - Query volume snapshots and their status
    - Display source volume information
    - Show snapshot creation and modification dates
    - Provide snapshot size and usage information
    
    Use when user requests snapshot information, backup queries, or volume restoration planning.
    
    Returns:
        List of volume snapshots with detailed information in JSON format.
    """
    try:
        logger.info("Fetching volume snapshots")
        snapshots = _get_volume_snapshots()
        
        result = {
            "timestamp": datetime.now().isoformat(),
            "total_snapshots": len(snapshots),
            "snapshots": snapshots
        }
        
        return json.dumps(result, indent=2, ensure_ascii=False)
        
    except Exception as error:
        logger.error("get_volume_snapshots failed error_type=%s", type(error).__name__)
        raise ToolError("OpenStack query failed: get_volume_snapshots") from None
