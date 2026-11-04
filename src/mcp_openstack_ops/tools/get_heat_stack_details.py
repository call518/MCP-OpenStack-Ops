"""Tool implementation for get_heat_stack_details."""

import json
from ..services.orchestration import get_heat_stack_details as _query
from ..mcp_main import mcp


@mcp.tool()
async def get_heat_stack_details(stack_name: str, section: str = 'resources') -> str:
    """Query resources, events, template, or outputs for a Heat stack.

    Args:
        stack_name: Stack name or ID.
        section: Detail section to return: resources, events, template, or outputs.
    """
    return json.dumps(_query(stack_name=stack_name, section=section), indent=2)
