"""Tool implementation for set_routers."""

import json
from ..services.network import set_routers as _set_routers
from ..mcp_main import conditional_tool, _is_modify_operation_allowed


@conditional_tool
async def set_routers(
    action: str,
    router_name: str,
    description: str = '',
) -> str:
    """Create/delete project-owned routers without detaching interfaces."""
    if not _is_modify_operation_allowed():
        return json.dumps({'success': False, 'error': 'MODIFY_OPERATIONS_DISABLED'})
    result = _set_routers(
        action=action,
        router_name=router_name,
        description=description,
    )
    return json.dumps(result, indent=2)
