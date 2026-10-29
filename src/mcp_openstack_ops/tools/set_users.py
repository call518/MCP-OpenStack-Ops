"""Tool implementation for set_users."""

import json
from ..services.identity import set_users as _set_users
from ..mcp_main import conditional_tool, _is_modify_operation_allowed


@conditional_tool
async def set_users(
    action: str,
    user_name: str,
    domain_id: str = 'default',
    password_env: str = '',
    description: str = '',
    enabled: bool = True,
) -> str:
    """Create/delete Keystone users; password_env names a server environment variable.

    Never supply passwords in chat. This tool does not grant project roles.
    """
    if not _is_modify_operation_allowed():
        return json.dumps({'success': False, 'error': 'MODIFY_OPERATIONS_DISABLED'})
    result = _set_users(
        action=action,
        user_name=user_name,
        domain_id=domain_id,
        password_env=password_env,
        description=description,
        enabled=enabled,
    )
    return json.dumps(result, indent=2)
