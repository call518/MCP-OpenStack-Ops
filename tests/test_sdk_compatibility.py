"""Regression tests for openstacksdk API compatibility.

These guard calls that broke with real openstacksdk proxies: methods that do
not exist on any release, and keyword arguments renamed between releases.

Limits of the static check: it only sees ``conn.<service>.<method>()`` calls
and simple ``api = conn.<service>`` aliases, and it cannot validate keywords
of proxy methods that accept ``**kwargs``/``**query`` (for example a wrong
filter name passed to a listing method). Resource attribute names are covered
by the behavioural tests that use real SDK resource objects.
"""

import ast
import inspect
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, create_autospec

import pytest
from openstack.block_storage.v3._proxy import Proxy as StorageProxy
from openstack.block_storage.v3.backup import Backup
from openstack.compute.v2._proxy import Proxy as ComputeProxy
from openstack.compute.v2.server import Server
from openstack.compute.v2.service import Service
from openstack.identity.v3._proxy import Proxy as IdentityProxy
from openstack.image.v2._proxy import Proxy as ImageProxy
from openstack.load_balancer.v2._proxy import Proxy as LoadBalancerProxy
from openstack.network.v2._proxy import Proxy as NetworkProxy
from openstack.orchestration.v1._proxy import Proxy as HeatProxy

from mcp_openstack_ops import connection, functions
from mcp_openstack_ops.services import compute, storage

SOURCE = Path(__file__).resolve().parents[1] / 'src' / 'mcp_openstack_ops'
PROXIES = {
    'compute': ComputeProxy,
    'network': NetworkProxy,
    'block_storage': StorageProxy,
    'volume': StorageProxy,
    'image': ImageProxy,
    'identity': IdentityProxy,
    'orchestration': HeatProxy,
    'load_balancer': LoadBalancerProxy,
}


def _proxy_calls():
    """Yield (location, service, method, keywords) for conn.<service>.<method>() calls.

    Also follows simple aliases such as ``api = conn.block_storage``.
    """
    for path in sorted(SOURCE.rglob('*.py')):
        tree = ast.parse(path.read_text())
        aliases = {}
        for node in ast.walk(tree):
            if (isinstance(node, ast.Assign) and isinstance(node.value, ast.Attribute)
                    and isinstance(node.value.value, ast.Name)
                    and node.value.value.id == 'conn' and node.value.attr in PROXIES):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        aliases[target.id] = node.value.attr
            elif (isinstance(node, ast.Assign) and isinstance(node.value, ast.Attribute)
                  and isinstance(node.value.value, ast.Call)
                  and node.value.attr in PROXIES):
                # api = get_openstack_connection().block_storage
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        aliases[target.id] = node.value.attr
        for node in ast.walk(tree):
            if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)):
                continue
            owner = node.func.value
            service = None
            if (isinstance(owner, ast.Attribute) and isinstance(owner.value, ast.Name)
                    and owner.value.id == 'conn' and owner.attr in PROXIES):
                service = owner.attr
            elif isinstance(owner, ast.Name) and owner.id in aliases:
                service = aliases[owner.id]
            if service:
                keywords = [kw.arg for kw in node.keywords if kw.arg]
                yield (f'{path.name}:{node.lineno}', service, node.func.attr, keywords)


def test_every_proxy_call_exists_in_installed_openstacksdk():
    calls = list(_proxy_calls())
    assert len(calls) > 150
    missing = [f'{loc} conn.{svc}.{method}()' for loc, svc, method, _ in calls
               if not hasattr(PROXIES[svc], method)]
    assert not missing, missing


def test_proxy_call_keywords_match_installed_openstacksdk():
    mismatches = []
    for loc, svc, method, keywords in _proxy_calls():
        target = getattr(PROXIES[svc], method, None)
        if target is None or not keywords:
            continue
        parameters = inspect.signature(target).parameters
        if any(p.kind is p.VAR_KEYWORD for p in parameters.values()):
            continue
        mismatches.extend(f'{loc} conn.{svc}.{method}({kw}=)'
                          for kw in keywords if kw not in parameters)
    assert not mismatches, mismatches


