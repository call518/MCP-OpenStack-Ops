"""Regression tests for real API operations and honest monitoring output."""

from types import SimpleNamespace
from unittest.mock import Mock, create_autospec

import pytest
from openstack.block_storage.v3._proxy import Proxy as StorageProxy
from openstack.block_storage.v3.backup import Backup
from openstack.block_storage.v3.group import Group
from openstack.block_storage.v3.type import Type
from openstack.compute.v2._proxy import Proxy as ComputeProxy
from openstack.compute.v2.flavor import Flavor
from openstack.compute.v2.hypervisor import Hypervisor
from openstack.compute.v2.server import Server
from openstack.identity.v3._proxy import Proxy as IdentityProxy
from openstack.identity.v3.domain import Domain
from openstack.identity.v3.group import Group as IdentityGroup
from openstack.identity.v3.user import User
from openstack.image.v2._proxy import Proxy as ImageProxy
from openstack.image.v2.image import Image
from openstack.image.v2.member import Member
from openstack.network.v2._proxy import Proxy as NetworkProxy
from openstack.network.v2.agent import Agent
from openstack.network.v2.network import Network
from openstack.network.v2.qos_policy import QoSPolicy
from openstack.network.v2.router import Router
from openstack.network.v2.security_group import SecurityGroup
from openstack.network.v2.subnet import Subnet
from openstack.orchestration.v1._proxy import Proxy as HeatProxy
from openstack.orchestration.v1.stack import Stack

from mcp_openstack_ops import connection, functions
from mcp_openstack_ops.services import alarms, identity, image, monitoring, network
from mcp_openstack_ops.services import orchestration, storage


@pytest.fixture
def conn(monkeypatch):
    value = SimpleNamespace(
        current_project_id='project-a',
        compute=create_autospec(ComputeProxy, instance=True),
        network=create_autospec(NetworkProxy, instance=True),
        block_storage=create_autospec(StorageProxy, instance=True),
        identity=create_autospec(IdentityProxy, instance=True),
        image=create_autospec(ImageProxy, instance=True),
        orchestration=create_autospec(HeatProxy, instance=True),
        session=Mock(), config=Mock(region_name='RegionOne'),
    )
    value.volume = value.block_storage
    value.compute.servers.return_value = []
    value.compute.flavors.return_value = []
    value.compute.hypervisors.return_value = []
    value.identity.projects.return_value = []
    value.identity.users.return_value = []
    for name in ('networks', 'subnets', 'ports', 'routers', 'ips'):
        getattr(value.network, name).return_value = []
    value.block_storage.volumes.return_value = []
    value.block_storage.snapshots.return_value = []
    value.config.get_interface.return_value = 'internal'
    monkeypatch.setattr(connection, 'get_openstack_connection', lambda: value)
    monkeypatch.setattr(connection, 'get_current_project_id', lambda: 'project-a')
    monkeypatch.setattr(functions, 'get_openstack_connection', lambda: value)
    monkeypatch.setattr(identity, 'get_openstack_connection', lambda: value)
    monkeypatch.setattr(alarms, 'get_openstack_connection', lambda: value)
    return value


@pytest.fixture
def alarm_api(conn, monkeypatch):
    api = Mock()
    monkeypatch.setattr(alarms, 'Adapter', Mock(return_value=api))
    api.get.return_value.json.return_value = [
        {'alarm_id': 'alarm-a', 'name': 'cpu-high', 'project_id': 'project-a'},
        {'alarm_id': 'alarm-b', 'name': 'other', 'project_id': 'project-b'},
    ]
    return api


def test_alarm_create_posts_real_gnocchi_rule(alarm_api):
    alarm_api.post.return_value.json.return_value = {'alarm_id': 'created'}
    result = alarms.set_alarms('create', 'cpu-high', 'server-a', 0)
    assert result == {'success': True, 'alarm': {'alarm_id': 'created'}}
    body = alarm_api.post.call_args.kwargs['json']
    assert body['gnocchi_resources_threshold_rule']['threshold'] == 0
    assert body['gnocchi_resources_threshold_rule']['resource_id'] == 'server-a'
    assert body['project_id'] == 'project-a'
    alarm_api.post.return_value.raise_for_status.assert_called_once()


