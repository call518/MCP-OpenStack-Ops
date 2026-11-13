"""Cross-project reads (issue #86): opt-in switch, policy denial, and scope."""

import importlib
import json
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from fastmcp.exceptions import ToolError
from openstack import exceptions as sdk_exceptions

import mcp_openstack_ops.mcp_main  # noqa: F401  Register tools before importing them.
from mcp_openstack_ops import connection
from mcp_openstack_ops.services import compute, identity, storage

CURRENT = 'project-a'
OTHER = 'project-b'


def _tool(name):
    module = importlib.import_module(f'mcp_openstack_ops.tools.{name}')
    tool = getattr(module, name)
    return getattr(tool, 'fn', tool)


def _server(server_id, project_id, status='ACTIVE'):
    return SimpleNamespace(
        id=server_id, name=server_id, status=status, project_id=project_id,
        flavor={}, image={'id': 'image-1'}, addresses={}, security_groups=[],
    )


def _project(project_id, name):
    return SimpleNamespace(id=project_id, name=name, domain_id='default',
                           is_enabled=True, description='')


@pytest.fixture
def conn(monkeypatch):
    value = SimpleNamespace(
        current_project_id=CURRENT, compute=Mock(), volume=Mock(),
        identity=Mock(), image=Mock(), block_storage=Mock(),
    )
    value.image.get_image.return_value = SimpleNamespace(name='cirros')
    value.identity.projects.return_value = [
        _project(CURRENT, 'alpha'), _project(OTHER, 'beta')]
    monkeypatch.setattr(connection, 'get_openstack_connection', lambda: value)
    monkeypatch.setattr(connection, 'get_current_project_id', lambda: CURRENT)
    return value


@pytest.fixture
def enabled(monkeypatch):
    monkeypatch.setenv('ALLOW_CROSS_PROJECT_READ', 'true')


@pytest.fixture
def disabled(monkeypatch):
    monkeypatch.delenv('ALLOW_CROSS_PROJECT_READ', raising=False)


def _forbidden():
    return sdk_exceptions.ForbiddenException('Policy does not allow this')


# --- switch off: no OpenStack call, clear error -----------------------------

def test_disabled_switch_blocks_every_read_before_connecting(monkeypatch, disabled):
    connect = Mock()
    monkeypatch.setattr(connection, 'get_openstack_connection', connect)

    result = compute.get_instance_details(all_projects=True)
    assert result['success'] is False
    assert result['error_type'] == 'cross_project'
    assert result['error'] == connection.CROSS_PROJECT_READ_DISABLED
    for service in (storage.get_volume_list, storage.get_volume_snapshots):
        with pytest.raises(connection.CrossProjectReadError,
                           match='ALLOW_CROSS_PROJECT_READ=true'):
            service(all_projects=True)
    for service in (compute.search_instances, compute.get_instances_by_status):
        with pytest.raises(connection.CrossProjectReadError):
            service('ACTIVE', all_projects=True)
    projects = identity.get_project_details(all_projects=True)
    assert projects == {'success': False,
                        'message': connection.CROSS_PROJECT_READ_DISABLED}
    connect.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize('name, kwargs', [
    ('search_instances', {'search_term': 'web'}),
    ('get_instances_by_status', {'status': 'ACTIVE'}),
    ('get_volume_list', {}),
    ('get_volume_snapshots', {}),
])
async def test_tools_report_disabled_switch_as_tool_error(disabled, name, kwargs):
    with pytest.raises(ToolError, match='ALLOW_CROSS_PROJECT_READ=true'):
        await _tool(name)(all_projects=True, **kwargs)


@pytest.mark.asyncio
async def test_instance_details_tool_reports_disabled_switch(disabled):
    reply = await _tool('get_instance_details')(all_projects=True)
    assert reply.startswith('Error: Failed to fetch instance details')
    assert 'ALLOW_CROSS_PROJECT_READ=true' in reply


# --- default stays current-project only --------------------------------------

def test_default_instance_list_stays_project_scoped(conn, enabled):
    conn.compute.servers.return_value = [_server('a', CURRENT), _server('b', OTHER)]

    result = compute.get_instance_details()

    conn.compute.servers.assert_called_once_with(details=True, all_projects=False)
    assert [row['id'] for row in result['instances']] == ['a']
    assert 'scope' not in result
    assert 'project_name' not in result['instances'][0]


def test_lookup_by_name_ignores_cross_project_switch(conn, enabled):
    conn.compute.servers.return_value = [_server('web', OTHER)]

    assert compute.get_instance_by_name('web') is None
    conn.compute.servers.assert_called_once_with(details=True, all_projects=False)


# --- compute -----------------------------------------------------------------

