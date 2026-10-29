"""Tool implementation for set_volume_types."""

import json
from ..services.storage import set_volume_types as _set_volume_types
from ..mcp_main import conditional_tool, _is_modify_operation_allowed


@conditional_tool
async def set_volume_types(
    action: str,
    type_name: str,
    description: str = '',
) -> str:
    """Create/delete Cinder volume types, usually an administrative operation."""
    if not _is_modify_operation_allowed():
        return json.dumps({'success': False, 'error': 'MODIFY_OPERATIONS_DISABLED'})
    result = _set_volume_types(
        action=action,
        type_name=type_name,
        description=description,
    )
    return json.dumps(result, indent=2)
