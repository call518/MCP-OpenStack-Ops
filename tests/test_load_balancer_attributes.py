"""Load balancer services must read real openstacksdk attribute names.

These tests return genuine ``openstack.load_balancer.v2`` resource objects from
an autospecced Octavia proxy, so a wrong attribute name (``admin_state_up``
instead of ``is_admin_state_up``, singular quota fields, ...) or a proxy call
that does not match the SDK signature fails here instead of in production.
"""

from types import SimpleNamespace
from unittest.mock import create_autospec

import pytest
from openstack.load_balancer.v2._proxy import Proxy as LoadBalancerProxy
from openstack.load_balancer.v2.amphora import Amphora
from openstack.load_balancer.v2.availability_zone import AvailabilityZone
from openstack.load_balancer.v2.flavor import Flavor
from openstack.load_balancer.v2.health_monitor import HealthMonitor
from openstack.load_balancer.v2.l7_policy import L7Policy
from openstack.load_balancer.v2.l7_rule import L7Rule
from openstack.load_balancer.v2.listener import Listener
from openstack.load_balancer.v2.load_balancer import LoadBalancer
from openstack.load_balancer.v2.member import Member
from openstack.load_balancer.v2.pool import Pool
from openstack.load_balancer.v2.quota import Quota

from mcp_openstack_ops import connection
from mcp_openstack_ops.services.load_balancer import (
    amphorae, core, health_monitors, l7_policies, listeners, management, pools,
)

LB_MODULES = (amphorae, core, health_monitors, l7_policies, listeners, management, pools)


@pytest.fixture
def conn(monkeypatch):
    value = SimpleNamespace(
        current_project_id='project-a',
        load_balancer=create_autospec(LoadBalancerProxy, instance=True),
    )
    monkeypatch.setattr(connection, 'get_openstack_connection', lambda: value)
    for module in LB_MODULES:
        monkeypatch.setattr(module, 'get_openstack_connection', lambda: value)
    return value


def _lb(**overrides):
    attrs = dict(
        id='lb-1', name='web-lb', description='', vip_address='10.0.0.10',
        vip_port_id='port-1', vip_subnet_id='subnet-1', vip_network_id='net-1',
        provisioning_status='ACTIVE', operating_status='ONLINE',
        is_admin_state_up=False, project_id='project-a', provider='amphora',
    )
    attrs.update(overrides)
    return LoadBalancer.existing(**attrs)


def _listener(lb_id='lb-1', **overrides):
    attrs = dict(
        id='lis-1', name='http', description='', protocol='HTTP', protocol_port=80,
        is_admin_state_up=False, load_balancers=[{'id': lb_id}], default_pool_id=None,
    )
    attrs.update(overrides)
    return Listener.existing(**attrs)


def _pool(**overrides):
    attrs = dict(
        id='pool-1', name='web-pool', description='', protocol='HTTP',
        lb_algorithm='ROUND_ROBIN', listener_id='lis-1', is_admin_state_up=False,
        provisioning_status='ACTIVE', operating_status='ONLINE',
    )
    attrs.update(overrides)
    return Pool.existing(**attrs)


def _member(**overrides):
    attrs = dict(
        id='mem-1', name='web-1', address='10.0.0.21', protocol_port=8080, weight=5,
        is_admin_state_up=False, provisioning_status='ACTIVE',
        operating_status='ONLINE', backup=False,
    )
    attrs.update(overrides)
    return Member.existing(**attrs)


def test_load_balancer_list_reports_vip_qos_policy(conn):
    conn.load_balancer.load_balancers.return_value = [
        _lb(vip_qos_policy_id='qos-vip')]
    conn.load_balancer.listeners.return_value = []

    [lb] = core.get_load_balancer_list()['load_balancers']

    assert lb['vip_qos_policy_id'] == 'qos-vip'


def test_load_balancer_list_and_details_report_flavor_and_zone(conn):
    lb = _lb(flavor_id='flavor-1', availability_zone='az-1')
    conn.load_balancer.load_balancers.return_value = [lb]
    conn.load_balancer.find_load_balancer.return_value = lb
    conn.load_balancer.listeners.return_value = []

    [listed] = core.get_load_balancer_list()['load_balancers']
    details = core.get_load_balancer_details('web-lb')['load_balancer']

    for row in (listed, details):
        assert row['flavor_id'] == 'flavor-1'
        assert row['availability_zone'] == 'az-1'


