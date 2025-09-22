"""
OpenStack Network (Neutron) Service Functions

This module contains functions for managing networks, subnets, routers,
security groups, floating IPs, and other networking components.
"""

import logging
from typing import Dict, List, Any, Optional

# Configure logging
logger = logging.getLogger(__name__)


def get_network_details(network_name: str = "all") -> List[Dict[str, Any]]:
    """
    Get detailed information about networks in current project.
    
    Args:
        network_name: Name of specific network or "all" for all networks
    
    Returns:
        List of network dictionaries with detailed information for current project
    """
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
                if (validate_resource_ownership(network, "Network") or 
                    getattr(network, 'is_shared', False) or 
                    getattr(network, 'is_router_external', False)):  # Include shared and external networks
                    
                    # Get subnets for this network with project validation
                    subnets = []
                    for subnet in conn.network.subnets():
                        if getattr(subnet, 'network_id', None) == network.id:
                            # Enhanced validation using utility functions
                            if validate_resource_ownership(subnet, "Subnet"):
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
                        'status': getattr(network, 'status', 'unknown'),
                        'admin_state_up': getattr(network, 'is_admin_state_up', True),
                        'shared': getattr(network, 'is_shared', False),
                        'external': getattr(network, 'is_router_external', False),
                        'provider_network_type': getattr(network, 'provider_network_type', None),
                        'provider_physical_network': getattr(network, 'provider_physical_network', None),
                        'provider_segmentation_id': getattr(network, 'provider_segmentation_id', None),
                        'mtu': getattr(network, 'mtu', 1500),
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
                        for subnet in conn.network.subnets():
                            if getattr(subnet, 'network_id', None) == network.id:
                                subnet_project = getattr(subnet, 'project_id', None) or getattr(subnet, 'tenant_id', None)
                                if subnet_project == current_project_id:
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
                            'status': getattr(network, 'status', 'unknown'),
                            'admin_state_up': getattr(network, 'is_admin_state_up', True),
                            'shared': getattr(network, 'is_shared', False),
                            'external': getattr(network, 'is_router_external', False),
                            'provider_network_type': getattr(network, 'provider_network_type', None),
                            'provider_physical_network': getattr(network, 'provider_physical_network', None),
                            'provider_segmentation_id': getattr(network, 'provider_segmentation_id', None),
                            'mtu': getattr(network, 'mtu', 1500),
                            'tenant_id': getattr(network, 'tenant_id', 'unknown'),
                            'project_id': network_project,
                            'created_at': str(getattr(network, 'created_at', 'unknown')),
                            'updated_at': str(getattr(network, 'updated_at', 'unknown')),
                            'subnets': subnets,
                            'subnet_count': len(subnets)
                        })
                        break
        
        return networks
        
    except Exception as e:
        logger.error(f"Failed to get network details: {e}")
        return [
            {
                'id': 'net-1', 'name': 'demo-network', 'status': 'ACTIVE',
                'admin_state_up': True, 'shared': False, 'external': False,
                'subnets': [], 'error': str(e)
            }
        ]


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


def get_security_groups() -> List[Dict[str, Any]]:
    """
    Get list of security groups with rules for current project.
    
    Returns:
        List of security group dictionaries for current project
    """
    try:
        # Import here to avoid circular imports
        from ..connection import get_openstack_connection
        conn = get_openstack_connection()
        current_project_id = conn.current_project_id
        security_groups = []
        
        for sg in conn.network.security_groups():
            # Filter by current project
            sg_project_id = getattr(sg, 'project_id', None) or getattr(sg, 'tenant_id', None)
            if sg_project_id == current_project_id:
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
                        'ethertype': rule.get('ethertype', 'IPv4')
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
        
        logger.info(f"Retrieved {len(security_groups)} security groups for project {current_project_id}")
        return security_groups
    except Exception as e:
        logger.error(f"Failed to get security groups: {e}")
        return [
            {
                'id': 'default-sg', 'name': 'default', 'description': 'Default security group',
                'rules': [{'direction': 'ingress', 'protocol': 'tcp', 'port_range_min': 22, 'port_range_max': 22}],
                'error': str(e)
            }
        ]


