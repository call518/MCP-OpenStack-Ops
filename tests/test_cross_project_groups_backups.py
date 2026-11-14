"""Cross-project reads for backups, volume groups and server groups (issue #86)."""

import importlib
import json
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

import mcp_openstack_ops.mcp_main  # noqa: F401  Register tools before importing them.
from mcp_openstack_ops import connection
from mcp_openstack_ops.services import compute, storage

CURRENT = 'project-a'
OTHER = 'project-b'


def _tool(name):
    tool = getattr(importlib.import_module(f'mcp_openstack_ops.tools.{name}'), name)
    return getattr(tool, 'fn', tool)


def _resource(item_id, project_id):
    data = {'id': item_id, 'name': item_id, 'project_id': project_id}
    return SimpleNamespace(**data, to_dict=lambda: dict(data))


def _server_group(group_id, project_id):
    return SimpleNamespace(id=group_id, name=group_id, policies=['affinity'],
                           policy=None, member_ids=[], metadata={},
                           project_id=project_id, user_id='u')


@pytest.fixture
def conn(monkeypatch):
    value = SimpleNamespace(current_project_id=CURRENT, compute=Mock(),
                            block_storage=Mock(), identity=Mock())
    value.identity.projects.return_value = [
        SimpleNamespace(id=CURRENT, name='alpha'),
        SimpleNamespace(id=OTHER, name='beta')]
    monkeypatch.setattr(connection, 'get_openstack_connection', lambda: value)
    monkeypatch.setattr(connection, 'get_current_project_id', lambda: CURRENT)
    return value


@pytest.fixture
def enabled(monkeypatch):
    monkeypatch.setenv('ALLOW_CROSS_PROJECT_READ', 'true')


# --- default stays as before --------------------------------------------------

@pytest.mark.asyncio
@pytest.mark.parametrize('name, attr, key', [
    ('get_volume_backups', 'backups', 'backups'),
    ('get_volume_groups', 'groups', 'groups'),
])
async def test_default_cinder_lists_are_unchanged(conn, enabled, name, attr, key):
    getattr(conn.block_storage, attr).return_value = [_resource('a', CURRENT)]

    reply = json.loads(await _tool(name)())

    getattr(conn.block_storage, attr).assert_called_once_with()
    assert reply == {'success': True, key: [
        {'id': 'a', 'name': 'a', 'project_id': CURRENT}], 'count': 1}


def test_default_server_groups_are_unchanged(conn, enabled):
    conn.compute.server_groups.return_value = [_server_group('g', CURRENT)]

    rows = compute.get_server_groups()

    conn.compute.server_groups.assert_called_once_with()
    assert [row['id'] for row in rows] == ['g']
    assert 'project_name' not in rows[0]


# --- all_projects ------------------------------------------------------------

from fastmcp.exceptions import ToolError  # noqa: E402
from openstack import exceptions as sdk_exceptions  # noqa: E402


@pytest.mark.asyncio
@pytest.mark.parametrize('name', ['get_volume_backups', 'get_volume_groups'])
async def test_disabled_switch_blocks_cinder_lists_before_connecting(monkeypatch, name):
    monkeypatch.delenv('ALLOW_CROSS_PROJECT_READ', raising=False)
    connect = Mock()
    monkeypatch.setattr(connection, 'get_openstack_connection', connect)

    with pytest.raises(ToolError, match='ALLOW_CROSS_PROJECT_READ=true'):
        await _tool(name)(all_projects=True)
    connect.assert_not_called()


def test_disabled_switch_blocks_server_groups_before_connecting(monkeypatch):
    monkeypatch.delenv('ALLOW_CROSS_PROJECT_READ', raising=False)
    connect = Mock()
    monkeypatch.setattr(connection, 'get_openstack_connection', connect)

    with pytest.raises(connection.CrossProjectReadError):
        compute.get_server_groups(all_projects=True)
    connect.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize('name, attr, key', [
    ('get_volume_backups', 'backups', 'backups'),
    ('get_volume_groups', 'groups', 'groups'),
])
async def test_cinder_lists_keep_other_projects(conn, enabled, name, attr, key):
    getattr(conn.block_storage, attr).return_value = [
        _resource('a', CURRENT), _resource('b', OTHER), _resource('x', None)]

    reply = json.loads(await _tool(name)(all_projects=True))

    getattr(conn.block_storage, attr).assert_called_once_with(all_projects=True)
    rows = {row['id']: row for row in reply[key]}
    assert rows['b']['project_name'] == 'beta'
    assert rows['x']['project_name'] is None
    assert reply['scope'] == {'all_projects': True, 'projects_in_result': 2}


@pytest.mark.asyncio
async def test_narrowed_cinder_list_carries_warning(conn, enabled):
    conn.block_storage.backups.return_value = [_resource('a', CURRENT)]

    reply = json.loads(await _tool('get_volume_backups')(all_projects=True))

    assert reply['scope']['warning'] == connection.CROSS_PROJECT_NARROWED_WARNING


@pytest.mark.asyncio
async def test_cinder_list_policy_denial_is_a_tool_error(conn, enabled):
    conn.block_storage.groups.side_effect = sdk_exceptions.ForbiddenException('no')

    with pytest.raises(ToolError, match='policy denied'):
        await _tool('get_volume_groups')(all_projects=True)


@pytest.mark.asyncio
async def test_server_groups_keep_other_projects(conn, enabled):
    conn.compute.server_groups.return_value = [_server_group('g-a', CURRENT),
                                               _server_group('g-b', OTHER)]

    reply = json.loads(await _tool('get_server_groups')(all_projects=True))

    conn.compute.server_groups.assert_called_once_with(all_projects=True)
    rows = {row['id']: row for row in reply['result']['server_groups']}
    assert rows['g-b']['project_name'] == 'beta'
    assert reply['result']['scope'] == {'all_projects': True, 'projects_in_result': 2}


def test_server_groups_policy_denial_raises_clear_error(conn, enabled):
    conn.compute.server_groups.side_effect = sdk_exceptions.ForbiddenException('no')

    with pytest.raises(connection.CrossProjectReadError, match='policy denied'):
        compute.get_server_groups(all_projects=True)


@pytest.mark.asyncio
async def test_server_groups_tool_has_no_scope_by_default(conn, enabled):
    conn.compute.server_groups.return_value = [_server_group('g-a', CURRENT)]

    reply = json.loads(await _tool('get_server_groups')())

    assert 'scope' not in reply['result']


@pytest.mark.asyncio
async def test_hidden_owner_projects_carry_their_own_warning(conn, enabled):
    # Cinder shows backup owners only to administrators.
    conn.block_storage.backups.return_value = [_resource('a', None)]

    reply = json.loads(await _tool('get_volume_backups')(all_projects=True))

    assert reply['scope']['warning'] == storage.PROJECT_ATTRIBUTE_HIDDEN


@pytest.mark.asyncio
async def test_group_owners_come_from_newer_microversion(conn, enabled):
    conn.block_storage.groups.return_value = [_resource('g-b', None)]
    conn.block_storage.get.return_value.json.return_value = {
        'groups': [{'id': 'g-b', 'project_id': OTHER}]}

    reply = json.loads(await _tool('get_volume_groups')(all_projects=True))

    conn.block_storage.get.assert_called_once_with(
        '/groups/detail?all_tenants=1', microversion='3.58', raise_exc=True)
    assert reply['groups'][0]['project_name'] == 'beta'
    assert reply['scope'] == {'all_projects': True, 'projects_in_result': 1}
