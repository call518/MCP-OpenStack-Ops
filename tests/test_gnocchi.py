"""Unit tests for read-only, project-scoped Gnocchi operations."""

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from mcp_openstack_ops.services import gnocchi

OWN = {"id": "res-a", "project_id": "project-a", "type": "instance",
       "original_resource_id": "res-a", "metrics": {"cpu": "m-cpu",
                                                     "memory.usage": "m-mem"}}
OTHER = {"id": "res-b", "project_id": "project-b", "metrics": {}}


@pytest.fixture
def client(monkeypatch):
    conn = SimpleNamespace(current_project_id="project-a", session=Mock(),
                           config=Mock(region_name="RegionOne"))
    conn.config.get_interface.return_value = "internal"
    api = Mock()
    factory = Mock(return_value=api)
    monkeypatch.setattr(gnocchi, "get_openstack_connection", lambda: conn)
    monkeypatch.setattr(gnocchi.gnocchi_client, "Client", factory)
    api.resource.get.side_effect = lambda _type, rid: {
        "res-a": OWN, "res-b": OTHER}[rid]
    api.factory = factory
    return api


def test_client_uses_session_interface_and_region(client):
    client.capabilities.list.return_value = {"aggregation_methods": ["mean"]}
    gnocchi.get_gnocchi_service_info("capabilities")
    kwargs = client.factory.call_args.kwargs
    assert kwargs["adapter_options"] == {"interface": "internal",
                                         "region_name": "RegionOne"}


def test_resource_search_is_project_scoped_with_filters(client):
    client.resource.search.return_value = [OWN]
    result = gnocchi.get_gnocchi_resources(
        "instance", filters='{"display_name": "vm1"}', limit=1)
    query = client.resource.search.call_args.kwargs["query"]
    assert query == {"and": [{"=": {"project_id": "project-a"}},
                             {"=": {"display_name": "vm1"}}]}
    assert result["success"] and result["next_marker"] == "res-a"


@pytest.mark.parametrize("filters", ["[1]", "not-json"])
def test_invalid_filters_fail_without_search(client, filters):
    assert not gnocchi.get_gnocchi_resources(filters=filters)["success"]
    client.resource.search.assert_not_called()


@pytest.mark.parametrize("limit", [0, 1001])
def test_limit_bounds_are_enforced(client, limit):
    assert not gnocchi.get_gnocchi_resources(limit=limit)["success"]
    assert not gnocchi.get_gnocchi_measures("cpu", "res-a", limit=limit)["success"]
    client.factory.assert_not_called()


def test_resource_in_other_project_is_rejected(client):
    result = gnocchi.get_gnocchi_resources(resource_id="res-b")
    assert not result["success"]
    assert "current project" in result["error"]


def test_resource_history_after_ownership_check(client):
    client.resource.history.return_value = [OWN, OWN]
    result = gnocchi.get_gnocchi_resources("instance", "res-a", history=True)
    assert result["count"] == 2
    client.resource.history.assert_called_once_with(
        "instance", "res-a", details=True, limit=100, marker=None)


def test_metrics_for_resource_are_detailed(client):
    client.metric.get.side_effect = lambda mid, **_: {"id": mid}
    result = gnocchi.get_gnocchi_metrics(resource_id="res-a")
    assert {m["id"] for m in result["metrics"]} == {"m-cpu", "m-mem"}


def test_metric_listing_flattens_project_resources(client):
    client.resource.search.return_value = [OWN]
    result = gnocchi.get_gnocchi_metrics(limit=1)
    assert result["metrics"][0]["name"] == "cpu"
    assert result["total"] == 2 and result["truncated"]


@pytest.mark.parametrize("found, ok", [
    # Real Gnocchi responses embed the resource; creator is the Ceilometer
    # service project and must not decide ownership of attached metrics.
    ({"id": "m", "creator": "ceilo:service",
      "resource": {"id": "res-a", "project_id": "project-a"}}, True),
    ({"id": "m", "creator": "user:project-a",
      "resource": {"id": "res-b", "project_id": "project-b"}}, False),
    ({"id": "m", "resource": None, "creator": "user:project-a"}, True),
    ({"id": "m", "resource": None, "creator": "user:project-b"}, False),
])
def test_metric_by_id_checks_project_ownership(client, found, ok):
    client.metric.get.return_value = found
    assert gnocchi.get_gnocchi_metrics(metric="m")["success"] is ok


