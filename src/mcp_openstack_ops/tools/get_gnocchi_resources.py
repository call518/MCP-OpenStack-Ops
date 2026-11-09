"""Tool implementation for get_gnocchi_resources."""

import json
from ..functions import get_gnocchi_resources as _get_gnocchi_resources
from ..mcp_main import mcp


@mcp.tool()
async def get_gnocchi_resources(
    resource_type: str = "generic",
    resource_id: str = "",
    filters: str = "",
    history: bool = False,
    limit: int = 100,
    marker: str = "",
) -> str:
    """
    List, search, or show current-project Gnocchi (telemetry) resources.

    Resources are the objects Ceilometer measures, such as instances, disks,
    and network interfaces. Each resource maps metric names to metric IDs.
    Use this to find which metrics exist for a server before reading measures.

    Args:
        resource_type: Gnocchi resource type (generic, instance,
            instance_disk, instance_network_interface, ...; default generic)
        resource_id: Resource ID; for instances this is the Nova server UUID.
            When set, returns that resource with its metrics map.
        filters: JSON object of attribute equality filters for listing, for
            example {"display_name": "vm1"} or {"original_resource_id": "..."}
        history: With resource_id, return the resource's revision history
        limit: Maximum resources or revisions to return (1-1000, default 100)
        marker: Pagination marker from a previous next_marker value

    Requires a metric endpoint in the Keystone catalog. Results are limited to
    the current project. Missing services or denied calls return failure.

    Returns:
        JSON string with resources, a single resource, or its history.
    """
    result = _get_gnocchi_resources(
        resource_type=resource_type, resource_id=resource_id or None,
        filters=filters or None, history=history, limit=limit,
        marker=marker or None,
    )
    return json.dumps(result, indent=2, ensure_ascii=False, default=str)
