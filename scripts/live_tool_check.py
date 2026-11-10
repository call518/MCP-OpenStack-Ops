#!/usr/bin/env python3
"""Exercise every registered MCP tool against a real, disposable OpenStack cloud.

The script calls tools through a real MCP client: in process via FastMCP's
in-memory transport (default) or over Streamable HTTP with ``--url``. It
creates its own resources, all named with ``--prefix``, polls final states
through openstacksdk where an operation is asynchronous, and removes what it
created. It never prints credentials.

Use only a disposable test cloud and an administrator account: some steps
create and delete projects, domains, users, roles, flavors and networks.

    . admin-openrc.sh
    ALLOW_MODIFY_OPERATIONS=true uv run python scripts/live_tool_check.py \
        --i-understand-this-is-destructive \
        --image cirros --flavor m1.tiny --resize-flavor m1.small \
        --network demo-net --external-network public1 --output results.json

The default image, flavor, network and server names are those created by
Kolla-Ansible's init-runonce demo set-up; pass the names of your cloud's
resources otherwise. Keep result files out of the repository.

Each call is classified from the tool output:
  ok          the tool returned a successful result
  error       the tool returned an explicit error/unsuccessful result
  exception   schema validation, transport or unexpected server error
              (a ToolError raised by a tool is an explicit error)
Expected-error calls (negative tests) are marked ``expect="error"``; a
negative call passes when it returns an explicit error instead of a crash or
a misleading success. Final-state checks are recorded separately: an accepted
request is not reported as a completed operation.
"""

from __future__ import annotations

import argparse
import re
import asyncio
import json
import os
import sys
import time
import traceback
from datetime import date, timedelta
from typing import Any, Callable, Optional

RESULTS: list[dict[str, Any]] = []
CREATED_FIPS: list[str] = []
ABSENT_SERVICES: set[str] = set()


def classify(text: str) -> str:
    stripped = text.lstrip()
    if stripped.startswith('❌') or stripped.lower().startswith(('error', 'failed')):
        return 'error'
    try:
        # Some tools append a post-action status line after the JSON document.
        data, _ = json.JSONDecoder().raw_decode(stripped)
    except (ValueError, TypeError):
        lowered = stripped[:200].lower()
        if 'failed' in lowered or 'error:' in lowered or 'not found' in lowered:
            return 'error'
        return 'ok'
    if _is_partial(data):
        return 'partial'
    return 'error' if _has_error(data) else 'ok'


def classify_error_result(text: str) -> str:
    """Classify an MCP error result (``isError=true``).

    A ToolError raised by a tool is an explicit, intended error. Schema
    validation failures and unexpected exceptions are MCP-level failures.
    """
    lowered = text.lower()
    if ('validation error' in lowered or lowered.startswith('error calling tool')
            or 'unknown tool' in lowered):
        return 'exception'
    return 'error'


def _is_partial(data) -> bool:
    """A result that succeeded overall but reports failed sections."""
    if not isinstance(data, dict):
        return False
    candidates = [data] + [v for v in data.values() if isinstance(v, dict)]
    if any(c.get('partial') is True or c.get('failed_sections') for c in candidates):
        return True
    # e.g. {"quota_data": {"success": true, ... {"storage": {"success": false}}}}
    return any(c.get('success') is True and _has_error({k: v for k, v in c.items() if k != 'success'})
               for c in candidates)


def _has_error(data, depth: int = 0) -> bool:
    """Find explicit failures, including ones nested in result envelopes.

    Tools wrap service results (``{"result": {"success": false}}``) or return
    lists whose only entry carries an ``error`` key; both are failures.
    """
    if depth > 3:
        return False
    if isinstance(data, dict):
        if data.get('success') is False:
            return True
        if data.get('error') and data.get('success') is not True:
            return True
        return any(_has_error(value, depth + 1) for key, value in data.items()
                   if key in {'result', 'data', 'usage_data', 'quota_data', 'project_data',
                              'resource_monitoring'} or isinstance(value, dict))
    if isinstance(data, list) and data and all(isinstance(item, dict) for item in data):
        return all(item.get('error') for item in data)
    return False


# Tools that need an optional service. When the service is absent from the
# cloud, an explicit error (or a partial result) is the correct outcome; an
# MCP exception is still a failure.
OPTIONAL_SERVICE_PREFIXES = {
    'get_load_balancer': 'load-balancer', 'set_load_balancer': 'load-balancer',
    'get_volume': 'block-storage', 'set_volume': 'block-storage',
    'set_snapshot': 'block-storage', 'set_alarms': 'alarming',
    'get_network_qos_policies': 'qos', 'set_network_qos_policies': 'qos',
    'get_gnocchi': 'metric',
}
# Composite reads whose block-storage section fails without Cinder.
STORAGE_SECTION_TOOLS = {'get_quota', 'set_quota', 'get_resource_monitoring',
                         'get_usage_statistics', 'set_metrics'}


