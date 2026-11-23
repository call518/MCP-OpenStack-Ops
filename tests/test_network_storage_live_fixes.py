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
from openstack.network.v2.port import Port
from openstack.network.v2.router import Router
from openstack.network.v2.security_group import SecurityGroup
from openstack.network.v2.subnet import Subnet

from mcp_openstack_ops import connection
from mcp_openstack_ops.services import network, storage
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


@pytest.mark.parametrize('network_name', ['all', 'public'])
def test_network_details_report_qos_policy_and_description(conn, network_name):
    conn.network.networks.return_value = [Network.existing(
        id='ext-net', name='public', project_id='admin', is_router_external=True,
        description='uplink', qos_policy_id='qos-net')]

    [row] = network.get_network_details(network_name=network_name)

    assert row['qos_policy_id'] == 'qos-net'
    assert row['description'] == 'uplink'


def test_security_group_rules_report_description(conn):
    conn.network.security_groups.return_value = [SecurityGroup.existing(
        id='sg-1', name='web', project_id='project-a', security_group_rules=[
            {'id': 'r1', 'direction': 'ingress', 'protocol': 'tcp',
             'ethertype': 'IPv4', 'description': 'https from office'}])]

    [group] = network.get_security_groups()

    assert group['rules'][0]['description'] == 'https from office'


def _router():
    return Router.existing(id='r1', name='edge', project_id='project-a',
                           routes=[{'destination': '10.9.0.0/16',
                                    'nexthop': '10.0.0.254'}])


def test_routers_report_static_routes_and_interfaces(conn):
    conn.network.routers.return_value = [_router()]
    conn.network.ports.return_value = [Port.existing(
        id='p1', device_id='r1', device_owner='network:router_interface',
        fixed_ips=[{'subnet_id': 'subnet-1', 'ip_address': '10.0.0.1'}])]

    [row] = network.get_routers()

    assert row['routes'] == [{'destination': '10.9.0.0/16', 'nexthop': '10.0.0.254'}]
    assert row['interface_count'] == 1
    assert 'interfaces_error' not in row


def test_routers_report_failed_interface_lookup_as_null(conn):
    conn.network.routers.return_value = [_router()]
    conn.network.ports.side_effect = sdk_exceptions.HttpException('port list failed')

    [row] = network.get_routers()

    assert row['interfaces'] is None
    assert row['interface_count'] is None
    assert 'port list failed' in row['interfaces_error']


def test_floating_ips_report_qos_policy(conn):
    conn.network.ips.return_value = [_floating_ip(qos_policy_id='qos-fip')]

    [row] = network.get_floating_ips()

    assert row['qos_policy_id'] == 'qos-fip'


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


def test_volume_create_reports_acceptance_not_completion(conn):
    conn.volume.create_volume.return_value = SimpleNamespace(
        id='vol-1', name='data', status='creating', size=1, volume_type='lvm')

    result = storage.set_volume('data', 'create', size=1)

    assert result['success'] is True, result
    assert 'accepted' in result['message'], result
    assert 'successfully' not in result['message'], result
    assert result['volume']['status'] == 'creating'


# --- 5. subnet and port create defaults --------------------------------------

@pytest.mark.asyncio
@pytest.mark.parametrize('gateway_ip,expected', [
    ('', 'absent'),  # an explicit null would create a subnet without a gateway
    ('10.0.0.254', '10.0.0.254'),
])
async def test_subnet_create_gateway_default_and_description(
        conn, monkeypatch, gateway_ip, expected):
    monkeypatch.setenv('ALLOW_MODIFY_OPERATIONS', 'true')
    _, handler = _tool('set_subnets')
    conn.network.create_subnet.return_value = SimpleNamespace(
        id='subnet-1', name='s', network_id='net-1', cidr='10.0.0.0/24',
        gateway_ip='10.0.0.1')

    result = json.loads(await handler(
        action='create', subnet_name='s', network_id='net-1',
        cidr='10.0.0.0/24', description='d', gateway_ip=gateway_ip))

    assert result['success'] is True, result
    params = conn.network.create_subnet.call_args.kwargs
    assert params.get('gateway_ip', 'absent') == expected
    assert params['description'] == 'd'


@pytest.mark.asyncio
@pytest.mark.parametrize('security_groups,expected', [
    ('[]', 'absent'),  # an explicit [] would create a port without any group
    ('["sg-1"]', ['sg-1']),
])
async def test_port_create_security_group_default_and_description(
        conn, monkeypatch, security_groups, expected):
    monkeypatch.setenv('ALLOW_MODIFY_OPERATIONS', 'true')
    _, handler = _tool('set_network_ports')
    conn.network.create_port.return_value = SimpleNamespace(
        id='port-1', name='p', network_id='net-1', status='DOWN',
        mac_address='fa:16:3e:00:00:01')

    result = json.loads(await handler(
        action='create', port_name='p', network_id='net-1', description='d',
        security_groups=security_groups))

    assert result['success'] is True, result
    params = conn.network.create_port.call_args.kwargs
    assert params.get('security_group_ids', 'absent') == expected
    assert params['description'] == 'd'


