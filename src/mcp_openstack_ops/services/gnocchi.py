"""Read-only, project-scoped Gnocchi (metric service) operations."""

import json
import math
import re
from datetime import datetime
from typing import Any

from gnocchiclient.v1 import client as gnocchi_client
from keystoneauth1 import exceptions as ksa_exceptions

from ..connection import get_openstack_connection

GNOCCHI_UNAVAILABLE = "Metric service (Gnocchi) is not available in this cloud"
MAX_LIMIT = 1000
MAX_SERIES = 100
MAX_TOP = 100
MAX_OPERATIONS_LENGTH = 1000
SERVICE_INFO_SECTIONS = (
    "archive_policies", "archive_policy_rules", "resource_types",
    "capabilities", "status",
)
# Names inserted into an operations expression must not contain spaces or
# parentheses, so they cannot change the expression structure.
_TOKEN = re.compile(r"^[^\s()]+$")
AGGREGATES_HINT = (
    "Check metric names with get_gnocchi_metrics and aggregation methods "
    "with get_gnocchi_service_info. 'Metric ... does not exist' also means no "
    "current-project resource of resource_type matched filters and has that "
    "metric. When combining resources whose points do not align, set fill=0 "
    "or lower needed_overlap."
)


def _context() -> tuple[Any, str]:
    """Return a Gnocchi client bound to the authenticated session and project."""
    conn = get_openstack_connection()
    project_id = conn.current_project_id
    if not project_id:
        raise ValueError("A project-scoped connection is required")
    client = gnocchi_client.Client(
        session=conn.session,
        adapter_options={
            "interface": conn.config.get_interface(),
            "region_name": conn.config.region_name,
        },
    )
    return client, project_id


def _check_limit(limit: int) -> None:
    if not 1 <= limit <= MAX_LIMIT:
        raise ValueError(f"limit must be between 1 and {MAX_LIMIT}")


def _is_unavailable(exc: Exception) -> bool:
    """True when the Keystone catalog has no metric endpoint (no Gnocchi)."""
    return isinstance(exc, ksa_exceptions.EndpointNotFound)


def _error_text(exc: Exception) -> str:
    if _is_unavailable(exc):
        return f"{GNOCCHI_UNAVAILABLE}: {exc}"
    return str(exc)


def _failure(exc: Exception) -> dict[str, Any]:
    message = (GNOCCHI_UNAVAILABLE if _is_unavailable(exc)
               else "Gnocchi operation failed")
    return {"success": False, "message": message, "error": _error_text(exc)}


def _owned_resource(client: Any, project_id: str, resource_type: str,
                    resource_id: str) -> dict[str, Any]:
    """Fetch a resource and reject resources outside the current project."""
    resource = client.resource.get(resource_type, resource_id)
    if resource.get("project_id") != project_id:
        raise ValueError("Resource not found in the current project")
    return resource


def _owned_metric(client: Any, project_id: str, metric: str,
                  resource_id: str | None) -> dict[str, Any]:
    """Fetch a metric and confirm its resource or creator is in this project."""
    if resource_id:
        _owned_resource(client, project_id, "generic", resource_id)
        return client.metric.get(metric, resource_id=resource_id)
    found = client.metric.get(metric)
    # Gnocchi embeds the owning resource; metrics are created by the
    # Ceilometer service project, so creator only applies to standalone ones.
    resource = found.get("resource")
    if resource:
        owner = resource.get("project_id")
    else:
        owner = str(found.get("creator", "")).partition(":")[2]
    if owner != project_id:
        raise ValueError("Metric not found in the current project")
    return found


def get_gnocchi_resources(
    resource_type: str = "generic",
    resource_id: str | None = None,
    filters: str | None = None,
    history: bool = False,
    limit: int = 100,
    marker: str | None = None,
) -> dict[str, Any]:
    """List, search, show, or show the history of current-project resources."""
    try:
        _check_limit(limit)
        client, project_id = _context()
        if resource_id:
            resource = _owned_resource(client, project_id, resource_type,
                                       resource_id)
            if not history:
                return {"success": True, "resource": resource}
            revisions = client.resource.history(
                resource_type, resource_id, details=True, limit=limit,
                marker=marker)
            return {"success": True, "resource_id": resource["id"],
                    "history": revisions, "count": len(revisions)}
        conditions = [{"=": {"project_id": project_id}}]
        if filters:
            parsed = json.loads(filters)
            if not isinstance(parsed, dict):
                raise ValueError("filters must be a JSON object")
            conditions += [{"=": {key: value}} for key, value in parsed.items()]
        resources = client.resource.search(
            resource_type=resource_type, query={"and": conditions},
            details=True, limit=limit, marker=marker)
        return {
            "success": True, "resource_type": resource_type,
            "resources": resources, "count": len(resources),
            "next_marker": resources[-1]["id"] if len(resources) == limit else None,
        }
    except Exception as exc:
        return _failure(exc)