def test_all_projects_instance_list_keeps_other_projects(conn, enabled):
    conn.compute.servers.return_value = [_server('a', CURRENT), _server('b', OTHER)]

    result = compute.get_instance_details(all_projects=True)

    conn.compute.servers.assert_called_once_with(details=True, all_projects=True)
    rows = {row['id']: row for row in result['instances']}
    assert rows['b']['project_id'] == OTHER
    assert rows['b']['project_name'] == 'beta'
    assert result['scope'] == {'all_projects': True, 'projects_in_result': 2}


def test_current_project_only_result_carries_warning(conn, enabled):
    conn.compute.servers.return_value = [_server('a', CURRENT)]

    result = compute.get_instance_details(all_projects=True)

    assert result['scope']['projects_in_result'] == 1
    assert result['scope']['warning'] == connection.CROSS_PROJECT_NARROWED_WARNING


def test_policy_denial_is_a_failure_not_current_project_results(conn, enabled):
    conn.compute.servers.side_effect = _forbidden()

    result = compute.get_instance_details(all_projects=True)

    assert result['success'] is False
    assert result['error'] == connection.CROSS_PROJECT_READ_DENIED
    assert result['instances'] == []
    with pytest.raises(connection.CrossProjectReadError, match='policy denied'):
        compute.get_instances_by_status('ACTIVE', all_projects=True)


def test_missing_project_names_fall_back_to_ids(conn, enabled):
    conn.compute.servers.return_value = [_server('b', OTHER)]
    conn.identity.projects.side_effect = _forbidden()

    result = compute.get_instance_details(all_projects=True)

    assert result['instances'][0]['project_id'] == OTHER
    assert result['instances'][0]['project_name'] is None


def test_other_project_boot_volume_image_is_resolved(conn, enabled):
    server = _server('b', OTHER)
    server.image = {}
    server.attached_volumes = [{'id': 'vol-b'}]
    conn.compute.servers.return_value = [server]
    conn.block_storage.get_volume.return_value = SimpleNamespace(
        project_id=OTHER, is_bootable=True,
        volume_image_metadata={'image_id': 'image-1', 'image_name': 'cirros'})

    result = compute.get_instance_details(all_projects=True)

    assert result['instances'][0]['image'] == {'id': 'image-1', 'name': 'cirros'}


@pytest.mark.asyncio
async def test_search_and_status_tools_pass_scope(conn, enabled):
    conn.compute.servers.return_value = [_server('web-a', CURRENT),
                                         _server('web-b', OTHER)]

    found = json.loads(await _tool('search_instances')(
        search_term='web', all_projects=True))
    by_status = json.loads(await _tool('get_instances_by_status')(
        status='ACTIVE', all_projects=True))

    assert {row['id'] for row in found['matching_instances']} == {'web-a', 'web-b'}
    assert found['scope']['projects_in_result'] == 2
    assert {row['id'] for row in by_status['instances']} == {'web-a', 'web-b'}
    assert by_status['scope'] == {'all_projects': True, 'projects_in_result': 2}
    for call in conn.compute.servers.call_args_list:
        assert call.kwargs['all_projects'] is True


# --- storage -----------------------------------------------------------------

def _volume(volume_id, project_id):
    return SimpleNamespace(id=volume_id, name=volume_id, project_id=project_id,
                           attachments=[])


def test_all_projects_volume_list_keeps_owner_project(conn, enabled):
    conn.volume.volumes.return_value = [_volume('v-a', CURRENT),
                                        _volume('v-b', OTHER),
                                        _volume('v-x', None)]

    volumes = storage.get_volume_list(all_projects=True)

    conn.volume.volumes.assert_called_once_with(all_projects=True)
    rows = {row['id']: row for row in volumes}
    assert rows['v-b']['project_id'] == OTHER
    assert rows['v-b']['project_name'] == 'beta'
    # An unknown owner is never attributed to the current project.
    assert rows['v-x']['project_id'] is None


def test_all_projects_snapshot_list_keeps_other_projects(conn, enabled):
    conn.volume.snapshots.return_value = [
        SimpleNamespace(id='s-a', project_id=CURRENT),
        SimpleNamespace(id='s-b', project_id=OTHER),
    ]

    snapshots = storage.get_volume_snapshots(all_projects=True)

    conn.volume.snapshots.assert_called_once_with(all_projects=True)
    assert {row['id']: row['project_name'] for row in snapshots} == {
        's-a': 'alpha', 's-b': 'beta'}


@pytest.mark.parametrize('service, attr', [
    (storage.get_volume_list, 'volumes'),
    (storage.get_volume_snapshots, 'snapshots'),
])
def test_storage_policy_denial_raises_clear_error(conn, enabled, service, attr):
    getattr(conn.volume, attr).side_effect = _forbidden()

    with pytest.raises(connection.CrossProjectReadError, match='policy denied'):
        service(all_projects=True)


@pytest.mark.asyncio
async def test_volume_tool_reports_narrowed_scope(conn, enabled):
    conn.volume.volumes.return_value = [_volume('v-a', CURRENT)]

    reply = json.loads(await _tool('get_volume_list')(all_projects=True))

    assert reply['count'] == 1
    assert reply['scope']['warning'] == connection.CROSS_PROJECT_NARROWED_WARNING


