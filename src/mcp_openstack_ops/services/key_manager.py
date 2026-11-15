"""Barbican (key-manager) operations that never carry secret payloads.

Secret payloads are kept out of every request and response on purpose: tool
arguments and results pass through the client's LLM, so a key or password
there would leak to an external model. Upload user certificates through the
CLI or another trusted path, then reference them by name or href.

``Proxy.get_secret`` and ``Proxy.find_secret`` download the decrypted payload
(``Secret.fetch`` calls ``/payload``), so this module reads secret metadata
with a plain GET instead and never calls them.
"""

import base64
import datetime
import ipaddress
import itertools
import re
from typing import Any, Dict, List, Optional

from ..connection import get_openstack_connection

MAX_LIMIT = 1000
_UUID = re.compile(r'^[0-9a-fA-F]{8}-(?:[0-9a-fA-F]{4}-){3}[0-9a-fA-F]{12}$')
KEY_MANAGER_UNAVAILABLE = 'Barbican (key-manager) service is not available'
SECRET_FIELDS = (
    'name', 'secret_ref', 'secret_type', 'status', 'algorithm', 'bit_length',
    'mode', 'content_types', 'expiration', 'created', 'updated', 'creator_id',
)


def _is_unavailable(exc: BaseException) -> bool:
    from openstack import exceptions as sdk_exceptions
    if isinstance(exc, (sdk_exceptions.EndpointNotFound,
                        sdk_exceptions.ServiceDisabledException,
                        sdk_exceptions.ServiceDiscoveryException)):
        return True
    from keystoneauth1 import exceptions as ksa_exceptions
    return isinstance(exc, ksa_exceptions.EndpointNotFound)


def _failure(operation: str, exc: BaseException) -> Dict[str, Any]:
    message = KEY_MANAGER_UNAVAILABLE if _is_unavailable(exc) else f'{operation} failed'
    return {'success': False, 'message': message, 'error': str(exc)}


def _check_limit(limit: int) -> None:
    if not 1 <= limit <= MAX_LIMIT:
        raise ValueError(f'limit must be between 1 and {MAX_LIMIT}')


def _ref_id(ref: Optional[str]) -> Optional[str]:
    return ref.rstrip('/').rsplit('/', 1)[-1] if ref else None


def _api(conn: Any, method: str, path: str, **kwargs: Any) -> Any:
    """Call the key-manager endpoint and raise on HTTP errors.

    Accept is always JSON: older Barbican answers GET /secrets/{id} with the
    payload when another media type is accepted.
    """
    response = getattr(conn.key_manager, method)(
        path, raise_exc=True, headers={'Accept': 'application/json'}, **kwargs)
    return response.json() if response.content else {}


def _secret_dict(data: Dict[str, Any]) -> Dict[str, Any]:
    """Keep metadata fields only, so a payload can never be returned."""
    item = {key: data.get(key) for key in SECRET_FIELDS}
    item['id'] = _ref_id(item['secret_ref'])
    return item


def _resolve(conn: Any, kind: str, name_or_ref: str) -> Dict[str, Any]:
    """Return the metadata of a secret or container by href, ID or unique name."""
    if not name_or_ref or not name_or_ref.strip():
        raise ValueError(f'{kind} name, ID or href is required')
    value = name_or_ref.strip()
    collection = f'{kind}s'
    if f'/{collection}/' in value or _UUID.match(value):
        return _api(conn, 'get', f'/{collection}/{_ref_id(value)}')
    data = _api(conn, 'get', f'/{collection}', params={'name': value, 'limit': 2})
    matches = [item for item in data.get(collection, []) if item.get('name') == value]
    if len(matches) != 1:
        raise ValueError(f'{kind} not found or name is ambiguous; use an ID or href: {value}')
    return matches[0]


