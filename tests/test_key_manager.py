"""Barbican tools: metadata only, no payload in or out, Octavia TLS references."""

import base64
import json
from types import SimpleNamespace
from unittest.mock import create_autospec

import pytest
from cryptography import x509
from cryptography.hazmat.primitives.serialization import pkcs12
from keystoneauth1 import exceptions as ksa_exceptions
from openstack.key_manager.v1._proxy import Proxy as KeyManagerProxy
from openstack.key_manager.v1.secret import Secret
from openstack.load_balancer.v2._proxy import Proxy as LoadBalancerProxy
from openstack.load_balancer.v2.listener import Listener
from openstack.load_balancer.v2.load_balancer import LoadBalancer

from mcp_openstack_ops import connection
from mcp_openstack_ops.services import key_manager
from openstack.load_balancer.v2.pool import Pool

from mcp_openstack_ops.services.load_balancer import listeners, pools

BASE = 'https://kms.example/v1'
SECRET_ID = '11111111-2222-3333-4444-555555555555'
SECRET_REF = f'{BASE}/secrets/{SECRET_ID}'
CONTAINER_ID = '99999999-2222-3333-4444-555555555555'
CONTAINER_REF = f'{BASE}/containers/{CONTAINER_ID}'


class Response:
    def __init__(self, data=None):
        self._data = data
        self.content = b'' if data is None else json.dumps(data).encode()

    def json(self):
        return self._data


def _secret(name='web-tls', **extra):
    return {'name': name, 'secret_ref': SECRET_REF, 'secret_type': 'opaque',
            'status': 'ACTIVE', 'content_types': {'default': 'application/octet-stream'},
            **extra}


@pytest.fixture
def conn(monkeypatch):
    value = SimpleNamespace(
        current_project_id='project-a',
        key_manager=create_autospec(KeyManagerProxy, instance=True),
        load_balancer=create_autospec(LoadBalancerProxy, instance=True),
    )
    value.routes = {}
    value.calls = []

    def route(method):
        def handler(path, **kwargs):
            value.calls.append((method, path, kwargs))
            assert kwargs['headers'] == {'Accept': 'application/json'}
            assert kwargs['raise_exc'] is True
            result = value.routes[(method, path)]
            return Response(result(kwargs) if callable(result) else result)
        return handler

    for method in ('get', 'put', 'patch', 'delete'):
        getattr(value.key_manager, method).side_effect = route(method)
    for module in (connection, key_manager, listeners, pools):
        monkeypatch.setattr(module, 'get_openstack_connection', lambda: value)
    yield value
    # Both SDK calls download the decrypted payload; they must never be used.
    value.key_manager.get_secret.assert_not_called()
    value.key_manager.find_secret.assert_not_called()


def test_secret_list_pages_and_drops_payload(conn):
    pages = {0: [_secret('a', payload='TOP-SECRET'), _secret('b')], 2: [_secret('c')]}
    conn.routes[('get', '/secrets')] = lambda kw: {
        'secrets': pages[kw['params']['offset']], 'total': 3}

    result = key_manager.get_secrets(limit=2)

    assert result['success'] is True, result
    assert [s['name'] for s in result['secrets']] == ['a', 'b']
    assert result['truncated'] is True
    assert result['secrets'][0]['id'] == SECRET_ID
    assert 'TOP-SECRET' not in json.dumps(result)
    assert all('payload' not in s for s in result['secrets'])


def test_secret_show_by_name_reads_metadata_and_consumers(conn):
    conn.routes[('get', '/secrets')] = {'secrets': [_secret()], 'total': 1}
    conn.key_manager.secret_consumers.return_value = iter([SimpleNamespace(
        service='octavia', resource_type='listener', resource_id='lis-1')])

    result = key_manager.get_secrets(name='web-tls')

    assert result['success'] is True, result
    assert result['secret']['secret_ref'] == SECRET_REF
    assert result['secret']['consumers'][0]['service'] == 'octavia'
    _, path, kwargs = conn.calls[0]
    assert path == '/secrets' and kwargs['params']['name'] == 'web-tls'
    conn.key_manager.secret_consumers.assert_called_once_with(SECRET_ID)


