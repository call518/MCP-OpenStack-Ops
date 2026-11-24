"""Regressions discovered during the expanded issue #73 live validation."""

import importlib
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from mcp_openstack_ops import connection
from mcp_openstack_ops.services import compute, monitoring, storage


def _tool_handler(module, name):
    tool = getattr(module, name)
    return getattr(tool, 'fn', tool)


@pytest.mark.parametrize(
    'tool,actions',
    [
        ('set_instance', {'delete', 'resize', 'snapshot', 'rebuild'}),
        ('set_flavor', {'set_extra_specs', 'get_flavors'}),
        ('set_project', {'update', 'get_project_details'}),
        ('set_keypair', {'import', 'get_keypair_list'}),
        ('set_network_ports', {'create', 'get_network_ports'}),
        ('set_subnets', {'create', 'get_subnets'}),
    ],
)
def test_tool_descriptions_expose_supported_actions(tool, actions):
    module = importlib.import_module(f'mcp_openstack_ops.tools.{tool}')
    description = (_tool_handler(module, tool).__doc__ or '').lower()
    assert all(action in description for action in actions)


@pytest.mark.asyncio
async def test_instance_tool_forwards_advanced_action_parameters(monkeypatch):
    module = importlib.import_module('mcp_openstack_ops.tools.set_instance')
    service = Mock(return_value={'success': True})
    monkeypatch.setattr(module, '_set_instance', service)
    monkeypatch.setattr(module, '_get_instance_by_name', Mock(return_value=None))
    monkeypatch.setattr('time.sleep', lambda _: None)

    await _tool_handler(module, 'set_instance')(
        instance_names='vm', action='snapshot', force=True,
        snapshot_name='backup', metadata='{"purpose": "test"}',
        preserve_ephemeral=True,
    )

    assert service.call_args.args == ('vm', 'snapshot')
    assert service.call_args.kwargs['force'] is True
    assert service.call_args.kwargs['snapshot_name'] == 'backup'
    assert service.call_args.kwargs['metadata'] == {'purpose': 'test'}
    assert service.call_args.kwargs['preserve_ephemeral'] is True


def _row(i, name=None, status='ACTIVE', flavor='m1.small', image='ubuntu-24.04'):
    return {'id': f'vm-{i}', 'name': name or f'dev-{i}', 'status': status,
            'flavor': {'name': flavor}, 'image': {'name': image}}


def _instance_tool(monkeypatch, rows):
    module = importlib.import_module('mcp_openstack_ops.tools.set_instance')
    service = Mock(return_value={'success': True})
    listing = Mock(return_value={'instances': rows, 'count': len(rows)})
    monkeypatch.setattr(module, '_set_instance', service)
    monkeypatch.setattr(module, '_get_instance_details', listing)
    monkeypatch.setattr(module, '_get_instance_by_name', Mock(return_value=None))
    monkeypatch.setattr('time.sleep', lambda _: None)
    return _tool_handler(module, 'set_instance'), service, listing


def _acted(service):
    return [call.args[0] for call in service.call_args_list]


@pytest.mark.asyncio
@pytest.mark.parametrize('env,total,acted', [
    (None, 100, 100),     # default limit: exactly 100 still runs
    (None, 101, 0),       # default limit: 101 is refused
    ('', 101, 0),         # empty value uses the default
    ('500', 450, 450),    # a raised limit needs no extra listing
    ('500', 501, 0),
    ('2', 3, 0),          # lowered limit
])
async def test_instance_filter_max_matches(monkeypatch, env, total, acted):
    if env is None:
        monkeypatch.delenv('INSTANCE_FILTER_MAX_MATCHES', raising=False)
    else:
        monkeypatch.setenv('INSTANCE_FILTER_MAX_MATCHES', env)
    handler, service, listing = _instance_tool(
        monkeypatch, [_row(i) for i in range(total)])

    result = await handler(name_contains='dev', action='stop')

    assert service.call_count == acted
    listing.assert_called_once()
    assert listing.call_args.kwargs['include_all'] is True
    if not acted:
        assert 'INSTANCE_FILTER_MAX_MATCHES' in result, result
        assert 'no action was taken' in result


@pytest.mark.asyncio
async def test_instance_filters_combine_with_and(monkeypatch):
    rows = [_row(1, 'dev-1', 'ACTIVE'), _row(2, 'dev-2', 'SHUTOFF'),
            _row(3, 'prod-1', 'ACTIVE')]
    handler, service, _ = _instance_tool(monkeypatch, rows)

    await handler(name_contains='dev', status='active', action='stop')

    # Previously the name and status matches were joined (union).
    assert _acted(service) == ['dev-1']


@pytest.mark.asyncio
async def test_instance_flavor_and_image_filters_match_names(monkeypatch):
    rows = [_row(1, flavor='m1.small', image='ubuntu-24.04'),
            _row(2, flavor='m1.large', image='ubuntu-24.04'),
            _row(3, flavor='m1.small', image='rocky-9')]
    handler, service, listing = _instance_tool(monkeypatch, rows)

    await handler(flavor_contains='SMALL', action='stop')
    assert _acted(service) == ['dev-1', 'dev-3']
    assert listing.call_args.kwargs['enrich_images'] is False

    service.reset_mock()
    await handler(flavor_contains='small', image_contains='rocky', action='stop')
    assert _acted(service) == ['dev-3']
    assert listing.call_args.kwargs['enrich_images'] is True


