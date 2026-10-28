"""Resolve instance image identity without guessing from image listings."""

from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from mcp_openstack_ops import connection
from mcp_openstack_ops.services import compute


@pytest.fixture
def conn(monkeypatch):
    conn = Mock()
    conn.image.get_image.return_value = SimpleNamespace(name='ubuntu-24-04')
    conn.block_storage.get_volume.return_value = SimpleNamespace(
        project_id='project-a', is_bootable=True,
        volume_image_metadata={'image_id': 'image-a', 'image_name': 'original-name'},
    )
    monkeypatch.setattr(connection, 'get_openstack_connection', lambda: conn)
    monkeypatch.setattr(connection, 'get_current_project_id', lambda: 'project-a')
    return conn


def volume_server(**kwargs):
    return SimpleNamespace(
        image={}, attached_volumes=[{'id': 'volume-a'}], **kwargs
    )


@pytest.mark.parametrize('reference', [
    {'id': 'image-a'}, SimpleNamespace(id='image-a'),
])
def test_image_backed_server_does_not_query_volumes(conn, reference):
    assert compute._get_server_image(conn, SimpleNamespace(image=reference)) == {
        'id': 'image-a', 'name': 'ubuntu-24-04',
    }
    conn.block_storage.get_volume.assert_not_called()


def test_glance_failure_preserves_nova_image_id(conn):
    conn.image.get_image.side_effect = RuntimeError('not accessible')
    server = SimpleNamespace(image={'id': 'image-a'})
    assert compute._get_server_image(conn, server) == {
        'id': 'image-a', 'name': 'unknown',
    }


def test_volume_backed_server_uses_image_metadata(conn):
    assert compute._get_server_image(conn, volume_server()) == {
        'id': 'image-a', 'name': 'ubuntu-24-04',
    }
    conn.block_storage.get_volume.assert_called_once_with('volume-a')


def test_deleted_image_retains_boot_volume_metadata(conn):
    conn.image.get_image.side_effect = RuntimeError('image deleted')
    assert compute._get_server_image(conn, volume_server()) == {
        'id': 'image-a', 'name': 'original-name',
    }


@pytest.mark.parametrize('attribute,value', [
    ('is_bootable', False),
    ('is_bootable', 'false'),
    ('volume_image_metadata', {}),
    ('project_id', 'another-project'),
])
def test_unavailable_or_foreign_boot_image_stays_unknown(conn, attribute, value):
    setattr(conn.block_storage.get_volume.return_value, attribute, value)
    assert compute._get_server_image(conn, volume_server()) == {
        'id': 'unknown', 'name': 'unknown',
    }
    conn.image.get_image.assert_not_called()


def test_ambiguous_bootable_volumes_are_not_guessed(conn):
    server = SimpleNamespace(image={}, attached_volumes=[{'id': 'a'}, {'id': 'b'}])
    assert compute._get_server_image(conn, server)['id'] == 'unknown'


def test_explicit_boot_index_selects_root_volume(conn):
    server = SimpleNamespace(image={}, attached_volumes=[
        {'id': 'a', 'boot_index': 1}, {'id': 'b', 'boot_index': 0},
    ])
    assert compute._get_server_image(conn, server)['id'] == 'image-a'
    conn.block_storage.get_volume.assert_called_once_with('b')


def test_volume_lookup_failure_does_not_fail_instance_details(conn):
    conn.block_storage.get_volume.side_effect = RuntimeError('not accessible')
    server = volume_server(
        id='server-a', name='vm', project_id='project-a', status='ACTIVE'
    )
    conn.compute.servers.return_value = [server]
    result = compute.get_instance_by_name('vm')
    assert result['id'] == 'server-a'
    assert result['image'] == {'id': 'unknown', 'name': 'unknown'}


def test_name_and_status_queries_share_image_resolution(conn):
    server = volume_server(
        id='server-a', name='vm', project_id='project-a', status='ACTIVE'
    )
    conn.compute.servers.return_value = [server]
    expected = {'id': 'image-a', 'name': 'ubuntu-24-04'}
    assert compute.get_instance_by_name('vm')['image'] == expected
    assert compute.get_instances_by_status('ACTIVE')[0]['image'] == expected
