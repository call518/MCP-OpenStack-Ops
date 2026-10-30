"""Regressions reproduced while exercising the registered tools on OpenStack."""

import importlib
import json
from types import SimpleNamespace
from unittest.mock import Mock, create_autospec

import pytest
from openstack.compute.v2._proxy import Proxy as ComputeProxy
from openstack.compute.v2.server import Server
from openstack.network.v2._proxy import Proxy as NetworkProxy
from openstack.orchestration.v1._proxy import Proxy as HeatProxy
from openstack.orchestration.v1.stack import Stack

from mcp_openstack_ops import connection, functions
from mcp_openstack_ops.services import compute, monitoring, network, orchestration
import mcp_openstack_ops.mcp_main  # Register tools before importing tool modules.


async def invoke(name, **kwargs):
    module = importlib.import_module(f'mcp_openstack_ops.tools.{name}')
    handler = getattr(module, name)
    return await getattr(handler, 'fn', handler)(**kwargs)


@pytest.fixture
def conn(monkeypatch):
    value = SimpleNamespace(
        compute=create_autospec(ComputeProxy, instance=True),
        network=create_autospec(NetworkProxy, instance=True),
        orchestration=create_autospec(HeatProxy, instance=True),
        current_project_id='project-a',
    )
    value.compute.servers.return_value = [
        Server(id='server-a', name='vm', project_id='project-a', metadata={'keep': 'v'})
    ]
    monkeypatch.setattr(connection, 'get_openstack_connection', lambda: value)
    return value


@pytest.mark.asyncio
@pytest.mark.parametrize('tool,kwargs', [
    ('get_load_balancer_health_monitors', {}),
    ('get_load_balancer_pool_members', {'pool_name_or_id': 'pool-a'}),
    ('set_load_balancer_pool', {'action': 'list'}),
    ('set_load_balancer_pool_member', {'action': 'list', 'pool_name_or_id': 'pool-a'}),
])
async def test_load_balancer_tools_reach_service_exports(monkeypatch, tool, kwargs):
    service = Mock(return_value={'success': True})
    monkeypatch.setattr(functions, tool, service)
    result = await invoke(tool, **kwargs)
    assert 'mcp_openstack_ops.tools.functions' not in result
    service.assert_called_once()


@pytest.mark.asyncio
@pytest.mark.parametrize('action,names', [('list', ''), ('create', 'image-a')])
async def test_image_scalar_and_list_paths_reach_service(monkeypatch, action, names):
    module = importlib.import_module('mcp_openstack_ops.tools.set_image')
    service = Mock(return_value={'success': True})
    monkeypatch.setattr(module, '_set_image', service)
    await invoke('set_image', action=action, image_names=names)
    service.assert_called_once()
    assert service.call_args.kwargs['properties'] == {}


@pytest.mark.asyncio
async def test_heat_scalar_name_parses_json_template(monkeypatch):
    module = importlib.import_module('mcp_openstack_ops.tools.set_heat_stack')
    service = Mock(return_value={'success': True})
    monkeypatch.setattr(module, '_set_heat_stack', service)
    template = {'heat_template_version': '2018-08-31', 'resources': {}}
    await invoke('set_heat_stack', action='create', stack_names='stack-a',
                 template=json.dumps(template))
    service.assert_called_once_with('stack-a', 'create', template=template)


def test_heat_create_uses_api_string_tags_and_sdk_status(conn):
    conn.orchestration.create_stack.return_value = Stack(
        id='stack-a', stack_name='stack-a', stack_status='CREATE_IN_PROGRESS'
    )
    result = orchestration.set_heat_stack(
        'stack-a', 'create', template={'resources': {}}
    )
    assert result['success'], result
    assert conn.orchestration.create_stack.call_args.kwargs['tags'] == ''
    assert result['stack']['status'] == 'CREATE_IN_PROGRESS'


@pytest.mark.asyncio
async def test_metadata_only_tool_preserves_name_and_description(conn):
    result = await invoke('set_server_properties', instance_name='vm', action='set',
                          metadata={'added': 'value'})
    assert json.loads(result)['success']
    conn.compute.update_server.assert_not_called()
    conn.compute.set_server_metadata.assert_called_once_with(
        conn.compute.servers.return_value[0], added='value'
    )


def test_metadata_unset_uses_sdk_metadata_endpoint(conn):
    result = compute.set_server_properties('vm', 'unset', properties=['keep'])
    assert result['success'], result
    conn.compute.delete_server_metadata.assert_called_once_with(
        conn.compute.servers.return_value[0], keys=['keep']
    )
    conn.compute.update_server.assert_not_called()


def test_server_backup_uses_sdk_backup_action(conn):
    result = compute.create_server_backup('vm', 'backup-a', backup_type='weekly',
                                          rotation=2)
    assert result['success'], result
    conn.compute.backup_server.assert_called_once_with(
        conn.compute.servers.return_value[0], name='backup-a',
        backup_type='weekly', rotation=2,
    )


