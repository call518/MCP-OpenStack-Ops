"""Tool implementation for get_load_balancer_status."""

import json
from ..services.load_balancer import (
    set_load_balancer as _lb_query,
    set_load_balancer_listener as _listener_query,
)
from ..mcp_main import mcp


@mcp.tool()
async def get_load_balancer_status(
    lb_name_or_id: str = "",
    listener_name_or_id: str = "",
) -> str:
    """Show a load balancer's status tree and statistics, or a listener's
    statistics (like 'openstack loadbalancer status show' and
    'openstack loadbalancer stats show').

    Statistics are Octavia's traffic counters (bytes in/out, connections),
    not Gnocchi measurements. Give lb_name_or_id, listener_name_or_id, or both.

    Args:
        lb_name_or_id: Load balancer name or ID. Returns status (its
            load_balancer_status: provisioning and operating status with
            listeners, pools, members and health monitors) and statistics
            (its load_balancer_stats).
        listener_name_or_id: Listener name or ID. Returns listener_statistics
            (its listener_stats, including request_errors).

    Returns:
        JSON with the requested sections; each section reports its own
        success or error.
    """
    if not (lb_name_or_id or listener_name_or_id):
        return json.dumps({
            'success': False,
            'message': 'lb_name_or_id or listener_name_or_id is required',
        }, indent=2)
    result = {}
    if lb_name_or_id:
        result['status'] = _lb_query(action='status', lb_name_or_id=lb_name_or_id)
        result['statistics'] = _lb_query(action='stats', lb_name_or_id=lb_name_or_id)
    if listener_name_or_id:
        result['listener_statistics'] = _listener_query(
            action='stats', listener_name_or_id=listener_name_or_id)
    result['success'] = all(part.get('success') for part in result.values())
    return json.dumps(result, indent=2)
