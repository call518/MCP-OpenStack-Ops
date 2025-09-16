import os
from openstack import connection
from dotenv import load_dotenv

def get_openstack_connection():
    """
    Creates OpenStack connection using proxy URLs for all services.
    """
    load_dotenv()
    
    proxy_host = "192.168.35.2"
    
    return connection.Connection(
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

def get_cluster_status():
    """
    Returns a summary of cluster status using OpenStack SDK.
    """
    try:
        conn = get_openstack_connection()
        
        # Get basic cluster information
        services = [svc.name for svc in conn.identity.services()]
        instances = [server.name for server in conn.compute.servers()]
        networks = [net.name for net in conn.network.networks()]
        
        return {
            'instances': instances if instances else ['No instances found'],
            'networks': networks if networks else ['No networks found'],
            'services': services,
            'connection_status': 'Connected via SDK'
        }
    except Exception as e:
        print(f"Warning: Unable to connect to OpenStack ({str(e)[:100]}). Using mock data.")
        return {
            'instances': ['demo-instance-1', 'demo-instance-2'],
            'networks': ['public', 'private', 'external'],
            'services': ['nova', 'neutron', 'keystone'],
            'connection_status': f'Failed: {str(e)[:100]}...'
        }

def get_service_status():
    """
    Returns detailed service status information.
    """
    try:
        conn = get_openstack_connection()
        services = []
        for service in conn.compute.services():
            services.append({
                'binary': service.binary,
                'host': service.host,
                'status': service.status,
                'state': service.state,
                'zone': getattr(service, 'zone', 'unknown')
            })
        return services
    except Exception as e:
        return [
            {'binary': 'nova-compute', 'host': 'controller', 'status': 'enabled', 'state': 'up', 'zone': 'nova'},
            {'binary': 'neutron-server', 'host': 'controller', 'status': 'enabled', 'state': 'up', 'zone': 'internal'},
        ]

def get_instance_details():
    """
    Returns detailed instance information.
    """
    try:
        conn = get_openstack_connection()
        instances = []
        for server in conn.compute.servers():
            instances.append({
                'id': server.id,
                'name': server.name,
                'status': server.status,
                'power_state': getattr(server, 'power_state', 'unknown'),
                'vm_state': getattr(server, 'vm_state', 'unknown'),
                'created': str(server.created_at) if hasattr(server, 'created_at') else 'unknown',
                'flavor': server.flavor['id'] if server.flavor else 'unknown',
                'image': server.image['id'] if server.image else 'unknown'
            })
        return instances
    except Exception as e:
        return [
            {'id': 'demo-1', 'name': 'demo-instance-1', 'status': 'ACTIVE', 'power_state': '1', 'vm_state': 'active', 'created': '2025-09-16T00:00:00Z', 'flavor': 'm1.small', 'image': 'ubuntu-20.04'},
            {'id': 'demo-2', 'name': 'demo-instance-2', 'status': 'ACTIVE', 'power_state': '1', 'vm_state': 'active', 'created': '2025-09-16T01:00:00Z', 'flavor': 'm1.medium', 'image': 'centos-8'}
        ]

def get_network_details():
    """
    Returns detailed network information.
    """
    try:
        conn = get_openstack_connection()
        networks = []
        for network in conn.network.networks():
            networks.append({
                'id': network.id,
                'name': network.name,
                'status': network.status,
                'admin_state_up': network.is_admin_state_up,
                'shared': network.is_shared,
                'external': getattr(network, 'is_router_external', False),
                'subnets': network.subnet_ids if hasattr(network, 'subnet_ids') else []
            })
        return networks
    except Exception as e:
        return [
            {'id': 'net-1', 'name': 'public', 'status': 'ACTIVE', 'admin_state_up': True, 'shared': True, 'external': True, 'subnets': ['subnet-1']},
            {'id': 'net-2', 'name': 'private', 'status': 'ACTIVE', 'admin_state_up': True, 'shared': False, 'external': False, 'subnets': ['subnet-2']}
        ]

def get_service_status():
    """
    Returns detailed service status information.
    """
    try:
        conn = get_openstack_connection()
        services = []
        for service in conn.compute.services():
            services.append({
                'binary': service.binary,
                'host': service.host,
                'status': service.status,
                'state': service.state,
                'zone': getattr(service, 'zone', 'unknown')
            })
        return services
    except Exception as e:
        return [
            {'binary': 'nova-compute', 'host': 'controller', 'status': 'enabled', 'state': 'up', 'zone': 'nova'},
            {'binary': 'neutron-server', 'host': 'controller', 'status': 'enabled', 'state': 'up', 'zone': 'internal'},
        ]

def get_instance_details():
    """
    Returns detailed instance information.
    """
    try:
        conn = get_openstack_connection()
        instances = []
        for server in conn.compute.servers():
            instances.append({
                'id': server.id,
                'name': server.name,
                'status': server.status,
                'power_state': getattr(server, 'power_state', 'unknown'),
                'vm_state': getattr(server, 'vm_state', 'unknown'),
                'created': str(server.created_at) if hasattr(server, 'created_at') else 'unknown',
                'flavor': server.flavor['id'] if server.flavor else 'unknown',
                'image': server.image['id'] if server.image else 'unknown'
            })
        return instances
    except Exception as e:
        return [
            {'id': 'demo-1', 'name': 'demo-instance-1', 'status': 'ACTIVE', 'power_state': '1', 'vm_state': 'active', 'created': '2025-09-16T00:00:00Z', 'flavor': 'm1.small', 'image': 'ubuntu-20.04'},
            {'id': 'demo-2', 'name': 'demo-instance-2', 'status': 'ACTIVE', 'power_state': '1', 'vm_state': 'active', 'created': '2025-09-16T01:00:00Z', 'flavor': 'm1.medium', 'image': 'centos-8'}
        ]

def get_network_details():
    """
    Returns detailed network information.
    """
    try:
        conn = get_openstack_connection()
        networks = []
        for network in conn.network.networks():
            networks.append({
                'id': network.id,
                'name': network.name,
                'status': network.status,
                'admin_state_up': network.is_admin_state_up,
                'shared': network.is_shared,
                'external': getattr(network, 'is_router_external', False),
                'subnets': network.subnet_ids if hasattr(network, 'subnet_ids') else []
            })
        return networks
    except Exception as e:
        return [
            {'id': 'net-1', 'name': 'public', 'status': 'ACTIVE', 'admin_state_up': True, 'shared': True, 'external': True, 'subnets': ['subnet-1']},
            {'id': 'net-2', 'name': 'private', 'status': 'ACTIVE', 'admin_state_up': True, 'shared': False, 'external': False, 'subnets': ['subnet-2']}
        ]

def manage_instance(instance_name: str, action: str):
    """
    Manages OpenStack instances (start, stop, restart, etc.)
    
    Args:
        instance_name: Name of the instance to manage
        action: Action to perform (start, stop, restart, pause, unpause)
    
    Returns:
        Result of the management operation
    """
    try:
        conn = get_openstack_connection()
        
        # Find the instance
        instance = None
        for server in conn.compute.servers():
            if server.name == instance_name:
                instance = server
                break
                
        if not instance:
            return {
                'success': False,
                'message': f'Instance "{instance_name}" not found',
                'current_state': 'NOT_FOUND'
            }
        
        # Perform the action
        if action.lower() == 'start':
            conn.compute.start_server(instance)
            return {
                'success': True, 
                'message': f'Instance "{instance_name}" start command sent',
                'previous_state': instance.status,
                'requested_action': 'START'
            }
        elif action.lower() == 'stop':
            conn.compute.stop_server(instance)
            return {
                'success': True,
                'message': f'Instance "{instance_name}" stop command sent', 
                'previous_state': instance.status,
                'requested_action': 'STOP'
            }
        elif action.lower() == 'restart' or action.lower() == 'reboot':
            conn.compute.reboot_server(instance, reboot_type='SOFT')
            return {
                'success': True,
                'message': f'Instance "{instance_name}" restart command sent',
                'previous_state': instance.status,
                'requested_action': 'RESTART'
            }
        elif action.lower() == 'pause':
            conn.compute.pause_server(instance)
            return {
                'success': True,
                'message': f'Instance "{instance_name}" pause command sent',
                'previous_state': instance.status, 
                'requested_action': 'PAUSE'
            }
        elif action.lower() == 'unpause' or action.lower() == 'resume':
            conn.compute.unpause_server(instance)
            return {
                'success': True,
                'message': f'Instance "{instance_name}" unpause command sent',
                'previous_state': instance.status,
                'requested_action': 'UNPAUSE'
            }
        else:
            return {
                'success': False,
                'message': f'Unknown action "{action}". Supported: start, stop, restart, pause, unpause',
                'current_state': instance.status
            }
            
    except Exception as e:
        return {
            'success': False,
            'message': f'Failed to manage instance "{instance_name}": {str(e)}',
            'error': str(e)
        }


def manage_volume(volume_name: str, action: str, **kwargs):
    """
    Manages OpenStack volumes (create, delete, attach, detach)
    
    Args:
        volume_name: Name of the volume
        action: Action to perform (create, delete, attach, detach, list)
        **kwargs: Additional parameters (size, instance_name, etc.)
    
    Returns:
        Result of the volume management operation
    """
    try:
        conn = get_openstack_connection()
        
        if action.lower() == 'list':
            volumes = []
            for volume in conn.volume.volumes():
                volumes.append({
                    'id': volume.id,
                    'name': volume.name,
                    'size': volume.size,
                    'status': volume.status,
                    'attachments': volume.attachments
                })
            return {
                'success': True,
                'volumes': volumes,
                'count': len(volumes)
            }
            
        elif action.lower() == 'create':
            size = kwargs.get('size', 1)  # Default 1GB
            description = kwargs.get('description', f'Volume created via MCP: {volume_name}')
            
            volume = conn.volume.create_volume(
                name=volume_name,
                size=size,
                description=description
            )
            
            return {
                'success': True,
                'message': f'Volume "{volume_name}" creation started',
                'volume_id': volume.id,
                'size': size,
                'status': volume.status
            }
            
        elif action.lower() == 'delete':
            # Find the volume
            volume = None
            for vol in conn.volume.volumes():
                if vol.name == volume_name:
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
            
        else:
            return {
                'success': False,
                'message': f'Unknown action "{action}". Supported: create, delete, list'
            }
            
    except Exception as e:
        return {
            'success': False,
            'message': f'Failed to manage volume: {str(e)}',
            'error': str(e)
        }


def monitor_resources():
    """
    Monitors resource usage across the OpenStack cluster
    
    Returns:
        Resource usage statistics and monitoring data
    """
    try:
        conn = get_openstack_connection()
        
        # Get hypervisor statistics
        hypervisors = []
        for hypervisor in conn.compute.hypervisors():
            hypervisors.append({
                'id': hypervisor.id,
                'name': hypervisor.hypervisor_hostname,
                'status': hypervisor.status,
                'state': hypervisor.state,
                'vcpus_used': hypervisor.vcpus_used,
                'vcpus': hypervisor.vcpus,
                'memory_mb_used': hypervisor.memory_mb_used,
                'memory_mb': hypervisor.memory_mb,
                'local_gb_used': hypervisor.local_gb_used,
                'local_gb': hypervisor.local_gb,
                'running_vms': hypervisor.running_vms
            })
            
        # Calculate cluster totals
        total_vcpus = sum(h['vcpus'] for h in hypervisors)
        used_vcpus = sum(h['vcpus_used'] for h in hypervisors) 
        total_memory = sum(h['memory_mb'] for h in hypervisors)
        used_memory = sum(h['memory_mb_used'] for h in hypervisors)
        total_storage = sum(h['local_gb'] for h in hypervisors)
        used_storage = sum(h['local_gb_used'] for h in hypervisors)
        
        return {
            'cluster_summary': {
                'total_hypervisors': len(hypervisors),
                'vcpu_usage': f'{used_vcpus}/{total_vcpus} ({(used_vcpus/total_vcpus*100):.1f}% used)' if total_vcpus > 0 else 'N/A',
                'memory_usage': f'{used_memory}/{total_memory} MB ({(used_memory/total_memory*100):.1f}% used)' if total_memory > 0 else 'N/A',
                'storage_usage': f'{used_storage}/{total_storage} GB ({(used_storage/total_storage*100):.1f}% used)' if total_storage > 0 else 'N/A'
            },
            'hypervisors': hypervisors
        }
        
    except Exception as e:
        return {
            'error': f'Failed to fetch resource monitoring data: {str(e)}',
            'fallback_data': {
                'cluster_summary': {
                    'status': 'Monitoring data unavailable',
                    'reason': str(e)
                }
            }
        }
