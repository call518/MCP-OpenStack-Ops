"""Cross-project reads for images, Heat stacks and load balancers (issue #86)."""

import importlib
import json
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

import mcp_openstack_ops.mcp_main  # noqa: F401  Register tools before importing them.
from mcp_openstack_ops import connection
from mcp_openstack_ops.services import image, orchestration
from mcp_openstack_ops.services.load_balancer import core as lb_core

CURRENT = 'project-a'
OTHER = 'project-b'


def _tool(name):
    tool = getattr(importlib.import_module(f'mcp_openstack_ops.tools.{name}'), name)
    return getattr(tool, 'fn', tool)


def _image(image_id, owner, visibility='private'):
    return SimpleNamespace(id=image_id, name=image_id, status='active',
                           visibility=visibility, owner=owner)


def _stack(stack_id, project_id):
    return SimpleNamespace(
        id=stack_id, name=stack_id, status='CREATE_COMPLETE', project_id=project_id,
        links=[{'rel': 'self',
                'href': f'http://heat:8004/v1/{project_id}/stacks/{stack_id}/{stack_id}'}])


def _lb(lb_id, project_id):
    return SimpleNamespace(
        id=lb_id, name=lb_id, description='', vip_address='10.0.0.1',
        vip_port_id='p', vip_subnet_id='s', vip_network_id='n',
        provisioning_status='ACTIVE', operating_status='ONLINE',
        is_admin_state_up=True, project_id=project_id, provider='amphora',
        created_at='t', updated_at='t')


@pytest.fixture
def conn(monkeypatch):
    value = SimpleNamespace(current_project_id=CURRENT, image=Mock(),
                            orchestration=Mock(), load_balancer=Mock(),
                            identity=Mock())
    value.identity.projects.return_value = [
        SimpleNamespace(id=CURRENT, name='alpha'),
        SimpleNamespace(id=OTHER, name='beta')]
    value.load_balancer.listeners.return_value = []
    monkeypatch.setattr(connection, 'get_openstack_connection', lambda: value)
    monkeypatch.setattr(connection, 'get_current_project_id', lambda: CURRENT)
    monkeypatch.setattr(lb_core, 'get_openstack_connection', lambda: value)
    return value


@pytest.fixture
def enabled(monkeypatch):
    monkeypatch.setenv('ALLOW_CROSS_PROJECT_READ', 'true')


# --- default stays as before --------------------------------------------------

def test_default_image_list_is_unchanged(conn, enabled):
    conn.image.images.return_value = [
        _image('own', CURRENT), _image('other-private', OTHER),
        _image('public', OTHER, 'public')]

    rows = image.get_image_detail_list()

    conn.image.images.assert_called_once_with()
    assert [row['id'] for row in rows] == ['own', 'public']
    assert 'project_name' not in rows[0]


def test_default_stack_list_is_unchanged(conn, enabled):
    conn.orchestration.stacks.return_value = [_stack('s-a', CURRENT),
                                              _stack('s-b', OTHER)]

    rows = orchestration.get_heat_stacks()

    conn.orchestration.stacks.assert_called_once_with()
    assert [row['id'] for row in rows] == ['s-a']
    assert rows[0]['project_id'] == CURRENT


def test_default_load_balancer_list_is_unchanged(conn, enabled):
    conn.load_balancer.load_balancers.return_value = [_lb('lb-a', CURRENT),
                                                      _lb('lb-b', OTHER)]

    result = lb_core.get_load_balancer_list()

    conn.load_balancer.load_balancers.assert_called_once_with()
    assert [row['id'] for row in result['load_balancers']] == ['lb-a']
    assert 'scope' not in result


# --- all_projects ------------------------------------------------------------

from fastmcp.exceptions import ToolError  # noqa: E402,F401
from openstack import exceptions as sdk_exceptions  # noqa: E402


