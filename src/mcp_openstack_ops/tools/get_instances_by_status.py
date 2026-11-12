"""Tool implementation for get_instances_by_status."""

from functools import partial

from anyio import to_thread

from fastmcp.exceptions import ToolError

import json
from datetime import datetime
from ..functions import get_instances_by_status as _get_instances_by_status
from ..connection import CrossProjectReadError, cross_project_items_scope
from ..services.compute import NOVA_SERVER_STATUSES
from ..mcp_main import (
    logger,
    mcp,
)

@mcp.tool()
async def get_instances_by_status(status: str, all_projects: bool = False) -> str:
    """
    Get instances filtered by status.
    
    Args:
        status: Nova server status to filter by, case-insensitive (ACTIVE,
            BUILD, DELETED, ERROR, HARD_REBOOT, MIGRATING, PASSWORD, PAUSED,
            REBOOT, REBUILD, RESCUE, RESIZE, REVERT_RESIZE, SHELVED,
            SHELVED_OFFLOADED, SHUTOFF, SOFT_DELETED, SUSPENDED, UNKNOWN,
            VERIFY_RESIZE)
        all_projects: If True, include every project the credential's OpenStack
            policy allows (like 'openstack server list --status --all-projects'). Requires
            ALLOW_CROSS_PROJECT_READ=true on the server; a disabled or denied
            request is reported as an error, never as current-project results.
        
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
        
        instances = await to_thread.run_sync(partial(
            _get_instances_by_status, normalized, all_projects=all_projects))
        
        result = {
            "timestamp": datetime.now().isoformat(),
            "status_filter": normalized,
            "instances_found": len(instances),
            "instances": instances
        }
        if all_projects:
            result["scope"] = await to_thread.run_sync(
                partial(cross_project_items_scope, instances))
        
        return json.dumps(result, indent=2, ensure_ascii=False)
        
    except CrossProjectReadError as error:
        raise ToolError(f"OpenStack query failed: get_instances_by_status - {error}") from None
    except Exception as error:
        logger.error("get_instances_by_status failed error_type=%s", type(error).__name__)
        raise ToolError("OpenStack query failed: get_instances_by_status") from None
