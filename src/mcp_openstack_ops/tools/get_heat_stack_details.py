"""Tool implementation for get_heat_stack_details."""

import json
from ..services.orchestration import get_heat_stack_details as _query
from ..mcp_main import mcp


@mcp.tool()
async def get_heat_stack_details(stack_name: str, section: str = 'resources') -> str:
    """Query a Heat stack by name or ID. section: resources, events, template, outputs.
    """
    return json.dumps(_query(stack_name=stack_name, section=section), indent=2)