def test_secret_show_by_href_uses_metadata_get(conn):
    conn.routes[('get', f'/secrets/{SECRET_ID}')] = _secret()
    conn.key_manager.secret_consumers.side_effect = RuntimeError('API 1.1 required')

    result = key_manager.get_secrets(name=SECRET_REF)

    assert result['success'] is True, result
    assert result['secret']['consumers_error'] == 'API 1.1 required'


def test_ambiguous_name_is_rejected(conn):
    conn.routes[('get', '/secrets')] = {'secrets': [_secret(), _secret()], 'total': 2}

    result = key_manager.set_secret('delete', name='web-tls')

    assert result['success'] is False
    assert 'ambiguous' in result['error']


def test_self_signed_tls_stores_pkcs12_and_never_returns_the_key(conn):
    conn.key_manager.create_secret.return_value = Secret.existing(secret_ref=SECRET_REF)

    result = key_manager.set_secret(
        'create_self_signed_tls', name='web-tls', common_name='192.168.35.169',
        subject_alt_names=['192.168.35.169', '10.40.40.185', 'web.example'])

    assert result['success'] is True, result
    assert result['secret']['secret_ref'] == SECRET_REF
    text = json.dumps(result)
    assert 'PRIVATE KEY' not in text and 'payload' not in text
    assert 'BEGIN CERTIFICATE' in result['certificate']['certificate_pem']
    _, attrs = conn.key_manager.create_secret.call_args
    assert attrs['secret_type'] == 'opaque'
    assert attrs['payload_content_encoding'] == 'base64'
    key, cert, _ = pkcs12.load_key_and_certificates(
        base64.b64decode(attrs['payload']), None)
    assert key is not None
    san = cert.extensions.get_extension_for_class(x509.SubjectAlternativeName).value
    assert [str(ip) for ip in san.get_values_for_type(x509.IPAddress)] == [
        '192.168.35.169', '10.40.40.185']
    assert san.get_values_for_type(x509.DNSName) == ['web.example']
    assert attrs['payload'] not in text


@pytest.mark.parametrize('action', ['store', 'create', 'get_payload'])
def test_set_secret_offers_no_payload_upload(conn, action):
    result = key_manager.set_secret(action, name='x')

    assert result['success'] is False
    assert 'create_self_signed_tls, delete' in result['error']
    conn.key_manager.create_secret.assert_not_called()


def test_set_secret_tool_has_no_payload_parameter():
    import inspect
    from mcp_openstack_ops.tools import set_secret as tool
    handler = tool.set_secret
    handler = getattr(handler, 'fn', handler)
    assert not any('payload' in p for p in inspect.signature(handler).parameters)


def test_secret_delete_resolves_name(conn):
    conn.routes[('get', '/secrets')] = {'secrets': [_secret()], 'total': 1}
    conn.routes[('delete', f'/secrets/{SECRET_ID}')] = None

    result = key_manager.set_secret('delete', name='web-tls')

    assert result['success'] is True, result
    assert ('delete', f'/secrets/{SECRET_ID}') in [(m, p) for m, p, _ in conn.calls]


def test_container_create_resolves_secret_names(conn):
    conn.routes[('get', '/secrets')] = {'secrets': [_secret('web-cert')], 'total': 1}
    conn.key_manager.create_container.return_value = SimpleNamespace(
        container_ref=CONTAINER_REF)

    result = key_manager.set_secret_container(
        'create', name='web', container_type='certificate',
        secret_refs={'certificate': 'web-cert'})

    assert result['success'] is True, result
    conn.key_manager.create_container.assert_called_once_with(
        name='web', type='certificate',
        secret_refs=[{'name': 'certificate', 'secret_ref': SECRET_REF}])


def test_order_create_defaults_and_show_keeps_container_ref(conn):
    conn.key_manager.create_order.return_value = SimpleNamespace(
        order_ref=f'{BASE}/orders/o-1')

    created = key_manager.set_secret_order('create', order_type='asymmetric', name='k')
    conn.routes[('get', '/orders/o-1')] = {
        'order_ref': f'{BASE}/orders/o-1', 'type': 'asymmetric', 'status': 'ACTIVE',
        'container_ref': CONTAINER_REF, 'meta': {'name': 'k', 'payload': 'x'}}
    shown = key_manager.get_secret_orders(order_id=f'{BASE}/orders/o-1')

    assert created['success'] is True, created
    _, kwargs = conn.key_manager.create_order.call_args
    assert kwargs['type'] == 'asymmetric'
    assert kwargs['meta']['algorithm'] == 'rsa' and kwargs['meta']['bit_length'] == 2048
    assert shown['order']['container_ref'] == CONTAINER_REF
    assert 'payload' not in shown['order']['meta']