@pytest.mark.parametrize('threshold', [None, float('nan'), float('inf')])
def test_invalid_alarm_threshold_never_posts(alarm_api, threshold):
    assert not alarms.set_alarms('create', 'name', 'server-a', threshold)['success']
    alarm_api.post.assert_not_called()


def test_alarm_list_is_project_scoped(alarm_api):
    result = alarms.set_alarms('list')
    assert result['count'] == 1
    assert result['alarms'][0]['alarm_id'] == 'alarm-a'


def test_alarm_missing_delete_fails_without_write(alarm_api):
    assert not alarms.set_alarms('delete', 'nonexistent')['success']
    alarm_api.delete.assert_not_called()


def test_alarm_ambiguous_name_fails(alarm_api):
    alarm_api.get.return_value.json.return_value = [
        {'alarm_id': str(i), 'name': 'duplicate', 'project_id': 'project-a'}
        for i in range(2)
    ]
    assert not alarms.set_alarms('delete', 'duplicate')['success']
    alarm_api.delete.assert_not_called()


def test_alarm_delete_calls_api_and_propagates_failure(alarm_api):
    assert alarms.set_alarms('delete', 'alarm-a')['success']
    alarm_api.delete.assert_called_once_with('/v2/alarms/alarm-a')
    alarm_api.delete.return_value.raise_for_status.side_effect = RuntimeError('denied')
    assert not alarms.set_alarms('delete', 'alarm-a')['success']


def test_alarm_show_uses_real_detail_response(alarm_api):
    alarm_api.get.return_value.json.side_effect = [
        [{'alarm_id': 'alarm-a', 'project_id': 'project-a'}],
        {'alarm_id': 'alarm-a', 'state': 'alarm'},
    ]
    assert alarms.set_alarms('show', 'alarm-a')['alarm_details']['state'] == 'alarm'


@pytest.mark.parametrize('action,enabled', [('enable', True), ('disable', False)])
def test_agent_state_uses_sdk(conn, action, enabled):
    conn.network.update_agent.return_value = Agent(id='agent-a', admin_state_up=enabled)
    assert network.set_network_agents(action, 'agent-a')['success']
    conn.network.update_agent.assert_called_once_with('agent-a',
        is_admin_state_up=enabled)


def test_agent_list_and_missing_id(conn):
    conn.network.agents.return_value = [Agent(id='agent-a')]
    assert network.set_network_agents('list')['count'] == 1
    assert not network.set_network_agents('enable')['success']
    conn.network.update_agent.assert_not_called()


def test_qos_policy_create_and_list(conn):
    policy = QoSPolicy(id='qos-a', name='qos', project_id='project-a')
    conn.network.create_qos_policy.return_value = policy
    assert network.set_network_qos_policies('create', 'qos', shared=True)['success']
    conn.network.create_qos_policy.assert_called_once_with(
        name='qos', project_id='project-a', description='', is_shared=True,
    )
    conn.network.qos_policies.return_value = [
        policy, QoSPolicy(id='qos-b', name='other', project_id='project-b'),
    ]
    assert network.set_network_qos_policies('list')['count'] == 1
    assert not network.set_network_qos_policies('delete', 'other')['success']
    conn.network.delete_qos_policy.assert_not_called()
    assert network.set_network_qos_policies('delete', 'qos-a')['success']
    conn.network.delete_qos_policy.assert_called_once_with(policy, ignore_missing=False)


@pytest.mark.parametrize('start,end,total', [
    ('192.0.2.10', '192.0.2.19', 10),
    ('192.0.2.10', '192.0.2.10', 1),
    ('2001:db8::1', '2001:db8::10', 16),
])
def test_floating_ip_pool_counts_actual_addresses(conn, start, end, total):
    conn.network.networks.return_value = [Network(id='net', is_router_external=True)]
    conn.network.subnets.return_value = [Subnet(
        network_id='net', allocation_pools=[{'start': start, 'end': end}],
    )]
    result = network.get_floating_ip_pools()[0]
    assert result['total_ips'] == total
    assert result['available_ips'] is None
    assert result['used_ips_scope'] == 'visible_floating_ip_allocations'