@pytest.mark.asyncio
async def test_instance_filter_rejects_invalid_status(monkeypatch):
    handler, service, listing = _instance_tool(monkeypatch, [_row(1)])

    result = await handler(status='RUNNING', action='stop')

    assert result.startswith('Error: Invalid instance status "RUNNING"'), result
    listing.assert_not_called()
    service.assert_not_called()


@pytest.mark.asyncio
async def test_instance_filter_listing_failure_is_redacted(monkeypatch):
    handler, service, listing = _instance_tool(monkeypatch, [])
    listing.return_value = {'instances': [], 'success': False,
                            'error': 'private detail'}

    result = await handler(name_contains='dev', action='stop')

    assert 'OpenStack instance listing failed' in result
    assert 'private detail' not in result
    service.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize('value', ['0', '-5', 'abc', '1.5'])
async def test_instance_filter_rejects_invalid_limit(monkeypatch, value):
    monkeypatch.setenv('INSTANCE_FILTER_MAX_MATCHES', value)
    handler, service, _ = _instance_tool(monkeypatch, [_row(1)])

    result = await handler(name_contains='dev', action='stop')

    assert 'INSTANCE_FILTER_MAX_MATCHES must be a positive integer' in result
    service.assert_not_called()


@pytest.mark.asyncio
async def test_flavor_set_alias_uses_backend_action_and_parameter(monkeypatch):
    module = importlib.import_module('mcp_openstack_ops.tools.set_flavor')
    service = Mock(return_value={'success': True})
    monkeypatch.setattr(module, '_set_flavor', service)

    await _tool_handler(module, 'set_flavor')(
        flavor_name='small', action='set', properties='{"hw:cpu_policy": "shared"}',
    )

    assert service.call_args.kwargs['action'] == 'set_extra_specs'
    assert service.call_args.kwargs['extra_specs'] == {'hw:cpu_policy': 'shared'}


@pytest.mark.asyncio
async def test_project_set_alias_forwards_backend_parameter_names(monkeypatch):
    module = importlib.import_module('mcp_openstack_ops.tools.set_project')
    service = Mock(return_value={'success': True})
    monkeypatch.setattr(module, '_set_project', service)

    await _tool_handler(module, 'set_project')(
        project_name='project', action='set', enable=True, domain='default',
    )

    assert service.call_args.kwargs['action'] == 'update'
    assert service.call_args.kwargs['enabled'] is True
    assert service.call_args.kwargs['domain_id'] == 'default'


@pytest.mark.asyncio
async def test_keypair_import_alias_calls_create(monkeypatch):
    module = importlib.import_module('mcp_openstack_ops.tools.set_keypair')
    service = Mock(return_value={'success': True})
    monkeypatch.setattr(module, '_set_keypair', service)
    monkeypatch.setattr(module, '_get_resource_status_by_name', Mock(return_value='Unknown'))
    monkeypatch.setattr('time.sleep', lambda _: None)

    await _tool_handler(module, 'set_keypair')(
        action='import', keypair_names='key', public_key='ssh-ed25519 placeholder',
    )

    assert service.call_args.args[:2] == ('key', 'create')


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


@pytest.mark.parametrize('kwargs,expected', [
    ({'size': 1, 'new_size': 2}, 2),
    ({'size': 3, 'new_size': None}, 3),
    ({'size': 4}, 4),
])
def test_volume_extend_prefers_explicit_new_size(volume_connection, kwargs, expected):
    conn, _, volume = volume_connection
    volume.size = 1
    result = storage.set_volume(volume.name, 'extend', **kwargs)
    assert result['success']
    conn.volume.extend_volume.assert_called_once_with(volume, size=expected)


@pytest.mark.parametrize(
    "snapshots,name,expected",
    [
        ([{"name": "snap-a", "status": "available"}], "snap-a", "available"),
        ([{"name": "other", "status": "available"}], "snap-a", "Not Found"),
        ({"error": "API failure"}, "snap-a", "Not Found"),
    ],
)
def test_snapshot_resource_status(monkeypatch, snapshots, name, expected):
    from mcp_openstack_ops import mcp_main

    monkeypatch.setattr(mcp_main, "_get_volume_snapshots", lambda: snapshots)

    assert mcp_main._get_resource_status_by_name("snapshot", name) == expected


@pytest.mark.parametrize('available', [True, False, None])
def test_availability_zones_read_sdk_state(monkeypatch, available):
    from openstack.compute.v2.availability_zone import AvailabilityZone as ComputeZone
    from openstack.block_storage.v3.availability_zone import AvailabilityZone as VolumeZone

    conn = Mock()
    state = {'available': available} if available is not None else None
    conn.compute.availability_zones.return_value = [ComputeZone(name='nova', state=state)]
    conn.volume.availability_zones.return_value = [VolumeZone(name='nova', state=state)]
    conn.network.availability_zones.return_value = []
    monkeypatch.setattr(connection, 'get_openstack_connection', lambda: conn)
    zones = monitoring.get_availability_zones()['availability_zones']
    assert zones['compute'][0]['available'] is available
    assert zones['volume'][0]['available'] is available


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


@pytest.mark.asyncio
@pytest.mark.parametrize('parameter', ['parent', 'tags'])
async def test_project_rejects_unimplemented_parameters(monkeypatch, parameter):
    module = importlib.import_module('mcp_openstack_ops.tools.set_project')
    service = Mock(return_value={'success': True})
    monkeypatch.setattr(module, '_set_project', service)

    result = await _tool_handler(module, 'set_project')(
        project_name='project', action='create', **{parameter: 'value'},
    )

    assert result.startswith('Error: Not implemented'), result
    service.assert_not_called()
