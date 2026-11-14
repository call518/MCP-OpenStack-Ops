"""Tool implementation for get_heat_stack_details."""

import json
from ..services.orchestration import get_heat_stack_details as _query
from ..mcp_main import mcp


@mcp.tool()
async def get_heat_stack_details(stack_name: str, section: str = 'resources',
                                 nested_depth: int = 0) -> str:
    """Query resources, events, template, or outputs for a Heat stack.

    Args:
        stack_name: Stack name or ID.
        section: Detail section to return: resources, events, template, or outputs.
        nested_depth: For resources and events, also include nested stacks
            down to this depth (e.g. 2 shows AutoScalingGroup members and
            their servers). 0 shows the top-level stack only.
    """
    kwargs = {'nested_depth': nested_depth} if nested_depth else {}
    return json.dumps(_query(stack_name=stack_name, section=section, **kwargs),
                      indent=2)