def test_listener_list_reports_connection_limit(conn):
    conn.load_balancer.find_load_balancer.return_value = _lb()
    conn.load_balancer.listeners.return_value = [_listener(connection_limit=500)]

    listed = listeners.get_load_balancer_listeners('web-lb')

    assert listed['listeners'][0]['connection_limit'] == 500


def test_load_balancer_list_reads_is_admin_state_up_and_filters_listeners(conn):
    conn.load_balancer.load_balancers.return_value = [
        _lb(), _lb(id='lb-other-project', project_id='project-b'),
    ]
    conn.load_balancer.listeners.return_value = [
        _listener(), _listener(id='lis-foreign', lb_id='lb-2'),
    ]

    result = core.get_load_balancer_list()

    assert result['success'] is True
    [lb] = result['load_balancers']
    assert 'error' not in lb
    assert lb['admin_state_up'] is False
    assert lb['listener_count'] == 1
    assert lb['listeners'][0] == {
        'id': 'lis-1', 'name': 'http', 'protocol': 'HTTP',
        'protocol_port': 80, 'admin_state_up': False,
    }
    conn.load_balancer.listeners.assert_called_once_with(load_balancer_id='lb-1')


def test_load_balancer_details_and_status(conn):
    conn.load_balancer.find_load_balancer.return_value = _lb()
    conn.load_balancer.listeners.return_value = [_listener()]
    conn.load_balancer.pools.return_value = [_pool()]
    conn.load_balancer.members.return_value = [_member()]

    result = core.get_load_balancer_details('web-lb')

    assert result['success'] is True, result
    details = result['load_balancer']
    assert details['admin_state_up'] is False
    assert details['listeners'][0]['admin_state_up'] is False
    pool = details['listeners'][0]['pools'][0]
    assert pool['admin_state_up'] is False
    assert pool['member_count'] == 1
    conn.load_balancer.members.assert_called_once_with('pool-1')
    # Octavia rejects ?listener_id= on GET /pools with 400; filter by LB instead.
    conn.load_balancer.pools.assert_called_once_with(loadbalancer_id='lb-1')

    tree = {'statuses': {'loadbalancer': {
        'id': 'lb-1', 'provisioning_status': 'PENDING_UPDATE', 'operating_status': 'ONLINE',
        'listeners': [{'id': 'lis-1', 'provisioning_status': 'PENDING_CREATE',
                       'operating_status': 'OFFLINE', 'pools': [{'id': 'pool-1', 'members': [
                           {'id': 'mem-1', 'operating_status': 'ONLINE'}]}]}],
    }}}
    conn.load_balancer.get.return_value = SimpleNamespace(json=lambda: tree)

    status = core.set_load_balancer('status', lb_name_or_id='web-lb')
    assert status['success'] is True
    result = status['load_balancer_status']
    assert result['admin_state_up'] is False
    assert result['provisioning_status'] == 'PENDING_UPDATE'
    assert result['listeners'][0]['provisioning_status'] == 'PENDING_CREATE'
    assert result['listeners'][0]['pools'][0]['members'][0]['operating_status'] == 'ONLINE'
    assert conn.load_balancer.get.call_args.args[0] == '/lbaas/loadbalancers/lb-1/status'
    assert conn.load_balancer.get.call_args.kwargs['raise_exc'] is True

    conn.load_balancer.get.side_effect = RuntimeError('404 status API missing')
    failed = core.set_load_balancer('status', lb_name_or_id='web-lb')
    assert failed['success'] is False and '404' in failed['message']


def test_load_balancer_update_reports_sdk_admin_state(conn):
    conn.load_balancer.find_load_balancer.return_value = _lb()
    conn.load_balancer.update_load_balancer.return_value = _lb(is_admin_state_up=True)

    result = core.set_load_balancer('set', lb_name_or_id='web-lb', admin_state_up=True)

    assert result['success'] is True
    assert result['load_balancer']['admin_state_up'] is True
    _, kwargs = conn.load_balancer.update_load_balancer.call_args
    assert LoadBalancer.new(**kwargs).is_admin_state_up is True


