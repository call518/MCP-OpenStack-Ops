"""services.core.get_service_status falls back to OS_AUTH_* for the identity endpoint.

An `import os` inside the function once made `os` a local name, so the
fallback raised UnboundLocalError whenever the endpoint lookup failed.
"""

from types import SimpleNamespace
from unittest.mock import Mock

from mcp_openstack_ops.services import core


def test_identity_endpoint_falls_back_to_configured_host(monkeypatch):
    monkeypatch.setenv('OS_AUTH_HOST', 'keystone.example')
    monkeypatch.setenv('OS_AUTH_PORT', '5000')
    conn = Mock()
    conn.session.get_endpoint.side_effect = RuntimeError('no catalog entry')
    conn.identity.projects.return_value = [SimpleNamespace(is_enabled=True)]
    conn.identity.users.return_value = []
    conn.identity.roles.return_value = []
    monkeypatch.setattr(core, 'get_openstack_connection', lambda: conn)

    result = core.get_service_status('identity')

    assert result['success'] is True, result
    status = result['service_status']
    assert 'error' not in status
    assert status['endpoint'].endswith('://keystone.example:5000')
    assert status['details']['projects'] == 1