def get_gnocchi_metrics(
    resource_id: str | None = None,
    metric: str | None = None,
    resource_type: str = "generic",
    limit: int = 100,
) -> dict[str, Any]:
    """Show one metric, a resource's metrics, or metrics of project resources."""
    try:
        _check_limit(limit)
        client, project_id = _context()
        if metric:
            return {"success": True,
                    "metric": _owned_metric(client, project_id, metric,
                                            resource_id)}
        if resource_id:
            resource = _owned_resource(client, project_id, resource_type,
                                       resource_id)
            metrics = [client.metric.get(metric_id)
                       for metric_id in resource.get("metrics", {}).values()]
            return {"success": True, "resource_id": resource["id"],
                    "metrics": metrics, "count": len(metrics)}
        resources = client.resource.search(
            resource_type=resource_type,
            query={"=": {"project_id": project_id}}, details=True,
            limit=MAX_LIMIT)
        metrics = [
            {"name": name, "id": metric_id, "resource_id": resource["id"],
             "resource_type": resource.get("type"),
             "original_resource_id": resource.get("original_resource_id")}
            for resource in resources
            for name, metric_id in sorted(resource.get("metrics", {}).items())
        ]
        return {"success": True, "metrics": metrics[:limit],
                "count": min(len(metrics), limit), "total": len(metrics),
                "truncated": len(metrics) > limit
                or len(resources) == MAX_LIMIT}
    except Exception as exc:
        return _failure(exc)


def get_gnocchi_measures(
    metric: str,
    resource_id: str | None = None,
    start: str | None = None,
    stop: str | None = None,
    granularity: float | None = None,
    aggregation: str = "mean",
    resample: float | None = None,
    refresh: bool = False,
    limit: int = 100,
) -> dict[str, Any]:
    """Return the latest stored measures for a current-project metric."""
    try:
        if not metric or not metric.strip():
            raise ValueError("metric is required")
        _check_limit(limit)
        client, project_id = _context()
        _owned_metric(client, project_id, metric, resource_id)
        measures = client.metric.get_measures(
            metric, start=start, stop=stop, aggregation=aggregation,
            granularity=granularity, resource_id=resource_id,
            refresh=refresh, resample=resample)
        rows = [
            [ts.isoformat() if isinstance(ts, datetime) else ts, step, value]
            for ts, step, value in measures
        ]
        return {
            "success": True, "metric": metric, "resource_id": resource_id,
            "aggregation": aggregation, "columns": ["timestamp", "granularity",
                                                    "value"],
            "measures": rows[-limit:], "count": min(len(rows), limit),
            "total": len(rows), "truncated": len(rows) > limit,
        }
    except Exception as exc:
        return _failure(exc)


def get_gnocchi_service_info(sections: str | None = None) -> dict[str, Any]:
    """Read archive policies, rules, resource types, capabilities and status."""
    try:
        requested = ([s.strip() for s in sections.split(",") if s.strip()]
                     if sections else list(SERVICE_INFO_SECTIONS))
        unknown = set(requested) - set(SERVICE_INFO_SECTIONS)
        if unknown or not requested:
            raise ValueError("sections must be a comma-separated subset of: "
                             + ", ".join(SERVICE_INFO_SECTIONS))
        client, _ = _context()
        readers = {
            "archive_policies": client.archive_policy.list,
            "archive_policy_rules": client.archive_policy_rule.list,
            "resource_types": client.resource_type.list,
            "capabilities": client.capabilities.list,
            "status": client.status.get,
        }
        data: dict[str, Any] = {}
        errors: dict[str, str] = {}
        for section in requested:
            try:
                data[section] = readers[section]()
            except Exception as exc:
                errors[section] = _error_text(exc)
        return {"success": bool(data), "partial": bool(errors and data),
                "sections": data, "errors": errors}
    except Exception as exc:
        return _failure(exc)


def _token(value: str, field: str) -> str:
    if not _TOKEN.match(value):
        raise ValueError(f"{field} must be a single name without spaces or "
                         "parentheses")
    return value


def _build_operations(metric: str | None, aggregation: str,
                      reaggregation: str | None,
                      operations: str | None) -> str:
    """Build a Gnocchi operations expression from one of the two input modes."""
    if operations:
        if metric or reaggregation:
            raise ValueError("Use either metric/aggregation/reaggregation or "
                             "operations, not both")
        expression = operations.strip()
        if len(expression) > MAX_OPERATIONS_LENGTH:
            raise ValueError("operations is too long")
        depth = 0
        for char in expression:
            depth += {"(": 1, ")": -1}.get(char, 0)
            if depth < 0:
                break
        if not expression.startswith("(") or depth != 0:
            raise ValueError("operations must be one balanced expression such "
                             "as (metric cpu rate:mean)")
        return expression
    if not metric:
        raise ValueError("metric or operations is required")
    expression = (f"(metric {_token(metric, 'metric')} "
                  f"{_token(aggregation, 'aggregation')})")
    if reaggregation:
        expression = (f"(aggregate {_token(reaggregation, 'reaggregation')} "
                      f"{expression})")
    return expression