def resolve_secret_ref(conn: Any, name_or_ref: str) -> str:
    """Return the href Octavia expects for a secret or container name/ID/href."""
    value = name_or_ref.strip()
    if value.startswith(('http://', 'https://')):
        return value
    try:
        return _resolve(conn, 'secret', value)['secret_ref']
    except ValueError:
        return _resolve(conn, 'container', value)['container_ref']


def _container_dict(data: Dict[str, Any]) -> Dict[str, Any]:
    return {
        'id': _ref_id(data.get('container_ref')),
        'name': data.get('name'),
        'container_ref': data.get('container_ref'),
        'type': data.get('type'),
        'status': data.get('status'),
        'secret_refs': data.get('secret_refs') or [],
        'consumers': data.get('consumers') or [],
        'created': data.get('created'),
        'updated': data.get('updated'),
    }


ORDER_FIELDS = (
    'order_ref', 'type', 'status', 'meta', 'secret_ref', 'container_ref',
    'sub_status', 'sub_status_message', 'error_status_code', 'error_reason',
    'created', 'updated', 'creator_id',
)


def _order_dict(data: Dict[str, Any]) -> Dict[str, Any]:
    """Read the raw order: the SDK Order resource drops container_ref."""
    item = {key: data.get(key) for key in ORDER_FIELDS}
    item['meta'] = {k: v for k, v in (item['meta'] or {}).items() if k != 'payload'}
    item['id'] = _ref_id(item['order_ref'])
    return item


def _list_raw(conn: Any, collection: str, limit: int,
              **filters: Any) -> Dict[str, Any]:
    """Page through a Barbican collection with offset/limit up to ``limit`` items."""
    items: List[Dict[str, Any]] = []
    offset = 0
    while len(items) <= limit:
        params = {**filters, 'offset': offset,
                  'limit': min(100, limit + 1 - len(items))}
        page = _api(conn, 'get', f'/{collection}', params=params)
        batch = page.get(collection, [])
        items.extend(batch)
        offset += len(batch)
        if not batch or offset >= page.get('total', 0):
            break
    return {'items': items[:limit], 'truncated': len(items) > limit}


# ---------------------------------------------------------------------------
# Read operations
# ---------------------------------------------------------------------------

def get_secrets(name: str = '', secret_type: str = '', limit: int = 100) -> Dict[str, Any]:
    """List secret metadata in the current project; with name, show one secret."""
    try:
        _check_limit(limit)
        conn = get_openstack_connection()
        if name:
            secret = _secret_dict(_resolve(conn, 'secret', name))
            try:  # Secret consumers need key-manager API 1.1.
                consumers = itertools.islice(
                    conn.key_manager.secret_consumers(secret['id']), MAX_LIMIT)
                secret['consumers'] = [
                    {'service': c.service, 'resource_type': c.resource_type,
                     'resource_id': c.resource_id} for c in consumers
                ]
            except Exception as exc:
                secret['consumers_error'] = str(exc)
            return {'success': True, 'secret': secret}
        filters = {'secret_type': secret_type} if secret_type else {}
        listed = _list_raw(conn, 'secrets', limit, **filters)
        secrets = [_secret_dict(item) for item in listed['items']]
        return {'success': True, 'secrets': secrets, 'count': len(secrets),
                'truncated': listed['truncated']}
    except Exception as exc:
        return _failure('Barbican secret query', exc)


def get_secret_containers(name: str = '', limit: int = 100) -> Dict[str, Any]:
    """List containers in the current project; with name, show one container."""
    try:
        _check_limit(limit)
        conn = get_openstack_connection()
        if name:
            return {'success': True,
                    'container': _container_dict(_resolve(conn, 'container', name))}
        listed = _list_raw(conn, 'containers', limit)
        containers = [_container_dict(item) for item in listed['items']]
        return {'success': True, 'containers': containers, 'count': len(containers),
                'truncated': listed['truncated']}
    except Exception as exc:
        return _failure('Barbican container query', exc)


