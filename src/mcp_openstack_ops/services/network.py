"""
OpenStack Network (Neutron) Service Functions

This module contains functions for managing networks, subnets, routers,
security groups, floating IPs, and other networking components.
"""

import logging
from ipaddress import ip_address, ip_network
from typing import Dict, List, Any, Optional

# Configure logging
logger = logging.getLogger(__name__)


def _can_read_network_subnet(subnet: Any, network: Any, project_id: str) -> bool:
    """Accept API-visible shared subnets without widening private ownership."""
    if getattr(subnet, "network_id", None) != network.id:
        return False
    owner = getattr(subnet, "project_id", None) or getattr(subnet, "tenant_id", None)
    network_owner = (getattr(network, "project_id", None)
                     or getattr(network, "tenant_id", None))
    if owner and owner == project_id:
        return True
    return bool(
        owner and owner == network_owner
        and (getattr(network, "is_shared", False)
             or getattr(network, "is_router_external", False))
    )


def _label_project_rows(conn: Any, rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Give cross-project rows a real owner ID (or None) and the project name."""
    from ..connection import get_project_names
    names = get_project_names(conn)
    for row in rows:
        owner = row.get('project_id') or row.get('tenant_id')
        row['project_id'] = owner if owner and owner != 'unknown' else None
        row['project_name'] = names.get(row['project_id'])
    return rows


def get_network_details(network_name: str = "all", all_projects: bool = False) -> List[Dict[str, Any]]:
    """
    Get detailed information about networks in current project.

    Args:
        network_name: Name of specific network or "all" for all networks
        all_projects: With network_name "all", list every network Neutron
            shows this credential (requires ALLOW_CROSS_PROJECT_READ=true)

    Returns:
        List of network dictionaries with detailed information for current project
    """
    if all_projects:
        from ..connection import require_cross_project_read
        require_cross_project_read()
    try:
        # Import here to avoid circular imports
        from ..connection import get_openstack_connection, get_current_project_id, validate_resource_ownership
        conn = get_openstack_connection()
        current_project_id = get_current_project_id()
        
        networks = []
        
        if network_name.lower() == "all":
            for network in conn.network.networks():
                # Get project ID first
                network_project = getattr(network, 'project_id', None) or getattr(network, 'tenant_id', None)
                
                # Enhanced project validation with utility functions
                if (all_projects or
                    getattr(network, 'is_shared', False) or
                    getattr(network, 'is_router_external', False) or
                    validate_resource_ownership(network, "Network")):  # Include shared and external networks

                    # Get subnets for this network with project validation
                    subnets = []
                    for subnet in conn.network.subnets(network_id=network.id):
                        if getattr(subnet, 'network_id', None) == network.id:
                            # Enhanced validation using utility functions
                            if all_projects or _can_read_network_subnet(subnet, network, current_project_id):
                                subnets.append({
                                    'id': subnet.id,
                                    'name': getattr(subnet, 'name', 'unnamed'),
                                    'cidr': getattr(subnet, 'cidr', 'unknown'),
                                    'ip_version': getattr(subnet, 'ip_version', 4),
                                    'gateway_ip': getattr(subnet, 'gateway_ip', None),
                                    'enable_dhcp': getattr(subnet, 'is_dhcp_enabled', False)
                                })

                    networks.append({
                        'id': network.id,
                        'name': getattr(network, 'name', 'unnamed'),
                        'description': getattr(network, 'description', ''),
                        'status': getattr(network, 'status', 'unknown'),
                        'admin_state_up': getattr(network, 'is_admin_state_up', True),
                        'shared': getattr(network, 'is_shared', False),
                        'external': getattr(network, 'is_router_external', False),
                        'provider_network_type': getattr(network, 'provider_network_type', None),
                        'provider_physical_network': getattr(network, 'provider_physical_network', None),
                        'provider_segmentation_id': getattr(network, 'provider_segmentation_id', None),
                        'mtu': getattr(network, 'mtu', 1500),
                        'qos_policy_id': getattr(network, 'qos_policy_id', None),
                        'tenant_id': getattr(network, 'tenant_id', 'unknown'),
                        'project_id': network_project,
                        'created_at': str(getattr(network, 'created_at', 'unknown')),
                        'updated_at': str(getattr(network, 'updated_at', 'unknown')),
                        'subnets': subnets,
                        'subnet_count': len(subnets)
                    })
        else:
            # Get specific network
            for network in conn.network.networks():
                if getattr(network, 'name', '') == network_name or network.id == network_name:
                    # Check if network is accessible by current project
                    network_project = getattr(network, 'project_id', None) or getattr(network, 'tenant_id', None)
                    if (network_project == current_project_id or 
                        getattr(network, 'is_shared', False) or 
                        getattr(network, 'is_router_external', False)):
                        
                        # Get subnets for this network
                        subnets = []
                        for subnet in conn.network.subnets(network_id=network.id):
                            if getattr(subnet, 'network_id', None) == network.id:
                                subnet_project = getattr(subnet, 'project_id', None) or getattr(subnet, 'tenant_id', None)
                                if _can_read_network_subnet(subnet, network, current_project_id):
                                    subnets.append({
                                        'id': subnet.id,
                                        'name': getattr(subnet, 'name', 'unnamed'),
                                        'cidr': getattr(subnet, 'cidr', 'unknown'),
                                        'ip_version': getattr(subnet, 'ip_version', 4),
                                        'gateway_ip': getattr(subnet, 'gateway_ip', None),
                                        'enable_dhcp': getattr(subnet, 'is_dhcp_enabled', False),
                                        'dns_nameservers': getattr(subnet, 'dns_nameservers', []),
                                        'allocation_pools': getattr(subnet, 'allocation_pools', [])
                                    })
                        
                        networks.append({
                            'id': network.id,
                            'name': getattr(network, 'name', 'unnamed'),
                            'description': getattr(network, 'description', ''),
                            'status': getattr(network, 'status', 'unknown'),
                            'admin_state_up': getattr(network, 'is_admin_state_up', True),
                            'shared': getattr(network, 'is_shared', False),
                            'external': getattr(network, 'is_router_external', False),
                            'provider_network_type': getattr(network, 'provider_network_type', None),
                            'provider_physical_network': getattr(network, 'provider_physical_network', None),
                            'provider_segmentation_id': getattr(network, 'provider_segmentation_id', None),
                            'mtu': getattr(network, 'mtu', 1500),
                        'qos_policy_id': getattr(network, 'qos_policy_id', None),
                            'tenant_id': getattr(network, 'tenant_id', 'unknown'),
                            'project_id': network_project,
                            'created_at': str(getattr(network, 'created_at', 'unknown')),
                            'updated_at': str(getattr(network, 'updated_at', 'unknown')),
                            'subnets': subnets,
                            'subnet_count': len(subnets)
                        })
                        break

        if all_projects and network_name.lower() == "all":
            _label_project_rows(conn, networks)
        return networks

    except Exception as e:
        logger.error(f"Failed to get network details: {e}")
        raise RuntimeError("OpenStack resource query failed") from None


def set_networks(action: str, network_name: Optional[str] = None, **kwargs) -> Dict[str, Any]:
    """
    Manage networks (create, delete, update, list).
    
    Args:
        action: Action to perform (create, delete, update, list)
        network_name: Name of the network (required for create/delete/update)
        **kwargs: Additional parameters
    
    Returns:
        Result of the network operation
    """
    try:
        # Import here to avoid circular imports
        from ..connection import get_openstack_connection
        conn = get_openstack_connection()
        
        if action.lower() == 'create':
            if not network_name or not network_name.strip():
                return {
                    'success': False,
                    'message': 'Network name is required for create action'
                }
            
            # Network creation parameters
            create_params = {
                'name': network_name,
                'admin_state_up': kwargs.get('admin_state_up', True)
            }
            
            # Optional parameters
            if kwargs.get('description'):
                create_params['description'] = kwargs['description']
            if kwargs.get('shared') is not None:
                create_params['is_shared'] = kwargs['shared']
            if kwargs.get('external') is not None:
                create_params['is_router_external'] = kwargs['external']
            if kwargs.get('provider_network_type'):
                create_params['provider_network_type'] = kwargs['provider_network_type']
            if kwargs.get('provider_physical_network'):
                create_params['provider_physical_network'] = kwargs['provider_physical_network']
            if kwargs.get('provider_segmentation_id'):
                create_params['provider_segmentation_id'] = kwargs['provider_segmentation_id']
            if kwargs.get('mtu'):
                create_params['mtu'] = kwargs['mtu']
            
            network = conn.network.create_network(**create_params)
            return {
                'success': True,
                'message': f'Network "{network_name}" created successfully',
                'network': {
                    'id': network.id,
                    'name': network.name,
                    'status': network.status,
                    'admin_state_up': network.is_admin_state_up
                }
            }
            
        elif action.lower() == 'delete':
            if not network_name or not network_name.strip():
                return {
                    'success': False,
                    'message': 'Network name or ID is required for delete action'
                }
            
            # Find the network using secure project-scoped lookup
            from ..connection import find_resource_by_name_or_id, get_openstack_connection
            conn = get_openstack_connection()
            
            network = find_resource_by_name_or_id(
                conn.network.networks(), 
                network_name, 
                "Network"
            )

            if not network:
                return {
                    'success': False,
                    'message': f'Network "{network_name}" not found or not accessible in current project'
                }

            conn.network.delete_network(network)
            return {
                'success': True,
                'message': f'Network "{network_name}" deleted successfully'
            }
            
        elif action.lower() == 'update':
            if not network_name or not network_name.strip():
                return {
                    'success': False,
                    'message': 'Network name or ID is required for update action'
                }
            
            # Find the network
            network = None
            for net in conn.network.networks():
                if getattr(net, 'name', '') == network_name or net.id == network_name:
                    network = net
                    break
            
            if not network:
                return {
                    'success': False,
                    'message': f'Network "{network_name}" not found'
                }
            
            # Update parameters
            update_params = {}
            if kwargs.get('description') is not None:
                update_params['description'] = kwargs['description']
            if kwargs.get('admin_state_up') is not None:
                update_params['admin_state_up'] = kwargs['admin_state_up']
            if kwargs.get('shared') is not None:
                update_params['is_shared'] = kwargs['shared']
            if kwargs.get('mtu'):
                update_params['mtu'] = kwargs['mtu']
            
            if update_params:
                updated_network = conn.network.update_network(network, **update_params)
                return {
                    'success': True,
                    'message': f'Network "{network_name}" updated successfully',
                    'network': {
                        'id': updated_network.id,
                        'name': updated_network.name,
                        'status': updated_network.status,
                        'admin_state_up': updated_network.is_admin_state_up
                    }
                }
            else:
                return {
                    'success': False,
                    'message': 'No update parameters provided'
                }
        
        elif action.lower() == 'list':
            # Use existing get_network_details function
            return get_network_details("all")
            
        else:
            return {
                'success': False,
                'message': f'Unsupported action: {action}. Supported actions: create, delete, update, list'
            }
    
    except Exception as e:
        logger.error(f"Network management failed: {e}")
        return {
            'success': False,
            'message': f'Network management failed: {str(e)}'
        }


def get_security_groups(all_projects: bool = False) -> List[Dict[str, Any]]:
    """
    Get list of security groups with rules for current project.

    Args:
        all_projects: List every security group Neutron shows this credential
            (requires ALLOW_CROSS_PROJECT_READ=true)

    Returns:
        List of security group dictionaries for current project
    """
    if all_projects:
        from ..connection import require_cross_project_read
        require_cross_project_read()
    try:
        # Import here to avoid circular imports
        from ..connection import get_openstack_connection
        conn = get_openstack_connection()
        current_project_id = conn.current_project_id
        security_groups = []

        for sg in conn.network.security_groups():
            # Filter by current project
            sg_project_id = getattr(sg, 'project_id', None) or getattr(sg, 'tenant_id', None)
            if all_projects or sg_project_id == current_project_id:
                rules = []
                for rule in getattr(sg, 'security_group_rules', []):
                    rules.append({
                        'id': rule.get('id', 'unknown'),
                        'direction': rule.get('direction', 'unknown'),
                        'protocol': rule.get('protocol', 'any'),
                        'port_range_min': rule.get('port_range_min'),
                        'port_range_max': rule.get('port_range_max'),
                        'remote_ip_prefix': rule.get('remote_ip_prefix'),
                        'remote_group_id': rule.get('remote_group_id'),
                        'ethertype': rule.get('ethertype', 'IPv4'),
                        'description': rule.get('description', ''),
                    })
                
                security_groups.append({
                    'id': sg.id,
                    'name': getattr(sg, 'name', 'unnamed'),
                    'description': getattr(sg, 'description', ''),
                    'tenant_id': getattr(sg, 'tenant_id', 'unknown'),
                    'project_id': getattr(sg, 'project_id', 'unknown'),
                    'created_at': str(getattr(sg, 'created_at', 'unknown')),
                    'updated_at': str(getattr(sg, 'updated_at', 'unknown')),
                    'rules': rules,
                    'rule_count': len(rules)
                })
                if all_projects:
                    security_groups[-1]['shared'] = bool(getattr(sg, 'is_shared', False))

        if all_projects:
            _label_project_rows(conn, security_groups)
        logger.info(f"Retrieved {len(security_groups)} security groups for project {current_project_id}")
        return security_groups
    except Exception as e:
        logger.error(f"Failed to get security groups: {e}")
        # Do not fabricate a placeholder security group: callers report the error.
        raise


def get_floating_ips(all_projects: bool = False) -> List[Dict[str, Any]]:
    """
    Get list of floating IPs for current project.

    Args:
        all_projects: List every floating IP Neutron shows this credential
            (requires ALLOW_CROSS_PROJECT_READ=true)

    Returns:
        List of floating IP dictionaries for current project
    """
    if all_projects:
        from ..connection import require_cross_project_read
        require_cross_project_read()
    try:
        # Import here to avoid circular imports
        from ..connection import get_openstack_connection
        conn = get_openstack_connection()
        current_project_id = conn.current_project_id
        floating_ips = []

        for fip in conn.network.ips():
            # Filter by current project
            fip_project_id = getattr(fip, 'project_id', None) or getattr(fip, 'tenant_id', None)
            if all_projects or fip_project_id == current_project_id:
                floating_ips.append({
                    'id': fip.id,
                    'floating_ip_address': getattr(fip, 'floating_ip_address', 'unknown'),
                    'fixed_ip_address': getattr(fip, 'fixed_ip_address', None),
                    'port_id': getattr(fip, 'port_id', None),
                    'router_id': getattr(fip, 'router_id', None),
                    'status': getattr(fip, 'status', 'unknown'),
                    'tenant_id': getattr(fip, 'tenant_id', 'unknown'),
                    'project_id': getattr(fip, 'project_id', 'unknown'),
                    'floating_network_id': getattr(fip, 'floating_network_id', 'unknown'),
                    'qos_policy_id': getattr(fip, 'qos_policy_id', None),
                    'created_at': str(getattr(fip, 'created_at', 'unknown')),
                    'updated_at': str(getattr(fip, 'updated_at', 'unknown')),
                    'description': getattr(fip, 'description', '')
                })

        if all_projects:
            _label_project_rows(conn, floating_ips)
        logger.info(f"Retrieved {len(floating_ips)} floating IPs for project {current_project_id}")
        return floating_ips
    except Exception as e:
        logger.error(f"Failed to get floating IPs: {e}")
        # Do not fabricate a placeholder address: callers report the error.
        raise


def set_floating_ip(action: str, **kwargs) -> Dict[str, Any]:
    """
    Manage floating IPs (allocate, release, associate, disassociate).
    
    Args:
        action: Action to perform (allocate, release, associate, disassociate, list)
        **kwargs: Additional parameters depending on action
    
    Returns:
        Result of the floating IP operation
    """
    try:
        # Import here to avoid circular imports
        from ..connection import get_openstack_connection
        conn = get_openstack_connection()
        
        if action.lower() == 'list':
            floating_ips = []
            for fip in conn.network.ips():
                floating_ips.append({
                    'id': fip.id,
                    'floating_ip_address': getattr(fip, 'floating_ip_address', 'unknown'),
                    'fixed_ip_address': getattr(fip, 'fixed_ip_address', None),
                    'port_id': getattr(fip, 'port_id', None),
                    'status': getattr(fip, 'status', 'unknown')
                })
            return {
                'success': True,
                'floating_ips': floating_ips,
                'count': len(floating_ips)
            }
            
        elif action.lower() == 'allocate':
            network_name = kwargs.get('network', kwargs.get('network_name'))
            subnet_id = kwargs.get('subnet_id')
            
            if not network_name:
                return {
                    'success': False,
                    'message': 'network parameter is required for allocate action'
                }
            
            # Find the external network
            external_network = None
            for network in conn.network.networks():
                if (getattr(network, 'name', '') == network_name or network.id == network_name) and \
                   getattr(network, 'is_router_external', False):
                    external_network = network
                    break
            
            if not external_network:
                return {
                    'success': False,
                    'message': f'External network "{network_name}" not found'
                }
            
            create_params = {
                'floating_network_id': external_network.id
            }
            
            if subnet_id:
                create_params['subnet_id'] = subnet_id
            # Forward the optional attributes `openstack floating ip create`
            # accepts; dropping them reported success without applying them.
            for key in ('description', 'port_id', 'floating_ip_address'):
                if kwargs.get(key):
                    create_params[key] = kwargs[key]

            fip = conn.network.create_ip(**create_params)
            
            return {
                'success': True,
                'message': f'Floating IP allocated successfully',
                'floating_ip': {
                    'id': fip.id,
                    'floating_ip_address': getattr(fip, 'floating_ip_address', 'unknown'),
                    'status': getattr(fip, 'status', 'unknown'),
                    'floating_network_id': getattr(fip, 'floating_network_id', 'unknown'),
                    'port_id': getattr(fip, 'port_id', None),
                    'description': getattr(fip, 'description', '')
                }
            }
            
        elif action.lower() == 'release':
            floating_ip_id = kwargs.get('floating_ip_id', kwargs.get('id'))
            floating_ip_address = kwargs.get('floating_ip_address', kwargs.get('ip'))
            
            if not floating_ip_id and not floating_ip_address:
                return {
                    'success': False,
                    'message': 'floating_ip_id or floating_ip_address is required for release action'
                }
            
            # Find the floating IP
            fip = None
            for f in conn.network.ips():
                if (floating_ip_id and f.id == floating_ip_id) or \
                   (floating_ip_address and getattr(f, 'floating_ip_address', '') == floating_ip_address):
                    fip = f
                    break
            
            if not fip:
                return {
                    'success': False,
                    'message': 'Floating IP not found'
                }
            
            conn.network.delete_ip(fip)
            
            return {
                'success': True,
                'message': f'Floating IP {getattr(fip, "floating_ip_address", fip.id)} released successfully'
            }
            
        elif action.lower() == 'associate':
            floating_ip_id = kwargs.get('floating_ip_id', kwargs.get('id'))
            floating_ip_address = kwargs.get('floating_ip_address', kwargs.get('ip'))
            port_id = kwargs.get('port_id')
            fixed_ip_address = kwargs.get('fixed_ip_address')
            
            if not floating_ip_id and not floating_ip_address:
                return {
                    'success': False,
                    'message': 'floating_ip_id or floating_ip_address is required'
                }
                
            if not port_id:
                return {
                    'success': False,
                    'message': 'port_id is required for associate action'
                }
            
            # Find the floating IP
            fip = None
            for f in conn.network.ips():
                if (floating_ip_id and f.id == floating_ip_id) or \
                   (floating_ip_address and getattr(f, 'floating_ip_address', '') == floating_ip_address):
                    fip = f
                    break
            
            if not fip:
                return {
                    'success': False,
                    'message': 'Floating IP not found'
                }
            
            update_params = {'port_id': port_id}
            if fixed_ip_address:
                update_params['fixed_ip_address'] = fixed_ip_address
            
            updated_fip = conn.network.update_ip(fip, **update_params)
            
            return {
                'success': True,
                'message': f'Floating IP {getattr(fip, "floating_ip_address", fip.id)} associated successfully',
                'floating_ip': {
                    'id': updated_fip.id,
                    'floating_ip_address': getattr(updated_fip, 'floating_ip_address', 'unknown'),
                    'fixed_ip_address': getattr(updated_fip, 'fixed_ip_address', None),
                    'port_id': getattr(updated_fip, 'port_id', None)
                }
            }
            
        elif action.lower() == 'disassociate':
            floating_ip_id = kwargs.get('floating_ip_id', kwargs.get('id'))
            floating_ip_address = kwargs.get('floating_ip_address', kwargs.get('ip'))
            
            if not floating_ip_id and not floating_ip_address:
                return {
                    'success': False,
                    'message': 'floating_ip_id or floating_ip_address is required'
                }
            
            # Find the floating IP
            fip = None
            for f in conn.network.ips():
                if (floating_ip_id and f.id == floating_ip_id) or \
                   (floating_ip_address and getattr(f, 'floating_ip_address', '') == floating_ip_address):
                    fip = f
                    break
            
            if not fip:
                return {
                    'success': False,
                    'message': 'Floating IP not found'
                }
            
            updated_fip = conn.network.update_ip(fip, port_id=None)
            
            return {
                'success': True,
                'message': f'Floating IP {getattr(fip, "floating_ip_address", fip.id)} disassociated successfully'
            }
        
        elif action.lower() == 'show':
            floating_ip_id = kwargs.get('floating_ip_id', kwargs.get('id'))
            floating_ip_address = kwargs.get('floating_ip_address', kwargs.get('ip'))
            
            if not floating_ip_id and not floating_ip_address:
                return {
                    'success': False,
                    'message': 'floating_ip_id or floating_ip_address is required for show action'
                }
            
            # Find the floating IP
            fip = None
            for f in conn.network.ips():
                if (floating_ip_id and f.id == floating_ip_id) or \
                   (floating_ip_address and getattr(f, 'floating_ip_address', '') == floating_ip_address):
                    fip = f
                    break
            
            if not fip:
                return {
                    'success': False,
                    'message': 'Floating IP not found'
                }
            
            return {
                'success': True,
                'floating_ip': {
                    'id': fip.id,
                    'floating_ip_address': getattr(fip, 'floating_ip_address', 'unknown'),
                    'fixed_ip_address': getattr(fip, 'fixed_ip_address', None),
                    'port_id': getattr(fip, 'port_id', None),
                    'router_id': getattr(fip, 'router_id', None),
                    'status': getattr(fip, 'status', 'unknown'),
                    'tenant_id': getattr(fip, 'tenant_id', 'unknown'),
                    'project_id': getattr(fip, 'project_id', 'unknown'),
                    'floating_network_id': getattr(fip, 'floating_network_id', 'unknown'),
                    'description': getattr(fip, 'description', ''),
                    'created_at': str(getattr(fip, 'created_at', 'unknown')),
                    'updated_at': str(getattr(fip, 'updated_at', 'unknown'))
                }
            }
            
        elif action.lower() == 'set':
            floating_ip_id = kwargs.get('floating_ip_id', kwargs.get('id'))
            floating_ip_address = kwargs.get('floating_ip_address', kwargs.get('ip'))
            
            if not floating_ip_id and not floating_ip_address:
                return {
                    'success': False,
                    'message': 'floating_ip_id or floating_ip_address is required for set action'
                }
            
            # Find the floating IP
            fip = None
            for f in conn.network.ips():
                if (floating_ip_id and f.id == floating_ip_id) or \
                   (floating_ip_address and getattr(f, 'floating_ip_address', '') == floating_ip_address):
                    fip = f
                    break
            
            if not fip:
                return {
                    'success': False,
                    'message': 'Floating IP not found'
                }
            
            # Update parameters
            update_params = {}
            if kwargs.get('description') is not None:
                update_params['description'] = kwargs['description']
            if kwargs.get('port_id') is not None:
                update_params['port_id'] = kwargs['port_id']
            if kwargs.get('fixed_ip_address') is not None:
                update_params['fixed_ip_address'] = kwargs['fixed_ip_address']
            
            if not update_params:
                return {
                    'success': False,
                    'message': 'No update parameters provided'
                }
            
            updated_fip = conn.network.update_ip(fip, **update_params)
            
            return {
                'success': True,
                'message': f'Floating IP {getattr(fip, "floating_ip_address", fip.id)} updated successfully',
                'floating_ip': {
                    'id': updated_fip.id,
                    'floating_ip_address': getattr(updated_fip, 'floating_ip_address', 'unknown'),
                    'fixed_ip_address': getattr(updated_fip, 'fixed_ip_address', None),
                    'port_id': getattr(updated_fip, 'port_id', None),
                    'description': getattr(updated_fip, 'description', '')
                }
            }
            
        elif action.lower() == 'unset':
            floating_ip_id = kwargs.get('floating_ip_id', kwargs.get('id'))
            floating_ip_address = kwargs.get('floating_ip_address', kwargs.get('ip'))
            
            if not floating_ip_id and not floating_ip_address:
                return {
                    'success': False,
                    'message': 'floating_ip_id or floating_ip_address is required for unset action'
                }
            
            # Find the floating IP
            fip = None
            for f in conn.network.ips():
                if (floating_ip_id and f.id == floating_ip_id) or \
                   (floating_ip_address and getattr(f, 'floating_ip_address', '') == floating_ip_address):
                    fip = f
                    break
            
            if not fip:
                return {
                    'success': False,
                    'message': 'Floating IP not found'
                }
            
            # Unset parameters (clear them)
            update_params = {}
            unset_properties = kwargs.get('properties', [])
            
            if 'description' in unset_properties:
                update_params['description'] = ''
            if 'port' in unset_properties:
                update_params['port_id'] = None
                update_params['fixed_ip_address'] = None
            
            if not update_params:
                return {
                    'success': False,
                    'message': 'No properties specified to unset'
                }
            
            updated_fip = conn.network.update_ip(fip, **update_params)
            
            return {
                'success': True,
                'message': f'Floating IP {getattr(fip, "floating_ip_address", fip.id)} properties unset successfully',
                'floating_ip': {
                    'id': updated_fip.id,
                    'floating_ip_address': getattr(updated_fip, 'floating_ip_address', 'unknown'),
                    'fixed_ip_address': getattr(updated_fip, 'fixed_ip_address', None),
                    'port_id': getattr(updated_fip, 'port_id', None)
                }
            }
        
        else:
            return {
                'success': False,
                'message': f'Unknown action "{action}". Supported: allocate, release, associate, disassociate, list, show, set, unset'
            }
            
    except Exception as e:
        logger.error(f"Failed to manage floating IP: {e}")
        return {
            'success': False,
            'message': f'Failed to manage floating IP: {str(e)}',
            'error': str(e)
        }


def get_floating_ip_pools() -> List[Dict[str, Any]]:
    """
    Get list of floating IP pools (external networks).
    
    Returns:
        List of floating IP pool dictionaries
    """
    try:
        # Import here to avoid circular imports
        from ..connection import get_openstack_connection
        conn = get_openstack_connection()
        pools = []
        
        for network in conn.network.networks():
            if getattr(network, 'is_router_external', False):
                # Count available and used floating IPs
                used_ips = 0
                total_ips = 0
                
                for subnet in conn.network.subnets():
                    if getattr(subnet, 'network_id', None) == network.id:
                        # Calculate total IPs from allocation pools
                        allocation_pools = getattr(subnet, 'allocation_pools', [])
                        for pool in allocation_pools:
                            start = ip_address(pool['start'])
                            end = ip_address(pool['end'])
                            if start.version != end.version or end < start:
                                raise ValueError("Invalid allocation pool range")
                            total_ips += int(end) - int(start) + 1
                
                # Count used floating IPs
                for fip in conn.network.ips():
                    if getattr(fip, 'floating_network_id', None) == network.id:
                        used_ips += 1
                
                pools.append({
                    'id': network.id,
                    'name': getattr(network, 'name', 'unnamed'),
                    'network_id': network.id,
                    'total_ips': total_ips,
                    'used_ips': used_ips,
                    # Floating IP visibility does not establish global free capacity.
                    'available_ips': None,
                    'data_source': 'subnet_allocation_pools',
                    'used_ips_scope': 'visible_floating_ip_allocations',
                    'available_ips_note': (
                        'Global free capacity is unknown: other projects and '
                            'non-floating port allocations may consume addresses'
                    ),
                    'admin_state_up': getattr(network, 'is_admin_state_up', True)
                })
        
        return pools
    except Exception as e:
        logger.error(f"Failed to get floating IP pools: {e}")
        # Do not return a placeholder pool that is counted as a real one.
        raise


def _find_port_forwarding_fip(conn: Any, floating_ip_id: Optional[str],
                              floating_ip_address: Optional[str]):
    """Return the current project's floating IP given by ID or address, or None."""
    project_id = conn.current_project_id
    for fip in conn.network.ips(project_id=project_id):
        if getattr(fip, 'project_id', None) != project_id:
            continue
        if (floating_ip_id and fip.id == floating_ip_id) or (
                floating_ip_address
                and getattr(fip, 'floating_ip_address', '') == floating_ip_address):
            return fip
    return None


def set_floating_ip_port_forwarding(action: str, **kwargs) -> Dict[str, Any]:
    """
    Manage floating IP port forwarding rules.

    Every action takes floating_ip_id or floating_ip_address and works only on
    floating IPs owned by the current project.

    Args:
        action: Action to perform (create, delete, list, show, set)
        **kwargs: Additional parameters depending on action

    Returns:
        Result of the port forwarding operation
    """
    try:
        # Import here to avoid circular imports
        from ..connection import get_openstack_connection
        conn = get_openstack_connection()

        action = action.lower()
        if action not in {'list', 'create', 'delete', 'show', 'set'}:
            return {
                'success': False,
                'message': f'Unsupported action: {action}. Supported actions: create, delete, list, show, set'
            }
        floating_ip_id = kwargs.get('floating_ip_id')
        floating_ip_address = kwargs.get('floating_ip_address')
        if not floating_ip_id and not floating_ip_address:
            return {
                'success': False,
                'message': f'floating_ip_id or floating_ip_address is required for {action} action'
            }
        fip = _find_port_forwarding_fip(conn, floating_ip_id, floating_ip_address)
        if not fip:
            return {
                'success': False,
                'message': 'Floating IP not found in the current project'
            }
        if action in {'delete', 'show', 'set'} and not kwargs.get('port_forwarding_id'):
            return {
                'success': False,
                'message': f'port_forwarding_id is required for {action} action'
            }

        if action == 'list':
            # Get port forwarding rules for this floating IP
            port_forwardings = []
            try:
                for pf in conn.network.port_forwardings(fip.id):
                    port_forwardings.append({
                        'id': pf.id,
                        'protocol': getattr(pf, 'protocol', 'unknown'),
                        'external_port': getattr(pf, 'external_port', 0),
                        'internal_port': getattr(pf, 'internal_port', 0),
                        'internal_ip_address': getattr(pf, 'internal_ip_address', 'unknown'),
                        'internal_port_id': getattr(pf, 'internal_port_id', None),
                        'description': getattr(pf, 'description', '')
                    })
            except Exception as e:
                logger.warning(f"Could not retrieve port forwarding rules: {e}")
                return {'success': False, 'message': str(e)}
                
            return {
                'success': True,
                'floating_ip_id': fip.id,
                'floating_ip_address': getattr(fip, 'floating_ip_address', 'unknown'),
                'port_forwardings': port_forwardings,
                'count': len(port_forwardings)
            }
            
        elif action == 'create':
            protocol = kwargs.get('protocol', 'tcp')
            external_port = kwargs.get('external_port')
            internal_port = kwargs.get('internal_port')
            internal_ip_address = kwargs.get('internal_ip_address')
            internal_port_id = kwargs.get('internal_port_id')
            description = kwargs.get('description', '')

            if not external_port or not internal_port:
                return {
                    'success': False,
                    'message': 'external_port and internal_port are required for create action'
                }

            create_params = {
                'protocol': protocol,
                'external_port': external_port,
                'internal_port': internal_port
            }
            
            if internal_ip_address:
                create_params['internal_ip_address'] = internal_ip_address
            if internal_port_id:
                create_params['internal_port_id'] = internal_port_id
            if description:
                create_params['description'] = description
            
            try:
                pf = conn.network.create_port_forwarding(
                    floatingip_id=fip.id, **create_params
                )
                return {
                    'success': True,
                    'message': f'Port forwarding rule created successfully',
                    'port_forwarding': {
                        'id': pf.id,
                        'protocol': getattr(pf, 'protocol', protocol),
                        'external_port': getattr(pf, 'external_port', external_port),
                        'internal_port': getattr(pf, 'internal_port', internal_port),
                        'internal_ip_address': getattr(pf, 'internal_ip_address', internal_ip_address)
                    }
                }
            except Exception as e:
                return {
                    'success': False,
                    'message': f'Failed to create port forwarding rule: {str(e)}',
                    'note': 'Port forwarding may not be supported in this OpenStack deployment'
                }
                
        elif action == 'delete':
            port_forwarding_id = kwargs.get('port_forwarding_id')

            try:
                conn.network.delete_port_forwarding(
                    port_forwarding_id, floating_ip=fip.id
                )
                return {
                    'success': True,
                    'message': f'Port forwarding rule deleted successfully'
                }
            except Exception as e:
                return {
                    'success': False,
                    'message': f'Failed to delete port forwarding rule: {str(e)}'
                }
                
        elif action == 'show':
            port_forwarding_id = kwargs.get('port_forwarding_id')

            try:
                pf = conn.network.get_port_forwarding(
                    port_forwarding_id, floating_ip=fip.id
                )
                return {
                    'success': True,
                    'port_forwarding': {
                        'id': pf.id,
                        'protocol': getattr(pf, 'protocol', 'unknown'),
                        'external_port': getattr(pf, 'external_port', 0),
                        'internal_port': getattr(pf, 'internal_port', 0),
                        'internal_ip_address': getattr(pf, 'internal_ip_address', 'unknown'),
                        'internal_port_id': getattr(pf, 'internal_port_id', None),
                        'description': getattr(pf, 'description', ''),
                        # Neutron returns no timestamps for port forwardings.
                        'created_at': getattr(pf, 'created_at', None),
                        'updated_at': getattr(pf, 'updated_at', None)
                    }
                }
            except Exception as e:
                return {
                    'success': False,
                    'message': f'Failed to get port forwarding rule: {str(e)}'
                }
                
        else:  # set
            port_forwarding_id = kwargs.get('port_forwarding_id')

            update_params = {}
            if kwargs.get('description') is not None:
                update_params['description'] = kwargs['description']
            if kwargs.get('internal_ip_address'):
                update_params['internal_ip_address'] = kwargs['internal_ip_address']
            if kwargs.get('internal_port'):
                update_params['internal_port'] = kwargs['internal_port']
            if kwargs.get('internal_port_id'):
                update_params['internal_port_id'] = kwargs['internal_port_id']
            
            if not update_params:
                return {
                    'success': False,
                    'message': 'No update parameters provided'
                }
            
            try:
                pf = conn.network.update_port_forwarding(
                    port_forwarding_id,
                    floating_ip=fip.id,
                    **update_params
                )
                return {
                    'success': True,
                    'message': f'Port forwarding rule updated successfully',
                    'port_forwarding': {
                        'id': pf.id,
                        'protocol': getattr(pf, 'protocol', 'unknown'),
                        'external_port': getattr(pf, 'external_port', 0),
                        'internal_port': getattr(pf, 'internal_port', 0),
                        'internal_ip_address': getattr(pf, 'internal_ip_address', 'unknown')
                    }
                }
            except Exception as e:
                return {
                    'success': False,
                    'message': f'Failed to update port forwarding rule: {str(e)}'
                }

    except Exception as e:
        logger.error(f"Port forwarding management failed: {e}")
        return {
            'success': False,
            'message': f'Port forwarding management failed: {str(e)}'
        }


def get_routers(all_projects: bool = False) -> List[Dict[str, Any]]:
    """
    Get list of routers with detailed information for current project.

    Args:
        all_projects: List every router Neutron shows this credential
            (requires ALLOW_CROSS_PROJECT_READ=true)

    Returns:
        List of router dictionaries for current project
    """
    if all_projects:
        from ..connection import require_cross_project_read
        require_cross_project_read()
    try:
        # Import here to avoid circular imports
        from ..connection import get_openstack_connection
        conn = get_openstack_connection()
        current_project_id = conn.current_project_id
        routers = []

        for router in conn.network.routers():
            # Filter by current project
            router_project_id = getattr(router, 'project_id', None) or getattr(router, 'tenant_id', None)
            if all_projects or router_project_id == current_project_id:
                # Get router interfaces (ports)
                interfaces = []
                interfaces_error = None
                try:
                    for port in conn.network.ports():
                        if getattr(port, 'device_id', '') == router.id and \
                           getattr(port, 'device_owner', '').startswith('network:router_interface'):
                            interfaces.append({
                                'port_id': port.id,
                                'subnet_id': getattr(port, 'fixed_ips', [{}])[0].get('subnet_id', 'unknown') if getattr(port, 'fixed_ips', []) else 'unknown',
                                'ip_address': getattr(port, 'fixed_ips', [{}])[0].get('ip_address', 'unknown') if getattr(port, 'fixed_ips', []) else 'unknown'
                            })
                except Exception as e:
                    logger.warning(f"Failed to get router interfaces for {router.id}: {e}")
                    interfaces_error = str(e)

                router_info = {
                    'id': router.id,
                    'name': getattr(router, 'name', 'unnamed'),
                    'status': getattr(router, 'status', 'unknown'),
                    'admin_state_up': getattr(router, 'is_admin_state_up', True),
                    'external_gateway_info': getattr(router, 'external_gateway_info', None),
                    'tenant_id': getattr(router, 'tenant_id', 'unknown'),
                    'project_id': getattr(router, 'project_id', 'unknown'),
                    'created_at': str(getattr(router, 'created_at', 'unknown')),
                    'updated_at': str(getattr(router, 'updated_at', 'unknown')),
                    'description': getattr(router, 'description', ''),
                    'ha': getattr(router, 'is_ha', False),
                    'distributed': getattr(router, 'is_distributed', False),
                    'routes': getattr(router, 'routes', None),
                    'interfaces': interfaces,
                    'interface_count': len(interfaces)
                }
                if interfaces_error is not None:
                    # A failed lookup is not "no interfaces": report null and why.
                    router_info.update(interfaces=None, interface_count=None,
                                       interfaces_error=interfaces_error)
                routers.append(router_info)

        if all_projects:
            _label_project_rows(conn, routers)
        logger.info(f"Retrieved {len(routers)} routers for project {current_project_id}")
        return routers
    except Exception as e:
        logger.error(f"Failed to get routers: {e}")
        raise RuntimeError("OpenStack resource query failed") from None


def set_network_ports(action: str, port_name: Optional[str] = None, **kwargs) -> Dict[str, Any]:
    """
    Manage network ports.
    
    Args:
        action: Action to perform (list, show, create, delete, update)
        port_name: Name or ID of port (for specific operations)
        **kwargs: Additional parameters
    
    Returns:
        Result of the port operation
    """
    try:
        # Import here to avoid circular imports
        from ..connection import get_openstack_connection
        conn = get_openstack_connection()
        all_projects = bool(kwargs.get('all_projects'))
        if all_projects and action.lower() != 'list':
            raise ValueError('all_projects applies only to list')
        if all_projects:
            from ..connection import require_cross_project_read
            require_cross_project_read()

        def visible_ports():
            # Neutron returns every project's ports to an administrator, so
            # narrow to the current project unless all_projects is requested.
            if all_projects:
                return conn.network.ports()
            return conn.network.ports(project_id=conn.current_project_id)

        if action.lower() == 'list':
            ports = []
            for port in visible_ports():
                ports.append({
                    'id': port.id,
                    'name': getattr(port, 'name', 'unnamed'),
                    'description': getattr(port, 'description', ''),
                    'project_id': getattr(port, 'project_id', None),
                    'network_id': getattr(port, 'network_id', 'unknown'),
                    'status': getattr(port, 'status', 'unknown'),
                    'admin_state_up': getattr(port, 'is_admin_state_up', True),
                    'device_id': getattr(port, 'device_id', ''),
                    'device_owner': getattr(port, 'device_owner', ''),
                    'mac_address': getattr(port, 'mac_address', 'unknown'),
                    'fixed_ips': getattr(port, 'fixed_ips', []),
                    'security_groups': getattr(port, 'security_group_ids', []),
                    'qos_policy_id': getattr(port, 'qos_policy_id', None),
                    'qos_network_policy_id': getattr(port, 'qos_network_policy_id', None),
                })
            if all_projects:
                from ..connection import shared_items_scope
                _label_project_rows(conn, ports)
                return {'success': True, 'ports': ports, 'count': len(ports),
                        'scope': shared_items_scope(ports)}
            return {
                'success': True,
                'ports': ports,
                'count': len(ports)
            }
            
        elif action.lower() == 'show':
            if not port_name:
                return {
                    'success': False,
                    'message': 'port_name is required for show action'
                }
            
            # Find the port
            for port in visible_ports():
                if getattr(port, 'name', '') == port_name or port.id == port_name:
                    row = {
                        'id': port.id,
                        'name': getattr(port, 'name', 'unnamed'),
                        'description': getattr(port, 'description', ''),
                        'project_id': getattr(port, 'project_id', None),
                        'network_id': getattr(port, 'network_id', 'unknown'),
                        'status': getattr(port, 'status', 'unknown'),
                        'admin_state_up': getattr(port, 'is_admin_state_up', True),
                        'device_id': getattr(port, 'device_id', ''),
                        'device_owner': getattr(port, 'device_owner', ''),
                        'mac_address': getattr(port, 'mac_address', 'unknown'),
                        'fixed_ips': getattr(port, 'fixed_ips', []),
                        'security_groups': getattr(port, 'security_group_ids', []),
                        'qos_policy_id': getattr(port, 'qos_policy_id', None),
                        'qos_network_policy_id': getattr(port, 'qos_network_policy_id', None),
                        'created_at': str(getattr(port, 'created_at', 'unknown')),
                        'updated_at': str(getattr(port, 'updated_at', 'unknown'))
                    }
                    return {'success': True, 'port': row}

            return {
                'success': False,
                'message': f'Port "{port_name}" not found in the current project'
            }
            
        elif action.lower() == 'create':
            network_id = kwargs.get('network_id')
            name = kwargs.get('name', port_name)
            
            if not network_id:
                return {
                    'success': False,
                    'message': 'network_id is required for create action'
                }
            
            create_params = {'network_id': network_id}
            if name:
                create_params['name'] = name
            if kwargs.get('description'):
                create_params['description'] = kwargs['description']

            # Optional parameters
            if 'admin_state_up' in kwargs:
                create_params['is_admin_state_up'] = kwargs['admin_state_up']
            if 'fixed_ips' in kwargs:
                create_params['fixed_ips'] = kwargs['fixed_ips']
            if 'security_groups' in kwargs:
                create_params['security_group_ids'] = kwargs['security_groups']
            
            port = conn.network.create_port(**create_params)
            
            return {
                'success': True,
                'message': f'Port "{name or port.id}" created successfully',
                'port': {
                    'id': port.id,
                    'name': getattr(port, 'name', 'unnamed'),
                    'network_id': getattr(port, 'network_id', 'unknown'),
                    'status': getattr(port, 'status', 'unknown'),
                    'mac_address': getattr(port, 'mac_address', 'unknown')
                }
            }
            
        elif action.lower() == 'delete':
            if not port_name:
                return {
                    'success': False,
                    'message': 'port_name is required for delete action'
                }
            
            # Find the port using secure project-scoped lookup
            from ..connection import find_resource_by_name_or_id
            
            port = find_resource_by_name_or_id(
                conn.network.ports(), 
                port_name, 
                "Network Port"
            )
            
            if not port:
                return {
                    'success': False,
                    'message': f'Port "{port_name}" not found or not accessible in current project'
                }
                    
            conn.network.delete_port(port)
            return {
                'success': True,
                'message': f'Port "{port_name}" deleted successfully'
            }
            
        else:
            return {
                'success': False,
                'message': f'Unknown action "{action}". Supported: list, show, create, delete'
            }
            
    except Exception as e:
        logger.error(f"Failed to manage network port: {e}")
        return {
            'success': False,
            'message': f'Failed to manage network port: {str(e)}',
            'error': str(e)
        }


def set_subnets(action: str, subnet_name: Optional[str] = None, **kwargs) -> Dict[str, Any]:
    """
    Manage network subnets.
    
    Args:
        action: Action to perform (list, show, create, delete, update)
        subnet_name: Name or ID of subnet (for specific operations)
        **kwargs: Additional parameters
    
    Returns:
        Result of the subnet operation
    """
    try:
        # Import here to avoid circular imports
        from ..connection import get_openstack_connection
        conn = get_openstack_connection()
        
        if action.lower() == 'list':
            subnets = []
            for subnet in conn.network.subnets():
                subnets.append({
                    'id': subnet.id,
                    'name': getattr(subnet, 'name', 'unnamed'),
                    'description': getattr(subnet, 'description', ''),
                    'network_id': getattr(subnet, 'network_id', 'unknown'),
                    'cidr': getattr(subnet, 'cidr', 'unknown'),
                    'ip_version': getattr(subnet, 'ip_version', 4),
                    'gateway_ip': getattr(subnet, 'gateway_ip', None),
                    'enable_dhcp': getattr(subnet, 'is_dhcp_enabled', False),
                    'allocation_pools': getattr(subnet, 'allocation_pools', []),
                    'dns_nameservers': getattr(subnet, 'dns_nameservers', [])
                })
            return {
                'success': True,
                'subnets': subnets,
                'count': len(subnets)
            }
            
        elif action.lower() == 'show':
            if not subnet_name:
                return {
                    'success': False,
                    'message': 'subnet_name is required for show action'
                }
            
            # Find the subnet
            for subnet in conn.network.subnets():
                if getattr(subnet, 'name', '') == subnet_name or subnet.id == subnet_name:
                    return {
                        'success': True,
                        'subnet': {
                            'id': subnet.id,
                            'name': getattr(subnet, 'name', 'unnamed'),
                            'description': getattr(subnet, 'description', ''),
                            'network_id': getattr(subnet, 'network_id', 'unknown'),
                            'cidr': getattr(subnet, 'cidr', 'unknown'),
                            'ip_version': getattr(subnet, 'ip_version', 4),
                            'gateway_ip': getattr(subnet, 'gateway_ip', None),
                            'enable_dhcp': getattr(subnet, 'is_dhcp_enabled', False),
                            'allocation_pools': getattr(subnet, 'allocation_pools', []),
                            'dns_nameservers': getattr(subnet, 'dns_nameservers', []),
                            'host_routes': getattr(subnet, 'host_routes', []),
                            'created_at': str(getattr(subnet, 'created_at', 'unknown')),
                            'updated_at': str(getattr(subnet, 'updated_at', 'unknown'))
                        }
                    }
            
            return {
                'success': False,
                'message': f'Subnet "{subnet_name}" not found'
            }
            
        elif action.lower() == 'create':
            network_id = kwargs.get('network_id')
            cidr = kwargs.get('cidr')
            name = kwargs.get('name', subnet_name)
            
            if not network_id:
                return {
                    'success': False,
                    'message': 'network_id is required for create action'
                }
                
            if not cidr:
                return {
                    'success': False,
                    'message': 'cidr is required for create action'
                }
            
            create_params = {
                'network_id': network_id,
                'cidr': cidr,
                'ip_version': kwargs.get('ip_version', 4)
            }
            
            if name:
                create_params['name'] = name
            if kwargs.get('description'):
                create_params['description'] = kwargs['description']
            if 'gateway_ip' in kwargs:
                create_params['gateway_ip'] = kwargs['gateway_ip']
            if 'enable_dhcp' in kwargs:
                create_params['is_dhcp_enabled'] = kwargs['enable_dhcp']
            if 'dns_nameservers' in kwargs:
                create_params['dns_nameservers'] = kwargs['dns_nameservers']
            if 'allocation_pools' in kwargs:
                create_params['allocation_pools'] = kwargs['allocation_pools']
            
            subnet = conn.network.create_subnet(**create_params)
            
            return {
                'success': True,
                'message': f'Subnet "{name or subnet.id}" created successfully',
                'subnet': {
                    'id': subnet.id,
                    'name': getattr(subnet, 'name', 'unnamed'),
                    'network_id': getattr(subnet, 'network_id', 'unknown'),
                    'cidr': getattr(subnet, 'cidr', 'unknown'),
                    'gateway_ip': getattr(subnet, 'gateway_ip', None)
                }
            }
            
        elif action.lower() == 'delete':
            if not subnet_name:
                return {
                    'success': False,
                    'message': 'subnet_name is required for delete action'
                }
            
            # Find the subnet using secure project-scoped lookup
            from ..connection import find_resource_by_name_or_id
            
            subnet = find_resource_by_name_or_id(
                conn.network.subnets(), 
                subnet_name, 
                "Subnet"
            )
            
            if not subnet:
                return {
                    'success': False,
                    'message': f'Subnet "{subnet_name}" not found or not accessible in current project'
                }
            
            conn.network.delete_subnet(subnet)
            return {
                'success': True,
                'message': f'Subnet "{subnet_name}" deleted successfully'
            }
            
        else:
            return {
                'success': False,
                'message': f'Unknown action "{action}". Supported: list, show, create, delete'
            }
            
    except Exception as e:
        logger.error(f"Failed to manage subnet: {e}")
        return {
            'success': False,
            'message': f'Failed to manage subnet: {str(e)}',
            'error': str(e)
        }

QOS_RULE_FIELDS = {
    'bandwidth_limit': {'max_kbps', 'max_burst_kbps', 'direction'},
    'dscp_marking': {'dscp_mark'},
    'minimum_bandwidth': {'min_kbps', 'direction'},
    'packet_rate_limit': {'max_kpps', 'max_burst_kpps', 'direction'},
    'minimum_packet_rate': {'min_kpps', 'direction'},
}
QOS_TARGET_TYPES = {'port', 'network', 'floating_ip', 'router'}
SHARED_POLICY_WARNING = (
    'This policy is shared with all projects; rule changes apply immediately '
    'to every port, network, floating IP and router gateway that uses it, '
    'including resources in other projects that this tool cannot list.'
)


def _match_one(resources, name_or_id: str, label: str):
    """Return the single resource matching an ID, else a unique name."""
    matches = [r for r in resources if r.id == name_or_id]
    if not matches:
        matches = [r for r in resources if r.name == name_or_id]
    if len(matches) != 1:
        raise ValueError(f'{label} not found or name is ambiguous; use an ID')
    return matches[0]


def _find_qos_target(conn: Any, target_type: str, target: str, project_id: str):
    """Find a project-owned port, network, floating IP or router."""
    if target_type == 'floating_ip':
        ips = [ip for ip in conn.network.ips(project_id=project_id)
               if ip.project_id == project_id]
        matches = [ip for ip in ips if target in (ip.id, ip.floating_ip_address)]
        if len(matches) != 1:
            raise ValueError('Floating IP not found in the current project')
        return matches[0]
    listing = {
        'port': conn.network.ports, 'network': conn.network.networks,
        'router': conn.network.routers,
    }[target_type]
    resources = [r for r in listing(project_id=project_id)
                 if r.project_id == project_id]
    return _match_one(resources, target, target_type.capitalize())


def _target_qos_policy_id(conn: Any, target_type: str, target_id: str):
    """Read back the QoS policy ID currently set on a target."""
    if target_type == 'router':
        gateway = conn.network.get_router(target_id).external_gateway_info or {}
        return gateway.get('qos_policy_id')
    getter = {
        'port': conn.network.get_port, 'network': conn.network.get_network,
        'floating_ip': conn.network.get_ip,
    }[target_type]
    return getter(target_id).qos_policy_id


def _set_target_qos_policy(conn: Any, target_type: str, resource: Any,
                           policy_id: Optional[str]) -> None:
    """Set or clear a target's QoS policy; None clears it."""
    if target_type == 'router':
        gateway = resource.external_gateway_info or {}
        if not gateway.get('network_id'):
            raise ValueError('Router has no external gateway')
        # Send only network_id and qos_policy_id, as `openstack router set
        # --qos-policy` does; fixed IPs and SNAT stay unchanged.
        conn.network.update_router(resource, external_gateway_info={
            'network_id': gateway['network_id'], 'qos_policy_id': policy_id,
        })
        return
    updater = {
        'port': conn.network.update_port, 'network': conn.network.update_network,
        'floating_ip': conn.network.update_ip,
    }[target_type]
    updater(resource, qos_policy_id=policy_id)


def _qos_policy_groups(conn: Any, project_id: str):
    """Return (project-owned, shared-from-other-projects) QoS policies."""
    owned = [p for p in conn.network.qos_policies(project_id=project_id)
             if p.project_id == project_id]
    foreign_shared = [p for p in conn.network.qos_policies(is_shared=True)
                      if p.is_shared and p.project_id != project_id]
    return owned, foreign_shared


def find_usable_qos_policy(conn: Any, name_or_id: str):
    """Find a QoS policy owned by or shared with the current project."""
    project_id = conn.current_project_id
    if not project_id:
        raise ValueError('A project-scoped connection is required')
    owned, foreign_shared = _qos_policy_groups(conn, project_id)
    return _match_one(owned + foreign_shared, name_or_id, 'QoS policy')


def _validated_rule_values(rule_type: str, values: Any) -> Dict[str, Any]:
    """Reject rule fields that the rule type does not define."""
    if not isinstance(values, dict) or not values:
        raise ValueError('rule must be a non-empty JSON object')
    unknown = set(values) - QOS_RULE_FIELDS[rule_type]
    if unknown:
        raise ValueError(
            f'Unsupported fields for {rule_type}: {", ".join(sorted(unknown))}; '
            f'allowed: {", ".join(sorted(QOS_RULE_FIELDS[rule_type]))}')
    return values


def _policy_result(conn: Any, policy: Any, project_id: str) -> Dict[str, Any]:
    """Return the policy re-read from Neutron with ownership and share flags."""
    current = conn.network.get_qos_policy(policy.id)
    result: Dict[str, Any] = {
        'success': True, 'policy': current.to_dict(),
        'owned': current.project_id == project_id,
    }
    if current.is_shared:
        result['warning'] = SHARED_POLICY_WARNING
    return result


def set_network_qos_policies(
    action: str, policy_name: Optional[str] = None, **kwargs
) -> Dict[str, Any]:
    """Manage Neutron QoS policies, their rules and their attachments.

    Policies and rules are changed only when owned by the current project.
    associate/disassociate also accept policies shared with this project and
    change only project-owned ports, networks, floating IPs and routers.
    """
    from ..connection import get_openstack_connection

    try:
        action = action.lower()
        actions = {
            'list', 'show', 'create', 'update', 'delete', 'add_rule',
            'update_rule', 'delete_rule', 'associate', 'disassociate',
        }
        if action not in actions:
            raise ValueError(f'Supported actions: {", ".join(sorted(actions))}')
        if action != 'list' and not (policy_name and policy_name.strip()):
            raise ValueError('policy_name is required')
        conn = get_openstack_connection()
        project_id = conn.current_project_id
        if not project_id:
            raise ValueError('A project-scoped connection is required')
        shared = kwargs.get('shared')
        if action == 'create':
            policy = conn.network.create_qos_policy(
                name=policy_name, project_id=project_id,
                description=kwargs.get('description') or '',
                is_shared=bool(shared),
            )
            result = {'success': True, 'policy': policy.to_dict()}
            if policy.is_shared:
                result['warning'] = SHARED_POLICY_WARNING
            return result
        owned, foreign_shared = _qos_policy_groups(conn, project_id)
        if action == 'list':
            return {
                'success': True, 'policies': [p.to_dict() for p in owned],
                'count': len(owned),
                'shared_from_other_projects': [
                    p.to_dict() for p in foreign_shared],
            }
        usable = owned + foreign_shared
        if action in {'show', 'associate', 'disassociate'}:
            policy = _match_one(usable, policy_name, 'Policy')
        else:
            policy = _match_one(owned, policy_name, 'Project-owned policy')

        if action == 'show':
            return _policy_result(conn, policy, project_id)
        if action == 'delete':
            conn.network.delete_qos_policy(policy, ignore_missing=False)
            return {'success': True, 'message': 'QoS policy deletion accepted'}
        if action == 'update':
            changes: Dict[str, Any] = {}
            for key in ('new_name', 'description'):
                if kwargs.get(key) is not None:
                    changes['name' if key == 'new_name' else key] = kwargs[key]
            if shared is not None:
                changes['is_shared'] = shared
            if not changes:
                raise ValueError('Provide new_name, description or shared')
            conn.network.update_qos_policy(policy, **changes)
            return _policy_result(conn, policy, project_id)

        if action in {'add_rule', 'update_rule', 'delete_rule'}:
            rule_type = kwargs.get('rule_type') or ''
            rule_id = kwargs.get('rule_id') or ''
            if action == 'add_rule':
                if rule_type not in QOS_RULE_FIELDS:
                    raise ValueError(
                        'rule_type must be one of: '
                        + ', '.join(sorted(QOS_RULE_FIELDS)))
            else:
                if not rule_id:
                    raise ValueError(f'rule_id is required for {action}')
                existing = [r for r in (policy.rules or [])
                            if r.get('id') == rule_id]
                if len(existing) != 1:
                    raise ValueError('Rule not found in this policy')
                rule_type = existing[0]['type']
            method = f'qos_{rule_type}_rule'
            if action == 'add_rule':
                values = _validated_rule_values(rule_type, kwargs.get('rule'))
                getattr(conn.network, 'create_' + method)(policy, **values)
            elif action == 'update_rule':
                values = _validated_rule_values(rule_type, kwargs.get('rule'))
                getattr(conn.network, 'update_' + method)(
                    rule_id, policy, **values)
            else:
                getattr(conn.network, 'delete_' + method)(
                    rule_id, policy, ignore_missing=False)
            return _policy_result(conn, policy, project_id)

        target_type = kwargs.get('target_type') or ''
        target = kwargs.get('target') or ''
        if target_type not in QOS_TARGET_TYPES:
            raise ValueError(
                'target_type must be one of: ' + ', '.join(sorted(QOS_TARGET_TYPES)))
        if not target.strip():
            raise ValueError(f'target is required for {action}')
        resource = _find_qos_target(conn, target_type, target.strip(), project_id)
        current_id = _target_qos_policy_id(conn, target_type, resource.id)
        if action == 'disassociate' and current_id != policy.id:
            raise ValueError(
                f'{target_type} {resource.id} does not use policy {policy.id}; '
                f'its current QoS policy is {current_id}')
        new_id = policy.id if action == 'associate' else None
        _set_target_qos_policy(conn, target_type, resource, new_id)
        applied_id = _target_qos_policy_id(conn, target_type, resource.id)
        confirmed = applied_id == new_id
        return {
            'success': confirmed, 'accepted': True, 'confirmed': confirmed,
            'message': f'QoS {action} '
                       + ('confirmed' if confirmed else 'not confirmed by read-back'),
            'policy_id': policy.id, 'target_type': target_type,
            'target_id': resource.id, 'previous_qos_policy_id': current_id,
            'qos_policy_id': applied_id,
        }
    except Exception as exc:
        return {'success': False, 'message': 'Network QoS operation failed',
                'error': str(exc)}


def set_network_agents(
    action: str, agent_id: Optional[str] = None, **kwargs
) -> Dict[str, Any]:
    """List or change Neutron agent administrative state; cloud-wide/admin API."""
    from ..connection import get_openstack_connection

    try:
        action = action.lower()
        if action not in {'list', 'enable', 'disable'}:
            raise ValueError('Supported actions: list, enable, disable')
        if action != 'list' and not agent_id:
            raise ValueError('agent_id is required')
        conn = get_openstack_connection()
        if action == 'list':
            agents = [a.to_dict() for a in conn.network.agents()]
            return {'success': True, 'agents': agents, 'count': len(agents)}
        agent = conn.network.update_agent(
            agent_id, is_admin_state_up=action == 'enable',
        )
        return {'success': True, 'agent': agent.to_dict()}
    except Exception as exc:
        return {'success': False, 'message': 'Network agent operation failed',
                'error': str(exc)}


def _find_owned_network_resource(resources, name_or_id: str, project_id: str):
    """Reject missing/ambiguous matches and resources owned by another project."""
    if not project_id:
        raise ValueError('A project-scoped connection is required')
    resources = [r for r in resources if r.project_id == project_id]
    matches = [r for r in resources if r.id == name_or_id]
    if not matches:
        matches = [r for r in resources if r.name == name_or_id]
    if len(matches) != 1:
        raise ValueError('Resource not found or name is ambiguous; use an ID')
    return matches[0]


def set_routers(
    action: str, router_name: str, description: str = ''
) -> Dict[str, Any]:
    """Create or delete a project-owned router without changing interfaces."""
    from ..connection import get_openstack_connection

    try:
        if action.lower() not in {'create', 'delete'} or not router_name.strip():
            raise ValueError('Use create/delete and provide router_name')
        conn = get_openstack_connection()
        if action.lower() == 'create':
            router = conn.network.create_router(name=router_name,
                description=description)
            return {'success': True, 'router': router.to_dict()}
        router = _find_owned_network_resource(
            conn.network.routers(), router_name, conn.current_project_id,
        )
        conn.network.delete_router(router, ignore_missing=False)
        return {'success': True, 'message': 'Router deletion accepted'}
    except Exception as exc:
        return {'success': False, 'message': 'Router operation failed',
            'error': str(exc)}


def set_security_groups(
    action: str, group_name: str, description: str = ''
) -> Dict[str, Any]:
    """Create or delete a project-owned Neutron security group."""
    from ..connection import get_openstack_connection

    try:
        if action.lower() not in {'create', 'delete'} or not group_name.strip():
            raise ValueError('Use create/delete and provide group_name')
        conn = get_openstack_connection()
        if action.lower() == 'create':
            group = conn.network.create_security_group(name=group_name,
                description=description)
            return {'success': True, 'security_group': group.to_dict()}
        group = _find_owned_network_resource(
            conn.network.security_groups(), group_name, conn.current_project_id,
        )
        conn.network.delete_security_group(group, ignore_missing=False)
        return {'success': True, 'message': 'Security group deletion accepted'}
    except Exception as exc:
        return {'success': False, 'message': 'Security group operation failed',
            'error': str(exc)}


def set_security_group_rules(
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
) -> Dict[str, Any]:
    """Create or delete a rule on a project-owned security group."""
    from ..connection import get_openstack_connection

    try:
        action = action.strip().lower()
        if action not in {'create', 'delete'}:
            raise ValueError('Supported actions: create, delete')
        if not security_group.strip():
            raise ValueError('security_group is required')

        conn = get_openstack_connection()
        project_id = conn.current_project_id
        groups = list(conn.network.security_groups())
        group = _find_owned_network_resource(
            groups, security_group.strip(), project_id,
        )

        if action == 'delete':
            if not rule_id.strip():
                raise ValueError('rule_id is required for delete')
            rules = conn.network.security_group_rules(
                security_group_id=group.id,
            )
            matches = [
                rule for rule in rules
                if rule.id == rule_id.strip()
                and getattr(rule, 'security_group_id', None) == group.id
                and (
                    getattr(rule, 'project_id', None)
                    or getattr(rule, 'tenant_id', None)
                ) == project_id
            ]
            if len(matches) != 1:
                raise ValueError(
                    'Rule not found in the selected project-owned security group'
                )
            conn.network.delete_security_group_rule(
                matches[0], ignore_missing=False,
            )
            return {
                'success': True,
                'message': 'Security group rule deletion accepted',
            }

        direction = direction.strip().lower()
        if direction not in {'ingress', 'egress'}:
            raise ValueError('direction must be ingress or egress')

        ether_types = {'ipv4': 'IPv4', 'ipv6': 'IPv6'}
        normalized_ether_type = ether_types.get(ether_type.strip().lower())
        if normalized_ether_type is None:
            raise ValueError('ether_type must be IPv4 or IPv6')

        protocol = protocol.strip().lower()
        named_protocols = {
            'ah', 'dccp', 'egp', 'esp', 'gre', 'icmp', 'igmp',
            'ipv6-encap', 'ipv6-frag', 'ipv6-icmp', 'ipv6-nonxt',
            'ipv6-opts', 'ipv6-route', 'ospf', 'pgm', 'rsvp', 'sctp',
            'tcp', 'udp', 'udplite', 'vrrp',
        }
        if protocol in {'any', 'all'}:
            normalized_protocol = None
        elif protocol.isdigit() and 0 <= int(protocol) <= 255:
            normalized_protocol = protocol
        elif protocol in named_protocols:
            normalized_protocol = protocol
        else:
            raise ValueError(
                'protocol must be any, a supported protocol name, or 0-255'
            )
        if protocol == 'icmp' and normalized_ether_type != 'IPv4':
            raise ValueError('icmp requires ether_type IPv4')
        if protocol == 'ipv6-icmp' and normalized_ether_type != 'IPv6':
            raise ValueError('ipv6-icmp requires ether_type IPv6')

        remote_ip_prefix = remote_ip_prefix.strip()
        remote_group = remote_group.strip()
        if bool(remote_ip_prefix) == bool(remote_group):
            raise ValueError(
                'Provide exactly one of remote_ip_prefix or remote_group'
            )

        attrs: Dict[str, Any] = {
            'security_group_id': group.id,
            'direction': direction,
            'protocol': normalized_protocol,
            'ether_type': normalized_ether_type,
            'description': description,
        }
        if remote_ip_prefix:
            prefix = ip_network(remote_ip_prefix, strict=True)
            expected_version = 4 if normalized_ether_type == 'IPv4' else 6
            if prefix.version != expected_version:
                raise ValueError(
                    'remote_ip_prefix IP version must match ether_type'
                )
            attrs['remote_ip_prefix'] = str(prefix)
        else:
            remote = _find_owned_network_resource(
                groups, remote_group, project_id,
            )
            attrs['remote_group_id'] = remote.id

        if port_range_min is not None or port_range_max is not None:
            if normalized_protocol is None:
                raise ValueError('Port ranges cannot be used with protocol any')
            if port_range_min is None:
                port_range_min = port_range_max
            if port_range_max is None:
                port_range_max = port_range_min
            port_protocols = {'tcp', 'udp', 'sctp', 'dccp', 'udplite'}
            icmp_protocols = {'icmp', 'ipv6-icmp'}
            if protocol not in port_protocols | icmp_protocols:
                raise ValueError(
                    'Port ranges require a port-based or ICMP protocol name'
                )
            minimum = 0 if protocol in icmp_protocols else 1
            maximum = 255 if protocol in icmp_protocols else 65535
            if not (
                minimum <= port_range_min <= port_range_max <= maximum
            ):
                raise ValueError(
                    f'Port range must be {minimum}-{maximum} and ordered'
                )
            attrs['port_range_min'] = port_range_min
            attrs['port_range_max'] = port_range_max

        rule = conn.network.create_security_group_rule(**attrs)
        return {'success': True, 'security_group_rule': rule.to_dict()}
    except Exception as exc:
        return {
            'success': False,
            'message': 'Security group rule operation failed',
            'error': str(exc),
        }