def get_floating_ips() -> List[Dict[str, Any]]:
    """
    Get list of floating IPs for current project.
    
    Returns:
        List of floating IP dictionaries for current project
    """
    try:
        # Import here to avoid circular imports
        from ..connection import get_openstack_connection
        conn = get_openstack_connection()
        current_project_id = conn.current_project_id
        floating_ips = []
        
        for fip in conn.network.ips():
            # Filter by current project
            fip_project_id = getattr(fip, 'project_id', None) or getattr(fip, 'tenant_id', None)
            if fip_project_id == current_project_id:
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
                    'created_at': str(getattr(fip, 'created_at', 'unknown')),
                    'updated_at': str(getattr(fip, 'updated_at', 'unknown')),
                    'description': getattr(fip, 'description', '')
                })
        
        logger.info(f"Retrieved {len(floating_ips)} floating IPs for project {current_project_id}")
        return floating_ips
    except Exception as e:
        logger.error(f"Failed to get floating IPs: {e}")
        return [
            {
                'id': 'fip-1', 'floating_ip_address': '192.168.1.100',
                'fixed_ip_address': None, 'status': 'DOWN', 'error': str(e)
            }
        ]


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
            
            fip = conn.network.create_ip(**create_params)
            
            return {
                'success': True,
                'message': f'Floating IP allocated successfully',
                'floating_ip': {
                    'id': fip.id,
                    'floating_ip_address': getattr(fip, 'floating_ip_address', 'unknown'),
                    'status': getattr(fip, 'status', 'unknown'),
                    'floating_network_id': getattr(fip, 'floating_network_id', 'unknown')
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
                            # Simple IP range calculation (this could be more sophisticated)
                            total_ips += 100  # Placeholder calculation
                
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
                    'available_ips': total_ips - used_ips,
                    'admin_state_up': getattr(network, 'is_admin_state_up', True)
                })
        
        return pools
    except Exception as e:
        logger.error(f"Failed to get floating IP pools: {e}")
        return [{
            'id': 'pool-error',
            'name': 'Error retrieving pools',
            'error': str(e)
        }]