def test_listener_list_and_show_report_load_balancer_id(conn):
    conn.load_balancer.find_load_balancer.return_value = _lb()
    conn.load_balancer.listeners.return_value = [_listener()]
    conn.load_balancer.find_listener.return_value = _listener(load_balancer_id='lb-1')

    listed = listeners.get_load_balancer_listeners('web-lb')
    shown = listeners.set_load_balancer_listener('show', listener_name_or_id='http')

    assert listed['success'] is True, listed
    assert listed['listeners'][0]['admin_state_up'] is False
    assert listed['listeners'][0]['loadbalancer_id'] == 'lb-1'
    conn.load_balancer.listeners.assert_called_once_with(load_balancer_id='lb-1')
    assert shown['success'] is True, shown
    assert shown['listener']['admin_state_up'] is False
    assert shown['listener']['loadbalancer_id'] == 'lb-1'


def test_listener_create_passes_sdk_compatible_attrs(conn):
    conn.load_balancer.find_load_balancer.return_value = _lb()
    conn.load_balancer.create_listener.return_value = _listener(is_admin_state_up=True)

    result = listeners.set_load_balancer_listener(
        'create', name='http', lb_name_or_id='web-lb', protocol='http', protocol_port=80,
    )

    assert result['success'] is True, result
    assert result['listener']['admin_state_up'] is True
    _, kwargs = conn.load_balancer.create_listener.call_args
    created = Listener.new(**kwargs)
    assert created.load_balancer_id == 'lb-1'
    assert created.is_admin_state_up is True


def test_pool_list_and_create(conn):
    conn.load_balancer.pools.return_value = [_pool()]
    conn.load_balancer.members.return_value = [_member()]
    conn.load_balancer.listeners.return_value = [_listener()]
    conn.load_balancer.create_pool.return_value = _pool(is_admin_state_up=True)

    listed = pools.get_load_balancer_pools()
    created = pools.set_load_balancer_pool(
        'create', name='web-pool', listener_name_or_id='http', protocol='http',
    )

    assert listed['success'] is True, listed
    assert listed['pools'][0]['admin_state_up'] is False
    assert listed['pools'][0]['members'][0]['admin_state_up'] is False
    conn.load_balancer.members.assert_called_once_with('pool-1')
    assert created['success'] is True, created
    assert created['pool']['admin_state_up'] is True
    assert created['pool']['listener_id'] == 'lis-1'


def test_pool_member_create_reports_success_after_sdk_create(conn):
    pool = _pool()
    conn.load_balancer.pools.return_value = [pool]
    conn.load_balancer.create_member.return_value = _member()
    conn.load_balancer.get_member.return_value = _member()

    created = pools.set_load_balancer_pool_member(
        'create', 'web-pool', address='10.0.0.21', protocol_port=8080, admin_state_up=False,
    )
    shown = pools.set_load_balancer_pool_member('show', 'web-pool', member_id='mem-1')

    assert created['success'] is True, created
    assert created['member']['admin_state_up'] is False
    assert created['member']['pool_id'] == 'pool-1'
    args, kwargs = conn.load_balancer.create_member.call_args
    assert args == (pool,)
    assert Member.new(**kwargs).is_admin_state_up is False
    assert shown['success'] is True, shown
    assert shown['member']['admin_state_up'] is False


def test_health_monitor_list_show_and_set(conn):
    monitor = HealthMonitor.existing(
        id='hm-1', name='hm', type='HTTP', delay=5, timeout=3, max_retries=2,
        max_retries_down=2, is_admin_state_up=False, provisioning_status='ACTIVE',
        operating_status='ONLINE', pool_id='pool-1',
    )
    conn.load_balancer.health_monitors.return_value = [monitor]
    conn.load_balancer.update_health_monitor.return_value = monitor

    listed = health_monitors.get_load_balancer_health_monitors()
    shown = health_monitors.set_load_balancer_health_monitor('show', monitor_name_or_id='hm')
    updated = health_monitors.set_load_balancer_health_monitor(
        'set', monitor_name_or_id='hm', admin_state_up=False,
    )

    assert listed['success'] is True, listed
    assert listed['health_monitors'][0]['admin_state_up'] is False
    assert shown['success'] is True, shown
    assert shown['health_monitor']['admin_state_up'] is False
    assert updated['success'] is True, updated
    assert updated['health_monitor']['admin_state_up'] is False