def test_measures_return_latest_rows(client):
    stamp = datetime(2026, 1, 1, tzinfo=timezone.utc)
    client.metric.get.return_value = {"id": "m-cpu"}
    client.metric.get_measures.return_value = [
        (stamp, 300.0, 1.0), ("2026-01-01T00:05:00+00:00", 300.0, 2.0)]
    result = gnocchi.get_gnocchi_measures(
        "cpu", "res-a", start="2026-01-01T00:00:00", granularity=300, limit=1)
    assert result["measures"] == [["2026-01-01T00:05:00+00:00", 300.0, 2.0]]
    assert result["total"] == 2 and result["truncated"]
    client.metric.get_measures.assert_called_once_with(
        "cpu", start="2026-01-01T00:00:00", stop=None, aggregation="mean",
        granularity=300, resource_id="res-a", refresh=False, resample=None)


def test_measures_rejected_for_other_project(client):
    result = gnocchi.get_gnocchi_measures("cpu", "res-b")
    assert not result["success"]
    client.metric.get_measures.assert_not_called()


def test_service_info_reports_partial_section_failure(client):
    client.archive_policy.list.return_value = [{"name": "low"}]
    client.status.get.side_effect = RuntimeError("403 Forbidden")
    result = gnocchi.get_gnocchi_service_info("archive_policies,status")
    assert result["success"] and result["partial"]
    assert result["errors"] == {"status": "403 Forbidden"}


def test_service_info_rejects_unknown_section(client):
    assert not gnocchi.get_gnocchi_service_info("bogus")["success"]
    client.factory.assert_not_called()


STAMP = datetime(2026, 1, 1, tzinfo=timezone.utc)
PER_RESOURCE = {
    "measures": {
        "res-a": {"cpu": {"rate:mean": [(STAMP, 300.0, 5.0)]}},
        "res-c": {"cpu": {"rate:mean": [(STAMP, 300.0, 9.0)]}},
        "res-d": {"cpu": {"rate:mean": [(STAMP, 300.0, None)]}},
    },
    "references": [{"id": "res-a", "display_name": "vm-a"},
                   {"id": "res-c", "display_name": "vm-c"}],
}


def test_aggregates_simple_mode_builds_expression_and_scopes_project(client):
    client.aggregates.fetch.return_value = {
        "measures": {"aggregated": [(STAMP, 300.0, 7.0)]}}
    result = gnocchi.get_gnocchi_aggregates(
        "cpu", "rate:mean", "mean", filters='{"flavor_name": "m1.small"}')
    args, kwargs = client.aggregates.fetch.call_args
    assert args[0] == "(aggregate mean (metric cpu rate:mean))"
    assert kwargs["search"] == {"and": [{"=": {"project_id": "project-a"}},
                                        {"=": {"flavor_name": "m1.small"}}]}
    assert result["operations"] == args[0]
    assert result["series"][0]["label"] == "aggregated"
    assert result["series"][0]["latest"] == 7.0


def test_aggregates_expression_mode_is_still_project_scoped(client):
    client.aggregates.fetch.return_value = {"measures": {}}
    expression = "(metric 00000000-0000-0000-0000-000000000000 mean)"
    gnocchi.get_gnocchi_aggregates(operations=expression)
    args, kwargs = client.aggregates.fetch.call_args
    assert args[0] == expression
    assert kwargs["search"]["and"][0] == {"=": {"project_id": "project-a"}}


def test_aggregates_top_ranks_latest_values_and_names_resources(client):
    client.aggregates.fetch.return_value = PER_RESOURCE
    result = gnocchi.get_gnocchi_aggregates("cpu", "rate:mean", top=1)
    assert [s["resource_id"] for s in result["series"]] == ["res-c"]
    assert result["series"][0]["resource_name"] == "vm-c"
    assert result["total_series"] == 3 and result["ranked_by"]


def test_aggregates_nan_gaps_become_null_and_are_not_ranked(client):
    client.aggregates.fetch.return_value = {"measures": {
        "res-a": {"cpu": {"rate:mean": [(STAMP, 300.0, 5.0)]}},
        "res-c": {"cpu": {"rate:mean": [(STAMP, 300.0, 3.0),
                                        (STAMP, 300.0, float("nan"))]}}}}
    result = gnocchi.get_gnocchi_aggregates("cpu", "rate:mean", top=2)
    assert [s["latest"] for s in result["series"]] == [5.0, 3.0]
    assert result["series"][1]["rows"][-1][2] is None


