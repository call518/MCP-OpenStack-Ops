"""Read tools must report retrieval failures instead of placeholder data."""

import importlib
import json

import pytest

from mcp_openstack_ops import connection
import mcp_openstack_ops.mcp_main  # Register tools before importing tool modules.

PLACEHOLDERS = ('192.168.1.100', 'fip-1', 'default-sg', 'type-1', 'user-1',
                'error-stack', 'pool-error')


def _tool_handler(module, name):
    tool = getattr(module, name)
    return getattr(tool, 'fn', tool)


@pytest.mark.asyncio
@pytest.mark.parametrize('tool', [
    'get_floating_ips', 'get_floating_ip_pools', 'get_security_groups',
    'get_volume_types', 'get_role_assignments', 'get_heat_stacks',
    'get_image_detail_list', 'get_server_groups', 'get_instance_details',
])
async def test_read_tool_reports_connection_failure(monkeypatch, tool):
    def unreachable():
        raise ConnectionError('identity endpoint unreachable')

    monkeypatch.setattr(connection, 'get_openstack_connection', unreachable)
    module = importlib.import_module(f'mcp_openstack_ops.tools.{tool}')
    output = await _tool_handler(module, tool)()

    assert output.startswith('Error:'), output
    assert 'identity endpoint unreachable' in output
    assert not any(marker in output for marker in PLACEHOLDERS), output
    with pytest.raises(ValueError):
        json.loads(output)
