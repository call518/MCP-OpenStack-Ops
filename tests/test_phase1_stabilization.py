"""Regression checks for issue #73's first external validation report."""

import asyncio
import logging
from types import SimpleNamespace
from unittest.mock import Mock

import httpx
import pytest

from mcp_openstack_ops import connection, user_connection as users
from mcp_openstack_ops.services import compute, identity, network, storage


@pytest.mark.parametrize('service', [
    network.get_network_details, network.get_routers,
    compute.get_flavor_list, storage.get_volume_list,
    storage.get_volume_snapshots, identity.get_user_list,
    identity.get_keypair_list,
])
def test_failed_queries_never_return_demo_resources(monkeypatch, service):
    monkeypatch.setattr(connection, 'get_openstack_connection',
                        Mock(side_effect=RuntimeError('private detail')))
    with pytest.raises(RuntimeError, match='OpenStack resource query failed'):
        service()


@pytest.mark.parametrize('selection', ['all', 'shared'])
def test_shared_subnet_visibility_keeps_private_resources_isolated(
    monkeypatch, caplog, selection
):
    shared = SimpleNamespace(id='shared-id', name='shared', project_id='owner',
                             is_shared=True, is_router_external=False)
    private = SimpleNamespace(id='private-id', name='private', project_id='other',
                              is_shared=False, is_router_external=False)
    subnet = SimpleNamespace(id='subnet', network_id='shared-id',
                             project_id='owner', cidr='192.0.2.0/24')
    wrong = SimpleNamespace(id='wrong', network_id='private-id', project_id='other')
    proxy = Mock()
    proxy.networks.return_value = [shared, private]
    proxy.subnets.return_value = [subnet, wrong]
    conn = SimpleNamespace(network=proxy, current_project_id='project')
    monkeypatch.setattr(connection, 'get_openstack_connection', lambda: conn)
    monkeypatch.setattr(connection, 'get_current_project_id', lambda: 'project')
    result = network.get_network_details(selection)
    assert [row['id'] for row in result] == ['shared-id']
    assert [row['id'] for row in result[0]['subnets']] == ['subnet']
    assert 'Subnet subnet' not in caplog.text
    assert 'Network shared-id' not in caplog.text
    proxy.subnets.assert_called_once_with(network_id='shared-id')


@pytest.mark.asyncio
async def test_auth_timing_failure_class_and_secret_safety(monkeypatch, caplog):
    monkeypatch.setattr(users, 'authenticate',
                        Mock(side_effect=TimeoutError('private-secret')))
    caplog.set_level(logging.INFO, logger=users.__name__)
    app = Mock()
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=users.UserConnectionMiddleware(app)),
        base_url='https://mcp.example',
    ) as client:
        reply = await client.post('/mcp', headers={
            'X-OpenStack-Application-Credential-ID': 'credential',
            'X-OpenStack-Application-Credential-Secret': 'private-secret',
        })
    assert reply.status_code == 503
    assert 'error_type=TimeoutError' in caplog.text
    assert 'auth_duration_ms=' in caplog.text
    assert 'private-secret' not in caplog.text + reply.text
    app.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize('outcome', ['success', 'failure', 'cancel'])
async def test_tool_timing_records_completion_and_cancellation(
    monkeypatch, caplog, outcome
):
    monkeypatch.setattr(users, 'enabled', True)
    caplog.set_level(logging.INFO, logger=users.__name__)
    principal = users.RequestIdentity(Mock(), 'user', 'project', (), 'request')
    token = users._identity.set(principal)

    async def invoke(context):
        if outcome == 'failure':
            raise RuntimeError('private-detail')
        if outcome == 'cancel':
            raise asyncio.CancelledError()
        return 'result'

    try:
        call = users.UserAuditMiddleware().on_call_tool(
            SimpleNamespace(message=SimpleNamespace(name='query')), invoke)
        if outcome == 'success':
            assert await call == 'result'
        else:
            with pytest.raises(RuntimeError if outcome == 'failure'
                               else asyncio.CancelledError):
                await call
    finally:
        users._identity.reset(token)
    assert 'duration_ms=' in caplog.text
    assert 'request_id=request' in caplog.text
    assert 'private-detail' not in caplog.text


