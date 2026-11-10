"""
OpenStack Core Connection and Cluster Management Functions

This module contains core functions for OpenStack connection management and cluster-wide operations.
"""

import os
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from ..connection import get_openstack_connection, reset_connection_cache
from .. import user_connection

# Configure logging
logger = logging.getLogger(__name__)


def _probe_request_options(conn) -> Dict[str, Any]:
    """Protect user tokens without changing legacy probe TLS behavior."""
    if user_connection.enabled:
        return {"verify": conn.session.verify, "allow_redirects": False}
    return {}


# get_cluster_status function removed - use combination of get_* tools for comprehensive cluster reports


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
                            service_status['endpoint'] = f"{user_connection.service_protocol()}://{os.environ.get('OS_AUTH_HOST', 'localhost')}:{os.environ.get('OS_AUTH_PORT', '5000')}"
                        
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
                            heat_url = f"{user_connection.service_protocol()}://{auth_host}:{heat_port}/v1/{project_id}/stacks"
                            
                            headers = {
                                'X-Auth-Token': token,
                                'Content-Type': 'application/json'
                            }
                            
                            # Make a test call to Heat API (get stacks)
                            response = requests.get(heat_url, headers=headers, timeout=10, **_probe_request_options(conn))
                            
                            if response.status_code in [200, 404]:  # 404 is OK - means no stacks
                                service_status['endpoint'] = f"{user_connection.service_protocol()}://{auth_host}:{heat_port}"
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
                    service_status['endpoint'] = f"{user_connection.service_protocol()}://{os.environ.get('OS_AUTH_HOST', 'localhost')}:{os.environ.get('OS_AUTH_PORT', '5000')}"
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

                    # Get project ID and token
                    project_id = conn.current_project_id
                    token = conn.identity.get_token()
                    
                    # Construct Heat API URL
                    auth_host = os.environ.get('OS_AUTH_HOST', 'localhost')
                    heat_port = os.environ.get('OS_HEAT_STACK_PORT', '8004')
                    heat_url = f"{user_connection.service_protocol()}://{auth_host}:{heat_port}/v1/{project_id}/stacks"
                    
                    headers = {'X-Auth-Token': token}
                    
                    # Test Heat API with timeout
                    response = requests.get(heat_url, headers=headers, timeout=10, **_probe_request_options(conn))
                    
                    if response.status_code == 200:
                        data = response.json()
                        stacks = data.get('stacks', [])
                        
                        # Also check Heat engine services status
                        heat_services = []
                        try:
                            services_url = f"{user_connection.service_protocol()}://{auth_host}:{heat_port}/v1/{project_id}/services"
                            services_response = requests.get(services_url, headers=headers, timeout=5, **_probe_request_options(conn))
                            
                            if services_response.status_code == 200:
                                services_data = services_response.json()
                                heat_services = services_data.get('services', [])
                        except Exception as services_error:
                            logger.warning(f"Could not fetch Heat services details: {services_error}")
                        
                        # Analyze Heat engine status
                        up_services = [s for s in heat_services if s.get('status') == 'up']
                        down_services = [s for s in heat_services if s.get('status') == 'down']
                        
                        service_status['endpoint'] = f"{user_connection.service_protocol()}://{auth_host}:{heat_port}/v1"
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
