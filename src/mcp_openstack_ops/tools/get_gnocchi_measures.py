"""Tool implementation for get_gnocchi_measures."""

import json
from ..functions import get_gnocchi_measures as _get_gnocchi_measures
from ..mcp_main import mcp


@mcp.tool()
async def get_gnocchi_measures(
    metric: str,
    resource_id: str = "",
    start: str = "",
    stop: str = "",
    granularity: float | None = None,
    aggregation: str = "mean",
    resample: float | None = None,
    refresh: bool = False,
    limit: int = 100,
) -> str:
    """
    Read stored Gnocchi measures (telemetry time series) for a metric.

    Use for measured utilization, load, trends, and history ("CPU usage of
    vm1", "memory over the last hour"). Values are observed telemetry
    collected by Ceilometer, such as cpu, memory.usage, or disk and network
    counters. Cumulative counters like cpu (nanoseconds) grow over time;
    compare consecutive values for rates. Some metrics such as vcpus and memory
    record flavor sizes, not usage. For averages, totals, top N, or groups
    across many resources, use get_gnocchi_aggregates. For allocations,
    capacity, or quotas, use
    get_resource_monitoring or get_quota. If a metric is not collected, report
    that; do not substitute allocation data.

    Args:
        metric: Metric UUID, or a metric name when resource_id is given
        resource_id: Resource ID (Nova server UUID for instances)
        start: Inclusive ISO 8601 start time (default: all retained data)
        stop: Exclusive ISO 8601 stop time
        granularity: Granularity in seconds from the metric archive policy
        aggregation: Aggregation method from the archive policy (default mean)
        resample: Resample interval in seconds (requires granularity)
        refresh: Process pending measures before reading
        limit: Maximum latest measures to return (1-1000, default 100)

    Requires a metric endpoint in the Keystone catalog. Results are limited to
    the current project. Missing services or denied calls return failure.

    Returns:
        JSON string with [timestamp, granularity, value] rows.
    """
    result = _get_gnocchi_measures(
        metric=metric, resource_id=resource_id or None, start=start or None,
        stop=stop or None, granularity=granularity, aggregation=aggregation,
        resample=resample, refresh=refresh, limit=limit,
    )
    return json.dumps(result, indent=2, ensure_ascii=False, default=str)
