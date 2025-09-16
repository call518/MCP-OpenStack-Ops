import os
import logging
from typing import Dict, List, Any, Optional
from openstack import connection
from dotenv import load_dotenv
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global connection cache
_connection_cache = None

def get_openstack_connection():
    """
    Creates and caches OpenStack connection using proxy URLs for all services.
    Returns cached connection if available to improve performance.
    """
    global _connection_cache
    
    if _connection_cache is not None:
        try:
            # Test connection validity
            _connection_cache.identity.get_token()
            return _connection_cache
        except Exception as e:
            logger.warning(f"Cached connection invalid, creating new one: {e}")
            _connection_cache = None
    
    load_dotenv()
    
    proxy_host = os.environ.get("OS_PROXY_HOST", "192.168.35.2")
    
    try:
        _connection_cache = connection.Connection(
            auth_url=f"http://{proxy_host}:5555",
            project_name=os.environ.get("OS_PROJECT_NAME"),
            username=os.environ.get("OS_USERNAME"),
            password=os.environ.get("OS_PASSWORD"),
            user_domain_name=os.environ.get("OS_USER_DOMAIN_NAME", "Default"),
            project_domain_name=os.environ.get("OS_PROJECT_DOMAIN_NAME", "Default"),
            region_name=os.environ.get("OS_REGION_NAME", "RegionOne"),
            identity_api_version=os.environ.get("OS_IDENTITY_API_VERSION", "3"),
            interface="internal",
            # Override all service endpoints to use proxy
            identity_endpoint=f"http://{proxy_host}:5555",
            compute_endpoint=f"http://{proxy_host}:8774/v2.1",
            network_endpoint=f"http://{proxy_host}:9696",
            volume_endpoint=f"http://{proxy_host}:8776/v3",
            image_endpoint=f"http://{proxy_host}:9292",
            placement_endpoint=f"http://{proxy_host}:8780",
            timeout=10
        )
        return _connection_cache
    except Exception as e:
        logger.error(f"Failed to create OpenStack connection: {e}")
        raise