def test_pool_reports_relations_from_octavia_get_response(conn):
    # Octavia GET responses carry listeners/loadbalancers lists, not listener_id.
    pool = Pool.existing(
        id='pool-1', name='web-pool', description='', protocol='HTTP',
        lb_algorithm='ROUND_ROBIN', is_admin_state_up=True,
        provisioning_status='ACTIVE', operating_status='ONLINE',
        listeners=[{'id': 'lis-1'}], loadbalancers=[{'id': 'lb-1'}],
        health_monitor_id='hm-1',
    )
    conn.load_balancer.pools.return_value = [pool]
    conn.load_balancer.members.return_value = []

    listed = pools.get_load_balancer_pools()
    shown = pools.set_load_balancer_pool('show', pool_name_or_id='web-pool')

    conn.load_balancer.find_listener.return_value = _listener()
    conn.load_balancer.pools.reset_mock()
    conn.load_balancer.pools.return_value = [
        pool, Pool.existing(id='pool-2', name='other', listeners=[{'id': 'lis-2'}]),
    ]
    by_listener = pools.get_load_balancer_pools('http')

    # Octavia rejects ?listener_id= on GET /pools with 400; filter client-side.
    conn.load_balancer.pools.assert_called_once_with()
    assert [p['id'] for p in by_listener['pools']] == ['pool-1']
    for result in (listed['pools'][0], shown['pool']):
        assert result['listener_id'] == 'lis-1'
        assert result['listener_ids'] == ['lis-1']
        assert result['loadbalancer_ids'] == ['lb-1']
        assert result['health_monitor_id'] == 'hm-1'


def test_health_monitor_reports_and_filters_by_octavia_pools_list(conn):
    # Octavia GET responses carry a pools list, not pool_id.
    def monitor(monitor_id, pool_id):
        return HealthMonitor.existing(
            id=monitor_id, name=monitor_id, type='TCP', delay=10, timeout=5,
            max_retries=3, is_admin_state_up=True, provisioning_status='ACTIVE',
            operating_status='ONLINE', pools=[{'id': pool_id}],
        )

    conn.load_balancer.pools.return_value = [_pool()]
    conn.load_balancer.health_monitors.return_value = [
        monitor('hm-1', 'pool-1'), monitor('hm-other', 'pool-2'),
    ]

    listed = health_monitors.get_load_balancer_health_monitors()
    filtered = health_monitors.get_load_balancer_health_monitors('web-pool')
    shown = health_monitors.set_load_balancer_health_monitor('show', monitor_name_or_id='hm-1')

    assert listed['health_monitors'][0]['pool_id'] == 'pool-1'
    assert listed['health_monitors'][0]['pool_ids'] == ['pool-1']
    assert [m['id'] for m in filtered['health_monitors']] == ['hm-1']
    assert shown['health_monitor']['pool_id'] == 'pool-1'
    assert shown['health_monitor']['pool_ids'] == ['pool-1']


def test_l7_policy_list_and_rule_show(conn):
    policy = L7Policy.existing(
        id='pol-1', name='redirect', description='', listener_id='lis-1', action='REJECT',
        position=1, is_admin_state_up=False, provisioning_status='ACTIVE',
        operating_status='ONLINE',
    )
    rule = L7Rule.existing(
        id='rule-1', l7_policy_id='pol-1', type='PATH', compare_type='STARTS_WITH',
        rule_value='/api', key=None, invert=False, is_admin_state_up=False,
        provisioning_status='ACTIVE', operating_status='ONLINE',
    )
    conn.load_balancer.l7_policies.return_value = [policy]
    conn.load_balancer.find_l7_policy.return_value = policy
    conn.load_balancer.l7_rules.return_value = [rule]

    policies = l7_policies.get_load_balancer_l7_policies()
    rules = l7_policies.get_load_balancer_l7_rules('redirect')

    assert policies['success'] is True, policies
    assert policies['l7_policies'][0]['admin_state_up'] is False
    assert rules['success'] is True, rules
    assert rules['l7_rules'][0]['l7policy_id'] == 'pol-1'
    assert rules['l7_rules'][0]['value'] == '/api'
    assert rules['l7_rules'][0]['admin_state_up'] is False


def test_l7_rule_create_passes_policy_and_rule_value(conn):
    policy = L7Policy.existing(id='pol-1', name='redirect')
    conn.load_balancer.find_l7_policy.return_value = policy
    conn.load_balancer.create_l7_rule.return_value = L7Rule.existing(
        id='rule-1', type='PATH', compare_type='STARTS_WITH', rule_value='/api',
    )

    result = l7_policies.set_load_balancer_l7_rule(
        'create', policy_name_or_id='redirect', value='/api', admin_state_up=False,
    )

    assert result['success'] is True, result
    assert result['l7_rule']['value'] == '/api'
    args, kwargs = conn.load_balancer.create_l7_rule.call_args
    assert args == ('pol-1',)
    created = L7Rule.new(**kwargs)
    assert created.rule_value == '/api'
    assert created.is_admin_state_up is False