def _series(measures: dict[str, Any], path: tuple[str, ...] = ()) -> list:
    """Flatten Gnocchi aggregate measures into labeled series."""
    found = []
    for key, value in measures.items():
        if isinstance(value, dict):
            found += _series(value, path + (key,))
            continue
        labels = path + (key,)
        entry: dict[str, Any] = {"label": "/".join(labels)}
        if len(labels) == 3:
            entry.update(resource_id=labels[0], metric=labels[1],
                         aggregation=labels[2])
        # Gnocchi returns NaN for unfilled gaps; NaN is not valid JSON.
        rows = [[ts.isoformat() if isinstance(ts, datetime) else ts, step,
                 None if isinstance(point, float) and math.isnan(point)
                 else point] for ts, step, point in value]
        entry["rows"] = rows
        found.append(entry)
    return found


def _collect(response: dict[str, Any], group: dict | None) -> list:
    names = {ref.get("id"): ref.get("display_name") or ref.get("name")
             for ref in response.get("references") or []
             if isinstance(ref, dict)}
    collected = []
    for entry in _series(response.get("measures") or {}):
        if group is not None:
            entry["group"] = group
        if names.get(entry.get("resource_id")):
            entry["resource_name"] = names[entry["resource_id"]]
        collected.append(entry)
    return collected


def get_gnocchi_aggregates(
    metric: str | None = None,
    aggregation: str = "mean",
    reaggregation: str | None = None,
    operations: str | None = None,
    resource_type: str = "instance",
    filters: str | None = None,
    groupby: str | None = None,
    top: int = 0,
    start: str | None = None,
    stop: str | None = None,
    granularity: float | None = None,
    fill: str | None = None,
    needed_overlap: float | None = None,
    limit: int = 20,
) -> dict[str, Any]:
    """Aggregate measures across current-project resources."""
    try:
        _check_limit(limit)
        if not 0 <= top <= MAX_TOP:
            raise ValueError(f"top must be between 0 and {MAX_TOP}")
        expression = _build_operations(metric, aggregation, reaggregation,
                                       operations)
        _token(resource_type, "resource_type")
        groups = ([_token(g.strip(), "groupby") for g in groupby.split(",")
                   if g.strip()] if groupby else None)
        conditions: list[dict[str, Any]] = []
        if filters:
            parsed = json.loads(filters)
            if not isinstance(parsed, dict):
                raise ValueError("filters must be a JSON object")
            conditions = [{"=": {key: value}} for key, value in parsed.items()]
        fill_value: Any = None
        if fill in ("null", "dropna"):
            fill_value = fill
        elif fill not in (None, ""):
            fill_value = float(fill)
        client, project_id = _context()
        # The project condition is always applied. With a search, Gnocchi
        # resolves (metric X ...) as metric names of matched resources only.
        search = {"and": [{"=": {"project_id": project_id}}] + conditions}
        response = client.aggregates.fetch(
            expression, search=search, resource_type=resource_type,
            start=start, stop=stop, granularity=granularity,
            needed_overlap=needed_overlap, groupby=groups,
            fill=fill_value, details=True)
        if groups:
            series = [entry for item in response
                      for entry in _collect(item.get("measures") or {},
                                            item.get("group"))]
        else:
            series = _collect(response, None)
        for entry in series:
            values = [row[2] for row in entry["rows"] if row[2] is not None]
            entry["latest"] = values[-1] if values else None
            entry["total"] = len(entry["rows"])
            entry["rows"] = entry["rows"][-limit:]
        total_series = len(series)
        if top:
            series = sorted(
                (s for s in series if s["latest"] is not None),
                key=lambda s: s["latest"], reverse=True)[:top]
        truncated = len(series) > MAX_SERIES
        series = series[:MAX_SERIES]
        return {
            "success": True, "operations": expression,
            "resource_type": resource_type, "groupby": groups,
            "ranked_by": "latest value, highest first" if top else None,
            "columns": ["timestamp", "granularity", "value"],
            "series": series, "series_count": len(series),
            "total_series": total_series, "truncated": truncated,
        }
    except Exception as exc:
        result = _failure(exc)
        if not _is_unavailable(exc):
            result["hint"] = AGGREGATES_HINT
        return result
