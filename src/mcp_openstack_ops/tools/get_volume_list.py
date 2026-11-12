"""Tool implementation for get_volume_list."""

from functools import partial

from anyio import to_thread

import json
from datetime import datetime

from fastmcp.exceptions import ToolError

from ..connection import CrossProjectReadError, cross_project_items_scope
from ..services.storage import CINDER_UNAVAILABLE
from ..functions import get_volume_list as _get_volume_list
from ..mcp_main import (
    logger,
    mcp,
)

@mcp.tool()
async def get_volume_list(all_projects: bool = False) -> str:
    """
    Get list of all volumes with detailed information.
    
    Functions:
    - List all volumes in the project
    - Show volume status, size, and type information
    - Display attachment information for volumes
    - Provide detailed metadata for each volume
    
    Use when user requests volume listing, volume information, or storage overview.
    
    Args:
        all_projects: If True, include every project the credential's OpenStack
            policy allows (like 'openstack volume list --all-projects'). Requires
            ALLOW_CROSS_PROJECT_READ=true on the server; a disabled or denied
            request is reported as an error, never as current-project results.

    Returns:
        Detailed volume list in JSON format with volume information, attachments, and metadata.
    """
    try:
        logger.info("Fetching volume list")
        volumes = await to_thread.run_sync(partial(_get_volume_list, all_projects=all_projects))
        
        response = {
            "timestamp": datetime.now().isoformat(),
            "volumes": volumes,
            "count": len(volumes),
            "operation": "list_volumes"
        }
        
        if all_projects:
            response["scope"] = await to_thread.run_sync(
                partial(cross_project_items_scope, volumes))
        
        return json.dumps(response, indent=2, ensure_ascii=False)
        
    except CrossProjectReadError as error:
        raise ToolError(f"OpenStack query failed: get_volume_list - {error}") from None
    except Exception as error:
        logger.error("get_volume_list failed error_type=%s", type(error).__name__)
        # Keep upstream's redacted ToolError; only the explicit, endpoint-
        # redacted "Cinder not available" reason is added to it.
        if CINDER_UNAVAILABLE in str(error):
            raise ToolError(f"OpenStack query failed: get_volume_list - {error}") from None
        raise ToolError("OpenStack query failed: get_volume_list") from None
