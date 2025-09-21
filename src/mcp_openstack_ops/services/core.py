"""
OpenStack Core Connection and Cluster Management Functions

This module contains core functions for OpenStack connection management and cluster-wide operations.
"""

import os
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from ..connection import get_openstack_connection, reset_connection_cache

# Configure logging
logger = logging.getLogger(__name__)


# get_cluster_status function removed - use combination of get_* tools for comprehensive cluster reports


def get_service_status(service_name: str = "") -> Dict[str, Any]:
    """
    Get comprehensive OpenStack cluster status including all services and resources.
    
    Returns:
        Dict containing cluster status information
    """
    try:
        conn = get_openstack_connection()
        
        # Get basic cluster information
        project_id = conn.current_project_id
        project = conn.identity.get_project(project_id)
        
        status_data = {
            'cluster_info': {
                'project_name': project.name,
                'project_id': project.id,
                'domain': getattr(project, 'domain_id', 'default'),
                'enabled': project.is_enabled,
                'description': getattr(project, 'description', ''),
                'check_time': datetime.now().isoformat()
            },
            'services': {},
            'resources': {},
            'quotas': {},
            'health': {
                'overall': 'unknown',
                'issues': []
            }
        }
        
        # Check service availability
        services = ['compute', 'network', 'volume', 'image', 'identity', 'orchestration']
        
        for service in services:
            try:
                service_status = {
                    'available': True,
                    'endpoint': 'unknown',
                    'version': 'unknown',
                    'last_check': datetime.now().isoformat()
                }
                
                if service == 'compute':
                    # Test compute service
                    list(conn.compute.servers(limit=1))
                    service_status['endpoint'] = conn.compute.get_endpoint()
                    
                elif service == 'network':
                    # Test network service
                    list(conn.network.networks(limit=1))
                    service_status['endpoint'] = conn.network.get_endpoint()
                    
                elif service == 'volume':
                    # Test volume service
                    list(conn.volume.volumes(limit=1))
                    service_status['endpoint'] = conn.volume.get_endpoint()
                    
                elif service == 'image':
                    # Test image service
                    list(conn.image.images(limit=1))
                    service_status['endpoint'] = conn.image.get_endpoint()
                    
                elif service == 'identity':
                    # Test identity service
                    conn.identity.get_token()
                    # Identity service endpoint handling
                    try:
                        service_status['endpoint'] = conn.session.get_endpoint(service_type='identity', interface='public')
                    except Exception:
                        service_status['endpoint'] = f"http://{os.environ.get('OS_AUTH_HOST', 'localhost')}:{os.environ.get('OS_AUTH_PORT', '5000')}"
                    
                elif service == 'orchestration':
                    # Test orchestration service (Heat) with manual API call
                    try:
                        import requests
                        import os
                        
                        # Get project ID and token
                        project_id = conn.current_project_id
                        token = conn.identity.get_token()
                        
                        # Construct Heat API URL
                        auth_host = os.environ.get('OS_AUTH_HOST', 'localhost')
                        heat_port = os.environ.get('OS_HEAT_STACK_PORT', '8004')
                        heat_url = f"http://{auth_host}:{heat_port}/v1/{project_id}/stacks"
                        
                        headers = {'X-Auth-Token': token}
                        
                        # Test Heat API with timeout
                        response = requests.get(heat_url, headers=headers, timeout=5)
                        
                        if response.status_code == 200:
                            data = response.json()
                            stacks_count = len(data.get('stacks', []))
                            
                            # Also get Heat engine services information
                            try:
                                services_url = f"http://{auth_host}:{heat_port}/v1/{project_id}/services"
                                services_response = requests.get(services_url, headers=headers, timeout=3)
                                
                                heat_engines_info = "engines status unknown"
                                if services_response.status_code == 200:
                                    services_data = services_response.json()
                                    heat_services = services_data.get('services', [])
                                    up_engines = [s for s in heat_services if s.get('status') == 'up']
                                    heat_engines_info = f"{len(up_engines)}/{len(heat_services)} engines up"
                            except Exception:
                                heat_engines_info = "engines status unavailable"
                            
                            service_status['endpoint'] = f"http://{auth_host}:{heat_port}/v1"
                            service_status['details'] = {
                                'stacks_count': stacks_count,
                                'api_version': 'v1',
                                'status': 'accessible',
                                'engines_info': heat_engines_info
                            }
                            logger.info(f"Heat service check successful: {stacks_count} stacks found, {heat_engines_info}")
                        else:
                            raise Exception(f"Heat API returned {response.status_code}: {response.text[:100]}")
                            
                    except requests.exceptions.Timeout:
                        logger.warning("Heat service check timeout")
                        service_status['available'] = False
                        service_status['endpoint'] = 'timeout'
                        service_status['error'] = 'API call timeout (5s)'
                    except Exception as e:
                        logger.warning(f"Heat service check failed: {e}")
                        service_status['available'] = False
                        service_status['endpoint'] = 'unavailable'
                        service_status['error'] = f'Heat API error: {str(e)}'
                
                status_data['services'][service] = service_status
                
            except Exception as e:
                status_data['services'][service] = {
                    'available': False,
                    'error': str(e),
                    'last_check': datetime.now().isoformat()
                }
                status_data['health']['issues'].append(f'{service.title()} service: {str(e)}')
        
        # Get resource counts
        try:
            # Compute resources
            instances = list(conn.compute.servers())
            flavors = list(conn.compute.flavors())
            keypairs = list(conn.compute.keypairs())
            
            # Analyze instance states
            instance_states = {}
            for instance in instances:
                state = getattr(instance, 'status', 'UNKNOWN').upper()
                instance_states[state] = instance_states.get(state, 0) + 1
            
            status_data['resources']['compute'] = {
                'instances': len(instances),
                'flavors': len(flavors),
                'keypairs': len(keypairs),
                'instance_states': instance_states
            }
            
            # Network resources (enhanced)
            networks = list(conn.network.networks())
            subnets = list(conn.network.subnets())
            routers = list(conn.network.routers())
            floating_ips = list(conn.network.ips())
            security_groups = list(conn.network.security_groups())
            ports = list(conn.network.ports())  # Add ports collection
            
            # Analyze floating IP usage
            floating_ip_states = {'DOWN': 0, 'ACTIVE': 0, 'ERROR': 0, 'OTHER': 0}
            external_networks = 0
            private_networks = 0
            
            for network in networks:
                if getattr(network, 'is_router_external', False):
                    external_networks += 1
                else:
                    private_networks += 1
            
            for fip in floating_ips:
                state = getattr(fip, 'status', 'UNKNOWN').upper()
                if state in floating_ip_states:
                    floating_ip_states[state] += 1
                else:
                    floating_ip_states['OTHER'] += 1
            
            # Analyze port states
            port_states = {'ACTIVE': 0, 'DOWN': 0, 'BUILD': 0, 'ERROR': 0, 'OTHER': 0}
            for port in ports:
                state = getattr(port, 'status', 'UNKNOWN').upper()
                if state in port_states:
                    port_states[state] += 1
                else:
                    port_states['OTHER'] += 1
            
            status_data['resources']['network'] = {
                'networks': len(networks),
                'external_networks': external_networks,
                'private_networks': private_networks,
                'subnets': len(subnets),
                'routers': len(routers),
                'floating_ips': len(floating_ips),
                'floating_ip_states': floating_ip_states,
                'security_groups': len(security_groups),
                'ports': len(ports),
                'port_states': port_states
            }
            
            # Volume resources (enhanced with backup information and detailed volume analysis)
            volumes = list(conn.volume.volumes())
            snapshots = list(conn.volume.snapshots())
            
            # Analyze volume states and characteristics
            volume_states = {}
            total_volume_size = 0
            bootable_volumes = 0
            encrypted_volumes = 0
            multiattach_volumes = 0
            attached_volumes = 0
            volume_attachments = []
            
            for volume in volumes:
                state = getattr(volume, 'status', 'UNKNOWN').upper()
                volume_states[state] = volume_states.get(state, 0) + 1
                total_volume_size += getattr(volume, 'size', 0)
                
                # Track volume characteristics
                if getattr(volume, 'is_bootable', False):
                    bootable_volumes += 1
                if getattr(volume, 'encrypted', False):
                    encrypted_volumes += 1  
                if getattr(volume, 'multiattach', False):
                    multiattach_volumes += 1
                
                # Track attachments
                attachments = getattr(volume, 'attachments', [])
                if attachments:
                    attached_volumes += 1
                    volume_attachments.extend(attachments)
            
            # Get volume snapshots with state analysis
            snapshot_states = {}
            total_snapshot_size = 0
            for snapshot in snapshots:
                state = getattr(snapshot, 'status', 'UNKNOWN').upper()
                snapshot_states[state] = snapshot_states.get(state, 0) + 1
                total_snapshot_size += getattr(snapshot, 'size', 0)
            
            # Get volume types information  
            volume_types = []
            try:
                from ..services.storage import get_volume_types
                volume_types = get_volume_types()
            except Exception as e:
                logger.warning(f"Could not retrieve volume types: {e}")
            
            # Get volume backup information
            backups = []
            backup_states = {}
            total_backup_size = 0
            try:
                from ..services.storage import set_volume_backups
                backup_result = set_volume_backups('list')
                if backup_result.get('success'):
                    backups = backup_result.get('backups', [])
                    # Analyze backup states and sizes
                    for backup in backups:
                        state = backup.get('status', 'UNKNOWN').upper()
                        backup_states[state] = backup_states.get(state, 0) + 1
                        total_backup_size += backup.get('size', 0)
                else:
                    logger.warning("Volume backup service not available")
            except Exception as e:
                logger.warning(f"Could not retrieve backup information: {e}")
            
            status_data['resources']['volume'] = {
                'volumes': len(volumes),
                'snapshots': len(snapshots),
                'volume_states': volume_states,
                'snapshot_states': snapshot_states,
                'total_size_gb': total_volume_size,
                'total_snapshot_size_gb': total_snapshot_size,
                'backups': len(backups),
                'backup_states': backup_states,
                'total_backup_size_gb': total_backup_size,
                'volume_characteristics': {
                    'bootable_volumes': bootable_volumes,
                    'encrypted_volumes': encrypted_volumes,
                    'multiattach_volumes': multiattach_volumes,
                    'attached_volumes': attached_volumes,
                    'available_volumes': volume_states.get('AVAILABLE', 0),
                    'in_use_volumes': volume_states.get('IN-USE', 0),
                    'total_attachments': len(volume_attachments)
                },
                'volume_types_available': len(volume_types),
                'storage_summary': {
                    'total_storage_gb': total_volume_size + total_snapshot_size + total_backup_size,
                    'volumes_gb': total_volume_size,
                    'snapshots_gb': total_snapshot_size,
                    'backups_gb': total_backup_size
                }
            }
            
            # Image resources (enhanced)
            images = list(conn.image.images())
            
            # Analyze image visibility and status
            image_visibility = {'public': 0, 'private': 0, 'shared': 0, 'community': 0}
            image_status = {'active': 0, 'saving': 0, 'queued': 0, 'killed': 0, 'deleted': 0, 'other': 0}
            
            for image in images:
                visibility = getattr(image, 'visibility', 'private')
                status = getattr(image, 'status', 'unknown').lower()
                
                if visibility in image_visibility:
                    image_visibility[visibility] += 1
                
                if status in image_status:
                    image_status[status] += 1
                else:
                    image_status['other'] += 1
            
            status_data['resources']['image'] = {
                'images': len(images),
                'image_visibility': image_visibility,
                'image_status': image_status
            }
            
            # Load Balancer resources (new)
            try:
                # Quick check if load balancer service is accessible with timeout
                import requests
                from requests.adapters import HTTPAdapter
                from urllib3.util.retry import Retry
                
                # Try to access load balancer service with short timeout
                timeout_session = requests.Session()
                timeout_adapter = HTTPAdapter(max_retries=Retry(total=0))
                timeout_session.mount('http://', timeout_adapter)
                timeout_session.mount('https://', timeout_adapter)
                
                # Get token and construct load balancer endpoint URL
                token = conn.identity.get_token()
                auth_host = os.environ.get('OS_AUTH_HOST', 'localhost')
                
                # Try different potential load balancer ports
                lb_ports = [9876, 9876]  # Octavia default port
                lb_accessible = False
                
                for port in lb_ports:
                    try:
                        lb_url = f"http://{auth_host}:{port}/v2.0/lbaas/loadbalancers"
                        headers = {'X-Auth-Token': token}
                        
                        response = timeout_session.get(lb_url, headers=headers, timeout=3)
                        if response.status_code in [200, 401, 403]:  # Service exists
                            lb_accessible = True
                            break
                    except Exception:
                        continue
                
                if lb_accessible:
                    # Use OpenStack SDK to get load balancer info
                    load_balancers = list(conn.load_balancer.load_balancers())
                    
                    # Analyze load balancer states
                    lb_states = {}
                    total_listeners = 0
                    total_pools = 0
                    total_members = 0
                    
                    for lb in load_balancers[:10]:  # Limit to first 10 LBs to avoid timeout
                        state = getattr(lb, 'provisioning_status', 'UNKNOWN').upper()
                        lb_states[state] = lb_states.get(state, 0) + 1
                        
                        # Count listeners and pools for each LB (with timeout protection)
                        try:
                            listeners = list(conn.load_balancer.listeners(loadbalancer_id=lb.id))
                            total_listeners += len(listeners)
                            
                            for listener in listeners[:5]:  # Limit listeners per LB
                                try:
                                    pools = list(conn.load_balancer.pools(listener_id=listener.id))
                                    total_pools += len(pools)
                                    
                                    for pool in pools[:3]:  # Limit pools per listener
                                        try:
                                            members = list(conn.load_balancer.members(pool=pool.id))
                                            total_members += len(members)
                                        except Exception:
                                            pass  # Skip member counting if failed
                                except Exception:
                                    pass  # Skip pool counting if failed
                        except Exception:
                            pass  # Skip listener counting if failed
                    
                    status_data['resources']['load_balancer'] = {
                        'load_balancers': len(load_balancers),
                        'lb_states': lb_states,
                        'listeners': total_listeners,
                        'pools': total_pools,
                        'members': total_members,
                        'note': f'Limited to first {min(10, len(load_balancers))} load balancers for performance'
                    }
                else:
                    status_data['resources']['load_balancer'] = {
                        'load_balancers': 0,
                        'note': 'Load balancer service not accessible or not installed',
                        'ports_tested': lb_ports
                    }
                    
            except Exception as e:
                # Load balancer service not available or accessible
                status_data['resources']['load_balancer'] = {
                    'load_balancers': 0,
                    'note': 'Load balancer service not available',
                    'error': str(e)[:100]
                }
            
            # Hypervisor information (enhanced with Nova Statistics API)
            try:
                hypervisors = list(conn.compute.hypervisors(details=True))
                
                total_vcpus = 0
                used_vcpus = 0
                total_ram_mb = 0
                used_ram_mb = 0
                total_disk_gb = 0
                used_disk_gb = 0
                total_running_vms = 0
                hypervisor_states = {'up': 0, 'down': 0, 'unknown': 0}
                data_source = 'hypervisor_individual_api'
                
                for hv in hypervisors:
                    # Resource totals (handle None values safely)
                    hv_vcpus = getattr(hv, 'vcpus', None) or 0
                    hv_vcpus_used = getattr(hv, 'vcpus_used', None) or 0
                    hv_memory_mb = getattr(hv, 'memory_size_mb', None) or getattr(hv, 'memory_mb', None) or 0
                    hv_memory_mb_used = getattr(hv, 'memory_used_mb', None) or getattr(hv, 'memory_mb_used', None) or 0
                    hv_disk_gb = getattr(hv, 'local_disk_size_gb', None) or getattr(hv, 'local_gb', None) or 0
                    hv_disk_gb_used = getattr(hv, 'local_disk_used_gb', None) or getattr(hv, 'local_gb_used', None) or 0
                    hv_running_vms = getattr(hv, 'running_vms', None) or 0
                    
                    # Safely add values
                    total_vcpus += hv_vcpus
                    used_vcpus += hv_vcpus_used
                    total_ram_mb += hv_memory_mb
                    used_ram_mb += hv_memory_mb_used
                    total_disk_gb += hv_disk_gb
                    used_disk_gb += hv_disk_gb_used
                    total_running_vms += hv_running_vms
                    
                    # Hypervisor state
                    state = str(getattr(hv, 'state', 'unknown')).lower()
                    if state in hypervisor_states:
                        hypervisor_states[state] += 1
                    else:
                        hypervisor_states['unknown'] += 1
                
                # Try Nova Statistics API for better data
                try:
                    stats_response = conn.compute.get('/os-hypervisors/statistics')
                    if stats_response.status_code == 200:
                        stats_data = stats_response.json()
                        hypervisor_statistics = stats_data.get('hypervisor_statistics', {})
                        
                        if hypervisor_statistics:
                            # Use statistics API data as it's more reliable
                            total_vcpus = hypervisor_statistics.get('vcpus', total_vcpus)
                            used_vcpus = hypervisor_statistics.get('vcpus_used', used_vcpus)
                            total_ram_mb = hypervisor_statistics.get('memory_mb', total_ram_mb)
                            used_ram_mb = hypervisor_statistics.get('memory_mb_used', used_ram_mb)
                            total_disk_gb = hypervisor_statistics.get('local_gb', total_disk_gb)
                            used_disk_gb = hypervisor_statistics.get('local_gb_used', used_disk_gb)
                            total_running_vms = hypervisor_statistics.get('running_vms', total_running_vms)
                            data_source = 'nova_statistics_api'
                            
                            logger.info(f"Using Nova Statistics API: {total_vcpus} vCPUs, {total_ram_mb} MB RAM, {total_running_vms} VMs")
                except Exception as e:
                    logger.warning(f"Nova Statistics API failed: {e}")
                
                # Fallback: Calculate from actual instances if still no data
                if total_vcpus == 0 or used_vcpus == 0:
                    instance_vcpus = 0
                    instance_ram_mb = 0
                    
                    # Always calculate from instances and their flavors for accurate usage
                    for instance in instances:
                        try:
                            # Get flavor information from instance
                            flavor_id = None
                            if hasattr(instance, 'flavor') and isinstance(instance.flavor, dict):
                                flavor_id = instance.flavor.get('id')
                            elif hasattr(instance, 'flavor') and hasattr(instance.flavor, 'id'):
                                flavor_id = instance.flavor.id
                            
                            flavor = None
                            if flavor_id:
                                try:
                                    # Try to get flavor by ID first
                                    flavor = conn.compute.get_flavor(flavor_id)
                                except Exception:
                                    # If ID fails, try to find flavor by name
                                    try:
                                        flavors = list(conn.compute.flavors())
                                        for f in flavors:
                                            if getattr(f, 'name', '') == flavor_id or getattr(f, 'id', '') == flavor_id:
                                                flavor = f
                                                break
                                    except Exception as e2:
                                        logger.warning(f"Could not find flavor {flavor_id} by name either: {e2}")
                            
                            if flavor:
                                vcpus = getattr(flavor, 'vcpus', 0)
                                ram_mb = getattr(flavor, 'ram', 0)
                                instance_vcpus += vcpus if vcpus else 0
                                instance_ram_mb += ram_mb if ram_mb else 0
                                logger.info(f"Instance {getattr(instance, 'id', 'unknown')} using flavor {flavor_id}: {vcpus} vCPUs, {ram_mb} MB RAM")
                            else:
                                logger.warning(f"Could not find flavor info for instance {getattr(instance, 'id', 'unknown')} with flavor {flavor_id}")
                                
                        except Exception as e:
                            logger.warning(f"Error processing instance {getattr(instance, 'id', 'unknown')}: {e}")
                            continue
                    
                    # Set realistic estimates when hypervisor data is not available
                    if total_vcpus == 0 or total_vcpus <= instance_vcpus:
                        # Estimate total capacity: use reasonable default estimates
                        # (Nova Statistics API will provide better data if available)
                        estimated_total_vcpus = 40  # Conservative estimate
                        estimated_total_ram_mb = 96000  # Conservative estimate
                        
                        total_vcpus = estimated_total_vcpus
                        total_ram_mb = estimated_total_ram_mb
                        
                        logger.info(f"Using estimated capacity: {total_vcpus} vCPUs, {total_ram_mb} MB RAM (hypervisor data unavailable)")
                        data_source = 'estimated_fallback'
                    
                    # Use actual instance resource usage 
                    used_vcpus = instance_vcpus
                    used_ram_mb = instance_ram_mb
                
                status_data['resources']['hypervisors'] = {
                    'hypervisors': len(hypervisors),
                    'hypervisor_states': hypervisor_states,
                    'running_vms': total_running_vms,
                    'vcpus_total': total_vcpus,
                    'vcpus_used': used_vcpus,
                    'vcpus_available': max(0, total_vcpus - used_vcpus),
                    'memory_mb_total': total_ram_mb,
                    'memory_mb_used': used_ram_mb,
                    'memory_mb_available': max(0, total_ram_mb - used_ram_mb),
                    'disk_gb_total': total_disk_gb,
                    'disk_gb_used': used_disk_gb,
                    'disk_gb_available': max(0, total_disk_gb - used_disk_gb),
                    'resource_utilization': {
                        'vcpu_usage_percent': round((used_vcpus / total_vcpus * 100), 1) if total_vcpus > 0 else 0,
                        'memory_usage_percent': round((used_ram_mb / total_ram_mb * 100), 1) if total_ram_mb > 0 else 0,
                        'disk_usage_percent': round((used_disk_gb / total_disk_gb * 100), 1) if total_disk_gb > 0 else 0
                    },
                    'data_source': data_source
                }
                
            except Exception as e:
                status_data['resources']['hypervisors'] = {
                    'hypervisors': 0,
                    'note': 'Hypervisor details not accessible',
                    'error': str(e)[:100]
                }
            
            # Floating IP pools information (new)
            try:
                floating_ip_pools = []
                external_networks = [net for net in networks if getattr(net, 'is_router_external', False)]
                
                for ext_network in external_networks:
                    pool_info = {
                        'network_id': ext_network.id,
                        'network_name': getattr(ext_network, 'name', 'unnamed'),
                        'used_ips': 0,
                        'admin_state_up': getattr(ext_network, 'is_admin_state_up', True)
                    }
                    
                    # Count floating IPs from this network
                    for fip in floating_ips:
                        if getattr(fip, 'floating_network_id', None) == ext_network.id:
                            pool_info['used_ips'] += 1
                    
                    floating_ip_pools.append(pool_info)
                
                status_data['resources']['floating_ip_pools'] = {
                    'pools': len(floating_ip_pools),
                    'pool_details': floating_ip_pools
                }
                
            except Exception as e:
                status_data['resources']['floating_ip_pools'] = {
                    'pools': 0,
                    'note': 'Floating IP pools not accessible',
                    'error': str(e)[:100]
                }
            
        except Exception as e:
            status_data['health']['issues'].append(f'Resource count error: {str(e)}')
        
        # Get quotas (enhanced with usage data)
        try:
            compute_quotas = conn.compute.get_quota_set(project_id)
            network_quotas = conn.network.get_quota(project_id)
            volume_quotas = conn.volume.get_quota_set(project_id)
            
            # Calculate current usage for compute resources
            current_vcpus_used = 0
            current_ram_used = 0
            
            # Always calculate from instances and their flavors for accurate usage
            for instance in instances:
                try:
                    # Get flavor information from instance
                    flavor_id = None
                    if hasattr(instance, 'flavor') and isinstance(instance.flavor, dict):
                        flavor_id = instance.flavor.get('id')
                    elif hasattr(instance, 'flavor') and hasattr(instance.flavor, 'id'):
                        flavor_id = instance.flavor.id
                    
                    flavor = None
                    if flavor_id:
                        try:
                            # Try to get flavor by ID first
                            flavor = conn.compute.get_flavor(flavor_id)
                        except Exception:
                            # If ID fails, try to find flavor by name
                            try:
                                flavors = list(conn.compute.flavors())
                                for f in flavors:
                                    if getattr(f, 'name', '') == flavor_id or getattr(f, 'id', '') == flavor_id:
                                        flavor = f
                                        break
                            except Exception as e2:
                                logger.warning(f"Could not find flavor {flavor_id} by name either: {e2}")
                    
                    if flavor:
                        vcpus = getattr(flavor, 'vcpus', 0)
                        ram_mb = getattr(flavor, 'ram', 0)
                        current_vcpus_used += vcpus if vcpus else 0
                        current_ram_used += ram_mb if ram_mb else 0
                        logger.info(f"Instance {getattr(instance, 'id', 'unknown')} using flavor {flavor_id}: {vcpus} vCPUs, {ram_mb} MB RAM")
                    else:
                        logger.warning(f"Could not find flavor info for instance {getattr(instance, 'id', 'unknown')} with flavor {flavor_id}")
                        
                except Exception as e:
                    logger.warning(f"Error processing instance {getattr(instance, 'id', 'unknown')}: {e}")
                    continue
            
            # Get hypervisor usage if available and non-zero, otherwise use instance calculation
            if 'hypervisors' in status_data['resources'] and status_data['resources']['hypervisors'].get('vcpus_used', 0) > 0:
                hv_vcpus_used = status_data['resources']['hypervisors']['vcpus_used']
                hv_ram_used = status_data['resources']['hypervisors']['memory_mb_used']
                # Use hypervisor data if it seems reasonable
                if hv_vcpus_used >= current_vcpus_used:
                    current_vcpus_used = hv_vcpus_used
                if hv_ram_used >= current_ram_used:
                    current_ram_used = hv_ram_used
            
            # Calculate current network ports usage
            current_ports_used = len(ports) if 'ports' in locals() else status_data['resources']['network'].get('ports', 0)
            
            status_data['quotas'] = {
                'compute': {
                    'instances': {
                        'used': len(instances),
                        'limit': getattr(compute_quotas, 'instances', -1)
                    },
                    'cores': {
                        'used': current_vcpus_used,
                        'limit': getattr(compute_quotas, 'cores', -1)
                    },
                    'ram': {
                        'used': current_ram_used,
                        'limit': getattr(compute_quotas, 'ram', -1)
                    }
                },
                'network': {
                    'networks': {
                        'used': len(networks),
                        'limit': getattr(network_quotas, 'networks', -1)
                    },
                    'subnets': {
                        'used': len(subnets),
                        'limit': getattr(network_quotas, 'subnets', -1)
                    },
                    'ports': {
                        'used': current_ports_used,
                        'limit': getattr(network_quotas, 'ports', -1)
                    },
                    'routers': {
                        'used': len(routers),
                        'limit': getattr(network_quotas, 'routers', -1)
                    },
                    'floatingips': {
                        'used': len(floating_ips),
                        'limit': getattr(network_quotas, 'floatingips', -1)
                    }
                },
                'volume': {
                    'volumes': {
                        'used': len(volumes),
                        'limit': getattr(volume_quotas, 'volumes', -1)
                    },
                    'snapshots': {
                        'used': len(snapshots),
                        'limit': getattr(volume_quotas, 'snapshots', -1)
                    },
                    'gigabytes': {
                        'used': total_volume_size,
                        'limit': getattr(volume_quotas, 'gigabytes', -1)
                    },
                    'backups': {
                        'used': len(backups),
                        'limit': getattr(volume_quotas, 'backups', -1)
                    },
                    'backup_gigabytes': {
                        'used': total_backup_size,
                        'limit': getattr(volume_quotas, 'backup_gigabytes', -1)
                    }
                }
            }
        except Exception as e:
            status_data['health']['issues'].append(f'Quota retrieval error: {str(e)}')
        
        # Determine overall health (enhanced)
        available_services = sum(1 for s in status_data['services'].values() if s.get('available', False))
        total_services = len(status_data['services'])
        
        # Health scoring based on multiple factors
        health_score = 0
        health_details = []
        max_score = 100
        
        # Service availability (40 points)
        service_score = (available_services / total_services) * 40 if total_services > 0 else 0
        health_score += service_score
        health_details.append(f"Service availability: {available_services}/{total_services} ({service_score:.1f}/40 points)")
        
        # Resource health (30 points)
        resource_score = 0
        try:
            # Check hypervisor health
            if 'hypervisors' in status_data['resources']:
                hv_data = status_data['resources']['hypervisors']
                if isinstance(hv_data, dict) and 'resource_utilization' in hv_data:
                    util = hv_data['resource_utilization']
                    # Penalize high utilization (>80% is concerning, >90% is critical)
                    cpu_util = util.get('vcpu_usage_percent', 0)
                    mem_util = util.get('memory_usage_percent', 0)
                    disk_util = util.get('disk_usage_percent', 0)
                    
                    avg_util = (cpu_util + mem_util + disk_util) / 3
                    if avg_util < 60:
                        resource_score = 30  # Excellent
                    elif avg_util < 75:
                        resource_score = 25  # Good
                    elif avg_util < 85:
                        resource_score = 20  # Moderate
                    elif avg_util < 95:
                        resource_score = 10  # High
                    else:
                        resource_score = 0   # Critical
                    
                    health_details.append(f"Resource utilization: {avg_util:.1f}% avg ({resource_score}/30 points)")
                else:
                    resource_score = 15  # Partial score if no detailed info
                    health_details.append("Resource utilization: limited data (15/30 points)")
            else:
                resource_score = 15  # Partial score if no hypervisor data
                health_details.append("Resource utilization: no data available (15/30 points)")
        except Exception:
            resource_score = 10  # Minimal score on error
            health_details.append("Resource utilization: error retrieving data (10/30 points)")
        
        health_score += resource_score
        
        # Instance health (20 points)
        instance_health_score = 0
        try:
            if 'compute' in status_data['resources'] and 'instance_states' in status_data['resources']['compute']:
                instance_states = status_data['resources']['compute']['instance_states']
                total_instances = sum(instance_states.values())
                
                if total_instances > 0:
                    active_instances = instance_states.get('ACTIVE', 0)
                    error_instances = instance_states.get('ERROR', 0) + instance_states.get('SUSPENDED', 0)
                    
                    # Score based on active vs error ratio
                    active_ratio = active_instances / total_instances
                    error_ratio = error_instances / total_instances
                    
                    if error_ratio == 0 and active_ratio > 0.8:
                        instance_health_score = 20  # Excellent
                    elif error_ratio < 0.05:
                        instance_health_score = 18  # Very good
                    elif error_ratio < 0.1:
                        instance_health_score = 15  # Good
                    elif error_ratio < 0.2:
                        instance_health_score = 10  # Moderate
                    else:
                        instance_health_score = 5   # Poor
                    
                    health_details.append(f"Instance health: {active_instances} active, {error_instances} error ({instance_health_score}/20 points)")
                else:
                    instance_health_score = 20  # Perfect score if no instances
                    health_details.append("Instance health: no instances (20/20 points)")
            else:
                instance_health_score = 10  # Partial score
                health_details.append("Instance health: limited data (10/20 points)")
        except Exception:
            instance_health_score = 5  # Minimal score on error
            health_details.append("Instance health: error retrieving data (5/20 points)")
        
        health_score += instance_health_score
        
        # Load balancer health (10 points)
        lb_health_score = 0
        try:
            if 'load_balancer' in status_data['resources']:
                lb_data = status_data['resources']['load_balancer']
                if isinstance(lb_data, dict) and 'load_balancers' in lb_data:
                    total_lbs = lb_data.get('load_balancers', 0)
                    
                    if total_lbs == 0:
                        lb_health_score = 10  # No load balancers is fine
                        health_details.append("Load balancer health: no load balancers (10/10 points)")
                    elif 'lb_states' in lb_data:
                        lb_states = lb_data['lb_states']
                        active_lbs = lb_states.get('ACTIVE', 0)
                        error_lbs = lb_states.get('ERROR', 0)
                        
                        if error_lbs == 0:
                            lb_health_score = 10  # Perfect
                        elif error_lbs / total_lbs < 0.1:
                            lb_health_score = 8   # Good
                        elif error_lbs / total_lbs < 0.2:
                            lb_health_score = 6   # Moderate
                        else:
                            lb_health_score = 3   # Poor
                        
                        health_details.append(f"Load balancer health: {active_lbs} active, {error_lbs} error ({lb_health_score}/10 points)")
                    else:
                        lb_health_score = 5  # Partial score
                        health_details.append("Load balancer health: limited data (5/10 points)")
                else:
                    lb_health_score = 8  # Most points if service not available (not critical)
                    health_details.append("Load balancer health: service not available (8/10 points)")
            else:
                lb_health_score = 8  # Most points if no LB data
                health_details.append("Load balancer health: no data available (8/10 points)")
        except Exception:
            lb_health_score = 5  # Partial score on error
            health_details.append("Load balancer health: error retrieving data (5/10 points)")
        
        health_score += lb_health_score
        
        # Determine overall health status
        if health_score >= 90:
            overall_health = 'excellent'
        elif health_score >= 80:
            overall_health = 'healthy'
        elif health_score >= 70:
            overall_health = 'good'
        elif health_score >= 60:
            overall_health = 'degraded'
        elif health_score >= 40:
            overall_health = 'poor'
        else:
            overall_health = 'critical'
        
        status_data['health']['overall'] = overall_health
        status_data['health']['service_availability'] = f"{available_services}/{total_services}"
        status_data['health']['health_score'] = round(health_score, 1)
        status_data['health']['max_score'] = max_score
        status_data['health']['health_details'] = health_details
        
        # Add cluster summary
        status_data['cluster_summary'] = {
            'total_services': total_services,
            'available_services': available_services,
            'total_instances': status_data['resources']['compute'].get('instances', 0),
            'total_networks': status_data['resources']['network'].get('networks', 0),
            'total_volumes': status_data['resources']['volume'].get('volumes', 0),
            'total_backups': status_data['resources']['volume'].get('backups', 0),
            'total_images': status_data['resources']['image'].get('images', 0),
            'total_floating_ips': status_data['resources']['network'].get('floating_ips', 0),
            'health_status': overall_health,
            'health_score': f"{round(health_score, 1)}/{max_score}"
        }
        
        if 'load_balancer' in status_data['resources']:
            status_data['cluster_summary']['total_load_balancers'] = status_data['resources']['load_balancer'].get('load_balancers', 0)
        
        if 'hypervisors' in status_data['resources']:
            hv_data = status_data['resources']['hypervisors']
            if isinstance(hv_data, dict):
                status_data['cluster_summary']['total_hypervisors'] = hv_data.get('hypervisors', 0)
                if 'resource_utilization' in hv_data:
                    util = hv_data['resource_utilization']
                    status_data['cluster_summary']['avg_resource_utilization'] = f"{((util.get('vcpu_usage_percent', 0) + util.get('memory_usage_percent', 0) + util.get('disk_usage_percent', 0)) / 3):.1f}%"
        
        return status_data
        
    except Exception as e:
        logger.error(f"Failed to get cluster status: {e}")
        return {
            'cluster_info': {
                'project_name': 'unknown',
                'project_id': 'unknown',
                'check_time': datetime.now().isoformat()
            },
            'services': {},
            'resources': {},
            'quotas': {},
            'health': {
                'overall': 'error',
                'issues': [f'Cluster status check failed: {str(e)}']
            },
            'error': str(e)
        }


