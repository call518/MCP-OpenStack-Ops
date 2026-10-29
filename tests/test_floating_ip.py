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
