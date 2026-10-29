"""Tool implementation for get_image_members."""

import json
from ..services.image import set_image_members as _query
from ..mcp_main import mcp


@mcp.tool()
async def get_image_members(image_name: str) -> str:
    """List member projects for an image by name or ID."""
    return json.dumps(_query(action="list", image_name=image_name), indent=2)