def get_secret_orders(order_id: str = '', limit: int = 100) -> Dict[str, Any]:
    """List key-generation orders; with order_id (ID or href), show one order."""
    try:
        _check_limit(limit)
        conn = get_openstack_connection()
        if order_id:
            return {'success': True, 'order': _order_dict(
                _api(conn, 'get', f'/orders/{_ref_id(order_id)}'))}
        listed = _list_raw(conn, 'orders', limit)
        orders = [_order_dict(item) for item in listed['items']]
        return {'success': True, 'orders': orders, 'count': len(orders),
                'truncated': listed['truncated']}
    except Exception as exc:
        return _failure('Barbican order query', exc)


def get_secret_acl(name_or_ref: str, target_type: str = 'secret') -> Dict[str, Any]:
    """Show the read ACL of a secret or container."""
    try:
        conn = get_openstack_connection()
        target = _acl_target(conn, name_or_ref, target_type)
        acl = _api(conn, 'get', f"{target['path']}/acl")
        return {'success': True, 'target_type': target_type, 'name': target['name'],
                'ref': target['ref'], 'acl': acl}
    except Exception as exc:
        return _failure('Barbican ACL query', exc)


def get_key_manager_quotas() -> Dict[str, Any]:
    """Show the effective Barbican quotas of the current project (-1 = unlimited)."""
    try:
        quota = get_openstack_connection().key_manager.get_quota()
        return {'success': True, 'quotas': {
            'secrets': quota.secrets, 'orders': quota.orders,
            'containers': quota.containers, 'consumers': quota.consumers,
            'cas': quota.cas,
        }}
    except Exception as exc:
        return _failure('Barbican quota query', exc)


def get_secret_stores() -> Dict[str, Any]:
    """List secret stores; only clouds with multiple backends enabled serve this."""
    try:
        stores = [{
            'id': store.secret_store_id, 'name': store.name, 'status': store.status,
            'global_default': store.global_default,
            'secret_store_plugin': store.secret_store_plugin,
            'crypto_plugin': store.crypto_plugin,
        } for store in get_openstack_connection().key_manager.secret_stores()]
        return {'success': True, 'secret_stores': stores, 'count': len(stores)}
    except Exception as exc:
        result = _failure('Barbican secret store query', exc)
        if not _is_unavailable(exc):
            result['message'] += ('; this API is served only when Barbican '
                                  'enables multiple secret store backends')
        return result


# ---------------------------------------------------------------------------
# Write operations
# ---------------------------------------------------------------------------

def _self_signed_pkcs12(common_name: str, subject_alt_names: List[str], days: int,
                        key_size: int) -> Dict[str, Any]:
    """Build an unencrypted PKCS#12 bundle; the key never leaves this process."""
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.hazmat.primitives.serialization import pkcs12
    from cryptography.x509.oid import NameOID

    names = []
    for value in subject_alt_names:
        try:
            names.append(x509.IPAddress(ipaddress.ip_address(value)))
        except ValueError:
            names.append(x509.DNSName(value))
    key = rsa.generate_private_key(public_exponent=65537, key_size=key_size)
    subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, common_name)])
    now = datetime.datetime.now(datetime.timezone.utc)
    builder = (x509.CertificateBuilder()
               .subject_name(subject).issuer_name(subject)
               .public_key(key.public_key())
               .serial_number(x509.random_serial_number())
               .not_valid_before(now - datetime.timedelta(minutes=5))
               .not_valid_after(now + datetime.timedelta(days=days))
               .add_extension(x509.BasicConstraints(ca=False, path_length=None),
                              critical=True))
    if names:
        builder = builder.add_extension(x509.SubjectAlternativeName(names),
                                        critical=False)
    cert = builder.sign(key, hashes.SHA256())
    bundle = pkcs12.serialize_key_and_certificates(
        common_name.encode(), key, cert, None, serialization.NoEncryption())
    return {
        'payload': base64.b64encode(bundle).decode('ascii'),
        'certificate_pem': cert.public_bytes(serialization.Encoding.PEM).decode('ascii'),
        'sha256_fingerprint': cert.fingerprint(hashes.SHA256()).hex(':'),
        'not_after': cert.not_valid_after_utc.isoformat(),
    }


