"""Reads live in get_* tools; set_* tools refuse read actions."""

import importlib
import json
import pkgutil
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from fastmcp.exceptions import ToolError

import mcp_openstack_ops.mcp_main  # Register tools before importing tool modules.
from mcp_openstack_ops import connection, tools
from mcp_openstack_ops.mcp_main import mcp


def _module(name):
    return importlib.import_module(f'mcp_openstack_ops.tools.{name}')


async def invoke(name, **kwargs):
    handler = getattr(_module(name), name)
    return await getattr(handler, 'fn', handler)(**kwargs)


def _set_tools_with_reads():
    cases = []
    for info in pkgutil.iter_modules(tools.__path__):
        if not info.name.startswith('set_'):
            continue
        for action, target in getattr(_module(info.name), 'READ_ACTIONS', {}).items():
            cases.append((info.name, action, target))
    return cases


READ_CASES = _set_tools_with_reads()
REQUIRED = {
    'set_volume': {'volume_names': 'v'}, 'set_image': {'image_names': 'i'},
    'set_project': {'project_name': 'p'}, 'set_quota': {'project_name': 'p'},
    'set_flavor': {'flavor_name': 'f'}, 'set_server_group': {'group_name': 'g'},
    'set_server_migration': {'instance_name': 'vm'},
    'set_server_volume': {'instance_name': 'vm'},
    'set_image_members': {'image_name': 'i'}, 'set_image_metadata': {'image_name': 'i'},
    'set_image_visibility': {'image_name': 'i'},
    'set_load_balancer_pool_member': {'pool_name_or_id': 'pool'},
}


def test_every_moved_read_is_covered():
    tools_with_reads = {name for name, _, _ in READ_CASES}
    assert len(tools_with_reads) == 34
    assert len(READ_CASES) == 52


@pytest.mark.asyncio
@pytest.mark.parametrize('tool,action,target', READ_CASES)
async def test_set_tool_refuses_read_action_without_cloud_call(
        monkeypatch, tool, action, target):
    monkeypatch.setenv('ALLOW_MODIFY_OPERATIONS', 'true')
    monkeypatch.setattr(connection, 'get_openstack_connection',
                        Mock(side_effect=AssertionError('must not reach cloud')))
    result = json.loads(await invoke(tool, action=action.upper(),
                                     **REQUIRED.get(tool, {})))
    assert result['success'] is False
    assert result['error'] == 'READ_ACTION_USE_GET_TOOL'
    assert target in result['message']
    registered = {t.name for t in await mcp.list_tools()}
    assert target in registered


def _patch_query(monkeypatch, tool, attr='_query', value=None):
    query = Mock(return_value={'success': True} if value is None else value)
    monkeypatch.setattr(_module(tool), attr, query)
    return query


@pytest.mark.asyncio
@pytest.mark.parametrize('tool,kwargs,expected', [
    ('get_network_ports', {}, ((), {'action': 'list', 'all_projects': False})),
    ('get_network_ports', {'port_name': 'p'},
     ((), {'action': 'show', 'port_name': 'p', 'all_projects': False})),
    ('get_subnets', {}, ((), {'action': 'list', 'all_projects': False})),
    ('get_subnets', {'subnet_name': 's'},
     ((), {'action': 'show', 'subnet_name': 's', 'all_projects': False})),
    ('get_network_agents', {}, ((), {'action': 'list'})),
    ('get_alarms', {}, ((), {'action': 'list'})),
    ('get_alarms', {'alarm_name': 'a'}, ((), {'action': 'show', 'alarm_name': 'a'})),
    ('get_domains', {'domain_name': 'd'}, ((), {'action': 'show', 'domain_name': 'd'})),
    ('get_roles', {}, ((), {'action': 'list'})),
    ('get_volume_backups', {'backup_name': 'b'},
     ((), {'action': 'show', 'backup_name': 'b'})),
    ('get_volume_groups', {'group_name': 'g'},
     ((), {'action': 'show', 'group_name': 'g'})),
    ('get_server_migrations', {}, (('', 'list'), {'all_projects': False})),
    ('get_server_migrations', {'all_projects': True}, (('', 'list'), {'all_projects': True})),
    ('get_server_migrations', {'instance_name': 'vm', 'migration_id': 'm'},
     (('vm', 'show'), {'migration_id': 'm', 'all_projects': False})),
    ('get_floating_ip_port_forwardings', {'floating_ip_address': '203.0.113.5'},
     (('list',), {'floating_ip_id': None, 'floating_ip_address': '203.0.113.5',
                  'port_forwarding_id': None})),
    ('get_floating_ip_port_forwardings',
     {'floating_ip_id': 'fip', 'port_forwarding_id': 'pf'},
     (('show',), {'floating_ip_id': 'fip', 'floating_ip_address': None,
                  'port_forwarding_id': 'pf'})),
])
async def test_get_tool_routes_to_service_action(monkeypatch, tool, kwargs, expected):
    query = _patch_query(monkeypatch, tool)
    assert json.loads(await invoke(tool, **kwargs)) == {'success': True}
    args, call_kwargs = expected
    query.assert_called_once_with(*args, **call_kwargs)