class Runner:
    def __init__(self, client, conn, args):
        self.client = client
        self.conn = conn
        self.args = args
        self.tools: set[str] = set()
        self.absent: set[str] = set()

    def required_service(self, tool: str) -> Optional[str]:
        for prefix, service in OPTIONAL_SERVICE_PREFIXES.items():
            if tool.startswith(prefix):
                return service
        if tool in STORAGE_SECTION_TOOLS:
            return 'block-storage'
        return None

    async def call(self, tool: str, params: Optional[dict] = None, *, expect: str = 'ok',
                   note: str = '', kind: str = 'read') -> str:
        params = params or {}
        start = time.monotonic()
        entry: dict[str, Any] = {'tool': tool, 'params': params, 'expect': expect,
                                 'kind': kind, 'note': note}
        if tool not in self.tools:
            entry.update(outcome='not_registered', output='', seconds=0)
            RESULTS.append(entry)
            print(f'[NOT REGISTERED] {tool}')
            return ''
        try:
            result = await self.client.call_tool(tool, params, raise_on_error=False)
            text = '\n'.join(getattr(c, 'text', '') for c in result.content)
            outcome = classify_error_result(text) if result.is_error else classify(text)
        except Exception as exc:  # transport or client error
            text = f'{type(exc).__name__}: {exc}'
            outcome = 'exception'
        entry.update(outcome=outcome, output=text[:1500], seconds=round(time.monotonic() - start, 2))
        service = self.required_service(tool)
        if service in self.absent:
            entry['requires_absent'] = service
        if expect == 'ok' and service in self.absent:
            # The service is not deployed: an explicit error (or a partial
            # result, or a success for an action that does not need it) is
            # right; an MCP exception is not.
            entry['service_absent'] = service
            entry['passed'] = outcome in ('error', 'partial', 'ok')
        else:
            entry['passed'] = (outcome == expect)
        RESULTS.append(entry)
        flag = 'PASS' if entry['passed'] else 'FAIL'
        print(f'[{flag}] {tool} {json.dumps(params)[:120]} -> {outcome} ({entry["seconds"]}s) '
              f'{text[:160]!r}')
        return text

    def check(self, name: str, fn: Callable[[], Any], timeout: int = 0, interval: int = 5) -> bool:
        """Record a final-state check performed with openstacksdk (polling up to timeout)."""
        deadline = time.monotonic() + timeout
        detail: Any = None
        while True:
            try:
                ok, detail = fn()
            except Exception as exc:
                ok, detail = False, f'{type(exc).__name__}: {exc}'
            if ok or time.monotonic() >= deadline:
                break
            time.sleep(interval)
        RESULTS.append({'tool': None, 'check': name, 'passed': bool(ok), 'detail': str(detail)[:500],
                        'polling_limit_s': timeout})
        print(f'  [{"STATE OK" if ok else "STATE FAIL"}] {name}: {str(detail)[:160]}')
        return bool(ok)

    # --- sdk helpers -------------------------------------------------------
    def server(self, name):
        return self.conn.compute.find_server(name, ignore_missing=True)

    def server_status(self, name, *statuses, task_none=True):
        def fn():
            srv = self.server(name)
            if srv is None:
                return 'DELETED' in statuses, 'missing'
            srv = self.conn.compute.get_server(srv.id)
            ok = srv.status in statuses and (not task_none or not srv.task_state)
            return ok, f'status={srv.status} task_state={srv.task_state}'
        return fn

    def gone(self, finder, name):
        def fn():
            res = finder(name, ignore_missing=True)
            return res is None, 'gone' if res is None else f'still present: {getattr(res, "status", "")}'
        return fn

    def has_service(self, service_type: str) -> bool:
        try:
            return bool(self.conn.endpoint_for(service_type))
        except Exception:
            return False


