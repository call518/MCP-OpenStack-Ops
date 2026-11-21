"""Flavor extra specs, server flavor names and microversion discovery redirects."""

import asyncio
import json
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
import requests

from mcp_openstack_ops import user_connection as users
from mcp_openstack_ops.services import compute


# --- RestrictedSession: same-origin redirects only ------------------------

def _response(status, url, location=None):
    response = requests.Response()
    response.status_code = status
    response.url = url
    response.raw = Mock()
    if location:
        response.headers["Location"] = location
    return response


def _session_with(monkeypatch, responses):
    sent = []

    def send(self, request, **kwargs):
        sent.append((request.method, request.url, dict(request.headers),
                     kwargs.get("allow_redirects")))
        return responses.pop(0)

    monkeypatch.setattr(requests.Session, "send", send)
    return users.RestrictedSession("https"), sent


def _get(url, method="GET"):
    return requests.Request(method, url, headers={"X-Auth-Token": "token"}).prepare()


def test_same_origin_get_redirect_is_followed_with_the_token(monkeypatch):
    session, sent = _session_with(monkeypatch, [
        _response(302, "https://nova.example/v2.1", "https://nova.example/v2.1/"),
        _response(200, "https://nova.example/v2.1/"),
    ])
    response = session.send(_get("https://nova.example/v2.1"))
    assert response.status_code == 200
    assert [url for _, url, _, _ in sent] == [
        "https://nova.example/v2.1", "https://nova.example/v2.1/"]
    assert all(headers["X-Auth-Token"] == "token" for _, _, headers, _ in sent)
    assert all(allow is False for *_, allow in sent)


def test_relative_and_default_port_redirects_count_as_same_origin(monkeypatch):
    session, sent = _session_with(monkeypatch, [
        _response(301, "https://nova.example/v2.1", "/v2.1/"),
        _response(302, "https://nova.example/v2.1/", "https://NOVA.example:443/v2.1/x"),
        _response(200, "https://nova.example:443/v2.1/x"),
    ])
    assert session.send(_get("https://nova.example/v2.1")).status_code == 200
    assert len(sent) == 3


@pytest.mark.parametrize("location", [
    "https://attacker.example/v2.1/",      # other host
    "https://nova.example:8443/v2.1/",     # other port
    "http://nova.example/v2.1/",           # downgrade
])
def test_cross_origin_redirect_is_returned_not_followed(monkeypatch, location):
    session, sent = _session_with(monkeypatch, [
        _response(302, "https://nova.example/v2.1", location),
    ])
    response = session.send(_get("https://nova.example/v2.1"))
    assert response.status_code == 302
    assert len(sent) == 1


def test_non_get_redirect_is_not_followed(monkeypatch):
    session, sent = _session_with(monkeypatch, [
        _response(307, "https://nova.example/servers", "https://nova.example/servers/"),
    ])
    assert session.send(_get("https://nova.example/servers", "POST")).status_code == 307
    assert len(sent) == 1


def test_redirect_loop_stops_after_the_hop_limit(monkeypatch):
    loop = [_response(302, "https://nova.example/a", "https://nova.example/a")
            for _ in range(10)]
    session, sent = _session_with(monkeypatch, loop)
    assert session.send(_get("https://nova.example/a")).status_code == 302
    assert len(sent) == 1 + users._MAX_SAME_ORIGIN_REDIRECTS


def test_plain_http_is_still_rejected_before_sending(monkeypatch):
    session, sent = _session_with(monkeypatch, [])
    with pytest.raises(ValueError, match="require HTTPS"):
        session.send(_get("http://nova.example/v2.1"))
    assert sent == []


# --- Flavor extra specs and accelerators ----------------------------------

def _flavor(name="f", specs=None, microversion=None, **sizes):
    return SimpleNamespace(
        id=f"id-{name}", name=name, extra_specs=specs or {}, microversion=microversion,
        vcpus=sizes.get("vcpus", 1), ram=sizes.get("ram", 1024), disk=0, ephemeral=0,
        swap=0, rxtx_factor=1.0, is_public=True, description=None)


def test_listed_extra_specs_are_used_without_another_request():
    conn = Mock()
    specs, error = compute._flavor_extra_specs(conn, _flavor(specs={"a": "1"}))
    assert (specs, error) == ({"a": "1"}, None)
    conn.compute.fetch_flavor_extra_specs.assert_not_called()


def test_empty_specs_at_2_61_mean_none_set():
    conn = Mock()
    assert compute._flavor_extra_specs(conn, _flavor(microversion="2.96")) == ({}, None)
    conn.compute.fetch_flavor_extra_specs.assert_not_called()


@pytest.mark.parametrize("microversion", [None, "2.1", "2.60"])
def test_specs_missing_from_older_lists_are_fetched(microversion):
    conn = Mock()
    conn.compute.fetch_flavor_extra_specs.return_value = SimpleNamespace(
        extra_specs={"pci_passthrough:alias": "gpu:2"})
    specs, error = compute._flavor_extra_specs(conn, _flavor(microversion=microversion))
    assert specs == {"pci_passthrough:alias": "gpu:2"} and error is None


