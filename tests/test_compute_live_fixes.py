"""Regressions for compute defects observed live on OpenStack 2026.1.

Proxies are ``create_autospec`` of the real openstacksdk proxies, so a call
with the wrong signature fails exactly as it did against the live cloud.
"""

import importlib
import inspect
import json
from types import SimpleNamespace
from unittest.mock import Mock, create_autospec

import pytest
from fastmcp.exceptions import ToolError
from openstack import exceptions as sdk_exceptions
from openstack.compute.v2._proxy import Proxy as ComputeProxy
from openstack.compute.v2.server import Server
from openstack.compute.v2.server_interface import ServerInterface
from openstack.image.v2._proxy import Proxy as ImageProxy
from openstack.image.v2.image import Image
from openstack.network.v2._proxy import Proxy as NetworkProxy
from openstack.network.v2.network import Network
from openstack.network.v2.port import Port

from mcp_openstack_ops import connection, functions
import mcp_openstack_ops.mcp_main  # noqa: F401  Register tools first.
from mcp_openstack_ops.services import compute


def _tool_handler(module_name, name):
    module = importlib.import_module(f'mcp_openstack_ops.tools.{module_name}')
    tool = getattr(module, name)
    return module, getattr(tool, 'fn', tool)


@pytest.fixture
def conn(monkeypatch):
    value = SimpleNamespace(
        current_project_id='project-a',
        compute=create_autospec(ComputeProxy, instance=True),
        network=create_autospec(NetworkProxy, instance=True),
        image=create_autospec(ImageProxy, instance=True),
        session=Mock(), config=Mock(region_name='RegionOne'),
    )
    value.compute.servers.return_value = [
        Server.existing(id='s1', name='vm', project_id='project-a')]
    value.compute.server_interfaces.return_value = []
    value.compute.volume_attachments.return_value = []
    value.network.networks.return_value = [
        Network.existing(id='net-0123456789', name='lab-net',
                         project_id='project-a')]
    value.image.images.return_value = [
        Image.existing(id='img-1', name='cirros', visibility='public')]
    monkeypatch.setattr(connection, 'get_openstack_connection', lambda: value)
    monkeypatch.setattr(connection, 'get_current_project_id',
                        lambda: 'project-a')
    monkeypatch.setattr(functions, 'get_openstack_connection', lambda: value)
    return value


# --- 1. rebuild ----------------------------------------------------------

def test_rebuild_passes_image_positionally_with_sdk_attr_names(conn):
    result = compute.set_instance('vm', 'rebuild', image='cirros',
                                  new_name='vm-rebuilt', metadata={},
                                  preserve_ephemeral=False)

    assert result['success'] is True, result
    args, kwargs = conn.compute.rebuild_server.call_args
    assert args[1] == 'img-1'
    assert kwargs == {'name': 'vm-rebuilt', 'preserve_ephemeral': False}
    # Every attr must be a real Server.rebuild() keyword.
    inspect.signature(Server.rebuild).bind(None, None, 'img-1', **kwargs)


# --- 2. console ----------------------------------------------------------

def test_console_uses_remote_consoles_api(conn):
    conn.compute.get_server_console_url.side_effect = (
        sdk_exceptions.NotFoundException('404 /servers/s1/action'))
    conn.compute.create_console.return_value = {
        'type': 'novnc', 'protocol': 'vnc',
        'url': 'https://console.example/vnc_auto.html?token=t'}

    result = compute.set_instance('vm', 'console', type='novnc')

    assert result['success'] is True, result
    assert result['console']['url'].startswith('https://console.example/')
    args, _ = conn.compute.create_console.call_args
    assert args[1] == 'novnc'


# --- 3. add_port / remove_port by name ----------------------------------

def test_add_port_resolves_port_by_name(conn):
    conn.network.get_port.side_effect = sdk_exceptions.NotFoundException()
    conn.network.find_port.return_value = Port.existing(
        id='port-1', name='user-port', project_id='project-a')

    result = compute.set_server_network('vm', 'add_port', port='user-port')

    assert result['success'] is True, result
    conn.compute.create_server_interface.assert_called_once()
    assert (conn.compute.create_server_interface.call_args.kwargs
            == {'port_id': 'port-1'})