def set_secret(action: str, name: str = '', common_name: str = '',
               subject_alt_names: Optional[List[str]] = None, days: int = 365,
               key_size: int = 2048, expiration: str = '') -> Dict[str, Any]:
    """Create a self-signed TLS secret or delete a secret.

    No action accepts a payload: uploading user key material would pass it
    through the LLM, so that path is intentionally not provided.
    """
    try:
        action = (action or '').lower()
        if action not in {'create_self_signed_tls', 'delete'}:
            raise ValueError('Supported actions: create_self_signed_tls, delete')
        conn = get_openstack_connection()
        if action == 'delete':
            secret = _secret_dict(_resolve(conn, 'secret', name))
            _api(conn, 'delete', f"/secrets/{secret['id']}")
            return {'success': True, 'message': f"Secret deleted: {secret['name']}",
                    'secret': secret}
        if not name or not common_name:
            raise ValueError('name and common_name are required')
        if not 1 <= days <= 3650:
            raise ValueError('days must be between 1 and 3650')
        if key_size not in (2048, 3072, 4096):
            raise ValueError('key_size must be 2048, 3072 or 4096')
        generated = _self_signed_pkcs12(common_name, subject_alt_names or [],
                                        days, key_size)
        attrs = {
            'name': name, 'secret_type': 'opaque',
            'payload': generated.pop('payload'),
            'payload_content_type': 'application/octet-stream',
            'payload_content_encoding': 'base64',
        }
        if expiration:
            attrs['expiration'] = expiration
        created = conn.key_manager.create_secret(**attrs)
        return {
            'success': True,
            'message': ('Self-signed TLS certificate stored as a PKCS#12 secret; '
                        'the private key is not returned'),
            'secret': {'name': name, 'secret_ref': created.secret_ref,
                       'id': _ref_id(created.secret_ref)},
            'certificate': {'common_name': common_name,
                            'subject_alt_names': subject_alt_names or [],
                            **generated},
        }
    except Exception as exc:
        return _failure('Barbican secret operation', exc)


CONTAINER_TYPES = {'generic', 'certificate', 'rsa'}