async def run(args) -> int:
    import openstack
    from fastmcp import Client

    conn = openstack.connect()  # from OS_* environment
    if args.url:
        client = Client(args.url)
    else:
        from mcp_openstack_ops.mcp_main import mcp
        client = Client(mcp)

    P = args.prefix
    async with client:
        listed = await client.list_tools()
        r = Runner(client, conn, args)
        r.tools = {t.name for t in listed}
        print(f'Registered tools discovered: {len(r.tools)}')
        for service in ('load-balancer', 'block-storage', 'alarming', 'metric'):
            if not r.has_service(service):
                r.absent.add(service)
        try:
            if not conn.network.find_extension('qos'):
                r.absent.add('qos')
        except Exception:
            r.absent.add('qos')
        print(f'Optional services absent: {sorted(r.absent) or "none"}')
        ABSENT_SERVICES.update(r.absent)
        modify = os.environ.get('ALLOW_MODIFY_OPERATIONS', 'false').lower() == 'true'

        # ---------------------------------------------------------------- reads
        for tool in sorted(r.tools):
            schema = next(t for t in listed if t.name == tool).inputSchema
            if tool.startswith(('get_', 'search_')) and not schema.get('required'):
                if tool == 'get_instance':
                    # Needs at least one filter; covered by explicit calls below.
                    await r.call(tool, {}, expect='error', note='requires a filter')
                    continue
                if tool == 'get_gnocchi_aggregates':
                    # Needs metric or operations; covered by explicit calls below.
                    await r.call(tool, {}, expect='error', note='requires metric or operations')
                    continue
                await r.call(tool, {})
        await r.call('get_instance', {'all_instances': True})
        await r.call('get_instance', {'names': args.existing_server})
        await r.call('get_instance', {'search_term': args.existing_server[:3]})
        await r.call('get_instance', {'status': 'ACTIVE'})
        await r.call('get_instance', {'ids': '00000000-0000-0000-0000-000000000000'},
                     note='unknown id', expect='ok')
        await r.call('get_instance_by_name', {'instance_name': args.existing_server})
        await r.call('get_gnocchi_aggregates', {'metric': 'cpu', 'aggregation': 'rate:mean',
                                                'reaggregation': 'mean'})
        existing = conn.compute.find_server(args.existing_server, ignore_missing=True)
        if existing:
            await r.call('get_gnocchi_measures', {'metric': 'cpu', 'resource_id': existing.id})
        await r.call('get_instance_by_name', {'instance_name': f'{P}-missing'}, expect='error')
        await r.call('get_instance_details', {'instance_names': args.existing_server})
        await r.call('get_instance_details', {'all_instances': True, 'limit': 5})
        await r.call('get_instances_by_status', {'status': 'ACTIVE'})
        await r.call('get_instances_by_status', {'status': 'NOT_A_STATUS'}, note='invalid status',
                     expect='error')
        await r.call('search_instances', {'search_term': args.existing_server[:3]})
        await r.call('search_instances', {'search_term': f'{P}-nothing'}, note='no match')
        await r.call('get_server_events', {'instance_name': args.existing_server,
                                           'include_event_details': True})
        await r.call('get_server_events', {'instance_name': f'{P}-missing'}, expect='error')
        await r.call('get_server_volumes', {'instance_name': args.existing_server})
        await r.call('get_server_volumes', {'instance_name': f'{P}-missing'}, expect='error')
        await r.call('get_network_details', {'network_name': args.network})
        await r.call('get_network_details', {'network_name': f'{P}-missing'}, expect='error')
        await r.call('get_project_details', {'project_name': os.environ.get('OS_PROJECT_NAME', '')})
        await r.call('get_project_details', {'project_name': f'{P}-missing'}, expect='error')
        await r.call('get_quota', {'project_name': os.environ.get('OS_PROJECT_NAME', '')})
        await r.call('get_hypervisor_details', {'hypervisor_name': 'all'})
        await r.call('get_hypervisor_details', {'hypervisor_name': f'{P}-missing'}, expect='error')
        today = date.today()
        await r.call('get_usage_statistics', {'start_date': str(today - timedelta(days=7)),
                                              'end_date': str(today + timedelta(days=1))})
        await r.call('get_usage_statistics', {'start_date': 'not-a-date'}, expect='error')
        await r.call('get_image_members', {'image_name': args.image}, expect='error',
                     note='public image: Glance refuses member listing')
        await r.call('get_image_members', {'image_name': f'{P}-missing'}, expect='error')
        await r.call('get_heat_stack_details', {'stack_name': f'{P}-missing'}, expect='error')
        await r.call('get_load_balancer_details', {'lb_name_or_id': f'{P}-missing'}, expect='error')
        await r.call('get_load_balancer_listeners', {'lb_name_or_id': f'{P}-missing'}, expect='error')
        await r.call('get_load_balancer_pool_members', {'pool_name_or_id': f'{P}-missing'},
                     expect='error')
        await r.call('get_load_balancer_l7_rules', {'policy_name_or_id': f'{P}-missing'},
                     expect='error')

        if not modify:
            return 0

        # -------------------------------------------------- admin read actions
        await r.call('set_flavor', {'flavor_name': '', 'action': 'list'})
        await r.call('set_project', {'project_name': '', 'action': 'list'})
        agents_out = await r.call('set_compute_agents', {'action': 'list'})
        r.check('set_compute_agents list includes hypervisors', lambda: (
            '"hypervisors"' in agents_out, agents_out[:200]))
        svc = next(iter(conn.compute.services()), None)
        if svc is not None:
            await r.call('set_compute_agents', {'action': 'show', 'agent_id': svc.id})
            await r.call('set_compute_agents', {'action': 'show', 'host': svc.host})
        await r.call('set_compute_agents', {'action': 'show', 'agent_id': f'{P}-missing'},
                     expect='error')
        await r.call('set_network_agents', {'action': 'list'})
        await r.call('set_services', {'action': 'list'})
        await r.call('set_service_logs', {'action': 'list'})
        await r.call('set_metrics', {'action': 'list'})
        await r.call('set_metrics', {'action': 'summary'})
        await r.call('set_metrics', {'action': 'show'}, expect='error', note='documented unsupported')
        await r.call('set_roles', {'action': 'list'})
        await r.call('set_domains', {'action': 'list'})
        await r.call('set_identity_groups', {'action': 'list'})
        await r.call('set_network_qos_policies', {'action': 'list'})
        await r.call('set_volume_qos', {'action': 'list'})
        await r.call('set_volume_backups', {'action': 'list'})
        await r.call('set_volume_groups', {'action': 'list'})
        await r.call('set_alarms', {'action': 'list'})
        await r.call('set_floating_ip', {'action': 'list'})
        await r.call('set_floating_ip_port_forwarding', {'action': 'list'}, expect='error',
                     note='requires a floating IP: listing without one must be refused')
        await r.call('set_networks', {'action': 'list'})
        await r.call('set_subnets', {'action': 'list'})
        await r.call('set_network_ports', {'action': 'list'})
        await r.call('set_image', {'image_names': '', 'action': 'list'})
        await r.call('set_volume', {'volume_names': '', 'action': 'list'})

        # ------------------------------------------------------- identity CRUD
        await r.call('set_domains', {'action': 'create', 'domain_name': f'{P}-domain',
                                     'description': 'mcp live check'}, kind='write')
        await r.call('set_domains', {'action': 'show', 'domain_name': f'{P}-domain'})
        await r.call('set_domains', {'action': 'update', 'domain_name': f'{P}-domain',
                                     'description': 'updated', 'enabled': False}, kind='write')
        await r.call('set_domains', {'action': 'delete', 'domain_name': f'{P}-domain'}, kind='write')
        r.check('domain deleted', r.gone(conn.identity.find_domain, f'{P}-domain'))
        await r.call('set_domains', {'action': 'show', 'domain_name': f'{P}-missing'}, expect='error')

        await r.call('set_identity_groups', {'action': 'create', 'group_name': f'{P}-group'}, kind='write')
        await r.call('set_identity_groups', {'action': 'show', 'group_name': f'{P}-group'})
        await r.call('set_identity_groups', {'action': 'update', 'group_name': f'{P}-group',
                                             'description': 'updated'}, kind='write')
        await r.call('set_identity_groups', {'action': 'delete', 'group_name': f'{P}-group'}, kind='write')
        r.check('group deleted', r.gone(conn.identity.find_group, f'{P}-group'))

        await r.call('set_roles', {'action': 'create', 'role_name': f'{P}-role'}, kind='write',
                     note='no delete action; removed by cleanup via SDK')

        os.environ.setdefault('MCPVAL_USER_PASSWORD', os.urandom(12).hex())
        await r.call('set_users', {'action': 'create', 'user_name': f'{P}-user',
                                   'password_env': 'MCPVAL_USER_PASSWORD'}, kind='write')
        await r.call('set_users', {'action': 'create', 'user_name': f'{P}-user2',
                                   'password_env': 'MCPVAL_UNSET_VARIABLE'}, expect='error')
        await r.call('set_users', {'action': 'delete', 'user_name': f'{P}-user'}, kind='write')
        r.check('user deleted', r.gone(conn.identity.find_user, f'{P}-user'))

        await r.call('set_project', {'project_name': f'{P}-project', 'action': 'create',
                                     'description': 'mcp live check'}, kind='write')
        await r.call('set_project', {'project_name': f'{P}-project', 'action': 'show'})
        await r.call('set_project', {'project_name': f'{P}-project', 'action': 'update',
                                     'description': 'updated', 'tags': 'mcpval'}, kind='write')
        await r.call('set_quota', {'project_name': f'{P}-project', 'action': 'list'})
        await r.call('set_quota', {'project_name': f'{P}-project', 'action': 'set', 'cores': 3,
                                   'instances': 3, 'networks': 3, 'volumes': 3}, kind='write')
        r.check('compute quota cores=3', lambda: (
            (q := conn.compute.get_quota_set(conn.identity.find_project(f'{P}-project').id)).cores == 3,
            f'cores={q.cores}'))
        await r.call('set_quota', {'project_name': f'{P}-project', 'action': 'delete'}, kind='write')
        await r.call('get_quota', {'project_name': f'{P}-project'})
        await r.call('set_project', {'project_name': f'{P}-project', 'action': 'delete'}, kind='write')
        r.check('project deleted', r.gone(conn.identity.find_project, f'{P}-project'))
        await r.call('set_project', {'project_name': f'{P}-missing', 'action': 'show'}, expect='error')

        # ------------------------------------------------------------- flavors
        await r.call('set_flavor', {'flavor_name': f'{P}-flavor', 'action': 'create', 'vcpus': 1,
                                    'ram': 128, 'disk': 1}, kind='write')
        await r.call('set_flavor', {'flavor_name': f'{P}-flavor', 'action': 'set_extra_specs',
                                    'properties': json.dumps({'hw:cpu_policy': 'shared'})}, kind='write')
        r.check('flavor extra spec', lambda: (
            (f := conn.compute.find_flavor(f'{P}-flavor', get_extra_specs=True)) is not None
            and (f.extra_specs or {}).get('hw:cpu_policy') == 'shared', getattr(f, 'extra_specs', None)))
        await r.call('set_flavor', {'flavor_name': f'{P}-flavor', 'action': 'delete'}, kind='write')
        r.check('flavor deleted', r.gone(conn.compute.find_flavor, f'{P}-flavor'))
        await r.call('set_flavor', {'flavor_name': f'{P}-missing', 'action': 'delete'}, expect='error')

        # ------------------------------------------------------------- network
        await r.call('set_networks', {'action': 'create', 'network_names': f'{P}-net',
                                      'description': 'mcp live check'}, kind='write')
        net = conn.network.find_network(f'{P}-net')
        r.check('network created', lambda: (net is not None, getattr(net, 'status', None)))
        await r.call('set_networks', {'action': 'update', 'network_names': f'{P}-net',
                                      'description': 'updated'}, kind='write')
        net_id = net.id if net else ''
        await r.call('set_subnets', {'action': 'create', 'subnet_name': f'{P}-subnet',
                                     'network_id': net_id, 'cidr': '10.97.0.0/24'}, kind='write')
        await r.call('set_subnets', {'action': 'show', 'subnet_name': f'{P}-subnet'})
        await r.call('set_subnets', {'action': 'create', 'subnet_name': f'{P}-badsubnet',
                                     'network_id': net_id, 'cidr': 'not-a-cidr'}, expect='error')
        await r.call('set_network_ports', {'action': 'create', 'port_name': f'{P}-port',
                                           'network_id': net_id}, kind='write')
        await r.call('set_network_ports', {'action': 'show', 'port_name': f'{P}-port'})
        await r.call('set_network_ports', {'action': 'show', 'port_name': f'{P}-missing'}, expect='error')
        await r.call('set_routers', {'action': 'create', 'router_name': f'{P}-router'}, kind='write')
        await r.call('get_routers', {})
        await r.call('set_routers', {'action': 'delete', 'router_name': f'{P}-router'}, kind='write')
        r.check('router deleted', r.gone(conn.network.find_router, f'{P}-router'))
        await r.call('set_security_groups', {'action': 'create', 'group_name': f'{P}-sg'}, kind='write')
        await r.call('set_network_qos_policies', {'action': 'create', 'policy_name': f'{P}-qos'},
                     kind='write', expect='ok' if conn.network.find_extension('qos') else 'error',
                     note='requires the Neutron qos extension')
        await r.call('set_network_qos_policies', {'action': 'delete', 'policy_name': f'{P}-qos'},
                     kind='write', expect='ok' if conn.network.find_extension('qos') else 'error')

        ips_before = {f.id for f in conn.network.ips()}
        await r.call('set_floating_ip', {'action': 'create', 'floating_network_id':
                                         conn.network.find_network(args.external_network).id,
                                         'description': f'{P}-fip'}, kind='write')
        new_ips = [f for f in conn.network.ips() if f.id not in ips_before]
        fip = next((f for f in new_ips if f.description == f'{P}-fip'), None)
        r.check('floating IP created with its description', lambda: (
            fip is not None, [f.description for f in new_ips]))
        if fip is None and len(new_ips) == 1:
            fip = new_ips[0]  # keep testing (and cleaning up) the IP we created
            if not args.no_cleanup:
                CREATED_FIPS.append(fip.id)
        fip_addr = fip.floating_ip_address if fip else ''
        await r.call('set_floating_ip', {'action': 'show', 'floating_ip_address': fip_addr})
        await r.call('set_floating_ip', {'action': 'set', 'floating_ip_address': fip_addr,
                                         'description': f'{P}-fip'}, kind='write')
        await r.call('set_floating_ip_port_forwarding', {'action': 'list', 'floating_ip_address': fip_addr},
                     expect='ok' if conn.network.find_extension('floating-ip-port-forwarding') else 'error',
                     note='requires the floating-ip-port-forwarding extension')
        await r.call('get_floating_ips', {})

        # ------------------------------------------------------------- keypair
        await r.call('set_keypair', {'action': 'create', 'keypair_names': f'{P}-kp'}, kind='write')
        await r.call('set_keypair', {'action': 'show', 'keypair_names': f'{P}-kp'})
        await r.call('set_keypair', {'action': 'show', 'keypair_names': f'{P}-missing'}, expect='error')

        # ------------------------------------------------------------ images
        await r.call('set_image', {'image_names': f'{P}-image', 'action': 'create',
                                   'properties': '{"mcpval": "yes"}'}, kind='write')
        await r.call('set_image_metadata', {'action': 'set', 'image_name': f'{P}-image',
                                            'properties': '{"os_distro": "cirros"}'}, kind='write')
        await r.call('set_image_metadata', {'action': 'show', 'image_name': f'{P}-image'})
        await r.call('set_image_visibility', {'action': 'set', 'image_name': f'{P}-image',
                                              'visibility': 'shared'}, kind='write')
        await r.call('set_image_visibility', {'action': 'show', 'image_name': f'{P}-image'})
        if args.member_project:
            demo_project = conn.identity.find_project(args.member_project)
        else:
            demo_project = conn.identity.create_project(name=f'{P}-member', domain_id='default',
                                                        description='mcp live check image member')
        if demo_project:
            await r.call('set_image_members', {'action': 'add', 'image_name': f'{P}-image',
                                               'member_project': demo_project.name}, kind='write')
            await r.call('set_image_members', {'action': 'list', 'image_name': f'{P}-image'})
            await r.call('set_image_members', {'action': 'remove', 'image_name': f'{P}-image',
                                               'member_project': demo_project.name}, kind='write')
        await r.call('set_image', {'image_names': f'{P}-image', 'action': 'update',
                                   'min_ram': 64}, kind='write')
        await r.call('set_image', {'image_names': f'{P}-image', 'action': 'delete'}, kind='write')
        r.check('image deleted', r.gone(conn.image.find_image, f'{P}-image'), timeout=30)
        await r.call('set_image_metadata', {'action': 'show', 'image_name': f'{P}-missing'}, expect='error')

        # ------------------------------------------------------------ servers
        vm = f'{P}-vm1'
        await r.call('set_server_group', {'group_name': f'{P}-sgroup', 'action': 'create',
                                          'policies': 'soft-anti-affinity'}, kind='write')
        await r.call('set_server_group', {'group_name': f'{P}-sgroup', 'action': 'show'})
        vm2 = f'{P}-vm2'
        await r.call('set_instance', {'instance_names': f'{vm},{vm2}', 'action': 'create',
                                      'flavor': args.flavor, 'image': args.image,
                                      'networks': args.network, 'key_name': f'{P}-kp'},
                     kind='write', note='bulk create of two servers')
        boot_ok = r.check('server ACTIVE after create', r.server_status(vm, 'ACTIVE'), timeout=args.timeout)
        if r.check('second server ACTIVE after create', r.server_status(vm2, 'ACTIVE'), timeout=args.timeout):
            await r.call('set_instance', {'instance_names': vm2, 'action': 'delete', 'force': True},
                         kind='write', note='force delete')
            r.check('second server force-deleted', r.server_status(vm2, 'DELETED'), timeout=args.timeout)
        await r.call('set_instance', {'instance_names': f'{P}-vm-bad', 'action': 'create',
                                      'flavor': f'{P}-missing', 'image': args.image}, expect='error')
        if boot_ok:
            lifecycle = [
                ('stop', {}, ('SHUTOFF',)), ('start', {}, ('ACTIVE',)),
                ('reboot', {'reboot_type': 'SOFT'}, ('ACTIVE',)),
                ('pause', {}, ('PAUSED',)), ('unpause', {}, ('ACTIVE',)),
                ('suspend', {}, ('SUSPENDED',)), ('resume', {}, ('ACTIVE',)),
                ('lock', {}, ('ACTIVE',)), ('unlock', {}, ('ACTIVE',)),
                ('rescue', {}, ('RESCUE',)), ('unrescue', {}, ('ACTIVE',)),
                ('shelve', {}, ('SHELVED', 'SHELVED_OFFLOADED')), ('unshelve', {}, ('ACTIVE',)),
            ]
            for action, extra, target in lifecycle:
                await r.call('set_instance', {'instance_names': vm, 'action': action, **extra}, kind='write')
                r.check(f'server {action} -> {"/".join(target)}', r.server_status(vm, *target),
                        timeout=args.timeout)
                if action == 'lock':
                    details = await r.call('get_instance_details', {'instance_names': vm})
                    r.check('get_instance_details reports locked=true', lambda: (
                        '"locked": true' in details, details[:200]))
            r.check('server locked flag cleared', lambda: (
                not conn.compute.get_server(r.server(vm).id).is_locked, 'is_locked checked'))
            await r.call('set_instance', {'instance_names': vm, 'action': 'console',
                                          'console_type': 'novnc'})
            await r.call('set_server_properties', {'instance_name': vm, 'action': 'set',
                                                   'metadata': {'mcpval': 'yes'},
                                                   'description': 'mcp live check'}, kind='write')
            r.check('server metadata set', lambda: (
                conn.compute.get_server(r.server(vm).id).metadata.get('mcpval') == 'yes', 'metadata'))
            await r.call('set_server_properties', {'instance_name': vm, 'action': 'unset',
                                                   'properties': ['mcpval']}, kind='write')
            r.check('server metadata unset', lambda: (
                'mcpval' not in conn.compute.get_server(r.server(vm).id).metadata, 'metadata'))
            await r.call('set_server_security_group', {'instance_name': vm, 'action': 'add',
                                                       'security_group': f'{P}-sg'}, kind='write')
            await r.call('set_server_security_group', {'instance_name': vm, 'action': 'remove',
                                                       'security_group': f'{P}-sg'}, kind='write')
            await r.call('set_server_security_group', {'instance_name': vm, 'action': 'add',
                                                       'security_group': f'{P}-missing'}, expect='error')
            await r.call('set_server_network', {'instance_name': vm, 'action': 'add_network',
                                                'network': f'{P}-net'}, kind='write')
            r.check('server has second network', lambda: (
                f'{P}-net' in (conn.compute.get_server(r.server(vm).id).addresses or {}),
                list((conn.compute.get_server(r.server(vm).id).addresses or {}).keys())), timeout=60)
            await r.call('set_server_fixed_ip', {'instance_name': vm, 'action': 'add',
                                                 'network': f'{P}-net'}, kind='write')
            time.sleep(10)
            addrs = (conn.compute.get_server(r.server(vm).id).addresses or {}).get(f'{P}-net', [])
            if len(addrs) > 1:
                await r.call('set_server_fixed_ip', {'instance_name': vm, 'action': 'remove',
                                                     'fixed_ip': addrs[-1]['addr']}, kind='write')
            await r.call('set_server_network', {'instance_name': vm, 'action': 'remove_network',
                                                'network': f'{P}-net'}, kind='write')
            r.check('second network removed', lambda: (
                f'{P}-net' not in (conn.compute.get_server(r.server(vm).id).addresses or {}),
                list((conn.compute.get_server(r.server(vm).id).addresses or {}).keys())), timeout=60)
            await r.call('set_server_network', {'instance_name': vm, 'action': 'add_port',
                                                'port': f'{P}-port'}, kind='write')
            r.check('port attached', lambda: (
                (p := conn.network.find_port(f'{P}-port')) is not None and p.device_id == r.server(vm).id,
                getattr(p, 'device_id', None)), timeout=60)
            await r.call('set_server_network', {'instance_name': vm, 'action': 'remove_port',
                                                'port': f'{P}-port'}, kind='write')
            r.check('port detached', lambda: (
                (p := conn.network.find_port(f'{P}-port')) is None or not p.device_id,
                getattr(p, 'device_id', None)), timeout=60)
            if fip_addr:
                await r.call('set_server_floating_ip', {'instance_name': vm, 'action': 'add',
                                                        'floating_ip': fip_addr}, kind='write')
                r.check('floating IP associated', lambda: (
                    bool(conn.network.find_ip(fip_addr).port_id), conn.network.find_ip(fip_addr).status),
                    timeout=30)
                await r.call('set_server_floating_ip', {'instance_name': vm, 'action': 'remove',
                                                        'floating_ip': fip_addr}, kind='write')
                r.check('floating IP disassociated', lambda: (
                    not conn.network.find_ip(fip_addr).port_id, conn.network.find_ip(fip_addr).status),
                    timeout=30)
            await r.call('set_server_volume', {'instance_name': vm, 'action': 'list'})
            await r.call('set_server_migration', {'instance_name': vm, 'action': 'list'})
            await r.call('set_server_migration', {'instance_name': vm, 'action': 'show',
                                                  'migration_id': '999999'}, expect='error')
            await r.call('set_server_dump', {'instance_name': vm}, expect='error',
                         note='documented unsupported')
            await r.call('get_server_events', {'instance_name': vm, 'include_event_details': True})
            await r.call('set_instance', {'instance_names': vm, 'action': 'snapshot',
                                          'snapshot_name': f'{P}-snap-image',
                                          'metadata': '{"mcpval": "yes"}'}, kind='write')
            r.check('server snapshot image active', lambda: (
                (i := conn.image.find_image(f'{P}-snap-image')) is not None and i.status == 'active',
                getattr(i, 'status', None)), timeout=args.timeout)
            await r.call('set_server_backup', {'instance_name': vm, 'backup_name': f'{P}-backup',
                                               'backup_type': 'daily', 'rotation': 1}, kind='write')
            r.check('server backup image active', lambda: (
                (i := conn.image.find_image(f'{P}-backup')) is not None and i.status == 'active',
                getattr(i, 'status', None)), timeout=args.timeout)
            r.check('server ACTIVE after images', r.server_status(vm, 'ACTIVE'), timeout=args.timeout)
            if args.resize_flavor:
                await r.call('set_instance', {'instance_names': vm, 'action': 'resize',
                                              'flavor': args.resize_flavor}, kind='write')
                if r.check('server VERIFY_RESIZE', r.server_status(vm, 'VERIFY_RESIZE'), timeout=args.timeout):
                    await r.call('set_instance', {'instance_names': vm, 'action': 'revert_resize'}, kind='write')
                    r.check('resize reverted -> ACTIVE', r.server_status(vm, 'ACTIVE'), timeout=args.timeout)
                    await r.call('set_instance', {'instance_names': vm, 'action': 'resize',
                                                  'flavor': args.resize_flavor}, kind='write')
                    r.check('server VERIFY_RESIZE again', r.server_status(vm, 'VERIFY_RESIZE'),
                            timeout=args.timeout)
                    await r.call('set_instance', {'instance_names': vm, 'action': 'confirm_resize'},
                                 kind='write')
                    r.check('resize confirmed -> ACTIVE with new flavor', lambda: (
                        (s := conn.compute.get_server(r.server(vm).id)).status == 'ACTIVE'
                        and s.flavor.get('original_name', s.flavor.get('name')) == args.resize_flavor,
                        f'{s.status} {s.flavor.get("original_name")}'), timeout=args.timeout)
            await r.call('set_instance', {'instance_names': vm, 'action': 'rebuild', 'image': args.image,
                                          'new_name': vm}, kind='write')
            r.check('server rebuilt -> ACTIVE', r.server_status(vm, 'ACTIVE'), timeout=args.timeout)
            await r.call('set_server_migration', {'instance_name': vm, 'action': 'migrate'}, kind='write',
                         expect='ok' if len(list(conn.compute.hypervisors())) > 1 else 'error',
                         note='single compute host: no migration target expected')
            out = await r.call('set_server_migration', {'instance_name': vm, 'action': 'evacuate'},
                               kind='write', expect='error',
                               note='source host is up: Nova must refuse; no onSharedStorage schema error')
            r.check('evacuate not rejected for onSharedStorage', lambda: (
                'onSharedStorage' not in out and 'Additional properties' not in out, out[:300]))
        await r.call('set_instance', {'instance_names': vm, 'action': 'delete'}, kind='write')
        r.check('server deleted', r.server_status(vm, 'DELETED'), timeout=args.timeout)
        await r.call('set_instance', {'instance_names': f'{P}-missing', 'action': 'stop'}, expect='error')
        await r.call('set_server_group', {'group_name': f'{P}-sgroup', 'action': 'delete'}, kind='write')

        # --------------------------------------------------------- block storage
        has_cinder = r.has_service('block-storage') or r.has_service('volumev3')
        expect_cinder = 'ok' if has_cinder else 'error'
        await r.call('set_volume', {'volume_names': f'{P}-vol', 'action': 'create', 'size': 1},
                     kind='write', expect=expect_cinder, note='requires Cinder')
        if has_cinder:
            r.check('volume available', lambda: (
                (v := conn.block_storage.find_volume(f'{P}-vol')) is not None and v.status == 'available',
                getattr(v, 'status', None)), timeout=args.timeout)
            await r.call('set_volume', {'volume_names': f'{P}-vol', 'action': 'extend', 'new_size': 2},
                         kind='write')
            r.check('volume extended to 2 GiB', lambda: (
                (v := conn.block_storage.find_volume(f'{P}-vol')).size == 2 and v.status == 'available',
                f'{v.size} {v.status}'), timeout=args.timeout)
            await r.call('set_snapshot', {'action': 'create', 'snapshot_names': f'{P}-vsnap',
                                          'volume_id': conn.block_storage.find_volume(f'{P}-vol').id},
                         kind='write')
            r.check('volume snapshot available', lambda: (
                (s := conn.block_storage.find_snapshot(f'{P}-vsnap')) is not None and s.status == 'available',
                getattr(s, 'status', None)), timeout=args.timeout)
            await r.call('get_volume_snapshots', {})
            await r.call('set_snapshot', {'action': 'delete', 'snapshot_names': f'{P}-vsnap'}, kind='write')
            r.check('volume snapshot deleted', r.gone(conn.block_storage.find_snapshot, f'{P}-vsnap'),
                    timeout=args.timeout)
            await r.call('set_volume_types', {'action': 'create', 'type_name': f'{P}-vtype'}, kind='write')
            await r.call('get_volume_types', {})
            await r.call('set_volume_types', {'action': 'delete', 'type_name': f'{P}-vtype'}, kind='write')
            await r.call('set_volume_qos', {'action': 'create', 'qos_name': f'{P}-vqos',
                                            'specs': '{"read_iops_sec": "1000"}'}, kind='write')
            await r.call('set_volume_qos', {'action': 'show', 'qos_name': f'{P}-vqos'})
            await r.call('set_volume_qos', {'action': 'delete', 'qos_name': f'{P}-vqos'}, kind='write')
            await r.call('set_volume_backups', {'action': 'create', 'backup_name': f'{P}-vbackup',
                                                'volume_id': conn.block_storage.find_volume(f'{P}-vol').id},
                         kind='write', note='requires cinder-backup')
            r.check('volume backup available', lambda: (
                (b := conn.block_storage.find_backup(f'{P}-vbackup', ignore_missing=True)) is not None
                and b.status == 'available', getattr(b, 'status', None)), timeout=args.timeout)
            await r.call('set_volume_backups', {'action': 'delete', 'backup_name': f'{P}-vbackup'}, kind='write')
            r.check('volume backup deleted', r.gone(conn.block_storage.find_backup, f'{P}-vbackup'),
                    timeout=args.timeout)
            await r.call('set_volume_groups', {'action': 'list'})
            await r.call('set_volume', {'volume_names': f'{P}-vol', 'action': 'delete'}, kind='write')
            r.check('volume deleted', r.gone(conn.block_storage.find_volume, f'{P}-vol'), timeout=args.timeout)
        await r.call('set_volume', {'volume_names': f'{P}-missing', 'action': 'delete'}, expect='error')
        if not has_cinder:
            await r.call('set_snapshot', {'action': 'create', 'snapshot_names': f'{P}-vsnap',
                                          'volume_id': f'{P}-missing'}, kind='write')
            await r.call('set_volume_types', {'action': 'create', 'type_name': f'{P}-vtype'}, kind='write')

        # --------------------------------------------------------- orchestration
        has_heat = r.has_service('orchestration')
        template = json.dumps({'heat_template_version': '2021-04-16',
                               'resources': {'rnd': {'type': 'OS::Heat::RandomString',
                                                     'properties': {'length': 8}}},
                               'outputs': {'value': {'value': {'get_attr': ['rnd', 'value']}}}})
        template2 = template.replace('"length": 8', '"length": 12')
        expect_heat = 'ok' if has_heat else 'error'
        await r.call('set_heat_stack', {'stack_names': f'{P}-stack', 'action': 'create',
                                        'template': template}, kind='write', expect=expect_heat)
        if has_heat:
            r.check('stack CREATE_COMPLETE', lambda: (
                (s := conn.orchestration.find_stack(f'{P}-stack')) is not None
                and s.status == 'CREATE_COMPLETE', getattr(s, 'status', None)), timeout=args.timeout)
            for section in ('resources', 'events', 'template', 'outputs'):
                await r.call('get_heat_stack_details', {'stack_name': f'{P}-stack', 'section': section})
            await r.call('get_heat_stacks', {})
            await r.call('set_heat_stack', {'stack_names': f'{P}-stack', 'action': 'update',
                                            'template': template2}, kind='write')
            r.check('stack UPDATE_COMPLETE', lambda: (
                (s := conn.orchestration.find_stack(f'{P}-stack')) is not None
                and s.status == 'UPDATE_COMPLETE', getattr(s, 'status', None)), timeout=args.timeout)
            await r.call('set_heat_stack', {'stack_names': f'{P}-stack', 'action': 'delete'}, kind='write')
            r.check('stack deleted', lambda: (
                (s := conn.orchestration.find_stack(f'{P}-stack')) is None or s.status == 'DELETE_COMPLETE',
                getattr(s, 'status', 'gone')), timeout=args.timeout)

        # ------------------------------------------------------- load balancer
        has_lb = r.has_service('load-balancer')
        await r.call('set_load_balancer', {'action': 'status', 'lb_name_or_id': f'{P}-missing'},
                     expect='error', note='missing load balancer' + ('' if has_lb else '; Octavia absent'))
        for tool, params in [
            ('set_load_balancer_amphora', {'action': 'show', 'amphora_id': f'{P}-missing'}),
            ('set_load_balancer_availability_zone', {'action': 'show', 'az_name': f'{P}-missing'}),
            ('set_load_balancer_flavor', {'action': 'show', 'flavor_name_or_id': f'{P}-missing'}),
            ('set_load_balancer_health_monitor', {'action': 'show', 'monitor_name_or_id': f'{P}-missing'}),
            ('set_load_balancer_l7_policy', {'action': 'delete', 'policy_name_or_id': f'{P}-missing'}),
            ('set_load_balancer_l7_rule', {'action': 'show', 'policy_name_or_id': f'{P}-missing',
                                           'rule_id': f'{P}-missing'}),
            ('set_load_balancer_listener', {'action': 'show', 'listener_name_or_id': f'{P}-missing'}),
            ('set_load_balancer_pool', {'action': 'show', 'pool_name_or_id': f'{P}-missing'}),
            ('set_load_balancer_pool_member', {'action': 'show', 'pool_name_or_id': f'{P}-missing',
                                               'member_id': f'{P}-missing'}),
            ('set_load_balancer_quota', {'action': 'reset', 'project_id': f'{P}-missing'}),
        ]:
            await r.call(tool, params, expect='error',
                         note='missing resource' + ('' if has_lb else '; Octavia absent'))
        await r.call('set_alarms', {'action': 'show', 'alarm_name': f'{P}-missing'}, expect='error',
                     note='missing alarm' + ('' if r.has_service('alarming') else '; Aodh absent'))

        # ------------------------------------------------------------- cleanup
        await r.call('set_keypair', {'action': 'delete', 'keypair_names': f'{P}-kp'}, kind='write')
        r.check('keypair deleted', r.gone(conn.compute.find_keypair, f'{P}-kp'))
        if fip_addr:
            await r.call('set_floating_ip', {'action': 'delete', 'floating_ip_address': fip_addr}, kind='write')
            r.check('floating IP released', lambda: (
                conn.network.find_ip(fip_addr) is None, 'released'), timeout=30)
        await r.call('set_network_ports', {'action': 'delete', 'port_name': f'{P}-port'}, kind='write')
        await r.call('set_subnets', {'action': 'delete', 'subnet_name': f'{P}-subnet'}, kind='write')
        await r.call('set_security_groups', {'action': 'delete', 'group_name': f'{P}-sg'}, kind='write')
        await r.call('set_networks', {'action': 'delete', 'network_names': f'{P}-net'}, kind='write')
        r.check('network deleted', r.gone(conn.network.find_network, f'{P}-net'), timeout=30)
    return 0