def get_cluster_status() -> Dict[str, Any]:
    """
    Returns a comprehensive summary of cluster status using OpenStack SDK.
    
    Returns:
        Dict containing cluster status information including instances, networks, 
        services, and connection status.
    """
    try:
        conn = get_openstack_connection()
        
        # Get basic cluster information with better error handling
        services = []
        instances = []
        networks = []
        
        try:
            services = [svc.name for svc in conn.identity.services()]
        except Exception as e:
            logger.warning(f"Failed to get services: {e}")
            
        try:
            instances = [server.name for server in conn.compute.servers()]
        except Exception as e:
            logger.warning(f"Failed to get instances: {e}")
            
        try:
            networks = [net.name for net in conn.network.networks()]
        except Exception as e:
            logger.warning(f"Failed to get networks: {e}")
        
        return {
            'instances': instances if instances else ['No instances found'],
            'networks': networks if networks else ['No networks found'],
            'services': services if services else ['No services accessible'],
            'connection_status': 'Connected via SDK',
            'timestamp': datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Unable to connect to OpenStack: {e}")
        return {
            'instances': ['Connection failed - using demo data'],
            'networks': ['public', 'private', 'external'],
            'services': ['nova', 'neutron', 'keystone'],
            'connection_status': f'Failed: {str(e)[:100]}...',
            'timestamp': datetime.now().isoformat(),
            'error': True
        }


def get_service_status() -> List[Dict[str, Any]]:
    """
    Returns detailed service status information for compute and network services.
    
    Returns:
        List of service status dictionaries with comprehensive information.
    """
    try:
        conn = get_openstack_connection()
        services = []
        
        # Get compute services
        try:
            for service in conn.compute.services():
                services.append({
                    'binary': service.binary,
                    'host': service.host,
                    'status': service.status,
                    'state': service.state,
                    'zone': getattr(service, 'zone', 'unknown'),
                    'updated_at': str(getattr(service, 'updated_at', 'unknown')),
                    'disabled_reason': getattr(service, 'disabled_reason', None),
                    'service_type': 'compute'
                })
        except Exception as e:
            logger.warning(f"Failed to get compute services: {e}")
            
        # Get network services if available
        try:
            for agent in conn.network.agents():
                services.append({
                    'binary': agent.binary,
                    'host': agent.host,
                    'status': 'enabled' if agent.is_admin_state_up else 'disabled',
                    'state': 'up' if agent.alive else 'down',
                    'zone': getattr(agent, 'availability_zone', 'unknown'),
                    'updated_at': str(getattr(agent, 'heartbeat_timestamp', 'unknown')),
                    'agent_type': agent.agent_type,
                    'service_type': 'network'
                })
        except Exception as e:
            logger.warning(f"Failed to get network agents: {e}")
            
        return services if services else [
            {'binary': 'nova-compute', 'host': 'controller', 'status': 'enabled', 'state': 'up', 'zone': 'nova', 'service_type': 'compute'},
            {'binary': 'neutron-server', 'host': 'controller', 'status': 'enabled', 'state': 'up', 'zone': 'internal', 'service_type': 'network'}
        ]
    except Exception as e:
        logger.error(f"Failed to get service status: {e}")
        return [
            {'binary': 'nova-compute', 'host': 'controller', 'status': 'enabled', 'state': 'up', 'zone': 'nova', 'service_type': 'compute', 'error': str(e)},
            {'binary': 'neutron-server', 'host': 'controller', 'status': 'enabled', 'state': 'up', 'zone': 'internal', 'service_type': 'network', 'error': str(e)}
        ]


def get_instance_details(instance_names: Optional[List[str]] = None, instance_ids: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """
    Returns detailed instance information with comprehensive server data.
    
    Args:
        instance_names: Optional list of instance names to filter by
        instance_ids: Optional list of instance IDs to filter by
        If both are None, returns all instances
    
    Returns:
        List of instance dictionaries with detailed server information.
    """
    try:
        conn = get_openstack_connection()
        instances = []
        
        # Determine which servers to query
        servers_to_process = []
        
        if instance_names or instance_ids:
            # Get specific instances
            all_servers = list(conn.compute.servers(detailed=True))
            
            for server in all_servers:
                should_include = False
                
                # Check if server name matches
                if instance_names and server.name in instance_names:
                    should_include = True
                
                # Check if server ID matches
                if instance_ids and server.id in instance_ids:
                    should_include = True
                
                if should_include:
                    servers_to_process.append(server)
        else:
            # Get all instances
            servers_to_process = list(conn.compute.servers(detailed=True))
        
        for server in servers_to_process:
            # Get flavor details
            flavor_name = 'unknown'
            if server.flavor:
                try:
                    flavor = conn.compute.get_flavor(server.flavor['id'])
                    flavor_name = f"{flavor.name} (vcpus: {flavor.vcpus}, ram: {flavor.ram}MB, disk: {flavor.disk}GB)"
                except Exception:
                    flavor_name = server.flavor.get('id', 'unknown')
            
            # Get image details
            image_name = 'unknown'
            if server.image:
                try:
                    image = conn.image.get_image(server.image['id'])
                    image_name = image.name
                except Exception:
                    image_name = server.image.get('id', 'unknown')
            
            # Get network information
            networks = []
            for network_name, addresses in getattr(server, 'addresses', {}).items():
                for addr in addresses:
                    networks.append({
                        'network': network_name,
                        'ip': addr.get('addr', 'unknown'),
                        'type': addr.get('OS-EXT-IPS:type', 'unknown'),
                        'mac': addr.get('OS-EXT-IPS-MAC:mac_addr', 'unknown')
                    })
            
            instances.append({
                'id': server.id,
                'name': server.name,
                'status': server.status,
                'power_state': getattr(server, 'power_state', 'unknown'),
                'vm_state': getattr(server, 'vm_state', 'unknown'),
                'task_state': getattr(server, 'task_state', None),
                'created': str(server.created_at) if hasattr(server, 'created_at') else 'unknown',
                'updated': str(server.updated_at) if hasattr(server, 'updated_at') else 'unknown',
                'flavor': flavor_name,
                'image': image_name,
                'host': getattr(server, 'OS-EXT-SRV-ATTR:host', 'unknown'),
                'hypervisor_hostname': getattr(server, 'OS-EXT-SRV-ATTR:hypervisor_hostname', 'unknown'),
                'availability_zone': getattr(server, 'OS-EXT-AZ:availability_zone', 'unknown'),
                'networks': networks,
                'metadata': getattr(server, 'metadata', {}),
                'security_groups': [sg.get('name', 'unknown') for sg in getattr(server, 'security_groups', [])],
                'key_name': getattr(server, 'key_name', None),
                'user_id': getattr(server, 'user_id', 'unknown'),
                'tenant_id': getattr(server, 'tenant_id', 'unknown')
            })
        
        return instances
    except Exception as e:
        logger.error(f"Failed to get instance details: {e}")
        return [
            {
                'id': 'demo-1', 'name': 'demo-instance-1', 'status': 'ACTIVE', 
                'power_state': '1', 'vm_state': 'active', 'task_state': None,
                'created': '2025-09-16T00:00:00Z', 'updated': '2025-09-16T00:00:00Z',
                'flavor': 'm1.small (vcpus: 1, ram: 2048MB, disk: 20GB)', 
                'image': 'ubuntu-20.04', 'host': 'compute-1',
                'hypervisor_hostname': 'compute-1', 'availability_zone': 'nova',
                'networks': [{'network': 'private', 'ip': '10.0.0.10', 'type': 'fixed', 'mac': '00:00:00:00:00:01'}],
                'metadata': {}, 'security_groups': ['default'], 
                'key_name': None, 'user_id': 'demo-user', 'tenant_id': 'demo-project',
                'error': str(e)
            }
        ]


def get_instance_by_name(instance_name: str) -> Optional[Dict[str, Any]]:
    """
    Get detailed information for a specific instance by name.
    
    Args:
        instance_name: Name of the instance to retrieve
        
    Returns:
        Instance dictionary with detailed information, or None if not found
    """
    instances = get_instance_details(instance_names=[instance_name])
    return instances[0] if instances else None


def get_instance_by_id(instance_id: str) -> Optional[Dict[str, Any]]:
    """
    Get detailed information for a specific instance by ID.
    
    Args:
        instance_id: ID of the instance to retrieve
        
    Returns:
        Instance dictionary with detailed information, or None if not found
    """
    instances = get_instance_details(instance_ids=[instance_id])
    return instances[0] if instances else None


def search_instances(search_term: str, search_in: str = 'name') -> List[Dict[str, Any]]:
    """
    Search for instances based on various criteria.
    
    Args:
        search_term: Term to search for
        search_in: Field to search in ('name', 'status', 'host', 'flavor', 'image', 'all')
        
    Returns:
        List of matching instance dictionaries
    """
    try:
        all_instances = get_instance_details()
        matching_instances = []
        
        search_term_lower = search_term.lower()
        
        for instance in all_instances:
            match_found = False
            
            if search_in == 'name' or search_in == 'all':
                if search_term_lower in instance.get('name', '').lower():
                    match_found = True
                    
            if search_in == 'status' or search_in == 'all':
                if search_term_lower in instance.get('status', '').lower():
                    match_found = True
                    
            if search_in == 'host' or search_in == 'all':
                if search_term_lower in instance.get('host', '').lower():
                    match_found = True
                    
            if search_in == 'flavor' or search_in == 'all':
                if search_term_lower in instance.get('flavor', '').lower():
                    match_found = True
                    
            if search_in == 'image' or search_in == 'all':
                if search_term_lower in instance.get('image', '').lower():
                    match_found = True
                    
            if search_in == 'availability_zone' or search_in == 'all':
                if search_term_lower in instance.get('availability_zone', '').lower():
                    match_found = True
            
            if match_found:
                matching_instances.append(instance)
        
        return matching_instances
        
    except Exception as e:
        logger.error(f"Failed to search instances: {e}")
        return []


def get_instances_by_status(status: str) -> List[Dict[str, Any]]:
    """
    Get instances filtered by status.
    
    Args:
        status: Instance status to filter by (ACTIVE, SHUTOFF, ERROR, etc.)
        
    Returns:
        List of instances with the specified status
    """
    return search_instances(status, 'status')


def get_network_details() -> List[Dict[str, Any]]:
    """
    Returns detailed network information with comprehensive network data.
    
    Returns:
        List of network dictionaries with detailed information.
    """
    try:
        conn = get_openstack_connection()
        networks = []
        
        for network in conn.network.networks():
            # Get subnet details
            subnets = []
            for subnet_id in getattr(network, 'subnet_ids', []):
                try:
                    subnet = conn.network.get_subnet(subnet_id)
                    subnets.append({
                        'id': subnet.id,
                        'name': subnet.name,
                        'cidr': subnet.cidr,
                        'gateway_ip': subnet.gateway_ip,
                        'enable_dhcp': subnet.is_dhcp_enabled,
                        'ip_version': subnet.ip_version,
                        'allocation_pools': subnet.allocation_pools
                    })
                except Exception as e:
                    logger.warning(f"Failed to get subnet {subnet_id}: {e}")
                    subnets.append({'id': subnet_id, 'error': str(e)})
            
            networks.append({
                'id': network.id,
                'name': network.name,
                'status': network.status,
                'admin_state_up': network.is_admin_state_up,
                'shared': network.is_shared,
                'external': getattr(network, 'is_router_external', False),
                'provider_network_type': getattr(network, 'provider:network_type', None),
                'provider_physical_network': getattr(network, 'provider:physical_network', None),
                'provider_segmentation_id': getattr(network, 'provider:segmentation_id', None),
                'mtu': getattr(network, 'mtu', None),
                'port_security_enabled': getattr(network, 'port_security_enabled', True),
                'subnets': subnets,
                'created_at': str(getattr(network, 'created_at', 'unknown')),
                'updated_at': str(getattr(network, 'updated_at', 'unknown')),
                'tenant_id': getattr(network, 'tenant_id', 'unknown')
            })
        
        return networks
    except Exception as e:
        logger.error(f"Failed to get network details: {e}")
        return [
            {
                'id': 'net-1', 'name': 'public', 'status': 'ACTIVE', 
                'admin_state_up': True, 'shared': True, 'external': True,
                'provider_network_type': 'flat', 'provider_physical_network': 'physnet1',
                'mtu': 1500, 'port_security_enabled': True,
                'subnets': [{'id': 'subnet-1', 'name': 'public-subnet', 'cidr': '192.168.1.0/24'}],
                'error': str(e)
            },
            {
                'id': 'net-2', 'name': 'private', 'status': 'ACTIVE',
                'admin_state_up': True, 'shared': False, 'external': False,
                'provider_network_type': 'vxlan', 'provider_segmentation_id': 1001,
                'mtu': 1450, 'port_security_enabled': True,
                'subnets': [{'id': 'subnet-2', 'name': 'private-subnet', 'cidr': '10.0.0.0/24'}],
                'error': str(e)
            }
        ]


def manage_instance(instance_name: str, action: str) -> Dict[str, Any]:
    """
    Manages OpenStack instances (start, stop, restart, etc.)
    
    Args:
        instance_name: Name of the instance to manage
        action: Action to perform (start, stop, restart, pause, unpause, delete)
    
    Returns:
        Result of the management operation
    """
    try:
        conn = get_openstack_connection()
        
        # Find the instance
        instance = None
        for server in conn.compute.servers():
            if server.name == instance_name or server.id == instance_name:
                instance = server
                break
                
        if not instance:
            return {
                'success': False,
                'message': f'Instance "{instance_name}" not found',
                'current_state': 'NOT_FOUND'
            }
        
        action = action.lower()
        previous_state = instance.status
        
        # Perform the action
        if action == 'start':
            conn.compute.start_server(instance)
            message = f'Instance "{instance_name}" start command sent'
        elif action == 'stop':
            conn.compute.stop_server(instance)
            message = f'Instance "{instance_name}" stop command sent'
        elif action in ['restart', 'reboot']:
            reboot_type = 'SOFT'  # Can be SOFT or HARD
            conn.compute.reboot_server(instance, reboot_type=reboot_type)
            message = f'Instance "{instance_name}" {reboot_type} restart command sent'
        elif action == 'pause':
            conn.compute.pause_server(instance)
            message = f'Instance "{instance_name}" pause command sent'
        elif action in ['unpause', 'resume']:
            conn.compute.unpause_server(instance)
            message = f'Instance "{instance_name}" unpause command sent'
        elif action == 'suspend':
            conn.compute.suspend_server(instance)
            message = f'Instance "{instance_name}" suspend command sent'
        elif action == 'resume_suspended':
            conn.compute.resume_server(instance)
            message = f'Instance "{instance_name}" resume from suspend command sent'
        elif action == 'delete':
            conn.compute.delete_server(instance)
            message = f'Instance "{instance_name}" delete command sent'
        else:
            return {
                'success': False,
                'message': f'Unknown action "{action}". Supported: start, stop, restart, pause, unpause, suspend, resume_suspended, delete',
                'current_state': instance.status
            }
            
        return {
            'success': True,
            'message': message,
            'previous_state': previous_state,
            'requested_action': action.upper(),
            'instance_id': instance.id
        }
            
    except Exception as e:
        logger.error(f"Failed to manage instance {instance_name}: {e}")
        return {
            'success': False,
            'message': f'Failed to manage instance "{instance_name}": {str(e)}',
            'error': str(e)
        }


def manage_volume(volume_name: str, action: str, **kwargs) -> Dict[str, Any]:
    """
    Manages OpenStack volumes (create, delete, attach, detach)
    
    Args:
        volume_name: Name or ID of the volume
        action: Action to perform (create, delete, attach, detach, list, extend)
        **kwargs: Additional parameters (size, instance_name, device, new_size, etc.)
    
    Returns:
        Result of the volume management operation
    """
    try:
        conn = get_openstack_connection()
        
        if action.lower() == 'list':
            volumes = []
            for volume in conn.volume.volumes(detailed=True):
                attachments = []
                for attachment in getattr(volume, 'attachments', []):
                    attachments.append({
                        'server_id': attachment.get('server_id'),
                        'device': attachment.get('device'),
                        'attachment_id': attachment.get('attachment_id')
                    })
                
                volumes.append({
                    'id': volume.id,
                    'name': volume.name,
                    'size': volume.size,
                    'status': volume.status,
                    'volume_type': getattr(volume, 'volume_type', 'unknown'),
                    'bootable': getattr(volume, 'bootable', False),
                    'encrypted': getattr(volume, 'encrypted', False),
                    'attachments': attachments,
                    'created_at': str(getattr(volume, 'created_at', 'unknown')),
                    'availability_zone': getattr(volume, 'availability_zone', 'unknown')
                })
            return {
                'success': True,
                'volumes': volumes,
                'count': len(volumes)
            }
            
        elif action.lower() == 'create':
            size = kwargs.get('size', 1)  # Default 1GB
            description = kwargs.get('description', f'Volume created via MCP: {volume_name}')
            volume_type = kwargs.get('volume_type', None)
            availability_zone = kwargs.get('availability_zone', None)
            
            volume = conn.volume.create_volume(
                name=volume_name,
                size=size,
                description=description,
                volume_type=volume_type,
                availability_zone=availability_zone
            )
            
            return {
                'success': True,
                'message': f'Volume "{volume_name}" creation started',
                'volume_id': volume.id,
                'size': size,
                'status': volume.status,
                'volume_type': volume_type
            }
            
        elif action.lower() == 'delete':
            # Find the volume
            volume = None
            for vol in conn.volume.volumes():
                if vol.name == volume_name or vol.id == volume_name:
                    volume = vol
                    break
                    
            if not volume:
                return {
                    'success': False,
                    'message': f'Volume "{volume_name}" not found'
                }
                
            conn.volume.delete_volume(volume)
            return {
                'success': True,
                'message': f'Volume "{volume_name}" deletion started',
                'volume_id': volume.id
            }
            
        elif action.lower() == 'extend':
            new_size = kwargs.get('new_size', None)
            if not new_size:
                return {
                    'success': False,
                    'message': 'new_size parameter is required for extend action'
                }
                
            # Find the volume
            volume = None
            for vol in conn.volume.volumes():
                if vol.name == volume_name or vol.id == volume_name:
                    volume = vol
                    break
                    
            if not volume:
                return {
                    'success': False,
                    'message': f'Volume "{volume_name}" not found'
                }
                
            conn.volume.extend_volume(volume, new_size)
            return {
                'success': True,
                'message': f'Volume "{volume_name}" extend to {new_size}GB started',
                'volume_id': volume.id,
                'old_size': volume.size,
                'new_size': new_size
            }
            
        else:
            return {
                'success': False,
                'message': f'Unknown action "{action}". Supported: create, delete, list, extend'
            }
            
    except Exception as e:
        logger.error(f"Failed to manage volume: {e}")
        return {
            'success': False,
            'message': f'Failed to manage volume: {str(e)}',
            'error': str(e)
        }


def monitor_resources() -> Dict[str, Any]:
    """
    Monitors resource usage across the OpenStack cluster
    
    Returns:
        Resource usage statistics and monitoring data
    """
    try:
        conn = get_openstack_connection()
        
        # Get hypervisor statistics
        hypervisors = []
        for hypervisor in conn.compute.hypervisors(details=True):
            cpu_usage_percent = (hypervisor.vcpus_used / hypervisor.vcpus * 100) if hypervisor.vcpus > 0 else 0
            memory_usage_percent = (hypervisor.memory_mb_used / hypervisor.memory_mb * 100) if hypervisor.memory_mb > 0 else 0
            disk_usage_percent = (hypervisor.local_gb_used / hypervisor.local_gb * 100) if hypervisor.local_gb > 0 else 0
            
            hypervisors.append({
                'id': hypervisor.id,
                'name': hypervisor.hypervisor_hostname,
                'status': hypervisor.status,
                'state': hypervisor.state,
                'hypervisor_type': getattr(hypervisor, 'hypervisor_type', 'unknown'),
                'hypervisor_version': getattr(hypervisor, 'hypervisor_version', 'unknown'),
                'vcpus_used': hypervisor.vcpus_used,
                'vcpus': hypervisor.vcpus,
                'vcpu_usage_percent': round(cpu_usage_percent, 2),
                'memory_mb_used': hypervisor.memory_mb_used,
                'memory_mb': hypervisor.memory_mb,
                'memory_usage_percent': round(memory_usage_percent, 2),
                'local_gb_used': hypervisor.local_gb_used,
                'local_gb': hypervisor.local_gb,
                'disk_usage_percent': round(disk_usage_percent, 2),
                'running_vms': hypervisor.running_vms,
                'disk_available_least': getattr(hypervisor, 'disk_available_least', None),
                'free_ram_mb': getattr(hypervisor, 'free_ram_mb', None),
                'free_disk_gb': getattr(hypervisor, 'free_disk_gb', None)
            })
            
        # Calculate cluster totals
        total_vcpus = sum(h['vcpus'] for h in hypervisors)
        used_vcpus = sum(h['vcpus_used'] for h in hypervisors) 
        total_memory = sum(h['memory_mb'] for h in hypervisors)
        used_memory = sum(h['memory_mb_used'] for h in hypervisors)
        total_storage = sum(h['local_gb'] for h in hypervisors)
        used_storage = sum(h['local_gb_used'] for h in hypervisors)
        total_vms = sum(h['running_vms'] for h in hypervisors)
        
        # Get quota information if available
        quotas = {}
        try:
            project_id = conn.current_project_id
            compute_quotas = conn.compute.get_quota_set(project_id)
            quotas['compute'] = {
                'instances': getattr(compute_quotas, 'instances', 'unlimited'),
                'cores': getattr(compute_quotas, 'cores', 'unlimited'),
                'ram': getattr(compute_quotas, 'ram', 'unlimited'),
                'volumes': getattr(compute_quotas, 'volumes', 'unlimited')
            }
        except Exception as e:
            logger.warning(f"Failed to get quotas: {e}")
        
        return {
            'cluster_summary': {
                'total_hypervisors': len(hypervisors),
                'total_running_instances': total_vms,
                'vcpu_usage': f'{used_vcpus}/{total_vcpus} ({(used_vcpus/total_vcpus*100):.1f}% used)' if total_vcpus > 0 else 'N/A',
                'memory_usage': f'{used_memory}/{total_memory} MB ({(used_memory/total_memory*100):.1f}% used)' if total_memory > 0 else 'N/A',
                'storage_usage': f'{used_storage}/{total_storage} GB ({(used_storage/total_storage*100):.1f}% used)' if total_storage > 0 else 'N/A',
                'timestamp': datetime.now().isoformat()
            },
            'hypervisors': hypervisors,
            'quotas': quotas
        }
        
    except Exception as e:
        logger.error(f"Failed to fetch resource monitoring data: {e}")
        return {
            'error': f'Failed to fetch resource monitoring data: {str(e)}',
            'fallback_data': {
                'cluster_summary': {
                    'status': 'Monitoring data unavailable',
                    'reason': str(e),
                    'timestamp': datetime.now().isoformat()
                }
            }
        }


def get_project_info() -> Dict[str, Any]:
    """
    Get information about the current OpenStack project/tenant.
    
    Returns:
        Dict containing project information
    """
    try:
        conn = get_openstack_connection()
        
        project_id = conn.current_project_id
        project = conn.identity.get_project(project_id)
        
        # Get project quotas
        quotas = {}
        try:
            compute_quotas = conn.compute.get_quota_set(project_id)
            network_quotas = conn.network.get_quota(project_id)
            volume_quotas = conn.volume.get_quota_set(project_id)
            
            quotas = {
                'compute': {
                    'instances': getattr(compute_quotas, 'instances', -1),
                    'cores': getattr(compute_quotas, 'cores', -1),
                    'ram': getattr(compute_quotas, 'ram', -1)
                },
                'network': {
                    'networks': getattr(network_quotas, 'networks', -1),
                    'subnets': getattr(network_quotas, 'subnets', -1),
                    'ports': getattr(network_quotas, 'ports', -1),
                    'routers': getattr(network_quotas, 'routers', -1),
                    'floating_ips': getattr(network_quotas, 'floating_ips', -1),
                    'security_groups': getattr(network_quotas, 'security_groups', -1)
                },
                'volume': {
                    'volumes': getattr(volume_quotas, 'volumes', -1),
                    'gigabytes': getattr(volume_quotas, 'gigabytes', -1),
                    'snapshots': getattr(volume_quotas, 'snapshots', -1)
                }
            }
        except Exception as e:
            logger.warning(f"Failed to get quotas: {e}")
        
        # Get usage statistics
        usage_stats = {}
        try:
            instances = list(conn.compute.servers())
            networks = list(conn.network.networks())
            volumes = list(conn.volume.volumes())
            
            usage_stats = {
                'instances_count': len(instances),
                'networks_count': len(networks),
                'volumes_count': len(volumes),
                'total_volume_size': sum(getattr(vol, 'size', 0) for vol in volumes)
            }
        except Exception as e:
            logger.warning(f"Failed to get usage stats: {e}")
        
        return {
            'project_id': project.id,
            'project_name': project.name,
            'description': getattr(project, 'description', ''),
            'enabled': getattr(project, 'is_enabled', True),
            'domain_id': getattr(project, 'domain_id', 'unknown'),
            'quotas': quotas,
            'usage_stats': usage_stats,
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get project info: {e}")
        return {
            'error': f'Failed to get project info: {str(e)}',
            'timestamp': datetime.now().isoformat()
        }


def get_flavor_list() -> List[Dict[str, Any]]:
    """
    Get list of available flavors with detailed information.
    
    Returns:
        List of flavor dictionaries
    """
    try:
        conn = get_openstack_connection()
        flavors = []
        
        for flavor in conn.compute.flavors(get_extra_specs=True):
            flavors.append({
                'id': flavor.id,
                'name': flavor.name,
                'vcpus': flavor.vcpus,
                'ram': flavor.ram,
                'disk': flavor.disk,
                'ephemeral': getattr(flavor, 'ephemeral', 0),
                'swap': getattr(flavor, 'swap', 0),
                'rxtx_factor': getattr(flavor, 'rxtx_factor', 1.0),
                'is_public': getattr(flavor, 'is_public', True),
                'extra_specs': getattr(flavor, 'extra_specs', {})
            })
        
        return flavors
    except Exception as e:
        logger.error(f"Failed to get flavor list: {e}")
        return [
            {'id': 'm1.tiny', 'name': 'm1.tiny', 'vcpus': 1, 'ram': 512, 'disk': 1, 'error': str(e)},
            {'id': 'm1.small', 'name': 'm1.small', 'vcpus': 1, 'ram': 2048, 'disk': 20, 'error': str(e)},
            {'id': 'm1.medium', 'name': 'm1.medium', 'vcpus': 2, 'ram': 4096, 'disk': 40, 'error': str(e)}
        ]


def get_image_list() -> List[Dict[str, Any]]:
    """
    Get list of available images.
    
    Returns:
        List of image dictionaries
    """
    try:
        conn = get_openstack_connection()
        images = []
        
        for image in conn.image.images():
            # Skip if image name starts with '.' (system images)
            if image.name and image.name.startswith('.'):
                continue
                
            images.append({
                'id': image.id,
                'name': image.name,
                'status': image.status,
                'visibility': getattr(image, 'visibility', 'unknown'),
                'size': getattr(image, 'size', 0),
                'disk_format': getattr(image, 'disk_format', 'unknown'),
                'container_format': getattr(image, 'container_format', 'unknown'),
                'min_disk': getattr(image, 'min_disk', 0),
                'min_ram': getattr(image, 'min_ram', 0),
                'created_at': str(getattr(image, 'created_at', 'unknown')),
                'updated_at': str(getattr(image, 'updated_at', 'unknown')),
                'properties': getattr(image, 'properties', {}),
                'tags': list(getattr(image, 'tags', []))
            })
        
        return images
    except Exception as e:
        logger.error(f"Failed to get image list: {e}")
        return [
            {'id': 'ubuntu-20.04', 'name': 'Ubuntu 20.04', 'status': 'active', 'error': str(e)},
            {'id': 'centos-8', 'name': 'CentOS 8', 'status': 'active', 'error': str(e)}
        ]


def reset_connection_cache():
    """
    Reset the connection cache. Useful for testing or when connection parameters change.
    """
    global _connection_cache
    _connection_cache = None
    logger.info("OpenStack connection cache reset")
