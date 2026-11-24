"""Tool implementation for get_server_migrations."""

import json
from ..services.compute import set_server_migration as _query
from ..mcp_main import mcp


@mcp.tool()
async def get_server_migrations(
    instance_name: str = "",
    migration_id: str = "",
    all_projects: bool = False,
) -> str:
    """List server migrations of the current project, or show one migration of
    a server.

    Args:
        instance_name: Optional server name or ID in the current project. When
            provided, list that server's in-progress migrations (Nova's server
            migrations API); otherwise list the current project's migrations
            from Nova's os-migrations API, which cloud policy usually restricts
            to administrators.
        migration_id: Optional migration ID; requires instance_name. When
            provided, show that migration.
        all_projects: Only without instance_name. If True, list the
            migrations of every server in the cloud (like 'openstack server
            migration list' as an administrator). Requires
            ALLOW_CROSS_PROJECT_READ=true on the server; rows then carry
            project_name, and the result has a scope (check scope.warning).

    Returns:
        JSON with migrations (or migration): server_id, status,
        migration_type, source_node, dest_node, created_at and updated_at;
        os-migrations rows also carry project_id (null before Nova
        microversion 2.80).
    """
    if migration_id:
        if not instance_name:
            return json.dumps({
                'success': False,
                'message': 'instance_name is required with migration_id',
            }, indent=2)
        return json.dumps(_query(instance_name, 'show', migration_id=migration_id,
                                 all_projects=all_projects), indent=2)
    return json.dumps(_query(instance_name, 'list', all_projects=all_projects),
                      indent=2)
