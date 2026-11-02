"""Regressions discovered during the expanded issue #73 live validation."""

import importlib
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from mcp_openstack_ops import connection
from mcp_openstack_ops.services import compute, storage


@pytest.fixture
def volume_connection(monkeypatch):
    server = SimpleNamespace(id='server-id', name='vm', project_id='project')
    volume = SimpleNamespace(
        id='volume-id', name='data', project_id='project', status='available',
        attachments=[{'server_id': server.id}],
    )
    conn = Mock()
    conn.compute.servers.return_value = [server]
    conn.volume.volumes.return_value = [volume]
    monkeypatch.setattr(connection, 'get_openstack_connection', lambda: conn)
    monkeypatch.setattr(connection, 'get_current_project_id', lambda: 'project')
    return conn, server, volume


@pytest.mark.parametrize('identifier', ['instance_name', 'instance_id', 'server_id'])
def test_volume_attach_resolves_owned_server_and_sdk_arguments(
    volume_connection, identifier
):
    conn, server, volume = volume_connection
    value = server.name if identifier == 'instance_name' else server.id
    result = storage.set_volume(volume.name, 'attach', **{identifier: value})
    assert result['success']
    conn.compute.create_volume_attachment.assert_called_once_with(
        server.id, volume.id)


@pytest.mark.parametrize('foreign', ['server', 'volume'])
def test_volume_attach_rejects_foreign_resources(volume_connection, foreign):
    conn, server, volume = volume_connection
    (server if foreign == 'server' else volume).project_id = 'other'
    assert not storage.set_volume('data', 'attach', instance_name='vm')['success']
    conn.compute.create_volume_attachment.assert_not_called()


def test_volume_detach_uses_server_then_volume(volume_connection):
    conn, server, volume = volume_connection
    assert storage.set_volume('data', 'detach')['success']
    conn.compute.delete_volume_attachment.assert_called_once_with(
        server.id, volume.id)


def test_volume_detach_rejects_foreign_server(volume_connection):
    conn, server, volume = volume_connection
    server.project_id = 'other'
    assert not storage.set_volume('data', 'detach')['success']
    conn.compute.delete_volume_attachment.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize('mtu', [None, 1400])
async def test_network_tool_uses_backend_mtu_unless_explicit(monkeypatch, mtu):
    module = importlib.import_module('mcp_openstack_ops.tools.set_networks')
    service = Mock(return_value={'success': True})
    monkeypatch.setattr(module, '_set_networks', service)
    monkeypatch.setattr(module, '_get_resource_status_by_name',
                        Mock(return_value='ACTIVE'))
    monkeypatch.setattr('time.sleep', lambda _: None)
    target = getattr(module.set_networks, 'fn', module.set_networks)
    await target(action='create', network_names='test',
                 **({} if mtu is None else {'mtu': mtu}))
    assert service.call_args.kwargs.get('mtu') == (0 if mtu is None else mtu)


@pytest.mark.parametrize('sensitive,term,offset,expected', [
    (False, 'WEB', 0, ['0', '1']),
    (False, 'web', 2, ['2']),
    (True, 'Web', 0, ['0']),
    (True, 'WEB', 0, []),
    (False, 'web', 10, []),
])
def test_search_case_and_offset(monkeypatch, sensitive, term, offset, expected):
    rows = [{'id': str(i), 'name': name, 'status': 'ACTIVE'}
            for i, name in enumerate(['Web-a', 'web-b', 'web-c'])]
    query = Mock(side_effect=lambda **kw: {'instances': [r for r in rows if
        not kw.get('instance_names') or r['id'] in kw['instance_names']]})
    monkeypatch.setattr(connection, 'get_openstack_connection', Mock())
    monkeypatch.setattr(compute, 'get_instance_details', query)
    result = compute.search_instances(term, ['name'], limit=2,
                                      offset=offset, case_sensitive=sensitive)
    assert [r['id'] for r in result] == expected


@pytest.mark.asyncio
@pytest.mark.parametrize('tool', ['search_instances', 'get_instance'])
async def test_search_tools_forward_case_and_offset(monkeypatch, tool):
    module = importlib.import_module('mcp_openstack_ops.tools.' + tool)
    service = Mock(return_value=[])
    monkeypatch.setattr(module, '_search_instances', service)
    target = getattr(getattr(module, tool), 'fn', getattr(module, tool))
    await target(search_term='Web', offset=3, case_sensitive=True)
    assert service.call_args.kwargs['offset'] == 3
    assert service.call_args.kwargs['case_sensitive'] is True
    assert service.call_args.kwargs['with_pagination'] is True


@pytest.mark.parametrize('offset,expected,has_more', [
    (0, ['0', '1'], True), (2, ['2'], False), (10, [], False),
])
def test_search_pagination_metadata(monkeypatch, offset, expected, has_more):
    rows = [{'id': str(i), 'name': 'web', 'status': 'ACTIVE'} for i in range(3)]
    monkeypatch.setattr(connection, 'get_openstack_connection', Mock())
    monkeypatch.setattr(compute, 'get_instance_details', Mock(side_effect=lambda **kw: {
        'instances': [r for r in rows if not kw.get('instance_names')
                      or r['id'] in kw['instance_names']],
    }))
    result = compute.search_instances('web', ['name'], limit=2, offset=offset,
                                      with_pagination=True)
    assert [r['id'] for r in result['instances']] == expected
    assert result['pagination'] == {'limit': 2, 'offset': offset,
                                    'has_more': has_more}


@pytest.mark.asyncio
@pytest.mark.parametrize('tool', ['search_instances', 'get_instance'])
async def test_search_tools_preserve_query_and_page_metadata(monkeypatch, tool):
    import json
    module = importlib.import_module('mcp_openstack_ops.tools.' + tool)
    page = {'limit': 2, 'offset': 0, 'has_more': True}
    service = Mock(return_value={'instances': [{'id': 'owned'}],
                                 'pagination': page, 'search_info': {}})
    monkeypatch.setattr(module, '_search_instances', service)
    target = getattr(getattr(module, tool), 'fn', getattr(module, tool))
    result = json.loads(await target(search_term='Web', limit=2,
                                     case_sensitive=True))
    assert result['pagination'] == page
    info = result['search_info'] if tool == 'search_instances' else result
    assert info['search_term'] == 'Web'
    assert info['case_sensitive'] is True
    if tool == 'get_instance':
        assert result['query_type'] == 'search'
        assert result['total_instances'] == 1