def test_disabled_switch_blocks_reads_before_connecting(monkeypatch):
    monkeypatch.delenv('ALLOW_CROSS_PROJECT_READ', raising=False)
    connect = Mock()
    monkeypatch.setattr(connection, 'get_openstack_connection', connect)
    monkeypatch.setattr(lb_core, 'get_openstack_connection', connect)

    for service in (image.get_image_detail_list, orchestration.get_heat_stacks):
        with pytest.raises(connection.CrossProjectReadError,
                           match='ALLOW_CROSS_PROJECT_READ=true'):
            service(all_projects=True)
    result = lb_core.get_load_balancer_list(all_projects=True)
    assert result['success'] is False
    assert result['message'] == connection.CROSS_PROJECT_READ_DISABLED
    connect.assert_not_called()


@pytest.mark.asyncio
async def test_image_list_keeps_other_private_images(conn, enabled):
    conn.image.images.return_value = [
        _image('own', CURRENT), _image('other-private', OTHER),
        _image('public', OTHER, 'public')]

    reply = json.loads(await _tool('get_image_detail_list')(all_projects=True))

    rows = {row['id']: row for row in reply['images']}
    assert set(rows) == {'own', 'other-private', 'public'}
    assert rows['other-private']['project_name'] == 'beta'
    assert reply['scope'] == {'all_projects': True, 'projects_in_result': 2}


@pytest.mark.asyncio
async def test_public_images_do_not_prove_cross_project_read(conn, enabled):
    conn.image.images.return_value = [_image('own', CURRENT),
                                      _image('public', OTHER, 'public')]

    reply = json.loads(await _tool('get_image_detail_list')(all_projects=True))

    assert reply['scope']['warning'] == connection.SHARED_NARROWED_WARNING


@pytest.mark.asyncio
async def test_global_stack_list_uses_global_tenant(conn, enabled):
    conn.orchestration.get.return_value.json.return_value = {'stacks': [
        {'id': 's-b', 'stack_name': 'web', 'stack_status': 'CREATE_COMPLETE',
         'project': OTHER},
        {'id': 's-a', 'stack_name': 'db', 'stack_status': 'CREATE_COMPLETE',
         'links': [{'rel': 'self',
                    'href': f'http://heat:8004/v1/{CURRENT}/stacks/db/s-a'}]},
    ]}

    reply = json.loads(await _tool('get_heat_stacks')(all_projects=True))

    conn.orchestration.get.assert_called_once_with('/stacks?global_tenant=True', raise_exc=True)
    rows = {row['id']: row for row in reply['stacks']}
    assert rows['s-b']['project_name'] == 'beta'
    assert rows['s-a']['project_id'] == CURRENT
    assert reply['scope'] == {'all_projects': True, 'projects_in_result': 2}


@pytest.mark.asyncio
async def test_heat_global_index_denial_is_reported(conn, enabled):
    # Raw proxy requests raise keystoneauth's Forbidden, as Heat does by default.
    from keystoneauth1 import exceptions as ksa_exceptions
    conn.orchestration.get.side_effect = ksa_exceptions.Forbidden('no')

    reply = await _tool('get_heat_stacks')(all_projects=True)

    assert reply.startswith('Error: Failed to fetch Heat stacks')
    assert connection.CROSS_PROJECT_READ_DENIED in reply


@pytest.mark.asyncio
async def test_load_balancer_list_keeps_other_projects(conn, enabled):
    conn.load_balancer.load_balancers.return_value = [_lb('lb-a', CURRENT),
                                                      _lb('lb-b', OTHER)]

    reply = json.loads(await _tool('get_load_balancer_list')(
        all_projects=True, limit=1))

    result = reply['result']
    assert [row['id'] for row in result['load_balancers']] == ['lb-a']
    assert result['load_balancers'][0]['project_name'] == 'alpha'
    assert result['summary']['total_available'] == 2
    assert result['scope'] == {'all_projects': True, 'projects_in_result': 2}


def test_narrowed_load_balancer_list_carries_warning(conn, enabled):
    conn.load_balancer.load_balancers.return_value = [_lb('lb-a', CURRENT)]

    result = lb_core.get_load_balancer_list(all_projects=True)

    assert result['scope']['warning'] == connection.CROSS_PROJECT_NARROWED_WARNING


@pytest.mark.asyncio
async def test_load_balancer_tool_has_no_scope_by_default(conn, enabled):
    conn.load_balancer.load_balancers.return_value = [_lb('lb-a', CURRENT)]

    reply = json.loads(await _tool('get_load_balancer_list')())

    assert 'scope' not in reply['result']
