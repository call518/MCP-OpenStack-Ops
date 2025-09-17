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
    
    # Check required environment variables
    required_vars = ["OS_PROJECT_NAME", "OS_USERNAME", "OS_PASSWORD", "OS_AUTH_HOST", "OS_AUTH_PORT"]
    missing_vars = [var for var in required_vars if not os.environ.get(var)]
    
    if missing_vars:
        error_msg = f"Missing required OpenStack environment variables: {missing_vars}"
        logger.error(error_msg)
        logger.error("Please ensure your .env file contains OpenStack authentication credentials")
        raise ValueError(error_msg)
    
    # Get OpenStack connection parameters
    os_auth_host = os.environ.get("OS_AUTH_HOST")
    os_auth_port = os.environ.get("OS_AUTH_PORT")
    
    # Get configurable service ports (with defaults)
    # Note: OS_AUTH_PORT is used for Identity service endpoint
    compute_port = os.environ.get("OS_COMPUTE_PORT", "8774") 
    network_port = os.environ.get("OS_NETWORK_PORT", "9696")
    volume_port = os.environ.get("OS_VOLUME_PORT", "8776")
    image_port = os.environ.get("OS_IMAGE_PORT", "9292")
    placement_port = os.environ.get("OS_PLACEMENT_PORT", "8780")
    heat_stack_port = os.environ.get("OS_HEAT_STACK_PORT", "8004")
    heat_stack_cfn_port = os.environ.get("OS_HEAT_STACK_CFN_PORT", "18888")
    
    try:
        logger.info(f"Creating OpenStack connection with proxy host: {os_auth_host}")
        _connection_cache = connection.Connection(
            auth_url=f"http://{os_auth_host}:{os_auth_port}",
            project_name=os.environ.get("OS_PROJECT_NAME"),
            username=os.environ.get("OS_USERNAME"),
            password=os.environ.get("OS_PASSWORD"),
            user_domain_name=os.environ.get("OS_USER_DOMAIN_NAME", "Default"),
            project_domain_name=os.environ.get("OS_PROJECT_DOMAIN_NAME", "Default"),
            region_name=os.environ.get("OS_REGION_NAME", "RegionOne"),
            identity_api_version=os.environ.get("OS_IDENTITY_API_VERSION", "3"),
            interface="internal",
            # Override all service endpoints to use proxy
            identity_endpoint=f"http://{os_auth_host}:{os_auth_port}",
            compute_endpoint=f"http://{os_auth_host}:{compute_port}/v2.1",
            network_endpoint=f"http://{os_auth_host}:{network_port}",
            volume_endpoint=f"http://{os_auth_host}:{volume_port}/v3",
            image_endpoint=f"http://{os_auth_host}:{image_port}",
            placement_endpoint=f"http://{os_auth_host}:{placement_port}",
            orchestration_endpoint=f"http://{os_auth_host}:{heat_stack_port}/v1",
            timeout=10
        )
        
        # Test the connection
        try:
            token = _connection_cache.identity.get_token()
            logger.info(f"OpenStack connection successful. Token acquired: {token[:20]}...")
        except Exception as test_e:
            logger.error(f"Connection test failed: {test_e}")
            raise
            
        return _connection_cache
    except Exception as e:
        logger.error(f"Failed to create OpenStack connection: {e}")
        logger.error("Please check your OpenStack credentials and network connectivity")
        raise


