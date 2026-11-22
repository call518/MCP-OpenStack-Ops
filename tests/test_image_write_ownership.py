"""Glance writes act only on images owned by the current project.

Public, shared and community images of other projects stay readable, but
update, delete, metadata set and visibility set must not touch them.
Updates must also keep the image's other custom properties.
"""

from types import SimpleNamespace
from unittest.mock import create_autospec

import pytest
from openstack.image.v2._proxy import Proxy as ImageProxy
from openstack.image.v2.image import Image

from mcp_openstack_ops import connection
from mcp_openstack_ops.services import image as image_service


def _image(image_id, owner, visibility='private', name='img'):
    return Image.existing(id=image_id, name=name, owner=owner,
                          visibility=visibility, is_protected=False,
                          status='active')


@pytest.fixture
def conn(monkeypatch):
    value = SimpleNamespace(
        current_project_id='project-a',
        image=create_autospec(ImageProxy, instance=True),
        patches=[],
    )

    def update_image(image, **attrs):
        # Build the resource as openstacksdk's Proxy._get_resource does and
        # record the JSON patch that commit() would send.
        if isinstance(image, Image):
            image._update(**attrs)
            res = image
        else:
            res = Image.new(id=image, **attrs)
        value.patches.append(
            res._prepare_request(prepend_key=False, patch=True).body)
        return res

    value.image.update_image.side_effect = update_image
    monkeypatch.setattr(connection, 'get_openstack_connection', lambda: value)
    return value


WRITES = [
    lambda: image_service.set_image('img', 'update', visibility='private'),
    lambda: image_service.set_image('img', 'delete'),
    lambda: image_service.set_image_metadata('set', 'img',
                                             properties={'os_type': 'linux'}),
    lambda: image_service.set_image_visibility('set', 'img',
                                               visibility='private'),
]


@pytest.mark.parametrize('write', WRITES)
def test_writes_reject_foreign_public_image(conn, write):
    conn.image.images.return_value = [_image('foreign', 'project-b', 'public')]

    result = write()

    assert result['success'] is False, result
    assert 'not owned by the current project' in result['error']
    conn.image.update_image.assert_not_called()
    conn.image.delete_image.assert_not_called()


@pytest.mark.parametrize('write', WRITES)
def test_writes_target_owned_image_over_foreign_namesake(conn, write):
    owned = _image('owned', 'project-a')
    conn.image.images.return_value = [_image('foreign', 'project-b', 'public'),
                                      owned]

    result = write()

    assert result['success'] is True, result
    calls = conn.image.update_image.call_args_list + \
        conn.image.delete_image.call_args_list
    assert len(calls) == 1
    target = calls[0].args[0]
    assert getattr(target, 'id', target) == 'owned'


@pytest.mark.parametrize('write', [
    lambda: image_service.set_image('img', 'update',
                                    properties={'new_key': 'v'}),
    lambda: image_service.set_image_metadata('set', 'img',
                                             properties={'new_key': 'v'}),
])
def test_property_update_keeps_other_properties(conn, write):
    owned = Image.existing(id='owned', name='img', owner='project-a',
                           visibility='private', status='queued',
                           old_key='keep')
    conn.image.images.return_value = [owned]

    result = write()

    assert result['success'] is True, result
    assert conn.patches == [[{'op': 'add', 'path': '/new_key', 'value': 'v'}]]


def test_ambiguous_owned_name_is_rejected(conn):
    conn.image.images.return_value = [_image('one', 'project-a'),
                                      _image('two', 'project-a')]

    result = image_service.set_image('img', 'delete')

    assert result['success'] is False
    assert 'ambiguous' in result['error']
    conn.image.delete_image.assert_not_called()


def test_show_still_reads_foreign_public_image(conn):
    foreign = _image('foreign', 'project-b', 'public')
    conn.image.images.return_value = [foreign]
    conn.image.get_image.return_value = foreign

    metadata = image_service.set_image_metadata('show', 'img')
    visibility = image_service.set_image_visibility('show', 'img')

    assert metadata['success'] is True, metadata
    assert visibility['success'] is True, visibility
    assert visibility['owner'] == 'project-b'


def test_create_reports_record_without_data(conn):
    conn.image.create_image.return_value = _image('new', 'project-a')

    result = image_service.set_image('img', 'create')

    assert result['success'] is True
    assert 'without data' in result['message']