def sdk_cleanup(prefix: str) -> list[str]:
    """Remove anything left with the test prefix (failed steps, actions without delete)."""
    import openstack
    conn = openstack.connect()
    removed = []

    def attempt(label, fn):
        try:
            fn()
            removed.append(label)
        except Exception as exc:
            removed.append(f'{label} FAILED: {exc}')

    for s in conn.compute.servers(all_projects=False):
        if s.name.startswith(prefix):
            attempt(f'server {s.name}', lambda s=s: conn.compute.delete_server(s, force=True))
    for i in conn.image.images():
        if (i.name or '').startswith(prefix):
            attempt(f'image {i.name}', lambda i=i: conn.image.delete_image(i))
    for k in conn.compute.keypairs():
        if k.name.startswith(prefix):
            attempt(f'keypair {k.name}', lambda k=k: conn.compute.delete_keypair(k))
    for g in conn.compute.server_groups():
        if g.name.startswith(prefix):
            attempt(f'server group {g.name}', lambda g=g: conn.compute.delete_server_group(g))
    for f in conn.compute.flavors():
        if f.name.startswith(prefix):
            attempt(f'flavor {f.name}', lambda f=f: conn.compute.delete_flavor(f))
    for ip in conn.network.ips():
        if (ip.description or '').startswith(prefix) or ip.id in CREATED_FIPS:
            attempt(f'floating ip {ip.floating_ip_address}', lambda ip=ip: conn.network.delete_ip(ip))
    for rt in conn.network.routers():
        if rt.name.startswith(prefix):
            attempt(f'router {rt.name}', lambda rt=rt: conn.network.delete_router(rt))
    for p in conn.network.ports():
        if (p.name or '').startswith(prefix):
            attempt(f'port {p.name}', lambda p=p: conn.network.delete_port(p))
    for n in conn.network.networks():
        if n.name.startswith(prefix):
            attempt(f'network {n.name}', lambda n=n: conn.network.delete_network(n))
    for sg in conn.network.security_groups():
        if sg.name.startswith(prefix):
            attempt(f'security group {sg.name}', lambda sg=sg: conn.network.delete_security_group(sg))
    for role in conn.identity.roles():
        if role.name.startswith(prefix):
            attempt(f'role {role.name}', lambda role=role: conn.identity.delete_role(role))
    for u in conn.identity.users():
        if u.name.startswith(prefix):
            attempt(f'user {u.name}', lambda u=u: conn.identity.delete_user(u))
    for g in conn.identity.groups():
        if g.name.startswith(prefix):
            attempt(f'group {g.name}', lambda g=g: conn.identity.delete_group(g))
    for p in conn.identity.projects():
        if p.name.startswith(prefix):
            attempt(f'project {p.name}', lambda p=p: conn.identity.delete_project(p))
    for d in conn.identity.domains():
        if d.name.startswith(prefix):
            attempt(f'domain {d.name}', lambda d=d: (conn.identity.update_domain(d, is_enabled=False),
                                                     conn.identity.delete_domain(d)))
    try:
        for st in conn.orchestration.stacks():
            if st.name.startswith(prefix):
                attempt(f'stack {st.name}', lambda st=st: conn.orchestration.delete_stack(st))
    except Exception:
        pass
    try:
        for b in conn.block_storage.backups():
            if (b.name or '').startswith(prefix):
                attempt(f'backup {b.name}', lambda b=b: conn.block_storage.delete_backup(b, force=True))
    except Exception:
        pass
    try:
        for v in conn.block_storage.volumes():
            if (v.name or '').startswith(prefix):
                attempt(f'volume {v.name}', lambda v=v: conn.block_storage.delete_volume(v, force=True))
    except Exception:
        pass
    return removed


