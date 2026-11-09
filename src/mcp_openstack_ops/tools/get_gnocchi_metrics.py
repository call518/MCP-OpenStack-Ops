"""Tool implementation for get_gnocchi_metrics."""

import json
from ..functions import get_gnocchi_metrics as _get_gnocchi_metrics
from ..mcp_main import mcp


@mcp.tool()
async def get_gnocchi_metrics(
    resource_id: str = "",
    metric: str = "",
    resource_type: str = "generic",
    limit: int = 100,
) -> str:
    """
    List or show current-project Gnocchi metrics.

    Without arguments, lists metric names and IDs of current-project
    resources. With resource_id, shows that resource's metrics including
    archive policy and unit. With metric, shows one metric. Use it to check
    which telemetry metrics are actually collected before reading measures or
    creating alarms. These are measured telemetry series, not allocations or
    quotas.

    Args:
        resource_id: Resource ID (Nova server UUID for instances)
        metric: Metric UUID, or a metric name such as cpu or memory.usage when
            resource_id is also given
        resource_type: Gnocchi resource type used for listing (default generic)
        limit: Maximum metrics to return (1-1000, default 100)

    Requires a metric endpoint in the Keystone catalog. Results are limited to
    the current project. Missing services or denied calls return failure.

    Returns:
        JSON string with metric details or a metric list.
    """
    result = _get_gnocchi_metrics(
        resource_id=resource_id or None, metric=metric or None,
        resource_type=resource_type, limit=limit,
    )
    return json.dumps(result, indent=2, ensure_ascii=False, default=str)