@pytest.mark.parametrize('action', ['list', 'create', 'show', 'set', 'delete'])
def test_port_forwarding_uses_sdk_parent_parameters(conn, action):
    conn.network.ips.return_value = [SimpleNamespace(id='fip-a')]
    rule = SimpleNamespace(id='rule-a', protocol='tcp')
    conn.network.port_forwardings.return_value = []
    conn.network.create_port_forwarding.return_value = rule
    conn.network.get_port_forwarding.return_value = rule
    conn.network.update_port_forwarding.return_value = rule
    result = network.set_floating_ip_port_forwarding(
        action, floating_ip_id='fip-a', port_forwarding_id='rule-a',
        external_port=18022, internal_port=22, description='test',
    )
    assert result['success'], result
    if action == 'list':
        conn.network.port_forwardings.assert_called_once_with('fip-a')
    elif action == 'create':
        assert conn.network.create_port_forwarding.call_args.kwargs[
            'floatingip_id'] == 'fip-a'
    else:
        method = {'show': 'get', 'set': 'update', 'delete': 'delete'}[action]
        assert getattr(conn.network, f'{method}_port_forwarding').call_args.kwargs[
            'floating_ip'] == 'fip-a'


def test_port_forwarding_list_failure_never_looks_like_empty_success(conn):
    conn.network.ips.return_value = [SimpleNamespace(id='fip-a')]
    conn.network.port_forwardings.side_effect = RuntimeError('API unavailable')
    result = network.set_floating_ip_port_forwarding('list', floating_ip_id='fip-a')
    assert result['success'] is False


@pytest.mark.asyncio
async def test_quota_tool_routes_fields_without_changing_schema(monkeypatch):
    module = importlib.import_module('mcp_openstack_ops.tools.set_quota')
    service = Mock(return_value={'success': True})
    monkeypatch.setattr(module, '_set_quota', service)
    monkeypatch.setenv('ALLOW_MODIFY_OPERATIONS', 'true')
    result = await invoke('set_quota', project_name='test-project', action='set',
                          cores=2, floating_ips=3, volumes=4)
    assert json.loads(result)['success']
    calls = {c.kwargs['service']: c.kwargs for c in service.call_args_list}
    assert calls['compute']['cores'] == 2
    assert calls['network']['floating_ips'] == 3
    assert calls['volume']['volumes'] == 4


@pytest.mark.asyncio
async def test_quota_list_is_read_only(monkeypatch):
    module = importlib.import_module('mcp_openstack_ops.tools.set_quota')
    getter = Mock(return_value={'success': True})
    setter = Mock()
    monkeypatch.setattr(module, '_get_quota', getter, raising=False)
    monkeypatch.setattr(module, '_set_quota', setter)
    result = await invoke('set_quota', project_name='test-project', action='list')
    assert json.loads(result)['success']
    getter.assert_called_once_with('test-project')
    setter.assert_not_called()


@pytest.mark.asyncio
async def test_quota_mutation_is_blocked_at_runtime(monkeypatch):
    monkeypatch.setenv('ALLOW_MODIFY_OPERATIONS', 'false')
    result = await invoke('set_quota', project_name='test-project', action='delete')
    assert 'MODIFY_OPERATIONS_DISABLED' in result


@pytest.mark.asyncio
async def test_quota_partial_failure_is_reported(monkeypatch):
    module = importlib.import_module('mcp_openstack_ops.tools.set_quota')
    monkeypatch.setenv('ALLOW_MODIFY_OPERATIONS', 'true')
    service = Mock(side_effect=[
        {'success': True}, {'success': False, 'error': 'denied'},
    ])
    monkeypatch.setattr(module, '_set_quota', service)
    result = await invoke('set_quota', project_name='test', action='set',
                          cores=2, networks=2)
    assert 'incomplete' in result
    assert 'denied' in result


@pytest.mark.asyncio
async def test_quota_delete_routes_all_services(monkeypatch):
    module = importlib.import_module('mcp_openstack_ops.tools.set_quota')
    monkeypatch.setenv('ALLOW_MODIFY_OPERATIONS', 'true')
    service = Mock(return_value={'success': True})
    monkeypatch.setattr(module, '_set_quota', service)
    result = await invoke('set_quota', project_name='test', action='delete')
    assert json.loads(result)['success']
    assert {c.kwargs['service'] for c in service.call_args_list} == {
        'compute', 'network', 'volume',
    }
    assert all(c.kwargs['action'] == 'delete' for c in service.call_args_list)


@pytest.mark.parametrize('service,proxy,method', [
    ('compute', 'compute', 'revert_quota_set'),
    ('network', 'network', 'delete_quota'),
    ('volume', 'volume', 'revert_quota_set'),
])
def test_quota_reset_uses_sdk_methods(conn, service, proxy, method):
    from openstack.block_storage.v3._proxy import Proxy as StorageProxy
    conn.identity = Mock()
    conn.identity.projects.return_value = [SimpleNamespace(name='test', id='project-a')]
    conn.volume = create_autospec(StorageProxy, instance=True)
    result = monitoring.set_quota('test', service, action='delete')
    assert result['success'], result
    assert getattr(getattr(conn, proxy), method).call_args.args == ('project-a',)


@pytest.mark.parametrize('key', ['floating_ips', 'floatingips'])
def test_quota_network_accepts_public_and_legacy_names(conn, key):
    conn.identity = Mock()
    conn.identity.projects.return_value = [SimpleNamespace(name='test', id='project-a')]
    assert monitoring.set_quota('test', 'network', **{key: 3})['success']
    conn.network.update_quota.assert_called_once_with('project-a', floating_ips=3)


def test_server_backup_does_not_mutate_metadata_input(conn):
    metadata = {'keep': 'value'}
    result = compute.create_server_backup('vm', 'backup-a', metadata=metadata)
    assert result['success']
    assert result['backup_id'] is None
    assert metadata == {'keep': 'value'}