@pytest.fixture
def conn(monkeypatch):
    value = SimpleNamespace(
        current_project_id='project-a',
        compute=create_autospec(ComputeProxy, instance=True),
        network=create_autospec(NetworkProxy, instance=True),
        block_storage=create_autospec(StorageProxy, instance=True),
        identity=create_autospec(IdentityProxy, instance=True),
        image=create_autospec(ImageProxy, instance=True),
        session=Mock(), config=Mock(region_name='RegionOne'),
    )
    value.compute.hypervisors.return_value = []
    value.config.get_interface.return_value = 'internal'
    value.volume = value.block_storage
    monkeypatch.setattr(connection, 'get_openstack_connection', lambda: value)
    monkeypatch.setattr(functions, 'get_openstack_connection', lambda: value)
    return value


def test_force_delete_uses_delete_server_force_flag(conn):
    server = Server(id='server-a', name='vm', project_id='project-a')
    conn.compute.servers.return_value = [server]
    result = compute.set_instance('vm', 'delete', force=True)
    assert result['success'], result
    conn.compute.delete_server.assert_called_once_with(server, force=True)


def test_regular_delete_does_not_force(conn):
    server = Server(id='server-a', name='vm', project_id='project-a')
    conn.compute.servers.return_value = [server]
    assert compute.set_instance('vm', 'delete')['success']
    conn.compute.delete_server.assert_called_once_with(server)


def test_compute_agent_show_by_id_uses_service_listing(conn):
    service = Service(id='svc-1', binary='nova-compute', host='node1', availability_zone='nova',
                      status='enabled', state='up')
    conn.compute.services.return_value = [service]
    result = functions.set_compute_agents('show', agent_id='svc-1')
    assert result['success'], result
    assert result['agent_details']['host'] == 'node1'
    assert result['agent_details']['zone'] == 'nova'


def test_compute_agent_list_and_host_show_read_sdk_zone_field(conn):
    service = Service(id='svc-1', binary='nova-compute', host='node1',
                      availability_zone='az1', status='enabled', state='up')
    conn.compute.services.return_value = [service]
    listed = functions.set_compute_agents('list')
    assert listed['success'], listed
    assert listed['compute_services'][0]['zone'] == 'az1'
    by_host = functions.set_compute_agents('show', host='node1')
    assert by_host['success'], by_host
    assert by_host['agents_on_host'][0]['zone'] == 'az1'


def test_compute_agent_show_unknown_id_is_explicit_error(conn):
    conn.compute.services.return_value = []
    result = functions.set_compute_agents('show', agent_id='missing')
    assert result['success'] is False
    assert 'not found' in result['message']


class _OldStorageApi:
    """openstacksdk < 4.14 restore_backup signature."""

    def __init__(self):
        self.calls = []

    def restore_backup(self, backup, volume_id=None, name=None):
        self.calls.append({'volume_id': volume_id, 'name': name})
        return Backup(id='backup-a')


class _NewStorageApi:
    """openstacksdk >= 4.14 restore_backup signature."""

    def __init__(self):
        self.calls = []

    def restore_backup(self, backup, volume=None, name=None):
        self.calls.append({'volume': volume, 'name': name})
        return Backup(id='backup-a')


@pytest.mark.parametrize('api_class, key', [(_OldStorageApi, 'volume_id'),
                                            (_NewStorageApi, 'volume')])
def test_restore_backup_adapts_to_sdk_signature(api_class, key):
    api = api_class()
    storage._restore_backup(api, Backup(id='backup-a'), 'volume-a', 'restored')
    assert api.calls == [{key: 'volume-a', 'name': 'restored'}]


def test_restore_backup_with_installed_sdk_proxy(conn):
    backup = Backup(id='backup-a', name='backup')
    api = conn.block_storage
    api.find_backup.return_value = backup
    api.restore_backup.return_value = backup
    result = storage.set_volume_backups('restore', 'backup', volume_id='volume-a',
                                        volume_name='restored')
    assert result['success'], result
    key = ('volume' if 'volume' in inspect.signature(StorageProxy.restore_backup).parameters
           else 'volume_id')
    api.restore_backup.assert_called_once_with(backup, **{key: 'volume-a'}, name='restored')