def test_bad_pool_range_does_not_fabricate_capacity(conn):
    conn.network.networks.return_value = [Network(id='net', is_router_external=True)]
    conn.network.subnets.return_value = [Subnet(
        network_id='net', allocation_pools=[{'start': '192.0.2.19',
            'end': '192.0.2.10'}],
    )]
    assert 'error' in network.get_floating_ip_pools()[0]


def test_monitoring_separates_capacity_quota_and_allocations(conn):
    conn.compute.servers.return_value = [Server(
        id='server', project_id='project-a', status='ACTIVE',
        flavor={'id': 'flavor-a'},
    )]
    conn.compute.get_flavor.return_value = Flavor(
        id='flavor-a', vcpus=2, ram=4096, disk=10, swap=64, ephemeral=1,
    )
    conn.compute.hypervisors.return_value = [Hypervisor(
        id='hv', vcpus=64, memory_mb=131072, local_gb=1000,
    )]
    conn.compute.get_quota_set.return_value = SimpleNamespace(cores=12, ram=24576)
    result = monitoring.get_resource_monitoring()['monitoring_data']['compute']
    assert result['total_vcpus'] == 64
    assert result['total_memory_mb'] == 131072
    assert result['total_disk_gb'] == 1000
    assert result['quota_limits']['vcpus'] == 12
    assert result['used_vcpus'] == 2
    assert result['used_disk_gb'] == 11.0625
    assert result['usage_basis'] == 'flavor_allocations_not_live_utilization'


def test_unavailable_capacity_stays_unknown(conn):
    conn.compute.hypervisors.side_effect = RuntimeError('denied')
    result = monitoring.get_resource_monitoring()['monitoring_data']['compute']
    assert result['total_vcpus'] is None
    assert result['total_memory_mb'] is None
    assert result['total_disk_gb'] is None
    assert result['total_hypervisors'] is None


def test_incomplete_flavors_are_unknown_not_zero(conn):
    conn.compute.servers.return_value = [Server(
        id='server', project_id='project-a', flavor={}, status='ACTIVE',
    )]
    result = monitoring.get_resource_monitoring()['monitoring_data']['compute']
    assert result['used_vcpus'] is None
    assert result['allocation_errors']


def test_period_usage_passes_dates_to_nova(conn):
    conn.compute.get.return_value.json.return_value = {'tenant_usage': {
        'tenant_id': 'project-a', 'total_vcpus_usage': 48,
        'total_memory_mb_usage': 1024, 'total_local_gb_usage': 10,
        'total_hours': 24, 'server_usages': [],
    }}
    result = monitoring.get_usage_statistics('2026-01-01', '2026-01-03')
    assert result['success']
    conn.compute.get.assert_called_once_with(
        '/os-simple-tenant-usage/project-a',
        params={'start': '2026-01-01T00:00:00', 'end': '2026-01-03T00:00:00',
            'limit': 1000},
        microversion='2.40',
    )
    data = result['usage_statistics']
    assert data['period_compute']['total_vcpus_usage'] == 48
    assert data['period']['timezone'] == 'UTC'
    assert 'network' in data['snapshot_fields']


@pytest.mark.parametrize('start,end', [
    ('bad', '2026-01-03'), ('2026-01-03', '2026-01-01'),
    ('2026-01-01', '2026-01-01'),
])
def test_invalid_usage_range_never_calls_api(conn, start, end):
    assert not monitoring.get_usage_statistics(start, end)['success']
    conn.compute.get.assert_not_called()


def test_usage_api_failure_has_no_snapshot_fallback(conn):
    conn.compute.get.side_effect = RuntimeError('usage extension unavailable')
    assert not monitoring.get_usage_statistics('2026-01-01', '2026-01-02')['success']
    conn.compute.servers.assert_not_called()


