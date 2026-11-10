"""Root disk choices for set_instance create: local disk, new volume, existing volume.

Proxies are ``create_autospec`` of the real openstacksdk proxies, and the
create arguments are checked against the real ``Server`` resource.
"""

import importlib
from types import SimpleNamespace
from unittest.mock import Mock, create_autospec

import pytest
from openstack.block_storage.v3._proxy import Proxy as BlockStorageProxy
from openstack.block_storage.v3.volume import Volume
from openstack.compute.v2._proxy import Proxy as ComputeProxy
from openstack.compute.v2.flavor import Flavor
from openstack.compute.v2.server import Server
from openstack.image.v2._proxy import Proxy as ImageProxy
from openstack.image.v2.image import Image
from openstack.network.v2._proxy import Proxy as NetworkProxy
from openstack.network.v2.network import Network

from mcp_openstack_ops import connection
import mcp_openstack_ops.mcp_main  # noqa: F401  Register tools first.
from mcp_openstack_ops.services import compute


@pytest.fixture
def conn(monkeypatch):
    value = SimpleNamespace(
        compute=create_autospec(ComputeProxy, instance=True),
        network=create_autospec(NetworkProxy, instance=True),
        image=create_autospec(ImageProxy, instance=True),
        volume=create_autospec(BlockStorageProxy, instance=True),
    )
    value.compute.flavors.return_value = [
        Flavor.existing(id='flavor-1', name='m1.small', is_public=True)]
    value.image.images.return_value = [
        Image.existing(id='img-1', name='rocky-9', visibility='public')]
    value.network.networks.return_value = [
        Network.existing(id='net-1', name='private-net', project_id='project-a')]
    value.volume.volumes.return_value = [
        Volume.existing(id='vol-1', name='root-vol', status='available',
                        is_bootable=True, project_id='project-a'),
        Volume.existing(id='vol-2', name='busy-vol', status='in-use',
                        is_bootable=True, project_id='project-a'),
        Volume.existing(id='vol-3', name='data-vol', status='available',
                        is_bootable=False, project_id='project-a'),
    ]
    value.compute.create_server.return_value = Server.existing(
        id='server-1', name='vm-new', status='BUILD')
    monkeypatch.setattr(connection, 'get_openstack_connection', lambda: value)
    monkeypatch.setattr(connection, 'get_current_project_id', lambda: 'project-a')
    return value


def _create(**kwargs):
    return compute.set_instance('vm-new', 'create', flavor='m1.small',
                                networks=['private-net'], **kwargs)


def _sent(conn):
    kwargs = conn.compute.create_server.call_args.kwargs
    # Every key must be a real Server attribute, as create_server(**attrs) needs.
    assert all(hasattr(Server, key) for key in kwargs), kwargs
    return kwargs


def test_default_create_boots_the_image_on_the_flavor_disk(conn):
    result = _create(image='rocky-9')

    assert result['success'] is True, result
    sent = _sent(conn)
    assert sent['image_id'] == 'img-1'
    assert 'block_device_mapping' not in sent
    assert result['instance']['boot_source'] == 'image'


def test_boot_from_volume_creates_a_root_volume_from_the_image(conn):
    result = _create(image='rocky-9', boot_from_volume=True, volume_size=10,
                     volume_type='ssd', delete_on_termination=False)

    assert result['success'] is True, result
    sent = _sent(conn)
    assert 'image_id' not in sent
    assert sent['block_device_mapping'] == [{
        'boot_index': 0, 'uuid': 'img-1', 'source_type': 'image',
        'destination_type': 'volume', 'volume_size': 10,
        'delete_on_termination': False, 'volume_type': 'ssd',
    }]
    server = Server.new(**sent)
    assert server.block_device_mapping == sent['block_device_mapping']
    assert server.image_id is None
    assert result['instance']['boot_source'] == 'new_volume'
    assert result['instance']['image'] == {'id': 'img-1', 'name': 'rocky-9'}


def test_boot_volume_boots_an_existing_volume_without_an_image(conn):
    result = _create(boot_volume='root-vol')

    assert result['success'] is True, result
    sent = _sent(conn)
    assert 'image_id' not in sent
    assert sent['block_device_mapping'] == [{
        'boot_index': 0, 'uuid': 'vol-1', 'source_type': 'volume',
        'destination_type': 'volume', 'delete_on_termination': True,
    }]
    assert result['instance']['image'] is None
    assert result['instance']['boot_source'] == 'volume'


@pytest.mark.parametrize(('volume', 'message'), [
    ('busy-vol', 'must be available'),
    ('data-vol', 'is not bootable'),
    ('missing-vol', 'not found'),
])
def test_unusable_boot_volume_is_refused(conn, volume, message):
    result = _create(boot_volume=volume)

    assert result['success'] is False
    assert message in result['message']
    conn.compute.create_server.assert_not_called()


@pytest.mark.parametrize(('options', 'message'), [
    ({'image': 'rocky-9', 'boot_from_volume': True}, 'volume_size'),
    ({'image': 'rocky-9', 'boot_from_volume': True, 'volume_size': 0},
     'volume_size'),
    ({'image': 'rocky-9', 'volume_size': 10}, 'only when boot_from_volume'),
    ({'image': 'rocky-9', 'volume_type': 'ssd'}, 'only when boot_from_volume'),
    ({'image': 'rocky-9', 'boot_volume': 'root-vol'}, 'not both'),
    ({'boot_from_volume': True, 'volume_size': 10, 'boot_volume': 'root-vol'},
     'not both'),
])
def test_conflicting_root_disk_options_are_refused(conn, options, message):
    result = _create(**options)

    assert result['success'] is False
    assert message in result['message']
    conn.compute.create_server.assert_not_called()


def _tool(monkeypatch):
    module = importlib.import_module('mcp_openstack_ops.tools.set_instance')
    service = Mock(return_value={'success': True, 'message': 'started'})
    monkeypatch.setattr(module, '_set_instance', service)
    monkeypatch.setattr(module, '_get_instance_by_name', Mock(return_value=None))
    monkeypatch.setattr('time.sleep', lambda _: None)
    tool = module.set_instance
    return getattr(tool, 'fn', tool), service


@pytest.mark.asyncio
async def test_tool_forwards_boot_from_volume_to_every_instance(monkeypatch):
    handler, service = _tool(monkeypatch)

    await handler(instance_names='vm-1,vm-2,vm-3', action='create',
                  flavor='m1.small', image='rocky-9', networks='private-net',
                  boot_from_volume=True, volume_size=10, volume_type='ssd')

    assert [call.args[0] for call in service.call_args_list] == [
        'vm-1', 'vm-2', 'vm-3']
    for call in service.call_args_list:
        assert call.kwargs['boot_from_volume'] is True
        assert call.kwargs['volume_size'] == 10
        assert call.kwargs['volume_type'] == 'ssd'
        assert call.kwargs['delete_on_termination'] is True


@pytest.mark.asyncio
async def test_tool_refuses_one_boot_volume_for_several_instances(monkeypatch):
    handler, service = _tool(monkeypatch)

    result = await handler(instance_names='vm-1,vm-2', action='create',
                           flavor='m1.small', boot_volume='root-vol')

    assert result.startswith('Error: boot_volume')
    service.assert_not_called()
