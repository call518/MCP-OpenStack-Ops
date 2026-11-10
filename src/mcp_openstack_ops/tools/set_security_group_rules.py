"""Tool implementation for project-owned security group rules."""

import json
from typing import Optional

from ..mcp_main import conditional_tool, _is_modify_operation_allowed
from ..services.network import set_security_group_rules as _set_security_group_rules


@conditional_tool
async def set_security_group_rules(
    action: str,
    security_group: str,
    rule_id: str = '',
    direction: str = 'ingress',
    protocol: str = '',
    port_range_min: Optional[int] = None,
    port_range_max: Optional[int] = None,
    remote_ip_prefix: str = '',
    remote_group: str = '',
    ether_type: str = 'IPv4',
    description: str = '',
) -> str:
    """Create or delete a firewall rule on a project-owned security group.

    Use this tool to open or close TCP/UDP ports, allow ICMP, or manage other
    ingress and egress rules. To attach or detach an existing security group
    from a server, use set_server_security_group instead.

    Args:
        action: Operation to perform: create or delete.
        security_group: Project-owned security group name or ID.
        rule_id: Rule ID required for delete; ignored for create.
        direction: Traffic direction for create: ingress or egress.
        protocol: Protocol name, number 0-255, or explicit any/all.
        port_range_min: First TCP/UDP/SCTP/DCCP/UDPLite port or ICMP type.
        port_range_max: Last TCP/UDP/SCTP/DCCP/UDPLite port or ICMP code.
        remote_ip_prefix: Source/destination CIDR, for example 203.0.113.0/24.
        remote_group: Project-owned remote security group name or ID.
        ether_type: IP family for create: IPv4 or IPv6.
        description: Optional rule description.

    Exactly one of remote_ip_prefix and remote_group is required for create.
    Use 0.0.0.0/0 or ::/0 explicitly when access from anywhere is intended.
    Delete requires both security_group and rule_id and verifies their relation.
    """
    if not _is_modify_operation_allowed():
        return json.dumps({
            'success': False,
            'error': 'MODIFY_OPERATIONS_DISABLED',
        })
    result = _set_security_group_rules(
        action=action,
        security_group=security_group,
        rule_id=rule_id,
        direction=direction,
        protocol=protocol,
        port_range_min=port_range_min,
        port_range_max=port_range_max,
        remote_ip_prefix=remote_ip_prefix,
        remote_group=remote_group,
        ether_type=ether_type,
        description=description,
    )
    return json.dumps(result, indent=2)
