"""Tool implementation for set_domains."""

import json
from ..functions import set_domains as _set_domains
from ..mcp_main import (
    _is_modify_operation_allowed,
    _read_action_error,
    conditional_tool,
)

READ_ACTIONS = {'list': 'get_domains', 'show': 'get_domains'}


@conditional_tool
async def set_domains(
    action: str,
    domain_name: str = "",
    description: str = "",
    enabled: bool = True
) -> str:
    """
    Create, delete or update OpenStack domains for multi-tenancy
    organization. To list or show domains, use get_domains.

    Args:
        action: Action to perform - create, delete, update
        domain_name: Name of the domain (required for create)
        description: Description for the domain
        enabled: Enable the domain (default: True)
        
    Returns:
        JSON string with domain management operation results
    """
    read_error = _read_action_error(action, READ_ACTIONS)
    if read_error:
        return read_error
    
    if not _is_modify_operation_allowed() and action.lower() in ['create', 'delete',
        'update']:
        return json.dumps({
            'success': False,
            'message': f'Modify operations are not allowed in current environment for action: {action}',
            'error': f'MODIFY_OPERATIONS_DISABLED'
        })
    
    try:
        result = _set_domains(
            action=action,
            domain_name=domain_name if domain_name else None,
            description=description,
            enabled=enabled
        )
        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({
            'success': False,
            'message': f'Failed to manage domain: {str(e)}',
            'error': str(e)
        }, indent=2)
