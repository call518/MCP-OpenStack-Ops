"""Cross-project reads for Neutron list tools (issue #86, phase 2)."""

from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from mcp_openstack_ops import connection
from mcp_openstack_ops.services import network

CURRENT = 'project-a'
OTHER = 'project-b'


def _net(net_id, project_id, shared=False, external=False):
    return SimpleNamespace(id=net_id, name=net_id, project_id=project_id,
                           tenant_id=project_id, is_shared=shared,
                           is_router_external=external)


def _owned(item_id, project_id):
    return SimpleNamespace(id=item_id, name=item_id, project_id=project_id,
                           tenant_id=project_id, security_group_rules=[])


@pytest.fixture
def conn(monkeypatch):
    value = SimpleNamespace(current_project_id=CURRENT, network=Mock(),
                            identity=Mock())
    value.network.subnets.return_value = []
    value.network.ports.return_value = []
    value.identity.projects.return_value = [
        SimpleNamespace(id=CURRENT, name='alpha'),
        SimpleNamespace(id=OTHER, name='beta')]
    monkeypatch.setattr(connection, 'get_openstack_connection', lambda: value)
    monkeypatch.setattr(connection, 'get_current_project_id', lambda: CURRENT)
    return value


@pytest.fixture
def enabled(monkeypatch):
    monkeypatch.setenv('ALLOW_CROSS_PROJECT_READ', 'true')


# --- default stays current-project only --------------------------------------

def test_default_network_list_keeps_own_shared_and_external(conn, enabled):
    conn.network.networks.return_value = [
        _net('own', CURRENT), _net('private-b', OTHER),
        _net('shared-b', OTHER, shared=True), _net('ext', OTHER, external=True)]

    rows = network.get_network_details()

    conn.network.networks.assert_called_once_with()
    assert [row['id'] for row in rows] == ['own', 'shared-b', 'ext']
    assert 'project_name' not in rows[0]


@pytest.mark.parametrize('service, attr', [
    (network.get_routers, 'routers'),
    (network.get_security_groups, 'security_groups'),
    (network.get_floating_ips, 'ips'),
])
def test_default_owned_lists_stay_current_project(conn, enabled, service, attr):
    getattr(conn.network, attr).return_value = [_owned('a', CURRENT),
                                                _owned('b', OTHER)]

    rows = service()

    getattr(conn.network, attr).assert_called_once_with()
    assert [row['id'] for row in rows] == ['a']
    assert 'project_name' not in rows[0]


# --- all_projects ------------------------------------------------------------

import importlib  # noqa: E402
import json  # noqa: E402

from fastmcp.exceptions import ToolError  # noqa: E402

import mcp_openstack_ops.mcp_main  # noqa: E402,F401  Register tools.


def _tool(name):
    tool = getattr(importlib.import_module(f'mcp_openstack_ops.tools.{name}'), name)
    return getattr(tool, 'fn', tool)


def test_disabled_switch_blocks_neutron_reads_before_connecting(monkeypatch):
    monkeypatch.delenv('ALLOW_CROSS_PROJECT_READ', raising=False)
    connect = Mock()
    monkeypatch.setattr(connection, 'get_openstack_connection', connect)

    for service in (network.get_network_details, network.get_routers,
                    network.get_security_groups, network.get_floating_ips):
        with pytest.raises(connection.CrossProjectReadError,
                           match='ALLOW_CROSS_PROJECT_READ=true'):
            service(all_projects=True)
    connect.assert_not_called()


def test_all_projects_network_list_keeps_other_projects(conn, enabled):
    conn.network.networks.return_value = [
        _net('own', CURRENT), _net('private-b', OTHER),
        _net('ext', OTHER, external=True)]
    conn.network.subnets.return_value = [
        SimpleNamespace(id='sub-b', name='sub-b', network_id='private-b',
                        project_id=OTHER, tenant_id=OTHER)]

    rows = {row['id']: row for row in network.get_network_details(all_projects=True)}

    assert set(rows) == {'own', 'private-b', 'ext'}
    assert rows['private-b']['project_name'] == 'beta'
    assert [s['id'] for s in rows['private-b']['subnets']] == ['sub-b']
    scope = connection.shared_items_scope(rows.values())
    assert scope == {'all_projects': True, 'projects_in_result': 2}


def test_only_shared_other_project_networks_carry_warning(conn, enabled):
    conn.network.networks.return_value = [
        _net('own', CURRENT), _net('ext', OTHER, external=True),
        _net('shared-b', OTHER, shared=True)]

    rows = network.get_network_details(all_projects=True)
    scope = connection.shared_items_scope(rows)

    assert scope['projects_in_result'] == 2
    assert scope['warning'] == connection.SHARED_NARROWED_WARNING


@pytest.mark.parametrize('service, attr', [
    (network.get_routers, 'routers'),
    (network.get_security_groups, 'security_groups'),
    (network.get_floating_ips, 'ips'),
])
def test_all_projects_owned_lists_keep_other_projects(conn, enabled, service, attr):
    unowned = _owned('x', None)
    getattr(conn.network, attr).return_value = [_owned('a', CURRENT),
                                                _owned('b', OTHER), unowned]

    rows = {row['id']: row for row in service(all_projects=True)}

    getattr(conn.network, attr).assert_called_once_with()
    assert rows['b']['project_name'] == 'beta'
    assert rows['x']['project_id'] is None
    assert 'warning' not in connection.shared_items_scope(rows.values())


def test_current_project_only_owned_list_carries_warning(conn, enabled):
    conn.network.routers.return_value = [_owned('a', CURRENT)]

    scope = connection.shared_items_scope(network.get_routers(all_projects=True))

    assert scope['warning'] == connection.SHARED_NARROWED_WARNING


def test_shared_security_group_does_not_prove_cross_project_read(conn, enabled):
    shared = _owned('sg-b', OTHER)
    shared.is_shared = True
    conn.network.security_groups.return_value = [_owned('sg-a', CURRENT), shared]

    rows = network.get_security_groups(all_projects=True)

    assert rows[1]['shared'] is True
    assert connection.shared_items_scope(rows)['warning'] == (
        connection.SHARED_NARROWED_WARNING)


@pytest.mark.asyncio
async def test_network_tool_rejects_name_with_all_projects(conn, enabled):
    with pytest.raises(ToolError, match='omit network_name'):
        await _tool('get_network_details')(network_name='own', all_projects=True)
    conn.network.networks.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize('name', ['get_network_details', 'get_routers'])
async def test_neutron_tools_report_disabled_switch(monkeypatch, name):
    monkeypatch.delenv('ALLOW_CROSS_PROJECT_READ', raising=False)
    with pytest.raises(ToolError, match='ALLOW_CROSS_PROJECT_READ=true'):
        await _tool(name)(all_projects=True)


@pytest.mark.asyncio
@pytest.mark.parametrize('name, attr, key', [
    ('get_routers', 'routers', 'routers'),
    ('get_security_groups', 'security_groups', 'security_groups'),
    ('get_floating_ips', 'ips', 'floating_ips'),
])
async def test_neutron_tools_add_scope_only_with_all_projects(conn, enabled, name, attr, key):
    getattr(conn.network, attr).return_value = [_owned('a', CURRENT),
                                                _owned('b', OTHER)]

    default = json.loads(await _tool(name)())
    crossed = json.loads(await _tool(name)(all_projects=True))

    assert 'scope' not in default
    assert [row['id'] for row in default[key]] == ['a']
    assert crossed['scope'] == {'all_projects': True, 'projects_in_result': 2}