def test_acl_add_users_merges_existing_users(conn):
    conn.routes[('get', '/secrets')] = {'secrets': [_secret()], 'total': 1}
    acl_path = f'/secrets/{SECRET_ID}/acl'
    conn.routes[('get', acl_path)] = {'read': {'users': ['u1'], 'project-access': True}}
    conn.routes[('patch', acl_path)] = None

    result = key_manager.set_secret_acl('add_users', 'web-tls', users=['u2', 'u1'])

    assert result['success'] is True, result
    patch = [kw for m, p, kw in conn.calls if m == 'patch'][0]
    assert patch['json'] == {'read': {'users': ['u1', 'u2']}}


def test_acl_set_replaces_users_and_project_access(conn):
    conn.routes[('get', f'/containers/{CONTAINER_ID}')] = {
        'name': 'web', 'container_ref': CONTAINER_REF}
    acl_path = f'/containers/{CONTAINER_ID}/acl'
    conn.routes[('put', acl_path)] = None
    conn.routes[('get', acl_path)] = {'read': {'users': ['u3']}}

    result = key_manager.set_secret_acl(
        'set', CONTAINER_REF, target_type='container', users=['u3'],
        project_access=False)

    assert result['success'] is True, result
    put = [kw for m, p, kw in conn.calls if m == 'put'][0]
    assert put['json'] == {'read': {'users': ['u3'], 'project-access': False}}


def test_missing_barbican_endpoint_is_reported(conn):
    conn.key_manager.get_quota.side_effect = ksa_exceptions.EndpointNotFound('none')

    result = key_manager.get_key_manager_quotas()

    assert result == {'success': False, 'message': key_manager.KEY_MANAGER_UNAVAILABLE,
                      'error': 'none'}


def _lb():
    return LoadBalancer.existing(id='lb-1', name='web-lb')


def _listener(**overrides):
    attrs = dict(id='lis-1', name='https', protocol='TERMINATED_HTTPS',
                 protocol_port=443, is_admin_state_up=True,
                 load_balancers=[{'id': 'lb-1'}],
                 default_tls_container_ref=SECRET_REF, sni_container_refs=[])
    attrs.update(overrides)
    return Listener.existing(**attrs)


def test_terminated_https_requires_default_certificate(conn):
    result = listeners.set_load_balancer_listener(
        'create', name='https', lb_name_or_id='web-lb',
        protocol='TERMINATED_HTTPS', protocol_port=443)

    assert result['success'] is False
    assert 'default_tls_container_ref' in result['message']
    conn.load_balancer.create_listener.assert_not_called()


def test_terminated_https_listener_resolves_secret_names(conn):
    conn.routes[('get', '/secrets')] = {'secrets': [_secret()], 'total': 1}
    conn.load_balancer.find_load_balancer.return_value = _lb()
    conn.load_balancer.create_listener.return_value = _listener()

    result = listeners.set_load_balancer_listener(
        'create', name='https', lb_name_or_id='web-lb', protocol='terminated_https',
        protocol_port=443, default_tls_container_ref='web-tls',
        sni_container_refs=[SECRET_REF], default_pool_id='pool-1')

    assert result['success'] is True, result
    assert result['listener']['default_tls_container_ref'] == SECRET_REF
    _, kwargs = conn.load_balancer.create_listener.call_args
    created = Listener.new(**kwargs)
    assert created.protocol == 'TERMINATED_HTTPS'
    assert created.default_tls_container_ref == SECRET_REF
    assert created.sni_container_refs == [SECRET_REF]


def test_listener_falls_back_to_certificate_container(conn):
    conn.routes[('get', '/secrets')] = {'secrets': [], 'total': 0}
    conn.routes[('get', '/containers')] = {
        'containers': [{'name': 'web', 'container_ref': CONTAINER_REF}], 'total': 1}
    conn.load_balancer.find_listener.return_value = _listener()
    conn.load_balancer.update_listener.return_value = _listener(
        default_tls_container_ref=CONTAINER_REF)

    result = listeners.set_load_balancer_listener(
        'set', listener_name_or_id='https', default_tls_container_ref='web')

    assert result['success'] is True, result
    conn.load_balancer.update_listener.assert_called_once_with(
        'lis-1', default_tls_container_ref=CONTAINER_REF)


