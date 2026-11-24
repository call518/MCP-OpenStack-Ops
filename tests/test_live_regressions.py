"""Regressions reproduced while exercising the registered tools on OpenStack."""

import importlib
import json
from types import SimpleNamespace
from unittest.mock import Mock, create_autospec

import pytest
from openstack.compute.v2._proxy import Proxy as ComputeProxy
from openstack.compute.v2.server import Server
from openstack.compute.v2.hypervisor import Hypervisor
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
async def test_image_scalar_path_reaches_service(monkeypatch):
    module = importlib.import_module('mcp_openstack_ops.tools.set_image')
    service = Mock(return_value={'success': True})
    monkeypatch.setattr(module, '_set_image', service)
    await invoke('set_image', action='create', image_names='image-a')
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


def test_heat_create_omits_empty_tags_and_reads_sdk_status(conn):
    # tags=[] made Heat return HTTP 400 and tags='' was stored as [""].
    conn.orchestration.create_stack.return_value = Stack(
        id='stack-a', stack_name='stack-a', stack_status='CREATE_IN_PROGRESS'
    )
    result = orchestration.set_heat_stack(
        'stack-a', 'create', template={'resources': {}}
    )
    assert result['success'], result
    kwargs = conn.orchestration.create_stack.call_args.kwargs
    assert 'tags' not in kwargs and 'timeout' not in kwargs
    assert result['stack']['status'] == 'CREATE_IN_PROGRESS'


def test_heat_create_sends_timeout_files_and_environment(conn):
    conn.orchestration.create_stack.return_value = Stack(id='s', stack_name='web')
    files = {'member.yaml': 'heat_template_version: 2018-08-31'}
    env = {'resource_registry': {'My::Member': 'member.yaml'}}
    orchestration.set_heat_stack('web', 'create', template='t: 1',
                                 parameters={'image': 'img'}, files=files,
                                 environment=env, timeout_mins=90)
    conn.orchestration.create_stack.assert_called_once_with(
        name='web', template='t: 1', parameters={'image': 'img'}, files=files,
        environment=env, timeout_mins=90)
    # The SDK must put these fields in the request body.
    body = Stack(name='web', files=files, environment=env, timeout_mins=90)._body.dirty
    assert body['files'] == files and body['timeout_mins'] == 90


def _owned_stack():
    return Stack(id='stack-a', stack_name='app', links=[{'rel': 'self',
        'href': 'https://heat/v1/project-a/stacks/app/stack-a'}])


def test_heat_update_existing_patches_only_supplied_fields(conn):
    conn.orchestration.stacks.return_value = [_owned_stack()]
    result = orchestration.set_heat_stack('app', 'update', existing=True,
                                          parameters={'image': 'v2'})
    assert result['success'], result
    conn.orchestration.patch.assert_called_once_with(
        '/stacks/app/stack-a', json={'parameters': {'image': 'v2'}}, raise_exc=True)
    conn.orchestration.update_stack.assert_not_called()


def test_heat_update_replace_sends_files_and_requires_template(conn):
    stack = _owned_stack()
    conn.orchestration.stacks.return_value = [stack]
    conn.orchestration.update_stack.return_value = stack
    assert not orchestration.set_heat_stack('app', 'update')['success']
    files = {'member.yaml': 'x'}
    orchestration.set_heat_stack('app', 'update', template='t: 1', files=files,
                                 timeout_mins=90)
    conn.orchestration.update_stack.assert_called_once_with(
        stack, template='t: 1', files=files, timeout_mins=90, parameters={})
    conn.orchestration.patch.assert_not_called()


def test_heat_validate_posts_template_files_and_environment(conn):
    conn.orchestration.post.return_value = Mock(json=Mock(return_value={'Parameters': {}}))
    files = {'member.yaml': 'x'}
    result = orchestration.set_heat_stack('check', 'validate', template='t: 1',
                                          files=files, environment='e: 1',
                                          timeout_mins=90)
    assert result['success'] and result['validation'] == {'Parameters': {}}
    conn.orchestration.post.assert_called_once_with(
        '/validate', json={'template': 't: 1', 'files': files, 'environment': 'e: 1'},
        raise_exc=True)
    assert not orchestration.set_heat_stack('check', 'validate')['success']


