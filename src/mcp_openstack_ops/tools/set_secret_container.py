"""Tool implementation for set_secret_container."""

import json
from ..services.key_manager import set_secret_container as _set_secret_container
from ..mcp_main import (
    _is_modify_operation_allowed,
    conditional_tool,
)


@conditional_tool
async def set_secret_container(
    action: str,
    name: str = "",
    container_type: str = "generic",
    secret_refs: str = "{}"
) -> str:
    """
    Create a Barbican container from existing secrets, or delete a container.

    A container stores references only; deleting it keeps the secrets.

    Args:
        action: create or delete
        name: Container name (create), or container name, ID or href (delete)
        container_type: generic, certificate (entries certificate, private_key,
            private_key_passphrase, intermediates) or rsa (private_key,
            public_key, private_key_passphrase)
        secret_refs: JSON object mapping entry names to secret names, IDs or
            hrefs, e.g. '{"certificate": "web-cert", "private_key": "web-key"}'

    Returns:
        JSON string with the operation result
    """
    if not _is_modify_operation_allowed():
        return json.dumps({
            'success': False,
            'message': f'Modify operations are not allowed in current environment for action: {action}',
            'error': 'MODIFY_OPERATIONS_DISABLED'
        })
    try:
        refs = json.loads(secret_refs or "{}")
    except json.JSONDecodeError as e:
        return json.dumps({'success': False,
                           'message': f'Invalid JSON in secret_refs: {e}'})
    if not isinstance(refs, dict):
        return json.dumps({'success': False,
                           'message': 'secret_refs must be a JSON object'})
    return json.dumps(_set_secret_container(
        action=action, name=name, container_type=container_type, secret_refs=refs,
    ), indent=2, default=str)