def test_service_connection_failure_never_reports_up(conn, monkeypatch):
    monkeypatch.setattr(functions, 'get_openstack_connection',
        Mock(side_effect=RuntimeError('offline')))
    assert all(s['state'] == 'unknown' for s in functions.get_service_status())


def test_failed_component_is_in_service_results(conn):
    conn.compute.services.side_effect = RuntimeError('denied')
    conn.network.agents.return_value = [Agent(
        id='agent-a', binary='neutron-agent', host='host', alive=True,
            admin_state_up=True,
    )]
    conn.block_storage.services.return_value = []
    conn.image.images.return_value = []
    conn.orchestration.stacks.return_value = []
    result = functions.get_service_status()
    assert next(s for s in result if s['service_type'] == 'compute')[
        'state'] == 'unknown'
    assert next(s for s in result if s['service_type'] == 'network')['state'] == 'up'
    conn.orchestration.stacks.assert_called_once_with(limit=1)


@pytest.mark.parametrize(
    'service,func,name,model,list_method,create_method,delete_method', [
    ('network', network.set_routers, 'router', Router, 'routers', 'create_router',
        'delete_router'),
    ('network', network.set_security_groups, 'group', SecurityGroup, 'security_groups',
        'create_security_group', 'delete_security_group'),
    ('block_storage', storage.set_volume_types, 'type', Type, 'types', 'create_type',
        'delete_type'),
])
def test_new_resource_create_delete(conn, service, func, name, model, list_method,
    create_method, delete_method):
    api = getattr(conn, service)
    resource = model(id='resource-a', name=name, project_id='project-a')
    getattr(api, create_method).return_value = resource
    assert func('create', name)['success']
    getattr(api, create_method).assert_called_once_with(name=name, description='')
    getattr(api, list_method).return_value = [resource]
    if service == 'block_storage':
        api.find_type.return_value = resource
    assert func('delete', name)['success']
    getattr(api, delete_method).assert_called_once_with(resource, ignore_missing=False)


def test_router_cross_project_delete_rejected(conn):
    conn.network.routers.return_value = [Router(id='router-a', name='other',
        project_id='project-b')]
    assert not network.set_routers('delete', 'router-a')['success']
    conn.network.delete_router.assert_not_called()


def test_groups_create_requires_volume_types_and_resolves_ids(conn):
    assert not storage.set_volume_groups('create', 'group')['success']
    conn.block_storage.create_group.assert_not_called()
    conn.block_storage.find_group_type.return_value = SimpleNamespace(id='group-type')
    conn.block_storage.find_type.return_value = Type(id='volume-type')
    conn.block_storage.create_group.return_value = Group(id='group-a')
    assert storage.set_volume_groups('create', 'group',
        volume_types=['fast'])['success']
    conn.block_storage.create_group.assert_called_once_with(
        name='group', group_type='group-type', volume_types=['volume-type'],
            description='',
    )


def test_groups_list_show_delete(conn):
    group = Group(id='group-a', name='group')
    conn.block_storage.groups.return_value = [group]
    conn.block_storage.get_group.return_value = group
    assert storage.set_volume_groups('list')['count'] == 1
    assert storage.set_volume_groups('show', 'group')['group']['id'] == 'group-a'
    assert storage.set_volume_groups('delete', 'group')['success']
    conn.block_storage.delete_group.assert_called_once_with(group, delete_volumes=False)


def test_cinder_qos_create_uses_flat_specs(conn):
    api = conn.block_storage
    api.post.return_value.json.return_value = {'qos_specs': {'id': 'qos-a'}}
    assert storage.set_volume_qos('create', 'fast',
        specs={'read_iops_sec': '100'})['success']
    api.post.assert_called_once_with('/qos-specs', json={
        'qos_specs': {'name': 'fast', 'consumer': 'back-end', 'read_iops_sec': '100'},
    })
    api.post.return_value.raise_for_status.assert_called_once()