def set_floating_ip_port_forwarding(action: str, **kwargs) -> Dict[str, Any]:
    """
    Manage floating IP port forwarding rules.
    
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
        
        if action.lower() == 'list':
            floating_ip_id = kwargs.get('floating_ip_id')
            floating_ip_address = kwargs.get('floating_ip_address')
            
            if not floating_ip_id and not floating_ip_address:
                return {
                    'success': False,
                    'message': 'floating_ip_id or floating_ip_address is required for list action'
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
            
            # Get port forwarding rules for this floating IP
            port_forwardings = []
            try:
                for pf in conn.network.port_forwardings(floatingip=fip.id):
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
                # Return empty list if port forwarding is not supported
                
            return {
                'success': True,
                'floating_ip_id': fip.id,
                'floating_ip_address': getattr(fip, 'floating_ip_address', 'unknown'),
                'port_forwardings': port_forwardings,
                'count': len(port_forwardings)
            }
            
        elif action.lower() == 'create':
            floating_ip_id = kwargs.get('floating_ip_id')
            floating_ip_address = kwargs.get('floating_ip_address')
            protocol = kwargs.get('protocol', 'tcp')
            external_port = kwargs.get('external_port')
            internal_port = kwargs.get('internal_port')
            internal_ip_address = kwargs.get('internal_ip_address')
            internal_port_id = kwargs.get('internal_port_id')
            description = kwargs.get('description', '')
            
            if not floating_ip_id and not floating_ip_address:
                return {
                    'success': False,
                    'message': 'floating_ip_id or floating_ip_address is required'
                }
                
            if not external_port or not internal_port:
                return {
                    'success': False,
                    'message': 'external_port and internal_port are required for create action'
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
                pf = conn.network.create_port_forwarding(floatingip=fip.id, **create_params)
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
                
        elif action.lower() == 'delete':
            floating_ip_id = kwargs.get('floating_ip_id')
            port_forwarding_id = kwargs.get('port_forwarding_id')
            
            if not floating_ip_id or not port_forwarding_id:
                return {
                    'success': False,
                    'message': 'floating_ip_id and port_forwarding_id are required for delete action'
                }
            
            try:
                conn.network.delete_port_forwarding(port_forwarding_id, floatingip=floating_ip_id)
                return {
                    'success': True,
                    'message': f'Port forwarding rule deleted successfully'
                }
            except Exception as e:
                return {
                    'success': False,
                    'message': f'Failed to delete port forwarding rule: {str(e)}'
                }
                
        elif action.lower() == 'show':
            floating_ip_id = kwargs.get('floating_ip_id')
            port_forwarding_id = kwargs.get('port_forwarding_id')
            
            if not floating_ip_id or not port_forwarding_id:
                return {
                    'success': False,
                    'message': 'floating_ip_id and port_forwarding_id are required for show action'
                }
            
            try:
                pf = conn.network.get_port_forwarding(port_forwarding_id, floatingip=floating_ip_id)
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
                        'created_at': str(getattr(pf, 'created_at', 'unknown')),
                        'updated_at': str(getattr(pf, 'updated_at', 'unknown'))
                    }
                }
            except Exception as e:
                return {
                    'success': False,
                    'message': f'Failed to get port forwarding rule: {str(e)}'
                }
                
        elif action.lower() == 'set':
            floating_ip_id = kwargs.get('floating_ip_id')
            port_forwarding_id = kwargs.get('port_forwarding_id')
            
            if not floating_ip_id or not port_forwarding_id:
                return {
                    'success': False,
                    'message': 'floating_ip_id and port_forwarding_id are required for set action'
                }
            
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
                    floatingip=floating_ip_id, 
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
        
        else:
            return {
                'success': False,
                'message': f'Unsupported action: {action}. Supported actions: create, delete, list, show, set'
            }
            
    except Exception as e:
        logger.error(f"Port forwarding management failed: {e}")
        return {
            'success': False,
            'message': f'Port forwarding management failed: {str(e)}'
        }


def get_routers() -> List[Dict[str, Any]]:
    """
    Get list of routers with detailed information for current project.
    
    Returns:
        List of router dictionaries for current project
    """
    try:
        # Import here to avoid circular imports
        from ..connection import get_openstack_connection
        conn = get_openstack_connection()
        current_project_id = conn.current_project_id
        routers = []
        
        for router in conn.network.routers():
            # Filter by current project
            router_project_id = getattr(router, 'project_id', None) or getattr(router, 'tenant_id', None)
            if router_project_id == current_project_id:
                # Get router interfaces (ports)
                interfaces = []
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
                
                routers.append({
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
                    'interfaces': interfaces,
                    'interface_count': len(interfaces)
                })
        
        logger.info(f"Retrieved {len(routers)} routers for project {current_project_id}")
        return routers
    except Exception as e:
        logger.error(f"Failed to get routers: {e}")
        return [
            {
                'id': 'router-1', 'name': 'demo-router', 'status': 'ACTIVE',
                'admin_state_up': True, 'interfaces': [], 'error': str(e)
            }
        ]


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
        
        if action.lower() == 'list':
            ports = []
            for port in conn.network.ports():
                ports.append({
                    'id': port.id,
                    'name': getattr(port, 'name', 'unnamed'),
                    'network_id': getattr(port, 'network_id', 'unknown'),
                    'status': getattr(port, 'status', 'unknown'),
                    'admin_state_up': getattr(port, 'is_admin_state_up', True),
                    'device_id': getattr(port, 'device_id', ''),
                    'device_owner': getattr(port, 'device_owner', ''),
                    'mac_address': getattr(port, 'mac_address', 'unknown'),
                    'fixed_ips': getattr(port, 'fixed_ips', []),
                    'security_groups': getattr(port, 'security_group_ids', [])
                })
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
            for port in conn.network.ports():
                if getattr(port, 'name', '') == port_name or port.id == port_name:
                    return {
                        'success': True,
                        'port': {
                            'id': port.id,
                            'name': getattr(port, 'name', 'unnamed'),
                            'network_id': getattr(port, 'network_id', 'unknown'),
                            'status': getattr(port, 'status', 'unknown'),
                            'admin_state_up': getattr(port, 'is_admin_state_up', True),
                            'device_id': getattr(port, 'device_id', ''),
                            'device_owner': getattr(port, 'device_owner', ''),
                            'mac_address': getattr(port, 'mac_address', 'unknown'),
                            'fixed_ips': getattr(port, 'fixed_ips', []),
                            'security_groups': getattr(port, 'security_group_ids', []),
                            'created_at': str(getattr(port, 'created_at', 'unknown')),
                            'updated_at': str(getattr(port, 'updated_at', 'unknown'))
                        }
                    }
            
            return {
                'success': False,
                'message': f'Port "{port_name}" not found'
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