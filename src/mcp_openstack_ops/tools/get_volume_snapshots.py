"""Tool implementation for get_volume_snapshots."""

import json
from datetime import datetime

from fastmcp.exceptions import ToolError

from ..connection import CrossProjectReadError, cross_project_items_scope
from ..services.storage import CINDER_UNAVAILABLE
from ..functions import get_volume_snapshots as _get_volume_snapshots
from ..mcp_main import (
    logger,
    mcp,
)

@mcp.tool()
async def get_volume_snapshots(all_projects: bool = False) -> str:
    """
    Get list of volume snapshots.
    
    Functions:
    - Query volume snapshots and their status
    - Display source volume information
    - Show snapshot creation and modification dates
    - Provide snapshot size and usage information
    
    Use when user requests snapshot information, backup queries, or volume restoration planning.
    
    Args:
        all_projects: If True, include every project the credential's OpenStack
            policy allows (like 'openstack volume snapshot list --all-projects').
            Requires ALLOW_CROSS_PROJECT_READ=true on the server; a disabled or denied
            request is reported as an error, never as current-project results.

    Returns:
        List of volume snapshots with detailed information in JSON format.
    """
    try:
        logger.info("Fetching volume snapshots")
        snapshots = _get_volume_snapshots(all_projects=all_projects)
        
        result = {
            "timestamp": datetime.now().isoformat(),
            "total_snapshots": len(snapshots),
            "snapshots": snapshots
        }
        
        if all_projects:
            result["scope"] = cross_project_items_scope(snapshots)
        
        return json.dumps(result, indent=2, ensure_ascii=False)
        
    except CrossProjectReadError as error:
        raise ToolError(f"OpenStack query failed: get_volume_snapshots - {error}") from None
    except Exception as error:
        logger.error("get_volume_snapshots failed error_type=%s", type(error).__name__)
        # Keep upstream's redacted ToolError; only the explicit, endpoint-
        # redacted "Cinder not available" reason is added to it.
        if CINDER_UNAVAILABLE in str(error):
            raise ToolError(f"OpenStack query failed: get_volume_snapshots - {error}") from None
        raise ToolError("OpenStack query failed: get_volume_snapshots") from None
