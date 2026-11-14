"""Tool implementation for get_volume_backups."""

import json
from fastmcp.exceptions import ToolError
from ..connection import CrossProjectReadError, require_cross_project_read
from ..services.storage import set_volume_backups as _query
from ..mcp_main import mcp


@mcp.tool()
async def get_volume_backups(all_projects: bool = False) -> str:
    """List Cinder backups visible in the current project.

    Args:
        all_projects: If True, include every project the credential's OpenStack
            policy allows (like 'openstack volume backup list --all-projects');
            rows carry project_id and project_name. Requires
            ALLOW_CROSS_PROJECT_READ=true on the server. Cinder narrows an
            unauthorized request to the current project, so check scope.warning.
    """
    if not all_projects:
        return json.dumps(_query(action="list"), indent=2)
    try:
        require_cross_project_read()
        return json.dumps(_query(action="list", all_projects=True), indent=2)
    except CrossProjectReadError as error:
        raise ToolError(f"OpenStack query failed: get_volume_backups - {error}") from None
