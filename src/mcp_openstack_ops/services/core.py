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


def get_cluster_status() -> Dict[str, Any]:
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
            
            status_data['resources']['compute'] = {
                'instances': len(instances),
                'flavors': len(flavors),
                'keypairs': len(keypairs)
            }
            
            # Network resources
            networks = list(conn.network.networks())
            subnets = list(conn.network.subnets())
            routers = list(conn.network.routers())
            floating_ips = list(conn.network.ips())
            security_groups = list(conn.network.security_groups())
            
            status_data['resources']['network'] = {
                'networks': len(networks),
                'subnets': len(subnets),
                'routers': len(routers),
                'floating_ips': len(floating_ips),
                'security_groups': len(security_groups)
            }
            
            # Volume resources
            volumes = list(conn.volume.volumes())
            snapshots = list(conn.volume.snapshots())
            
            status_data['resources']['volume'] = {
                'volumes': len(volumes),
                'snapshots': len(snapshots)
            }
            
            # Image resources
            images = list(conn.image.images())
            status_data['resources']['image'] = {
                'images': len(images)
            }
            
        except Exception as e:
            status_data['health']['issues'].append(f'Resource count error: {str(e)}')
        
        # Get quotas
        try:
            compute_quotas = conn.compute.get_quota_set(project_id)
            network_quotas = conn.network.get_quota(project_id)
            volume_quotas = conn.volume.get_quota_set(project_id)
            
            status_data['quotas'] = {
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
                    'floatingips': getattr(network_quotas, 'floatingips', -1)
                },
                'volume': {
                    'volumes': getattr(volume_quotas, 'volumes', -1),
                    'snapshots': getattr(volume_quotas, 'snapshots', -1),
                    'gigabytes': getattr(volume_quotas, 'gigabytes', -1)
                }
            }
        except Exception as e:
            status_data['health']['issues'].append(f'Quota retrieval error: {str(e)}')
        
        # Determine overall health
        available_services = sum(1 for s in status_data['services'].values() if s.get('available', False))
        total_services = len(status_data['services'])
        
        if available_services == total_services:
            status_data['health']['overall'] = 'healthy'
        elif available_services >= total_services * 0.7:  # 70% or more services available
            status_data['health']['overall'] = 'degraded'
        else:
            status_data['health']['overall'] = 'unhealthy'
        
        status_data['health']['service_availability'] = f"{available_services}/{total_services}"
        
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
            # Return status for all services
            return get_cluster_status()['services']
        
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
