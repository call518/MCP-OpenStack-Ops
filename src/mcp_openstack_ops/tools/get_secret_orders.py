"""Tool implementation for get_secret_orders."""

import json
from ..services.key_manager import get_secret_orders as _query
from ..mcp_main import mcp


@mcp.tool()
async def get_secret_orders(order_id: str = "", limit: int = 100) -> str:
    """List or show Barbican key-generation orders of the current project.

    An ACTIVE order points to the generated secret (key orders) or container
    (asymmetric orders) through secret_ref or container_ref.

    Args:
        order_id: Order ID or href to show one order. Empty lists orders.
        limit: Maximum number of orders to list (1-1000).
    """
    return json.dumps(_query(order_id=order_id, limit=limit), indent=2, default=str)
