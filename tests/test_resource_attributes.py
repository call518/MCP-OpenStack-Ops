"""Regression tests: code must read the attribute names that real openstacksdk
resource classes define (e.g. ``is_locked``, not ``locked``).

Each test returns real SDK resource objects from autospec proxies, so reading
a non-existent attribute raises ``AttributeError`` or silently yields the
``getattr`` default, and the asserted output value would be wrong.
"""

from types import SimpleNamespace
from unittest.mock import Mock, create_autospec

import pytest
from openstack.block_storage.v3._proxy import Proxy as StorageProxy
from openstack.block_storage.v3.volume import Volume
from openstack.compute.v2._proxy import Proxy as ComputeProxy
from openstack.compute.v2.hypervisor import Hypervisor
from openstack.compute.v2.migration import Migration
from openstack.compute.v2.server import Server
from openstack.compute.v2.server_group import ServerGroup
from openstack.compute.v2.volume_attachment import VolumeAttachment
from openstack.identity.v3._proxy import Proxy as IdentityProxy
from openstack.identity.v3.project import Project
from openstack.identity.v3.service import Service
from openstack.network.v2._proxy import Proxy as NetworkProxy
from openstack.network.v2.agent import Agent
from openstack.network.v2.quota import Quota
from openstack.orchestration.v1._proxy import Proxy as HeatProxy
from openstack.orchestration.v1.stack import Stack

from mcp_openstack_ops import connection, functions
from mcp_openstack_ops.services import compute, identity, monitoring
from mcp_openstack_ops.services import orchestration, storage


@pytest.fixture
def conn(monkeypatch):
    value = SimpleNamespace(
        current_project_id='project-a',
        compute=create_autospec(ComputeProxy, instance=True),
        network=create_autospec(NetworkProxy, instance=True),
        block_storage=create_autospec(StorageProxy, instance=True),
        identity=create_autospec(IdentityProxy, instance=True),
        orchestration=create_autospec(HeatProxy, instance=True),
        session=Mock(), config=Mock(region_name='RegionOne'),
    )
    value.volume = value.block_storage
    for name in ('servers', 'hypervisors', 'services', 'keypairs',
                 'server_groups', 'migrations'):
        getattr(value.compute, name).return_value = []
    for name in ('networks', 'subnets', 'ports', 'routers', 'ips',
                 'security_groups', 'agents'):
        getattr(value.network, name).return_value = []
    value.block_storage.volumes.return_value = []
    value.identity.services.return_value = []
    monkeypatch.setattr(connection, 'get_openstack_connection', lambda: value)
    monkeypatch.setattr(connection, 'get_current_project_id', lambda: 'project-a')
    monkeypatch.setattr(functions, 'get_openstack_connection', lambda: value)
    monkeypatch.setattr(identity, 'get_openstack_connection', lambda: value)
    return value


def _server(**attrs):
    return Server.existing(id='s1', name='vm', project_id='project-a', **attrs)


# --- compute -------------------------------------------------------------

def test_instance_details_reports_sdk_is_locked(conn):
    conn.compute.servers.return_value = [_server(is_locked=True)]

    result = compute.get_instance_details(enrich_images=False)

    assert result['instances'][0]['locked'] is True


def test_server_groups_list_reports_sdk_member_ids(conn):
    conn.compute.server_groups.return_value = [ServerGroup.existing(
        id='g1', name='grp', project_id='project-a', policies=['affinity'],
        member_ids=['s1', 's2'])]

    group = compute.get_server_groups()[0]

    assert group['members'] == ['s1', 's2']
    assert group['member_count'] == 2


def test_server_group_show_reports_sdk_member_ids(conn):
    conn.compute.server_groups.return_value = [ServerGroup.existing(
        id='g1', name='grp', project_id='project-a', member_ids=['s1'])]

    result = compute.set_server_group('grp', 'show')

    assert result['server_group']['members'] == ['s1']


def test_server_group_create_reports_sdk_member_ids(conn):
    conn.compute.create_server_group.return_value = ServerGroup.existing(
        id='g1', name='grp', policies=['affinity'], member_ids=['s1'])

    result = compute.set_server_group('grp', 'create', policies=['affinity'])

    assert result['server_group']['members'] == ['s1']


def test_migration_list_reports_sdk_server_id(conn):
    conn.compute.migrations.return_value = [Migration.existing(
        id='m1', server_id='s1', status='completed')]

    result = compute.set_server_migration('', 'list')

    assert result['migrations'][0]['server_id'] == 's1'


def test_server_groups_list_handles_microversion_2_64_policy(conn):
    # Nova 2.64+ returns 'policy' and no 'policies' list.
    conn.compute.server_groups.return_value = [ServerGroup.existing(
        id='g1', name='grp', project_id='project-a', policy='soft-anti-affinity',
        member_ids=[])]

    group = compute.get_server_groups()[0]

    assert group['policies'] == ['soft-anti-affinity']


def test_migration_list_for_named_server_uses_server_migrations(conn):
    server = _server()
    conn.compute.servers.return_value = [server]
    conn.compute.server_migrations.return_value = []

    result = compute.set_server_migration('vm', 'list')

    assert result['success'] is True
    conn.compute.server_migrations.assert_called_once_with(server.id)


def test_migration_list_for_unknown_server_is_an_error(conn):
    result = compute.set_server_migration('missing', 'list')

    assert result['success'] is False