def test_l7_policy_create_passes_sdk_compatible_attrs(conn):
    conn.load_balancer.find_listener.return_value = _listener()
    conn.load_balancer.create_l7_policy.return_value = L7Policy.existing(
        id='pol-1', name='redirect', action='REJECT', position=1,
    )

    result = l7_policies.set_load_balancer_l7_policy(
        'create', listener_name_or_id='http', name='redirect', admin_state_up=False,
    )

    assert result['success'] is True, result
    _, kwargs = conn.load_balancer.create_l7_policy.call_args
    created = L7Policy.new(**kwargs)
    assert created.listener_id == 'lis-1'
    assert created.is_admin_state_up is False


def test_async_octavia_writes_report_acceptance_with_provisioning_status(conn):
    # Octavia answers writes with PENDING_*; the response must not claim
    # completion and must carry the state the caller polls.
    pending = {'provisioning_status': 'PENDING_UPDATE'}
    conn.load_balancer.find_load_balancer.return_value = _lb()
    conn.load_balancer.update_load_balancer.return_value = _lb(**pending)
    conn.load_balancer.create_listener.return_value = _listener(**pending)
    conn.load_balancer.find_listener.return_value = _listener()
    conn.load_balancer.create_l7_policy.return_value = L7Policy.existing(
        id='pol-1', name='redirect', action='REJECT', position=1, **pending)
    conn.load_balancer.find_l7_policy.return_value = L7Policy.existing(id='pol-1')
    conn.load_balancer.create_l7_rule.return_value = L7Rule.existing(
        id='rule-1', type='PATH', compare_type='STARTS_WITH', rule_value='/api',
        **pending)

    results = {
        'load_balancer': core.set_load_balancer(
            'set', lb_name_or_id='web-lb', description='x'),
        'listener': listeners.set_load_balancer_listener(
            'create', name='http', lb_name_or_id='web-lb', protocol='http',
            protocol_port=80),
        'l7_policy': l7_policies.set_load_balancer_l7_policy(
            'create', listener_name_or_id='http', name='redirect'),
        'l7_rule': l7_policies.set_load_balancer_l7_rule(
            'create', policy_name_or_id='redirect', value='/api'),
    }

    for key, result in results.items():
        assert result['success'] is True, result
        assert 'successfully' not in result['message'], result
        assert 'accepted' in result['message'], result
        assert result[key]['provisioning_status'] == 'PENDING_UPDATE', result


def _quota(project_id='project-a'):
    return Quota.existing(
        id=project_id, project_id=project_id, load_balancers=5, listeners=10,
        pools=15, health_monitors=20, members=25,
    )


EXPECTED_QUOTA = {
    'load_balancer': 5, 'listener': 10, 'pool': 15, 'health_monitor': 20, 'member': 25,
}


def test_quota_values_read_from_plural_sdk_attributes(conn):
    conn.load_balancer.get_quota.return_value = _quota()
    conn.load_balancer.quotas.return_value = [_quota()]
    conn.load_balancer.update_quota.return_value = _quota()

    single = management.get_load_balancer_quotas('project-a')
    listed = management.get_load_balancer_quotas()
    updated = management.set_load_balancer_quota('set', project_id='project-a', load_balancer=5)

    assert single['quota'] == {'project_id': 'project-a', **EXPECTED_QUOTA}
    assert listed['quotas'] == [{'project_id': 'project-a', **EXPECTED_QUOTA}]
    assert updated['quota'] == {'project_id': 'project-a', **EXPECTED_QUOTA}
    args, kwargs = conn.load_balancer.update_quota.call_args
    assert args == ('project-a',)
    assert Quota.new(**kwargs).load_balancers == 5