def test_cinder_qos_list_show_set_delete_and_errors(conn):
    api = conn.block_storage
    policy = {'id': 'qos-a', 'name': 'fast'}
    api.get.return_value.json.return_value = {'qos_specs': [policy]}
    assert storage.set_volume_qos('list')['count'] == 1
    api.get.return_value.json.side_effect = [{'qos_specs': [policy]},
        {'qos_specs': policy}]
    assert storage.set_volume_qos('show', 'fast')['qos_policy']['id'] == 'qos-a'
    api.get.return_value.json.side_effect = None
    api.put.return_value.json.return_value = {'qos_specs': {'read_iops_sec': '200'}}
    assert storage.set_volume_qos('set', 'fast',
        specs={'read_iops_sec': '200'})['success']
    api.put.assert_called_once_with('/qos-specs/qos-a',
        json={'qos_specs': {'read_iops_sec': '200'}})
    assert storage.set_volume_qos('delete', 'fast', force=True)['success']
    api.delete.assert_called_once_with('/qos-specs/qos-a', params={'force': 'true'})
    api.delete.return_value.raise_for_status.side_effect = RuntimeError('denied')
    assert not storage.set_volume_qos('delete', 'fast')['success']


def test_backup_actions_reach_sdk(conn):
    api = conn.block_storage
    backup = Backup(id='backup-a', name='backup')
    api.backups.return_value = [backup]
    api.find_backup.return_value = backup
    api.create_backup.return_value = backup
    api.restore_backup.return_value = backup
    assert storage.set_volume_backups('list')['count'] == 1
    assert storage.set_volume_backups('show', 'backup')['success']
    assert not storage.set_volume_backups('create', 'backup')['success']
    assert storage.set_volume_backups('create', 'backup',
        volume_id='volume-a')['success']
    assert storage.set_volume_backups('restore', 'backup',
        volume_name='restored')['success']
    api.restore_backup.assert_called_once_with(backup, volume_id=None, name='restored')
    assert storage.set_volume_backups('delete', 'backup')['success']
    api.delete_backup.assert_called_once_with(backup, ignore_missing=False)


def test_transfer_listing_excludes_authorization_key(conn):
    transfer = Mock()
    transfer.to_dict.return_value = {'id': 'transfer-a',
        'auth_key': 'never-return-this'}
    conn.block_storage.transfers.return_value = [transfer]
    assert storage.get_volume_transfers()['transfers'] == [{'id': 'transfer-a'}]


def test_domain_delete_requires_explicit_disable(conn):
    api = conn.identity
    api.find_domain.return_value = Domain(id='domain-a', is_enabled=True)
    assert not identity.set_domains('delete', 'domain-a')['success']
    api.delete_domain.assert_not_called()
    api.update_domain.return_value = Domain(id='domain-a', is_enabled=False)
    assert identity.set_domains('update', 'domain-a', enabled=False)['success']
    api.find_domain.return_value = Domain(id='domain-a', is_enabled=False)
    assert identity.set_domains('delete', 'domain-a')['success']
    api.delete_domain.assert_called_once_with(api.find_domain.return_value,
        ignore_missing=False)


def test_identity_group_delete(conn):
    group = IdentityGroup(id='group-a', name='team')
    conn.identity.find_group.return_value = group
    assert functions.set_identity_groups('delete', 'team')['success']
    conn.identity.delete_group.assert_called_once_with(group, ignore_missing=False)


def test_user_password_only_from_environment(conn, monkeypatch):
    api = conn.identity
    assert not identity.set_users('create', 'operator')['success']
    api.create_user.assert_not_called()
    monkeypatch.setenv('TEST_NEW_USER_PASSWORD', 'test-only-password')
    api.create_user.return_value = User(id='user-a', name='operator',
        domain_id='default', is_enabled=True)
    result = identity.set_users('create', 'operator',
        password_env='TEST_NEW_USER_PASSWORD')
    assert result['success']
    assert 'test-only-password' not in str(result)
    api.create_user.assert_called_once_with(
        name='operator', domain_id='default', password='test-only-password',
        description='', is_enabled=True,
    )
    api.create_user.side_effect = RuntimeError('payload contained test-only-password')
    assert 'test-only-password' not in str(identity.set_users('create', 'operator',
        password_env='TEST_NEW_USER_PASSWORD'))


