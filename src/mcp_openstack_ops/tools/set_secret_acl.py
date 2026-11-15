"""Tool implementation for set_secret_acl."""

import json
from ..services.key_manager import set_secret_acl as _set_secret_acl
from ..mcp_main import (
    _is_modify_operation_allowed,
    conditional_tool,
)


@conditional_tool
async def set_secret_acl(
    action: str,
    name_or_ref: str,
    target_type: str = "secret",
    users: str = "",
    project_access: str = ""
) -> str:
    """
    Change the read ACL of a Barbican secret or container.

    Octavia normally grants its own read access when a TERMINATED_HTTPS
    listener is created, so this is not a required step for listeners.

    Args:
        action: add_users, remove_users, set (replace the user list) or
            delete (restore default project-wide access)
        name_or_ref: Secret or container name, ID or href
        target_type: secret or container
        users: Comma-separated Keystone user IDs (add_users, remove_users, set)
        project_access: For set only: true or false to change project-wide
            read access; empty keeps the current value

    Returns:
        JSON string with the operation result and the resulting ACL
    """
    if not _is_modify_operation_allowed():
        return json.dumps({
            'success': False,
            'message': f'Modify operations are not allowed in current environment for action: {action}',
            'error': 'MODIFY_OPERATIONS_DISABLED'
        })
    access = project_access.strip().lower()
    if access not in ('', 'true', 'false'):
        return json.dumps({'success': False,
                           'message': 'project_access must be true, false or empty'})
    return json.dumps(_set_secret_acl(
        action=action, name_or_ref=name_or_ref, target_type=target_type,
        users=[u.strip() for u in users.split(',') if u.strip()],
        project_access=None if not access else access == 'true',
    ), indent=2, default=str)
