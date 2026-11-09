"""Read-only, project-scoped Gnocchi (metric service) operations."""

import json
from datetime import datetime
from typing import Any

from gnocchiclient.v1 import client as gnocchi_client

from ..connection import get_openstack_connection

MAX_LIMIT = 1000
SERVICE_INFO_SECTIONS = (
    "archive_policies", "archive_policy_rules", "resource_types",
    "capabilities", "status",
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


def _failure(exc: Exception) -> dict[str, Any]:
    return {"success": False, "message": "Gnocchi operation failed",
            "error": str(exc)}


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
                errors[section] = str(exc)
        return {"success": bool(data), "partial": bool(errors and data),
                "sections": data, "errors": errors}
    except Exception as exc:
        return _failure(exc)