@pytest.mark.asyncio
async def test_get_identity_groups_show_uses_domain(monkeypatch):
    query = _patch_query(monkeypatch, 'get_identity_groups', 'set_identity_groups')
    await invoke('get_identity_groups', group_name='ops', domain_id='d1')
    query.assert_called_once_with(action='show', group_name='ops', domain_id='d1')


@pytest.mark.asyncio
@pytest.mark.parametrize('tool,name', [
    ('get_volume_backups', 'backup_name'), ('get_volume_groups', 'group_name')])
async def test_volume_show_refuses_all_projects(monkeypatch, tool, name):
    query = _patch_query(monkeypatch, tool)
    with pytest.raises(ToolError, match='all_projects applies only to the list'):
        await invoke(tool, all_projects=True, **{name: 'x'})
    query.assert_not_called()


@pytest.mark.asyncio
async def test_get_server_migrations_show_needs_instance(monkeypatch):
    query = _patch_query(monkeypatch, 'get_server_migrations')
    result = json.loads(await invoke('get_server_migrations', migration_id='m'))
    assert result['success'] is False
    query.assert_not_called()


@pytest.mark.asyncio
async def test_get_keypair_list_show_returns_service_result(monkeypatch):
    query = _patch_query(monkeypatch, 'get_keypair_list', '_keypair_query',
                         {'success': True, 'keypair': {'name': 'k'}})
    result = json.loads(await invoke('get_keypair_list', keypair_name='k'))
    assert result['keypair']['name'] == 'k'
    query.assert_called_once_with('k', 'show')


@pytest.mark.asyncio
async def test_get_load_balancer_pools_show(monkeypatch):
    query = _patch_query(monkeypatch, 'get_load_balancer_pools', '_pool_query',
                         {'success': True, 'pool': {'id': 'p'}})
    result = json.loads(await invoke('get_load_balancer_pools', pool_name_or_id='p'))
    assert result['result']['pool']['id'] == 'p'
    query.assert_called_once_with(action='show', pool_name_or_id='p')


@pytest.mark.asyncio
async def test_get_load_balancer_status_combines_sections(monkeypatch):
    module = _module('get_load_balancer_status')
    lb = Mock(side_effect=[{'success': True, 'load_balancer_status': {}},
                           {'success': False, 'message': 'stats failed'}])
    listener = Mock(return_value={'success': True, 'listener_stats': {}})
    monkeypatch.setattr(module, '_lb_query', lb)
    monkeypatch.setattr(module, '_listener_query', listener)

    result = json.loads(await invoke('get_load_balancer_status',
                                     lb_name_or_id='lb', listener_name_or_id='l'))

    assert [c.kwargs['action'] for c in lb.call_args_list] == ['status', 'stats']
    listener.assert_called_once_with(action='stats', listener_name_or_id='l')
    assert result['statistics']['message'] == 'stats failed'
    assert result['success'] is False


@pytest.mark.asyncio
async def test_get_load_balancer_status_needs_a_target():
    result = json.loads(await invoke('get_load_balancer_status'))
    assert result['success'] is False


def _fip(fip_id, address):
    return {'id': fip_id, 'floating_ip_address': address}


@pytest.mark.asyncio
@pytest.mark.parametrize('needle', ['fip-2', '203.0.113.2'])
async def test_get_floating_ips_shows_one_by_id_or_address(monkeypatch, needle):
    monkeypatch.setattr(_module('get_floating_ips'), '_get_floating_ips',
                        Mock(return_value=[_fip('fip-1', '203.0.113.1'),
                                           _fip('fip-2', '203.0.113.2')]))
    result = json.loads(await invoke('get_floating_ips', floating_ip=needle))
    assert [row['id'] for row in result['floating_ips']] == ['fip-2']


