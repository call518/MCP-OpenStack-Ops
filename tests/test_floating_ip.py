"""Regression tests for floating IP allocation through the MCP tool."""

import asyncio
import importlib
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

import mcp_openstack_ops.mcp_main  # Register tools before importing a tool module.


@pytest.mark.parametrize("action", ["create", "allocate"])
@pytest.mark.parametrize("network_id", ["external-network-id", "  external-network-id  "])
def test_allocate_floating_ip(
    action: str, network_id: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    tool = importlib.import_module("mcp_openstack_ops.tools.set_floating_ip")
    connection = importlib.import_module("mcp_openstack_ops.connection")
    network = Mock()
    network.networks.return_value = [
        SimpleNamespace(
            id="external-network-id", name="public", is_router_external=True
        )
    ]
    network.create_ip.return_value = SimpleNamespace(
        id="floating-ip-id",
        floating_ip_address="192.0.2.1",
        status="DOWN",
        floating_network_id="external-network-id",
    )
    monkeypatch.setattr(
        connection, "get_openstack_connection", lambda: SimpleNamespace(network=network)
    )
    monkeypatch.setattr(tool, "handle_operation_result", lambda result, *args: result)
    handler = getattr(tool.set_floating_ip, "fn", tool.set_floating_ip)

    result = asyncio.run(handler(action=action, floating_network_id=network_id))

    assert result["success"] is True, result
    assert result["floating_ip"]["id"] == "floating-ip-id"
    network.create_ip.assert_called_once_with(floating_network_id="external-network-id")


@pytest.mark.asyncio
@pytest.mark.parametrize("action", ["create", "allocate"])
async def test_multi_user_allocation_uses_callers_connection(monkeypatch, action):
    import httpx
    from starlette.responses import JSONResponse

    from mcp_openstack_ops import user_connection as users

    tool = importlib.import_module("mcp_openstack_ops.tools.set_floating_ip")
    monkeypatch.setattr(users, "enabled", True)
    identities = {}
    for name in ("alice", "bob"):
        conn = Mock(current_project_id=f"project-{name}")
        conn.network.networks.return_value = [
            SimpleNamespace(id=f"network-{name}", is_router_external=True)
        ]
        conn.network.create_ip.return_value = SimpleNamespace(
            id=f"ip-{name}", floating_ip_address="192.0.2.1", status="DOWN",
            floating_network_id=f"network-{name}",
        )
        identities[name] = users.RequestIdentity(
            conn, name, f"project-{name}", (name, "test-secret")
        )
    monkeypatch.setattr(users, "authenticate", lambda key, secret: identities[key])
    monkeypatch.setattr(tool, "handle_operation_result", lambda result, *args: result)
    handler = getattr(tool.set_floating_ip, "fn", tool.set_floating_ip)

    async def app(scope, receive, send):
        name = users._identity.get().user_id
        result = await handler(
            action=action, floating_network_id=f" network-{name} "
        )
        await JSONResponse(result)(scope, receive, send)

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=users.UserConnectionMiddleware(app)),
        base_url="https://mcp.example",
    ) as client:
        replies = await asyncio.gather(*[
            client.post("/mcp", headers={
                "X-OpenStack-Application-Credential-ID": name,
                "X-OpenStack-Application-Credential-Secret": "test-secret",
            }) for name in identities
        ])
    for name, reply in zip(identities, replies):
        assert reply.status_code == 200
        assert reply.json()["success"] is True
        assert reply.json()["floating_ip"]["id"] == f"ip-{name}"
        conn = identities[name].connection
        conn.network.create_ip.assert_called_once_with(
            floating_network_id=f"network-{name}"
        )
        conn.close.assert_called_once()
        conn.session.session.close.assert_called_once()
    assert users._identity.get() is None
