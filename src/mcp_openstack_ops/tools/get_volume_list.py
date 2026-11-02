"""Tool implementation for get_volume_list."""

from functools import partial

from anyio import to_thread

from fastmcp.exceptions import ToolError

import json
from datetime import datetime
from ..functions import get_volume_list as _get_volume_list
from ..mcp_main import (
    logger,
    mcp,
)

@mcp.tool()
async def get_volume_list() -> str:
    """
    Get list of all volumes with detailed information.
    
    Functions:
    - List all volumes in the project
    - Show volume status, size, and type information
    - Display attachment information for volumes
    - Provide detailed metadata for each volume
    
    Use when user requests volume listing, volume information, or storage overview.
    
    Returns:
        Detailed volume list in JSON format with volume information, attachments, and metadata.
    """
    try:
        logger.info("Fetching volume list")
        volumes = await to_thread.run_sync(partial(_get_volume_list))
        
        response = {
            "timestamp": datetime.now().isoformat(),
            "volumes": volumes,
            "count": len(volumes),
            "operation": "list_volumes"
        }
        
        return json.dumps(response, indent=2, ensure_ascii=False)
        
    except Exception as error:
        logger.error("get_volume_list failed error_type=%s", type(error).__name__)
        raise ToolError("OpenStack query failed: get_volume_list") from None
