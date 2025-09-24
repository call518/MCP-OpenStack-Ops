"""Tool implementation for set_image_visibility."""

import json
from ..functions import set_image_visibility as _set_image_visibility
from ..mcp_main import (
    _is_modify_operation_allowed,
    conditional_tool,
)

@conditional_tool
async def set_image_visibility(
    action: str,
    image_name: str,
    visibility: str = ""
) -> str:
    """
    Manage OpenStack image visibility settings for access control
    
    Args:
        action: Action to perform - show, set
        image_name: Name or ID of the image
        visibility: Visibility setting - public, private, shared, community (required for set)
        
    Returns:
        JSON string with image visibility management operation results
    """
    
    if not _is_modify_operation_allowed() and action.lower() in ['set']:
        return json.dumps({
            'success': False,
            'message': f'Modify operations are not allowed in current environment for action: {action}',
            'error': f'MODIFY_OPERATIONS_DISABLED'
        })
    
    try:
        result = _set_image_visibility(
            action=action,
            image_name=image_name,
            visibility=visibility if visibility else None
        )
        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({
            'success': False,
            'message': f'Failed to manage image visibility: {str(e)}',
            'error': str(e)
        }, indent=2)
