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
            'message': f"Network management failed: {str(e)}"
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
            instance_id = kwargs.get('instance_id')
            port_id = kwargs.get('port_id')
            
            if not floating_ip_id:
                return {
                    'success': False,
                    'message': 'floating_ip_id is required for associate action'
                }
            
            if not instance_id and not port_id:
                return {
                    'success': False,
                    'message': 'instance_id or port_id is required for associate action'
                }
            
            if instance_id:
                fip = conn.network.get_ip(floating_ip_id)
                if not fip:
                    return {
                        'success': False,
                        'message': 'Floating IP not found'
                    }
                
                # Find the port for the instance
                for port in conn.network.ports():
                    if getattr(port, 'device_id', None) == instance_id:
                        port_id = port.id
                        break
            
            if not port_id:
                return {
                    'success': False,
                    'message': 'No port found for the given instance'
                }
            
            # Associate the floating IP with the port
            conn.network.add_floating_ip_to_port(floating_ip_id, port_id)
            
            return {
                'success': True,
                'message': f'Floating IP {floating_ip_address} associated with port {port_id}'
            }
            
        elif action.lower() == 'disassociate':
            floating_ip_id = kwargs.get('floating_ip_id', kwargs.get('id'))
            floating_ip_address = kwargs.get('floating_ip_address', kwargs.get('ip'))
            
            if not floating_ip_id:
                return {
                    'success': False,
                    'message': 'floating_ip_id is required for disassociate action'
                }
            
            # Disassociate the floating IP from the port
            conn.network.remove_floating_ip_from_port(floating_ip_id)
            
            return {
                'success': True,
                'message': f'Floating IP {floating_ip_address} disassociated'
            }
            
        else:
            return {
                'success': False,
                'message': f'Unknown action: {action}. Supported: allocate, release, associate, disassociate, list'
            }
    
    except Exception as e:
        logger.error(f"Floating IP management failed: {e}")
        return {
            'success': False,
            'message': f"Floating IP management failed: {str(e)}"
        }


