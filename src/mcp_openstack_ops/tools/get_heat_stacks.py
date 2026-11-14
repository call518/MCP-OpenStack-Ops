"""Tool implementation for get_heat_stacks."""

import json
from datetime import datetime
from ..connection import cross_project_items_scope
from ..functions import get_heat_stacks as _get_heat_stacks
from ..mcp_main import (
    logger,
    mcp,
)

@mcp.tool()
async def get_heat_stacks(all_projects: bool = False) -> str:
    """
    Get list of Heat orchestration stacks.

    Functions:
    - Query Heat stacks and their current status
    - Display stack creation and update timestamps
    - Use get_heat_stack_details for templates, resources, events, or outputs
    - Provide orchestration deployment information

    Use when user requests stack information, orchestration queries, or infrastructure-as-code status.

    Args:
        all_projects: If True, list stacks of every project (like 'openstack
            stack list --all-projects'); rows carry project_id and
            project_name. Requires ALLOW_CROSS_PROJECT_READ=true on the server.
            Heat's default policy denies this even to administrators, so a
            policy-denial error is the usual result unless the operator allows
            stacks:global_index.

    Returns:
        List of Heat stacks with detailed information in JSON format.
    """
    try:
        logger.info("Fetching Heat stacks")
        # The default call keeps its original arguments.
        stacks = _get_heat_stacks(all_projects=True) if all_projects else _get_heat_stacks()

        result = {
            "timestamp": datetime.now().isoformat(),
            "total_stacks": len(stacks),
            "stacks": stacks
        }
        if all_projects:
            result["scope"] = cross_project_items_scope(stacks)

        return json.dumps(result, indent=2, ensure_ascii=False)
        
    except Exception as e:
        error_msg = f"Error: Failed to fetch Heat stacks - {str(e)}"
        logger.error(error_msg)
        return error_msg
