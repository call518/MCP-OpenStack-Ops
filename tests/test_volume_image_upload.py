"""set_volume: create from a snapshot and copy a volume into a Glance image.

A boot-from-volume server snapshot is a Glance record without data that
points at a Cinder snapshot. Turning it into a normal image takes a volume
from the snapshot and Cinder's os-volume_upload_image action, which copies the
data to Glance server-side.
"""

import importlib
import json
from types import SimpleNamespace
from unittest.mock import create_autospec

import pytest
from openstack.block_storage.v3._proxy import Proxy as StorageProxy
from openstack.block_storage.v3.snapshot import Snapshot
from openstack.block_storage.v3.volume import Volume
from openstack.image.v2._proxy import Proxy as ImageProxy
from openstack.image.v2.image import Image

from mcp_openstack_ops import connection
from mcp_openstack_ops.services import storage
import mcp_openstack_ops.mcp_main  # noqa: F401  Register tools first.


@pytest.fixture
def conn(monkeypatch):
    value = SimpleNamespace(
        current_project_id='project-a',
        block_storage=create_autospec(StorageProxy, instance=True),
        image=create_autospec(ImageProxy, instance=True),
    )
    value.volume = value.block_storage
    monkeypatch.setattr(connection, 'get_openstack_connection', lambda: value)
    monkeypatch.setattr(connection, 'get_current_project_id', lambda: 'project-a')
    return value


def _volume(**overrides):
    attrs = dict(id='vol-1', name='base-src', status='available', size=20,
                 project_id='project-a', attachments=[])
    attrs.update(overrides)
    return Volume.existing(**attrs)


def _snapshot(**overrides):
    attrs = dict(id='snap-1', name='snap-web', size=20, status='available',
                 project_id='project-a')
    attrs.update(overrides)
    return Snapshot.existing(**attrs)


def test_create_from_snapshot_uses_snapshot_id_and_size(conn):
    conn.volume.snapshots.return_value = [_snapshot()]
    conn.volume.create_volume.return_value = _volume(status='creating')

    result = storage.set_volume('base-src', 'create', size=1, source_snapshot='snap-web')

    assert result['success'] is True, result
    kwargs = conn.volume.create_volume.call_args.kwargs
    assert kwargs['snapshot_id'] == 'snap-1'
    assert 'size' not in kwargs  # Cinder takes the snapshot's 20 GB

    storage.set_volume('bigger', 'create', size=30, source_snapshot='snap-1')
    assert conn.volume.create_volume.call_args.kwargs['size'] == 30


def test_create_from_snapshot_refuses_other_projects_snapshot(conn):
    conn.volume.snapshots.return_value = [_snapshot(project_id='project-b')]

    result = storage.set_volume('base-src', 'create', source_snapshot='snap-web')

    assert result['success'] is False
    conn.volume.create_volume.assert_not_called()


def test_upload_to_image_reports_acceptance_and_current_states(conn):
    volume = _volume()
    conn.volume.volumes.return_value = [volume]
    conn.volume.upload_volume_to_image.return_value = {
        'id': 'vol-1', 'image_id': 'img-1', 'image_name': 'img-web',
        'disk_format': 'qcow2', 'container_format': 'bare',
        'visibility': 'private', 'protected': False, 'status': 'uploading',
    }
    conn.image.get_image.return_value = Image.existing(id='img-1', status='queued')
    conn.volume.get_volume.return_value = _volume(status='uploading')

    result = storage.set_volume(
        'base-src', 'upload_to_image', image_name='img-web', disk_format='qcow2')

    assert result['success'] is True and result['accepted'] is True, result
    assert 'accepted' in result['message'] and 'active' in result['message']
    assert result['image']['id'] == 'img-1'
    assert result['image']['status'] == 'queued'
    assert result['volume']['status'] == 'uploading'
    args, kwargs = conn.volume.upload_volume_to_image.call_args
    assert args == (volume, 'img-web')
    assert kwargs == {'force': False, 'disk_format': 'qcow2'}


def test_upload_to_image_reports_failed_status_read_as_null(conn):
    conn.volume.volumes.return_value = [_volume()]
    conn.volume.upload_volume_to_image.return_value = {'image_id': 'img-1'}
    conn.image.get_image.side_effect = RuntimeError('glance 503')
    conn.volume.get_volume.return_value = _volume(status='uploading')

    result = storage.set_volume('base-src', 'upload_to_image', image_name='img-web')

    assert result['image']['status'] is None
    assert 'glance 503' in result['image']['status_error']


@pytest.mark.parametrize('volume, kwargs, reason', [
    (_volume(status='in-use'), {'image_name': 'img'}, 'in-use'),
    (_volume(status='error'), {'image_name': 'img', 'force': True}, 'error'),
    (_volume(project_id='project-b'), {'image_name': 'img'}, 'not found'),
    (_volume(), {}, 'image_name is required'),
])
def test_upload_to_image_refusals_call_nothing(conn, volume, kwargs, reason):
    conn.volume.volumes.return_value = [volume]

    result = storage.set_volume('base-src', 'upload_to_image', **kwargs)

    assert result['success'] is False
    assert reason in result['message']
    conn.volume.upload_volume_to_image.assert_not_called()


