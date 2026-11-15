"""Tool implementation for set_secret_order."""

import json
from ..services.key_manager import set_secret_order as _set_secret_order
from ..mcp_main import (
    _is_modify_operation_allowed,
    conditional_tool,
)


@conditional_tool
async def set_secret_order(
    action: str,
    order_id: str = "",
    order_type: str = "key",
    name: str = "",
    algorithm: str = "",
    bit_length: int = 0,
    mode: str = "",
    expiration: str = ""
) -> str:
    """
    Order Barbican to generate a key, or delete an order.

    Barbican generates and stores the key itself; only references are returned.
    Orders are asynchronous: check the result with get_secret_orders.

    Args:
        action: create or delete
        order_id: Order ID or href (delete)
        order_type: key (symmetric; default aes 256 cbc) or asymmetric
            (default rsa 2048, result is an rsa container)
        name: Name of the generated secret or container (create)
        algorithm: Override the default algorithm, e.g. aes or rsa
        bit_length: Override the default key length
        mode: Override the default symmetric mode, e.g. cbc
        expiration: Optional expiration of the generated secret (ISO 8601, UTC)

    Returns:
        JSON string with the operation result
    """
    if not _is_modify_operation_allowed():
        return json.dumps({
            'success': False,
            'message': f'Modify operations are not allowed in current environment for action: {action}',
            'error': 'MODIFY_OPERATIONS_DISABLED'
        })
    return json.dumps(_set_secret_order(
        action=action, order_id=order_id, order_type=order_type, name=name,
        algorithm=algorithm, bit_length=bit_length, mode=mode, expiration=expiration,
    ), indent=2, default=str)