@pytest.mark.asyncio
async def test_get_floating_ips_unknown_one_is_an_error(monkeypatch):
    monkeypatch.setattr(_module('get_floating_ips'), '_get_floating_ips',
                        Mock(return_value=[_fip('fip-1', '203.0.113.1')]))
    result = await invoke('get_floating_ips', floating_ip='missing')
    assert result.startswith("Error: Floating IP 'missing' not found")


@pytest.mark.asyncio
async def test_get_image_detail_list_filters_by_name_and_reports_tags(monkeypatch):
    from mcp_openstack_ops.services import image as image_service
    conn = SimpleNamespace(current_project_id='project-a', image=Mock())
    conn.image.images.return_value = [
        SimpleNamespace(id='img-1', name='web', status='active', visibility='public',
                        owner='project-a', tags=['golden']),
        SimpleNamespace(id='img-2', name='db', status='active', visibility='public',
                        owner='project-a', tags=None)]
    monkeypatch.setattr(connection, 'get_openstack_connection', lambda: conn)

    rows = image_service.get_image_detail_list()
    assert [row['tags'] for row in rows] == [['golden'], []]
    shown = json.loads(await invoke('get_image_detail_list', image_name='web'))
    assert [row['id'] for row in shown['images']] == ['img-1']
    missing = await invoke('get_image_detail_list', image_name='none')
    assert missing == "Error: Image 'none' not found"



def _migration_conn(monkeypatch):
    from openstack.compute.v2.migration import Migration
    from openstack.compute.v2.server import Server
    conn = SimpleNamespace(current_project_id='project-a', compute=Mock(),
                           identity=Mock())
    conn.compute.servers.return_value = [Server(id='own-vm', name='vm')]
    conn.compute.migrations.return_value = [
        Migration.existing(id=1, server_id='own-vm', project_id='project-a'),
        Migration.existing(id=2, server_id='own-vm'),  # before Nova 2.80
        Migration.existing(id=3, server_id='other-vm', project_id='project-b'),
        Migration.existing(id=4, server_id='other-vm')]
    conn.identity.projects.return_value = [
        SimpleNamespace(id='project-a', name='demo'),
        SimpleNamespace(id='project-b', name='team-b')]
    monkeypatch.setattr(connection, 'get_openstack_connection', lambda: conn)
    monkeypatch.setattr(connection, 'get_current_project_id', lambda: 'project-a')
    return conn


@pytest.mark.asyncio
async def test_migration_list_keeps_current_project(monkeypatch):
    # os-migrations returns every server's migrations to an administrator.
    _migration_conn(monkeypatch)
    result = json.loads(await invoke('get_server_migrations'))
    assert [row['id'] for row in result['migrations']] == [1, 2]
    assert 'scope' not in result


@pytest.mark.asyncio
async def test_migration_list_all_projects_requires_switch(monkeypatch):
    conn = _migration_conn(monkeypatch)
    monkeypatch.delenv('ALLOW_CROSS_PROJECT_READ', raising=False)
    result = json.loads(await invoke('get_server_migrations', all_projects=True))
    assert result['success'] is False
    assert 'ALLOW_CROSS_PROJECT_READ=true' in result['error']
    conn.compute.migrations.assert_not_called()


@pytest.mark.asyncio
async def test_migration_list_all_projects_labels_rows(monkeypatch):
    _migration_conn(monkeypatch)
    monkeypatch.setenv('ALLOW_CROSS_PROJECT_READ', 'true')
    result = json.loads(await invoke('get_server_migrations', all_projects=True))
    assert [row['id'] for row in result['migrations']] == [1, 2, 3, 4]
    assert result['migrations'][2]['project_name'] == 'team-b'
    assert 'warning' not in result['scope']


@pytest.mark.asyncio
async def test_migration_all_projects_needs_no_instance(monkeypatch):
    conn = _migration_conn(monkeypatch)
    monkeypatch.setenv('ALLOW_CROSS_PROJECT_READ', 'true')
    result = json.loads(await invoke('get_server_migrations', instance_name='vm',
                                     all_projects=True))
    assert result['success'] is False
    assert 'without instance_name' in result['error']
    conn.compute.migrations.assert_not_called()