def test_unreadable_specs_are_null_with_an_error_not_empty():
    conn = Mock()
    conn.compute.fetch_flavor_extra_specs.side_effect = RuntimeError("403")
    specs, error = compute._flavor_extra_specs(conn, _flavor())
    assert specs is None and "403" in error


@pytest.mark.parametrize("specs, expected", [
    ({"pci_passthrough:alias": "gpu_h200:4"},
     [{"type": "pci_passthrough", "alias": "gpu_h200", "count": 4}]),
    ({"pci_passthrough:alias": "a:1, b"},
     [{"type": "pci_passthrough", "alias": "a", "count": 1},
      {"type": "pci_passthrough", "alias": "b", "count": 1}]),
    ({"resources:VGPU": "1"}, [{"type": "vgpu", "count": 1}]),
    ({"resources1:PGPU": "2"}, [{"type": "pgpu", "count": 2}]),
    ({"hw:mem_page_size": "1GB"}, []),
    (None, []),
])
def test_accelerators_are_parsed_from_extra_specs(specs, expected):
    assert compute._flavor_accelerators(specs) == expected


def _patch_flavors(monkeypatch, flavors, fetched=None, fail=False):
    conn = Mock()
    conn.compute.flavors.return_value = flavors
    if fail:
        conn.compute.fetch_flavor_extra_specs.side_effect = RuntimeError("denied")
    else:
        conn.compute.fetch_flavor_extra_specs.side_effect = (
            lambda f: SimpleNamespace(extra_specs=(fetched or {}).get(f.name, {})))
    monkeypatch.setattr("mcp_openstack_ops.connection.get_openstack_connection",
                        lambda: conn)
    return conn


def test_get_flavor_list_reports_fetched_specs_and_accelerators(monkeypatch):
    _patch_flavors(monkeypatch, [_flavor("gpu4"), _flavor("small")],
                   fetched={"gpu4": {"pci_passthrough:alias": "gpu_h200:4"}})
    rows = {row["name"]: row for row in compute.get_flavor_list()}
    assert rows["gpu4"]["accelerators"][0]["count"] == 4
    assert rows["small"]["extra_specs"] == {} and rows["small"]["accelerators"] == []
    assert "extra_specs_error" not in rows["small"]


def test_get_flavors_tool_filters_sorts_and_warns(monkeypatch):
    from mcp_openstack_ops.tools.get_flavors import get_flavors
    _patch_flavors(monkeypatch, [
        _flavor("c08m16", vcpus=8, microversion="2.96"),
        _flavor("c120m1900g04", specs={"pci_passthrough:alias": "gpu_h200:4"}, vcpus=120),
        _flavor("c01m01", vcpus=1, microversion="2.96"),
    ])
    result = json.loads(asyncio.run(get_flavors()))
    assert [f["name"] for f in result["flavors"]] == ["c01m01", "c08m16", "c120m1900g04"]
    assert "warning" not in result
    gpus = json.loads(asyncio.run(get_flavors(accelerators_only=True)))
    assert [f["name"] for f in gpus["flavors"]] == ["c120m1900g04"]
    named = json.loads(asyncio.run(get_flavors(name_contains="M16")))
    assert [f["name"] for f in named["flavors"]] == ["c08m16"]

    _patch_flavors(monkeypatch, [_flavor("x")], fail=True)
    unreadable = json.loads(asyncio.run(get_flavors()))
    assert unreadable["flavors"][0]["extra_specs"] is None
    assert "could not be read" in unreadable["warning"]


# --- Server flavor names ---------------------------------------------------

def test_embedded_flavor_name_and_sizes_are_used():
    server = SimpleNamespace(flavor={"original_name": "c04m08", "vcpus": 4,
                                     "ram": 8192, "disk": 0})
    conn = Mock()
    info = compute._server_flavor_info(conn, server, {})
    assert info == {"id": None, "name": "c04m08", "vcpus": 4, "ram": 8192, "disk": 0}
    conn.compute.get_flavor.assert_not_called()


def test_id_only_flavor_is_looked_up_once_per_id():
    conn = Mock()
    conn.compute.get_flavor.return_value = SimpleNamespace(
        name="c08m16", vcpus=8, ram=16384, disk=0)
    cache = {}
    servers = [SimpleNamespace(flavor=SimpleNamespace(
        id="f1", original_name=None, name=None, vcpus=0, ram=0, disk=0))
        for _ in range(3)]
    infos = [compute._server_flavor_info(conn, s, cache) for s in servers]
    assert all(i == {"id": "f1", "name": "c08m16", "vcpus": 8, "ram": 16384, "disk": 0}
               for i in infos)
    conn.compute.get_flavor.assert_called_once_with("f1")


def test_unresolvable_flavor_reports_null_sizes_not_zero():
    conn = Mock()
    conn.compute.get_flavor.side_effect = RuntimeError("not found")
    server = SimpleNamespace(flavor={"id": "gone", "vcpus": 0, "ram": 0, "disk": 0})
    info = compute._server_flavor_info(conn, server, {})
    assert info == {"id": "gone", "name": None, "vcpus": None, "ram": None, "disk": None}


def test_missing_flavor_is_all_null():
    info = compute._server_flavor_info(Mock(), SimpleNamespace(flavor=None), {})
    assert set(info.values()) == {None}
