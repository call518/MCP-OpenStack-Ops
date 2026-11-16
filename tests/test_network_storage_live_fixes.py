"""Regressions for network and block-storage defects seen on a live cloud.

The lab (OpenStack 2026.1, no Cinder) showed: floating IP descriptions dropped
on create, a missing network reported as an empty result, an unclear
``'NoneType' object has no attribute 'api_version'`` from every block-storage
call, and volume read tools raising instead of returning an error.
"""

import importlib
import json
from types import SimpleNamespace
from unittest.mock import Mock, create_autospec

import pytest
from fastmcp.exceptions import ToolError
from keystoneauth1 import exceptions as ksa_exceptions
from openstack import exceptions as sdk_exceptions
from openstack.block_storage.v3._proxy import Proxy as StorageProxy
from openstack.network.v2._proxy import Proxy as NetworkProxy
from openstack.network.v2.floating_ip import FloatingIP
from openstack.network.v2.network import Network

from mcp_openstack_ops import connection
from mcp_openstack_ops.services import storage
import mcp_openstack_ops.mcp_main  # Register tools before importing tool modules.

CINDER = 'Block Storage (Cinder) service is not available in this cloud'
SDK49 = "'NoneType' object has no attribute 'api_version'"
SDK422 = ('Failed to create a working proxy for service block-storage: '
          'No endpoint data found.')


def _tool(name):
    module = importlib.import_module(f'mcp_openstack_ops.tools.{name}')
    tool = getattr(module, name)
    return module, getattr(tool, 'fn', tool)


def _install(monkeypatch, value):
    monkeypatch.setattr(connection, 'get_openstack_connection', lambda: value)
    monkeypatch.setattr(connection, 'get_current_project_id', lambda: 'project-a')


@pytest.fixture
def conn(monkeypatch):
    value = SimpleNamespace(
        current_project_id='project-a',
        network=create_autospec(NetworkProxy, instance=True),
        block_storage=create_autospec(StorageProxy, instance=True),
    )
    value.volume = value.block_storage
    value.network.networks.return_value = []
    value.network.subnets.return_value = []
    value.network.ips.return_value = []
    _install(monkeypatch, value)
    return value


def _external_network():
    return Network.existing(id='ext-net', name='public', project_id='admin',
                            is_router_external=True)


def _floating_ip(**attrs):
    values = dict(id='fip-1', floating_ip_address='203.0.113.5',
                  floating_network_id='ext-net', project_id='project-a',
                  status='DOWN', description='')
    values.update(attrs)
    return FloatingIP.existing(**values)


# --- 1. floating IP description ----------------------------------------------

@pytest.mark.asyncio
async def test_floating_ip_create_forwards_description(conn, monkeypatch):
    module, handler = _tool('set_floating_ip')
    monkeypatch.setattr(module, 'handle_operation_result', lambda result, *a: result)
    conn.network.networks.return_value = [_external_network()]
    conn.network.create_ip.return_value = _floating_ip(description='x')

    result = await handler(action='create', floating_network_id='ext-net',
                           description='x')

    assert result['success'] is True, result
    conn.network.create_ip.assert_called_once_with(
        floating_network_id='ext-net', description='x')
    assert result['floating_ip']['description'] == 'x'


@pytest.mark.asyncio
async def test_floating_ip_set_show_delete_by_address(conn, monkeypatch):
    module, handler = _tool('set_floating_ip')
    monkeypatch.setattr(module, 'handle_operation_result', lambda result, *a: result)
    fip = _floating_ip(description='old')
    conn.network.ips.return_value = [fip]
    conn.network.update_ip.return_value = _floating_ip(description='new')

    updated = await handler(action='set', floating_ip_address='203.0.113.5',
                            description='new')
    shown = await handler(action='show', floating_ip_address='203.0.113.5')
    deleted = await handler(action='delete', floating_ip_address='203.0.113.5')

    conn.network.update_ip.assert_called_once_with(fip, description='new')
    assert updated['floating_ip']['description'] == 'new'
    assert shown['success'] is True
    assert shown['floating_ip']['id'] == 'fip-1'
    assert shown['floating_ip']['description'] == 'old'
    assert deleted['success'] is True, deleted
    conn.network.delete_ip.assert_called_once_with(fip)


# --- 2. missing network ------------------------------------------------------

@pytest.mark.asyncio
async def test_get_network_details_missing_network_is_explicit_error(conn):
    _, handler = _tool('get_network_details')
    conn.network.networks.return_value = [_external_network()]

    output = await handler(network_name='missing-net')

    assert output.startswith('Error:'), output
    assert 'missing-net' in output and 'not found' in output
    with pytest.raises(ValueError):
        json.loads(output)


@pytest.mark.asyncio
async def test_get_network_details_all_and_found_still_return_json(conn):
    _, handler = _tool('get_network_details')

    empty = json.loads(await handler(network_name='all'))
    conn.network.networks.return_value = [_external_network()]
    found = json.loads(await handler(network_name='public'))

    assert empty['network_details'] == []
    assert [row['id'] for row in found['network_details']] == ['ext-net']