def test_availability_zone_and_flavor_enabled_flag(conn):
    conn.load_balancer.availability_zones.return_value = [
        AvailabilityZone.existing(name='az1', availability_zone_profile_id='azp', is_enabled=False),
    ]
    conn.load_balancer.flavors.return_value = [
        Flavor.existing(id='fl-1', name='small', flavor_profile_id='fp', is_enabled=False),
    ]
    conn.load_balancer.create_availability_zone.return_value = AvailabilityZone.existing(
        name='az1', is_enabled=False,
    )
    conn.load_balancer.create_flavor.return_value = Flavor.existing(
        id='fl-1', name='small', is_enabled=False,
    )

    zones = management.get_load_balancer_availability_zones()
    flavors = management.get_load_balancer_flavors()
    az_created = management.set_load_balancer_availability_zone(
        'create', name='az1', availability_zone_profile_id='azp', enabled=False,
    )
    flavor_created = management.set_load_balancer_flavor(
        'create', name='small', flavor_profile_id='fp', enabled=False,
    )

    assert zones['availability_zones'][0]['enabled'] is False
    assert flavors['flavors'][0]['enabled'] is False
    assert az_created['availability_zone']['enabled'] is False
    assert flavor_created['flavor']['enabled'] is False
    _, kwargs = conn.load_balancer.create_availability_zone.call_args
    assert AvailabilityZone.new(**kwargs).is_enabled is False
    _, kwargs = conn.load_balancer.create_flavor.call_args
    assert Flavor.new(**kwargs).is_enabled is False


def test_amphora_reports_loadbalancer_id(conn):
    amphora = Amphora.existing(id='amp-1', loadbalancer_id='lb-1', compute_id='vm-1', role='MASTER')
    conn.load_balancer.find_load_balancer.return_value = _lb()
    conn.load_balancer.amphorae.return_value = [amphora]
    conn.load_balancer.get_amphora.return_value = amphora

    listed = amphorae.get_load_balancer_amphorae(loadbalancer_id='lb-1')
    shown = amphorae.set_load_balancer_amphora('show', amphora_id='amp-1')
    legacy_shown = amphorae._set_load_balancer_amphora('show', amphora_id='amp-1')

    assert listed['success'] is True, listed
    assert listed['amphorae'][0]['loadbalancer_id'] == 'lb-1'
    conn.load_balancer.find_load_balancer.assert_called_once_with('lb-1')
    conn.load_balancer.amphorae.assert_called_once_with(loadbalancer_id='lb-1')
    assert shown['amphora']['loadbalancer_id'] == 'lb-1'
    assert legacy_shown['amphora']['load_balancer_id'] == 'lb-1'


def _qos_network(conn):
    from openstack.network.v2._proxy import Proxy as NetworkProxy
    from openstack.network.v2.qos_policy import QoSPolicy

    owned = QoSPolicy.existing(
        id='qos-1', name='lb-dscp', project_id='project-a', is_shared=False)
    shared = QoSPolicy.existing(
        id='qos-2', name='shared-bw', project_id='project-b', is_shared=True)
    conn.network = create_autospec(NetworkProxy, instance=True)
    conn.network.qos_policies.side_effect = lambda **query: (
        [shared] if query.get('is_shared') else [owned])


def test_load_balancer_create_resolves_vip_qos_policy_name(conn):
    _qos_network(conn)
    conn.load_balancer.create_load_balancer.return_value = _lb(
        vip_qos_policy_id='qos-1', provisioning_status='PENDING_CREATE')

    result = core.set_load_balancer(
        'create', name='web-lb', vip_subnet_id='subnet-1', vip_qos_policy='lb-dscp')

    assert result['success'] is True, result
    assert result['load_balancer']['vip_qos_policy_id'] == 'qos-1'
    _, kwargs = conn.load_balancer.create_load_balancer.call_args
    created = LoadBalancer.new(**kwargs)
    assert created.vip_qos_policy_id == 'qos-1'
    assert created.is_admin_state_up is True


def test_load_balancer_set_accepts_shared_vip_qos_policy(conn):
    _qos_network(conn)
    conn.load_balancer.find_load_balancer.return_value = _lb()
    conn.load_balancer.update_load_balancer.return_value = _lb(
        vip_qos_policy_id='qos-2', provisioning_status='PENDING_UPDATE')

    result = core.set_load_balancer('set', lb_name_or_id='web-lb', vip_qos_policy='shared-bw')

    assert result['success'] is True, result
    assert 'accepted' in result['message']
    assert result['load_balancer']['vip_qos_policy_id'] == 'qos-2'
    assert result['load_balancer']['provisioning_status'] == 'PENDING_UPDATE'
    conn.load_balancer.update_load_balancer.assert_called_once_with(
        'lb-1', vip_qos_policy_id='qos-2')


