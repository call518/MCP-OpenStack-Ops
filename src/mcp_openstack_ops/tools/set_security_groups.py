"""Tool implementation for set_security_groups."""

import json
from ..services.network import set_security_groups as _set_security_groups
from ..mcp_main import conditional_tool, _is_modify_operation_allowed


@conditional_tool
async def set_security_groups(
    action: str,
    group_name: str,
    description: str = '',
) -> str:
    """Create/delete project-owned security groups subject to cloud policy."""
    if not _is_modify_operation_allowed():
        return json.dumps({'success': False, 'error': 'MODIFY_OPERATIONS_DISABLED'})
    result = _set_security_groups(
        action=action,
        group_name=group_name,
        description=description,
    )
    return json.dumps(result, indent=2)