def test_summary_status_filters_nova_without_image_or_volume_calls(monkeypatch):
    from openstack.compute.v2.server import Server
    conn = Mock()
    conn.compute.servers.return_value = [
        Server(id='a', name='active', project_id='project', status='ACTIVE'),
        Server(id='b', name='stopped', project_id='project', status='SHUTOFF'),
        Server(id='c', name='foreign', project_id='other', status='ACTIVE'),
    ]
    monkeypatch.setattr(connection, 'get_openstack_connection', lambda: conn)
    monkeypatch.setattr(connection, 'get_current_project_id', lambda: 'project')
    result = compute.get_instances_by_status('ACTIVE', enrich_images=False)
    assert [row['id'] for row in result] == ['a']
    conn.compute.servers.assert_called_once_with(
        details=True, all_projects=False, status='ACTIVE')
    conn.image.get_image.assert_not_called()
    conn.block_storage.get_volume.assert_not_called()


def test_name_search_enriches_only_selected_results(monkeypatch):
    from openstack.compute.v2.server import Server
    conn = Mock()
    conn.compute.servers.return_value = [
        Server(id=str(i), name=f'vm-{i}', project_id='project', status='ACTIVE')
        for i in range(20)
    ]
    monkeypatch.setattr(connection, 'get_openstack_connection', lambda: conn)
    monkeypatch.setattr(connection, 'get_current_project_id', lambda: 'project')
    enrich = Mock(return_value={'id': 'image', 'name': 'image'})
    monkeypatch.setattr(compute, '_get_server_image', enrich)
    result = compute.search_instances('vm-', ['name'], limit=2)
    assert len(result) == 2
    assert enrich.call_count == 2


@pytest.mark.asyncio
async def test_network_sdk_work_does_not_block_event_loop(monkeypatch):
    import importlib
    import threading
    import mcp_openstack_ops.mcp_main
    module = importlib.import_module('mcp_openstack_ops.tools.get_network_details')
    event_loop_thread = threading.get_ident()
    principal = users.RequestIdentity(Mock(), 'user', 'project', (), 'request')
    seen = []

    def query(name):
        seen.append((threading.get_ident(), users._identity.get()))
        return []

    monkeypatch.setattr(module, '_get_network_details', query)
    token = users._identity.set(principal)
    try:
        handler = getattr(module.get_network_details, 'fn', module.get_network_details)
        await handler()
    finally:
        users._identity.reset(token)
    assert seen[0][0] != event_loop_thread
    assert seen[0][1] is principal


@pytest.mark.asyncio
async def test_failed_network_query_is_an_explicit_tool_error(monkeypatch):
    import importlib
    from fastmcp.exceptions import ToolError
    import mcp_openstack_ops.mcp_main
    module = importlib.import_module('mcp_openstack_ops.tools.get_network_details')
    monkeypatch.setattr(module, '_get_network_details',
                        Mock(side_effect=RuntimeError('private-detail')))
    handler = getattr(module.get_network_details, 'fn', module.get_network_details)
    with pytest.raises(ToolError, match='OpenStack query failed') as caught:
        await handler()
    assert 'private-detail' not in str(caught.value)


def test_network_endpoint_override_is_explicitly_versioned(monkeypatch):
    monkeypatch.setenv('OS_AUTH_HOST', 'cloud.example')
    monkeypatch.setenv('OS_AUTH_PROTOCOL', 'https')
    monkeypatch.setattr(users.ApplicationCredential, 'get_access', lambda *args:
                        SimpleNamespace(user_id='user', project_id='project',
                                        auth_token='token'))
    principal = users.authenticate('credential', 'secret')
    try:
        assert principal.connection.config.get_endpoint('network').endswith('/v2.0')
    finally:
        users._close_connection(principal.connection)
