"""Tool implementation for set_volume_qos."""

import json
from ..functions import set_volume_qos as _set_volume_qos
from ..mcp_main import (
    _is_modify_operation_allowed,
    conditional_tool,
)

@conditional_tool
async def set_volume_qos(
    action: str,
    qos_name: str = "",
    consumer: str = "back-end",
    specs: str = "{}",
    force: bool = False
) -> str:
    """
    Manage OpenStack volume QoS specifications for performance control
    
    Args:
        action: Action to perform - list, create, delete, show, set
        qos_name: Name or ID of the QoS specification
        consumer: QoS consumer type - 'front-end', 'back-end', or 'both'
        specs: JSON string of QoS specifications (e.g., '{"read_iops_sec": 1000}')
        force: Force deletion even if QoS is associated with volume types
        
    Returns:
        JSON string with QoS operation results
    """
    
    if not _is_modify_operation_allowed() and action.lower() in ['create', 'delete', 'set']:
        return json.dumps({
            'success': False,
            'message': f'Modify operations are not allowed in current environment for action: {action}',
            'error': f'MODIFY_OPERATIONS_DISABLED'
        })
    
    try:
        # Parse specs from JSON string
        import json as json_lib
        parsed_specs = json_lib.loads(specs) if specs != "{}" else {}
        
        result = _set_volume_qos(
            action=action,
            qos_name=qos_name if qos_name else None,
            consumer=consumer,
            specs=parsed_specs,
            force=force
        )
        return json.dumps(result, indent=2)
    except json_lib.JSONDecodeError as e:
        return json.dumps({
            'success': False,
            'message': f'Invalid JSON in specs parameter: {str(e)}',
            'error': str(e)
        }, indent=2)
    except Exception as e:
        return json.dumps({
            'success': False,
            'message': f'Failed to manage volume QoS: {str(e)}',
            'error': str(e)
        }, indent=2)