def test_listener_certificate_error_carries_prerequisite_hint(conn):
    conn.load_balancer.find_load_balancer.return_value = _lb()
    conn.load_balancer.create_listener.side_effect = RuntimeError(
        f"Could not retrieve certificate: ['{SECRET_REF}']")

    result = listeners.set_load_balancer_listener(
        'create', name='https', lb_name_or_id='web-lb', protocol='TERMINATED_HTTPS',
        protocol_port=443, default_tls_container_ref=SECRET_REF)

    assert result['success'] is False
    assert 'docs/barbican-tls-guide.md' in result['message']


def test_listener_show_reports_tls_refs(conn):
    conn.load_balancer.find_listener.return_value = _listener(sni_container_refs=[SECRET_REF])

    result = listeners.set_load_balancer_listener('show', listener_name_or_id='https')

    assert result['listener']['default_tls_container_ref'] == SECRET_REF
    assert result['listener']['sni_container_refs'] == [SECRET_REF]


CA_ID = '22222222-2222-3333-4444-555555555555'
CA_REF = f'{BASE}/secrets/{CA_ID}'


def _pool(**overrides):
    attrs = dict(id='pool-1', name='web-pool', description='', protocol='HTTP',
                 lb_algorithm='ROUND_ROBIN', is_admin_state_up=True,
                 provisioning_status='ACTIVE', operating_status='ONLINE',
                 listeners=[{'id': 'lis-1'}], tls_enabled=True,
                 ca_tls_container_ref=CA_REF, tls_versions=['TLSv1.3'])
    attrs.update(overrides)
    return Pool.existing(**attrs)


def _secret_routes(conn):
    by_name = {'web-tls': _secret(), 'web-ca': _secret('web-ca', secret_ref=CA_REF)}
    conn.routes[('get', '/secrets')] = lambda kw: {
        'secrets': [by_name[kw['params']['name']]], 'total': 1}


def test_reencrypt_pool_create_uses_sdk_with_resolved_ca(conn):
    _secret_routes(conn)
    conn.load_balancer.listeners.return_value = [_listener()]
    conn.load_balancer.create_pool.return_value = _pool()

    result = pools.set_load_balancer_pool(
        'create', name='web-pool', listener_name_or_id='https', protocol='http',
        tls_enabled=True, ca_tls_container_ref='web-ca', tls_versions=['TLSv1.3'])

    assert result['success'] is True, result
    assert result['pool']['tls_enabled'] is True
    _, kwargs = conn.load_balancer.create_pool.call_args
    created = Pool.new(**kwargs)
    assert created.tls_enabled is True
    assert created.ca_tls_container_ref == CA_REF
    assert created.tls_versions == ['TLSv1.3']
    conn.load_balancer.post.assert_not_called()


def test_mtls_pool_create_sends_client_cert_through_octavia_api(conn):
    _secret_routes(conn)
    conn.load_balancer.listeners.return_value = [_listener()]
    conn.load_balancer.post.return_value = Response({'pool': {'id': 'pool-1'}})
    conn.load_balancer.get_pool.return_value = _pool()

    result = pools.set_load_balancer_pool(
        'create', name='web-pool', listener_name_or_id='https', protocol='HTTP',
        tls_enabled=True, tls_container_ref='web-tls', ca_tls_container_ref='web-ca')

    assert result['success'] is True, result
    conn.load_balancer.create_pool.assert_not_called()
    path = conn.load_balancer.post.call_args.args[0]
    body = conn.load_balancer.post.call_args.kwargs['json']['pool']
    assert path == '/lbaas/pools'
    assert conn.load_balancer.post.call_args.kwargs['raise_exc'] is True
    assert body == {
        'name': 'web-pool', 'listener_id': 'lis-1', 'protocol': 'HTTP',
        'lb_algorithm': 'ROUND_ROBIN', 'admin_state_up': True, 'tls_enabled': True,
        'tls_container_ref': SECRET_REF, 'ca_tls_container_ref': CA_REF,
    }
    conn.load_balancer.get_pool.assert_called_once_with('pool-1')
    assert result['pool']['tls_container_ref'] == SECRET_REF


