"""Tool implementation for get_server_groups."""

import json
from datetime import datetime
from ..connection import cross_project_items_scope
from ..functions import get_server_groups as _get_server_groups
from ..mcp_main import (
    logger,
    mcp,
)

@mcp.tool()
async def get_server_groups(all_projects: bool = False) -> str:
    """
    List all server groups with their details

    Args:
        all_projects: If True, include every project the credential's OpenStack
            policy allows (like 'openstack server group list --all-projects');
            rows carry project_id and project_name. Requires
            ALLOW_CROSS_PROJECT_READ=true on the server; a disabled or denied
            request is reported as an error. Check scope.warning.

    Returns:
        JSON string with server groups information
    """
    try:
        logger.info("Getting server groups list")

        # The default call keeps its original arguments.
        groups_result = (_get_server_groups(all_projects=True) if all_projects
                         else _get_server_groups())

        response = {
            "timestamp": datetime.now().isoformat(),
            "operation": "get_server_groups",
            "result": {
                "server_groups_count": len(groups_result),
                "server_groups": groups_result
            }
        }
        if all_projects:
            response["result"]["scope"] = cross_project_items_scope(groups_result)

        return json.dumps(response, indent=2, ensure_ascii=False)
        
    except Exception as e:
        error_msg = f"Error: Failed to get server groups - {str(e)}"
        logger.error(error_msg)
        return error_msg