def classify_tools(calls: list[dict]) -> dict[str, list[str]]:
    """Unique-tool classification.

    passed          every call met its expectation and at least one call
                    returned a successful result from the live service
    passed_partial_service  live data returned, but part of the tool needs a
                    service missing from the cloud and reported it explicitly
    error_paths_only  every call met its expectation but only error paths
                    were exercised (e.g. a documented unsupported action)
    service_absent  every call depended on a service missing from the cloud
                    and returned an explicit error (not validated live)
    partial         at least one live success, but some calls failed
    failed          no call met its expectation
    """
    by_tool: dict[str, list[dict]] = {}
    for call in calls:
        by_tool.setdefault(call['tool'], []).append(call)
    groups: dict[str, list[str]] = {'passed': [], 'passed_partial_service': [], 'service_absent': [],
                                     'error_paths_only': [], 'partial': [], 'failed': []}
    for tool, items in sorted(by_tool.items()):
        live_ok = [c for c in items if c.get('passed') and c.get('outcome') == 'ok']
        live_partial = [c for c in items if c.get('passed') and c.get('outcome') == 'partial']
        if all(c.get('passed') for c in items):
            if live_ok and not any(c.get('requires_absent') for c in items):
                groups['passed'].append(tool)
            elif live_ok or live_partial:
                # Live data from the available services; sections that need
                # the absent service returned explicit errors.
                groups['passed_partial_service'].append(tool)
            elif any(c.get('requires_absent') for c in items):
                groups['service_absent'].append(tool)
            else:
                groups['error_paths_only'].append(tool)
        elif any(c.get('passed') for c in items):
            groups['partial'].append(tool)
        else:
            groups['failed'].append(tool)
    return groups


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--url', help='Streamable HTTP MCP endpoint (default: in-process client)')
    parser.add_argument('--prefix', default='mcpval')
    parser.add_argument('--image', default='cirros')
    parser.add_argument('--flavor', default='m1.tiny')
    parser.add_argument('--resize-flavor', default='m1.small')
    parser.add_argument('--network', default='demo-net')
    parser.add_argument('--external-network', default='public1')
    parser.add_argument('--existing-server', default='demo1')
    parser.add_argument('--member-project', default='', help='project to add as image member')
    parser.add_argument('--timeout', type=int, default=300, help='polling limit per async state (s)')
    parser.add_argument('--output', default='live-tool-check.json')
    parser.add_argument('--no-cleanup', action='store_true')
    parser.add_argument('--i-understand-this-is-destructive', dest='destructive', action='store_true',
                        help='required with ALLOW_MODIFY_OPERATIONS=true: the run creates and deletes '
                             'projects, domains, users, roles, flavors, networks, images and servers, '
                             'and cleanup deletes every resource whose name starts with --prefix')
    args = parser.parse_args()

    if not re.fullmatch(r'[a-z][a-z0-9-]{3,}', args.prefix):
        parser.error('--prefix must match [a-z][a-z0-9-]{3,} (cleanup deletes every resource '
                     'whose name starts with it)')
    modify = os.environ.get('ALLOW_MODIFY_OPERATIONS', 'false').lower() == 'true'
    if modify and not args.destructive:
        parser.error('ALLOW_MODIFY_OPERATIONS=true runs state-changing checks against the cloud; '
                     'use a disposable test cloud and pass --i-understand-this-is-destructive')
    if not modify:
        args.no_cleanup = True  # a read-only run creates nothing

    started = time.time()
    try:
        asyncio.run(run(args))
    except Exception:
        traceback.print_exc()
        RESULTS.append({'tool': None, 'check': 'harness', 'passed': False, 'detail': traceback.format_exc()[-800:]})
    leftovers = [] if args.no_cleanup else sdk_cleanup(args.prefix)

    calls = [x for x in RESULTS if x.get('tool')]
    checks = [x for x in RESULTS if x.get('check')]
    import openstack.version
    summary = {
        'openstacksdk': openstack.version.__version__,
        'duration_s': round(time.time() - started),
        'calls': len(calls), 'calls_passed': sum(1 for c in calls if c.get('passed')),
        'state_checks': len(checks), 'state_checks_passed': sum(1 for c in checks if c['passed']),
        'tools_called': len({c['tool'] for c in calls}),
        'optional_services_absent': sorted(ABSENT_SERVICES),
        'tool_classification': classify_tools(calls),
        'cleanup_by_sdk': leftovers,
    }
    with open(args.output, 'w') as fh:
        json.dump({'summary': summary, 'results': RESULTS}, fh, indent=1)
    print(json.dumps(summary, indent=1))
    return 0


if __name__ == '__main__':
    sys.exit(main())