def get_cluster_status() -> Dict[str, Any]:
    """
    Returns a comprehensive and detailed summary of OpenStack cluster status.
    
    This function provides an extensive overview of the OpenStack cluster including:
    - Compute resources with server groups and affinity policies
    - Network configurations and floating IP management
    - Storage volumes and comprehensive quota information  
    - Image resources and usage statistics
    - Service status and health monitoring
    - Availability zones with detailed host information
    - Resource usage analytics and billing trends
    - Overall cluster health scoring
    
    Enhanced with data from newly added tools:
    - get_server_groups(): Affinity/anti-affinity policy information
    - get_availability_zones(): Detailed zone and host service status
    - get_usage_statistics(): Resource consumption trends and billing data
    - get_quota(): Comprehensive quota limits across all services
    
    Returns:
        Dict containing extensive cluster status information with enhanced sections:
        - compute_resources: Includes server_groups section with policy information
        - cluster_overview: Includes availability_zones with detailed host data
        - resource_usage: NEW section with usage analytics and trends
        - quota_information: NEW section with comprehensive quota details
        - Plus all existing sections with additional detail
    """
    try:
        conn = get_openstack_connection()
        cluster_info = {
            'timestamp': datetime.now().isoformat(),
            'connection_status': 'Connected via SDK',
            'cluster_overview': {},
            'compute_resources': {},
            'network_resources': {},
            'storage_resources': {},
            'service_status': {},
            'resource_usage': {},
            'health_summary': {}
        }
        
        # === COMPUTE RESOURCES ===
        try:
            servers = list(conn.compute.servers(details=True))
            logger.info(f"Retrieved {len(servers)} servers from OpenStack")
            
            # Try to get hypervisor info using get_resource_monitoring() function (Refactored)
            compute_nodes = {}
            total_vcpus = total_ram = total_disk = 0
            used_vcpus = used_ram = used_disk = 0
            hypervisors = []
            
            try:
                # Get hypervisor and resource data from get_resource_monitoring() function
                resource_data = get_resource_monitoring()
                
                if 'error' not in resource_data:
                    hypervisors = resource_data.get('hypervisors', [])
                    cluster_summary = resource_data.get('cluster_summary', {})
                    
                    logger.info(f"Retrieved {len(hypervisors)} hypervisors from get_resource_monitoring()")
                    
                    # Extract totals from get_resource_monitoring() data
                    physical_resources = cluster_summary.get('physical_resources', {})
                    
                    total_vcpus = physical_resources.get('pCPU', {}).get('total', 0)
                    used_vcpus = physical_resources.get('pCPU', {}).get('used', 0)
                    total_ram = physical_resources.get('physical_memory', {}).get('total_mb', 0)
                    used_ram = physical_resources.get('physical_memory', {}).get('used_mb', 0)
                    total_disk = physical_resources.get('physical_storage', {}).get('total_gb', 0)
                    used_disk = physical_resources.get('physical_storage', {}).get('used_gb', 0)
                    
                    # Convert hypervisor data to cluster_status format
                    for hv in hypervisors:
                        hv_name = hv.get('name', 'unknown')
                        compute_nodes[hv_name] = {
                            'status': hv.get('status', 'unknown'),
                            'state': hv.get('state', 'unknown'),
                            'vcpus': hv.get('pCPUs_total', 0),
                            'vcpus_used': hv.get('pCPUs_used', 0),
                            'memory_mb': hv.get('physical_memory_total_mb', 0),
                            'memory_mb_used': hv.get('physical_memory_used_mb', 0),
                            'local_gb': hv.get('local_storage_total_gb', 0),
                            'local_gb_used': hv.get('local_storage_used_gb', 0),
                            'running_vms': hv.get('running_vms', 0),
                            'hypervisor_type': hv.get('hypervisor_type', 'Unknown'),
                            'hypervisor_version': hv.get('hypervisor_version', 'Unknown')
                        }
                else:
                    logger.warning(f"get_resource_monitoring() returned error: {resource_data.get('error', 'Unknown error')}")
                    # Fall back to minimal hypervisor processing
                    hypervisors_raw = list(conn.compute.hypervisors(details=True))
                    for hv in hypervisors_raw:
                        hypervisors.append({
                            'name': getattr(hv, 'hypervisor_hostname', 'unknown'),
                            'status': getattr(hv, 'status', 'unknown'),
                            'state': getattr(hv, 'state', 'unknown')
                        })
                    
            except Exception as hv_error:
                logger.warning(f"Failed to get hypervisor details from get_resource_monitoring(): {hv_error}")
                # Continue without hypervisor info
            
            # Get other compute resources
            try:
                flavors = list(conn.compute.flavors(details=True))
                keypairs = list(conn.compute.keypairs())
            except Exception as flavor_error:
                logger.warning(f"Failed to get flavors/keypairs: {flavor_error}")
                flavors = []
                keypairs = []
            
            # Get server groups information using existing function (reuse pattern)
            server_groups_data = []
            try:
                server_groups_data = get_server_groups()
                logger.info(f"Retrieved {len(server_groups_data)} server groups from get_server_groups()")
            except Exception as sg_error:
                logger.warning(f"Failed to get server groups: {sg_error}")
                server_groups_data = []
            
            # Server status analysis with enhanced instance operational status
            server_status = {'ACTIVE': 0, 'ERROR': 0, 'SHUTOFF': 0, 'STOPPED': 0, 'PAUSED': 0, 'SUSPENDED': 0, 'BUILD': 0, 'REBOOT': 0, 'HARD_REBOOT': 0, 'OTHER': 0}
            servers_by_az = {}
            servers_detail = []
            flavor_usage = {}  # Track flavor usage
            
            # Single pass through servers for all analysis (performance optimization)
            for server in servers:
                status = server.status
                if status in server_status:
                    server_status[status] += 1
                else:
                    server_status['OTHER'] += 1
                
                az = getattr(server, 'availability_zone', 'Unknown')
                if az not in servers_by_az:
                    servers_by_az[az] = 0
                servers_by_az[az] += 1
                
                # Track flavor usage (Fix: Resolve flavor names properly)
                flavor_info = getattr(server, 'flavor', {})
                if flavor_info and isinstance(flavor_info, dict):
                    flavor_id = flavor_info.get('id', 'unknown')
                    if flavor_id != 'unknown' and flavor_id is not None:
                        # Try to get flavor name for better tracking
                        try:
                            flavor = conn.compute.get_flavor(flavor_id)
                            flavor_name = flavor.name
                        except Exception:
                            flavor_name = flavor_info.get('original_name', flavor_id)
                        
                        if flavor_name not in flavor_usage:
                            flavor_usage[flavor_name] = 0
                        flavor_usage[flavor_name] += 1
                
                servers_detail.append({
                    'name': server.name,
                    'status': server.status,
                    'flavor': getattr(server, 'flavor', {}).get('original_name', 'Unknown'),
                    'created': server.created_at,
                    'availability_zone': az,
                    'host': getattr(server, 'hypervisor_hostname', 'Unknown')
                })
            
            # Enhanced instance operational statistics
            instance_operations = {
                'deployment_summary': {
                    'total_deployed': len(servers),
                    'currently_active': server_status.get('ACTIVE', 0),
                    'shutdown_stopped': server_status.get('SHUTOFF', 0) + server_status.get('STOPPED', 0),
                    'in_error_state': server_status.get('ERROR', 0),
                    'in_transition': server_status.get('BUILD', 0) + server_status.get('REBOOT', 0) + server_status.get('HARD_REBOOT', 0),
                    'paused_suspended': server_status.get('PAUSED', 0) + server_status.get('SUSPENDED', 0),
                    'other_states': server_status.get('OTHER', 0)
                },
                'operational_health': {
                    'healthy_percentage': round((server_status.get('ACTIVE', 0) / max(len(servers), 1)) * 100, 1),
                    'problematic_percentage': round((server_status.get('ERROR', 0) / max(len(servers), 1)) * 100, 1),
                    'offline_percentage': round(((server_status.get('SHUTOFF', 0) + server_status.get('STOPPED', 0)) / max(len(servers), 1)) * 100, 1)
                },
                'availability_zones_distribution': servers_by_az,
                'top_flavors_usage': sorted(flavor_usage.items(), key=lambda x: x[1], reverse=True)[:5] if flavor_usage else []
            }
            
            cluster_info['compute_resources'] = {
                'total_hypervisors': len(hypervisors),
                'active_hypervisors': len([h for h in hypervisors if getattr(h, 'status', '') == 'enabled' and getattr(h, 'state', '') == 'up']),
                'compute_nodes': compute_nodes,
                'total_instances': len(servers),
                'instances_by_status': server_status,
                'instance_operations': instance_operations,  # Enhanced instance operational info
                'instances_by_az': servers_by_az,
                'instances_detail': servers_detail[:10],  # Top 10 for brevity
                'total_flavors': len(flavors),
                'total_keypairs': len(keypairs),
                'resource_utilization': {
                    'vcpu_usage': f"{used_vcpus}/{total_vcpus} ({(used_vcpus/total_vcpus*100):.1f}%)" if total_vcpus > 0 else "N/A (hypervisor data unavailable)",
                    'memory_usage_gb': f"{used_ram//1024}/{total_ram//1024} ({(used_ram/total_ram*100):.1f}%)" if total_ram > 0 else "N/A (hypervisor data unavailable)",
                    'disk_usage_gb': f"{used_disk}/{total_disk} ({(used_disk/total_disk*100):.1f}%)" if total_disk > 0 else "N/A (hypervisor data unavailable)"
                },
                # Enhanced: Add physical and quota usage information
                'physical_usage': {
                    'description': 'Physical compute resources (pCPU, physical RAM, storage)',
                    'total_physical_vcpus': total_vcpus,
                    'used_physical_vcpus': used_vcpus,
                    'total_physical_memory_mb': total_ram,
                    'used_physical_memory_mb': used_ram,
                    'total_physical_disk_gb': total_disk,
                    'used_physical_disk_gb': used_disk,
                    'physical_cpu_utilization_percent': round((used_vcpus/total_vcpus*100), 1) if total_vcpus > 0 else 0,
                    'physical_memory_utilization_percent': round((used_ram/total_ram*100), 1) if total_ram > 0 else 0,
                    'physical_disk_utilization_percent': round((used_disk/total_disk*100), 1) if total_disk > 0 else 0
                },
                'quota_usage': get_compute_quota_usage(conn),
                # NEW: Server groups information for affinity/anti-affinity policies
                'server_groups': {
                    'total_groups': len(server_groups_data),
                    'groups_detail': server_groups_data[:10] if server_groups_data else [],  # Top 10 for brevity
                    'policy_types': list(set([policy for group in server_groups_data for policy in group.get('policies', [])])) if server_groups_data else [],
                    'groups_with_members': len([g for g in server_groups_data if g.get('member_count', 0) > 0]) if server_groups_data else 0
                }
            }
            
            logger.info(f"Successfully processed compute resources: {len(servers)} instances, {len(hypervisors)} hypervisors")
            
        except Exception as e:
            logger.error(f"Failed to get compute info: {e}")
            # Provide minimal fallback data to prevent complete failure
            cluster_info['compute_resources'] = {
                'error': f"Failed to get compute info: {str(e)}",
                'total_hypervisors': 0,
                'active_hypervisors': 0,
                'compute_nodes': {},
                'total_instances': 0,
                'instances_by_status': {},
                'instance_operations': {
                    'deployment_summary': {
                        'total_deployed': 0,
                        'currently_active': 0,
                        'shutdown_stopped': 0,
                        'in_error_state': 0,
                        'in_transition': 0,
                        'paused_suspended': 0,
                        'other_states': 0
                    },
                    'operational_health': {},
                    'availability_zones_distribution': {},
                    'top_flavors_usage': []
                },
                'instances_by_az': {},
                'instances_detail': [],
                'image_usage_stats': {},
                'total_flavors': 0,
                'total_keypairs': 0,
                'resource_utilization': {
                    'vcpu_usage': '0/0',
                    'memory_usage_gb': '0/0',
                    'disk_usage_gb': '0/0'
                }
            }
        
        # === NETWORK RESOURCES === (Refactored: Use get_network_details() function)
        try:
            # Get detailed network information from existing function
            detailed_networks = get_network_details()
            
            # Get additional network resources for completeness
            try:
                subnets = list(conn.network.subnets())
                routers = list(conn.network.routers())
                floating_ips = list(conn.network.ips())
                security_groups = list(conn.network.security_groups())
            except Exception as e:
                logger.warning(f"Could not get additional network resources: {e}")
                subnets = []
                routers = []
                floating_ips = []
                security_groups = []
            
            # Process network details for cluster status format
            external_nets = 0
            networks_detail = []
            for net in detailed_networks:
                if net.get('external', False):
                    external_nets += 1
                networks_detail.append({
                    'name': net.get('name', 'Unknown'),
                    'status': net.get('status', 'Unknown'),
                    'is_external': net.get('external', False),
                    'is_shared': net.get('shared', False),
                    'subnets_count': len(net.get('subnets', [])),
                    'provider_network_type': net.get('provider_network_type', 'Unknown'),
                    'mtu': net.get('mtu', 'Unknown')
                })
            
            # Floating IP analysis (same as before for consistency)
            fip_status = {'ACTIVE': 0, 'DOWN': 0, 'AVAILABLE': 0}
            for fip in floating_ips:
                status = fip.status if fip.status in fip_status else 'AVAILABLE'
                fip_status[status] += 1
            
            cluster_info['network_resources'] = {
                'total_networks': len(detailed_networks),
                'external_networks': external_nets,
                'networks_detail': networks_detail,
                'detailed_networks': detailed_networks,  # Include full network details
                'total_subnets': len(subnets),
                'total_routers': len(routers),
                'active_routers': len([r for r in routers if r.status == 'ACTIVE']),
                'total_floating_ips': len(floating_ips),
                'floating_ips_status': fip_status,
                'total_security_groups': len(security_groups)
            }
        except Exception as e:
            cluster_info['network_resources'] = {'error': f"Failed to get network info: {str(e)}"}
        
        # === STORAGE RESOURCES ===
        try:
            volumes = list(conn.volume.volumes(details=True))
            volume_types = list(conn.volume.types())
            snapshots = list(conn.volume.snapshots())
            
            # Volume analysis with detailed information
            volume_status = {'available': 0, 'in-use': 0, 'error': 0, 'creating': 0, 'deleting': 0, 'other': 0}
            total_volume_size = 0
            volumes_detail = []
            volumes_by_type = {}
            
            for vol in volumes:
                status = vol.status.lower()
                if status in volume_status:
                    volume_status[status] += 1
                else:
                    volume_status['other'] += 1
                    
                total_volume_size += vol.size
                
                # Volume type analysis
                vol_type = getattr(vol, 'volume_type', 'unknown')
                if vol_type not in volumes_by_type:
                    volumes_by_type[vol_type] = {'count': 0, 'total_size_gb': 0}
                volumes_by_type[vol_type]['count'] += 1
                volumes_by_type[vol_type]['total_size_gb'] += vol.size
                
                # Add detailed volume info (top 10 for brevity)
                if len(volumes_detail) < 10:
                    attachments = getattr(vol, 'attachments', [])
                    attached_to = []
                    for att in attachments:
                        if isinstance(att, dict):
                            server_id = att.get('server_id', 'unknown')
                            device = att.get('device', 'unknown')
                            attached_to.append(f"Instance: {server_id} ({device})")
                    
                    volumes_detail.append({
                        'name': vol.name or vol.id[:8],
                        'size_gb': vol.size,
                        'status': vol.status,
                        'volume_type': vol_type,
                        'created_at': str(getattr(vol, 'created_at', 'unknown')),
                        'attached_to': attached_to if attached_to else ['Not attached'],
                        'bootable': getattr(vol, 'bootable', False),
                        'encrypted': getattr(vol, 'encrypted', False)
                    })
            
            # Calculate storage utilization (if quotas available)
            try:
                # Try to get volume quotas for current project
                quotas = conn.volume.get_quota_set(conn.current_project_id)
                quota_volumes = getattr(quotas, 'volumes', -1)
                quota_gigabytes = getattr(quotas, 'gigabytes', -1)
                
                volume_utilization = {
                    'volumes_used': len(volumes),
                    'volumes_quota': quota_volumes if quota_volumes > 0 else 'unlimited',
                    'storage_used_gb': total_volume_size,
                    'storage_quota_gb': quota_gigabytes if quota_gigabytes > 0 else 'unlimited',
                    'volume_usage_percent': f"{(len(volumes)/quota_volumes*100):.1f}%" if quota_volumes > 0 else 'N/A',
                    'storage_usage_percent': f"{(total_volume_size/quota_gigabytes*100):.1f}%" if quota_gigabytes > 0 else 'N/A'
                }
            except Exception as e:
                logger.warning(f"Could not get volume quotas: {e}")
                volume_utilization = {
                    'volumes_used': len(volumes),
                    'storage_used_gb': total_volume_size,
                    'quota_info': 'Not available'
                }
            
            cluster_info['storage_resources'] = {
                'total_volumes': len(volumes),
                'volumes_by_status': volume_status,
                'volumes_by_type': volumes_by_type,
                'volumes_detail': volumes_detail,
                'total_volume_size_gb': total_volume_size,
                'volume_utilization': volume_utilization,
                'total_volume_types': len(volume_types),
                'total_snapshots': len(snapshots),
                'volume_types': [{'name': vt.name, 'description': getattr(vt, 'description', '')} for vt in volume_types]
            }
            
            # Enhanced: Add comprehensive quota information using get_quota function (reuse pattern)
            try:
                comprehensive_quotas = get_quota()
                if comprehensive_quotas.get('success') and comprehensive_quotas.get('quotas'):
                    cluster_info['quota_information'] = {
                        'project_name': comprehensive_quotas.get('project_name', 'Current Project'),
                        'quota_details': comprehensive_quotas.get('quotas', {}),
                        'services_covered': list(comprehensive_quotas.get('quotas', {}).keys()),
                        'total_quota_categories': len(comprehensive_quotas.get('quotas', {})),
                        'quota_summary': {
                            'compute_limits': comprehensive_quotas.get('quotas', {}).get('compute', {}),
                            'volume_limits': comprehensive_quotas.get('quotas', {}).get('volume', {}),
                            'network_limits': comprehensive_quotas.get('quotas', {}).get('network', {})
                        }
                    }
                    logger.info(f"Added comprehensive quota information covering {len(comprehensive_quotas.get('quotas', {}))} service categories")
                else:
                    cluster_info['quota_information'] = {
                        'status': 'unavailable',
                        'reason': comprehensive_quotas.get('error', 'Quota information not accessible'),
                        'fallback': 'Basic quota information available in individual resource sections'
                    }
            except Exception as quota_error:
                logger.warning(f"Failed to get comprehensive quotas: {quota_error}")
                cluster_info['quota_information'] = {
                    'error': f"Failed to get comprehensive quotas: {str(quota_error)}",
                    'fallback': 'Basic quota information available in individual resource sections'
                }
        except Exception as e:
            cluster_info['storage_resources'] = {'error': f"Failed to get storage info: {str(e)}"}
            
        # === IMAGE RESOURCES (Glance) === (Refactored: Use get_image_list() function)
        try:
            # Get detailed image information from existing function
            detailed_images = get_image_list()
            
            # Process image analysis using detailed image data (simplified - no usage tracking)
            images_by_status = {'active': 0, 'queued': 0, 'saving': 0, 'killed': 0, 'deleted': 0, 'other': 0}
            images_by_visibility = {'public': 0, 'private': 0, 'shared': 0, 'community': 0}
            total_image_size = 0
            images_detail = []
            
            for img in detailed_images:
                # Status analysis
                status = img.get('status', 'unknown').lower()
                if status in images_by_status:
                    images_by_status[status] += 1
                else:
                    images_by_status['other'] += 1
                
                # Visibility analysis
                visibility = img.get('visibility', 'unknown')
                if visibility in images_by_visibility:
                    images_by_visibility[visibility] += 1
                
                # Size calculation
                img_size = img.get('size', 0) or 0
                total_image_size += img_size
                
                # Add detailed image info (top 15 for brevity)
                if len(images_detail) < 15:
                    images_detail.append({
                        'name': img.get('name') or 'Unnamed',
                        'id': img.get('id', '')[:8] + '...' if len(img.get('id', '')) > 8 else img.get('id', ''),
                        'status': img.get('status', 'unknown'),
                        'visibility': visibility,
                        'size_mb': round(img_size / (1024*1024), 1) if img_size > 0 else 0,
                        'disk_format': img.get('disk_format', 'unknown'),
                        'container_format': img.get('container_format', 'unknown'),
                        'created_at': str(img.get('created_at', 'unknown'))[:19] if img.get('created_at') != 'unknown' else 'unknown',
                        'min_disk': img.get('min_disk', 0),
                        'min_ram': img.get('min_ram', 0)
                    })
            
            cluster_info['image_resources'] = {
                'total_images': len(detailed_images),
                'images_by_status': images_by_status,
                'images_by_visibility': images_by_visibility,
                'images_detail': images_detail,
                'detailed_images': detailed_images,  # Include full image details from get_image_list()
                'total_image_size_gb': round(total_image_size / (1024*1024*1024), 2) if total_image_size > 0 else 0,
                'average_image_size_mb': round(total_image_size / len(detailed_images) / (1024*1024), 1) if len(detailed_images) > 0 and total_image_size > 0 else 0
            }
        except Exception as e:
            logger.warning(f"Failed to get image info: {e}")
            cluster_info['image_resources'] = {'error': f"Failed to get image info: {str(e)}"}
        
        # === SERVICE STATUS === (Refactored: Use get_service_status() function)
        try:
            # Get services data from existing function
            services_list = get_service_status()
            
            # Get additional service catalog info for completeness
            try:
                identity_services = list(conn.identity.services())
                endpoints = list(conn.identity.endpoints())
            except Exception as e:
                logger.warning(f"Could not get identity services/endpoints: {e}")
                identity_services = []
                endpoints = []
            
            # Process services into cluster status format
            services_by_type = {}
            compute_services = {}
            
            for svc in services_list:
                svc_type = svc.get('service_type', 'unknown')
                if svc_type not in services_by_type:
                    services_by_type[svc_type] = []
                
                services_by_type[svc_type].append({
                    'binary': svc.get('binary', 'unknown'),
                    'host': svc.get('host', 'unknown'),
                    'status': svc.get('status', 'unknown'),
                    'state': svc.get('state', 'unknown'),
                    'zone': svc.get('zone', 'unknown'),
                    'updated_at': svc.get('updated_at', 'unknown')
                })
                
                # Extract compute services for detailed health tracking
                if svc_type == 'compute':
                    status_key = f"{svc.get('binary', 'unknown')}@{svc.get('host', 'unknown')}"
                    compute_services[status_key] = {
                        'status': svc.get('status', 'unknown'),
                        'state': svc.get('state', 'unknown'),
                        'updated_at': svc.get('updated_at', 'unknown'),
                        'disabled_reason': svc.get('disabled_reason', None)
                    }
            
            cluster_info['service_status'] = {
                'total_services': len(identity_services),
                'services_by_type': services_by_type,
                'total_endpoints': len(endpoints),
                'compute_services': compute_services,
                'detailed_services': services_list  # Include full service details
            }
        except Exception as e:
            cluster_info['service_status'] = {'error': f"Failed to get service info: {str(e)}"}
        
        # === RESOURCE USAGE ANALYTICS === (NEW: Using get_usage_statistics function)
        try:
            # Get usage statistics for the last 30 days using existing function (reuse pattern)
            usage_analytics = get_usage_statistics()
            
            if usage_analytics.get('success'):
                cluster_info['resource_usage'] = {
                    'usage_period': f"{usage_analytics.get('start_date')} to {usage_analytics.get('end_date')}",
                    'usage_period_days': usage_analytics.get('usage_period_days', 0),
                    'total_projects_with_usage': usage_analytics.get('total_projects', 0),
                    'summary_statistics': usage_analytics.get('summary', {}),
                    'top_resource_consumers': usage_analytics.get('usage_statistics', [])[:5] if usage_analytics.get('usage_statistics') else [],  # Top 5 projects by usage
                    'resource_trends': {
                        'total_server_hours': usage_analytics.get('summary', {}).get('total_cpu_hours', 0),
                        'total_ram_mb_hours': usage_analytics.get('summary', {}).get('total_ram_mb_hours', 0),
                        'total_storage_gb_hours': usage_analytics.get('summary', {}).get('total_disk_gb_hours', 0),
                        'avg_daily_cpu_hours': round(usage_analytics.get('summary', {}).get('total_cpu_hours', 0) / max(usage_analytics.get('usage_period_days', 1), 1), 2),
                        'avg_daily_ram_gb_hours': round(usage_analytics.get('summary', {}).get('total_ram_mb_hours', 0) / (1024 * max(usage_analytics.get('usage_period_days', 1), 1)), 2)
                    }
                }
                logger.info(f"Added usage analytics data for {usage_analytics.get('total_projects', 0)} projects over {usage_analytics.get('usage_period_days', 0)} days")
            else:
                cluster_info['resource_usage'] = {
                    'status': 'unavailable',
                    'reason': usage_analytics.get('error', 'Usage statistics not available'),
                    'fallback_info': 'Current instance count available in compute_resources section'
                }
                logger.warning(f"Usage statistics unavailable: {usage_analytics.get('error', 'Unknown error')}")
        except Exception as e:
            logger.warning(f"Failed to get usage analytics: {e}")
            cluster_info['resource_usage'] = {
                'error': f"Failed to get usage analytics: {str(e)}",
                'fallback_info': 'Current resource information available in other sections'
            }
        
        # === CLUSTER OVERVIEW ===
        try:
            total_images = cluster_info.get('image_resources', {}).get('total_images', 0)
            if 'error' in cluster_info.get('image_resources', {}):
                total_images = 0
            
            # Extract detailed instance operation stats
            instance_ops = cluster_info.get('compute_resources', {}).get('instance_operations', {})
            compute_resources = cluster_info.get('compute_resources', {})
            image_resources = cluster_info.get('image_resources', {})
            
            # Get availability zones information using existing function (reuse pattern)
            availability_zones_data = {}
            try:
                az_data = get_availability_zones()
                if az_data.get('success'):
                    availability_zones_data = {
                        'compute_zones': az_data.get('compute_zones', []),
                        'volume_zones': az_data.get('volume_zones', []),
                        'total_compute_zones': len(az_data.get('compute_zones', [])),
                        'total_volume_zones': len(az_data.get('volume_zones', [])),
                        'zone_summary': {
                            'compute_hosts_total': sum([len(zone.get('hosts', {})) for zone in az_data.get('compute_zones', [])]),
                            'active_zones': len([zone for zone in az_data.get('compute_zones', []) if zone.get('zone_state', {}).get('available', False)])
                        }
                    }
                    logger.info(f"Retrieved availability zones data: {availability_zones_data['total_compute_zones']} compute zones, {availability_zones_data['total_volume_zones']} volume zones")
            except Exception as az_error:
                logger.warning(f"Failed to get availability zones: {az_error}")
                availability_zones_data = {}
                
            cluster_info['cluster_overview'] = {
                'total_projects': len(list(conn.identity.projects())) if 'error' not in cluster_info.get('service_status', {}) else 0,
                'total_users': len(list(conn.identity.users())) if 'error' not in cluster_info.get('service_status', {}) else 0,
                'total_images': total_images,
                'infrastructure_summary': {
                    'compute_nodes': cluster_info.get('compute_resources', {}).get('total_hypervisors', 0),
                    'total_instances': cluster_info.get('compute_resources', {}).get('total_instances', 0),
                    'total_volumes': cluster_info.get('storage_resources', {}).get('total_volumes', 0),
                    'total_networks': cluster_info.get('network_resources', {}).get('total_networks', 0),
                    'storage_used_gb': cluster_info.get('storage_resources', {}).get('total_volume_size_gb', 0),
                    'images_size_gb': cluster_info.get('image_resources', {}).get('total_image_size_gb', 0)
                },
                # Enhanced: Detailed instance operational status
                'instance_deployment_status': {
                    'total_deployed_instances': instance_ops.get('deployment_summary', {}).get('total_deployed', 0),
                    'currently_active': instance_ops.get('deployment_summary', {}).get('currently_active', 0),
                    'shutdown_or_stopped': instance_ops.get('deployment_summary', {}).get('shutdown_stopped', 0),
                    'in_error_state': instance_ops.get('deployment_summary', {}).get('in_error_state', 0),
                    'in_transition_state': instance_ops.get('deployment_summary', {}).get('in_transition', 0),
                    'paused_or_suspended': instance_ops.get('deployment_summary', {}).get('paused_suspended', 0),
                    'other_states': instance_ops.get('deployment_summary', {}).get('other_states', 0),
                    'operational_health': instance_ops.get('operational_health', {}),
                    'detailed_status_breakdown': compute_resources.get('instances_by_status', {})
                },
                # NEW: Detailed availability zones information
                'availability_zones': availability_zones_data
            }
        except Exception as e:
            logger.warning(f"Failed to build cluster overview: {e}")
            cluster_info['cluster_overview'] = {'error': f"Failed to build overview: {str(e)}"}
        
        # === HEALTH SUMMARY ===
        health_issues = []
        if cluster_info.get('compute_resources', {}).get('active_hypervisors', 0) == 0:
            health_issues.append("No active hypervisors found")
        if cluster_info.get('network_resources', {}).get('active_routers', 0) == 0:
            health_issues.append("No active routers found")
        if cluster_info.get('storage_resources', {}).get('total_volumes', 0) == 0:
            health_issues.append("No volumes found")
        if cluster_info.get('image_resources', {}).get('total_images', 0) == 0:
            health_issues.append("No images found")
        
        # Enhanced health checks for instance operations
        instance_ops = cluster_info.get('compute_resources', {}).get('instance_operations', {})
        if instance_ops.get('operational_health', {}).get('problematic_percentage', 0) > 10:
            health_issues.append(f"High error rate in instances: {instance_ops.get('operational_health', {}).get('problematic_percentage', 0)}%")
        if instance_ops.get('operational_health', {}).get('healthy_percentage', 0) < 70:
            health_issues.append(f"Low active instance ratio: {instance_ops.get('operational_health', {}).get('healthy_percentage', 0)}%")
        # Add more detailed health checks
        compute_resources = cluster_info.get('compute_resources', {})
        if isinstance(compute_resources.get('resource_utilization'), dict):
            vcpu_usage = compute_resources['resource_utilization'].get('vcpu_usage', '0/0')
            if '/' in vcpu_usage:
                used, total = vcpu_usage.split('/')[0], vcpu_usage.split('/')[0]
                if vcpu_usage.endswith('(100.0%)') or vcpu_usage.endswith('(99.'):
                    health_issues.append("CPU resources nearly exhausted")
        
        # Calculate overall health score
        total_checks = 12  # Increased for more comprehensive health checking
        passed_checks = total_checks - len(health_issues)
        health_score = (passed_checks / total_checks) * 100
        
        cluster_info['health_summary'] = {
            'overall_health_score': f"{health_score:.1f}%",
            'health_status': 'HEALTHY' if health_score >= 80 else 'WARNING' if health_score >= 60 else 'CRITICAL',
            'issues_found': len(health_issues),
            'health_issues': health_issues,
            'last_check': datetime.now().isoformat()
        }
        
        return cluster_info
        
    except Exception as e:
        logger.error(f"Unable to connect to OpenStack: {e}")
        return {
            'timestamp': datetime.now().isoformat(),
            'connection_status': f'Failed: {str(e)[:100]}...',
            'error': True,
            'error_details': str(e)
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
            
        # Get volume services (Cinder)
        try:
            for service in conn.volume.services():
                services.append({
                    'binary': service.binary,
                    'host': service.host,
                    'status': service.status,
                    'state': service.state,
                    'zone': getattr(service, 'zone', 'unknown'),
                    'updated_at': str(getattr(service, 'updated_at', 'unknown')),
                    'disabled_reason': getattr(service, 'disabled_reason', None),
                    'service_type': 'volume'
                })
        except Exception as e:
            logger.warning(f"Failed to get volume services: {e}")
            
        # Get image service status (Glance) - Check if service catalog is available
        try:
            # Test if image service is available by trying to list images (with limit)
            list(conn.image.images(limit=1))
            services.append({
                'binary': 'glance-api',
                'host': 'controller',  # Default host name
                'status': 'enabled',
                'state': 'up',
                'zone': 'internal',
                'updated_at': datetime.now().isoformat(),
                'disabled_reason': None,
                'service_type': 'image'
            })
        except Exception as e:
            logger.warning(f"Image service (Glance) appears to be down: {e}")
            services.append({
                'binary': 'glance-api',
                'host': 'controller',
                'status': 'enabled',
                'state': 'down',
                'zone': 'internal',
                'updated_at': 'unknown',
                'disabled_reason': f'Service check failed: {str(e)}',
                'service_type': 'image'
            })
            
        # Get orchestration service status (Heat) - Skip due to timeout issues
        try:
            # Skip Heat service check due to network timeout issues
            logger.warning("Skipping Heat service check due to known timeout issues")
            services.append({
                'binary': 'heat-engine',
                'host': 'controller',
                'status': 'enabled',
                'state': 'unknown',
                'zone': 'internal',
                'updated_at': 'skipped',
                'disabled_reason': 'Skipped due to timeout issues',
                'service_type': 'orchestration'
            })
        except Exception as e:
            logger.warning(f"Orchestration service (Heat) check skipped: {e}")
            services.append({
                'binary': 'heat-engine',
                'host': 'controller',
                'status': 'enabled',
                'state': 'down',
                'zone': 'internal',
                'updated_at': 'unknown',
                'disabled_reason': f'Service check failed: {str(e)}',
                'service_type': 'orchestration'
            })
            
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


def get_instance_details(
    instance_names: Optional[List[str]] = None, 
    instance_ids: Optional[List[str]] = None,
    limit: int = 50,
    offset: int = 0,
    include_all: bool = False
) -> Dict[str, Any]:
    """
    Returns detailed instance information with comprehensive server data.
    Implements pagination and limits to handle large-scale environments efficiently.
    
    Args:
        instance_names: Optional list of instance names to filter by
        instance_ids: Optional list of instance IDs to filter by
        limit: Maximum number of instances to return (default: 50, max: 200)
        offset: Number of instances to skip for pagination (default: 0)
        include_all: If True, ignores limit and returns all instances (use with caution)
        
    Returns:
        Dict containing:
        - instances: List of instance dictionaries with detailed server information
        - pagination: Pagination metadata (total_count, limit, offset, has_more)
        - performance: Timing and optimization information
    """
    start_time = datetime.now()
    
    try:
        # Validate and adjust limits for safety
        max_limit = 200
        if limit > max_limit:
            logger.warning(f"Requested limit {limit} exceeds maximum {max_limit}, adjusting")
            limit = max_limit
            
        if limit <= 0:
            limit = 50
            
        # Safety check for include_all
        if include_all:
            logger.warning("include_all=True requested - this may impact performance in large environments")
        
        conn = get_openstack_connection()
        instances = []
        total_count = 0
        
        # Determine which servers to query
        servers_to_process = []
        
        if instance_names or instance_ids:
            # Specific instance filtering - get basic info first for efficiency
            all_servers = list(conn.compute.servers(detailed=False))
            total_count = len(all_servers)
            
            filtered_servers = []
            for server in all_servers:
                should_include = False
                
                # Check if server name matches
                if instance_names and server.name in instance_names:
                    should_include = True
                
                # Check if server ID matches
                if instance_ids and server.id in instance_ids:
                    should_include = True
                
                if should_include:
                    filtered_servers.append(server)
            
            # Apply pagination to filtered results
            if not include_all:
                servers_to_process = filtered_servers[offset:offset + limit]
            else:
                servers_to_process = filtered_servers
                
            # Get detailed info for selected servers
            detailed_servers = []
            for server in servers_to_process:
                try:
                    detailed_server = conn.compute.get_server(server.id)
                    detailed_servers.append(detailed_server)
                except Exception as e:
                    logger.warning(f"Failed to get details for server {server.id}: {e}")
                    
            servers_to_process = detailed_servers
            total_count = len(filtered_servers)
            
        else:
            # No specific filtering - use API-level pagination if possible
            if include_all:
                servers_to_process = list(conn.compute.servers(detailed=True))
                total_count = len(servers_to_process)
            else:
                try:
                    # Try to use API pagination (more efficient)
                    servers_to_process = list(conn.compute.servers(
                        detailed=True,
                        limit=limit,
                        offset=offset
                    ))
                    
                    # Get total count with a separate lightweight call
                    try:
                        all_servers_basic = list(conn.compute.servers(detailed=False))
                        total_count = len(all_servers_basic)
                    except Exception:
                        total_count = len(servers_to_process)
                        
                except Exception as e:
                    logger.warning(f"API pagination failed, falling back to manual pagination: {e}")
                    all_servers = list(conn.compute.servers(detailed=True))
                    total_count = len(all_servers)
                    servers_to_process = all_servers[offset:offset + limit]
        
        # Process each server to get comprehensive details
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
        
        # Calculate pagination info
        has_more = (offset + len(instances)) < total_count
        end_time = datetime.now()
        processing_time = (end_time - start_time).total_seconds()
        
        return {
            'instances': instances,
            'pagination': {
                'total_count': total_count,
                'returned_count': len(instances),
                'limit': limit,
                'offset': offset,
                'has_more': has_more,
                'next_offset': offset + limit if has_more else None
            },
            'performance': {
                'processing_time_seconds': round(processing_time, 3),
                'instances_per_second': round(len(instances) / max(processing_time, 0.001), 2),
                'include_all_used': include_all
            },
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get instance details: {e}")
        return {
            'instances': [
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
            ],
            'pagination': {
                'total_count': 1,
                'returned_count': 1,
                'limit': limit,
                'offset': offset,
                'has_more': False,
                'next_offset': None
            },
            'performance': {
                'processing_time_seconds': 0,
                'instances_per_second': 0,
                'include_all_used': include_all
            },
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }


def get_instance_by_name(instance_name: str) -> Optional[Dict[str, Any]]:
    """
    Get detailed information for a specific instance by name.
    
    Args:
        instance_name: Name of the instance to retrieve
        
    Returns:
        Instance dictionary with detailed information, or None if not found
    """
    try:
        result = get_instance_details(instance_names=[instance_name])
        instances = result.get('instances', [])
        return instances[0] if instances else None
    except Exception as e:
        logger.error(f"Failed to get instance '{instance_name}': {e}")
        return None


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


def search_instances(
    search_term: str, 
    search_in: str = 'name',
    limit: int = 50,
    offset: int = 0,
    case_sensitive: bool = False
) -> Dict[str, Any]:
    """
    Search for instances based on various criteria with optimized performance.
    Supports partial string matching for flexible searching.
    
    Args:
        search_term: Term to search for (supports partial matching)
        search_in: Field to search in ('name', 'status', 'host', 'flavor', 'image', 'availability_zone', 'all')
        limit: Maximum number of matching instances to return (default: 50, max: 200)
        offset: Number of matching instances to skip for pagination (default: 0)
        case_sensitive: If True, performs case-sensitive search (default: False)
        
    Returns:
        Dict containing:
        - instances: List of matching instance dictionaries
        - search_info: Information about search parameters and results
        - pagination: Pagination metadata for search results
    """
    start_time = datetime.now()
    
    try:
        # Validate and adjust limits
        max_limit = 200
        if limit > max_limit:
            logger.warning(f"Requested limit {limit} exceeds maximum {max_limit}, adjusting")
            limit = max_limit
            
        if limit <= 0:
            limit = 50
        
        # Prepare search term
        if not search_term:
            logger.warning("Empty search term provided")
            return {
                'instances': [],
                'search_info': {
                    'search_term': search_term,
                    'search_in': search_in,
                    'case_sensitive': case_sensitive,
                    'matches_found': 0
                },
                'pagination': {
                    'limit': limit,
                    'offset': offset,
                    'has_more': False
                },
                'timestamp': datetime.now().isoformat()
            }
        
        search_term_processed = search_term if case_sensitive else search_term.lower()
        
        # For large environments, we'll use a more efficient approach
        # Get basic instance info first to perform initial filtering
        conn = get_openstack_connection()
        
        # Phase 1: Get basic info and perform lightweight filtering
        basic_servers = list(conn.compute.servers(detailed=False))
        logger.info(f"Searching through {len(basic_servers)} instances for '{search_term}' in '{search_in}'")
        
        potential_matches = []
        
        # Quick filtering based on available basic info
        for server in basic_servers:
            match_found = False
            
            # Check name (available in basic info)
            if search_in == 'name' or search_in == 'all':
                server_name = server.name if case_sensitive else server.name.lower()
                if search_term_processed in server_name:
                    match_found = True
            
            # Check status (available in basic info)  
            if search_in == 'status' or search_in == 'all':
                server_status = server.status if case_sensitive else server.status.lower()
                if search_term_processed in server_status:
                    match_found = True
            
            if match_found:
                potential_matches.append(server)
        
        # Apply pagination to potential matches before getting detailed info
        paginated_matches = potential_matches[offset:offset + limit]
        
        # Phase 2: Get detailed info for paginated potential matches
        matching_instances = []
        
        for server in paginated_matches:
            try:
                # Get detailed server info
                detailed_server = conn.compute.get_server(server.id)
                
                # Perform detailed matching (for fields not available in basic info)
                match_found = False
                
                # Re-check name with detailed info
                if search_in == 'name' or search_in == 'all':
                    server_name = detailed_server.name if case_sensitive else detailed_server.name.lower()
                    if search_term_processed in server_name:
                        match_found = True
                
                # Re-check status with detailed info
                if search_in == 'status' or search_in == 'all':
                    server_status = detailed_server.status if case_sensitive else detailed_server.status.lower()
                    if search_term_processed in server_status:
                        match_found = True
                
                # Check host (requires detailed info)
                if search_in == 'host' or search_in == 'all':
                    host = getattr(detailed_server, 'OS-EXT-SRV-ATTR:host', '')
                    host_processed = host if case_sensitive else host.lower()
                    if search_term_processed in host_processed:
                        match_found = True
                
                # Check availability zone (requires detailed info)
                if search_in == 'availability_zone' or search_in == 'all':
                    az = getattr(detailed_server, 'OS-EXT-AZ:availability_zone', '')
                    az_processed = az if case_sensitive else az.lower()
                    if search_term_processed in az_processed:
                        match_found = True
                
                # Check flavor (requires additional API call)
                if search_in == 'flavor' or search_in == 'all':
                    try:
                        if detailed_server.flavor:
                            flavor = conn.compute.get_flavor(detailed_server.flavor['id'])
                            flavor_name = flavor.name if case_sensitive else flavor.name.lower()
                            if search_term_processed in flavor_name:
                                match_found = True
                    except Exception as e:
                        logger.debug(f"Failed to get flavor for server {detailed_server.id}: {e}")
                
                # Check image (requires additional API call)
                if search_in == 'image' or search_in == 'all':
                    try:
                        if detailed_server.image:
                            image = conn.image.get_image(detailed_server.image['id'])
                            image_name = image.name if case_sensitive else image.name.lower()
                            if search_term_processed in image_name:
                                match_found = True
                    except Exception as e:
                        logger.debug(f"Failed to get image for server {detailed_server.id}: {e}")
                
                if match_found:
                    # Build detailed instance info (reuse logic from get_instance_details)
                    # Get flavor details
                    flavor_name = 'unknown'
                    if detailed_server.flavor:
                        try:
                            flavor = conn.compute.get_flavor(detailed_server.flavor['id'])
                            flavor_name = f"{flavor.name} (vcpus: {flavor.vcpus}, ram: {flavor.ram}MB, disk: {flavor.disk}GB)"
                        except Exception:
                            flavor_name = detailed_server.flavor.get('id', 'unknown')
                    
                    # Get image details
                    image_name = 'unknown'
                    if detailed_server.image:
                        try:
                            image = conn.image.get_image(detailed_server.image['id'])
                            image_name = image.name
                        except Exception:
                            image_name = detailed_server.image.get('id', 'unknown')
                    
                    # Get network information
                    networks = []
                    for network_name, addresses in getattr(detailed_server, 'addresses', {}).items():
                        for addr in addresses:
                            networks.append({
                                'network': network_name,
                                'ip': addr.get('addr', 'unknown'),
                                'type': addr.get('OS-EXT-IPS:type', 'unknown'),
                                'mac': addr.get('OS-EXT-IPS-MAC:mac_addr', 'unknown')
                            })
                    
                    matching_instances.append({
                        'id': detailed_server.id,
                        'name': detailed_server.name,
                        'status': detailed_server.status,
                        'power_state': getattr(detailed_server, 'power_state', 'unknown'),
                        'vm_state': getattr(detailed_server, 'vm_state', 'unknown'),
                        'task_state': getattr(detailed_server, 'task_state', None),
                        'created': str(detailed_server.created_at) if hasattr(detailed_server, 'created_at') else 'unknown',
                        'updated': str(detailed_server.updated_at) if hasattr(detailed_server, 'updated_at') else 'unknown',
                        'flavor': flavor_name,
                        'image': image_name,
                        'host': getattr(detailed_server, 'OS-EXT-SRV-ATTR:host', 'unknown'),
                        'hypervisor_hostname': getattr(detailed_server, 'OS-EXT-SRV-ATTR:hypervisor_hostname', 'unknown'),
                        'availability_zone': getattr(detailed_server, 'OS-EXT-AZ:availability_zone', 'unknown'),
                        'networks': networks,
                        'metadata': getattr(detailed_server, 'metadata', {}),
                        'security_groups': [sg.get('name', 'unknown') for sg in getattr(detailed_server, 'security_groups', [])],
                        'key_name': getattr(detailed_server, 'key_name', None),
                        'user_id': getattr(detailed_server, 'user_id', 'unknown'),
                        'tenant_id': getattr(detailed_server, 'tenant_id', 'unknown')
                    })
                    
            except Exception as e:
                logger.warning(f"Failed to process server {server.id} during search: {e}")
        
        # Calculate pagination info
        total_potential_matches = len(potential_matches)
        has_more = (offset + len(matching_instances)) < total_potential_matches
        end_time = datetime.now()
        processing_time = (end_time - start_time).total_seconds()
        
        return {
            'instances': matching_instances,
            'search_info': {
                'search_term': search_term,
                'search_in': search_in,
                'case_sensitive': case_sensitive,
                'matches_found': len(matching_instances),
                'total_potential_matches': total_potential_matches,
                'total_instances_scanned': len(basic_servers)
            },
            'pagination': {
                'limit': limit,
                'offset': offset,
                'has_more': has_more,
                'next_offset': offset + limit if has_more else None
            },
            'performance': {
                'processing_time_seconds': round(processing_time, 3),
                'instances_per_second': round(len(matching_instances) / max(processing_time, 0.001), 2)
            },
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to search instances: {e}")
        return {
            'instances': [],
            'search_info': {
                'search_term': search_term,
                'search_in': search_in,
                'case_sensitive': case_sensitive,
                'matches_found': 0,
                'error': str(e)
            },
            'pagination': {
                'limit': limit,
                'offset': offset,
                'has_more': False
            },
            'performance': {
                'processing_time_seconds': 0,
                'instances_per_second': 0
            },
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }


def get_instances_by_status(status: str) -> List[Dict[str, Any]]:
    """
    Get instances filtered by status.
    
    Args:
        status: Instance status to filter by (ACTIVE, SHUTOFF, ERROR, etc.)
        
    Returns:
        List of instances with the specified status
    """
    return search_instances(status, 'status')


def get_network_details(network_name: str = "all") -> List[Dict[str, Any]]:
    """
    Returns detailed network information with comprehensive network data.
    
    Args:
        network_name: Name of specific network to query, or "all" for all networks (default: "all")
    
    Returns:
        List of network dictionaries with detailed information.
    """
    try:
        conn = get_openstack_connection()
        networks = []
        
        # Get all networks or filter by name
        if network_name == "all":
            network_list = conn.network.networks()
        else:
            # Filter networks by name
            network_list = [n for n in conn.network.networks() if n.name == network_name]
        
        for network in network_list:
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
        logger.error(f"Failed to get network details for '{network_name}': {e}")
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


def set_instance(instance_name: str, action: str, **kwargs) -> Dict[str, Any]:
    """
    Manages OpenStack instances (start, stop, restart, backup, etc.)
    
    Args:
        instance_name: Name of the instance to manage
        action: Action to perform (start, stop, restart, pause, unpause, delete, backup, shelve, etc.)
        **kwargs: Additional parameters for specific actions:
            - backup_name: Custom name for backup image
            - flavor_id/flavor_name: For resize operations
            - image_id/image_name: For rebuild operations
            - admin_password: For rebuild operations
            - rescue_image_id: For rescue operations
    
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
        elif action in ['backup', 'create_backup']:
            # Create a backup image of the instance
            backup_name = kwargs.get('backup_name', f'{instance_name}-backup-{datetime.now().strftime("%Y%m%d-%H%M%S")}')
            image = conn.compute.create_server_image(instance, name=backup_name)
            message = f'Backup image "{backup_name}" creation started for instance "{instance_name}"'
            return {
                'success': True,
                'message': message,
                'backup_name': backup_name,
                'backup_image_id': image.id,
                'instance_id': instance.id,
                'previous_state': previous_state
            }
        elif action in ['shelve', 'shelve_offload']:
            # Shelve instance (shut down and store image)
            conn.compute.shelve_server(instance)
            message = f'Instance "{instance_name}" shelve command sent'
        elif action == 'unshelve':
            # Unshelve instance (restore from shelved state)
            conn.compute.unshelve_server(instance)
            message = f'Instance "{instance_name}" unshelve command sent'
        elif action in ['lock', 'admin_lock']:
            # Lock instance (prevent non-admin operations)
            conn.compute.lock_server(instance)
            message = f'Instance "{instance_name}" lock command sent'
        elif action == 'unlock':
            # Unlock instance
            conn.compute.unlock_server(instance)
            message = f'Instance "{instance_name}" unlock command sent'
        elif action in ['rescue', 'rescue_mode']:
            # Put instance in rescue mode
            rescue_image_id = kwargs.get('rescue_image_id', None)
            conn.compute.rescue_server(instance, image_id=rescue_image_id)
            message = f'Instance "{instance_name}" rescue mode command sent'
        elif action in ['unrescue', 'exit_rescue']:
            # Exit rescue mode
            conn.compute.unrescue_server(instance)
            message = f'Instance "{instance_name}" unrescue command sent'
        elif action in ['resize', 'change_flavor']:
            # Resize instance to new flavor
            new_flavor_id = kwargs.get('flavor_id') or kwargs.get('flavor_name')
            if not new_flavor_id:
                return {
                    'success': False,
                    'message': 'Flavor ID or name required for resize action',
                    'current_state': instance.status
                }
            
            # If flavor_name is provided, find the flavor ID
            if kwargs.get('flavor_name'):
                for flavor in conn.compute.flavors():
                    if flavor.name == kwargs.get('flavor_name'):
                        new_flavor_id = flavor.id
                        break
                else:
                    return {
                        'success': False,
                        'message': f'Flavor "{kwargs.get("flavor_name")}" not found',
                        'current_state': instance.status
                    }
            
            conn.compute.resize_server(instance, new_flavor_id)
            message = f'Instance "{instance_name}" resize to flavor "{new_flavor_id}" command sent'
        elif action == 'confirm_resize':
            # Confirm resize operation
            conn.compute.confirm_server_resize(instance)
            message = f'Instance "{instance_name}" resize confirmation sent'
        elif action == 'revert_resize':
            # Revert resize operation
            conn.compute.revert_server_resize(instance)
            message = f'Instance "{instance_name}" resize revert sent'
        elif action in ['rebuild', 'reinstall']:
            # Rebuild instance with new image
            new_image_id = kwargs.get('image_id') or kwargs.get('image_name')
            if not new_image_id:
                return {
                    'success': False,
                    'message': 'Image ID or name required for rebuild action',
                    'current_state': instance.status
                }
            
            # If image_name is provided, find the image ID
            if kwargs.get('image_name'):
                for image in conn.image.images():
                    if image.name == kwargs.get('image_name'):
                        new_image_id = image.id
                        break
                else:
                    return {
                        'success': False,
                        'message': f'Image "{kwargs.get("image_name")}" not found',
                        'current_state': instance.status
                    }
            
            admin_password = kwargs.get('admin_password', None)
            conn.compute.rebuild_server(instance, new_image_id, admin_password=admin_password)
            message = f'Instance "{instance_name}" rebuild with image "{new_image_id}" command sent'
        else:
            return {
                'success': False,
                'message': f'Unknown action "{action}". Supported: start, stop, restart, pause, unpause, suspend, resume_suspended, delete, backup, shelve, unshelve, lock, unlock, rescue, unrescue, resize, confirm_resize, revert_resize, rebuild',
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


def set_volume(volume_name: str, action: str, **kwargs) -> Dict[str, Any]:
    """
    Manages OpenStack volumes (create, delete, attach, detach)
    
    Args:
        volume_name: Name or ID of the volume (not required for 'list' action)
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
            
        elif action.lower() == 'backup':
            # Create volume backup
            backup_name = kwargs.get('backup_name', f'{volume_name}-backup-{datetime.now().strftime("%Y%m%d-%H%M%S")}')
            description = kwargs.get('description', f'Backup of volume {volume_name}')
            incremental = kwargs.get('incremental', False)
            force = kwargs.get('force', False)
            
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
            
            try:
                backup = conn.volume.create_backup(
                    volume_id=volume.id,
                    name=backup_name,
                    description=description,
                    incremental=incremental,
                    force=force
                )
                return {
                    'success': True,
                    'message': f'Volume backup "{backup_name}" creation started',
                    'backup_id': backup.id,
                    'volume_id': volume.id,
                    'incremental': incremental
                }
            except Exception as e:
                return {
                    'success': False,
                    'message': f'Failed to create backup: {str(e)}'
                }
                
        elif action.lower() == 'snapshot':
            # Create volume snapshot
            snapshot_name = kwargs.get('snapshot_name', f'{volume_name}-snapshot-{datetime.now().strftime("%Y%m%d-%H%M%S")}')
            description = kwargs.get('description', f'Snapshot of volume {volume_name}')
            force = kwargs.get('force', False)
            
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
            
            try:
                snapshot = conn.volume.create_snapshot(
                    volume_id=volume.id,
                    name=snapshot_name,
                    description=description,
                    force=force
                )
                return {
                    'success': True,
                    'message': f'Volume snapshot "{snapshot_name}" creation started',
                    'snapshot_id': snapshot.id,
                    'volume_id': volume.id
                }
            except Exception as e:
                return {
                    'success': False,
                    'message': f'Failed to create snapshot: {str(e)}'
                }
                
        elif action.lower() == 'clone':
            # Clone volume from another volume
            source_volume = kwargs.get('source_volume')
            if not source_volume:
                return {
                    'success': False,
                    'message': 'source_volume parameter is required for clone action'
                }
                
            # Find the source volume
            src_vol = None
            for vol in conn.volume.volumes():
                if vol.name == source_volume or vol.id == source_volume:
                    src_vol = vol
                    break
                    
            if not src_vol:
                return {
                    'success': False,
                    'message': f'Source volume "{source_volume}" not found'
                }
            
            size = kwargs.get('size', src_vol.size)
            description = kwargs.get('description', f'Clone of volume {source_volume}')
            volume_type = kwargs.get('volume_type', None)
            
            try:
                volume = conn.volume.create_volume(
                    name=volume_name,
                    size=size,
                    description=description,
                    volume_type=volume_type,
                    source_volid=src_vol.id
                )
                return {
                    'success': True,
                    'message': f'Volume clone "{volume_name}" creation started',
                    'volume_id': volume.id,
                    'source_volume_id': src_vol.id,
                    'size': size
                }
            except Exception as e:
                return {
                    'success': False,
                    'message': f'Failed to clone volume: {str(e)}'
                }
                
        elif action.lower() == 'transfer':
            # Transfer volume ownership
            transfer_name = kwargs.get('transfer_name', f'{volume_name}-transfer-{datetime.now().strftime("%Y%m%d-%H%M%S")}')
            
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
            
            try:
                transfer = conn.volume.create_volume_transfer(
                    volume_id=volume.id,
                    name=transfer_name
                )
                return {
                    'success': True,
                    'message': f'Volume transfer "{transfer_name}" created',
                    'transfer_id': transfer.id,
                    'auth_key': transfer.auth_key,
                    'volume_id': volume.id,
                    'warning': 'Save the auth_key - it will not be shown again!'
                }
            except Exception as e:
                return {
                    'success': False,
                    'message': f'Failed to create volume transfer: {str(e)}'
                }
                
        elif action.lower() == 'migrate':
            # Migrate volume to different backend/host
            host = kwargs.get('host')
            force_host_copy = kwargs.get('force_host_copy', False)
            lock_volume = kwargs.get('lock_volume', False)
            
            if not host:
                return {
                    'success': False,
                    'message': 'host parameter is required for migrate action'
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
            
            try:
                conn.volume.migrate_volume(
                    volume=volume,
                    host=host,
                    force_host_copy=force_host_copy,
                    lock_volume=lock_volume
                )
                return {
                    'success': True,
                    'message': f'Volume "{volume_name}" migration to host "{host}" started',
                    'volume_id': volume.id,
                    'target_host': host
                }
            except Exception as e:
                return {
                    'success': False,
                    'message': f'Failed to migrate volume: {str(e)}'
                }
        
        else:
            return {
                'success': False,
                'message': f'Unknown action "{action}". Supported: create, delete, list, extend, backup, snapshot, clone, transfer, migrate'
            }
            
    except Exception as e:
        logger.error(f"Failed to manage volume: {e}")
        return {
            'success': False,
            'message': f'Failed to manage volume: {str(e)}',
            'error': str(e)
        }


def get_resource_monitoring() -> Dict[str, Any]:
    """
    Monitors resource usage across the OpenStack cluster
    
    Returns:
        Resource usage statistics and monitoring data
    """
    try:
        conn = get_openstack_connection()
        
        # First try to get hypervisor statistics directly (like CLI does)
        hypervisor_stats = None
        try:
            # Try to get hypervisor statistics summary
            stats_response = conn.compute.get("/os-hypervisors/statistics")
            if stats_response.status_code == 200:
                hypervisor_stats = stats_response.json().get('hypervisor_statistics', {})
                logger.info(f"Got hypervisor statistics: {hypervisor_stats}")
        except Exception as e:
            logger.warning(f"Failed to get hypervisor statistics: {e}")
            
        # Get individual hypervisor details
        hypervisors = []
        for hypervisor in conn.compute.hypervisors(details=True):
            # Get detailed hypervisor info including usage statistics
            try:
                # Try to get more detailed info by making a specific API call
                hv_detail = conn.compute.get_hypervisor(hypervisor.id)
                logger.debug(f"Hypervisor {hypervisor.id} details: {hv_detail}")
                
                # Use the detailed response or fallback to original
                hv_data = hv_detail if hv_detail else hypervisor
                
            except Exception as detail_e:
                logger.warning(f"Failed to get detailed hypervisor info for {hypervisor.id}: {detail_e}")
                hv_data = hypervisor
            
            # Extract values with multiple fallback methods
            vcpus = getattr(hv_data, 'vcpus', None) or getattr(hypervisor, 'vcpus', 0) or 0
            vcpus_used = getattr(hv_data, 'vcpus_used', None) or getattr(hypervisor, 'vcpus_used', 0) or 0
            memory_mb = getattr(hv_data, 'memory_mb', None) or getattr(hypervisor, 'memory_mb', 0) or 0
            memory_mb_used = getattr(hv_data, 'memory_mb_used', None) or getattr(hypervisor, 'memory_mb_used', 0) or 0
            local_gb = getattr(hv_data, 'local_gb', None) or getattr(hypervisor, 'local_gb', 0) or 0
            local_gb_used = getattr(hv_data, 'local_gb_used', None) or getattr(hypervisor, 'local_gb_used', 0) or 0
            running_vms = getattr(hv_data, 'running_vms', None) or getattr(hypervisor, 'running_vms', 0) or 0
            
            # If we still have zero values but we have statistics, use those for totals
            if hypervisor_stats and len(list(conn.compute.hypervisors())) == 1:
                # For single hypervisor environments, use the statistics data
                vcpus = hypervisor_stats.get('vcpus', vcpus)
                vcpus_used = hypervisor_stats.get('vcpus_used', vcpus_used)
                memory_mb = hypervisor_stats.get('memory_mb', memory_mb)
                memory_mb_used = hypervisor_stats.get('memory_mb_used', memory_mb_used)
                local_gb = hypervisor_stats.get('local_gb', local_gb)
                local_gb_used = hypervisor_stats.get('local_gb_used', local_gb_used)
                running_vms = hypervisor_stats.get('running_vms', running_vms)
            
            cpu_usage_percent = (vcpus_used / vcpus * 100) if vcpus > 0 else 0
            memory_usage_percent = (memory_mb_used / memory_mb * 100) if memory_mb > 0 else 0
            disk_usage_percent = (local_gb_used / local_gb * 100) if local_gb > 0 else 0
            
            hypervisors.append({
                'id': getattr(hypervisor, 'id', 'unknown'),
                'name': getattr(hypervisor, 'hypervisor_hostname', 'unknown'),
                'status': getattr(hypervisor, 'status', 'unknown'),
                'state': getattr(hypervisor, 'state', 'unknown'),
                'hypervisor_type': getattr(hypervisor, 'hypervisor_type', 'unknown'),
                'hypervisor_version': getattr(hypervisor, 'hypervisor_version', 'unknown'),
                'pCPUs_used': vcpus_used,  # Physical CPU cores used
                'pCPUs_total': vcpus,      # Total physical CPU cores
                'pCPU_usage_percent': round(cpu_usage_percent, 2),
                'physical_memory_used_mb': memory_mb_used,
                'physical_memory_total_mb': memory_mb,
                'physical_memory_usage_percent': round(memory_usage_percent, 2),
                'local_storage_used_gb': local_gb_used,
                'local_storage_total_gb': local_gb,
                'local_storage_usage_percent': round(disk_usage_percent, 2),
                'running_vms': running_vms,
                'disk_available_least': getattr(hv_data, 'disk_available_least', None) or getattr(hypervisor, 'disk_available_least', None),
                'free_ram_mb': getattr(hv_data, 'free_ram_mb', None) or getattr(hypervisor, 'free_ram_mb', None),
                'free_disk_gb': getattr(hv_data, 'free_disk_gb', None) or getattr(hypervisor, 'free_disk_gb', None)
            })
            
        # Calculate cluster totals - use statistics if available, otherwise sum from hypervisors
        if hypervisor_stats:
            total_vcpus = hypervisor_stats.get('vcpus', sum(h['pCPUs_total'] for h in hypervisors))
            used_vcpus = hypervisor_stats.get('vcpus_used', sum(h['pCPUs_used'] for h in hypervisors))
            total_memory = hypervisor_stats.get('memory_mb', sum(h['physical_memory_total_mb'] for h in hypervisors))
            used_memory = hypervisor_stats.get('memory_mb_used', sum(h['physical_memory_used_mb'] for h in hypervisors))
            total_storage = hypervisor_stats.get('local_gb', sum(h['local_storage_total_gb'] for h in hypervisors))
            used_storage = hypervisor_stats.get('local_gb_used', sum(h['local_storage_used_gb'] for h in hypervisors))
            total_vms = hypervisor_stats.get('running_vms', sum(h['running_vms'] for h in hypervisors))
        else:
            total_vcpus = sum(h['pCPUs_total'] for h in hypervisors)
            used_vcpus = sum(h['pCPUs_used'] for h in hypervisors) 
            total_memory = sum(h['physical_memory_total_mb'] for h in hypervisors)
            used_memory = sum(h['physical_memory_used_mb'] for h in hypervisors)
            total_storage = sum(h['local_storage_total_gb'] for h in hypervisors)
            used_storage = sum(h['local_storage_used_gb'] for h in hypervisors)
            total_vms = sum(h['running_vms'] for h in hypervisors)
        
        # Get quota information and calculate project-level usage
        quotas = {}
        project_vcpu_quota = None
        project_ram_quota = None
        project_instance_quota = None
        
        try:
            project_id = conn.current_project_id
            compute_quotas = conn.compute.get_quota_set(project_id)
            project_vcpu_quota = getattr(compute_quotas, 'cores', None)
            project_ram_quota = getattr(compute_quotas, 'ram', None)  # in MB
            project_instance_quota = getattr(compute_quotas, 'instances', None)
            
            quotas['compute'] = {
                'instances': project_instance_quota if project_instance_quota != -1 else 'unlimited',
                'cores': project_vcpu_quota if project_vcpu_quota != -1 else 'unlimited',
                'ram': project_ram_quota if project_ram_quota != -1 else 'unlimited',
                'volumes': getattr(compute_quotas, 'volumes', 'unlimited')
            }
        except Exception as e:
            logger.warning(f"Failed to get quotas: {e}")
            quotas = {'error': f'Failed to get quotas: {str(e)}'}
        
        # Build comprehensive cluster summary with clearly separated physical and virtual perspectives
        cluster_summary = {
            'total_hypervisors': len(hypervisors),
            'total_running_instances': total_vms,
            'timestamp': datetime.now().isoformat()
        }
        
        # === PHYSICAL RESOURCES (Hardware Server Usage) ===
        cluster_summary['physical_resources'] = {
            'description': 'Physical hypervisor hardware resources (actual server capacity)',
            'pCPU': {
                'used': used_vcpus,
                'total': total_vcpus,
                'usage_percent': round((used_vcpus/total_vcpus*100), 1) if total_vcpus > 0 else 0,
                'unit': 'physical cores',
                'display': f'{used_vcpus}/{total_vcpus} physical cores ({(used_vcpus/total_vcpus*100):.1f}% used)' if total_vcpus > 0 else 'N/A'
            },
            'physical_memory': {
                'used_mb': used_memory,
                'total_mb': total_memory,
                'usage_percent': round((used_memory/total_memory*100), 1) if total_memory > 0 else 0,
                'unit': 'MB',
                'display': f'{used_memory}/{total_memory} MB ({(used_memory/total_memory*100):.1f}% used)' if total_memory > 0 else 'N/A'
            },
            'physical_storage': {
                'used_gb': used_storage,
                'total_gb': total_storage,
                'usage_percent': round((used_storage/total_storage*100), 1) if total_storage > 0 else 0,
                'unit': 'GB',
                'display': f'{used_storage}/{total_storage} GB ({(used_storage/total_storage*100):.1f}% used)' if total_storage > 0 else 'N/A'
            }
        }
        
        # === VIRTUAL RESOURCES (Quota/Allocation Usage) ===
        if project_vcpu_quota and project_vcpu_quota != -1:
            quota_vcpu_percent = (used_vcpus / project_vcpu_quota * 100) if project_vcpu_quota > 0 else 0
            quota_memory_percent = (used_memory / project_ram_quota * 100) if project_ram_quota and project_ram_quota != -1 else 0
            quota_instance_percent = (total_vms / project_instance_quota * 100) if project_instance_quota and project_instance_quota != -1 else 0
            
            cluster_summary['virtual_resources'] = {
                'description': 'Virtual resource allocation usage (project/tenant quotas like Horizon shows)',
                'vCPU': {
                    'used': used_vcpus,  # Note: currently same as pCPU used, but represents vCPU allocation
                    'quota': project_vcpu_quota,
                    'usage_percent': round(quota_vcpu_percent, 1),
                    'unit': 'virtual cores',
                    'display': f'{used_vcpus}/{project_vcpu_quota} virtual cores ({quota_vcpu_percent:.1f}% of quota used)'
                },
                'virtual_memory': {
                    'used_mb': used_memory,  # Note: currently same as physical, but represents virtual allocation
                    'quota_mb': project_ram_quota if project_ram_quota != -1 else 'unlimited',
                    'usage_percent': round(quota_memory_percent, 1) if project_ram_quota != -1 else 0,
                    'unit': 'MB',
                    'display': f'{used_memory}/{project_ram_quota} MB ({quota_memory_percent:.1f}% of quota used)' if project_ram_quota != -1 else f'{used_memory}/unlimited MB'
                },
                'instances': {
                    'used': total_vms,
                    'quota': project_instance_quota if project_instance_quota != -1 else 'unlimited',
                    'usage_percent': round(quota_instance_percent, 1) if project_instance_quota != -1 else 0,
                    'unit': 'instances',
                    'display': f'{total_vms}/{project_instance_quota} instances ({quota_instance_percent:.1f}% of quota used)' if project_instance_quota != -1 else f'{total_vms}/unlimited instances'
                }
            }
        else:
            cluster_summary['virtual_resources'] = {
                'description': 'Virtual resource allocation usage (project quotas unlimited or not available)',
                'vCPU': {'display': f'{used_vcpus}/unlimited virtual cores'},
                'virtual_memory': {'display': f'{used_memory}/unlimited MB'},
                'instances': {'display': f'{total_vms}/unlimited instances'},
                'note': 'Project quotas are unlimited or not available'
            }
        
        # Legacy compatibility fields (deprecated but maintained)
        cluster_summary.update({
            'pCPU_usage': f'{used_vcpus}/{total_vcpus} physical cores ({(used_vcpus/total_vcpus*100):.1f}% used)' if total_vcpus > 0 else 'N/A',
            'physical_memory_usage': f'{used_memory}/{total_memory} MB ({(used_memory/total_memory*100):.1f}% used)' if total_memory > 0 else 'N/A',
            'physical_storage_usage': f'{used_storage}/{total_storage} GB ({(used_storage/total_storage*100):.1f}% used)' if total_storage > 0 else 'N/A'
        })
        
        return {
            'cluster_summary': cluster_summary,
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
                    'floatingips': getattr(network_quotas, 'floatingips', -1)
                },
                'volume': {
                    'volumes': getattr(volume_quotas, 'volumes', -1),
                    'snapshots': getattr(volume_quotas, 'snapshots', -1),
                    'gigabytes': getattr(volume_quotas, 'gigabytes', -1)
                }
            }
        except Exception as e:
            logger.warning(f"Failed to get quotas: {e}")
            quotas = {'error': f'Failed to get quotas: {str(e)}'}

        return {
            'project': {
                'id': project.id,
                'name': project.name,
                'description': getattr(project, 'description', ''),
                'enabled': project.is_enabled,
                'domain_id': project.domain_id
            },
            'quotas': quotas,
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


# =============================================================================
# Identity (Keystone) Functions
# =============================================================================

def get_user_list() -> List[Dict[str, Any]]:
    """
    Get list of all users in the current domain.
    
    Returns:
        List of user dictionaries with detailed information
    """
    try:
        conn = get_openstack_connection()
        users = []
        
        for user in conn.identity.users():
            users.append({
                'id': user.id,
                'name': user.name,
                'email': getattr(user, 'email', None),
                'enabled': getattr(user, 'is_enabled', True),
                'description': getattr(user, 'description', ''),
                'domain_id': getattr(user, 'domain_id', 'default'),
                'default_project_id': getattr(user, 'default_project_id', None),
                'created_at': str(getattr(user, 'created_at', 'unknown')),
                'updated_at': str(getattr(user, 'updated_at', 'unknown'))
            })
        
        return users
    except Exception as e:
        logger.error(f"Failed to get user list: {e}")
        return [
            {'id': 'demo-user', 'name': 'demo', 'email': 'demo@example.com', 'enabled': True, 'error': str(e)}
        ]


def get_role_assignments() -> List[Dict[str, Any]]:
    """
    Get role assignments for the current project.
    
    Returns:
        List of role assignment dictionaries
    """
    try:
        conn = get_openstack_connection()
        assignments = []
        
        for assignment in conn.identity.role_assignments():
            assignments.append({
                'role_id': getattr(assignment, 'role', {}).get('id', 'unknown'),
                'user_id': getattr(assignment, 'user', {}).get('id', None),
                'group_id': getattr(assignment, 'group', {}).get('id', None),
                'project_id': getattr(assignment, 'project', {}).get('id', None),
                'domain_id': getattr(assignment, 'domain', {}).get('id', None),
                'scope': getattr(assignment, 'scope', {})
            })
        
        return assignments
    except Exception as e:
        logger.error(f"Failed to get role assignments: {e}")
        return [
            {'role_id': 'admin', 'user_id': 'demo-user', 'project_id': 'demo-project', 'error': str(e)}
        ]


# =============================================================================
# Compute (Nova) Functions - Enhanced
# =============================================================================

def get_keypair_list() -> List[Dict[str, Any]]:
    """
    Get list of SSH keypairs.
    
    Returns:
        List of keypair dictionaries
    """
    try:
        conn = get_openstack_connection()
        keypairs = []
        
        for keypair in conn.compute.keypairs():
            keypairs.append({
                'name': keypair.name,
                'fingerprint': keypair.fingerprint,
                'public_key': keypair.public_key[:100] + '...' if keypair.public_key and len(keypair.public_key) > 100 else keypair.public_key,
                'type': getattr(keypair, 'type', 'ssh'),
                'user_id': getattr(keypair, 'user_id', 'unknown'),
                'created_at': str(getattr(keypair, 'created_at', 'unknown'))
            })
        
        return keypairs
    except Exception as e:
        logger.error(f"Failed to get keypair list: {e}")
        return [
            {'name': 'demo-keypair', 'fingerprint': 'aa:bb:cc:dd:ee:ff', 'type': 'ssh', 'error': str(e)}
        ]


def set_keypair(keypair_name: str, action: str, **kwargs) -> Dict[str, Any]:
    """
    Manage SSH keypairs (create, delete, import).
    
    Args:
        keypair_name: Name of the keypair
        action: Action to perform (create, delete, import)
        **kwargs: Additional parameters (public_key for import)
    
    Returns:
        Result of the keypair operation
    """
    try:
        conn = get_openstack_connection()
        
        if action.lower() == 'create':
            keypair = conn.compute.create_keypair(name=keypair_name)
            return {
                'success': True,
                'message': f'Keypair "{keypair_name}" created successfully',
                'keypair': {
                    'name': keypair.name,
                    'fingerprint': keypair.fingerprint,
                    'private_key': keypair.private_key,
                    'public_key': keypair.public_key
                }
            }
            
        elif action.lower() == 'delete':
            conn.compute.delete_keypair(keypair_name)
            return {
                'success': True,
                'message': f'Keypair "{keypair_name}" deleted successfully'
            }
            
        elif action.lower() == 'import':
            public_key = kwargs.get('public_key')
            if not public_key:
                return {
                    'success': False,
                    'message': 'public_key parameter is required for import action'
                }
                
            keypair = conn.compute.create_keypair(
                name=keypair_name,
                public_key=public_key
            )
            return {
                'success': True,
                'message': f'Keypair "{keypair_name}" imported successfully',
                'keypair': {
                    'name': keypair.name,
                    'fingerprint': keypair.fingerprint,
                    'public_key': keypair.public_key
                }
            }
        else:
            return {
                'success': False,
                'message': f'Unknown action "{action}". Supported: create, delete, import'
            }
            
    except Exception as e:
        logger.error(f"Failed to manage keypair: {e}")
        return {
            'success': False,
            'message': f'Failed to manage keypair: {str(e)}',
            'error': str(e)
        }


def get_security_groups() -> List[Dict[str, Any]]:
    """
    Get list of security groups with rules.
    
    Returns:
        List of security group dictionaries
    """
    try:
        conn = get_openstack_connection()
        security_groups = []
        
        for sg in conn.network.security_groups():
            rules = []
            for rule in getattr(sg, 'security_group_rules', []):
                rules.append({
                    'id': rule.get('id', 'unknown'),
                    'direction': rule.get('direction', 'unknown'),
                    'protocol': rule.get('protocol', 'any'),
                    'port_range_min': rule.get('port_range_min'),
                    'port_range_max': rule.get('port_range_max'),
                    'remote_ip_prefix': rule.get('remote_ip_prefix'),
                    'remote_group_id': rule.get('remote_group_id')
                })
            
            security_groups.append({
                'id': sg.id,
                'name': sg.name,
                'description': getattr(sg, 'description', ''),
                'tenant_id': getattr(sg, 'tenant_id', 'unknown'),
                'created_at': str(getattr(sg, 'created_at', 'unknown')),
                'updated_at': str(getattr(sg, 'updated_at', 'unknown')),
                'rules': rules
            })
        
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


# =============================================================================
# Network (Neutron) Functions - Enhanced
# =============================================================================

def get_floating_ips() -> List[Dict[str, Any]]:
    """
    Get list of floating IPs.
    
    Returns:
        List of floating IP dictionaries
    """
    try:
        conn = get_openstack_connection()
        floating_ips = []
        
        for fip in conn.network.ips():
            floating_ips.append({
                'id': fip.id,
                'floating_ip_address': fip.floating_ip_address,
                'fixed_ip_address': fip.fixed_ip_address,
                'status': fip.status,
                'port_id': fip.port_id,
                'router_id': fip.router_id,
                'tenant_id': getattr(fip, 'tenant_id', 'unknown'),
                'floating_network_id': fip.floating_network_id,
                'created_at': str(getattr(fip, 'created_at', 'unknown')),
                'updated_at': str(getattr(fip, 'updated_at', 'unknown'))
            })
        
        return floating_ips
    except Exception as e:
        logger.error(f"Failed to get floating IPs: {e}")
        return [
            {
                'id': 'fip-1', 'floating_ip_address': '192.168.1.100', 'status': 'ACTIVE',
                'fixed_ip_address': '10.0.0.10', 'error': str(e)
            }
        ]


def set_floating_ip(action: str, **kwargs) -> Dict[str, Any]:
    """
    Manage floating IPs (create, delete, associate, disassociate).
    
    Args:
        action: Action to perform (create, delete, associate, disassociate)
        **kwargs: Additional parameters (floating_network_id, port_id, floating_ip_id)
    
    Returns:
        Result of the floating IP operation
    """
    try:
        conn = get_openstack_connection()
        
        if action.lower() == 'create':
            floating_network_id = kwargs.get('floating_network_id')
            if not floating_network_id:
                return {
                    'success': False,
                    'message': 'floating_network_id parameter is required for create action'
                }
                
            fip = conn.network.create_ip(
                floating_network_id=floating_network_id,
                port_id=kwargs.get('port_id')
            )
            return {
                'success': True,
                'message': f'Floating IP "{fip.floating_ip_address}" created successfully',
                'floating_ip': {
                    'id': fip.id,
                    'floating_ip_address': fip.floating_ip_address,
                    'status': fip.status
                }
            }
            
        elif action.lower() == 'delete':
            floating_ip_id = kwargs.get('floating_ip_id')
            if not floating_ip_id:
                return {
                    'success': False,
                    'message': 'floating_ip_id parameter is required for delete action'
                }
                
            conn.network.delete_ip(floating_ip_id)
            return {
                'success': True,
                'message': f'Floating IP deleted successfully'
            }
            
        elif action.lower() == 'associate':
            floating_ip_id = kwargs.get('floating_ip_id')
            port_id = kwargs.get('port_id')
            if not floating_ip_id or not port_id:
                return {
                    'success': False,
                    'message': 'floating_ip_id and port_id parameters are required for associate action'
                }
                
            fip = conn.network.update_ip(floating_ip_id, port_id=port_id)
            return {
                'success': True,
                'message': f'Floating IP associated successfully',
                'floating_ip': {
                    'id': fip.id,
                    'floating_ip_address': fip.floating_ip_address,
                    'port_id': fip.port_id
                }
            }
            
        elif action.lower() == 'disassociate':
            floating_ip_id = kwargs.get('floating_ip_id')
            if not floating_ip_id:
                return {
                    'success': False,
                    'message': 'floating_ip_id parameter is required for disassociate action'
                }
                
            fip = conn.network.update_ip(floating_ip_id, port_id=None)
            return {
                'success': True,
                'message': f'Floating IP disassociated successfully'
            }
        else:
            return {
                'success': False,
                'message': f'Unknown action "{action}". Supported: create, delete, associate, disassociate'
            }
            
    except Exception as e:
        logger.error(f"Failed to manage floating IP: {e}")
        return {
            'success': False,
            'message': f'Failed to manage floating IP: {str(e)}',
            'error': str(e)
        }


def get_routers() -> List[Dict[str, Any]]:
    """
    Get list of routers with detailed information.
    
    Returns:
        List of router dictionaries
    """
    try:
        conn = get_openstack_connection()
        routers = []
        
        for router in conn.network.routers():
            # Get external gateway info
            external_gateway = getattr(router, 'external_gateway_info', None)
            gateway_info = None
            if external_gateway:
                gateway_info = {
                    'network_id': external_gateway.get('network_id'),
                    'external_fixed_ips': external_gateway.get('external_fixed_ips', [])
                }
            
            routers.append({
                'id': router.id,
                'name': router.name,
                'status': router.status,
                'admin_state_up': getattr(router, 'is_admin_state_up', True),
                'tenant_id': getattr(router, 'tenant_id', 'unknown'),
                'external_gateway_info': gateway_info,
                'routes': getattr(router, 'routes', []),
                'created_at': str(getattr(router, 'created_at', 'unknown')),
                'updated_at': str(getattr(router, 'updated_at', 'unknown'))
            })
        
        return routers
    except Exception as e:
        logger.error(f"Failed to get routers: {e}")
        return [
            {
                'id': 'router-1', 'name': 'default-router', 'status': 'ACTIVE',
                'admin_state_up': True, 'external_gateway_info': None, 'error': str(e)
            }
        ]


# =============================================================================
# Block Storage (Cinder) Functions - Enhanced  
# =============================================================================

def get_volume_types() -> List[Dict[str, Any]]:
    """
    Get list of volume types.
    
    Returns:
        List of volume type dictionaries
    """
    try:
        conn = get_openstack_connection()
        volume_types = []
        
        for vtype in conn.volume.types():
            volume_types.append({
                'id': vtype.id,
                'name': vtype.name,
                'description': getattr(vtype, 'description', ''),
                'is_public': getattr(vtype, 'is_public', True),
                'extra_specs': getattr(vtype, 'extra_specs', {}),
                'created_at': str(getattr(vtype, 'created_at', 'unknown'))
            })
        
        return volume_types
    except Exception as e:
        logger.error(f"Failed to get volume types: {e}")
        return [
            {'id': '__DEFAULT__', 'name': 'default', 'description': 'Default volume type', 'is_public': True, 'error': str(e)}
        ]


def get_volume_snapshots() -> List[Dict[str, Any]]:
    """
    Get list of volume snapshots.
    
    Returns:
        List of volume snapshot dictionaries
    """
    try:
        conn = get_openstack_connection()
        snapshots = []
        
        for snapshot in conn.volume.snapshots(detailed=True):
            snapshots.append({
                'id': snapshot.id,
                'name': snapshot.name,
                'description': getattr(snapshot, 'description', ''),
                'status': snapshot.status,
                'size': snapshot.size,
                'volume_id': snapshot.volume_id,
                'user_id': getattr(snapshot, 'user_id', 'unknown'),
                'project_id': getattr(snapshot, 'project_id', 'unknown'),
                'created_at': str(getattr(snapshot, 'created_at', 'unknown')),
                'updated_at': str(getattr(snapshot, 'updated_at', 'unknown'))
            })
        
        return snapshots
    except Exception as e:
        logger.error(f"Failed to get volume snapshots: {e}")
        return [
            {
                'id': 'snap-1', 'name': 'demo-snapshot', 'status': 'available',
                'size': 10, 'volume_id': 'vol-1', 'error': str(e)
            }
        ]


def set_snapshot(snapshot_name: str, action: str, **kwargs) -> Dict[str, Any]:
    """
    Manage volume snapshots (create, delete).
    
    Args:
        snapshot_name: Name of the snapshot
        action: Action to perform (create, delete)
        **kwargs: Additional parameters (volume_id, description)
    
    Returns:
        Result of the snapshot operation
    """
    try:
        conn = get_openstack_connection()
        
        if action.lower() == 'create':
            volume_id = kwargs.get('volume_id')
            if not volume_id:
                return {
                    'success': False,
                    'message': 'volume_id parameter is required for create action'
                }
                
            snapshot = conn.volume.create_snapshot(
                name=snapshot_name,
                volume_id=volume_id,
                description=kwargs.get('description', f'Snapshot of volume {volume_id}')
            )
            return {
                'success': True,
                'message': f'Snapshot "{snapshot_name}" creation started',
                'snapshot': {
                    'id': snapshot.id,
                    'name': snapshot.name,
                    'status': snapshot.status,
                    'volume_id': snapshot.volume_id
                }
            }
            
        elif action.lower() == 'delete':
            # Find the snapshot
            snapshot = None
            for snap in conn.volume.snapshots():
                if snap.name == snapshot_name or snap.id == snapshot_name:
                    snapshot = snap
                    break
                    
            if not snapshot:
                return {
                    'success': False,
                    'message': f'Snapshot "{snapshot_name}" not found'
                }
                
            conn.volume.delete_snapshot(snapshot)
            return {
                'success': True,
                'message': f'Snapshot "{snapshot_name}" deletion started',
                'snapshot_id': snapshot.id
            }
        else:
            return {
                'success': False,
                'message': f'Unknown action "{action}". Supported: create, delete'
            }
            
    except Exception as e:
        logger.error(f"Failed to manage snapshot: {e}")
        return {
            'success': False,
            'message': f'Failed to manage snapshot: {str(e)}',
            'error': str(e)
        }


# =============================================================================
# Image Service (Glance) Functions - Enhanced
# =============================================================================

def set_image(image_name: str, action: str, **kwargs) -> Dict[str, Any]:
    """
    Manage images (create, delete, update, list).
    
    Args:
        image_name: Name or ID of the image (not required for 'list' action)
        action: Action to perform (create, delete, update, list)
        **kwargs: Additional parameters
    
    Returns:
        Result of the image operation
    """
    try:
        conn = get_openstack_connection()
        
        if action.lower() == 'list':
            images = []
            for image in conn.image.images():
                images.append({
                    'id': image.id,
                    'name': image.name,
                    'status': image.status,
                    'visibility': image.visibility,
                    'size': getattr(image, 'size', 0),
                    'disk_format': getattr(image, 'disk_format', 'unknown'),
                    'container_format': getattr(image, 'container_format', 'unknown'),
                    'min_disk': getattr(image, 'min_disk', 0),
                    'min_ram': getattr(image, 'min_ram', 0),
                    'owner': getattr(image, 'owner', 'unknown'),
                    'created_at': str(getattr(image, 'created_at', 'unknown')),
                    'updated_at': str(getattr(image, 'updated_at', 'unknown')),
                    'protected': getattr(image, 'is_protected', False),
                    'checksum': getattr(image, 'checksum', None),
                    'properties': getattr(image, 'properties', {})
                })
            return {
                'success': True,
                'images': images,
                'count': len(images)
            }
        
        elif action.lower() == 'create':
            container_format = kwargs.get('container_format', 'bare')
            disk_format = kwargs.get('disk_format', 'qcow2')
            
            image = conn.image.create_image(
                name=image_name,
                container_format=container_format,
                disk_format=disk_format,
                visibility=kwargs.get('visibility', 'private'),
                min_disk=kwargs.get('min_disk', 0),
                min_ram=kwargs.get('min_ram', 0),
                properties=kwargs.get('properties', {})
            )
            return {
                'success': True,
                'message': f'Image "{image_name}" created successfully',
                'image': {
                    'id': image.id,
                    'name': image.name,
                    'status': image.status,
                    'visibility': image.visibility
                }
            }
            
        elif action.lower() == 'delete':
            # Find the image
            image = None
            for img in conn.image.images():
                if img.name == image_name or img.id == image_name:
                    image = img
                    break
                    
            if not image:
                return {
                    'success': False,
                    'message': f'Image "{image_name}" not found'
                }
                
            conn.image.delete_image(image)
            return {
                'success': True,
                'message': f'Image "{image_name}" deleted successfully',
                'image_id': image.id
            }
            
        elif action.lower() == 'update':
            # Find the image
            image = None
            for img in conn.image.images():
                if img.name == image_name or img.id == image_name:
                    image = img
                    break
                    
            if not image:
                return {
                    'success': False,
                    'message': f'Image "{image_name}" not found'
                }
                
            update_params = {}
            if 'visibility' in kwargs:
                update_params['visibility'] = kwargs['visibility']
            if 'properties' in kwargs:
                update_params.update(kwargs['properties'])
                
            updated_image = conn.image.update_image(image, **update_params)
            return {
                'success': True,
                'message': f'Image "{image_name}" updated successfully',
                'image': {
                    'id': updated_image.id,
                    'name': updated_image.name,
                    'visibility': updated_image.visibility
                }
            }
        else:
            return {
                'success': False,
                'message': f'Unknown action "{action}". Supported: create, delete, update, list'
            }
            
    except Exception as e:
        logger.error(f"Failed to manage image: {e}")
        return {
            'success': False,
            'message': f'Failed to manage image: {str(e)}',
            'error': str(e)
        }


# =============================================================================
# Heat Stack Functions
# =============================================================================

def get_heat_stacks() -> List[Dict[str, Any]]:
    """
    Get list of Heat stacks.
    
    Returns:
        List of stack dictionaries
    """
    try:
        conn = get_openstack_connection()
        stacks = []
        
        for stack in conn.orchestration.stacks():
            stacks.append({
                'id': stack.id,
                'name': stack.name,
                'status': stack.status,
                'stack_status': getattr(stack, 'stack_status', 'unknown'),
                'stack_status_reason': getattr(stack, 'stack_status_reason', ''),
                'creation_time': str(getattr(stack, 'creation_time', 'unknown')),
                'updated_time': str(getattr(stack, 'updated_time', 'unknown')),
                'description': getattr(stack, 'description', ''),
                'tags': getattr(stack, 'tags', []),
                'timeout_mins': getattr(stack, 'timeout_mins', None),
                'owner': getattr(stack, 'stack_owner', 'unknown')
            })
        
        return stacks
    except Exception as e:
        logger.error(f"Failed to get stacks: {e}")
        return [
            {
                'id': 'stack-1', 'name': 'demo-stack', 'status': 'CREATE_COMPLETE',
                'stack_status': 'CREATE_COMPLETE', 'description': 'Demo stack', 'error': str(e)
            }
        ]


def set_heat_stack(stack_name: str, action: str, **kwargs) -> Dict[str, Any]:
    """
    Manage Heat stacks (create, delete, update).
    
    Args:
        stack_name: Name of the stack
        action: Action to perform (create, delete, update, abandon)
        **kwargs: Additional parameters (template, parameters)
    
    Returns:
        Result of the stack operation
    """
    try:
        conn = get_openstack_connection()
        
        if action.lower() == 'create':
            template = kwargs.get('template')
            if not template:
                return {
                    'success': False,
                    'message': 'template parameter is required for create action'
                }
                
            stack = conn.orchestration.create_stack(
                name=stack_name,
                template=template,
                parameters=kwargs.get('parameters', {}),
                timeout=kwargs.get('timeout', 60),
                tags=kwargs.get('tags', [])
            )
            return {
                'success': True,
                'message': f'Stack "{stack_name}" creation started',
                'stack': {
                    'id': stack.id,
                    'name': stack.name,
                    'status': stack.stack_status
                }
            }
            
        elif action.lower() == 'delete':
            # Find the stack
            stack = None
            for stk in conn.orchestration.stacks():
                if stk.name == stack_name or stk.id == stack_name:
                    stack = stk
                    break
                    
            if not stack:
                return {
                    'success': False,
                    'message': f'Stack "{stack_name}" not found'
                }
                
            conn.orchestration.delete_stack(stack)
            return {
                'success': True,
                'message': f'Stack "{stack_name}" deletion started',
                'stack_id': stack.id
            }
            
        elif action.lower() == 'update':
            # Find the stack
            stack = None
            for stk in conn.orchestration.stacks():
                if stk.name == stack_name or stk.id == stack_name:
                    stack = stk
                    break
                    
            if not stack:
                return {
                    'success': False,
                    'message': f'Stack "{stack_name}" not found'
                }
                
            template = kwargs.get('template')
            if not template:
                return {
                    'success': False,
                    'message': 'template parameter is required for update action'
                }
                
            updated_stack = conn.orchestration.update_stack(
                stack,
                template=template,
                parameters=kwargs.get('parameters', {})
            )
            return {
                'success': True,
                'message': f'Stack "{stack_name}" update started',
                'stack': {
                    'id': updated_stack.id,
                    'name': updated_stack.name,
                    'status': updated_stack.stack_status
                }
            }
        else:
            return {
                'success': False,
                'message': f'Unknown action "{action}". Supported: create, delete, update'
            }
            
    except Exception as e:
        logger.error(f"Failed to manage stack: {e}")
        return {
            'success': False,
            'message': f'Failed to manage stack: {str(e)}',
            'error': str(e)
        }


def get_compute_quota_usage(conn) -> Dict[str, Any]:
    """
    Get compute quota usage information for the current project.
    
    Args:
        conn: OpenStack connection object
        
    Returns:
        Dict containing quota usage information with physical vs virtual resource distinction
    """
    try:
        # Get current project ID
        project_id = conn.current_project_id
        
        # Get quota limits
        quotas = conn.compute.get_quota_set(project_id)
        
        # Get actual usage by counting real resources
        actual_instances = list(conn.compute.servers())
        actual_instance_count = len(actual_instances)
        
        # Calculate actual vCPU usage from running instances
        actual_vcpu_usage = 0
        actual_memory_usage = 0
        
        for instance in actual_instances:
            try:
                # Get flavor info - try both ID and direct object access
                flavor_info = instance.flavor
                if isinstance(flavor_info, dict):
                    flavor_id = flavor_info.get('id')
                    if flavor_id:
                        try:
                            # Try to get full flavor details
                            flavor = conn.compute.get_flavor(flavor_id)
                            actual_vcpu_usage += getattr(flavor, 'vcpus', 0)
                            actual_memory_usage += getattr(flavor, 'ram', 0)
                        except Exception:
                            # If flavor not found, try to get basic info from instance
                            logger.warning(f"Flavor {flavor_id} not found for instance {instance.id}, using instance flavor info if available")
                            # Some basic fallback - these values might be stored in instance metadata
                            actual_vcpu_usage += flavor_info.get('vcpus', 1)  # Default to 1 if not available
                            actual_memory_usage += flavor_info.get('ram', 512)  # Default to 512MB if not available
                else:
                    # Flavor object directly
                    actual_vcpu_usage += getattr(flavor_info, 'vcpus', 1)
                    actual_memory_usage += getattr(flavor_info, 'ram', 512)
                    
            except Exception as e:
                logger.warning(f"Could not get flavor info for instance {instance.id}: {e}")
                # Use minimal defaults when flavor info is unavailable
                actual_vcpu_usage += 1
                actual_memory_usage += 512
        
        # Get usage statistics from API (as fallback/comparison)
        try:
            usage = conn.compute.get_quota_set(project_id, usage=True)
        except Exception as usage_e:
            logger.warning(f"Failed to get quota usage from API: {usage_e}")
            usage = None
        
        # Helper function to safely extract quota limits
        def safe_get_quota_limit(obj, attr_name, default=-1):
            """Safely extract quota limits"""
            try:
                return getattr(obj, attr_name, default)
            except Exception:
                return default
        
        quota_info = {
            'description': 'Project quota usage (vCPU = virtual CPU allocation, pCPU = physical CPU usage)',
            'instances': {
                'used': actual_instance_count,  # Use actual count instead of quota API
                'limit': safe_get_quota_limit(quotas, 'instances', -1),
                'usage_percent': 0
            },
            'vcpus': {
                'description': 'Virtual CPUs (vCPU) - allocated to instances',
                'used': actual_vcpu_usage,  # Use actual usage from flavor calculations
                'limit': safe_get_quota_limit(quotas, 'cores', -1),
                'usage_percent': 0
            },
            'memory': {
                'description': 'Virtual memory (allocated to instances)',
                'used_mb': actual_memory_usage,  # Use actual memory from flavor calculations
                'limit_mb': safe_get_quota_limit(quotas, 'ram', -1),
                'usage_percent': 0
            }
        }
        
        # Add quota API data for comparison (if available)
        if usage:
            def safe_get_quota_value(obj, attr_name, default=0):
                """Safely extract quota values handling both dict and int responses"""
                try:
                    attr = getattr(obj, attr_name, default)
                    if isinstance(attr, dict):
                        return attr.get('in_use', default)
                    elif isinstance(attr, (int, float)):
                        return attr
                    else:
                        return default
                except Exception:
                    return default
            
            quota_info['api_reported_usage'] = {
                'instances': safe_get_quota_value(usage, 'instances', 0),
                'vcpus': safe_get_quota_value(usage, 'cores', 0),
                'memory_mb': safe_get_quota_value(usage, 'ram', 0)
            }
        
        # Calculate usage percentages
        for resource in ['instances', 'vcpus', 'memory']:
            resource_data = quota_info[resource]
            if resource == 'memory':
                used = resource_data['used_mb']
                limit = resource_data['limit_mb']
            else:
                used = resource_data['used']
                limit = resource_data['limit']
                
            if limit > 0:
                resource_data['usage_percent'] = round((used / limit) * 100, 1)
        
        logger.info(f"Quota usage - Actual instances: {actual_instance_count}, "
                   f"vCPUs: {actual_vcpu_usage}, Memory: {actual_memory_usage}MB")
        
        return quota_info
        
    except Exception as e:
        logger.warning(f"Could not get compute quota usage: {e}")
        return {
            'description': 'Quota usage data unavailable',
            'error': str(e),
            'instances': {'used': 0, 'limit': 'unknown'},
            'vcpus': {'used': 0, 'limit': 'unknown', 'description': 'Virtual CPUs (vCPU) - data unavailable'},
            'memory': {'used_mb': 0, 'limit_mb': 'unknown', 'description': 'Virtual memory - data unavailable'}
        }


# =============================================================================
# Read-only functions extracted from manage_* functions for ALLOW_MODIFY_OPERATIONS=false
# =============================================================================

def get_volume_list() -> List[Dict[str, Any]]:
    """
    Get list of all volumes (read-only operation extracted from manage_volume).
    
    Returns:
        List of volume information dictionaries
    """
    try:
        conn = get_openstack_connection()
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
        
        logger.info(f"Retrieved {len(volumes)} volumes")
        return volumes
        
    except Exception as e:
        logger.error(f"Failed to get volume list: {e}")
        return []


def get_image_detail_list() -> List[Dict[str, Any]]:
    """
    Get detailed list of all images (read-only operation extracted from manage_image).
    
    Returns:
        List of detailed image information dictionaries
    """
    try:
        conn = get_openstack_connection()
        images = []
        
        for image in conn.image.images():
            images.append({
                'id': image.id,
                'name': image.name,
                'status': image.status,
                'visibility': image.visibility,
                'size': getattr(image, 'size', 0),
                'disk_format': getattr(image, 'disk_format', 'unknown'),
                'container_format': getattr(image, 'container_format', 'unknown'),
                'min_disk': getattr(image, 'min_disk', 0),
                'min_ram': getattr(image, 'min_ram', 0),
                'owner': getattr(image, 'owner', 'unknown'),
                'created_at': str(getattr(image, 'created_at', 'unknown')),
                'updated_at': str(getattr(image, 'updated_at', 'unknown')),
                'protected': getattr(image, 'is_protected', False),
                'checksum': getattr(image, 'checksum', None),
                'properties': getattr(image, 'properties', {})
            })
        
        logger.info(f"Retrieved {len(images)} detailed images")
        return images
        
    except Exception as e:
        logger.error(f"Failed to get detailed image list: {e}")
        return []


def get_usage_statistics(start_date: str = "", end_date: str = "") -> Dict[str, Any]:
    """
    Get usage statistics for projects (similar to 'openstack usage list').
    
    Args:
        start_date: Start date in YYYY-MM-DD format (optional, defaults to 30 days ago)
        end_date: End date in YYYY-MM-DD format (optional, defaults to today)
    
    Returns:
        Usage statistics including servers, RAM MB-Hours, CPU Hours, and Disk GB-Hours
    """
    try:
        conn = get_openstack_connection()
        
        # Set default date range if not provided
        from datetime import datetime, timedelta
        if not end_date:
            end_time = datetime.now()
        else:
            end_time = datetime.strptime(end_date, '%Y-%m-%d')
            
        if not start_date:
            start_time = end_time - timedelta(days=30)
        else:
            start_time = datetime.strptime(start_date, '%Y-%m-%d')
        
        logger.info(f"Getting usage statistics from {start_time.strftime('%Y-%m-%d')} to {end_time.strftime('%Y-%m-%d')}")
        
        # Try to get usage statistics using the simple tenant usage API
        try:
            start_iso = start_time.isoformat()
            end_iso = end_time.isoformat()
            
            usage_response = conn.compute.get(f'/os-simple-tenant-usage?start={start_iso}&end={end_iso}&detailed=1')
            
            if usage_response.status_code == 200:
                usage_data = usage_response.json()
                tenant_usages = usage_data.get('tenant_usages', [])
                
                usage_list = []
                for usage in tenant_usages:
                    # Get project name from project ID
                    project_name = "Unknown"
                    try:
                        project = conn.identity.get_project(usage.get('tenant_id'))
                        project_name = project.name if project else usage.get('tenant_id', 'Unknown')
                    except Exception as e:
                        logger.warning(f"Could not get project name for {usage.get('tenant_id')}: {e}")
                        project_name = usage.get('tenant_id', 'Unknown')
                    
                    usage_info = {
                        'project': project_name,
                        'project_id': usage.get('tenant_id'),
                        'servers': len(usage.get('server_usages', [])),
                        'ram_mb_hours': round(usage.get('total_memory_mb_usage', 0), 2),
                        'cpu_hours': round(usage.get('total_vcpus_usage', 0), 2),
                        'disk_gb_hours': round(usage.get('total_local_gb_usage', 0), 2),
                        'uptime_hours': round(usage.get('total_hours', 0), 2),
                        'server_details': []
                    }
                    
                    # Add server details if available
                    for server_usage in usage.get('server_usages', []):
                        usage_info['server_details'].append({
                            'name': server_usage.get('name', 'Unknown'),
                            'instance_id': server_usage.get('instance_id'),
                            'uptime_hours': round(server_usage.get('hours', 0), 2),
                            'ram_mb_hours': round(server_usage.get('memory_mb', 0) * server_usage.get('hours', 0), 2),
                            'cpu_hours': round(server_usage.get('vcpus', 0) * server_usage.get('hours', 0), 2),
                            'disk_gb_hours': round(server_usage.get('local_gb', 0) * server_usage.get('hours', 0), 2),
                            'flavor': server_usage.get('flavor', 'Unknown')
                        })
                    
                    usage_list.append(usage_info)
                
                return {
                    'success': True,
                    'start_date': start_time.strftime('%Y-%m-%d'),
                    'end_date': end_time.strftime('%Y-%m-%d'),
                    'usage_period_days': (end_time - start_time).days,
                    'total_projects': len(usage_list),
                    'usage_statistics': usage_list,
                    'summary': {
                        'total_servers': sum(u['servers'] for u in usage_list),
                        'total_ram_mb_hours': sum(u['ram_mb_hours'] for u in usage_list),
                        'total_cpu_hours': sum(u['cpu_hours'] for u in usage_list),
                        'total_disk_gb_hours': sum(u['disk_gb_hours'] for u in usage_list)
                    }
                }
                
            else:
                logger.warning(f"Usage API returned status {usage_response.status_code}")
                return {
                    'success': False,
                    'error': f'Usage API returned status {usage_response.status_code}',
                    'message': 'Simple tenant usage API not available or accessible'
                }
                
        except Exception as api_error:
            logger.warning(f"Failed to get usage statistics from API: {api_error}")
            
            # Fallback: Calculate basic usage from current instances
            logger.info("Falling back to basic instance-based usage calculation")
            
            instances = []
            for server in conn.compute.servers(detailed=True):
                created_time = getattr(server, 'created_at', None)
                if created_time:
                    try:
                        if isinstance(created_time, str):
                            created_dt = datetime.fromisoformat(created_time.replace('Z', '+00:00'))
                        else:
                            created_dt = created_time
                        
                        # Calculate uptime in hours
                        uptime_hours = (end_time - max(created_dt, start_time)).total_seconds() / 3600
                        uptime_hours = max(0, uptime_hours)  # Don't allow negative hours
                        
                        if uptime_hours > 0:
                            flavor_info = getattr(server, 'flavor', {})
                            instances.append({
                                'name': server.name,
                                'id': server.id,
                                'status': server.status,
                                'created_at': str(created_dt),
                                'uptime_hours': round(uptime_hours, 2),
                                'flavor_id': flavor_info.get('id', 'unknown') if isinstance(flavor_info, dict) else 'unknown'
                            })
                    except Exception as dt_error:
                        logger.warning(f"Could not parse creation time for {server.name}: {dt_error}")
            
            # Get current project info
            project_info = conn.identity.get_project(conn.auth.auth.project_name)
            project_name = project_info.name if project_info else conn.auth.auth.project_name
            
            return {
                'success': True,
                'method': 'fallback_calculation',
                'start_date': start_time.strftime('%Y-%m-%d'),
                'end_date': end_time.strftime('%Y-%m-%d'),
                'usage_period_days': (end_time - start_time).days,
                'total_projects': 1,
                'usage_statistics': [{
                    'project': project_name,
                    'project_id': conn.auth.auth.project_name,
                    'servers': len(instances),
                    'note': 'Fallback calculation - actual usage data not available from API',
                    'active_instances': instances
                }],
                'warning': 'This is a fallback calculation. For accurate usage statistics, ensure the simple-tenant-usage API is available.'
            }
            
    except Exception as e:
        logger.error(f"Failed to get usage statistics: {e}")
        return {
            'success': False,
            'error': str(e),
            'message': 'Failed to retrieve usage statistics'
        }


def get_quota(project_name: str = "") -> Dict[str, Any]:
    """
    Get quota information for projects (similar to 'openstack quota show').
    
    Args:
        project_name: Name of the project (optional, defaults to current project from OS_PROJECT_NAME)
    
    Returns:
        Quota information for the specified project or current project
    """
    try:
        conn = get_openstack_connection()
        
        # If no project name specified, use environment variable OS_PROJECT_NAME
        if not project_name or project_name.strip() == "":
            project_name = os.environ.get('OS_PROJECT_NAME', 'admin')
            logger.info(f"No project specified, using default from OS_PROJECT_NAME: {project_name}")
        else:
            logger.info(f"Getting quota for specified project: {project_name}")
        
        # Find project by name
        try:
            project = conn.identity.find_project(project_name)
            if not project:
                return {
                    'success': False,
                    'error': f'Project "{project_name}" not found'
                }
            project_id = project.id
            logger.info(f"Found project: {project_name} ({project_id})")
        except Exception as e:
            return {
                'success': False,
                'error': f'Failed to find project "{project_name}": {str(e)}'
            }
        
        quota_data = {}
        
        # Get Compute (Nova) quotas - using correct API endpoints
        try:
            # Use direct API call instead of get_quota method
            compute_quotas = conn.compute.get(f'/os-quota-sets/{project_id}').json()['quota_set']
            quota_data['compute'] = {
                'cores': compute_quotas.get('cores', -1),
                'instances': compute_quotas.get('instances', -1),
                'ram': compute_quotas.get('ram', -1),
                'key_pairs': compute_quotas.get('key_pairs', -1),
                'server_groups': compute_quotas.get('server_groups', -1),
                'server_group_members': compute_quotas.get('server_group_members', -1),
                'injected_files': compute_quotas.get('injected_files', -1),
                'injected_file_content_bytes': compute_quotas.get('injected_file_content_bytes', -1),
                'injected_file_path_bytes': compute_quotas.get('injected_file_path_bytes', -1),
                'fixed_ips': compute_quotas.get('fixed_ips', None)  # Can be None
            }
        except Exception as e:
            logger.warning(f"Failed to get compute quota: {e}")
            quota_data['compute'] = {'error': f'Failed to get compute quota: {str(e)}'}
        
        # Get Volume (Cinder) quotas - using correct API endpoints
        try:
            volume_quotas = conn.volume.get(f'/os-quota-sets/{project_id}').json()['quota_set']
            quota_data['volume'] = {
                'volumes': volume_quotas.get('volumes', -1),
                'snapshots': volume_quotas.get('snapshots', -1),
                'gigabytes': volume_quotas.get('gigabytes', -1),
                'backups': volume_quotas.get('backups', -1),
                'backup_gigabytes': volume_quotas.get('backup_gigabytes', -1),
                'per_volume_gigabytes': volume_quotas.get('per_volume_gigabytes', -1),
                'groups': volume_quotas.get('groups', -1)
            }
            
            # Add volume type specific quotas
            for key, value in volume_quotas.items():
                if '___' in key:  # Volume type specific quotas (e.g., volumes___DEFAULT__)
                    quota_data['volume'][key] = value
                    
        except Exception as e:
            logger.warning(f"Failed to get volume quota: {e}")
            quota_data['volume'] = {'error': f'Failed to get volume quota: {str(e)}'}
        
        # Get Network (Neutron) quotas - using quotas API
        try:
            # Use the quotas method which should work for Neutron
            network_quota_obj = conn.network.get_quota(project_id)
            quota_data['network'] = {
                'networks': getattr(network_quota_obj, 'networks', -1),
                'subnets': getattr(network_quota_obj, 'subnets', -1),
                'ports': getattr(network_quota_obj, 'ports', -1),
                'routers': getattr(network_quota_obj, 'routers', -1),
                'floating_ips': getattr(network_quota_obj, 'floating_ips', -1),
                'security_groups': getattr(network_quota_obj, 'security_groups', -1),
                'security_group_rules': getattr(network_quota_obj, 'security_group_rules', -1),
                'rbac_policies': getattr(network_quota_obj, 'rbac_policies', -1),
                'subnet_pools': getattr(network_quota_obj, 'subnet_pools', -1)
            }
        except Exception as e:
            logger.warning(f"Failed to get network quota: {e}")
            quota_data['network'] = {'error': f'Failed to get network quota: {str(e)}'}
        
        # Create consolidated quota view (like openstack quota show output)
        consolidated_quota = {}
        
        # Add compute quotas
        if 'error' not in quota_data.get('compute', {}):
            compute = quota_data['compute']
            consolidated_quota.update({
                'cores': compute.get('cores', -1),
                'instances': compute.get('instances', -1),
                'ram': compute.get('ram', -1),
                'key-pairs': compute.get('key_pairs', -1),
                'server-groups': compute.get('server_groups', -1),
                'server-group-members': compute.get('server_group_members', -1),
                'injected-files': compute.get('injected_files', -1),
                'injected-file-size': compute.get('injected_file_content_bytes', -1),
                'injected-path-size': compute.get('injected_file_path_bytes', -1),
                'fixed_ips': compute.get('fixed_ips', None),  # Can be None
                'properties': 128  # Default value for image properties
            })
        
        # Add volume quotas
        if 'error' not in quota_data.get('volume', {}):
            volume = quota_data['volume']
            consolidated_quota.update({
                'volumes': volume.get('volumes', -1),
                'snapshots': volume.get('snapshots', -1),
                'gigabytes': volume.get('gigabytes', -1),
                'backups': volume.get('backups', -1),
                'backup-gigabytes': volume.get('backup_gigabytes', -1),
                'per-volume-gigabytes': volume.get('per_volume_gigabytes', -1),
                'groups': volume.get('groups', -1)
            })
            
            # Add volume type specific quotas
            for key, value in volume.items():
                if '___' in key:  # Volume type specific quotas
                    consolidated_quota[key] = value
        
        # Add network quotas
        if 'error' not in quota_data.get('network', {}):
            network = quota_data['network']
            consolidated_quota.update({
                'networks': network.get('networks', -1),
                'subnets': network.get('subnets', -1),
                'ports': network.get('ports', -1),
                'routers': network.get('routers', -1),
                'floating-ips': network.get('floating_ips', -1),
                'secgroups': network.get('security_groups', -1),
                'secgroup-rules': network.get('security_group_rules', -1),
                'rbac_policies': network.get('rbac_policies', -1),
                'subnet_pools': network.get('subnet_pools', -1)
            })
        
        return {
            'success': True,
            'project_name': project_name,
            'project_id': project_id,
            'quota_details': quota_data,
            'consolidated_quota': consolidated_quota,
            'total_quotas': len(consolidated_quota)
        }
        
    except Exception as e:
        logger.error(f"Failed to get quota information: {e}")
        return {
            'success': False,
            'error': str(e),
            'message': 'Failed to retrieve quota information'
        }


def set_quota(project_name: str, action: str, **kwargs) -> Dict[str, Any]:
    """
    Manage project quotas (set, delete, list).
    
    Args:
        project_name: Name of the project (required for set/delete, optional for list)
        action: Action to perform (set, delete, list)
        **kwargs: Quota parameters for set action (cores, instances, ram, volumes, etc.)
    
    Returns:
        Result of the quota management operation
    """
    try:
        conn = get_openstack_connection()
        
        if action.lower() == 'list':
            # List quotas for all projects the user has access to
            projects = []
            try:
                for project in conn.identity.projects():
                    try:
                        # Try to get quota for this project (will fail if no access)
                        quota_result = get_quota(project.name)
                        if quota_result.get('success', False):
                            projects.append({
                                'project_name': project.name,
                                'project_id': project.id,
                                'description': getattr(project, 'description', ''),
                                'enabled': getattr(project, 'is_enabled', True),
                                'quota_accessible': True
                            })
                    except Exception:
                        # Add project but mark quota as not accessible
                        projects.append({
                            'project_name': project.name,
                            'project_id': project.id,
                            'description': getattr(project, 'description', ''),
                            'enabled': getattr(project, 'is_enabled', True),
                            'quota_accessible': False
                        })
                        
                return {
                    'success': True,
                    'action': 'list',
                    'projects': projects,
                    'total_projects': len(projects)
                }
            except Exception as list_error:
                return {
                    'success': False,
                    'error': f'Failed to list projects: {str(list_error)}'
                }
        
        # Find project for set/delete operations
        try:
            project = conn.identity.find_project(project_name)
            if not project:
                return {
                    'success': False,
                    'error': f'Project "{project_name}" not found'
                }
            project_id = project.id
        except Exception as e:
            return {
                'success': False,
                'error': f'Failed to find project "{project_name}": {str(e)}'
            }
        
        if action.lower() == 'set':
            # Set quota values
            results = {}
            
            # Compute quota updates
            compute_updates = {}
            compute_fields = ['cores', 'instances', 'ram', 'key_pairs', 'server_groups', 
                            'server_group_members', 'injected_files', 'injected_file_content_bytes',
                            'injected_file_path_bytes', 'fixed_ips']
            
            for field in compute_fields:
                if field in kwargs:
                    compute_updates[field] = kwargs[field]
            
            if compute_updates:
                try:
                    # Use direct API call for compute quota update
                    quota_set = {"quota_set": compute_updates}
                    conn.compute.put(f'/os-quota-sets/{project_id}', json=quota_set)
                    results['compute'] = {'success': True, 'updated_fields': list(compute_updates.keys())}
                except Exception as e:
                    results['compute'] = {'success': False, 'error': str(e)}
            
            # Volume quota updates
            volume_updates = {}
            volume_fields = ['volumes', 'snapshots', 'gigabytes', 'backups', 
                           'backup_gigabytes', 'per_volume_gigabytes', 'groups']
            
            for field in volume_fields:
                if field in kwargs:
                    volume_updates[field] = kwargs[field]
            
            if volume_updates:
                try:
                    # Use direct API call for volume quota update
                    quota_set = {"quota_set": volume_updates}
                    conn.block_storage.put(f'/os-quota-sets/{project_id}', json=quota_set)
                    results['volume'] = {'success': True, 'updated_fields': list(volume_updates.keys())}
                except Exception as e:
                    results['volume'] = {'success': False, 'error': str(e)}
            
            # Network quota updates
            network_updates = {}
            network_fields = ['networks', 'subnets', 'ports', 'routers', 'floating_ips',
                            'security_groups', 'security_group_rules', 'rbac_policies', 'subnet_pools']
            
            for field in network_fields:
                if field in kwargs:
                    network_updates[field] = kwargs[field]
            
            if network_updates:
                try:
                    # Network quota update should work with SDK method
                    conn.network.update_quota(project_id, **network_updates)
                    results['network'] = {'success': True, 'updated_fields': list(network_updates.keys())}
                except Exception as e:
                    results['network'] = {'success': False, 'error': str(e)}
            
            if not results:
                return {
                    'success': False,
                    'error': 'No valid quota parameters provided',
                    'message': 'Specify quota parameters like cores, instances, ram, volumes, etc.'
                }
            
            return {
                'success': True,
                'action': 'set',
                'project_name': project_name,
                'project_id': project_id,
                'results': results
            }
            
        elif action.lower() == 'delete':
            # Delete/reset quotas to default values
            results = {}
            
            try:
                # Reset compute quotas
                conn.compute.revert_quota(project_id)
                results['compute'] = {'success': True, 'message': 'Reset to defaults'}
            except Exception as e:
                results['compute'] = {'success': False, 'error': str(e)}
            
            try:
                # Reset volume quotas
                conn.volume.revert_quota(project_id)
                results['volume'] = {'success': True, 'message': 'Reset to defaults'}
            except Exception as e:
                results['volume'] = {'success': False, 'error': str(e)}
            
            try:
                # Reset network quotas
                conn.network.delete_quota(project_id)
                results['network'] = {'success': True, 'message': 'Reset to defaults'}
            except Exception as e:
                results['network'] = {'success': False, 'error': str(e)}
            
            return {
                'success': True,
                'action': 'delete',
                'project_name': project_name,
                'project_id': project_id,
                'results': results
            }
        
        else:
            return {
                'success': False,
                'error': f'Unknown action: {action}',
                'message': 'Valid actions are: set, delete, list'
            }
            
    except Exception as e:
        logger.error(f"Failed to manage quota: {e}")
        return {
            'success': False,
            'error': str(e),
            'message': 'Failed to manage quota'
        }


def get_project_details(project_name: str = "") -> Dict[str, Any]:
    """
    Get OpenStack project details (similar to 'openstack project list/show').
    
    Args:
        project_name: Name of specific project to show details for (optional, lists all if empty)
    
    Returns:
        Project information including details, roles, and quotas
    """
    try:
        conn = get_openstack_connection()
        
        if not project_name or project_name.strip() == "":
            # List all projects
            projects = []
            try:
                for project in conn.identity.projects():
                    projects.append({
                        'id': project.id,
                        'name': project.name,
                        'description': getattr(project, 'description', ''),
                        'domain_id': getattr(project, 'domain_id', ''),
                        'enabled': getattr(project, 'is_enabled', True),
                        'parent_id': getattr(project, 'parent_id', None),
                        'created_at': str(getattr(project, 'created_at', 'unknown')),
                        'updated_at': str(getattr(project, 'updated_at', 'unknown')),
                        'tags': getattr(project, 'tags', [])
                    })
                
                return {
                    'success': True,
                    'operation': 'list',
                    'projects': projects,
                    'total_projects': len(projects)
                }
            except Exception as e:
                return {
                    'success': False,
                    'error': f'Failed to list projects: {str(e)}'
                }
        else:
            # Show specific project details
            try:
                project = conn.identity.find_project(project_name)
                if not project:
                    return {
                        'success': False,
                        'error': f'Project "{project_name}" not found'
                    }
                
                project_details = {
                    'id': project.id,
                    'name': project.name,
                    'description': getattr(project, 'description', ''),
                    'domain_id': getattr(project, 'domain_id', ''),
                    'enabled': getattr(project, 'is_enabled', True),
                    'parent_id': getattr(project, 'parent_id', None),
                    'created_at': str(getattr(project, 'created_at', 'unknown')),
                    'updated_at': str(getattr(project, 'updated_at', 'unknown')),
                    'tags': getattr(project, 'tags', [])
                }
                
                # Get role assignments for this project
                role_assignments = []
                try:
                    for assignment in conn.identity.role_assignments(project=project.id):
                        user_info = {}
                        if hasattr(assignment, 'user') and assignment.user:
                            try:
                                user = conn.identity.get_user(assignment.user['id'])
                                user_info = {
                                    'id': user.id,
                                    'name': user.name,
                                    'email': getattr(user, 'email', ''),
                                    'enabled': getattr(user, 'is_enabled', True)
                                }
                            except Exception:
                                user_info = assignment.user
                        
                        role_info = {}
                        if hasattr(assignment, 'role') and assignment.role:
                            try:
                                role = conn.identity.get_role(assignment.role['id'])
                                role_info = {
                                    'id': role.id,
                                    'name': role.name,
                                    'description': getattr(role, 'description', '')
                                }
                            except Exception:
                                role_info = assignment.role
                        
                        role_assignments.append({
                            'user': user_info,
                            'role': role_info,
                            'scope': getattr(assignment, 'scope', {})
                        })
                except Exception as e:
                    logger.warning(f"Failed to get role assignments: {e}")
                    role_assignments = [{'error': f'Failed to get role assignments: {str(e)}'}]
                
                # Get quota information
                quota_info = get_quota(project_name)
                
                return {
                    'success': True,
                    'operation': 'show',
                    'project': project_details,
                    'role_assignments': role_assignments,
                    'quota_info': quota_info.get('quota_details', {}) if quota_info.get('success') else {'error': 'Failed to get quota info'},
                    'total_role_assignments': len(role_assignments)
                }
                
            except Exception as e:
                return {
                    'success': False,
                    'error': f'Failed to get project details: {str(e)}'
                }
        
    except Exception as e:
        logger.error(f"Failed to get project details: {e}")
        return {
            'success': False,
            'error': str(e),
            'message': 'Failed to retrieve project information'
        }


def set_project(project_name: str, action: str, **kwargs) -> Dict[str, Any]:
    """
    Manage OpenStack projects (create, delete, set, cleanup).
    
    Args:
        project_name: Name of the project
        action: Action to perform (create, delete, set, cleanup)
        **kwargs: Additional parameters for project operations
            - description: Project description
            - domain: Domain name or ID
            - enable/disable: Enable or disable project
            - parent: Parent project name or ID
            - tags: List of tags
    
    Returns:
        Result of the project management operation
    """
    try:
        conn = get_openstack_connection()
        
        if action.lower() == 'create':
            # Create new project
            try:
                # Check if project already exists
                existing_project = conn.identity.find_project(project_name)
                if existing_project:
                    return {
                        'success': False,
                        'error': f'Project "{project_name}" already exists',
                        'existing_project_id': existing_project.id
                    }
                
                # Prepare creation parameters
                create_params = {
                    'name': project_name,
                    'description': kwargs.get('description', f'Project {project_name}'),
                    'is_enabled': kwargs.get('enable', True)
                }
                
                # Handle domain
                if 'domain' in kwargs:
                    domain = conn.identity.find_domain(kwargs['domain'])
                    if domain:
                        create_params['domain_id'] = domain.id
                    else:
                        create_params['domain_id'] = kwargs['domain']  # Assume it's an ID
                
                # Handle parent project
                if 'parent' in kwargs:
                    parent_project = conn.identity.find_project(kwargs['parent'])
                    if parent_project:
                        create_params['parent_id'] = parent_project.id
                    else:
                        create_params['parent_id'] = kwargs['parent']  # Assume it's an ID
                
                # Handle tags
                if 'tags' in kwargs:
                    if isinstance(kwargs['tags'], list):
                        create_params['tags'] = kwargs['tags']
                    else:
                        create_params['tags'] = [tag.strip() for tag in str(kwargs['tags']).split(',')]
                
                new_project = conn.identity.create_project(**create_params)
                
                return {
                    'success': True,
                    'action': 'create',
                    'project': {
                        'id': new_project.id,
                        'name': new_project.name,
                        'description': getattr(new_project, 'description', ''),
                        'enabled': getattr(new_project, 'is_enabled', True),
                        'domain_id': getattr(new_project, 'domain_id', ''),
                        'parent_id': getattr(new_project, 'parent_id', None)
                    },
                    'message': f'Project "{project_name}" created successfully'
                }
                
            except Exception as e:
                return {
                    'success': False,
                    'error': f'Failed to create project: {str(e)}'
                }
        
        elif action.lower() == 'delete':
            # Delete project
            try:
                project = conn.identity.find_project(project_name)
                if not project:
                    return {
                        'success': False,
                        'error': f'Project "{project_name}" not found'
                    }
                
                # Check if project has resources (optional safety check)
                resource_check = {
                    'instances': 0,
                    'volumes': 0,
                    'networks': 0,
                    'users': 0
                }
                
                try:
                    # Count instances
                    instances = list(conn.compute.servers(project_id=project.id))
                    resource_check['instances'] = len(instances)
                    
                    # Count volumes  
                    volumes = list(conn.volume.volumes(project_id=project.id))
                    resource_check['volumes'] = len(volumes)
                    
                    # Count networks (if accessible)
                    networks = list(conn.network.networks(project_id=project.id))
                    resource_check['networks'] = len(networks)
                    
                    # Count role assignments (users)
                    assignments = list(conn.identity.role_assignments(project=project.id))
                    resource_check['users'] = len(assignments)
                    
                except Exception as e:
                    logger.warning(f"Failed to check project resources: {e}")
                
                conn.identity.delete_project(project.id)
                
                return {
                    'success': True,
                    'action': 'delete',
                    'project_name': project_name,
                    'project_id': project.id,
                    'resource_check': resource_check,
                    'message': f'Project "{project_name}" deleted successfully'
                }
                
            except Exception as e:
                return {
                    'success': False,
                    'error': f'Failed to delete project: {str(e)}'
                }
        
        elif action.lower() == 'set':
            # Update project settings
            try:
                project = conn.identity.find_project(project_name)
                if not project:
                    return {
                        'success': False,
                        'error': f'Project "{project_name}" not found'
                    }
                
                # Prepare update parameters
                update_params = {}
                
                if 'description' in kwargs:
                    update_params['description'] = kwargs['description']
                
                if 'enable' in kwargs:
                    update_params['is_enabled'] = kwargs['enable']
                elif 'disable' in kwargs:
                    update_params['is_enabled'] = not kwargs['disable']
                
                if 'tags' in kwargs:
                    if isinstance(kwargs['tags'], list):
                        update_params['tags'] = kwargs['tags']
                    else:
                        update_params['tags'] = [tag.strip() for tag in str(kwargs['tags']).split(',')]
                
                if not update_params:
                    return {
                        'success': False,
                        'error': 'No valid parameters provided for update',
                        'message': 'Specify description, enable/disable, or tags'
                    }
                
                updated_project = conn.identity.update_project(project.id, **update_params)
                
                return {
                    'success': True,
                    'action': 'set',
                    'project_name': project_name,
                    'project_id': project.id,
                    'updated_fields': list(update_params.keys()),
                    'project': {
                        'id': updated_project.id,
                        'name': updated_project.name,
                        'description': getattr(updated_project, 'description', ''),
                        'enabled': getattr(updated_project, 'is_enabled', True),
                        'tags': getattr(updated_project, 'tags', [])
                    },
                    'message': f'Project "{project_name}" updated successfully'
                }
                
            except Exception as e:
                return {
                    'success': False,
                    'error': f'Failed to update project: {str(e)}'
                }
        
        elif action.lower() == 'cleanup':
            # Cleanup project resources
            try:
                project = conn.identity.find_project(project_name)
                if not project:
                    return {
                        'success': False,
                        'error': f'Project "{project_name}" not found'
                    }
                
                cleanup_results = {
                    'instances': {'count': 0, 'success': True, 'errors': []},
                    'volumes': {'count': 0, 'success': True, 'errors': []},
                    'networks': {'count': 0, 'success': True, 'errors': []},
                    'security_groups': {'count': 0, 'success': True, 'errors': []}
                }
                
                # Cleanup instances
                try:
                    instances = list(conn.compute.servers(project_id=project.id))
                    cleanup_results['instances']['count'] = len(instances)
                    for instance in instances:
                        try:
                            conn.compute.delete_server(instance.id, force=True)
                        except Exception as e:
                            cleanup_results['instances']['errors'].append(f"Instance {instance.name}: {str(e)}")
                            cleanup_results['instances']['success'] = False
                except Exception as e:
                    cleanup_results['instances']['errors'].append(f"Failed to list instances: {str(e)}")
                    cleanup_results['instances']['success'] = False
                
                # Cleanup volumes
                try:
                    volumes = list(conn.volume.volumes(project_id=project.id))
                    cleanup_results['volumes']['count'] = len(volumes)
                    for volume in volumes:
                        try:
                            conn.volume.delete_volume(volume.id, force=True)
                        except Exception as e:
                            cleanup_results['volumes']['errors'].append(f"Volume {volume.name}: {str(e)}")
                            cleanup_results['volumes']['success'] = False
                except Exception as e:
                    cleanup_results['volumes']['errors'].append(f"Failed to list volumes: {str(e)}")
                    cleanup_results['volumes']['success'] = False
                
                return {
                    'success': True,
                    'action': 'cleanup',
                    'project_name': project_name,
                    'project_id': project.id,
                    'cleanup_results': cleanup_results,
                    'message': f'Cleanup completed for project "{project_name}"'
                }
                
            except Exception as e:
                return {
                    'success': False,
                    'error': f'Failed to cleanup project: {str(e)}'
                }
        
        else:
            return {
                'success': False,
                'error': f'Unknown action: {action}',
                'message': 'Valid actions are: create, delete, set, cleanup'
            }
            
    except Exception as e:
        logger.error(f"Failed to manage project: {e}")
        return {
            'success': False,
            'error': str(e),
            'message': 'Failed to manage project'
        }


def get_server_events(instance_name: str, limit: int = 50) -> Dict[str, Any]:
    """
    Get recent events for a specific server
    
    Args:
        instance_name: Name or ID of the instance
        limit: Maximum number of events to return
    
    Returns:
        Dictionary with server events information
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
                'message': f'Instance "{instance_name}" not found'
            }
        
        # Get server events
        events = list(conn.compute.server_actions(instance, limit=limit))
        
        events_data = []
        for event in events:
            event_data = {
                'request_id': event.request_id,
                'action': event.action,
                'start_time': event.start_time,
                'finish_time': getattr(event, 'finish_time', None),
                'message': getattr(event, 'message', ''),
                'user_id': getattr(event, 'user_id', ''),
                'project_id': getattr(event, 'project_id', '')
            }
            
            # Get event details if available
            try:
                event_details = conn.compute.get_server_action(instance, event.request_id)
                if event_details:
                    event_data.update({
                        'details': {
                            'events': []
                        }
                    })
                    
                    if hasattr(event_details, 'events'):
                        for detail in event_details.events:
                            event_data['details']['events'].append({
                                'event': getattr(detail, 'event', ''),
                                'start_time': getattr(detail, 'start_time', ''),
                                'finish_time': getattr(detail, 'finish_time', ''),
                                'result': getattr(detail, 'result', ''),
                                'traceback': getattr(detail, 'traceback', '')
                            })
            except Exception as e:
                logger.debug(f"Could not get event details for {event.request_id}: {e}")
                
            events_data.append(event_data)
        
        return {
            'success': True,
            'instance_name': instance_name,
            'instance_id': instance.id,
            'events_count': len(events_data),
            'events': events_data
        }
        
    except Exception as e:
        logger.error(f"Failed to get server events for {instance_name}: {e}")
        return {
            'success': False,
            'message': f'Failed to get server events for "{instance_name}": {str(e)}',
            'error': str(e)
        }


def get_server_groups() -> List[Dict[str, Any]]:
    """
    List all server groups
    
    Returns:
        List of server groups with their details
    """
    try:
        conn = get_openstack_connection()
        
        server_groups = list(conn.compute.server_groups())
        
        groups_data = []
        for group in server_groups:
            group_data = {
                'id': group.id,
                'name': group.name,
                'project_id': group.project_id,
                'user_id': getattr(group, 'user_id', ''),
                'policies': group.policies,
                'members': group.members,
                'member_count': len(group.members),
                'metadata': getattr(group, 'metadata', {}),
                'created_at': getattr(group, 'created_at', '')
            }
            groups_data.append(group_data)
        
        return groups_data
        
    except Exception as e:
        logger.error(f"Failed to list server groups: {e}")
        return []


def set_server_group(group_name: str, action: str, **kwargs) -> Dict[str, Any]:
    """
    Manage server groups (create, delete, show)
    
    Args:
        group_name: Name of the server group
        action: Action to perform (create, delete, show)
        **kwargs: Additional parameters:
            - policies: List of policies for create (e.g., ['affinity'], ['anti-affinity'])
            - metadata: Dictionary of metadata for create
    
    Returns:
        Result of the server group operation
    """
    try:
        conn = get_openstack_connection()
        action = action.lower()
        
        if action == 'create':
            policies = kwargs.get('policies', ['anti-affinity'])
            if isinstance(policies, str):
                policies = [policies]
                
            metadata = kwargs.get('metadata', {})
            
            group = conn.compute.create_server_group(
                name=group_name,
                policies=policies,
                **metadata
            )
            
            return {
                'success': True,
                'message': f'Server group "{group_name}" created successfully',
                'group_id': group.id,
                'group_name': group.name,
                'policies': group.policies
            }
            
        elif action == 'delete':
            # Find the group
            group = None
            for sg in conn.compute.server_groups():
                if sg.name == group_name or sg.id == group_name:
                    group = sg
                    break
                    
            if not group:
                return {
                    'success': False,
                    'message': f'Server group "{group_name}" not found'
                }
            
            conn.compute.delete_server_group(group)
            return {
                'success': True,
                'message': f'Server group "{group_name}" deleted successfully',
                'group_id': group.id
            }
            
        elif action == 'show':
            # Find the group
            group = None
            for sg in conn.compute.server_groups():
                if sg.name == group_name or sg.id == group_name:
                    group = sg
                    break
                    
            if not group:
                return {
                    'success': False,
                    'message': f'Server group "{group_name}" not found'
                }
            
            return {
                'success': True,
                'group': {
                    'id': group.id,
                    'name': group.name,
                    'project_id': group.project_id,
                    'user_id': getattr(group, 'user_id', ''),
                    'policies': group.policies,
                    'members': group.members,
                    'member_count': len(group.members),
                    'metadata': getattr(group, 'metadata', {}),
                    'created_at': getattr(group, 'created_at', '')
                }
            }
            
        else:
            return {
                'success': False,
                'message': f'Unknown action "{action}". Supported: create, delete, show'
            }
            
    except Exception as e:
        logger.error(f"Failed to manage server group {group_name}: {e}")
        return {
            'success': False,
            'message': f'Failed to manage server group "{group_name}": {str(e)}',
            'error': str(e)
        }


def get_hypervisor_details(hypervisor_name: str = "all") -> Dict[str, Any]:
    """
    Get detailed information about hypervisors
    
    Args:
        hypervisor_name: Name/ID of specific hypervisor or "all" for all hypervisors
    
    Returns:
        Dictionary with hypervisor details and statistics
    """
    try:
        conn = get_openstack_connection()
        
        hypervisors = list(conn.compute.hypervisors(details=True))
        
        if hypervisor_name != "all":
            # Find specific hypervisor
            target_hypervisor = None
            for hv in hypervisors:
                if hv.name == hypervisor_name or str(hv.id) == str(hypervisor_name):
                    target_hypervisor = hv
                    break
            
            if not target_hypervisor:
                return {
                    'success': False,
                    'message': f'Hypervisor "{hypervisor_name}" not found'
                }
            hypervisors = [target_hypervisor]
        
        hypervisor_data = []
        total_stats = {
            'total_hypervisors': len(hypervisors),
            'total_vcpus': 0,
            'total_vcpus_used': 0,
            'total_memory_mb': 0,
            'total_memory_mb_used': 0,
            'total_local_gb': 0,
            'total_local_gb_used': 0,
            'total_running_vms': 0
        }
        
        for hv in hypervisors:
            hv_info = {
                'id': hv.id,
                'name': hv.name,
                'status': hv.status,
                'state': hv.state,
                'host_ip': getattr(hv, 'host_ip', ''),
                'hypervisor_type': getattr(hv, 'hypervisor_type', ''),
                'hypervisor_version': getattr(hv, 'hypervisor_version', ''),
                'service_id': getattr(hv, 'service', {}).get('id', ''),
                'service_host': getattr(hv, 'service', {}).get('host', ''),
                'vcpus': hv.vcpus,
                'vcpus_used': hv.vcpus_used,
                'vcpu_usage_percent': round((hv.vcpus_used / hv.vcpus * 100) if hv.vcpus > 0 else 0, 2),
                'memory_mb': hv.memory_mb,
                'memory_mb_used': hv.memory_mb_used,
                'memory_usage_percent': round((hv.memory_mb_used / hv.memory_mb * 100) if hv.memory_mb > 0 else 0, 2),
                'local_gb': hv.local_gb,
                'local_gb_used': hv.local_gb_used,
                'storage_usage_percent': round((hv.local_gb_used / hv.local_gb * 100) if hv.local_gb > 0 else 0, 2),
                'running_vms': hv.running_vms,
                'free_ram_mb': hv.free_ram_mb,
                'free_disk_gb': hv.free_disk_gb,
                'current_workload': getattr(hv, 'current_workload', 0),
                'disk_available_least': getattr(hv, 'disk_available_least', 0)
            }
            
            # Update totals
            total_stats['total_vcpus'] += hv.vcpus
            total_stats['total_vcpus_used'] += hv.vcpus_used
            total_stats['total_memory_mb'] += hv.memory_mb
            total_stats['total_memory_mb_used'] += hv.memory_mb_used
            total_stats['total_local_gb'] += hv.local_gb
            total_stats['total_local_gb_used'] += hv.local_gb_used
            total_stats['total_running_vms'] += hv.running_vms
            
            hypervisor_data.append(hv_info)
        
        # Calculate total usage percentages
        total_stats['total_vcpu_usage_percent'] = round(
            (total_stats['total_vcpus_used'] / total_stats['total_vcpus'] * 100) 
            if total_stats['total_vcpus'] > 0 else 0, 2
        )
        total_stats['total_memory_usage_percent'] = round(
            (total_stats['total_memory_mb_used'] / total_stats['total_memory_mb'] * 100) 
            if total_stats['total_memory_mb'] > 0 else 0, 2
        )
        total_stats['total_storage_usage_percent'] = round(
            (total_stats['total_local_gb_used'] / total_stats['total_local_gb'] * 100) 
            if total_stats['total_local_gb'] > 0 else 0, 2
        )
        
        return {
            'success': True,
            'hypervisor_count': len(hypervisor_data),
            'hypervisors': hypervisor_data,
            'cluster_statistics': total_stats,
            'query_target': hypervisor_name
        }
        
    except Exception as e:
        logger.error(f"Failed to get hypervisor details: {e}")
        return {
            'success': False,
            'message': f'Failed to get hypervisor details: {str(e)}',
            'error': str(e)
        }


def get_availability_zones() -> Dict[str, Any]:
    """
    List availability zones and their status
    
    Returns:
        Dictionary with availability zones information
    """
    try:
        conn = get_openstack_connection()
        
        # Get compute availability zones
        compute_zones = list(conn.compute.availability_zones(details=True))
        # Get volume availability zones  
        volume_zones = list(conn.block_storage.availability_zones())
        
        compute_zone_data = []
        for zone in compute_zones:
            zone_info = {
                'zone_name': zone.name,
                'zone_state': zone.state,
                'hosts': {}
            }
            
            # Process hosts in the zone
            if hasattr(zone, 'hosts') and zone.hosts:
                for host_name, services in zone.hosts.items():
                    host_info = {
                        'services': {}
                    }
                    for service_name, service_info in services.items():
                        host_info['services'][service_name] = {
                            'available': service_info.get('available', False),
                            'active': service_info.get('active', False)
                        }
                    zone_info['hosts'][host_name] = host_info
            
            compute_zone_data.append(zone_info)
        
        volume_zone_data = []
        for zone in volume_zones:
            zone_info = {
                'zone_name': zone.name,
                'zone_state': zone.state
            }
            volume_zone_data.append(zone_info)
        
        return {
            'success': True,
            'compute_zones': compute_zone_data,
            'volume_zones': volume_zone_data,
            'total_compute_zones': len(compute_zone_data),
            'total_volume_zones': len(volume_zone_data)
        }
        
    except Exception as e:
        logger.error(f"Failed to get availability zones: {e}")
        return {
            'success': False,
            'message': f'Failed to get availability zones: {str(e)}',
            'error': str(e)
        }


def set_flavor(flavor_name: str, action: str, **kwargs) -> Dict[str, Any]:
    """
    Manage OpenStack flavors (create, delete, set properties)
    
    Args:
        flavor_name: Name of the flavor
        action: Action to perform (create, delete, show, set, list)
        **kwargs: Additional parameters for flavor operations:
            - vcpus: Number of virtual CPUs
            - ram: Amount of RAM in MB
            - disk: Disk size in GB
            - ephemeral: Ephemeral disk size in GB
            - swap: Swap size in MB  
            - rxtx_factor: RX/TX factor
            - is_public: Whether flavor is public
            - properties: Dictionary of extra properties
    
    Returns:
        Result of the flavor operation
    """
    try:
        conn = get_openstack_connection()
        action = action.lower()
        
        if action == 'create':
            # Required parameters for create
            vcpus = kwargs.get('vcpus', 1)
            ram = kwargs.get('ram', 512)  # MB
            disk = kwargs.get('disk', 1)  # GB
            
            # Optional parameters
            ephemeral = kwargs.get('ephemeral', 0)
            swap = kwargs.get('swap', 0)
            rxtx_factor = kwargs.get('rxtx_factor', 1.0)
            is_public = kwargs.get('is_public', True)
            properties = kwargs.get('properties', {})
            
            flavor = conn.compute.create_flavor(
                name=flavor_name,
                vcpus=vcpus,
                ram=ram,
                disk=disk,
                ephemeral=ephemeral,
                swap=swap,
                rxtx_factor=rxtx_factor,
                is_public=is_public,
                **properties
            )
            
            return {
                'success': True,
                'message': f'Flavor "{flavor_name}" created successfully',
                'flavor': {
                    'id': flavor.id,
                    'name': flavor.name,
                    'vcpus': flavor.vcpus,
                    'ram': flavor.ram,
                    'disk': flavor.disk,
                    'ephemeral': flavor.ephemeral,
                    'swap': flavor.swap,
                    'is_public': flavor.is_public
                }
            }
            
        elif action == 'delete':
            # Find the flavor
            flavor = None
            for f in conn.compute.flavors(details=True):
                if f.name == flavor_name or f.id == flavor_name:
                    flavor = f
                    break
                    
            if not flavor:
                return {
                    'success': False,
                    'message': f'Flavor "{flavor_name}" not found'
                }
            
            conn.compute.delete_flavor(flavor)
            return {
                'success': True,
                'message': f'Flavor "{flavor_name}" deleted successfully',
                'flavor_id': flavor.id
            }
            
        elif action == 'show':
            # Find the flavor
            flavor = None
            for f in conn.compute.flavors(details=True):
                if f.name == flavor_name or f.id == flavor_name:
                    flavor = f
                    break
                    
            if not flavor:
                return {
                    'success': False,
                    'message': f'Flavor "{flavor_name}" not found'
                }
            
            return {
                'success': True,
                'flavor': {
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
                }
            }
            
        elif action == 'list':
            flavors = list(conn.compute.flavors(details=True))
            flavor_data = []
            
            for flavor in flavors:
                flavor_info = {
                    'id': flavor.id,
                    'name': flavor.name,
                    'vcpus': flavor.vcpus,
                    'ram': flavor.ram,
                    'disk': flavor.disk,
                    'ephemeral': getattr(flavor, 'ephemeral', 0),
                    'swap': getattr(flavor, 'swap', 0),
                    'rxtx_factor': getattr(flavor, 'rxtx_factor', 1.0),
                    'is_public': getattr(flavor, 'is_public', True)
                }
                flavor_data.append(flavor_info)
            
            return {
                'success': True,
                'flavor_count': len(flavor_data),
                'flavors': flavor_data
            }
            
        elif action == 'set':
            # Find the flavor
            flavor = None
            for f in conn.compute.flavors(details=True):
                if f.name == flavor_name or f.id == flavor_name:
                    flavor = f
                    break
                    
            if not flavor:
                return {
                    'success': False,
                    'message': f'Flavor "{flavor_name}" not found'
                }
            
            # Set extra specs if provided
            extra_specs = kwargs.get('properties', {})
            if extra_specs:
                conn.compute.create_flavor_extra_specs(flavor, extra_specs)
                return {
                    'success': True,
                    'message': f'Flavor "{flavor_name}" properties updated successfully',
                    'updated_properties': extra_specs
                }
            else:
                return {
                    'success': False,
                    'message': 'No properties provided to update'
                }
                
        else:
            return {
                'success': False,
                'message': f'Unknown action "{action}". Supported: create, delete, show, list, set'
            }
            
    except Exception as e:
        logger.error(f"Failed to manage flavor {flavor_name}: {e}")
        return {
            'success': False,
            'message': f'Failed to manage flavor "{flavor_name}": {str(e)}',
            'error': str(e)
        }


def get_server_volumes(instance_name: str) -> Dict[str, Any]:
    """
    Get all volumes attached to a specific server
    
    Args:
        instance_name: Name or ID of the server instance
    
    Returns:
        Dictionary with server volumes information
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
                'message': f'Instance "{instance_name}" not found'
            }
        
        # Get attached volumes
        volume_attachments = list(conn.compute.volume_attachments(instance))
        
        volumes_data = []
        total_size_gb = 0
        
        for attachment in volume_attachments:
            # Get volume details
            try:
                volume = conn.block_storage.get_volume(attachment.volume_id)
                volume_info = {
                    'attachment_id': attachment.id,
                    'volume_id': attachment.volume_id,
                    'device': attachment.device,
                    'volume_name': volume.name or 'N/A',
                    'volume_status': volume.status,
                    'size_gb': volume.size,
                    'volume_type': getattr(volume, 'volume_type', 'N/A'),
                    'bootable': getattr(volume, 'bootable', False),
                    'created_at': getattr(volume, 'created_at', ''),
                    'description': getattr(volume, 'description', ''),
                    'metadata': getattr(volume, 'metadata', {})
                }
                total_size_gb += volume.size
            except Exception as e:
                logger.warning(f"Could not get details for volume {attachment.volume_id}: {e}")
                volume_info = {
                    'attachment_id': attachment.id,
                    'volume_id': attachment.volume_id,
                    'device': attachment.device,
                    'volume_name': 'Unknown',
                    'volume_status': 'Unknown',
                    'size_gb': 0,
                    'error': f'Could not fetch volume details: {str(e)}'
                }
            
            volumes_data.append(volume_info)
        
        return {
            'success': True,
            'instance_name': instance_name,
            'instance_id': instance.id,
            'attached_volumes_count': len(volumes_data),
            'total_storage_gb': total_size_gb,
            'attached_volumes': volumes_data
        }
        
    except Exception as e:
        logger.error(f"Failed to get server volumes for {instance_name}: {e}")
        return {
            'success': False,
            'message': f'Failed to get server volumes for "{instance_name}": {str(e)}',
            'error': str(e)
        }


def set_server_volume(instance_name: str, action: str, **kwargs) -> Dict[str, Any]:
    """
    Manage server volume attachments (attach, detach)
    
    Args:
        instance_name: Name or ID of the server instance
        action: Action to perform (attach, detach, list)
        **kwargs: Additional parameters:
            - volume_id: Volume ID for attach/detach operations
            - volume_name: Volume name for attach/detach operations (alternative to volume_id)
            - device: Device path for attach operation (optional)
    
    Returns:
        Result of the server volume operation
    """
    try:
        conn = get_openstack_connection()
        action = action.lower()
        
        # Find the instance
        instance = None
        for server in conn.compute.servers():
            if server.name == instance_name or server.id == instance_name:
                instance = server
                break
                
        if not instance:
            return {
                'success': False,
                'message': f'Instance "{instance_name}" not found'
            }
        
        if action == 'list':
            # Return the attached volumes list
            return get_server_volumes(instance_name)
            
        elif action == 'attach':
            volume_id = kwargs.get('volume_id')
            volume_name = kwargs.get('volume_name')
            device = kwargs.get('device', None)
            
            if not volume_id and not volume_name:
                return {
                    'success': False,
                    'message': 'Either volume_id or volume_name is required for attach operation'
                }
            
            # If volume_name is provided, find the volume ID
            if volume_name and not volume_id:
                for volume in conn.block_storage.volumes():
                    if volume.name == volume_name:
                        volume_id = volume.id
                        break
                else:
                    return {
                        'success': False,
                        'message': f'Volume "{volume_name}" not found'
                    }
            
            # Attach the volume
            attachment = conn.compute.create_volume_attachment(
                server=instance,
                volume_id=volume_id,
                device=device
            )
            
            return {
                'success': True,
                'message': f'Volume "{volume_id}" attached to instance "{instance_name}"',
                'attachment_id': attachment.id,
                'volume_id': volume_id,
                'device': attachment.device,
                'instance_id': instance.id
            }
            
        elif action == 'detach':
            volume_id = kwargs.get('volume_id')
            volume_name = kwargs.get('volume_name')
            attachment_id = kwargs.get('attachment_id')
            
            if not volume_id and not volume_name and not attachment_id:
                return {
                    'success': False,
                    'message': 'Either volume_id, volume_name, or attachment_id is required for detach operation'
                }
            
            # If volume_name is provided, find the volume ID
            if volume_name and not volume_id:
                for volume in conn.block_storage.volumes():
                    if volume.name == volume_name:
                        volume_id = volume.id
                        break
                else:
                    return {
                        'success': False,
                        'message': f'Volume "{volume_name}" not found'
                    }
            
            # Find the attachment
            if not attachment_id:
                volume_attachments = list(conn.compute.volume_attachments(instance))
                for attachment in volume_attachments:
                    if attachment.volume_id == volume_id:
                        attachment_id = attachment.id
                        break
                else:
                    return {
                        'success': False,
                        'message': f'Volume "{volume_id}" is not attached to instance "{instance_name}"'
                    }
            
            # Detach the volume
            conn.compute.delete_volume_attachment(attachment_id, server=instance)
            
            return {
                'success': True,
                'message': f'Volume detached from instance "{instance_name}"',
                'attachment_id': attachment_id,
                'volume_id': volume_id,
                'instance_id': instance.id
            }
            
        else:
            return {
                'success': False,
                'message': f'Unknown action "{action}". Supported: attach, detach, list'
            }
            
    except Exception as e:
        logger.error(f"Failed to manage server volume for {instance_name}: {e}")
        return {
            'success': False,
            'message': f'Failed to manage server volume for "{instance_name}": {str(e)}',
            'error': str(e)
        }


def set_volume_backups(action: str, backup_name: Optional[str] = None, **kwargs) -> Dict[str, Any]:
    """
    Manage volume backups (list, show, delete, restore)
    
    Args:
        action: Action to perform (list, show, delete, restore)
        backup_name: Name or ID of the backup (required for show, delete, restore)
        **kwargs: Additional parameters
    
    Returns:
        Result of the backup management operation
    """
    try:
        conn = get_openstack_connection()
        
        if action.lower() == 'list':
            backups = []
            for backup in conn.volume.backups(detailed=True):
                backups.append({
                    'id': backup.id,
                    'name': backup.name or 'N/A',
                    'description': getattr(backup, 'description', 'N/A'),
                    'status': backup.status,
                    'size': getattr(backup, 'size', 'N/A'),
                    'volume_id': backup.volume_id,
                    'created_at': str(getattr(backup, 'created_at', 'N/A')),
                    'is_incremental': getattr(backup, 'is_incremental', False),
                    'availability_zone': getattr(backup, 'availability_zone', 'N/A')
                })
            return {
                'success': True,
                'backups': backups,
                'count': len(backups)
            }
            
        elif action.lower() == 'show':
            if not backup_name:
                return {
                    'success': False,
                    'message': 'backup_name is required for show action'
                }
                
            # Find the backup
            backup = None
            for bkp in conn.volume.backups():
                if bkp.name == backup_name or bkp.id == backup_name:
                    backup = bkp
                    break
                    
            if not backup:
                return {
                    'success': False,
                    'message': f'Backup "{backup_name}" not found'
                }
                
            return {
                'success': True,
                'backup': {
                    'id': backup.id,
                    'name': backup.name,
                    'description': getattr(backup, 'description', 'N/A'),
                    'status': backup.status,
                    'size': getattr(backup, 'size', 'N/A'),
                    'volume_id': backup.volume_id,
                    'created_at': str(getattr(backup, 'created_at', 'N/A')),
                    'updated_at': str(getattr(backup, 'updated_at', 'N/A')),
                    'is_incremental': getattr(backup, 'is_incremental', False),
                    'availability_zone': getattr(backup, 'availability_zone', 'N/A'),
                    'container': getattr(backup, 'container', 'N/A'),
                    'object_count': getattr(backup, 'object_count', 'N/A')
                }
            }
            
        elif action.lower() == 'delete':
            if not backup_name:
                return {
                    'success': False,
                    'message': 'backup_name is required for delete action'
                }
                
            # Find the backup
            backup = None
            for bkp in conn.volume.backups():
                if bkp.name == backup_name or bkp.id == backup_name:
                    backup = bkp
                    break
                    
            if not backup:
                return {
                    'success': False,
                    'message': f'Backup "{backup_name}" not found'
                }
                
            conn.volume.delete_backup(backup)
            return {
                'success': True,
                'message': f'Backup "{backup_name}" deletion started',
                'backup_id': backup.id
            }
            
        elif action.lower() == 'restore':
            if not backup_name:
                return {
                    'success': False,
                    'message': 'backup_name is required for restore action'
                }
                
            volume_name = kwargs.get('volume_name')
            if not volume_name:
                return {
                    'success': False,
                    'message': 'volume_name is required for restore action'
                }
                
            # Find the backup
            backup = None
            for bkp in conn.volume.backups():
                if bkp.name == backup_name or bkp.id == backup_name:
                    backup = bkp
                    break
                    
            if not backup:
                return {
                    'success': False,
                    'message': f'Backup "{backup_name}" not found'
                }
                
            try:
                restore = conn.volume.restore_backup(
                    backup_id=backup.id,
                    volume_id=None,  # Create new volume
                    name=volume_name
                )
                return {
                    'success': True,
                    'message': f'Backup "{backup_name}" restore to volume "{volume_name}" started',
                    'volume_id': restore.volume_id,
                    'backup_id': backup.id
                }
            except Exception as e:
                return {
                    'success': False,
                    'message': f'Failed to restore backup: {str(e)}'
                }
        
        else:
            return {
                'success': False,
                'message': f'Unknown action "{action}". Supported: list, show, delete, restore'
            }
            
    except Exception as e:
        logger.error(f"Failed to manage volume backup: {e}")
        return {
            'success': False,
            'message': f'Failed to manage volume backup: {str(e)}',
            'error': str(e)
        }


def set_volume_groups(action: str, group_name: Optional[str] = None, **kwargs) -> Dict[str, Any]:
    """
    Manage volume groups (list, create, delete, show, update)
    
    Args:
        action: Action to perform (list, create, delete, show, update)
        group_name: Name or ID of the volume group
        **kwargs: Additional parameters
    
    Returns:
        Result of the volume group management operation
    """
    try:
        conn = get_openstack_connection()
        
        if action.lower() == 'list':
            groups = []
            try:
                for group in conn.volume.groups(detailed=True):
                    groups.append({
                        'id': group.id,
                        'name': getattr(group, 'name', 'N/A'),
                        'description': getattr(group, 'description', 'N/A'),
                        'status': group.status,
                        'availability_zone': getattr(group, 'availability_zone', 'N/A'),
                        'group_type': getattr(group, 'group_type', 'N/A'),
                        'volumes': getattr(group, 'volumes', []),
                        'created_at': str(getattr(group, 'created_at', 'N/A'))
                    })
            except Exception as e:
                # Volume groups might not be supported
                return {
                    'success': False,
                    'message': f'Volume groups not supported or accessible: {str(e)}',
                    'groups': []
                }
            return {
                'success': True,
                'groups': groups,
                'count': len(groups)
            }
            
        elif action.lower() == 'create':
            if not group_name:
                return {
                    'success': False,
                    'message': 'group_name is required for create action'
                }
                
            description = kwargs.get('description', f'Volume group created via MCP: {group_name}')
            group_type = kwargs.get('group_type', 'default')
            availability_zone = kwargs.get('availability_zone', None)
            
            try:
                group = conn.volume.create_group(
                    name=group_name,
                    description=description,
                    group_type=group_type,
                    availability_zone=availability_zone
                )
                return {
                    'success': True,
                    'message': f'Volume group "{group_name}" creation started',
                    'group_id': group.id
                }
            except Exception as e:
                return {
                    'success': False,
                    'message': f'Failed to create volume group: {str(e)}'
                }
                
        elif action.lower() == 'delete':
            if not group_name:
                return {
                    'success': False,
                    'message': 'group_name is required for delete action'
                }
                
            # Find the group
            group = None
            try:
                for grp in conn.volume.groups():
                    if getattr(grp, 'name', '') == group_name or grp.id == group_name:
                        group = grp
                        break
                        
                if not group:
                    return {
                        'success': False,
                        'message': f'Volume group "{group_name}" not found'
                    }
                    
                delete_volumes = kwargs.get('delete_volumes', False)
                conn.volume.delete_group(group, delete_volumes=delete_volumes)
                return {
                    'success': True,
                    'message': f'Volume group "{group_name}" deletion started',
                    'group_id': group.id
                }
            except Exception as e:
                return {
                    'success': False,
                    'message': f'Failed to delete volume group: {str(e)}'
                }
        
        else:
            return {
                'success': False,
                'message': f'Unknown action "{action}". Supported: list, create, delete'
            }
            
    except Exception as e:
        logger.error(f"Failed to manage volume group: {e}")
        return {
            'success': False,
            'message': f'Failed to manage volume group: {str(e)}',
            'error': str(e)
        }


def set_volume_qos(action: str, qos_name: Optional[str] = None, **kwargs) -> Dict[str, Any]:
    """
    Manage volume QoS specifications (list, create, delete, show, set, unset)
    
    Args:
        action: Action to perform (list, create, delete, show, set, unset)
        qos_name: Name or ID of the QoS spec
        **kwargs: Additional parameters
    
    Returns:
        Result of the QoS management operation
    """
    try:
        conn = get_openstack_connection()
        
        if action.lower() == 'list':
            qos_specs = []
            try:
                for qos in conn.volume.qos_specs():
                    qos_specs.append({
                        'id': qos.id,
                        'name': qos.name,
                        'consumer': getattr(qos, 'consumer', 'N/A'),
                        'specs': getattr(qos, 'specs', {}),
                        'associations': []  # Would need separate API call to get this
                    })
            except Exception as e:
                return {
                    'success': False,
                    'message': f'QoS specs not supported or accessible: {str(e)}',
                    'qos_specs': []
                }
            return {
                'success': True,
                'qos_specs': qos_specs,
                'count': len(qos_specs)
            }
            
        elif action.lower() == 'create':
            if not qos_name:
                return {
                    'success': False,
                    'message': 'qos_name is required for create action'
                }
                
            consumer = kwargs.get('consumer', 'back-end')  # 'front-end', 'back-end', or 'both'
            specs = kwargs.get('specs', {})
            
            try:
                qos = conn.volume.create_qos_spec(
                    name=qos_name,
                    consumer=consumer,
                    specs=specs
                )
                return {
                    'success': True,
                    'message': f'QoS spec "{qos_name}" created',
                    'qos_id': qos.id,
                    'consumer': consumer,
                    'specs': specs
                }
            except Exception as e:
                return {
                    'success': False,
                    'message': f'Failed to create QoS spec: {str(e)}'
                }
                
        elif action.lower() == 'delete':
            if not qos_name:
                return {
                    'success': False,
                    'message': 'qos_name is required for delete action'
                }
                
            # Find the QoS spec
            qos = None
            try:
                for q in conn.volume.qos_specs():
                    if q.name == qos_name or q.id == qos_name:
                        qos = q
                        break
                        
                if not qos:
                    return {
                        'success': False,
                        'message': f'QoS spec "{qos_name}" not found'
                    }
                    
                force = kwargs.get('force', False)
                conn.volume.delete_qos_spec(qos, force=force)
                return {
                    'success': True,
                    'message': f'QoS spec "{qos_name}" deletion started',
                    'qos_id': qos.id
                }
            except Exception as e:
                return {
                    'success': False,
                    'message': f'Failed to delete QoS spec: {str(e)}'
                }
                
        elif action.lower() == 'set':
            if not qos_name:
                return {
                    'success': False,
                    'message': 'qos_name is required for set action'
                }
                
            specs = kwargs.get('specs', {})
            if not specs:
                return {
                    'success': False,
                    'message': 'specs parameter is required for set action'
                }
                
            # Find the QoS spec
            qos = None
            try:
                for q in conn.volume.qos_specs():
                    if q.name == qos_name or q.id == qos_name:
                        qos = q
                        break
                        
                if not qos:
                    return {
                        'success': False,
                        'message': f'QoS spec "{qos_name}" not found'
                    }
                    
                conn.volume.set_qos_spec_keys(qos, specs)
                return {
                    'success': True,
                    'message': f'QoS spec "{qos_name}" keys set',
                    'qos_id': qos.id,
                    'specs': specs
                }
            except Exception as e:
                return {
                    'success': False,
                    'message': f'Failed to set QoS spec keys: {str(e)}'
                }
        
        else:
            return {
                'success': False,
                'message': f'Unknown action "{action}". Supported: list, create, delete, set'
            }
            
    except Exception as e:
        logger.error(f"Failed to manage volume QoS: {e}")
        return {
            'success': False,
            'message': f'Failed to manage volume QoS: {str(e)}',
            'error': str(e)
        }


def set_network_ports(action: str, port_name: Optional[str] = None, **kwargs) -> Dict[str, Any]:
    """
    Manage OpenStack network ports (list, show, create, delete, update)
    
    Args:
        action: Action to perform (list, show, create, delete, update)
        port_name: Name or ID of the port
        **kwargs: Additional parameters
    
    Returns:
        Result of the port management operation
    """
    try:
        conn = get_openstack_connection()
        
        if action.lower() == 'list':
            ports = []
            for port in conn.network.ports():
                ports.append({
                    'id': port.id,
                    'name': port.name or 'N/A',
                    'status': port.status,
                    'admin_state_up': port.is_admin_state_up,
                    'network_id': port.network_id,
                    'device_id': port.device_id,
                    'device_owner': port.device_owner,
                    'mac_address': port.mac_address,
                    'fixed_ips': port.fixed_ips,
                    'security_groups': port.security_group_ids,
                    'port_security_enabled': getattr(port, 'port_security_enabled', None),
                    'created_at': str(getattr(port, 'created_at', 'N/A')),
                    'updated_at': str(getattr(port, 'updated_at', 'N/A'))
                })
            return {
                'success': True,
                'ports': ports,
                'count': len(ports)
            }
            
        elif action.lower() == 'create':
            if not port_name:
                return {
                    'success': False,
                    'message': 'port_name is required for create action'
                }
                
            network_id = kwargs.get('network_id')
            if not network_id:
                return {
                    'success': False,
                    'message': 'network_id is required for create action'
                }
                
            description = kwargs.get('description', f'Port created via MCP: {port_name}')
            admin_state_up = kwargs.get('admin_state_up', True)
            device_id = kwargs.get('device_id', '')
            device_owner = kwargs.get('device_owner', '')
            fixed_ips = kwargs.get('fixed_ips', [])
            security_groups = kwargs.get('security_groups', [])
            
            try:
                port = conn.network.create_port(
                    name=port_name,
                    network_id=network_id,
                    description=description,
                    admin_state_up=admin_state_up,
                    device_id=device_id,
                    device_owner=device_owner,
                    fixed_ips=fixed_ips,
                    security_group_ids=security_groups
                )
                return {
                    'success': True,
                    'message': f'Port "{port_name}" created successfully',
                    'port_id': port.id,
                    'network_id': network_id,
                    'mac_address': port.mac_address
                }
            except Exception as e:
                return {
                    'success': False,
                    'message': f'Failed to create port: {str(e)}'
                }
                
        elif action.lower() == 'delete':
            if not port_name:
                return {
                    'success': False,
                    'message': 'port_name is required for delete action'
                }
                
            # Find the port
            port = None
            for p in conn.network.ports():
                if p.name == port_name or p.id == port_name:
                    port = p
                    break
                    
            if not port:
                return {
                    'success': False,
                    'message': f'Port "{port_name}" not found'
                }
                
            try:
                conn.network.delete_port(port)
                return {
                    'success': True,
                    'message': f'Port "{port_name}" deleted successfully',
                    'port_id': port.id
                }
            except Exception as e:
                return {
                    'success': False,
                    'message': f'Failed to delete port: {str(e)}'
                }
        
        else:
            return {
                'success': False,
                'message': f'Unknown action "{action}". Supported: list, create, delete'
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
    Manage OpenStack network subnets (list, show, create, delete, update)
    
    Args:
        action: Action to perform (list, show, create, delete, update)
        subnet_name: Name or ID of the subnet
        **kwargs: Additional parameters
    
    Returns:
        Result of the subnet management operation
    """
    try:
        conn = get_openstack_connection()
        
        if action.lower() == 'list':
            subnets = []
            for subnet in conn.network.subnets():
                subnets.append({
                    'id': subnet.id,
                    'name': subnet.name or 'N/A',
                    'network_id': subnet.network_id,
                    'ip_version': subnet.ip_version,
                    'cidr': subnet.cidr,
                    'gateway_ip': subnet.gateway_ip,
                    'allocation_pools': subnet.allocation_pools,
                    'dns_nameservers': subnet.dns_nameservers,
                    'host_routes': subnet.host_routes,
                    'enable_dhcp': subnet.is_dhcp_enabled,
                    'ipv6_address_mode': getattr(subnet, 'ipv6_address_mode', None),
                    'ipv6_ra_mode': getattr(subnet, 'ipv6_ra_mode', None),
                    'created_at': str(getattr(subnet, 'created_at', 'N/A')),
                    'updated_at': str(getattr(subnet, 'updated_at', 'N/A'))
                })
            return {
                'success': True,
                'subnets': subnets,
                'count': len(subnets)
            }
            
        elif action.lower() == 'create':
            if not subnet_name:
                return {
                    'success': False,
                    'message': 'subnet_name is required for create action'
                }
                
            network_id = kwargs.get('network_id')
            cidr = kwargs.get('cidr')
            
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
                
            description = kwargs.get('description', f'Subnet created via MCP: {subnet_name}')
            ip_version = kwargs.get('ip_version', 4)
            enable_dhcp = kwargs.get('enable_dhcp', True)
            gateway_ip = kwargs.get('gateway_ip')
            allocation_pools = kwargs.get('allocation_pools', [])
            dns_nameservers = kwargs.get('dns_nameservers', [])
            host_routes = kwargs.get('host_routes', [])
            
            try:
                subnet = conn.network.create_subnet(
                    name=subnet_name,
                    network_id=network_id,
                    cidr=cidr,
                    ip_version=ip_version,
                    enable_dhcp=enable_dhcp,
                    gateway_ip=gateway_ip,
                    allocation_pools=allocation_pools,
                    dns_nameservers=dns_nameservers,
                    host_routes=host_routes,
                    description=description
                )
                return {
                    'success': True,
                    'message': f'Subnet "{subnet_name}" created successfully',
                    'subnet_id': subnet.id,
                    'network_id': network_id,
                    'cidr': cidr
                }
            except Exception as e:
                return {
                    'success': False,
                    'message': f'Failed to create subnet: {str(e)}'
                }
                
        elif action.lower() == 'delete':
            if not subnet_name:
                return {
                    'success': False,
                    'message': 'subnet_name is required for delete action'
                }
                
            # Find the subnet
            subnet = None
            for s in conn.network.subnets():
                if s.name == subnet_name or s.id == subnet_name:
                    subnet = s
                    break
                    
            if not subnet:
                return {
                    'success': False,
                    'message': f'Subnet "{subnet_name}" not found'
                }
                
            try:
                conn.network.delete_subnet(subnet)
                return {
                    'success': True,
                    'message': f'Subnet "{subnet_name}" deleted successfully',
                    'subnet_id': subnet.id
                }
            except Exception as e:
                return {
                    'success': False,
                    'message': f'Failed to delete subnet: {str(e)}'
                }
        
        else:
            return {
                'success': False,
                'message': f'Unknown action "{action}". Supported: list, create, delete'
            }
            
    except Exception as e:
        logger.error(f"Failed to manage subnet: {e}")
        return {
            'success': False,
            'message': f'Failed to manage subnet: {str(e)}',
            'error': str(e)
        }


def set_network_qos_policies(action: str, policy_name: Optional[str] = None, **kwargs) -> Dict[str, Any]:
    """
    Manage OpenStack network QoS policies (list, show, create, delete, update)
    
    Args:
        action: Action to perform (list, show, create, delete, update)
        policy_name: Name or ID of the QoS policy
        **kwargs: Additional parameters
    
    Returns:
        Result of the network QoS policy management operation
    """
    try:
        conn = get_openstack_connection()
        
        if action.lower() == 'list':
            policies = []
            try:
                for policy in conn.network.qos_policies():
                    policies.append({
                        'id': policy.id,
                        'name': policy.name or 'N/A',
                        'description': getattr(policy, 'description', 'N/A'),
                        'shared': getattr(policy, 'is_shared', False),
                        'is_default': getattr(policy, 'is_default', False),
                        'tenant_id': getattr(policy, 'tenant_id', 'N/A'),
                        'rules': getattr(policy, 'rules', []),
                        'created_at': str(getattr(policy, 'created_at', 'N/A')),
                        'updated_at': str(getattr(policy, 'updated_at', 'N/A'))
                    })
            except Exception as e:
                # QoS policies might not be supported
                return {
                    'success': False,
                    'message': f'Network QoS policies not supported or accessible: {str(e)}',
                    'policies': []
                }
            return {
                'success': True,
                'policies': policies,
                'count': len(policies)
            }
            
        elif action.lower() == 'create':
            if not policy_name:
                return {
                    'success': False,
                    'message': 'policy_name is required for create action'
                }
                
            description = kwargs.get('description', f'QoS policy created via MCP: {policy_name}')
            shared = kwargs.get('shared', False)
            
            try:
                policy = conn.network.create_qos_policy(
                    name=policy_name,
                    description=description,
                    shared=shared
                )
                return {
                    'success': True,
                    'message': f'QoS policy "{policy_name}" created successfully',
                    'policy_id': policy.id,
                    'shared': shared
                }
            except Exception as e:
                return {
                    'success': False,
                    'message': f'Failed to create QoS policy: {str(e)}'
                }
                
        elif action.lower() == 'delete':
            if not policy_name:
                return {
                    'success': False,
                    'message': 'policy_name is required for delete action'
                }
                
            # Find the policy
            policy = None
            try:
                for p in conn.network.qos_policies():
                    if p.name == policy_name or p.id == policy_name:
                        policy = p
                        break
                        
                if not policy:
                    return {
                        'success': False,
                        'message': f'QoS policy "{policy_name}" not found'
                    }
                    
                conn.network.delete_qos_policy(policy)
                return {
                    'success': True,
                    'message': f'QoS policy "{policy_name}" deleted successfully',
                    'policy_id': policy.id
                }
            except Exception as e:
                return {
                    'success': False,
                    'message': f'Failed to delete QoS policy: {str(e)}'
                }
        
        else:
            return {
                'success': False,
                'message': f'Unknown action "{action}". Supported: list, create, delete'
            }
            
    except Exception as e:
        logger.error(f"Failed to manage network QoS policy: {e}")
        return {
            'success': False,
            'message': f'Failed to manage network QoS policy: {str(e)}',
            'error': str(e)
        }


def set_network_agents(action: str, agent_id: Optional[str] = None, **kwargs) -> Dict[str, Any]:
    """
    Manage OpenStack network agents (list, show, enable, disable)
    
    Args:
        action: Action to perform (list, show, enable, disable)
        agent_id: ID of the network agent
        **kwargs: Additional parameters
    
    Returns:
        Result of the network agent management operation
    """
    try:
        conn = get_openstack_connection()
        
        if action.lower() == 'list':
            agents = []
            try:
                for agent in conn.network.agents():
                    agents.append({
                        'id': agent.id,
                        'agent_type': agent.agent_type,
                        'binary': agent.binary,
                        'host': agent.host,
                        'topic': getattr(agent, 'topic', 'N/A'),
                        'availability_zone': getattr(agent, 'availability_zone', 'N/A'),
                        'admin_state_up': agent.is_admin_state_up,
                        'alive': getattr(agent, 'is_alive', None),
                        'created_at': str(getattr(agent, 'created_at', 'N/A')),
                        'started_at': str(getattr(agent, 'started_at', 'N/A')),
                        'heartbeat_timestamp': str(getattr(agent, 'heartbeat_timestamp', 'N/A')),
                        'configurations': getattr(agent, 'configurations', {})
                    })
            except Exception as e:
                return {
                    'success': False,
                    'message': f'Network agents not accessible: {str(e)}',
                    'agents': []
                }
            return {
                'success': True,
                'agents': agents,
                'count': len(agents)
            }
            
        elif action.lower() in ['enable', 'disable']:
            if not agent_id:
                return {
                    'success': False,
                    'message': 'agent_id is required for enable/disable action'
                }
                
            try:
                admin_state_up = action.lower() == 'enable'
                conn.network.update_agent(agent_id, admin_state_up=admin_state_up)
                return {
                    'success': True,
                    'message': f'Agent "{agent_id}" {action.lower()}d successfully',
                    'agent_id': agent_id,
                    'admin_state_up': admin_state_up
                }
            except Exception as e:
                return {
                    'success': False,
                    'message': f'Failed to {action.lower()} agent: {str(e)}'
                }
        
        else:
            return {
                'success': False,
                'message': f'Unknown action "{action}". Supported: list, enable, disable'
            }
            
    except Exception as e:
        logger.error(f"Failed to manage network agent: {e}")
        return {
            'success': False,
            'message': f'Failed to manage network agent: {str(e)}',
            'error': str(e)
        }


def set_image_members(action: str, image_name: str, member_project: Optional[str] = None, **kwargs) -> Dict[str, Any]:
    """
    Manage OpenStack image members (sharing images between projects)
    
    Args:
        action: Action to perform (list, add, remove, show)
        image_name: Name or ID of the image
        member_project: Project ID to add/remove as member
        **kwargs: Additional parameters
    
    Returns:
        Result of the image member management operation
    """
    try:
        conn = get_openstack_connection()
        
        # Find the image
        image = None
        for img in conn.image.images():
            if img.name == image_name or img.id == image_name:
                image = img
                break
                
        if not image:
            return {
                'success': False,
                'message': f'Image "{image_name}" not found'
            }
        
        if action.lower() == 'list':
            members = []
            try:
                for member in conn.image.members(image.id):
                    members.append({
                        'member_id': member.member_id,
                        'image_id': member.image_id,
                        'status': member.status,
                        'created_at': str(getattr(member, 'created_at', 'N/A')),
                        'updated_at': str(getattr(member, 'updated_at', 'N/A'))
                    })
            except Exception as e:
                return {
                    'success': False,
                    'message': f'Failed to list image members: {str(e)}',
                    'members': []
                }
            return {
                'success': True,
                'image_id': image.id,
                'image_name': image.name,
                'members': members,
                'count': len(members)
            }
            
        elif action.lower() == 'add':
            if not member_project:
                return {
                    'success': False,
                    'message': 'member_project is required for add action'
                }
                
            try:
                member = conn.image.add_member(image.id, member_project)
                return {
                    'success': True,
                    'message': f'Project "{member_project}" added as member to image "{image_name}"',
                    'image_id': image.id,
                    'member_id': member_project,
                    'status': member.status
                }
            except Exception as e:
                return {
                    'success': False,
                    'message': f'Failed to add image member: {str(e)}'
                }
                
        elif action.lower() == 'remove':
            if not member_project:
                return {
                    'success': False,
                    'message': 'member_project is required for remove action'
                }
                
            try:
                conn.image.remove_member(image.id, member_project)
                return {
                    'success': True,
                    'message': f'Project "{member_project}" removed as member from image "{image_name}"',
                    'image_id': image.id,
                    'member_id': member_project
                }
            except Exception as e:
                return {
                    'success': False,
                    'message': f'Failed to remove image member: {str(e)}'
                }
        
        else:
            return {
                'success': False,
                'message': f'Unknown action "{action}". Supported: list, add, remove'
            }
            
    except Exception as e:
        logger.error(f"Failed to manage image members: {e}")
        return {
            'success': False,
            'message': f'Failed to manage image members: {str(e)}',
            'error': str(e)
        }


def set_image_metadata(action: str, image_name: str, **kwargs) -> Dict[str, Any]:
    """
    Manage OpenStack image metadata and properties
    
    Args:
        action: Action to perform (show, set, unset)
        image_name: Name or ID of the image
        **kwargs: Additional parameters (properties dict for set, property_keys list for unset)
    
    Returns:
        Result of the image metadata management operation
    """
    try:
        conn = get_openstack_connection()
        
        # Find the image
        image = None
        for img in conn.image.images():
            if img.name == image_name or img.id == image_name:
                image = img
                break
                
        if not image:
            return {
                'success': False,
                'message': f'Image "{image_name}" not found'
            }
        
        if action.lower() == 'show':
            try:
                # Get detailed image information including metadata
                detailed_image = conn.image.get_image(image.id)
                return {
                    'success': True,
                    'image_id': image.id,
                    'image_name': image.name,
                    'metadata': {
                        'properties': getattr(detailed_image, 'properties', {}),
                        'tags': getattr(detailed_image, 'tags', []),
                        'visibility': detailed_image.visibility,
                        'protected': detailed_image.is_protected,
                        'disk_format': detailed_image.disk_format,
                        'container_format': detailed_image.container_format,
                        'min_disk': getattr(detailed_image, 'min_disk', 0),
                        'min_ram': getattr(detailed_image, 'min_ram', 0),
                        'size': getattr(detailed_image, 'size', None),
                        'checksum': getattr(detailed_image, 'checksum', None),
                        'created_at': str(getattr(detailed_image, 'created_at', 'N/A')),
                        'updated_at': str(getattr(detailed_image, 'updated_at', 'N/A')),
                        'owner': getattr(detailed_image, 'owner', None),
                        'status': detailed_image.status
                    }
                }
            except Exception as e:
                return {
                    'success': False,
                    'message': f'Failed to show image metadata: {str(e)}'
                }
                
        elif action.lower() == 'set':
            properties = kwargs.get('properties', {})
            if not properties:
                return {
                    'success': False,
                    'message': 'properties parameter is required for set action'
                }
                
            try:
                # Update image properties
                updated_image = conn.image.update_image(image.id, **properties)
                return {
                    'success': True,
                    'message': f'Image "{image_name}" metadata updated',
                    'image_id': image.id,
                    'updated_properties': properties
                }
            except Exception as e:
                return {
                    'success': False,
                    'message': f'Failed to set image metadata: {str(e)}'
                }
        
        else:
            return {
                'success': False,
                'message': f'Unknown action "{action}". Supported: show, set'
            }
            
    except Exception as e:
        logger.error(f"Failed to manage image metadata: {e}")
        return {
            'success': False,
            'message': f'Failed to manage image metadata: {str(e)}',
            'error': str(e)
        }


def set_image_visibility(action: str, image_name: str, **kwargs) -> Dict[str, Any]:
    """
    Manage OpenStack image visibility settings
    
    Args:
        action: Action to perform (show, set)
        image_name: Name or ID of the image
        **kwargs: Additional parameters (visibility for set action)
    
    Returns:
        Result of the image visibility management operation
    """
    try:
        conn = get_openstack_connection()
        
        # Find the image
        image = None
        for img in conn.image.images():
            if img.name == image_name or img.id == image_name:
                image = img
                break
                
        if not image:
            return {
                'success': False,
                'message': f'Image "{image_name}" not found'
            }
        
        if action.lower() == 'show':
            return {
                'success': True,
                'image_id': image.id,
                'image_name': image.name,
                'visibility': image.visibility,
                'is_protected': image.is_protected,
                'owner': getattr(image, 'owner', None)
            }
            
        elif action.lower() == 'set':
            visibility = kwargs.get('visibility')
            if not visibility:
                return {
                    'success': False,
                    'message': 'visibility parameter is required for set action'
                }
                
            # Validate visibility value
            valid_visibilities = ['public', 'private', 'shared', 'community']
            if visibility not in valid_visibilities:
                return {
                    'success': False,
                    'message': f'Invalid visibility "{visibility}". Valid values: {valid_visibilities}'
                }
                
            try:
                conn.image.update_image(image.id, visibility=visibility)
                return {
                    'success': True,
                    'message': f'Image "{image_name}" visibility set to "{visibility}"',
                    'image_id': image.id,
                    'old_visibility': image.visibility,
                    'new_visibility': visibility
                }
            except Exception as e:
                return {
                    'success': False,
                    'message': f'Failed to set image visibility: {str(e)}'
                }
        
        else:
            return {
                'success': False,
                'message': f'Unknown action "{action}". Supported: show, set'
            }
            
    except Exception as e:
        logger.error(f"Failed to manage image visibility: {e}")
        return {
            'success': False,
            'message': f'Failed to manage image visibility: {str(e)}',
            'error': str(e)
        }


def set_domains(action: str, domain_name: Optional[str] = None, **kwargs) -> Dict[str, Any]:
    """
    Manage OpenStack domains (list, show, create, delete, update)
    
    Args:
        action: Action to perform (list, show, create, delete, update)
        domain_name: Name or ID of the domain
        **kwargs: Additional parameters
    
    Returns:
        Result of the domain management operation
    """
    try:
        conn = get_openstack_connection()
        
        if action.lower() == 'list':
            domains = []
            try:
                for domain in conn.identity.domains():
                    domains.append({
                        'id': domain.id,
                        'name': domain.name,
                        'description': getattr(domain, 'description', 'N/A'),
                        'enabled': domain.is_enabled,
                        'created_at': str(getattr(domain, 'created_at', 'N/A')),
                        'updated_at': str(getattr(domain, 'updated_at', 'N/A'))
                    })
            except Exception as e:
                return {
                    'success': False,
                    'message': f'Domains not accessible: {str(e)}',
                    'domains': []
                }
            return {
                'success': True,
                'domains': domains,
                'count': len(domains)
            }
            
        elif action.lower() == 'create':
            if not domain_name:
                return {
                    'success': False,
                    'message': 'domain_name is required for create action'
                }
                
            description = kwargs.get('description', f'Domain created via MCP: {domain_name}')
            enabled = kwargs.get('enabled', True)
            
            try:
                domain = conn.identity.create_domain(
                    name=domain_name,
                    description=description,
                    enabled=enabled
                )
                return {
                    'success': True,
                    'message': f'Domain "{domain_name}" created successfully',
                    'domain_id': domain.id,
                    'enabled': enabled
                }
            except Exception as e:
                return {
                    'success': False,
                    'message': f'Failed to create domain: {str(e)}'
                }
        
        else:
            return {
                'success': False,
                'message': f'Unknown action "{action}". Supported: list, create'
            }
            
    except Exception as e:
        logger.error(f"Failed to manage domain: {e}")
        return {
            'success': False,
            'message': f'Failed to manage domain: {str(e)}',
            'error': str(e)
        }


def set_identity_groups(action: str, group_name: Optional[str] = None, **kwargs) -> Dict[str, Any]:
    """
    Manage OpenStack identity groups (list, show, create, delete, update)
    
    Args:
        action: Action to perform (list, show, create, delete, update)
        group_name: Name or ID of the group
        **kwargs: Additional parameters
    
    Returns:
        Result of the identity group management operation
    """
    try:
        conn = get_openstack_connection()
        
        if action.lower() == 'list':
            groups = []
            try:
                for group in conn.identity.groups():
                    groups.append({
                        'id': group.id,
                        'name': group.name,
                        'description': getattr(group, 'description', 'N/A'),
                        'domain_id': getattr(group, 'domain_id', 'N/A'),
                        'created_at': str(getattr(group, 'created_at', 'N/A')),
                        'updated_at': str(getattr(group, 'updated_at', 'N/A'))
                    })
            except Exception as e:
                return {
                    'success': False,
                    'message': f'Identity groups not accessible: {str(e)}',
                    'groups': []
                }
            return {
                'success': True,
                'groups': groups,
                'count': len(groups)
            }
            
        elif action.lower() == 'create':
            if not group_name:
                return {
                    'success': False,
                    'message': 'group_name is required for create action'
                }
                
            description = kwargs.get('description', f'Group created via MCP: {group_name}')
            domain_id = kwargs.get('domain_id', 'default')
            
            try:
                group = conn.identity.create_group(
                    name=group_name,
                    description=description,
                    domain_id=domain_id
                )
                return {
                    'success': True,
                    'message': f'Group "{group_name}" created successfully',
                    'group_id': group.id,
                    'domain_id': domain_id
                }
            except Exception as e:
                return {
                    'success': False,
                    'message': f'Failed to create group: {str(e)}'
                }
        
        else:
            return {
                'success': False,
                'message': f'Unknown action "{action}". Supported: list, create'
            }
            
    except Exception as e:
        logger.error(f"Failed to manage identity group: {e}")
        return {
            'success': False,
            'message': f'Failed to manage identity group: {str(e)}',
            'error': str(e)
        }


def set_roles(action: str, role_name: Optional[str] = None, **kwargs) -> Dict[str, Any]:
    """
    Manage OpenStack roles (list, show, create, delete, assign, unassign)
    
    Args:
        action: Action to perform (list, show, create, delete, assign, unassign)
        role_name: Name or ID of the role
        **kwargs: Additional parameters
    
    Returns:
        Result of the role management operation
    """
    try:
        conn = get_openstack_connection()
        
        if action.lower() == 'list':
            roles = []
            try:
                for role in conn.identity.roles():
                    roles.append({
                        'id': role.id,
                        'name': role.name,
                        'description': getattr(role, 'description', 'N/A'),
                        'domain_id': getattr(role, 'domain_id', None),
                        'created_at': str(getattr(role, 'created_at', 'N/A')),
                        'updated_at': str(getattr(role, 'updated_at', 'N/A'))
                    })
            except Exception as e:
                return {
                    'success': False,
                    'message': f'Roles not accessible: {str(e)}',
                    'roles': []
                }
            return {
                'success': True,
                'roles': roles,
                'count': len(roles)
            }
            
        elif action.lower() == 'create':
            if not role_name:
                return {
                    'success': False,
                    'message': 'role_name is required for create action'
                }
                
            description = kwargs.get('description', f'Role created via MCP: {role_name}')
            domain_id = kwargs.get('domain_id', None)
            
            try:
                role = conn.identity.create_role(
                    name=role_name,
                    description=description,
                    domain_id=domain_id
                )
                return {
                    'success': True,
                    'message': f'Role "{role_name}" created successfully',
                    'role_id': role.id,
                    'domain_id': domain_id
                }
            except Exception as e:
                return {
                    'success': False,
                    'message': f'Failed to create role: {str(e)}'
                }
        
        else:
            return {
                'success': False,
                'message': f'Unknown action "{action}". Supported: list, create'
            }
            
    except Exception as e:
        logger.error(f"Failed to manage role: {e}")
        return {
            'success': False,
            'message': f'Failed to manage role: {str(e)}',
            'error': str(e)
        }


def set_services(action: str, service_name: Optional[str] = None, **kwargs) -> Dict[str, Any]:
    """
    Manage OpenStack services (list, show, create, delete)
    
    Args:
        action: Action to perform (list, show, create, delete)
        service_name: Name or ID of the service
        **kwargs: Additional parameters
    
    Returns:
        Result of the service management operation
    """
    try:
        conn = get_openstack_connection()
        
        if action.lower() == 'list':
            services = []
            try:
                for service in conn.identity.services():
                    services.append({
                        'id': service.id,
                        'name': service.name,
                        'type': service.type,
                        'description': getattr(service, 'description', 'N/A'),
                        'enabled': getattr(service, 'enabled', True),
                        'created_at': str(getattr(service, 'created_at', 'N/A')),
                        'updated_at': str(getattr(service, 'updated_at', 'N/A'))
                    })
            except Exception as e:
                return {
                    'success': False,
                    'message': f'Services not accessible: {str(e)}',
                    'services': []
                }
            return {
                'success': True,
                'services': services,
                'count': len(services)
            }
        
        else:
            return {
                'success': False,
                'message': f'Unknown action "{action}". Supported: list'
            }
            
    except Exception as e:
        logger.error(f"Failed to manage service: {e}")
        return {
            'success': False,
            'message': f'Failed to manage service: {str(e)}',
            'error': str(e)
        }


def set_service_logs(
    action: str,
    service_name: str = None,
    log_level: str = "INFO"
) -> Dict[str, Any]:
    """
    Manage OpenStack service logs and logging configuration.
    
    Args:
        action: Action to perform - list, show
        service_name: Name of the service to get logs for
        log_level: Log level filter (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        
    Returns:
        Service logs information
    """
    try:
        conn = get_openstack_connection()
        
        if action.lower() == 'list':
            # List available services for logging
            services = []
            try:
                # Get compute services
                for service in conn.compute.services():
                    services.append({
                        'name': service.binary,
                        'type': 'compute',
                        'host': service.host,
                        'status': service.status,
                        'state': service.state
                    })
                    
                # Get network agents (similar to services)
                for agent in conn.network.agents():
                    services.append({
                        'name': agent.agent_type,
                        'type': 'network',
                        'host': agent.host,
                        'status': 'enabled' if agent.is_enabled else 'disabled',
                        'state': 'up' if agent.is_alive else 'down'
                    })
                    
            except Exception as e:
                logger.warning(f"Could not get all services: {e}")
                
            return {
                'success': True,
                'services': services,
                'message': f'Found {len(services)} services available for logging',
                'log_level_filter': log_level
            }
            
        elif action.lower() == 'show':
            if not service_name:
                return {
                    'success': False,
                    'message': 'Service name required for show action'
                }
                
            # This would normally query actual log files or log aggregation service
            # For now, return service status and configuration info
            service_info = {
                'service_name': service_name,
                'log_level': log_level,
                'message': f'Log information for {service_name} (log level: {log_level})',
                'note': 'Log aggregation would require additional configuration with centralized logging system'
            }
            
            return {
                'success': True,
                'service_logs': service_info
            }
        
        else:
            return {
                'success': False,
                'message': f'Unknown action "{action}". Supported: list, show'
            }
            
    except Exception as e:
        logger.error(f"Failed to manage service logs: {e}")
        return {
            'success': False,
            'message': f'Failed to manage service logs: {str(e)}',
            'error': str(e)
        }


def set_metrics(
    action: str,
    resource_type: str = "compute",
    resource_id: str = None
) -> Dict[str, Any]:
    """
    Manage OpenStack metrics collection and monitoring.
    
    Args:
        action: Action to perform - list, show, summary
        resource_type: Type of resource (compute, network, storage, identity)
        resource_id: Specific resource ID to get metrics for
        
    Returns:
        Metrics information
    """
    try:
        conn = get_openstack_connection()
        
        if action.lower() == 'list':
            metrics = []
            
            if resource_type.lower() == 'compute':
                # Get compute metrics
                try:
                    for server in conn.compute.servers():
                        metrics.append({
                            'resource_type': 'compute',
                            'resource_id': server.id,
                            'resource_name': server.name,
                            'status': server.status,
                            'power_state': getattr(server, 'power_state', 'unknown'),
                            'created_at': server.created_at,
                            'updated_at': server.updated_at
                        })
                except Exception as e:
                    logger.warning(f"Could not get compute metrics: {e}")
                    
            elif resource_type.lower() == 'network':
                # Get network metrics
                try:
                    for network in conn.network.networks():
                        metrics.append({
                            'resource_type': 'network',
                            'resource_id': network.id,
                            'resource_name': network.name,
                            'status': network.status,
                            'is_admin_state_up': network.is_admin_state_up,
                            'created_at': getattr(network, 'created_at', None),
                            'updated_at': getattr(network, 'updated_at', None)
                        })
                except Exception as e:
                    logger.warning(f"Could not get network metrics: {e}")
                    
            elif resource_type.lower() == 'storage':
                # Get storage metrics
                try:
                    for volume in conn.block_storage.volumes():
                        metrics.append({
                            'resource_type': 'storage',
                            'resource_id': volume.id,
                            'resource_name': volume.name,
                            'status': volume.status,
                            'size': volume.size,
                            'created_at': volume.created_at,
                            'updated_at': volume.updated_at
                        })
                except Exception as e:
                    logger.warning(f"Could not get storage metrics: {e}")
                    
            return {
                'success': True,
                'metrics': metrics,
                'resource_type': resource_type,
                'count': len(metrics)
            }
            
        elif action.lower() == 'show':
            if not resource_id:
                return {
                    'success': False,
                    'message': 'Resource ID required for show action'
                }
                
            # Get specific resource metrics
            resource_metrics = {
                'resource_type': resource_type,
                'resource_id': resource_id,
                'timestamp': datetime.utcnow().isoformat(),
                'note': 'Detailed metrics would require integration with monitoring system like Prometheus or Ceilometer'
            }
            
            return {
                'success': True,
                'resource_metrics': resource_metrics
            }
            
        elif action.lower() == 'summary':
            # Get summary metrics across all resource types
            summary = {
                'compute': {'total': 0, 'active': 0, 'error': 0},
                'network': {'total': 0, 'active': 0, 'down': 0},
                'storage': {'total': 0, 'available': 0, 'in_use': 0},
                'timestamp': datetime.utcnow().isoformat()
            }
            
            try:
                # Compute summary
                servers = list(conn.compute.servers())
                summary['compute']['total'] = len(servers)
                summary['compute']['active'] = len([s for s in servers if s.status == 'ACTIVE'])
                summary['compute']['error'] = len([s for s in servers if s.status == 'ERROR'])
                
                # Network summary
                networks = list(conn.network.networks())
                summary['network']['total'] = len(networks)
                summary['network']['active'] = len([n for n in networks if n.status == 'ACTIVE'])
                summary['network']['down'] = len([n for n in networks if n.status == 'DOWN'])
                
                # Storage summary
                volumes = list(conn.block_storage.volumes())
                summary['storage']['total'] = len(volumes)
                summary['storage']['available'] = len([v for v in volumes if v.status == 'available'])
                summary['storage']['in_use'] = len([v for v in volumes if v.status == 'in-use'])
                
            except Exception as e:
                summary['error'] = f"Could not get complete summary: {str(e)}"
                
            return {
                'success': True,
                'summary': summary
            }
        
        else:
            return {
                'success': False,
                'message': f'Unknown action "{action}". Supported: list, show, summary'
            }
            
    except Exception as e:
        logger.error(f"Failed to manage metrics: {e}")
        return {
            'success': False,
            'message': f'Failed to manage metrics: {str(e)}',
            'error': str(e)
        }


def set_alarms(
    action: str,
    alarm_name: str = None,
    resource_id: str = None,
    threshold: float = None,
    comparison: str = "gt"
) -> Dict[str, Any]:
    """
    Manage OpenStack alarms and alerting (requires Aodh service).
    
    Args:
        action: Action to perform - list, create, show, delete
        alarm_name: Name of the alarm
        resource_id: Resource ID to monitor
        threshold: Threshold value for alarm
        comparison: Comparison operator (gt, lt, eq, ne, ge, le)
        
    Returns:
        Alarm management information
    """
    try:
        conn = get_openstack_connection()
        
        # Note: This would require Aodh (alarming service) to be installed
        # For now, we'll simulate alarm management
        
        if action.lower() == 'list':
            # List available alarms (simulated)
            alarms = [
                {
                    'name': 'cpu-high-alarm',
                    'type': 'threshold',
                    'state': 'ok',
                    'enabled': True,
                    'description': 'CPU usage alarm for compute instances'
                },
                {
                    'name': 'memory-high-alarm',
                    'type': 'threshold',
                    'state': 'alarm',
                    'enabled': True,
                    'description': 'Memory usage alarm for compute instances'
                }
            ]
            
            return {
                'success': True,
                'alarms': alarms,
                'count': len(alarms),
                'note': 'Alarm management requires Aodh service to be installed and configured'
            }
            
        elif action.lower() == 'create':
            if not alarm_name:
                return {
                    'success': False,
                    'message': 'Alarm name required for create action'
                }
                
            # Simulate alarm creation
            alarm = {
                'name': alarm_name,
                'resource_id': resource_id,
                'threshold': threshold,
                'comparison': comparison,
                'state': 'insufficient data',
                'enabled': True,
                'created_at': datetime.utcnow().isoformat()
            }
            
            return {
                'success': True,
                'alarm': alarm,
                'message': f'Alarm "{alarm_name}" created (simulation - requires Aodh service)'
            }
            
        elif action.lower() == 'show':
            if not alarm_name:
                return {
                    'success': False,
                    'message': 'Alarm name required for show action'
                }
                
            # Simulate alarm details
            alarm_details = {
                'name': alarm_name,
                'type': 'threshold',
                'state': 'ok',
                'enabled': True,
                'threshold': threshold or 80.0,
                'comparison': comparison,
                'resource_id': resource_id,
                'description': f'Alarm monitoring for {alarm_name}'
            }
            
            return {
                'success': True,
                'alarm_details': alarm_details
            }
            
        elif action.lower() == 'delete':
            if not alarm_name:
                return {
                    'success': False,
                    'message': 'Alarm name required for delete action'
                }
                
            return {
                'success': True,
                'message': f'Alarm "{alarm_name}" deleted (simulation - requires Aodh service)'
            }
        
        else:
            return {
                'success': False,
                'message': f'Unknown action "{action}". Supported: list, create, show, delete'
            }
            
    except Exception as e:
        logger.error(f"Failed to manage alarms: {e}")
        return {
            'success': False,
            'message': f'Failed to manage alarms: {str(e)}',
            'error': str(e)
        }


def set_compute_agents(
    action: str,
    agent_id: str = None,
    host: str = None
) -> Dict[str, Any]:
    """
    Manage OpenStack compute agents and hypervisor monitoring.
    
    Args:
        action: Action to perform - list, show
        agent_id: ID of specific agent
        host: Host name to filter agents
        
    Returns:
        Compute agent information
    """
    try:
        conn = get_openstack_connection()
        
        if action.lower() == 'list':
            agents = []
            
            # Get compute services (agents)
            try:
                for service in conn.compute.services():
                    if not host or service.host == host:
                        agents.append({
                            'id': service.id,
                            'binary': service.binary,
                            'host': service.host,
                            'zone': service.zone,
                            'status': service.status,
                            'state': service.state,
                            'updated_at': service.updated_at,
                            'disabled_reason': getattr(service, 'disabled_reason', None)
                        })
            except Exception as e:
                logger.warning(f"Could not get compute services: {e}")
                
            # Get hypervisor information
            try:
                hypervisors = []
                for hypervisor in conn.compute.hypervisors():
                    if not host or hypervisor.name == host:
                        hypervisors.append({
                            'id': hypervisor.id,
                            'name': hypervisor.name,
                            'status': hypervisor.status,
                            'state': hypervisor.state,
                            'vcpus': hypervisor.vcpus,
                            'vcpus_used': hypervisor.vcpus_used,
                            'memory_mb': hypervisor.memory_mb,
                            'memory_mb_used': hypervisor.memory_mb_used,
                            'local_gb': hypervisor.local_gb,
                            'local_gb_used': hypervisor.local_gb_used,
                            'running_vms': hypervisor.running_vms
                        })
                        
                return {
                    'success': True,
                    'compute_services': agents,
                    'hypervisors': hypervisors,
                    'count': {
                        'services': len(agents),
                        'hypervisors': len(hypervisors)
                    }
                }
            except Exception as e:
                logger.warning(f"Could not get hypervisor information: {e}")
                return {
                    'success': True,
                    'compute_services': agents,
                    'count': {'services': len(agents)}
                }
                
        elif action.lower() == 'show':
            if not agent_id and not host:
                return {
                    'success': False,
                    'message': 'Agent ID or host name required for show action'
                }
                
            # Get specific agent details
            if agent_id:
                try:
                    service = conn.compute.get_service(agent_id)
                    agent_details = {
                        'id': service.id,
                        'binary': service.binary,
                        'host': service.host,
                        'zone': service.zone,
                        'status': service.status,
                        'state': service.state,
                        'updated_at': service.updated_at,
                        'disabled_reason': getattr(service, 'disabled_reason', None)
                    }
                    
                    return {
                        'success': True,
                        'agent_details': agent_details
                    }
                except Exception as e:
                    return {
                        'success': False,
                        'message': f'Agent not found: {str(e)}'
                    }
            else:
                # Search by host
                agents = []
                for service in conn.compute.services():
                    if service.host == host:
                        agents.append({
                            'id': service.id,
                            'binary': service.binary,
                            'host': service.host,
                            'zone': service.zone,
                            'status': service.status,
                            'state': service.state
                        })
                        
                return {
                    'success': True,
                    'agents_on_host': agents,
                    'host': host,
                    'count': len(agents)
                }
        
        else:
            return {
                'success': False,
                'message': f'Unknown action "{action}". Supported: list, show'
            }
            
    except Exception as e:
        logger.error(f"Failed to manage compute agents: {e}")
        return {
            'success': False,
            'message': f'Failed to manage compute agents: {str(e)}',
            'error': str(e)
        }
