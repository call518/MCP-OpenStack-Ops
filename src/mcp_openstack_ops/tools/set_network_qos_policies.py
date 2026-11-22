"""Tool implementation for set_network_qos_policies."""

import json
from typing import Optional

from ..functions import set_network_qos_policies as _set_network_qos_policies
from ..mcp_main import (
    _is_modify_operation_allowed,
    conditional_tool,
)

MODIFY_ACTIONS = {
    'create', 'update', 'delete', 'add_rule', 'update_rule', 'delete_rule',
    'associate', 'disassociate',
}


@conditional_tool
async def set_network_qos_policies(
    action: str,
    policy_name: str = "",
    description: Optional[str] = None,
    shared: Optional[bool] = None,
    new_name: str = "",
    rule_type: str = "",
    rule_id: str = "",
    rule: str = "{}",
    target_type: str = "",
    target: str = "",
) -> str:
    """
    Manage Neutron QoS policies, their rules, and their attachment to
    project-owned ports, networks, floating IPs and router gateways.

    Policies and rules change only when owned by the current project.
    associate/disassociate also accept policies shared with this project.
    Attachment takes effect immediately on running traffic. A shared policy is
    visible to all projects; its rule changes apply at once to every resource
    using it, including other projects' resources this tool cannot list.
    Cloud policy may require admin or project-manager roles. Rule types the
    cloud's QoS driver does not support are rejected by Neutron.

    Args:
        action: list, show, create, update, delete, add_rule, update_rule,
            delete_rule, associate, or disassociate
        policy_name: Name or ID of the QoS policy
        description: Policy description for create/update
        shared: Share the policy with all projects (create/update); omit on
            update to keep the current value
        new_name: New policy name for update
        rule_type: Rule type for add_rule - bandwidth_limit, dscp_marking,
            minimum_bandwidth, packet_rate_limit, or minimum_packet_rate
        rule_id: Rule ID for update_rule/delete_rule (type is read from the policy)
        rule: JSON object of rule fields for add_rule/update_rule, e.g.
            '{"max_kbps": 10000, "max_burst_kbps": 8000, "direction": "egress"}'.
            Fields: bandwidth_limit max_kbps/max_burst_kbps/direction;
            dscp_marking dscp_mark; minimum_bandwidth min_kbps/direction;
            packet_rate_limit max_kpps/max_burst_kpps/direction;
            minimum_packet_rate min_kpps/direction (any, ingress or egress)
        target_type: port, network, floating_ip, or router (router gateway)
            for associate/disassociate
        target: Name or ID of the target; a floating IP also accepts its address

    Returns:
        JSON string with the operation result. associate/disassociate report
        confirmed only when a read-back shows the expected qos_policy_id.
    """

    if not _is_modify_operation_allowed() and action.lower() in MODIFY_ACTIONS:
        return json.dumps({
            'success': False,
            'message': f'Modify operations are not allowed in current environment for action: {action}',
            'error': 'MODIFY_OPERATIONS_DISABLED'
        })

    try:
        parsed_rule = json.loads(rule) if rule.strip() else {}
    except json.JSONDecodeError as e:
        return json.dumps({
            'success': False,
            'message': f'Invalid JSON in rule parameter: {str(e)}',
            'error': str(e)
        }, indent=2)

    try:
        result = _set_network_qos_policies(
            action=action,
            policy_name=policy_name if policy_name else None,
            description=description,
            shared=shared,
            new_name=new_name or None,
            rule_type=rule_type,
            rule_id=rule_id,
            rule=parsed_rule,
            target_type=target_type,
            target=target,
        )
        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({
            'success': False,
            'message': f'Failed to manage network QoS policy: {str(e)}',
            'error': str(e)
        }, indent=2)