def test_load_balancer_set_rejects_unknown_vip_qos_policy(conn):
    _qos_network(conn)
    conn.load_balancer.find_load_balancer.return_value = _lb()

    result = core.set_load_balancer('set', lb_name_or_id='web-lb', vip_qos_policy='missing')

    assert result['success'] is False
    conn.load_balancer.update_load_balancer.assert_not_called()


def test_load_balancer_unset_vip_qos_policy_requires_current_policy(conn):
    _qos_network(conn)
    conn.load_balancer.find_load_balancer.return_value = _lb(vip_qos_policy_id='qos-1')
    conn.load_balancer.update_load_balancer.return_value = _lb(
        vip_qos_policy_id=None, provisioning_status='PENDING_UPDATE')

    mismatch = core.set_load_balancer('unset', lb_name_or_id='web-lb', vip_qos_policy='shared-bw')
    assert mismatch['success'] is False and 'qos-1' in mismatch['message']
    conn.load_balancer.update_load_balancer.assert_not_called()

    result = core.set_load_balancer('unset', lb_name_or_id='web-lb', vip_qos_policy='lb-dscp')

    assert result['success'] is True, result
    assert result['load_balancer']['vip_qos_policy_id'] is None
    assert result['load_balancer']['provisioning_status'] == 'PENDING_UPDATE'
    assert 'VRRP' in result['warning']
    conn.load_balancer.update_load_balancer.assert_called_once_with(
        'lb-1', vip_qos_policy_id=None)


def test_load_balancer_details_report_vip_qos_policy(conn):
    conn.load_balancer.find_load_balancer.return_value = _lb(vip_qos_policy_id='qos-1')
    conn.load_balancer.listeners.return_value = []
    conn.load_balancer.pools.return_value = []

    result = core.get_load_balancer_details('web-lb')

    assert result['load_balancer']['vip_qos_policy_id'] == 'qos-1'


def test_set_load_balancer_tool_omits_admin_state_unless_given(monkeypatch):
    # A description-only set must not re-enable a disabled load balancer.
    import asyncio
    import json

    from mcp_openstack_ops.tools import set_load_balancer as tool_module

    calls = []
    monkeypatch.setattr(tool_module, '_is_modify_operation_allowed', lambda: True)
    monkeypatch.setattr(
        tool_module, '_set_load_balancer',
        lambda action, **kwargs: calls.append(kwargs) or {'success': True})
    tool = getattr(tool_module.set_load_balancer, 'fn', tool_module.set_load_balancer)

    json.loads(asyncio.run(tool('set', lb_name_or_id='web-lb', description='x')))
    json.loads(asyncio.run(tool(
        'set', lb_name_or_id='web-lb', admin_state_up=False, vip_qos_policy='lb-dscp')))

    assert 'admin_state_up' not in calls[0]
    assert calls[1]['admin_state_up'] is False
    assert calls[1]['vip_qos_policy'] == 'lb-dscp'


def test_pool_set_sends_only_given_values(conn):
    conn.load_balancer.pools.return_value = [_pool(lb_algorithm='LEAST_CONNECTIONS')]
    conn.load_balancer.listeners.return_value = [_listener()]
    conn.load_balancer.update_pool.return_value = _pool(name='renamed')
    conn.load_balancer.create_pool.return_value = _pool()

    renamed = pools.set_load_balancer_pool('set', pool_name_or_id='web-pool', name='renamed')
    empty = pools.set_load_balancer_pool('set', pool_name_or_id='web-pool')
    pools.set_load_balancer_pool('create', name='p', listener_name_or_id='http', protocol='http')

    assert renamed['success'] is True, renamed
    _, kwargs = conn.load_balancer.update_pool.call_args
    assert kwargs == {'name': 'renamed'}
    assert empty['success'] is False
    assert conn.load_balancer.update_pool.call_count == 1
    _, kwargs = conn.load_balancer.create_pool.call_args
    assert Pool.new(**kwargs).lb_algorithm == 'ROUND_ROBIN'
    assert Pool.new(**kwargs).is_admin_state_up is True