@pytest.mark.asyncio
async def test_heat_tool_parses_files_environment_and_options(monkeypatch):
    module = importlib.import_module('mcp_openstack_ops.tools.set_heat_stack')
    service = Mock(return_value={'success': True})
    monkeypatch.setattr(module, '_set_heat_stack', service)
    await invoke('set_heat_stack', action='update', stack_names='app',
                 files='{"member.yaml": "x"}', environment='parameter_defaults: {}',
                 timeout_mins=90, existing=True)
    service.assert_called_once_with('app', 'update', files={'member.yaml': 'x'},
                                    environment='parameter_defaults: {}',
                                    timeout_mins=90, existing=True)
    for bad in ('["member.yaml"]', '{"member.yaml": 1}', 'member.yaml'):
        result = await invoke('set_heat_stack', action='create', stack_names='app',
                              template='t: 1', files=bad)
        assert 'Invalid files format' in result
    assert service.call_count == 1


def test_heat_details_pass_nested_depth(conn):
    stack = _owned_stack()
    conn.orchestration.find_stack.return_value = stack
    conn.orchestration.resources.return_value = []
    conn.orchestration.stack_events.return_value = []
    # openstacksdk's Resource drops nested_depth, so resources use the raw API.
    conn.orchestration.get.return_value.json.return_value = {'resources': [
        {'resource_name': 'inner', 'resource_type': 'inner.yaml',
         'resource_status': 'CREATE_COMPLETE'},
        {'resource_name': 'rnd', 'resource_type': 'OS::Heat::RandomString',
         'resource_status': 'CREATE_COMPLETE', 'parent_resource': 'inner'},
    ]}
    result = orchestration.get_heat_stack_details('app', 'resources', nested_depth=2)
    assert result['success'], result
    conn.orchestration.get.assert_called_once_with(
        f'/stacks/{stack.name}/{stack.id}/resources', params={'nested_depth': 2})
    conn.orchestration.resources.assert_not_called()
    assert [(r['name'], r['status'], r.get('parent_resource'))
            for r in result['resources']] == [
        ('inner', 'CREATE_COMPLETE', None), ('rnd', 'CREATE_COMPLETE', 'inner')]
    assert orchestration.get_heat_stack_details('app', 'resources')['success']
    conn.orchestration.resources.assert_called_once_with(stack)
    assert orchestration.get_heat_stack_details('app', 'events', nested_depth=2)['success']
    conn.orchestration.stack_events.assert_called_once_with(stack, nested_depth=2)
    conn.orchestration.stack_events.reset_mock()
    assert orchestration.get_heat_stack_details('app', 'events')['success']
    conn.orchestration.stack_events.assert_called_once_with(
        conn.orchestration.find_stack.return_value)
    assert not orchestration.get_heat_stack_details('app', 'events', nested_depth=-1)['success']


def test_heat_list_requires_matching_owner_from_self_link(conn):
    conn.orchestration.stacks.return_value = [
        Stack(id='stack-a', stack_name='stack-a', stack_status='CREATE_COMPLETE',
              links=[{'rel': 'self', 'href': 'https://heat/v1/project-a/stacks/app/stack-a'}]),
        Stack(id='stack-b', stack_name='stack-b',
              links=[{'rel': 'self', 'href': 'https://heat/v1/project-b/stacks/app/stack-b'}]),
        Stack(id='unknown', stack_name='unknown'),
        SimpleNamespace(id='foreign', project_id='project-b'),
    ]
    result = orchestration.get_heat_stacks()
    assert [stack['id'] for stack in result] == ['stack-a']
    assert result[0]['project_id'] == 'project-a'
    assert result[0]['stack_status'] == 'CREATE_COMPLETE'
    conn.orchestration.stacks.assert_called_once_with()


@pytest.mark.parametrize('action', ['delete', 'update'])
def test_heat_write_rejects_foreign_and_unknown_owner(conn, action):
    for stack in [Stack(id='stack-b', stack_name='foreign',
                        links=[{'rel': 'self', 'href':
                                'https://heat/v1/project-b/stacks/foreign/stack-b'}]),
                  Stack(id='stack-b', stack_name='foreign')]:
        conn.orchestration.stacks.return_value = [stack]
        result = orchestration.set_heat_stack('foreign', action,
                                              template={'resources': {}})
        assert not result['success']
    conn.orchestration.delete_stack.assert_not_called()
    conn.orchestration.update_stack.assert_not_called()


def test_heat_delete_accepts_stack_with_matching_self_link(conn):
    stack = Stack(id='stack-a', stack_name='app', links=[{'rel': 'self',
        'href': 'https://heat/v1/project-a/stacks/app/stack-a'}])
    conn.orchestration.stacks.return_value = [stack]
    assert orchestration.set_heat_stack('app', 'delete')['success']
    conn.orchestration.delete_stack.assert_called_once_with(stack)


