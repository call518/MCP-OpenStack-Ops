"""Tool implementation for set_image_metadata."""

import json
from ..functions import set_image_metadata as _set_image_metadata
from ..mcp_main import (
    _is_modify_operation_allowed,
    _read_action_error,
    conditional_tool,
)

READ_ACTIONS = {'show': 'get_image_detail_list'}


@conditional_tool
async def set_image_metadata(
    action: str,
    image_name: str,
    properties: str = "{}"
) -> str:
    """
    Set OpenStack image metadata and properties. To read them, use
    get_image_detail_list (properties and tags).
    
    Args:
        action: Action to perform - set. It applies only to images owned by
            the current project
        image_name: Name or ID of the image
        properties: JSON string of properties to set (e.g., '{"os_type": "linux", "architecture": "x86_64"}')
        
    Returns:
        JSON string with image metadata management operation results
    """
    read_error = _read_action_error(action, READ_ACTIONS)
    if read_error:
        return read_error

    if not _is_modify_operation_allowed() and action.lower() in ['set']:
        return json.dumps({
            'success': False,
            'message': f'Modify operations are not allowed in current environment for action: {action}',
            'error': f'MODIFY_OPERATIONS_DISABLED'
        })
    
    try:
        # Parse properties from JSON string
        import json as json_lib
        parsed_properties = json_lib.loads(properties) if properties != "{}" else {}
        
        result = _set_image_metadata(
            action=action,
            image_name=image_name,
            properties=parsed_properties
        )
        return json.dumps(result, indent=2)
    except json_lib.JSONDecodeError as e:
        return json.dumps({
            'success': False,
            'message': f'Invalid JSON in properties parameter: {str(e)}',
            'error': str(e)
        }, indent=2)
    except Exception as e:
        return json.dumps({
            'success': False,
            'message': f'Failed to manage image metadata: {str(e)}',
            'error': str(e)
        }, indent=2)
