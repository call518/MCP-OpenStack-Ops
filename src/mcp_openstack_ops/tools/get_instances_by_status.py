"""Tool implementation for get_instances_by_status."""

from functools import partial

from anyio import to_thread

from fastmcp.exceptions import ToolError

import json
from datetime import datetime
from ..functions import get_instances_by_status as _get_instances_by_status
from ..services.compute import NOVA_SERVER_STATUSES
from ..mcp_main import (
    logger,
    mcp,
)

@mcp.tool()
async def get_instances_by_status(status: str) -> str:
    """
    Get instances filtered by status.
    
    Args:
        status: Nova server status to filter by, case-insensitive (ACTIVE,
            BUILD, DELETED, ERROR, HARD_REBOOT, MIGRATING, PASSWORD, PAUSED,
            REBOOT, REBUILD, RESCUE, RESIZE, REVERT_RESIZE, SHELVED,
            SHELVED_OFFLOADED, SHUTOFF, SOFT_DELETED, SUSPENDED, UNKNOWN,
            VERIFY_RESIZE)
        
    Returns:
        List of instances with the specified status. An invalid status or a
        failed query raises a ToolError (an MCP error result)
    """
    normalized = str(status or '').strip().upper()
    if normalized not in NOVA_SERVER_STATUSES:
        raise ToolError(
            f'Invalid instance status "{status}". Valid statuses: '
            + ', '.join(sorted(NOVA_SERVER_STATUSES))
        )
    try:
        logger.info(f"Getting instances with status: {normalized}")
        
        instances = await to_thread.run_sync(partial(_get_instances_by_status, normalized))
        
        result = {
            "timestamp": datetime.now().isoformat(),
            "status_filter": normalized,
            "instances_found": len(instances),
            "instances": instances
        }
        
        return json.dumps(result, indent=2, ensure_ascii=False)
        
    except Exception as error:
        logger.error("get_instances_by_status failed error_type=%s", type(error).__name__)
        raise ToolError("OpenStack query failed: get_instances_by_status") from None
