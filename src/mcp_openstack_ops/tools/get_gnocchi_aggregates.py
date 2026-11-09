"""Tool implementation for get_gnocchi_aggregates."""

import json
from ..functions import get_gnocchi_aggregates as _get_gnocchi_aggregates
from ..mcp_main import mcp


@mcp.tool()
async def get_gnocchi_aggregates(
    metric: str = "",
    aggregation: str = "mean",
    reaggregation: str = "",
    operations: str = "",
    resource_type: str = "instance",
    filters: str = "",
    groupby: str = "",
    top: int = 0,
    start: str = "",
    stop: str = "",
    granularity: float | None = None,
    fill: str = "",
    needed_overlap: float | None = None,
    limit: int = 20,
) -> str:
    """
    Aggregate measured telemetry across many current-project resources.

    Use for cross-resource questions: project-wide averages or totals, top N
    resources, per-flavor or per-host groups, and ratios between metrics.
    For one resource's time series, use get_gnocchi_measures instead. For
    allocations, capacity, or quotas, use get_resource_monitoring.

    Choose ONE mode:
    1. Simple mode (preferred): set metric and aggregation, plus optional
       reaggregation, groupby, and top. Leave operations empty.
       - Project-wide average CPU: metric="cpu", aggregation="rate:mean",
         reaggregation="mean"
       - Top 5 instances by CPU: metric="cpu", aggregation="rate:mean", top=5
       - Mean memory use per flavor: metric="memory.usage",
         reaggregation="mean", groupby="flavor_name"
    2. Expression mode: set operations only, for arithmetic between metrics
       or advanced Gnocchi functions. Leave metric and reaggregation empty.
       Write metric NAMES, never metric UUIDs, as (metric NAME AGGREGATION).
       Example ratio: (/ (metric memory.usage mean) (metric memory mean))
       Arithmetic returns points only where every operand has data; memory
       (flavor size) is recorded sparsely, so this ratio has fewer points.

    Units: cpu with rate:mean is CPU nanoseconds per granularity window;
    utilization fraction = value / (granularity * 1e9 * vCPUs). memory.usage
    is MB in use. vcpus and memory are flavor sizes, not usage.

    Results are always limited to resources of the current project. The
    response echoes the executed operations expression.

    Args:
        metric: Metric name for simple mode, such as cpu or memory.usage
        aggregation: Aggregation from the metric archive policy, such as mean
            or rate:mean (use rate:mean for cumulative cpu)
        reaggregation: Combine all matched resources into one series with
            mean, sum, min, max, or median. Empty keeps one series per resource
        operations: Expression mode only; a Gnocchi operations expression
        resource_type: Gnocchi resource type to search (default instance)
        filters: JSON object of attribute equality filters, for example
            {"flavor_name": "m1.small"}
        groupby: Comma-separated resource attributes, such as flavor_name or
            host; one result group per value
        top: Return only the N series with the highest latest value (0 = all)
        start: Inclusive ISO 8601 start time
        stop: Exclusive ISO 8601 stop time
        granularity: Granularity in seconds from the archive policy
        fill: Value for missing points when combining series: a number,
            "null", or "dropna"
        needed_overlap: Percent of aligned points required across series
            (Gnocchi default 100); lower it or set fill for uneven data
        limit: Maximum latest rows per series (1-1000, default 20)

    Requires a metric endpoint in the Keystone catalog. Missing services,
    invalid expressions, or denied calls return failure with a hint.

    Returns:
        JSON string with labeled series, each with latest value and rows.
    """
    result = _get_gnocchi_aggregates(
        metric=metric or None, aggregation=aggregation,
        reaggregation=reaggregation or None, operations=operations or None,
        resource_type=resource_type, filters=filters or None,
        groupby=groupby or None, top=top, start=start or None,
        stop=stop or None, granularity=granularity, fill=fill or None,
        needed_overlap=needed_overlap, limit=limit,
    )
    return json.dumps(result, indent=2, ensure_ascii=False, default=str)