@pytest.mark.asyncio
@pytest.mark.parametrize('action,key', [('list', 'ports'), ('show', 'port')])
async def test_port_read_reports_qos_policies_and_description(conn, action, key):
    _, handler = _tool('set_network_ports')
    conn.network.ports.return_value = [Port.existing(
        id='port-1', name='p', network_id='net-1', project_id='project-a',
        description='vip', qos_policy_id='qos-port',
        qos_network_policy_id='qos-net')]

    result = json.loads(await handler(action=action, port_name='p'))

    assert result['success'] is True, result
    port = result[key][0] if action == 'list' else result[key]
    assert port['qos_policy_id'] == 'qos-port'
    assert port['qos_network_policy_id'] == 'qos-net'
    assert port['description'] == 'vip'
    assert port['project_id'] == 'project-a'
    conn.network.ports.assert_called_once_with(project_id='project-a')


def _vrrp_port():
    # Octavia creates amphora VRRP ports with its own service credential.
    return Port.existing(id='vrrp-1', name='octavia-lb-vrrp-amp-1',
                         network_id='net-1', project_id='service-project',
                         device_owner='Octavia', qos_policy_id='qos-vip')


@pytest.mark.asyncio
async def test_port_list_all_projects_requires_switch(conn, monkeypatch):
    monkeypatch.delenv('ALLOW_CROSS_PROJECT_READ', raising=False)
    _, handler = _tool('set_network_ports')

    result = json.loads(await handler(action='list', all_projects=True))

    assert result['success'] is False
    assert 'ALLOW_CROSS_PROJECT_READ=true' in result['error']
    conn.network.ports.assert_not_called()


@pytest.mark.asyncio
async def test_port_list_all_projects_shows_other_project_ports(conn, monkeypatch):
    monkeypatch.setenv('ALLOW_CROSS_PROJECT_READ', 'true')
    conn.identity = Mock()
    conn.identity.projects.return_value = [
        SimpleNamespace(id='project-a', name='admin'),
        SimpleNamespace(id='service-project', name='service')]
    conn.network.ports.return_value = [_vrrp_port()]
    _, handler = _tool('set_network_ports')

    result = json.loads(await handler(action='list', all_projects=True))

    assert result['success'] is True, result
    conn.network.ports.assert_called_once_with()
    [row] = result['ports']
    assert (row['project_id'], row['project_name']) == ('service-project', 'service')
    assert row['qos_policy_id'] == 'qos-vip'
    assert result['scope'] == {'all_projects': True, 'projects_in_result': 1}


@pytest.mark.asyncio
async def test_port_show_rejects_all_projects(conn, monkeypatch):
    monkeypatch.setenv('ALLOW_CROSS_PROJECT_READ', 'true')
    _, handler = _tool('set_network_ports')

    result = json.loads(await handler(action='show', port_name='vrrp-1',
                                      all_projects=True))

    assert result['success'] is False
    assert 'only to list' in result['error']
    conn.network.ports.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize('action,key', [('list', 'subnets'), ('show', 'subnet')])
async def test_subnet_read_reports_description(conn, action, key):
    _, handler = _tool('set_subnets')
    conn.network.subnets.return_value = [Subnet.existing(
        id='subnet-1', name='s', network_id='net-1', cidr='10.0.0.0/24',
        description='app tier')]

    result = json.loads(await handler(action=action, subnet_name='s'))

    assert result['success'] is True, result
    subnet = result[key][0] if action == 'list' else result[key]
    assert subnet['description'] == 'app tier'


# --- 6. unimplemented set_volume parameters ----------------------------------

@pytest.mark.asyncio
@pytest.mark.parametrize('parameter,value', [
    ('source_volume', 'src'), ('backup_name', 'b'), ('transfer_name', 't'),
    ('host', 'h'), ('incremental', True), ('force_host_copy', True),
    ('lock_volume', True),
])
async def test_volume_rejects_unimplemented_parameters(
        monkeypatch, parameter, value):
    module, handler = _tool('set_volume')
    service = Mock(return_value={'success': True})
    monkeypatch.setattr(module, '_set_volume', service)

    result = await handler(volume_names='data', action='create',
                           **{parameter: value})

    assert result.startswith('Error: Not implemented'), result
    assert parameter in result
    service.assert_not_called()
