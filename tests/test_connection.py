"""Connection configuration required by real project-scoped Heat endpoints."""

import logging
from types import SimpleNamespace
from unittest.mock import Mock

from mcp_openstack_ops import connection


def test_heat_endpoint_is_scoped_after_authentication(monkeypatch, caplog):
    for name, value in {
        'OS_PROJECT_NAME': 'test-project', 'OS_USERNAME': 'test-user',
        'OS_PASSWORD': 'test-only-password', 'OS_AUTH_HOST': 'cloud.example.test',
        'OS_AUTH_PORT': '5000', 'OS_AUTH_PROTOCOL': 'http',
        'OS_HEAT_STACK_PORT': '18004',
    }.items():
        monkeypatch.setenv(name, value)
    fake = Mock(current_project_id='project-a')
    fake.config = SimpleNamespace(config={})
    fake.identity.get_token.return_value = 'test-only-token'
    constructor = Mock(return_value=fake)
    monkeypatch.setattr(connection.connection, 'Connection', constructor)
    monkeypatch.setattr(connection, 'load_dotenv', lambda: None)
    monkeypatch.setattr(connection, '_connection_cache', None)
    with caplog.at_level(logging.INFO):
        assert connection.get_openstack_connection() is fake
    assert constructor.call_args.kwargs['orchestration_api_version'] == '1'
    assert fake.config.config['orchestration_endpoint_override'] == (
        'http://cloud.example.test:18004/v1/project-a'
    )
    assert 'test-only-token' not in caplog.text
    assert 'test-only-password' not in caplog.text