def set_secret_container(action: str, name: str = '', container_type: str = 'generic',
                         secret_refs: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    """Create a container from existing secrets or delete a container."""
    try:
        action = (action or '').lower()
        if action not in {'create', 'delete'}:
            raise ValueError('Supported actions: create, delete')
        conn = get_openstack_connection()
        if action == 'delete':
            container = _container_dict(_resolve(conn, 'container', name))
            _api(conn, 'delete', f"/containers/{container['id']}")
            return {'success': True,
                    'message': f"Container deleted: {container['name']}",
                    'container': container}
        if not name:
            raise ValueError('name is required')
        if container_type not in CONTAINER_TYPES:
            raise ValueError(f'container_type must be one of {sorted(CONTAINER_TYPES)}')
        if not secret_refs:
            raise ValueError('secret_refs is required, e.g. {"certificate": "<secret>"}')
        refs = [{'name': ref_name,
                 'secret_ref': _resolve(conn, 'secret', value)['secret_ref']}
                for ref_name, value in secret_refs.items()]
        created = conn.key_manager.create_container(
            name=name, type=container_type, secret_refs=refs)
        return {'success': True, 'message': f'Container created: {name}',
                'container': {'name': name, 'type': container_type,
                              'container_ref': created.container_ref,
                              'id': _ref_id(created.container_ref),
                              'secret_refs': refs}}
    except Exception as exc:
        return _failure('Barbican container operation', exc)


ORDER_DEFAULTS = {
    'key': {'algorithm': 'aes', 'bit_length': 256, 'mode': 'cbc'},
    'asymmetric': {'algorithm': 'rsa', 'bit_length': 2048},
}


def set_secret_order(action: str, order_id: str = '', order_type: str = 'key',
                     name: str = '', algorithm: str = '', bit_length: int = 0,
                     mode: str = '', expiration: str = '') -> Dict[str, Any]:
    """Order Barbican to generate a key inside Barbican, or delete an order.

    The generated key stays in Barbican; only references are returned.
    """
    try:
        action = (action or '').lower()
        if action not in {'create', 'delete'}:
            raise ValueError('Supported actions: create, delete')
        conn = get_openstack_connection()
        if action == 'delete':
            if not order_id:
                raise ValueError('order_id is required')
            conn.key_manager.delete_order(_ref_id(order_id), ignore_missing=False)
            return {'success': True, 'message': f'Order deleted: {_ref_id(order_id)}'}
        if order_type not in ORDER_DEFAULTS:
            raise ValueError('order_type must be key or asymmetric')
        if not name:
            raise ValueError('name is required')
        meta = dict(ORDER_DEFAULTS[order_type], name=name,
                    payload_content_type='application/octet-stream')
        if algorithm:
            meta['algorithm'] = algorithm
        if bit_length:
            meta['bit_length'] = bit_length
        if mode:
            meta['mode'] = mode
        if expiration:
            meta['expiration'] = expiration
        order = conn.key_manager.create_order(type=order_type, meta=meta)
        return {'success': True,
                'message': ('Order accepted; Barbican generates the key '
                            'asynchronously. Check it with get_secret_orders.'),
                'order': {'id': _ref_id(order.order_ref), 'order_ref': order.order_ref,
                          'type': order_type, 'meta': meta}}
    except Exception as exc:
        return _failure('Barbican order operation', exc)


def _acl_target(conn: Any, name_or_ref: str, target_type: str) -> Dict[str, Any]:
    if target_type not in {'secret', 'container'}:
        raise ValueError('target_type must be secret or container')
    data = _resolve(conn, target_type, name_or_ref)
    ref = data.get(f'{target_type}_ref')
    return {'path': f'/{target_type}s/{_ref_id(ref)}', 'ref': ref,
            'name': data.get('name')}


def set_secret_acl(action: str, name_or_ref: str, target_type: str = 'secret',
                   users: Optional[List[str]] = None,
                   project_access: Optional[bool] = None) -> Dict[str, Any]:
    """Change the read ACL of a secret or container.

    add_users/remove_users edit the user list, set replaces it (and optionally
    project_access), delete restores the default project-wide access.
    """
    try:
        action = (action or '').lower()
        if action not in {'add_users', 'remove_users', 'set', 'delete'}:
            raise ValueError('Supported actions: add_users, remove_users, set, delete')
        if action in {'add_users', 'remove_users'} and not users:
            raise ValueError('users is required for add_users and remove_users')
        conn = get_openstack_connection()
        target = _acl_target(conn, name_or_ref, target_type)
        path = f"{target['path']}/acl"
        if action == 'delete':
            _api(conn, 'delete', path)
        elif action == 'set':
            read: Dict[str, Any] = {'users': list(users or [])}
            if project_access is not None:
                read['project-access'] = project_access
            _api(conn, 'put', path, json={'read': read})
        else:
            current = _api(conn, 'get', path).get('read', {}).get('users', [])
            if action == 'add_users':
                updated = list(dict.fromkeys([*current, *users]))
            else:
                updated = [user for user in current if user not in set(users)]
            _api(conn, 'patch', path, json={'read': {'users': updated}})
        acl = _api(conn, 'get', path)
        return {'success': True, 'message': f'ACL {action} applied',
                'target_type': target_type, 'name': target['name'],
                'ref': target['ref'], 'acl': acl}
    except Exception as exc:
        return _failure('Barbican ACL operation', exc)