def get_service_status(service_name: str = "") -> Dict[str, Any]:
    """
    Get detailed status for specific OpenStack services.
    
    Args:
        service_name: Name of service to check (compute, network, volume, image, identity, orchestration)
                     If empty, returns status for all services
    
    Returns:
        Dict containing service status information
    """
    try:
        conn = get_openstack_connection()
        
        if not service_name:
            # Return status for all services instead of using get_cluster_status
            services = ['compute', 'network', 'volume', 'image', 'identity', 'orchestration']
            all_services = {}
            
            for service in services:
                try:
                    service_status = {
                        'available': True,
                        'endpoint': 'unknown',
                        'version': 'unknown',
                        'last_check': datetime.now().isoformat()
                    }
                    
                    if service == 'compute':
                        # Test compute service
                        list(conn.compute.servers(limit=1))
                        service_status['endpoint'] = conn.compute.get_endpoint()
                        
                    elif service == 'network':
                        # Test network service
                        list(conn.network.networks(limit=1))
                        service_status['endpoint'] = conn.network.get_endpoint()
                        
                    elif service == 'volume':
                        # Test volume service
                        list(conn.volume.volumes(limit=1))
                        service_status['endpoint'] = conn.volume.get_endpoint()
                        
                    elif service == 'image':
                        # Test image service
                        list(conn.image.images(limit=1))
                        service_status['endpoint'] = conn.image.get_endpoint()
                        
                    elif service == 'identity':
                        # Test identity service
                        conn.identity.get_token()
                        try:
                            service_status['endpoint'] = conn.session.get_endpoint(service_type='identity', interface='public')
                        except Exception:
                            service_status['endpoint'] = f"http://{os.environ.get('OS_AUTH_HOST', 'localhost')}:{os.environ.get('OS_AUTH_PORT', '5000')}"
                        
                    elif service == 'orchestration':
                        # Test orchestration service (Heat) with manual API call
                        try:
                            import requests
                            
                            # Get project ID and token
                            project_id = conn.current_project_id
                            token = conn.identity.get_token()
                            
                            # Construct Heat API URL
                            auth_host = os.environ.get('OS_AUTH_HOST', 'localhost')
                            heat_port = os.environ.get('OS_HEAT_STACK_PORT', '8004')
                            heat_url = f"http://{auth_host}:{heat_port}/v1/{project_id}/stacks"
                            
                            headers = {
                                'X-Auth-Token': token,
                                'Content-Type': 'application/json'
                            }
                            
                            # Make a test call to Heat API (get stacks)
                            response = requests.get(heat_url, headers=headers, timeout=10)
                            
                            if response.status_code in [200, 404]:  # 404 is OK - means no stacks
                                service_status['endpoint'] = f"http://{auth_host}:{heat_port}"
                                service_status['version'] = 'v1'
                            else:
                                raise Exception(f"Heat API returned status {response.status_code}")
                                
                        except Exception as heat_e:
                            logger.warning(f"Heat service test failed: {heat_e}")
                            service_status['available'] = False
                            service_status['error'] = str(heat_e)
                    
                    all_services[service] = service_status
                    
                except Exception as e:
                    all_services[service] = {
                        'available': False,
                        'error': str(e),
                        'last_check': datetime.now().isoformat()
                    }
            
            return all_services
        
        service_name = service_name.lower()
        supported_services = ['compute', 'network', 'volume', 'image', 'identity', 'orchestration']
        
        if service_name not in supported_services:
            return {
                'success': False,
                'error': f'Unsupported service: {service_name}',
                'supported_services': supported_services
            }
        
        service_status = {
            'service': service_name,
            'available': False,
            'endpoint': 'unknown',
            'version': 'unknown',
            'details': {},
            'check_time': datetime.now().isoformat()
        }
        
        try:
            if service_name == 'compute':
                # Detailed compute service check
                service_status['endpoint'] = conn.compute.get_endpoint()
                hypervisors = list(conn.compute.hypervisors())
                services = list(conn.compute.services())
                flavors = list(conn.compute.flavors())
                
                service_status['available'] = True
                service_status['details'] = {
                    'hypervisors': len(hypervisors),
                    'compute_services': len(services),
                    'flavors': len(flavors),
                    'hypervisor_list': [h.name for h in hypervisors[:5]]  # First 5 hypervisors
                }
                
            elif service_name == 'network':
                # Detailed network service check
                service_status['endpoint'] = conn.network.get_endpoint()
                networks = list(conn.network.networks())
                agents = list(conn.network.agents())
                
                service_status['available'] = True
                service_status['details'] = {
                    'networks': len(networks),
                    'agents': len(agents),
                    'public_networks': len([n for n in networks if getattr(n, 'is_router_external', False)]),
                    'private_networks': len([n for n in networks if not getattr(n, 'is_router_external', False)])
                }
                
            elif service_name == 'volume':
                # Detailed volume service check
                service_status['endpoint'] = conn.volume.get_endpoint()
                volumes = list(conn.volume.volumes())
                volume_types = list(conn.volume.types())
                
                service_status['available'] = True
                service_status['details'] = {
                    'volumes': len(volumes),
                    'volume_types': len(volume_types),
                    'available_volumes': len([v for v in volumes if v.status == 'available']),
                    'in_use_volumes': len([v for v in volumes if v.status == 'in-use'])
                }
                
            elif service_name == 'image':
                # Detailed image service check
                service_status['endpoint'] = conn.image.get_endpoint()
                images = list(conn.image.images())
                
                service_status['available'] = True
                service_status['details'] = {
                    'images': len(images),
                    'active_images': len([i for i in images if i.status == 'active']),
                    'public_images': len([i for i in images if getattr(i, 'visibility', '') == 'public']),
                    'private_images': len([i for i in images if getattr(i, 'visibility', '') == 'private'])
                }
                
            elif service_name == 'identity':
                # Detailed identity service check
                try:
                    service_status['endpoint'] = conn.session.get_endpoint(service_type='identity', interface='public')
                except Exception:
                    service_status['endpoint'] = f"http://{os.environ.get('OS_AUTH_HOST', 'localhost')}:{os.environ.get('OS_AUTH_PORT', '5000')}"
                projects = list(conn.identity.projects())
                users = list(conn.identity.users())
                roles = list(conn.identity.roles())
                
                service_status['available'] = True
                service_status['details'] = {
                    'projects': len(projects),
                    'users': len(users),
                    'roles': len(roles),
                    'enabled_projects': len([p for p in projects if p.is_enabled])
                }
                
            elif service_name == 'orchestration':
                # Detailed orchestration service check with direct API call
                try:
                    import requests
                    import os
                    
                    # Get project ID and token
                    project_id = conn.current_project_id
                    token = conn.identity.get_token()
                    
                    # Construct Heat API URL
                    auth_host = os.environ.get('OS_AUTH_HOST', 'localhost')
                    heat_port = os.environ.get('OS_HEAT_STACK_PORT', '8004')
                    heat_url = f"http://{auth_host}:{heat_port}/v1/{project_id}/stacks"
                    
                    headers = {'X-Auth-Token': token}
                    
                    # Test Heat API with timeout
                    response = requests.get(heat_url, headers=headers, timeout=10)
                    
                    if response.status_code == 200:
                        data = response.json()
                        stacks = data.get('stacks', [])
                        
                        # Also check Heat engine services status
                        heat_services = []
                        try:
                            services_url = f"http://{auth_host}:{heat_port}/v1/{project_id}/services"
                            services_response = requests.get(services_url, headers=headers, timeout=5)
                            
                            if services_response.status_code == 200:
                                services_data = services_response.json()
                                heat_services = services_data.get('services', [])
                        except Exception as services_error:
                            logger.warning(f"Could not fetch Heat services details: {services_error}")
                        
                        # Analyze Heat engine status
                        up_services = [s for s in heat_services if s.get('status') == 'up']
                        down_services = [s for s in heat_services if s.get('status') == 'down']
                        
                        service_status['endpoint'] = f"http://{auth_host}:{heat_port}/v1"
                        service_status['available'] = True
                        service_status['details'] = {
                            'stacks': len(stacks),
                            'create_complete': len([s for s in stacks if s.get('stack_status') == 'CREATE_COMPLETE']),
                            'create_failed': len([s for s in stacks if s.get('stack_status') == 'CREATE_FAILED']),
                            'update_complete': len([s for s in stacks if s.get('stack_status') == 'UPDATE_COMPLETE']),
                            'other_status': len([s for s in stacks if s.get('stack_status') not in ['CREATE_COMPLETE', 'CREATE_FAILED', 'UPDATE_COMPLETE']]),
                            'api_version': 'v1',
                            'api_accessible': True,
                            'heat_engines': {
                                'total': len(heat_services),
                                'up': len(up_services),
                                'down': len(down_services),
                                'all_engines_running': len(heat_services) > 0 and len(down_services) == 0,
                                'engines_summary': f"{len(up_services)}/{len(heat_services)} engines up" if heat_services else "engines status unknown"
                            }
                        }
                        logger.info(f"Heat detailed check successful: {len(stacks)} stacks found, {len(up_services)}/{len(heat_services)} engines up")
                    else:
                        raise Exception(f"Heat API returned {response.status_code}: {response.text[:100]}")
                        
                except requests.exceptions.Timeout:
                    logger.warning("Heat detailed check timeout")
                    service_status['available'] = False
                    service_status['endpoint'] = 'timeout'
                    service_status['error'] = 'Detailed API call timeout (10s)'
                    service_status['details'] = {
                        'stacks': 0,
                        'note': 'API call timed out'
                    }
                
        except Exception as e:
            service_status['available'] = False
            service_status['error'] = str(e)
        
        return {
            'success': service_status['available'],
            'service_status': service_status
        }
        
    except Exception as e:
        logger.error(f"Failed to get service status: {e}")
        return {
            'success': False,
            'error': str(e),
            'service': service_name or 'all'
        }