def test_member_set_sends_only_given_values_and_allows_zero_weight(conn):
    pool = _pool()
    conn.load_balancer.pools.return_value = [pool]
    conn.load_balancer.get_member.return_value = _member(backup=True)
    conn.load_balancer.update_member.return_value = _member(backup=True)
    conn.load_balancer.create_member.return_value = _member()

    renamed = pools.set_load_balancer_pool_member(
        'set', 'web-pool', member_id='mem-1', name='web-1b')
    drained = pools.set_load_balancer_pool_member(
        'set', 'web-pool', member_id='mem-1', weight=0)
    empty = pools.set_load_balancer_pool_member('set', 'web-pool', member_id='mem-1')
    pools.set_load_balancer_pool_member(
        'create', 'web-pool', address='10.0.0.22', protocol_port=80)

    assert renamed['success'] is True and drained['success'] is True
    first, second = conn.load_balancer.update_member.call_args_list
    assert first.kwargs == {'name': 'web-1b'}
    assert second.kwargs == {'weight': 0}
    assert empty['success'] is False
    created = Member.new(**conn.load_balancer.create_member.call_args.kwargs)
    assert (created.weight, created.is_admin_state_up, created.backup) == (1, True, False)


def test_health_monitor_set_sends_only_given_values(conn):
    monitor = HealthMonitor.existing(
        id='hm-1', name='hm', type='HTTP', delay=30, timeout=7, max_retries=4,
        max_retries_down=4, is_admin_state_up=False, url_path='/health',
        expected_codes='200-204', http_method='HEAD', pools=[{'id': 'pool-1'}],
    )
    conn.load_balancer.health_monitors.return_value = [monitor]
    conn.load_balancer.update_health_monitor.return_value = monitor
    conn.load_balancer.pools.return_value = [_pool()]
    conn.load_balancer.create_health_monitor.return_value = monitor

    renamed = health_monitors.set_load_balancer_health_monitor(
        'set', monitor_name_or_id='hm', name='hm2')
    empty = health_monitors.set_load_balancer_health_monitor('set', monitor_name_or_id='hm')
    health_monitors.set_load_balancer_health_monitor('create', pool_name_or_id='web-pool')

    assert renamed['success'] is True, renamed
    args, kwargs = conn.load_balancer.update_health_monitor.call_args
    assert args == (monitor,) and kwargs == {'name': 'hm2'}
    assert empty['success'] is False
    assert conn.load_balancer.update_health_monitor.call_count == 1
    created = HealthMonitor.new(**conn.load_balancer.create_health_monitor.call_args.kwargs)
    assert (created.delay, created.timeout, created.max_retries, created.max_retries_down,
            created.is_admin_state_up, created.http_method, created.url_path,
            created.expected_codes) == (10, 5, 3, 3, True, 'GET', '/', '200')


@pytest.mark.parametrize('tool_name, target, call_args, unset_keys', [
    ('set_load_balancer_listener', '_set_load_balancer_listener',
     {'action': 'set', 'listener_name_or_id': 'http', 'name': 'x'}, ['admin_state_up']),
    ('set_load_balancer_pool', 'functions.set_load_balancer_pool',
     {'action': 'set', 'pool_name_or_id': 'web-pool', 'name': 'x'},
     ['admin_state_up', 'lb_algorithm']),
    ('set_load_balancer_pool_member', 'functions.set_load_balancer_pool_member',
     {'action': 'set', 'pool_name_or_id': 'web-pool', 'member_id': 'm', 'name': 'x'},
     ['admin_state_up', 'weight', 'backup']),
    ('set_load_balancer_health_monitor', '_set_load_balancer_health_monitor',
     {'action': 'set', 'monitor_name_or_id': 'hm', 'name': 'x'},
     ['admin_state_up', 'delay', 'timeout', 'max_retries', 'max_retries_down',
      'http_method', 'url_path', 'expected_codes']),
])
def test_lb_set_tools_leave_omitted_values_unset(monkeypatch, tool_name, target,
                                                 call_args, unset_keys):
    # An omitted value must not reach the service as a default that
    # overwrites the current setting.
    import asyncio
    import importlib

    from mcp_openstack_ops import functions

    module = importlib.import_module(f'mcp_openstack_ops.tools.{tool_name}')
    calls = []

    def fake(**kwargs):
        calls.append(kwargs)
        return {'success': True}

    if hasattr(module, '_is_modify_operation_allowed'):
        monkeypatch.setattr(module, '_is_modify_operation_allowed', lambda: True)
    if target.startswith('functions.'):
        monkeypatch.setattr(functions, target.split('.', 1)[1], fake)
    else:
        monkeypatch.setattr(module, target, fake)
    tool = getattr(module, tool_name)
    asyncio.run(getattr(tool, 'fn', tool)(**call_args))

    [kwargs] = calls
    for key in unset_keys:
        assert kwargs.get(key) in (None, ''), (key, kwargs)
