"""Project-scoped Aodh alarm operations using the authenticated service catalog."""

import math
from typing import Any
from urllib.parse import quote

from keystoneauth1.adapter import Adapter

from ..connection import get_openstack_connection


def set_alarms(
    action: str,
    alarm_name: str | None = None,
    resource_id: str | None = None,
    threshold: float | None = None,
    comparison: str = "gt",
    metric: str = "cpu_util",
    resource_type: str = "instance",
    aggregation_method: str = "mean",
    granularity: int = 300,
    evaluation_periods: int = 1,
    alarm_actions: list[str] | None = None,
) -> dict[str, Any]:
    """List, create, show or delete real Gnocchi resource threshold alarms.

    Requires an alarming endpoint and Aodh/Gnocchi in the target cloud.
    """
    try:
        action = action.lower()
        if action not in {"list", "create", "show", "delete"}:
            raise ValueError("Supported actions: list, create, show, delete")
        if action != "list" and not (alarm_name and alarm_name.strip()):
            raise ValueError("alarm_name is required")
        if action == "create":
            if not resource_id or not metric or not resource_type:
                raise ValueError("resource_id, metric and resource_type are required")
            if threshold is None or not math.isfinite(threshold):
                raise ValueError("A finite threshold is required")
            if comparison not in {"gt", "lt", "eq", "ne", "ge", "le"}:
                raise ValueError("Invalid comparison operator")
            if granularity <= 0 or evaluation_periods <= 0:
                raise ValueError("granularity and evaluation_periods must be positive")
        conn = get_openstack_connection()
        project_id = conn.current_project_id
        if not project_id:
            raise ValueError("A project-scoped connection is required")
        api = Adapter(
            session=conn.session, service_type="alarming",
            interface=conn.config.get_interface(),
            region_name=conn.config.region_name,
        )
        if action == "create":
            body = {
                "name": alarm_name, "type": "gnocchi_resources_threshold",
                "project_id": project_id, "enabled": True,
                "alarm_actions": alarm_actions or [],
                "gnocchi_resources_threshold_rule": {
                    "resource_id": resource_id, "resource_type": resource_type,
                    "metric": metric, "threshold": threshold,
                    "comparison_operator": comparison,
                    "aggregation_method": aggregation_method,
                    "granularity": granularity,
                    "evaluation_periods": evaluation_periods,
                },
            }
            response = api.post("/v2/alarms", json=body)
            response.raise_for_status()
            return {"success": True, "alarm": response.json()}
        params = {
            "q.field": "project_id", "q.op": "eq", "q.value": project_id,
            "limit": 100,
        }
        alarms = []
        seen = set()
        while True:
            response = api.get("/v2/alarms", params=dict(params))
            response.raise_for_status()
            page = response.json()
            ids = [alarm["alarm_id"] for alarm in page]
            if len(set(ids)) != len(ids) or seen.intersection(ids):
                raise ValueError("Alarm pagination repeated an alarm")
            seen.update(ids)
            alarms.extend(a for a in page if a.get("project_id") == project_id)
            if len(page) < 100:
                break
            params['marker'] = ids[-1]
        if action == "list":
            return {"success": True, "alarms": alarms, "count": len(alarms)}
        matches = [a for a in alarms if a.get("alarm_id") == alarm_name]
        if not matches:
            matches = [a for a in alarms if a.get("name") == alarm_name]
        if len(matches) != 1:
            raise ValueError("Alarm not found or name is ambiguous; use an alarm ID")
        alarm = matches[0]
        path = "/v2/alarms/" + quote(alarm["alarm_id"], safe="")
        if action == "show":
            response = api.get(path)
            response.raise_for_status()
            return {"success": True, "alarm_details": response.json()}
        response = api.delete(path)
        response.raise_for_status()
        return {"success": True, "message": "Alarm deletion accepted",
            "alarm_id": alarm["alarm_id"]}
    except Exception as exc:
        return {"success": False, "message": "Aodh alarm operation failed",
            "error": str(exc)}