def test_user_delete_protects_current_identity(conn):
    user = User(id='user-a', name='operator')
    conn.identity.find_user.return_value = user
    conn.session.get_user_id.return_value = 'user-a'
    assert not identity.set_users('delete', 'operator')['success']
    conn.identity.delete_user.assert_not_called()
    conn.session.get_user_id.return_value = 'admin'
    assert identity.set_users('delete', 'operator')['success']
    conn.identity.delete_user.assert_called_once_with(user, ignore_missing=False)


def test_glance_member_sdk_argument_order(conn):
    conn.image.find_image.return_value = Image(
        id='image-a', name='shared', owner='project-a',
    )
    conn.image.add_member.return_value = Member(member='project-b', status='pending')
    assert image.set_image_members('add', 'shared', 'project-b')['success']
    conn.image.add_member.assert_called_once_with('image-a', member_id='project-b')
    assert image.set_image_members('remove', 'shared', 'project-b')['success']
    conn.image.remove_member.assert_called_once_with('project-b', image='image-a',
        ignore_missing=False)


@pytest.mark.parametrize('section', ['resources', 'events', 'template', 'outputs'])
def test_heat_queries_use_actual_sdk_or_template_response(conn, section):
    api = conn.orchestration
    stack = Stack(id='stack-a', name='app', outputs=[{'output_key': 'ip',
        'output_value': '192.0.2.1'}])
    api.find_stack.return_value = stack
    api.resources.return_value = [Router(id='resource-a')]
    api.stack_events.return_value = [Router(id='event-a')]
    api.get_stack.return_value = stack
    template = {'AWSTemplateFormatVersion': '2010-09-09', 'Resources': {}}
    api.get.return_value.json.return_value = template
    result = orchestration.get_heat_stack_details('app', section)
    assert result['success']
    assert result['stack_id'] == 'stack-a'
    if section == 'template':
        assert result[section] == template
        api.get.assert_called_once_with('/stacks/app/stack-a/template')
    elif section == 'outputs':
        assert result[section][0]['output_key'] == 'ip'
    else:
        assert len(result[section]) == 1


def test_unsupported_logs_and_telemetry_do_not_report_success(conn):
    assert not functions.set_service_logs('show', 'nova')['success']
    assert not functions.set_metrics('show', resource_id='server-a')['success']


def test_usage_pagination_merges_totals_without_following_hostile_url(conn):
    def page(instance_id, hours, more):
        return {
            'tenant_usage': {
                'tenant_id': 'project-a', 'total_hours': hours,
                'total_vcpus_usage': hours * 2,
                'total_memory_mb_usage': hours * 4096,
                'total_local_gb_usage': hours * 10,
                'server_usages': [{'instance_id': instance_id}],
            },
            'tenant_usage_links': (
                [{'rel': 'next', 'href': 'https://untrusted.invalid/'}]
                if more else []
            ),
        }
    conn.compute.get.return_value.json.side_effect = [
        page('server-a', 10, True), page('server-b', 20, False),
    ]
    result = monitoring.get_usage_statistics('2026-01-01', '2026-01-03')
    assert result['success']
    data = result['usage_statistics']['period_compute']
    assert data['total_vcpus_usage'] == 60
    assert data['total_hours'] == 30
    assert len(data['server_usages']) == 2
    calls = conn.compute.get.call_args_list
    assert calls[0].args == calls[1].args
    assert calls[1].kwargs['params']['marker'] == 'server-a'
    assert calls[0].kwargs['params'].get('marker') is None


def test_usage_repeated_page_fails_instead_of_double_counting(conn):
    conn.compute.get.return_value.json.return_value = {
        'tenant_usage': {
            'tenant_id': 'project-a', 'total_hours': 1,
            'total_vcpus_usage': 2, 'total_memory_mb_usage': 4096,
            'total_local_gb_usage': 10,
            'server_usages': [{'instance_id': 'server-a'}],
        },
        'tenant_usage_links': [{'rel': 'next'}],
    }
    assert not monitoring.get_usage_statistics('2026-01-01', '2026-01-03')['success']
    assert conn.compute.get.call_count == 2