# --- identity ----------------------------------------------------------------

def test_project_summaries_list_every_visible_project(conn, enabled):
    result = identity.get_project_details(all_projects=True)

    assert result['success'] is True
    assert [(row['name'], row['is_current']) for row in result['projects']] == [
        ('alpha', True), ('beta', False)]
    assert set(result['projects'][0]) == {
        'id', 'name', 'domain_id', 'enabled', 'description', 'is_current'}
    assert result['scope'] == {'all_projects': True, 'projects_in_result': 2}


def test_ambiguous_project_name_returns_summaries(conn, enabled):
    conn.identity.projects.return_value = [
        _project(CURRENT, 'alpha'), _project(OTHER, 'beta'),
        _project('project-c', 'beta')]

    result = identity.get_project_details('beta', all_projects=True)

    assert [row['id'] for row in result['projects']] == [OTHER, 'project-c']
    assert 'resources' not in result['projects'][0]
    conn.identity.get_project.assert_not_called()


@pytest.mark.parametrize('name', ['beta', OTHER])
def test_other_project_details_by_name_or_id(conn, enabled, name):
    _details_conn(conn)
    conn.identity.get_project.return_value = _project(OTHER, 'beta')
    conn.compute.servers.return_value = [_server('a', CURRENT), _server('b', OTHER)]
    conn.volume.volumes.return_value = [_volume('v-a', CURRENT),
                                        _volume('v-b', OTHER)]
    conn.volume.snapshots.return_value = [SimpleNamespace(id='s-b', project_id=OTHER)]

    result = identity.get_project_details(name, all_projects=True)

    conn.identity.get_project.assert_called_once_with(OTHER)
    conn.compute.servers.assert_called_once_with(all_projects=True)
    conn.volume.volumes.assert_called_once_with(all_projects=True)
    conn.volume.snapshots.assert_called_once_with(all_projects=True)
    detail = result['projects'][0]
    assert (detail['id'], detail['is_current']) == (OTHER, False)
    assert detail['resources']['compute']['instances'] == 1
    assert detail['resources']['volume']['volumes'] == 1
    assert detail['resources']['volume']['snapshots'] == 1
    assert 'warning' not in detail['resources']['volume']
    assert 'note' in detail['resources']['network']
    assert result['scope'] == {'all_projects': True, 'projects_in_result': 1}


def test_other_project_details_report_compute_denial(conn, enabled):
    _details_conn(conn)
    conn.identity.get_project.return_value = _project(OTHER, 'beta')
    conn.compute.servers.side_effect = _forbidden()

    result = identity.get_project_details('beta', all_projects=True)

    assert result == {'success': False,
                      'message': connection.CROSS_PROJECT_READ_DENIED}


def test_other_project_details_warn_when_volumes_narrowed(conn, enabled):
    _details_conn(conn)
    conn.identity.get_project.return_value = _project(OTHER, 'beta')
    conn.compute.servers.return_value = []
    conn.volume.volumes.return_value = [_volume('v-a', CURRENT)]
    conn.volume.snapshots.return_value = []

    result = identity.get_project_details('beta', all_projects=True)

    volume = result['projects'][0]['resources']['volume']
    assert volume['volumes'] == 0
    assert volume['warning'] == connection.CROSS_PROJECT_NARROWED_WARNING


def test_project_summaries_report_policy_denial(conn, enabled):
    conn.identity.projects.side_effect = _forbidden()

    result = identity.get_project_details(all_projects=True)

    assert result == {'success': False,
                      'message': connection.CROSS_PROJECT_READ_DENIED}


def test_other_project_details_stay_unavailable_without_all_projects(conn, enabled):
    conn.identity.get_project.return_value = _project(CURRENT, 'alpha')

    result = identity.get_project_details('beta')

    assert result['success'] is False
    assert 'not accessible' in result['message']


def _details_conn(conn):
    conn.network = Mock()
    for attr in ('ips', 'networks', 'ports', 'routers'):
        getattr(conn.network, attr).return_value = []
    conn.identity.role_assignments.return_value = []
    return conn


def test_current_project_details_list_without_all_projects(conn, enabled):
    _details_conn(conn)
    conn.identity.get_project.return_value = _project(CURRENT, 'alpha')
    conn.compute.servers.return_value = [_server('a', CURRENT)]
    conn.volume.volumes.return_value = [_volume('v-a', CURRENT)]
    conn.volume.snapshots.return_value = []

    result = identity.get_project_details('alpha')

    conn.compute.servers.assert_called_once_with()
    conn.volume.volumes.assert_called_once_with()
    conn.volume.snapshots.assert_called_once_with()
    resources = result['projects'][0]['resources']
    assert resources['compute']['instances'] == 1
    assert resources['volume']['volumes'] == 1
    assert result['scope'] == 'single-project'