# --- 3./4. block storage absent ----------------------------------------------

def _no_cinder_errors():
    return [
        pytest.param(AttributeError(SDK49), SDK49, id='sdk-4.9-attributeerror'),
        pytest.param(sdk_exceptions.ServiceDiscoveryException(SDK422), SDK422,
                     id='sdk-4.22-discovery'),
        pytest.param(sdk_exceptions.EndpointNotFound('no block-storage endpoint'),
                     'no block-storage endpoint', id='endpoint-not-found'),
    ]


class _NoCinderConnection(SimpleNamespace):
    """Connection whose block-storage proxy cannot be built, as in the SDK."""

    @property
    def block_storage(self):
        raise self.error

    volume = block_storage


@pytest.fixture(params=['proxy-construction', 'proxy-call'])
def no_cinder(request, monkeypatch):
    def install(error):
        if request.param == 'proxy-construction':
            value = _NoCinderConnection(current_project_id='project-a', error=error)
        else:
            api = create_autospec(StorageProxy, instance=True)
            for name in ('volumes', 'snapshots', 'types', 'backups', 'groups',
                         'transfers'):
                getattr(api, name).side_effect = error
            api.get.side_effect = error
            value = SimpleNamespace(current_project_id='project-a',
                                    block_storage=api, volume=api)
        _install(monkeypatch, value)
    return install


@pytest.mark.parametrize('error,original', _no_cinder_errors())
@pytest.mark.parametrize('query', [storage.get_volume_list,
                                   storage.get_volume_snapshots])
def test_volume_queries_name_missing_cinder(no_cinder, query, error, original):
    no_cinder(error)
    with pytest.raises(RuntimeError, match='OpenStack resource query failed') as caught:
        query()
    assert f'{CINDER}: {original}' in str(caught.value)


@pytest.mark.parametrize('error,original', _no_cinder_errors())
@pytest.mark.parametrize('operation', [
    lambda: storage.set_volume('', 'list'),
    lambda: storage.set_snapshot('', 'list'),
    lambda: storage.set_volume_backups('list'),
    lambda: storage.set_volume_groups('list'),
    lambda: storage.set_volume_qos('list'),
    storage.get_volume_transfers,
], ids=['volume', 'snapshot', 'backups', 'groups', 'qos', 'transfers'])
def test_storage_operations_name_missing_cinder(no_cinder, operation, error, original):
    no_cinder(error)
    result = operation()
    assert result['success'] is False
    assert f'{CINDER}: {original}' in result['error']
    assert CINDER in result['message']


@pytest.mark.asyncio
@pytest.mark.parametrize('error,original', _no_cinder_errors())
@pytest.mark.parametrize('name', ['get_volume_list', 'get_volume_snapshots',
                                  'get_volume_types'])
async def test_volume_read_tools_return_error_when_cinder_missing(
    no_cinder, name, error, original
):
    no_cinder(error)
    _, handler = _tool(name)

    if name == 'get_volume_types':
        # This tool's existing convention returns an "Error: ..." string.
        output = await handler()
        assert output.startswith('Error:'), output
    else:
        # Upstream convention: a redacted ToolError (MCP error result).
        with pytest.raises(ToolError) as raised:
            await handler()
        output = str(raised.value)
        assert output.startswith(f'OpenStack query failed: {name}'), output
    assert f'{CINDER}: {original}' in output


@pytest.mark.asyncio
@pytest.mark.parametrize('name', ['get_volume_list', 'get_volume_snapshots'])
async def test_volume_read_tools_keep_unrelated_errors_redacted(monkeypatch, name):
    monkeypatch.setattr(connection, 'get_openstack_connection',
                        Mock(side_effect=RuntimeError('private detail')))
    _, handler = _tool(name)

    with pytest.raises(ToolError) as raised:
        await handler()

    assert str(raised.value) == f'OpenStack query failed: {name}'


def test_cinder_mapping_requires_the_volume_endpoint(monkeypatch):
    monkeypatch.delenv('OS_VOLUME_PORT', raising=False)
    cinder = ksa_exceptions.ConnectFailure(
        'Unable to establish connection to http://10.0.0.5:8776/v3/volumes/detail')
    identity = ksa_exceptions.ConnectFailure(
        'Unable to establish connection to http://10.0.0.5:5000/v3/auth/tokens')

    message = storage.block_storage_unavailable_message(cinder)

    assert message.startswith(f'{CINDER}: Unable to establish connection to')
    assert '10.0.0.5' not in message
    assert storage.block_storage_unavailable_message(identity) is None
    assert storage.block_storage_unavailable_message(
        AttributeError("'Volume' object has no attribute 'foo'")) is None
    assert storage.block_storage_unavailable_message(RuntimeError('boom')) is None