def test_aggregates_accepts_metric_names_with_symbols(client):
    client.aggregates.fetch.return_value = {"measures": {}}
    gnocchi.get_gnocchi_aggregates("demo.queue_depth|g")
    assert client.aggregates.fetch.call_args.args[0] == (
        "(metric demo.queue_depth|g mean)")


def test_aggregates_groupby_collects_each_group(client):
    client.aggregates.fetch.return_value = [
        {"group": {"flavor_name": "m1.small"},
         "measures": {"measures": {"aggregated": [(STAMP, 300.0, 1.0)]}}},
        {"group": {"flavor_name": "m1.large"},
         "measures": {"measures": {"aggregated": [(STAMP, 300.0, 2.0)]}}},
    ]
    result = gnocchi.get_gnocchi_aggregates(
        "memory.usage", reaggregation="mean", groupby="flavor_name")
    assert client.aggregates.fetch.call_args.kwargs["groupby"] == ["flavor_name"]
    assert [s["group"]["flavor_name"] for s in result["series"]] == [
        "m1.small", "m1.large"]


def test_aggregates_fill_zero_is_forwarded(client):
    client.aggregates.fetch.return_value = {"measures": {}}
    gnocchi.get_gnocchi_aggregates("cpu", fill="0")
    assert client.aggregates.fetch.call_args.kwargs["fill"] == 0.0


@pytest.mark.parametrize("kwargs", [
    {},
    {"metric": "cpu", "operations": "(metric cpu mean)"},
    {"metric": "cpu mean) (metric x"},
    {"metric": "cpu", "reaggregation": "mean)"},
    {"operations": "(metric cpu mean"},
    {"operations": "metric cpu mean"},
    {"operations": "(metric cpu mean))("},
    {"metric": "cpu", "groupby": "flavor name"},
    {"metric": "cpu", "top": 101},
    {"metric": "cpu", "filters": "[]"},
])
def test_aggregates_invalid_input_fails_before_cloud_call(client, kwargs):
    result = gnocchi.get_gnocchi_aggregates(**kwargs)
    assert not result["success"] and result["hint"]
    client.factory.assert_not_called()


def test_aggregates_failure_includes_hint(client):
    client.aggregates.fetch.side_effect = RuntimeError("No overlap")
    result = gnocchi.get_gnocchi_aggregates("cpu", reaggregation="mean")
    assert result["error"] == "No overlap" and "fill" in result["hint"]


def test_missing_endpoint_is_reported_as_failure(client):
    client.resource.search.side_effect = RuntimeError("endpoint not found")
    result = gnocchi.get_gnocchi_resources()
    assert result == {"success": False, "message": "Gnocchi operation failed",
                      "error": "endpoint not found"}


def _no_metric_endpoint():
    from keystoneauth1 import exceptions as ksa_exceptions
    return ksa_exceptions.EndpointNotFound(
        "internal endpoint for metric service in RegionOne region not found")


def test_missing_metric_service_is_named(client):
    client.resource.search.side_effect = _no_metric_endpoint()
    result = gnocchi.get_gnocchi_resources()
    assert result["success"] is False
    assert result["message"] == gnocchi.GNOCCHI_UNAVAILABLE
    assert result["error"].startswith(gnocchi.GNOCCHI_UNAVAILABLE + ": ")
    assert "metric service" in result["error"]


def test_missing_metric_service_in_service_info_sections(client):
    client.status.get.side_effect = _no_metric_endpoint()
    result = gnocchi.get_gnocchi_service_info("status")
    assert result["success"] is False
    assert result["errors"]["status"].startswith(gnocchi.GNOCCHI_UNAVAILABLE)


def test_missing_metric_service_aggregates_has_no_metric_hint(client):
    client.aggregates.fetch.side_effect = _no_metric_endpoint()
    result = gnocchi.get_gnocchi_aggregates("cpu", reaggregation="mean")
    assert result["message"] == gnocchi.GNOCCHI_UNAVAILABLE
    assert "hint" not in result
