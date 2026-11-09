"""Check actual FastMCP registration and runtime write guards without cloud IO."""

import os
from pathlib import Path
import subprocess
import sys

import pytest


@pytest.mark.parametrize('enabled', [False, True])
def test_tool_registration_and_runtime_write_guards(enabled):
    script = '''
import asyncio
import importlib
import inspect
import json
import os
from unittest.mock import Mock

from mcp_openstack_ops.mcp_main import mcp

async def verify():
    tools = {tool.name: tool for tool in await mcp.list_tools()}
    read_tools = [tool for tool in tools.values()
                  if tool.name.startswith(('get_', 'search_'))]
    assert len(read_tools) == 54
    for tool in read_tools:
        assert tool.description.strip(), tool.name
        for parameter, schema in tool.parameters.get('properties', {}).items():
            assert schema.get('description', '').strip(), f'{tool.name}.{parameter}'
    reads = {
        'get_volume_transfers', 'get_volume_backups', 'get_volume_groups',
        'get_volume_qos', 'get_domains', 'get_identity_groups',
        'get_image_members', 'get_heat_stack_details',
        'get_network_qos_policies', 'get_gnocchi_resources',
        'get_gnocchi_metrics', 'get_gnocchi_measures', 'get_gnocchi_service_info',
    }
    writes = {
        'set_alarms', 'set_routers', 'set_security_groups', 'set_users',
        'set_volume_types', 'set_domains', 'set_identity_groups',
        'set_volume_backups', 'set_volume_groups', 'set_volume_qos',
        'set_network_qos_policies', 'set_network_agents',
    }
    assert reads <= tools.keys()
    # Allocation tools and measured telemetry tools must point to each other.
    for name in ('get_resource_monitoring', 'get_usage_statistics'):
        assert 'get_gnocchi_measures' in tools[name].description, name
    assert 'get_resource_monitoring' in tools['get_gnocchi_measures'].description
    enabled = os.environ['ALLOW_MODIFY_OPERATIONS'] == 'true'
    assert (writes <= tools.keys()) if enabled else not (writes & tools.keys())
    if enabled:
        assert 'metric' in tools['set_alarms'].parameters['properties']
        alarm_metric = tools['set_alarms'].parameters['properties']['metric']
        assert 'rate:mean' in alarm_metric['description']
        assert 'volume_types' in tools['set_volume_groups'].parameters['properties']
        expected_actions = {
            'set_instance': {'delete', 'resize', 'snapshot', 'rebuild'},
            'set_flavor': {'set_extra_specs'},
            'set_project': {'update', 'show', 'list'},
            'set_keypair': {'import', 'show'},
            'set_network_ports': {'show'},
            'set_subnets': {'show'},
        }
        for name, actions in expected_actions.items():
            description = tools[name].parameters['properties']['action']['description']
            assert all(action in description for action in actions), name
    os.environ['ALLOW_MODIFY_OPERATIONS'] = 'false'
    cases = [
        ('set_alarms', {'action': 'create', 'alarm_name': 'a'}),
        ('set_routers', {'action': 'create', 'router_name': 'a'}),
        ('set_security_groups', {'action': 'delete', 'group_name': 'a'}),
        ('set_users', {'action': 'create', 'user_name': 'a'}),
        ('set_volume_types', {'action': 'delete', 'type_name': 'a'}),
        ('set_domains', {'action': 'delete', 'domain_name': 'a'}),
        ('set_identity_groups', {'action': 'update', 'group_name': 'a'}),
        ('set_volume_backups', {'action': 'create', 'backup_name': 'a'}),
        ('set_volume_groups', {'action': 'delete', 'group_name': 'a'}),
        ('set_volume_qos', {'action': 'set', 'qos_name': 'a'}),
        ('set_network_qos_policies', {'action': 'delete', 'policy_name': 'a'}),
        ('set_network_agents', {'action': 'disable', 'agent_id': 'a'}),
    ]
    for name, kwargs in cases:
        module = importlib.import_module('mcp_openstack_ops.tools.' + name)
        target_name = '_' + name
        target = Mock(side_effect=AssertionError('must not reach cloud'))
        if hasattr(module, target_name):
            setattr(module, target_name, target)
        handler = getattr(module, name)
        if not inspect.iscoroutinefunction(handler):
            handler = handler.fn
        result = json.loads(await handler(**kwargs))
        assert result['success'] is False, name
        assert result['error'] == 'MODIFY_OPERATIONS_DISABLED', name
        target.assert_not_called()

asyncio.run(verify())
'''
    result = subprocess.run(
        [sys.executable, '-c', script],
        cwd=Path(__file__).resolve().parents[1],
        env={**os.environ, 'ALLOW_MODIFY_OPERATIONS': str(enabled).lower()},
        capture_output=True, text=True, timeout=60,
    )
    assert result.returncode == 0, result.stderr