def test_remove_port_by_name_detaches_without_deleting_user_port(conn):
    conn.network.find_port.return_value = Port.existing(
        id='port-1', name='user-port', project_id='project-a')
    interface = ServerInterface.existing(port_id='port-1',
                                         net_id='net-0123456789',
                                         server_id='s1')
    conn.compute.server_interfaces.return_value = [interface]

    result = compute.set_server_network('vm', 'remove_port', port='user-port')

    assert result['success'] is True, result
    conn.compute.delete_server_interface.assert_called_once()
    assert conn.compute.delete_server_interface.call_args.args[0] is interface
    conn.network.delete_port.assert_not_called()


# --- 4. Nova-owned ports for add_network / fixed IP add ------------------

def test_add_network_lets_nova_create_the_port(conn):
    conn.compute.create_server_interface.return_value = (
        ServerInterface.existing(port_id='nova-port', net_id='net-0123456789',
                                 server_id='s1'))

    result = compute.set_server_network('vm', 'add_network',
                                        network='lab-net',
                                        fixed_ip='10.0.0.5')

    assert result['success'] is True, result
    assert result['port_id'] == 'nova-port'
    conn.network.create_port.assert_not_called()
    assert conn.compute.create_server_interface.call_args.kwargs == {
        'net_id': 'net-0123456789',
        'fixed_ips': [{'ip_address': '10.0.0.5'}]}


def test_fixed_ip_add_lets_nova_create_the_port(conn):
    conn.compute.create_server_interface.return_value = (
        ServerInterface.existing(port_id='nova-port', net_id='net-0123456789',
                                 server_id='s1',
                                 fixed_ips=[{'ip_address': '10.0.0.7',
                                             'subnet_id': 'sub-1'}]))

    result = compute.set_server_fixed_ip('vm', 'add', network='lab-net')

    assert result['success'] is True, result
    assert result['fixed_ip'] == '10.0.0.7'
    assert result['port_id'] == 'nova-port'
    conn.network.create_port.assert_not_called()
    assert conn.compute.create_server_interface.call_args.kwargs == {
        'net_id': 'net-0123456789'}


# --- 5. get_instances_by_status ------------------------------------------

@pytest.mark.asyncio
async def test_instances_by_invalid_status_returns_explicit_error(conn):
    _, handler = _tool_handler('get_instances_by_status',
                               'get_instances_by_status')

    with pytest.raises(ToolError, match='Invalid instance status') as raised:
        await handler('NOT_A_STATUS')

    assert 'SHUTOFF' in str(raised.value)
    conn.compute.servers.assert_not_called()


@pytest.mark.asyncio
async def test_instances_by_status_failure_is_a_redacted_tool_error(
        conn, monkeypatch):
    module, handler = _tool_handler('get_instances_by_status',
                                    'get_instances_by_status')
    monkeypatch.setattr(module, '_get_instances_by_status',
                        Mock(side_effect=RuntimeError('private detail')))

    with pytest.raises(ToolError) as raised:
        await handler('active')

    assert str(raised.value) == 'OpenStack query failed: get_instances_by_status'


@pytest.mark.asyncio
async def test_instances_by_status_is_case_insensitive(conn):
    conn.compute.servers.return_value = [Server.existing(
        id='s1', name='vm', project_id='project-a', status='SHUTOFF')]
    _, handler = _tool_handler('get_instances_by_status',
                               'get_instances_by_status')

    payload = json.loads(await handler('shutoff'))

    assert payload['status_filter'] == 'SHUTOFF'
    assert [i['name'] for i in payload['instances']] == ['vm']


# --- 6. get_server_volumes ----------------------------------------------

@pytest.mark.asyncio
async def test_server_volumes_for_missing_server_is_an_error(conn):
    _, handler = _tool_handler('get_server_volumes', 'get_server_volumes')

    output = await handler('missing-vm')

    assert output == 'Error: Server "missing-vm" not found'


@pytest.mark.asyncio
async def test_server_volumes_for_existing_server_without_volumes(conn):
    _, handler = _tool_handler('get_server_volumes', 'get_server_volumes')

    payload = json.loads(await handler('vm'))

    assert payload['result'] == []