def get_routers() -> List[Dict[str, Any]]:
    """
    Get list of routers for current project.
    
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
                routers.append({
                    'id': router.id,
                    'name': getattr(router, 'name', 'unnamed'),
                    'status': getattr(router, 'status', 'unknown'),
                    'admin_state_up': getattr(router, 'admin_state_up', True),
                    'external_gateway_info': getattr(router, 'external_gateway_info', None),
                    'tenant_id': getattr(router, 'tenant_id', 'unknown'),
                    'project_id': router_project_id,
                    'created_at': str(getattr(router, 'created_at', 'unknown')),
                    'updated_at': str(getattr(router, 'updated_at', 'unknown'))
                })
        
        logger.info(f"Retrieved {len(routers)} routers for project {current_project_id}")
        return routers
    except Exception as e:
        logger.error(f"Failed to get routers: {e}")
        return [
            {
                'id': 'router-1', 'name': 'router1', 'status': 'ACTIVE',
                'admin_state_up': True, 'error': str(e)
            }
        ]


def set_routers(action: str, router_name: Optional[str] = None, **kwargs) -> Dict[str, Any]:
    """
    Manage OpenStack routers.

    Args:
        action: Action to perform (list, show, create, set, delete, add_interface, remove_interface)
        router_name: Name or ID of router (for specific operations)
        **kwargs: Additional parameters

    Returns:
        Result of the router operation
    """
    try:
        from ..connection import get_openstack_connection
        conn = get_openstack_connection()

        if action.lower() == 'list':
            return {'success': True, 'routers': get_routers(), 'message': f'Retrieved {len(get_routers())} routers'}

        if action.lower() == 'show':
            routers = get_routers()
            for router in routers:
                if router['name'] == router_name or router['id'] == router_name:
                    return {'success': True, 'router': router, 'message': f'Found router {router_name}'}
            return {'success': False, 'message': f'Router {router_name} not found'}

        if action.lower() == 'create':
            create_params = {}
            create_params['name'] = kwargs.get('name', router_name)
            create_params['admin_state_up'] = kwargs.get('admin_state_up', True)
            if 'description' in kwargs:
                create_params['description'] = kwargs['description']
            if 'ha' in kwargs:
                create_params['ha'] = kwargs['ha']
            if 'distributed' in kwargs:
                create_params['distributed'] = kwargs['distributed']
            external_network_id = kwargs.get('external_network_id')
            if external_network_id:
                create_params['external_gateway_info'] = {'network_id': external_network_id, 'enable_snat': True}
                if 'gateway_ip' in kwargs:
                    create_params['external_gateway_info']['external_fixed_ips'] = [{'subnet_id': kwargs.get('subnet_id', ''), 'ip_address': kwargs['gateway_ip']}]
            router = conn.network.create_router(**create_params)
            return {'success': True, 'router': {'id': router.id, 'name': router.name, 'status': router.status}, 'message': f'Router {router.name} created'}

        if action.lower() == 'set':
            router = find_resource_by_name_or_id(conn.network.routers(), router_name, "Router")
            update_params = {}
            if 'name' in kwargs:
                update_params['name'] = kwargs['name']
            if 'description' in kwargs:
                update_params['description'] = kwargs['description']
            if 'admin_state_up' in kwargs:
                update_params['admin_state_up'] = kwargs['admin_state_up']
            if 'ha' in kwargs:
                update_params['ha'] = kwargs['ha']
            if 'distributed' in kwargs:
                update_params['distributed'] = kwargs['distributed']
            if 'external_network_id' in kwargs:
                update_params['external_gateway_info'] = {'network_id': kwargs['external_network_id'], 'enable_snat': True}
                if 'gateway_ip' in kwargs:
                    update_params['external_gateway_info']['external_fixed_ips'] = [{'subnet_id': kwargs.get('subnet_id', ''), 'ip_address': kwargs['gateway_ip']}]
            router = conn.network.update_router(router, **update_params)
            return {'success': True, 'router': {'id': router.id, 'name': router.name, 'status': router.status}, 'message': f'Router {router_name} updated'}

        if action.lower() == 'delete':
            router = find_resource_by_name_or_id(conn.network.routers(), router_name, "Router")
            conn.network.delete_router(router)
            return {'success': True, 'message': f'Router {router_name} deleted'}

        if action.lower() == 'add_interface':
            router = find_resource_by_name_or_id(conn.network.routers(), router_name, "Router")
            subnet_id = kwargs.get('subnet_id')
            if not subnet_id:
                return {'success': False, 'message': 'subnet_id is required for add_interface'}
            interface = conn.network.add_interface_to_router(router, subnet_id=subnet_id)
            return {'success': True, 'interface': {'id': interface.id, 'device_id': interface.device_id}, 'message': f'Interface added to router {router_name}'}

        if action.lower() == 'remove_interface':
            router = find_resource_by_name_or_id(conn.network.routers(), router_name, "Router")
            subnet_id = kwargs.get('subnet_id')
            if not subnet_id:
                return {'success': False, 'message': 'subnet_id is required for remove_interface'}
            conn.network.remove_interface_from_router(router, subnet_id=subnet_id)
            return {'success': True, 'message': f'Interface removed from router {router_name}'}

        return {'success': False, 'message': f'Unknown action: {action}'}
    except Exception as e:
        logger.error(f"Failed to set routers: {e}")
        return {'success': False, 'message': str(e)}


def set_network_ports(action: str, port_name: Optional[str] = None, **kwargs) -> Dict[str, Any]:
    """
    Manage network ports.
    
    Args:
        action: Action to perform (create, delete, update, list)
        port_name: Name or ID of the port
        **kwargs: Additional parameters
    
    Returns:
        Result of the port management operation
    """
    try:
        from ..connection import get_openstack_connection, find_resource_by_name_or_id
        conn = get_openstack_connection()
        
        if action.lower() == 'create':
            if not port_name or not port_name.strip():
                return {
                    'success': False,
                    'message': 'Port name is required for create action'
                }
            
            network_id = kwargs.get('network_id')
            if not network_id:
                return {
                    'success': False,
                    'message': 'network_id is required for port creation'
                }
            
            create_params = {
                'name': port_name,
                'network_id': network_id
            }
            
            if 'fixed_ips' in kwargs:
                create_params['fixed_ips'] = kwargs['fixed_ips']
            if 'security_groups' in kwargs:
                create_params['security_groups'] = kwargs['security_groups']
            if 'mac_address' in kwargs:
                create_params['mac_address'] = kwargs['mac_address']
            if 'device_id' in kwargs:
                create_params['device_id'] = kwargs['device_id']
            if 'device_owner' in kwargs:
                create_params['device_owner'] = kwargs['device_owner']
            
            port = conn.network.create_port(**create_params)
            return {
                'success': True,
                'message': f'Port "{port_name}" created successfully',
                'port': {
                    'id': port.id,
                    'name': port.name,
                    'status': port.status
                }
            }
            
        elif action.lower() == 'delete':
            if not port_name or not port_name.strip():
                return {
                    'success': False,
                    'message': 'Port name or ID is required for delete action'
                }
            
            port = find_resource_by_name_or_id(conn.network.ports(), port_name, "Port")
            if not port:
                return {
                    'success': False,
                    'message': f'Port "{port_name}" not found'
                }
            
            conn.network.delete_port(port)
            return {
                'success': True,
                'message': f'Port "{port_name}" deleted successfully'
            }
            
        elif action.lower() == 'update':
            if not port_name or not port_name.strip():
                return {
                    'success': False,
                    'message': 'Port name or ID is required for update action'
                }
            
            port = find_resource_by_name_or_id(conn.network.ports(), port_name, "Port")
            if not port:
                return {
                    'success': False,
                    'message': f'Port "{port_name}" not found'
                }
            
            update_params = {}
            if 'name' in kwargs:
                update_params['name'] = kwargs['name']
            if 'description' in kwargs:
                update_params['description'] = kwargs['description']
            if 'security_groups' in kwargs:
                update_params['security_groups'] = kwargs['security_groups']
            if 'device_id' in kwargs:
                update_params['device_id'] = kwargs['device_id']
            if 'device_owner' in kwargs:
                update_params['device_owner'] = kwargs['device_owner']
            
            if update_params:
                port = conn.network.update_port(port, **update_params)
                return {
                    'success': True,
                    'message': f'Port "{port_name}" updated successfully',
                    'port': {
                        'id': port.id,
                        'name': port.name,
                        'status': port.status
                    }
                }
            else:
                return {
                    'success': False,
                    'message': 'No update parameters provided'
                }
            
        elif action.lower() == 'list':
            ports = []
            for port in conn.network.ports():
                ports.append({
                    'id': port.id,
                    'name': getattr(port, 'name', 'unnamed'),
                    'status': getattr(port, 'status', 'unknown'),
                    'network_id': getattr(port, 'network_id', 'unknown'),
                    'device_id': getattr(port, 'device_id', None),
                    'device_owner': getattr(port, 'device_owner', None)
                })
            return {'success': True, 'ports': ports, 'count': len(ports)}
            
        else:
            return {
                'success': False,
                'message': f'Unsupported action: {action}. Supported actions: create, delete, update, list'
            }
    
    except Exception as e:
        logger.error(f"Port management failed: {e}")
        return {
            'success': False,
            'message': f"Port management failed: {str(e)}"
        }


def set_subnets(action: str, subnet_name: Optional[str] = None, **kwargs) -> Dict[str, Any]:
    """
    Manage subnets (create, delete, update, list).
    
    Args:
        action: Action to perform (create, delete, update, list)
        subnet_name: Name of the subnet (required for create/delete/update)
        **kwargs: Additional parameters
    
    Returns:
        Result of the subnet operation
    """
    try:
        from ..connection import get_openstack_connection, find_resource_by_name_or_id
        conn = get_openstack_connection()
        
        if action.lower() == 'create':
            if not subnet_name or not subnet_name.strip():
                return {
                    'success': False,
                    'message': 'Subnet name is required for create action'
                }
            
            network_id = kwargs.get('network_id')
            if not network_id:
                return {
                    'success': False,
                    'message': 'network_id is required for subnet creation'
                }
            
            cidr = kwargs.get('cidr')
            if not cidr:
                return {
                    'success': False,
                    'message': 'cidr is required for subnet creation'
                }
            
            ip_version = kwargs.get('ip_version', 4)
            
            create_params = {
                'name': subnet_name,
                'network_id': network_id,
                'cidr': cidr,
                'ip_version': ip_version
            }
            
            if 'gateway_ip' in kwargs:
                create_params['gateway_ip'] = kwargs['gateway_ip']
            if 'dns_nameservers' in kwargs:
                create_params['dns_nameservers'] = kwargs['dns_nameservers']
            if 'allocation_pools' in kwargs:
                create_params['allocation_pools'] = kwargs['allocation_pools']
            if 'enable_dhcp' in kwargs:
                create_params['enable_dhcp'] = kwargs['enable_dhcp']
            
            subnet = conn.network.create_subnet(**create_params)
            return {
                'success': True,
                'message': f'Subnet "{subnet_name}" created successfully',
                'subnet': {
                    'id': subnet.id,
                    'name': subnet.name,
                    'cidr': subnet.cidr,
                    'ip_version': subnet.ip_version
                }
            }
            
        elif action.lower() == 'delete':
            if not subnet_name or not subnet_name.strip():
                return {
                    'success': False,
                    'message': 'Subnet name or ID is required for delete action'
                }
            
            subnet = find_resource_by_name_or_id(conn.network.subnets(), subnet_name, "Subnet")
            if not subnet:
                return {
                    'success': False,
                    'message': f'Subnet "{subnet_name}" not found'
                }
            
            conn.network.delete_subnet(subnet)
            return {
                'success': True,
                'message': f'Subnet "{subnet_name}" deleted successfully'
            }
            
        elif action.lower() == 'update':
            if not subnet_name or not subnet_name.strip():
                return {
                    'success': False,
                    'message': 'Subnet name or ID is required for update action'
                }
            
            subnet = find_resource_by_name_or_id(conn.network.subnets(), subnet_name, "Subnet")
            if not subnet:
                return {
                    'success': False,
                    'message': f'Subnet "{subnet_name}" not found'
                }
            
            update_params = {}
            if 'name' in kwargs:
                update_params['name'] = kwargs['name']
            if 'gateway_ip' in kwargs:
                update_params['gateway_ip'] = kwargs['gateway_ip']
            if 'dns_nameservers' in kwargs:
                update_params['dns_nameservers'] = kwargs['dns_nameservers']
            if 'enable_dhcp' in kwargs:
                update_params['enable_dhcp'] = kwargs['enable_dhcp']
            
            if update_params:
                subnet = conn.network.update_subnet(subnet, **update_params)
                return {
                    'success': True,
                    'message': f'Subnet "{subnet_name}" updated successfully',
                    'subnet': {
                        'id': subnet.id,
                        'name': subnet.name,
                        'cidr': subnet.cidr
                    }
                }
            else:
                return {
                    'success': False,
                    'message': 'No update parameters provided'
                }
            
        elif action.lower() == 'list':
            subnets = []
            for subnet in conn.network.subnets():
                subnets.append({
                    'id': subnet.id,
                    'name': getattr(subnet, 'name', 'unnamed'),
                    'cidr': getattr(subnet, 'cidr', 'unknown'),
                    'ip_version': getattr(subnet, 'ip_version', 4),
                    'gateway_ip': getattr(subnet, 'gateway_ip', None),
                    'enable_dhcp': getattr(subnet, 'is_dhcp_enabled', False)
                })
            return {'success': True, 'subnets': subnets, 'count': len(subnets)}
            
        else:
            return {
                'success': False,
                'message': f'Unsupported action: {action}. Supported actions: create, delete, update, list'
            }
    
    except Exception as e:
        logger.error(f"Subnet management failed: {e}")
        return {
            'success': False,
            'message': f"Subnet management failed: {str(e)}"
        }


def set_network_ports(action: str, port_name: Optional[str] = None, **kwargs) -> Dict[str, Any]:
    """
    Manage network ports.
    
    Args:
        action: Action to perform (create, delete, update, list)
        port_name: Name or ID of the port
        **kwargs: Additional parameters
    
    Returns:
        Result of the port management operation
    """
    try:
        from ..connection import get_openstack_connection, find_resource_by_name_or_id
        conn = get_openstack_connection()
        
        if action.lower() == 'create':
            if not port_name or not port_name.strip():
                return {
                    'success': False,
                    'message': 'Port name is required for create action'
                }
            
            network_id = kwargs.get('network_id')
            if not network_id:
                return {
                    'success': False,
                    'message': 'network_id is required for port creation'
                }
            
            create_params = {
                'name': port_name,
                'network_id': network_id
            }
            
            if 'fixed_ips' in kwargs:
                create_params['fixed_ips'] = kwargs['fixed_ips']
            if 'security_groups' in kwargs:
                create_params['security_groups'] = kwargs['security_groups']
            if 'mac_address' in kwargs:
                create_params['mac_address'] = kwargs['mac_address']
            if 'device_id' in kwargs:
                create_params['device_id'] = kwargs['device_id']
            if 'device_owner' in kwargs:
                create_params['device_owner'] = kwargs['device_owner']
            
            port = conn.network.create_port(**create_params)
            return {
                'success': True,
                'message': f'Port "{port_name}" created successfully',
                'port': {
                    'id': port.id,
                    'name': port.name,
                    'status': port.status
                }
            }
            
        elif action.lower() == 'delete':
            if not port_name or not port_name.strip():
                return {
                    'success': False,
                    'message': 'Port name or ID is required for delete action'
                }
            
            port = find_resource_by_name_or_id(conn.network.ports(), port_name, "Port")
            if not port:
                return {
                    'success': False,
                    'message': f'Port "{port_name}" not found'
                }
            
            conn.network.delete_port(port)
            return {
                'success': True,
                'message': f'Port "{port_name}" deleted successfully'
            }
            
        elif action.lower() == 'update':
            if not port_name or not port_name.strip():
                return {
                    'success': False,
                    'message': 'Port name or ID is required for update action'
                }
            
            port = find_resource_by_name_or_id(conn.network.ports(), port_name, "Port")
            if not port:
                return {
                    'success': False,
                    'message': f'Port "{port_name}" not found'
                }
            
            update_params = {}
            if 'name' in kwargs:
                update_params['name'] = kwargs['name']
            if 'description' in kwargs:
                update_params['description'] = kwargs['description']
            if 'security_groups' in kwargs:
                update_params['security_groups'] = kwargs['security_groups']
            if 'device_id' in kwargs:
                update_params['device_id'] = kwargs['device_id']
            if 'device_owner' in kwargs:
                update_params['device_owner'] = kwargs['device_owner']
            
            if update_params:
                port = conn.network.update_port(port, **update_params)
                return {
                    'success': True,
                    'message': f'Port "{port_name}" updated successfully',
                    'port': {
                        'id': port.id,
                        'name': port.name,
                        'status': port.status
                    }
                }
            else:
                return {
                    'success': False,
                    'message': 'No update parameters provided'
                }
            
        elif action.lower() == 'list':
            ports = []
            for port in conn.network.ports():
                ports.append({
                    'id': port.id,
                    'name': getattr(port, 'name', 'unnamed'),
                    'status': getattr(port, 'status', 'unknown'),
                    'network_id': getattr(port, 'network_id', 'unknown'),
                    'device_id': getattr(port, 'device_id', None),
                    'device_owner': getattr(port, 'device_owner', None)
                })
            return {'success': True, 'ports': ports, 'count': len(ports)}
            
        else:
            return {
                'success': False,
                'message': f'Unsupported action: {action}. Supported actions: create, delete, update, list'
            }
    
    except Exception as e:
        logger.error(f"Port management failed: {e}")
        return {
            'success': False,
            'message': f"Port management failed: {str(e)}"
        }


def set_subnets(action: str, subnet_name: Optional[str] = None, **kwargs) -> Dict[str, Any]:
    """
    Manage subnets (create, delete, update, list).
    
    Args:
        action: Action to perform (create, delete, update, list)
        subnet_name: Name of the subnet (required for create/delete/update)
        **kwargs: Additional parameters
    
    Returns:
        Result of the subnet operation
    """
    try:
        from ..connection import get_openstack_connection, find_resource_by_name_or_id
        conn = get_openstack_connection()
        
        if action.lower() == 'create':
            if not subnet_name or not subnet_name.strip():
                return {
                    'success': False,
                    'message': 'Subnet name is required for create action'
                }
            
            network_id = kwargs.get('network_id')
            if not network_id:
                return {
                    'success': False,
                    'message': 'network_id is required for subnet creation'
                }
            
            cidr = kwargs.get('cidr')
            if not cidr:
                return {
                    'success': False,
                    'message': 'cidr is required for subnet creation'
                }
            
            ip_version = kwargs.get('ip_version', 4)
            
            create_params = {
                'name': subnet_name,
                'network_id': network_id,
                'cidr': cidr,
                'ip_version': ip_version
            }
            
            if 'gateway_ip' in kwargs:
                create_params['gateway_ip'] = kwargs['gateway_ip']
            if 'dns_nameservers' in kwargs:
                create_params['dns_nameservers'] = kwargs['dns_nameservers']
            if 'allocation_pools' in kwargs:
                create_params['allocation_pools'] = kwargs['allocation_pools']
            if 'enable_dhcp' in kwargs:
                create_params['enable_dhcp'] = kwargs['enable_dhcp']
            
            subnet = conn.network.create_subnet(**create_params)
            return {
                'success': True,
                'message': f'Subnet "{subnet_name}" created successfully',
                'subnet': {
                    'id': subnet.id,
                    'name': subnet.name,
                    'cidr': subnet.cidr,
                    'ip_version': subnet.ip_version
                }
            }
            
        elif action.lower() == 'delete':
            if not subnet_name or not subnet_name.strip():
                return {
                    'success': False,
                    'message': 'Subnet name or ID is required for delete action'
                }
            
            subnet = find_resource_by_name_or_id(conn.network.subnets(), subnet_name, "Subnet")
            if not subnet:
                return {
                    'success': False,
                    'message': f'Subnet "{subnet_name}" not found'
                }
            
            conn.network.delete_subnet(subnet)
            return {
                'success': True,
                'message': f'Subnet "{subnet_name}" deleted successfully'
            }
            
        elif action.lower() == 'update':
            if not subnet_name or not subnet_name.strip():
                return {
                    'success': False,
                    'message': 'Subnet name or ID is required for update action'
                }
            
            subnet = find_resource_by_name_or_id(conn.network.subnets(), subnet_name, "Subnet")
            if not subnet:
                return {
                    'success': False,
                    'message': f'Subnet "{subnet_name}" not found'
                }
            
            update_params = {}
            if 'name' in kwargs:
                update_params['name'] = kwargs['name']
            if 'gateway_ip' in kwargs:
                update_params['gateway_ip'] = kwargs['gateway_ip']
            if 'dns_nameservers' in kwargs:
                update_params['dns_nameservers'] = kwargs['dns_nameservers']
            if 'enable_dhcp' in kwargs:
                update_params['enable_dhcp'] = kwargs['enable_dhcp']
            
            if update_params:
                subnet = conn.network.update_subnet(subnet, **update_params)
                return {
                    'success': True,
                    'message': f'Subnet "{subnet_name}" updated successfully',
                    'subnet': {
                        'id': subnet.id,
                        'name': subnet.name,
                        'cidr': subnet.cidr
                    }
                }
            else:
                return {
                    'success': False,
                    'message': 'No update parameters provided'
                }
            
        elif action.lower() == 'list':
            subnets = []
            for subnet in conn.network.subnets():
                subnets.append({
                    'id': subnet.id,
                    'name': getattr(subnet, 'name', 'unnamed'),
                    'cidr': getattr(subnet, 'cidr', 'unknown'),
                    'ip_version': getattr(subnet, 'ip_version', 4),
                    'gateway_ip': getattr(subnet, 'gateway_ip', None),
                    'enable_dhcp': getattr(subnet, 'is_dhcp_enabled', False)
                })
            return {'success': True, 'subnets': subnets, 'count': len(subnets)}
            
        else:
            return {
                'success': False,
                'message': f'Unsupported action: {action}. Supported actions: create, delete, update, list'
            }
    
    except Exception as e:
        logger.error(f"Subnet management failed: {e}")
        return {
            'success': False,
            'message': f"Subnet management failed: {str(e)}"
        }


def get_subnets() -> List[Dict[str, Any]]:
    """
    Get list of subnets for current project.
    
    Returns:
        List of subnet dictionaries for current project
    """
    try:
        from ..connection import get_openstack_connection
        conn = get_openstack_connection()
        current_project_id = conn.current_project_id
        subnets = []
        
        for subnet in conn.network.subnets():
            subnet_project_id = getattr(subnet, 'project_id', None) or getattr(subnet, 'tenant_id', None)
            if subnet_project_id == current_project_id:
                subnets.append({
                    'id': subnet.id,
                    'name': getattr(subnet, 'name', 'unnamed'),
                    'cidr': getattr(subnet, 'cidr', 'unknown'),
                    'ip_version': getattr(subnet, 'ip_version', 4),
                    'gateway_ip': getattr(subnet, 'gateway_ip', None),
                    'enable_dhcp': getattr(subnet, 'is_dhcp_enabled', False)
                })
        
        logger.info(f"Retrieved {len(subnets)} subnets for project {current_project_id}")
        return subnets
    except Exception as e:
        logger.error(f"Failed to get subnets: {e}")
        return [
            {
                'id': 'subnet-1', 'name': 'subnet1', 'cidr': '10.0.0.0/24',
                'ip_version': 4, 'error': str(e)
            }
        ]