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

    status = core.set_load_balancer('status', lb_name_or_id='web-lb')
    assert status['success'] is True
    assert status['load_balancer_status']['admin_state_up'] is False


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
