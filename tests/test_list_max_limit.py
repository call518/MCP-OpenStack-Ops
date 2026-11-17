"""LIST_MAX_LIMIT caps how many items one list-tool call returns.

It replaces a hard-coded 200 in the instance listings and the load balancer
listing; the model reads further pages with offset.
"""

from types import SimpleNamespace
from unittest.mock import create_autospec

import pytest
from openstack.compute.v2._proxy import Proxy as ComputeProxy
from openstack.compute.v2.server import Server

from mcp_openstack_ops import connection, settings
from mcp_openstack_ops.services import compute
from mcp_openstack_ops.services.load_balancer import core as lb_core


@pytest.fixture
def servers(monkeypatch):
    conn = SimpleNamespace(current_project_id='project-a',
                           compute=create_autospec(ComputeProxy, instance=True))
    conn.compute.servers.return_value = [
        Server.existing(id=f's{i}', name=f'vm-{i}', project_id='project-a',
                        status='ACTIVE')
        for i in range(250)]
    monkeypatch.setattr(connection, 'get_openstack_connection', lambda: conn)
    monkeypatch.setattr(connection, 'get_current_project_id', lambda: 'project-a')
    return conn


@pytest.mark.parametrize('env,expected', [(None, 100), ('', 100), ('150', 150),
                                          ('20', 20)])
def test_instance_listing_page_follows_setting(servers, monkeypatch, env, expected):
    if env is None:
        monkeypatch.delenv('LIST_MAX_LIMIT', raising=False)
    else:
        monkeypatch.setenv('LIST_MAX_LIMIT', env)

    result = compute.get_instance_details(limit=500, enrich_images=False)

    assert result['count'] == expected
    assert result['limit'] == expected
    assert result['has_next'] is True


def test_invalid_listing_setting_is_reported(servers, monkeypatch):
    monkeypatch.setenv('LIST_MAX_LIMIT', 'abc')

    result = compute.get_instance_details(limit=10, enrich_images=False)

    assert result['success'] is False
    assert 'LIST_MAX_LIMIT must be a positive integer' in result['error']


def test_search_page_follows_setting(servers, monkeypatch):
    monkeypatch.setenv('LIST_MAX_LIMIT', '30')

    page = compute.search_instances('vm', ['name'], limit=500,
                                    with_pagination=True)

    assert len(page['instances']) == 30
    assert page['pagination'] == {'limit': 30, 'offset': 0, 'has_more': True}


def test_invalid_search_setting_names_the_variable(servers, monkeypatch):
    # search_instances hides other errors, so the setting is read first.
    monkeypatch.setenv('LIST_MAX_LIMIT', '0')

    with pytest.raises(ValueError, match='LIST_MAX_LIMIT'):
        compute.search_instances('vm', ['name'])


def test_invalid_load_balancer_setting_names_the_variable(monkeypatch):
    monkeypatch.setenv('LIST_MAX_LIMIT', '-1')

    with pytest.raises(ValueError, match='LIST_MAX_LIMIT'):
        lb_core.get_load_balancer_list()


def test_defaults_are_one_hundred():
    assert settings.DEFAULT_LIST_MAX_LIMIT == 100
    assert settings.DEFAULT_INSTANCE_FILTER_MAX_MATCHES == 100