def test_upload_to_image_allows_in_use_volume_with_force(conn):
    conn.volume.volumes.return_value = [_volume(status='in-use')]
    conn.volume.upload_volume_to_image.return_value = {'image_id': 'img-1'}
    conn.image.get_image.return_value = Image.existing(id='img-1', status='queued')
    conn.volume.get_volume.return_value = _volume(status='in-use')

    result = storage.set_volume(
        'base-src', 'upload_to_image', image_name='img', force=True)

    assert result['success'] is True, result
    assert conn.volume.upload_volume_to_image.call_args.kwargs['force'] is True


def test_upload_to_image_explains_cinder_force_upload_refusal(conn):
    # Cinder refuses force uploads unless enable_force_upload=True (default False).
    conn.volume.volumes.return_value = [_volume(status='in-use')]
    conn.volume.upload_volume_to_image.side_effect = RuntimeError(
        'BadRequestException: 400: Invalid volume: Volume vol-1 status must be available')

    result = storage.set_volume(
        'base-src', 'upload_to_image', image_name='img', force=True)

    assert result['success'] is False
    assert 'enable_force_upload' in result['message']
    assert 'set_instance action="snapshot"' in result['message']
    assert 'must be available' in result['error']


def test_upload_to_image_other_errors_are_not_rewritten(conn):
    conn.volume.volumes.return_value = [_volume()]
    conn.volume.upload_volume_to_image.side_effect = RuntimeError('glance quota exceeded')

    result = storage.set_volume('base-src', 'upload_to_image', image_name='img')

    assert result['success'] is False
    assert 'glance quota exceeded' in result['error']
    assert 'enable_force_upload' not in json.dumps(result)


@pytest.mark.asyncio
@pytest.mark.parametrize('force, expected', [(True, {'force': True}), (False, {})])
async def test_snapshot_tool_passes_force_for_create(monkeypatch, force, expected):
    monkeypatch.setenv('ALLOW_MODIFY_OPERATIONS', 'true')
    module = importlib.import_module('mcp_openstack_ops.tools.set_snapshot')
    calls = []

    def fake(snapshot_name, action, **kwargs):
        calls.append((snapshot_name, action, kwargs))
        return {'success': True, 'message': 'accepted'}

    monkeypatch.setattr(module, '_set_snapshot', fake)
    monkeypatch.setattr(module, '_get_resource_status_by_name', lambda *a: 'creating')
    monkeypatch.setattr('time.sleep', lambda *_: None)
    handler = getattr(module.set_snapshot, 'fn', module.set_snapshot)

    await handler(action='create', snapshot_names='snap-a', volume_id='vol-1',
                  force=force)

    assert calls == [('snap-a', 'create', {'volume_id': 'vol-1', **expected})]


def test_snapshot_service_sends_force_to_cinder(conn):
    conn.volume.create_snapshot.return_value = _snapshot(status='creating')

    storage.set_snapshot('snap-a', 'create', volume_id='vol-1', force=True)

    assert conn.volume.create_snapshot.call_args.kwargs['force'] is True


@pytest.mark.asyncio
async def test_tool_passes_upload_options_and_marks_result_async(conn, monkeypatch):
    monkeypatch.setenv('ALLOW_MODIFY_OPERATIONS', 'true')
    module = importlib.import_module('mcp_openstack_ops.tools.set_volume')
    calls = []

    def fake(volume_name, action, **kwargs):
        calls.append((volume_name, action, kwargs))
        return {'success': True, 'message': 'accepted'}

    monkeypatch.setattr(module, '_set_volume', fake)
    handler = getattr(module.set_volume, 'fn', module.set_volume)

    result = json.loads(await handler(
        volume_names='base-src', action='upload_to_image', image_name='img-web',
        disk_format='qcow2', visibility='private', protected=False))
    refused = await handler(volume_names='a,b', action='upload_to_image',
                            image_name='img-web')
    await handler(volume_names='base-src', action='create', source_snapshot='snap-web')

    assert result['operation_type'] == 'asynchronous'
    assert result['verification_needed'] is True
    name, action, kwargs = calls[0]
    assert (name, action) == ('base-src', 'upload_to_image')
    assert {k: kwargs[k] for k in ('image_name', 'disk_format', 'visibility',
                                   'protected')} == {
        'image_name': 'img-web', 'disk_format': 'qcow2',
        'visibility': 'private', 'protected': False}
    assert 'container_format' not in kwargs
    assert 'exactly one volume' in refused
    assert calls[1][2]['source_snapshot'] == 'snap-web'
    assert len(calls) == 2