def test_usage_rejects_another_projects_response(conn):
    conn.compute.get.return_value.json.return_value = {
        'tenant_usage': {'tenant_id': 'project-b', 'server_usages': []},
    }
    assert not monitoring.get_usage_statistics('2026-01-01', '2026-01-03')['success']


def test_empty_period_has_real_zero_usage(conn):
    conn.compute.get.return_value.json.return_value = {'tenant_usage': {}}
    result = monitoring.get_usage_statistics('2026-01-01', '2026-01-03')
    assert result['success']
    assert result['usage_statistics']['period_compute']['total_hours'] == 0


def test_snapshot_failure_is_reported_as_partial(conn):
    conn.compute.get.return_value.json.return_value = {'tenant_usage': {}}
    conn.network.networks.side_effect = RuntimeError('denied')
    result = monitoring.get_usage_statistics('2026-01-01', '2026-01-03')
    assert result['success'] is False
    assert result['partial'] is True
    assert result['failed_sections'] == ['network']
    assert result['usage_statistics']['period_compute']['total_hours'] == 0


def test_ambiguous_router_name_cannot_delete_arbitrary_resource(conn):
    conn.network.routers.return_value = [
        Router(id=f'router-{i}', name='duplicate', project_id='project-a')
        for i in range(2)
    ]
    assert not network.set_routers('delete', 'duplicate')['success']
    conn.network.delete_router.assert_not_called()


def test_alarm_pagination(alarm_api):
    alarm_api.get.return_value.json.side_effect = [
        [{'alarm_id': str(i), 'project_id': 'project-a'} for i in range(100)],
        [{'alarm_id': '100', 'project_id': 'project-a'}],
    ]
    assert alarms.set_alarms('list')['count'] == 101
    assert alarm_api.get.call_args_list[1].kwargs['params']['marker'] == '99'


@pytest.mark.parametrize('func,args,api_name,method_name', [
    (network.set_network_agents, ('enable', 'agent-a'), 'network', 'update_agent'),
    (network.set_network_qos_policies, ('create', 'qos'), 'network',
        'create_qos_policy'),
    (network.set_routers, ('create', 'router'), 'network', 'create_router'),
    (network.set_security_groups, ('create', 'group'), 'network',
        'create_security_group'),
    (storage.set_volume_types, ('create', 'fast'), 'block_storage', 'create_type'),
    (orchestration.get_heat_stack_details, ('app',), 'orchestration', 'find_stack'),
])
def test_api_denial_never_reports_success(conn, func, args, api_name, method_name):
    getattr(getattr(conn, api_name), method_name).side_effect = RuntimeError('denied')
    assert func(*args)['success'] is False


def test_usage_snapshot_excludes_other_projects_networks(conn):
    conn.compute.get.return_value.json.return_value = {'tenant_usage': {}}
    conn.network.networks.return_value = [
        Network(id='owned', project_id='project-a'),
        Network(id='shared', project_id='project-b', is_shared=True),
    ]
    result = monitoring.get_usage_statistics('2026-01-01', '2026-01-03')
    assert result['success']
    assert result['usage_statistics']['network']['total_networks'] == 1


def test_image_sharing_cannot_modify_another_projects_image(conn):
    conn.image.find_image.return_value = Image(
        id='image-b', name='shared', owner='project-b',
    )
    assert not image.set_image_members('add', 'shared', 'recipient')['success']
    conn.image.add_member.assert_not_called()


def test_image_member_list_uses_sdk(conn):
    conn.image.find_image.return_value = Image(
        id='image-a', name='shared', owner='project-a',
    )
    conn.image.members.return_value = [
        Member(member='project-b', image_id='image-a', status='pending'),
    ]
    result = image.set_image_members('list', 'shared')
    assert result['count'] == 1
    assert result['members'][0]['member_id'] == 'project-b'
    conn.image.members.assert_called_once_with('image-a')