def test_mtls_pool_set_puts_only_updatable_fields(conn):
    _secret_routes(conn)
    conn.load_balancer.pools.return_value = [_pool()]
    conn.load_balancer.put.return_value = Response({'pool': {'id': 'pool-1'}})
    conn.load_balancer.get_pool.return_value = _pool()

    result = pools.set_load_balancer_pool(
        'set', pool_name_or_id='web-pool', lb_algorithm='',
        tls_container_ref=SECRET_REF)

    assert result['success'] is True, result
    conn.load_balancer.update_pool.assert_not_called()
    assert conn.load_balancer.put.call_args.args[0] == '/lbaas/pools/pool-1'
    assert conn.load_balancer.put.call_args.kwargs['json'] == {
        'pool': {'admin_state_up': True, 'tls_container_ref': SECRET_REF}}


def test_pool_set_without_client_cert_uses_sdk(conn):
    conn.load_balancer.pools.return_value = [_pool()]
    conn.load_balancer.update_pool.return_value = _pool(tls_enabled=False)

    result = pools.set_load_balancer_pool(
        'set', pool_name_or_id='web-pool', lb_algorithm='', tls_enabled=False)

    assert result['success'] is True, result
    assert result['pool']['tls_enabled'] is False
    _, kwargs = conn.load_balancer.update_pool.call_args
    assert kwargs['tls_enabled'] is False
    conn.load_balancer.put.assert_not_called()


def test_pool_show_and_list_report_tls_settings(conn):
    conn.load_balancer.pools.return_value = [_pool()]
    conn.load_balancer.members.return_value = []
    conn.load_balancer.get.return_value = Response(
        {'pool': {'id': 'pool-1', 'tls_container_ref': SECRET_REF}})

    shown = pools.set_load_balancer_pool('show', pool_name_or_id='web-pool')
    listed = pools.get_load_balancer_pools()

    assert shown['pool']['tls_container_ref'] == SECRET_REF
    assert shown['pool']['ca_tls_container_ref'] == CA_REF
    assert conn.load_balancer.get.call_args.args[0] == '/lbaas/pools/pool-1'
    assert listed['pools'][0]['tls_enabled'] is True


def test_pool_tool_validates_and_splits_tls_inputs(monkeypatch):
    import asyncio
    from mcp_openstack_ops import functions
    from mcp_openstack_ops.tools import set_load_balancer_pool as tool
    handler = getattr(tool.set_load_balancer_pool, 'fn', tool.set_load_balancer_pool)
    calls = []
    monkeypatch.setattr(functions, 'set_load_balancer_pool',
                        lambda **kw: calls.append(kw) or {'success': True})

    bad = json.loads(asyncio.run(handler(action='set', tls_enabled='yes')))
    asyncio.run(handler(action='set', pool_name_or_id='p', tls_enabled='TRUE',
                        tls_versions='TLSv1.2, TLSv1.3', alpn_protocols='h2,http/1.1'))

    assert bad['success'] is False
    assert calls[0]['tls_enabled'] is True
    assert calls[0]['tls_versions'] == ['TLSv1.2', 'TLSv1.3']
    assert calls[0]['alpn_protocols'] == ['h2', 'http/1.1']


def test_listener_results_report_octavia_states(conn):
    lb = _lb()
    conn.load_balancer.find_load_balancer.return_value = lb
    pending = _listener(provisioning_status='PENDING_CREATE', operating_status='OFFLINE')
    conn.load_balancer.listeners.return_value = [pending]
    conn.load_balancer.find_listener.return_value = _listener(
        provisioning_status='ACTIVE', operating_status='ONLINE')

    listed = listeners.get_load_balancer_listeners('web-lb')
    shown = listeners.set_load_balancer_listener('show', listener_name_or_id='https')

    assert listed['listeners'][0]['provisioning_status'] == 'PENDING_CREATE'
    assert listed['listeners'][0]['operating_status'] == 'OFFLINE'
    assert shown['listener']['provisioning_status'] == 'ACTIVE'
    assert shown['listener']['operating_status'] == 'ONLINE'