def test_migration_list_failure_is_reported(conn):
    conn.compute.migrations.side_effect = RuntimeError('policy denied')

    result = compute.set_server_migration('', 'list')

    assert result['success'] is False
    assert 'policy denied' in result['message']


def test_evacuate_omits_on_shared_storage_by_default(conn):
    server = _server()
    conn.compute.servers.return_value = [server]

    result = compute.set_server_migration('vm', 'evacuate', host='cmp2')

    assert result['success'] is True
    conn.compute.evacuate_server.assert_called_once_with(server, host='cmp2')


def test_evacuate_sends_on_shared_storage_only_when_requested(conn):
    server = _server()
    conn.compute.servers.return_value = [server]

    compute.set_server_migration('vm', 'evacuate', on_shared_storage=True)

    conn.compute.evacuate_server.assert_called_once_with(
        server, on_shared_storage=True)


# --- storage -------------------------------------------------------------

def test_volume_list_reports_sdk_multiattach_and_source_volume(conn):
    conn.block_storage.volumes.return_value = [Volume.existing(
        id='v1', name='data', project_id='project-a', attachments=[],
        is_multiattach=True, source_volume_id='v0')]

    volume = storage.get_volume_list()[0]

    assert volume['multiattach'] is True
    assert volume['source_volid'] == 'v0'


def test_attach_precheck_honours_sdk_is_multiattach(conn):
    conn.compute.servers.return_value = [_server()]
    conn.block_storage.volumes.return_value = [Volume.existing(
        id='v1', name='data', project_id='project-a', status='reserved',
        is_multiattach=True)]
    conn.compute.create_volume_attachment.return_value = \
        VolumeAttachment.existing(id='a1', device='/dev/vdb')

    result = storage.set_server_volume('vm', 'attach', volume_name='data')

    assert result['success'] is True
    conn.compute.create_volume_attachment.assert_called_once_with('s1', 'v1')


# --- network quota -------------------------------------------------------

def test_get_quota_reports_sdk_floating_ips(conn):
    conn.network.get_quota.return_value = Quota.existing(floating_ips=7)

    result = monitoring.get_quota()

    assert result['quotas']['network']['limits']['floatingips'] == 7


def test_project_info_reports_sdk_floating_ips(conn):
    conn.identity.get_project.return_value = Project.existing(
        id='project-a', name='demo')
    conn.network.get_quota.return_value = Quota.existing(floating_ips=7)

    result = identity.get_project_info()

    assert result['quotas']['network']['floatingips'] == 7


# --- hypervisor statistics -----------------------------------------------

def test_hypervisor_details_notes_removed_statistics_api(conn):
    conn.compute.hypervisors.return_value = [Hypervisor.existing(
        id='h1', name='cmp1', memory_size=4096)]
    conn.compute.get.return_value = Mock(status_code=404)

    result = monitoring.get_hypervisor_details('all')

    assert result['enhanced_stats'] is None
    assert 'HTTP 404' in result['enhanced_stats_note']


# --- orchestration -------------------------------------------------------

def _stack(**attrs):
    # Heat list responses carry the project only in the self link.
    link = {'rel': 'self',
            'href': 'https://heat.example/v1/project-a/stacks/web/st1'}
    return Stack.existing(id='st1', name='web', links=[link],
                          status='CREATE_COMPLETE', **attrs)


def test_heat_stacks_report_sdk_owner_id(conn):
    conn.orchestration.stacks.return_value = [_stack(owner_id='parent-1')]

    stacks = orchestration.get_heat_stacks()

    assert stacks[0]['owner'] == 'parent-1'


def test_heat_stack_update_reports_sdk_status(conn):
    conn.orchestration.stacks.return_value = [_stack()]
    conn.orchestration.update_stack.return_value = Stack.existing(
        id='st1', name='web', status='UPDATE_IN_PROGRESS')

    result = orchestration.set_heat_stack(
        'web', 'update', template={'heat_template_version': '2018-08-31'})

    assert result['success'] is True
    assert result['stack']['status'] == 'UPDATE_IN_PROGRESS'


# --- functions.py ---------------------------------------------------------

def test_compute_agents_list_reads_sdk_hypervisor_capacity(conn):
    conn.compute.hypervisors.return_value = [Hypervisor.existing(
        id='h1', name='cmp1', status='enabled', state='up',
        memory_size=4096, local_disk_size=100, vcpus=8)]

    result = functions.set_compute_agents('list')

    assert result['hypervisors'][0]['memory_mb'] == 4096
    conn.compute.hypervisors.assert_called_once_with(details=True)


def test_services_list_reports_sdk_is_enabled(conn):
    conn.identity.services.return_value = [Service.existing(
        id='svc1', name='nova', type='compute', is_enabled=False)]

    result = functions.set_services('list')

    assert result['services'][0]['enabled'] is False


def test_service_logs_list_reports_sdk_agent_admin_state(conn):
    conn.network.agents.return_value = [Agent.existing(
        id='ag1', agent_type='L3 agent', host='net1',
        is_admin_state_up=False, is_alive=True)]

    result = functions.set_service_logs('list')

    network = [s for s in result['services'] if s['type'] == 'network']
    assert network == [{'name': 'L3 agent', 'type': 'network', 'host': 'net1',
                        'status': 'disabled', 'state': 'up'}]