def test_heat_details_reject_foreign_owner(conn):
    conn.orchestration.find_stack.return_value = Stack(
        id='stack-b', stack_name='foreign', links=[{'rel': 'self',
        'href': 'https://heat/v1/project-b/stacks/foreign/stack-b'}])
    assert not orchestration.get_heat_stack_details('foreign')['success']
    conn.orchestration.resources.assert_not_called()


def test_heat_list_requires_a_project_scope(conn):
    conn.current_project_id = None
    with pytest.raises(ValueError, match='project-scoped'):
        orchestration.get_heat_stacks()


@pytest.mark.parametrize('name', ['all', 'host-a'])
def test_hypervisor_missing_capacity_is_unknown_not_zero(conn, name):
    conn.compute.hypervisors.return_value = [
        Hypervisor(id='host-a', name='host-a', vcpus=0, memory_mb=1024),
    ]
    conn.compute.get.return_value.status_code = 404
    result = monitoring.get_hypervisor_details(name)
    host = result['hypervisors'][0] if name == 'all' else result['hypervisor']
    assert host['vcpus'] == 0
    assert host['memory_mb'] == 1024
    assert host['local_gb'] is None
    if name == 'all':
        assert result['total_stats']['local_gb'] is None


def test_hypervisor_totals_do_not_hide_missing_hosts_capacity(conn):
    conn.compute.hypervisors.return_value = [
        Hypervisor(id='a', name='a', vcpus=2),
        Hypervisor(id='b', name='b'),
    ]
    conn.compute.get.return_value.status_code = 404
    result = monitoring.get_hypervisor_details()
    assert result['total_stats']['count'] == 2
    assert result['total_stats']['vcpus'] is None


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
    conn.network.ips.return_value = [SimpleNamespace(id='fip-a', project_id='project-a')]
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
    conn.network.ips.return_value = [SimpleNamespace(id='fip-a', project_id='project-a')]
    conn.network.port_forwardings.side_effect = RuntimeError('API unavailable')
    result = network.set_floating_ip_port_forwarding('list', floating_ip_id='fip-a')
    assert result['success'] is False


@pytest.mark.parametrize('action', ['show', 'set', 'delete'])
def test_port_forwarding_rule_actions_accept_floating_ip_address(conn, action):
    conn.network.ips.return_value = [SimpleNamespace(
        id='fip-a', project_id='project-a', floating_ip_address='203.0.113.5')]
    rule = SimpleNamespace(id='rule-a', protocol='tcp')
    conn.network.get_port_forwarding.return_value = rule
    conn.network.update_port_forwarding.return_value = rule
    result = network.set_floating_ip_port_forwarding(
        action, floating_ip_address='203.0.113.5', port_forwarding_id='rule-a',
        description='new',
    )
    assert result['success'], result
    conn.network.ips.assert_called_once_with(project_id='project-a')
    method = {'show': 'get', 'set': 'update', 'delete': 'delete'}[action]
    assert getattr(conn.network, f'{method}_port_forwarding').call_args.kwargs[
        'floating_ip'] == 'fip-a'


@pytest.mark.parametrize('action', ['list', 'create', 'show', 'set', 'delete'])
def test_port_forwarding_refuses_other_project_floating_ip(conn, action):
    conn.network.ips.return_value = [SimpleNamespace(
        id='fip-b', project_id='project-b', floating_ip_address='203.0.113.9')]
    result = network.set_floating_ip_port_forwarding(
        action, floating_ip_address='203.0.113.9', port_forwarding_id='rule-a',
        external_port=18022, internal_port=22, description='new',
    )
    assert result == {'success': False,
                      'message': 'Floating IP not found in the current project'}
    conn.network.create_port_forwarding.assert_not_called()
    conn.network.get_port_forwarding.assert_not_called()
    conn.network.update_port_forwarding.assert_not_called()
    conn.network.delete_port_forwarding.assert_not_called()


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
async def test_quota_list_points_to_get_quota(monkeypatch):
    module = importlib.import_module('mcp_openstack_ops.tools.set_quota')
    setter = Mock()
    monkeypatch.setattr(module, '_set_quota', setter)
    result = json.loads(
        await invoke('set_quota', project_name='test-project', action='list'))
    assert result['error'] == 'READ_ACTION_USE_GET_TOOL'
    assert 'get_quota' in result['message']
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
