"""
OpenStack Monitoring and Metrics Functions

This module contains functions for monitoring OpenStack resources,
getting usage statistics, quotas, and availability information.
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta

# Configure logging
logger = logging.getLogger(__name__)


def get_resource_monitoring() -> Dict[str, Any]:
    """
    Get comprehensive resource monitoring information for current project.
    
    Returns:
        Dict containing monitoring data for current project's compute, network, and storage resources
    """
    try:
        # Import here to avoid circular imports
        from ..connection import get_openstack_connection
        conn = get_openstack_connection()
        current_project_id = conn.current_project_id
        
        monitoring_data = {
            'timestamp': datetime.now().isoformat(),
            'project_id': current_project_id,
            'compute': {},
            'network': {},
            'storage': {},
            'identity': {}
        }
        
        # Compute monitoring - filter servers by project
        try:
            all_servers = list(conn.compute.servers())
            servers = [s for s in all_servers if getattr(s, 'project_id', None) == current_project_id]
            
            # Calculate actual compute usage from instances
            total_used_vcpus = 0
            total_used_ram_mb = 0
            total_used_disk_gb = 0
            running_servers = 0
            
            for server in servers:
                if server.status == 'ACTIVE':
                    running_servers += 1
                
                # Get resource usage from server's flavor
                flavor = server.flavor
                if flavor:
                    # Server flavor is already a flavor object with resource info
                    vcpus = getattr(flavor, 'vcpus', 0) or 0
                    ram_mb = getattr(flavor, 'ram', 0) or 0
                    disk_gb = getattr(flavor, 'disk', 0) or 0
                    ephemeral_gb = getattr(flavor, 'OS-FLV-EXT-DATA:ephemeral', 0) or 0
                    swap_gb = getattr(flavor, 'swap', 0) or 0
                    
                    # Convert swap from MB to GB if it's in MB (some OpenStack versions use MB)
                    if swap_gb > 100:  # Likely in MB
                        swap_gb = swap_gb / 1024
                    
                    total_instance_disk = disk_gb + ephemeral_gb + swap_gb
                    
                    total_used_vcpus += vcpus
                    total_used_ram_mb += ram_mb
                    total_used_disk_gb += total_instance_disk
            
            # Try to get hypervisor totals (physical capacity)
            total_physical_vcpus = 0
            total_physical_ram_mb = 0
            total_physical_disk_gb = 0
            hypervisor_count = 0
            
            try:
                hypervisors = list(conn.compute.hypervisors())
                hypervisor_count = len(hypervisors)
                
                # Since hypervisor detailed stats are not available in this environment,
                # try to get quota limits as a reasonable approximation of capacity
                try:
                    quota = conn.compute.get_quota_set(current_project_id)
                    # Use quota limits as approximate capacity indicators
                    if hasattr(quota, 'cores') and quota.cores and quota.cores > 0:
                        total_physical_vcpus = quota.cores
                    if hasattr(quota, 'ram') and quota.ram and quota.ram > 0:
                        total_physical_ram_mb = quota.ram
                        
                except Exception as quota_error:
                    logger.info(f"Could not get quota for capacity estimation: {quota_error}")
                
                # Alternative: Try to get aggregate/availability zone stats
                try:
                    # Some deployments provide compute service stats
                    services = list(conn.compute.services(binary='nova-compute'))
                    if services and hypervisor_count > 0:
                        # Rough estimation: assume each compute service represents similar capacity
                        # This is just a fallback when hypervisor stats aren't available
                        if total_physical_vcpus == 0:
                            # Very rough estimate: if we can't get real data, 
                            # assume some reasonable default per hypervisor
                            estimated_vcpus_per_hypervisor = max(total_used_vcpus * 2, 8)  # At least double usage or 8
                            total_physical_vcpus = estimated_vcpus_per_hypervisor * hypervisor_count
                            
                        if total_physical_ram_mb == 0:
                            estimated_ram_per_hypervisor = max(total_used_ram_mb * 2, 16384)  # At least double usage or 16GB
                            total_physical_ram_mb = estimated_ram_per_hypervisor * hypervisor_count
                            
                except Exception:
                    pass
                    
            except Exception:
                # If hypervisor access fails, we'll still show instance usage
                pass
            
            compute_stats = {
                'total_servers': len(servers),
                'running_servers': running_servers,
                'total_hypervisors': hypervisor_count,
                # Physical capacity (from hypervisors)
                'total_vcpus': total_physical_vcpus,
                'total_memory_mb': total_physical_ram_mb,
                'total_disk_gb': total_physical_disk_gb,
                # Usage (from instances)
                'used_vcpus': total_used_vcpus,
                'used_memory_mb': total_used_ram_mb,
                'used_disk_gb': total_used_disk_gb,  # Calculated from instance flavors
                'project_server_count': len(servers)
            }
            
            monitoring_data['compute'] = compute_stats
        except Exception as e:
            monitoring_data['compute'] = {'error': str(e)}
            logger.warning(f"Failed to get compute monitoring data: {e}")
        
        # Network monitoring - filter by project
        try:
            all_networks = list(conn.network.networks())
            all_subnets = list(conn.network.subnets())
            all_ports = list(conn.network.ports())
            all_routers = list(conn.network.routers())
            all_floating_ips = list(conn.network.ips())
            
            # Filter by project (include shared/external networks for access)
            networks = [n for n in all_networks if (
                (getattr(n, 'project_id', None) or getattr(n, 'tenant_id', None)) == current_project_id or
                getattr(n, 'is_shared', False) or getattr(n, 'is_router_external', False)
            )]
            subnets = [s for s in all_subnets if (
                (getattr(s, 'project_id', None) or getattr(s, 'tenant_id', None)) == current_project_id
            )]
            ports = [p for p in all_ports if (
                (getattr(p, 'project_id', None) or getattr(p, 'tenant_id', None)) == current_project_id
            )]
            routers = [r for r in all_routers if (
                (getattr(r, 'project_id', None) or getattr(r, 'tenant_id', None)) == current_project_id
            )]
            floating_ips = [f for f in all_floating_ips if (
                (getattr(f, 'project_id', None) or getattr(f, 'tenant_id', None)) == current_project_id
            )]
            
            network_stats = {
                'total_networks': len(networks),
                'external_networks': len([n for n in networks if getattr(n, 'is_router_external', False)]),
                'total_subnets': len(subnets),
                'total_ports': len(ports),
                'active_ports': len([p for p in ports if p.status == 'ACTIVE']),
                'total_routers': len(routers),
                'active_routers': len([r for r in routers if r.status == 'ACTIVE']),
                'total_floating_ips': len(floating_ips),
                'allocated_floating_ips': len([f for f in floating_ips if f.fixed_ip_address])
            }
            
            monitoring_data['network'] = network_stats
        except Exception as e:
            monitoring_data['network'] = {'error': str(e)}
            logger.warning(f"Failed to get network monitoring data: {e}")
        
        # Storage monitoring - filter by project
        try:
            all_volumes = list(conn.volume.volumes())
            all_snapshots = list(conn.volume.snapshots())
            
            volumes = [v for v in all_volumes if getattr(v, 'project_id', None) == current_project_id]
            snapshots = [s for s in all_snapshots if getattr(s, 'project_id', None) == current_project_id]
            
            storage_stats = {
                'total_volumes': len(volumes),
                'available_volumes': len([v for v in volumes if v.status == 'available']),
                'in_use_volumes': len([v for v in volumes if v.status == 'in-use']),
                'total_volume_size_gb': sum(getattr(v, 'size', 0) for v in volumes),
                'total_snapshots': len(snapshots),
                'available_snapshots': len([s for s in snapshots if s.status == 'available'])
            }
            
            monitoring_data['storage'] = storage_stats
        except Exception as e:
            monitoring_data['storage'] = {'error': str(e)}
            logger.warning(f"Failed to get storage monitoring data: {e}")
        
        # Identity monitoring
        try:
            projects = list(conn.identity.projects())
            users = list(conn.identity.users())
            
            identity_stats = {
                'total_projects': len(projects),
                'enabled_projects': len([p for p in projects if p.is_enabled]),
                'total_users': len(users),
                'enabled_users': len([u for u in users if u.is_enabled])
            }
            
            monitoring_data['identity'] = identity_stats
        except Exception as e:
            monitoring_data['identity'] = {'error': str(e)}
            logger.warning(f"Failed to get identity monitoring data: {e}")
        
        return {
            'success': True,
            'monitoring_data': monitoring_data
        }
        
    except Exception as e:
        logger.error(f"Failed to get resource monitoring: {e}")
        return {
            'success': False,
            'error': str(e),
            'message': 'Failed to collect resource monitoring data'
        }


def get_compute_quota_usage(conn) -> Dict[str, Any]:
    """
    Get compute quota usage information.
    
    Args:
        conn: OpenStack connection object
    
    Returns:
        Dict containing compute quota usage data
    """
    try:
        project_id = conn.current_project_id
        quota = conn.compute.get_quota_set(project_id)
        limits = conn.compute.get_limits()
        
        # Get current usage
        servers = list(conn.compute.servers())
        total_vcpus = sum(getattr(server, 'flavor', {}).get('vcpus', 0) for server in servers)
        total_ram = sum(getattr(server, 'flavor', {}).get('ram', 0) for server in servers)
        
        usage_data = {
            'instances': {
                'used': len(servers),
                'limit': getattr(quota, 'instances', -1),
                'percentage': (len(servers) / getattr(quota, 'instances', 1)) * 100 if getattr(quota, 'instances', -1) > 0 else 0
            },
            'vcpus': {
                'used': total_vcpus,
                'limit': getattr(quota, 'cores', -1),
                'percentage': (total_vcpus / getattr(quota, 'cores', 1)) * 100 if getattr(quota, 'cores', -1) > 0 else 0
            },
            'ram': {
                'used': total_ram,
                'limit': getattr(quota, 'ram', -1),
                'percentage': (total_ram / getattr(quota, 'ram', 1)) * 100 if getattr(quota, 'ram', -1) > 0 else 0
            },
            'key_pairs': {
                'used': len(list(conn.compute.keypairs())),
                'limit': getattr(quota, 'key_pairs', -1),
                'percentage': 0  # Calculate if needed
            }
        }
        
        return usage_data
        
    except Exception as e:
        logger.error(f"Failed to get compute quota usage: {e}")
        return {
            'error': str(e),
            'instances': {'used': 0, 'limit': -1, 'percentage': 0},
            'vcpus': {'used': 0, 'limit': -1, 'percentage': 0},
            'ram': {'used': 0, 'limit': -1, 'percentage': 0}
        }


def get_usage_statistics(start_date: str = "", end_date: str = "") -> Dict[str, Any]:
    """
    Get usage statistics for the current project.
    
    Args:
        start_date: Start date for statistics (YYYY-MM-DD format)
        end_date: End date for statistics (YYYY-MM-DD format)
    
    Returns:
        Dict containing usage statistics
    """
    try:
        # Import here to avoid circular imports
        from ..connection import get_openstack_connection
        conn = get_openstack_connection()
        
        # Set default dates if not provided
        if not end_date:
            end_date = datetime.now().strftime('%Y-%m-%d')
        if not start_date:
            start_datetime = datetime.now() - timedelta(days=30)
            start_date = start_datetime.strftime('%Y-%m-%d')
        
        usage_stats = {
            'period': {
                'start_date': start_date,
                'end_date': end_date
            },
            'compute': {},
            'network': {},
            'storage': {}
        }
        
        # Compute usage
        try:
            servers = list(conn.compute.servers())
            flavors = {f.id: f for f in conn.compute.flavors()}
            
            server_stats = {
                'total_servers': len(servers),
                'servers_by_status': {},
                'servers_by_flavor': {},
                'total_vcpus': 0,
                'total_memory_mb': 0
            }
            
            for server in servers:
                status = server.status
                server_stats['servers_by_status'][status] = server_stats['servers_by_status'].get(status, 0) + 1
                
                flavor_id = getattr(server, 'flavor', {}).get('id')
                if flavor_id and flavor_id in flavors:
                    flavor_name = flavors[flavor_id].name
                    server_stats['servers_by_flavor'][flavor_name] = server_stats['servers_by_flavor'].get(flavor_name, 0) + 1
                    server_stats['total_vcpus'] += getattr(flavors[flavor_id], 'vcpus', 0)
                    server_stats['total_memory_mb'] += getattr(flavors[flavor_id], 'ram', 0)
            
            usage_stats['compute'] = server_stats
            
        except Exception as e:
            usage_stats['compute'] = {'error': str(e)}
            logger.warning(f"Failed to get compute usage: {e}")
        
        # Network usage
        try:
            networks = list(conn.network.networks())
            subnets = list(conn.network.subnets())
            ports = list(conn.network.ports())
            floating_ips = list(conn.network.ips())
            
            network_stats = {
                'total_networks': len(networks),
                'total_subnets': len(subnets),
                'total_ports': len(ports),
                'ports_by_status': {},
                'floating_ips': {
                    'total': len(floating_ips),
                    'allocated': len([f for f in floating_ips if f.fixed_ip_address]),
                    'available': len([f for f in floating_ips if not f.fixed_ip_address])
                }
            }
            
            for port in ports:
                status = port.status
                network_stats['ports_by_status'][status] = network_stats['ports_by_status'].get(status, 0) + 1
            
            usage_stats['network'] = network_stats
            
        except Exception as e:
            usage_stats['network'] = {'error': str(e)}
            logger.warning(f"Failed to get network usage: {e}")
        
        # Storage usage
        try:
            volumes = list(conn.volume.volumes())
            snapshots = list(conn.volume.snapshots())
            
            storage_stats = {
                'volumes': {
                    'total_count': len(volumes),
                    'total_size_gb': sum(getattr(v, 'size', 0) for v in volumes),
                    'volumes_by_status': {},
                    'volumes_by_type': {}
                },
                'snapshots': {
                    'total_count': len(snapshots),
                    'total_size_gb': sum(getattr(s, 'size', 0) for s in snapshots),
                    'snapshots_by_status': {}
                }
            }
            
            for volume in volumes:
                status = volume.status
                volume_type = getattr(volume, 'volume_type', 'unknown')
                storage_stats['volumes']['volumes_by_status'][status] = storage_stats['volumes']['volumes_by_status'].get(status, 0) + 1
                storage_stats['volumes']['volumes_by_type'][volume_type] = storage_stats['volumes']['volumes_by_type'].get(volume_type, 0) + 1
            
            for snapshot in snapshots:
                status = snapshot.status
                storage_stats['snapshots']['snapshots_by_status'][status] = storage_stats['snapshots']['snapshots_by_status'].get(status, 0) + 1
            
            usage_stats['storage'] = storage_stats
            
        except Exception as e:
            usage_stats['storage'] = {'error': str(e)}
            logger.warning(f"Failed to get storage usage: {e}")
        
        return {
            'success': True,
            'usage_statistics': usage_stats
        }
        
    except Exception as e:
        logger.error(f"Failed to get usage statistics: {e}")
        return {
            'success': False,
            'error': str(e),
            'message': 'Failed to collect usage statistics'
        }


def get_quota(project_name: str = "") -> Dict[str, Any]:
    """
    Get quota information for a project.
    
    Args:
        project_name: Name of the project (current project if empty)
    
    Returns:
        Dict containing quota information
    """
    try:
        # Import here to avoid circular imports
        from ..connection import get_openstack_connection
        conn = get_openstack_connection()
        
        # Get project ID
        if project_name:
            project = None
            for proj in conn.identity.projects():
                if proj.name == project_name:
                    project = proj
                    break
            
            if not project:
                return {
                    'success': False,
                    'error': f'Project "{project_name}" not found'
                }
            project_id = project.id
        else:
            project_id = conn.current_project_id
            project_name = "current project"
        
        quota_data = {
            'project_name': project_name,
            'project_id': project_id,
            'compute': {
                'limits': {},
                'usage': {}
            },
            'network': {
                'limits': {},
                'usage': {}
            },
            'volume': {
                'limits': {},
                'usage': {}
            }
        }
        
        # Compute quotas and usage
        try:
            compute_quotas = conn.compute.get_quota_set(project_id)
            quota_data['compute']['limits'] = {
                'instances': getattr(compute_quotas, 'instances', -1),
                'cores': getattr(compute_quotas, 'cores', -1),
                'ram': getattr(compute_quotas, 'ram', -1),
                'key_pairs': getattr(compute_quotas, 'key_pairs', -1),
                'metadata_items': getattr(compute_quotas, 'metadata_items', -1),
                'server_groups': getattr(compute_quotas, 'server_groups', -1),
                'server_group_members': getattr(compute_quotas, 'server_group_members', -1)
            }
            
            # Get compute usage
            instances = list(conn.compute.servers())
            active_instances = [i for i in instances if getattr(i, 'status', '') == 'ACTIVE']
            total_cores = 0
            total_ram = 0
            
            for instance in instances:
                try:
                    flavor = conn.compute.get_flavor(instance.flavor['id'])
                    total_cores += getattr(flavor, 'vcpus', 0)
                    total_ram += getattr(flavor, 'ram', 0)
                except Exception:
                    pass
            
            keypairs = list(conn.compute.keypairs())
            
            quota_data['compute']['usage'] = {
                'instances': len(instances),
                'cores': total_cores,
                'ram': total_ram,
                'key_pairs': len(keypairs),
                'active_instances': len(active_instances)
            }
        except Exception as e:
            quota_data['compute'] = {'error': str(e)}
        
        # Network quotas and usage
        try:
            network_quotas = conn.network.get_quota(project_id)
            quota_data['network']['limits'] = {
                'networks': getattr(network_quotas, 'networks', -1),
                'subnets': getattr(network_quotas, 'subnets', -1),
                'ports': getattr(network_quotas, 'ports', -1),
                'routers': getattr(network_quotas, 'routers', -1),
                'floatingips': getattr(network_quotas, 'floatingips', -1),
                'security_groups': getattr(network_quotas, 'security_groups', -1),
                'security_group_rules': getattr(network_quotas, 'security_group_rules', -1)
            }
            
            # Get network usage
            networks = list(conn.network.networks(project_id=project_id))
            subnets = list(conn.network.subnets(project_id=project_id))
            ports = list(conn.network.ports(project_id=project_id))
            routers = list(conn.network.routers(project_id=project_id))
            floatingips = list(conn.network.ips(project_id=project_id))
            security_groups = list(conn.network.security_groups(project_id=project_id))
            
            total_sg_rules = 0
            for sg in security_groups:
                try:
                    rules = list(conn.network.security_group_rules(security_group_id=sg.id))
                    total_sg_rules += len(rules)
                except Exception:
                    pass
            
            quota_data['network']['usage'] = {
                'networks': len(networks),
                'subnets': len(subnets),
                'ports': len(ports),
                'routers': len(routers),
                'floatingips': len(floatingips),
                'security_groups': len(security_groups),
                'security_group_rules': total_sg_rules
            }
        except Exception as e:
            quota_data['network'] = {'error': str(e)}
        
        # Volume quotas and usage
        try:
            volume_quotas = conn.volume.get_quota_set(project_id)
            quota_data['volume']['limits'] = {
                'volumes': getattr(volume_quotas, 'volumes', -1),
                'snapshots': getattr(volume_quotas, 'snapshots', -1),
                'gigabytes': getattr(volume_quotas, 'gigabytes', -1),
                'backups': getattr(volume_quotas, 'backups', -1),
                'backup_gigabytes': getattr(volume_quotas, 'backup_gigabytes', -1)
            }
            
            # Get volume usage
            volumes = list(conn.volume.volumes(project_id=project_id))
            snapshots = list(conn.volume.snapshots(project_id=project_id))
            
            total_gigabytes = sum(getattr(vol, 'size', 0) for vol in volumes)
            
            # Try to get backups (may not be available in all OpenStack deployments)
            try:
                backups = list(conn.volume.backups(project_id=project_id))
                backup_gigabytes = sum(getattr(backup, 'size', 0) for backup in backups)
            except Exception:
                backups = []
                backup_gigabytes = 0
            
            quota_data['volume']['usage'] = {
                'volumes': len(volumes),
                'snapshots': len(snapshots),
                'gigabytes': total_gigabytes,
                'backups': len(backups),
                'backup_gigabytes': backup_gigabytes
            }
        except Exception as e:
            quota_data['volume'] = {'error': str(e)}
        
        return {
            'success': True,
            'quotas': quota_data
        }
        
    except Exception as e:
        logger.error(f"Failed to get quota information: {e}")
        return {
            'success': False,
            'error': str(e),
            'message': 'Failed to retrieve quota information'
        }


def get_hypervisor_details(hypervisor_name: str = "all") -> Dict[str, Any]:
    """
    Get details about hypervisors.
    
    Args:
        hypervisor_name: Name of specific hypervisor or "all" for all hypervisors
    
    Returns:
        Dict containing hypervisor information
    """
    try:
        # Import here to avoid circular imports
        from ..connection import get_openstack_connection
        conn = get_openstack_connection()
        
        if hypervisor_name.lower() == "all":
            hypervisors = []
            total_stats = {
                'count': 0,
                'vcpus': 0,
                'vcpus_used': 0,
                'memory_mb': 0,
                'memory_mb_used': 0,
                'local_gb': 0,
                'local_gb_used': 0,
                'running_vms': 0
            }
            
            for hypervisor in conn.compute.hypervisors(details=True):
                # Safely get attributes with proper None handling
                vcpus = getattr(hypervisor, 'vcpus', None) or 0
                vcpus_used = getattr(hypervisor, 'vcpus_used', None) or 0
                memory_mb = getattr(hypervisor, 'memory_mb', None) or getattr(hypervisor, 'memory_size_mb', None) or 0
                memory_mb_used = getattr(hypervisor, 'memory_mb_used', None) or getattr(hypervisor, 'memory_used_mb', None) or 0
                local_gb = getattr(hypervisor, 'local_gb', None) or getattr(hypervisor, 'local_disk_size_gb', None) or 0
                local_gb_used = getattr(hypervisor, 'local_gb_used', None) or getattr(hypervisor, 'local_disk_used_gb', None) or 0
                running_vms = getattr(hypervisor, 'running_vms', None) or 0
                
                hyp_data = {
                    'id': hypervisor.id,
                    'name': getattr(hypervisor, 'name', 'unknown'),
                    'host_ip': getattr(hypervisor, 'host_ip', 'unknown'),
                    'status': getattr(hypervisor, 'status', 'unknown'),
                    'state': getattr(hypervisor, 'state', 'unknown'),
                    'vcpus': vcpus,
                    'vcpus_used': vcpus_used,
                    'memory_mb': memory_mb,
                    'memory_mb_used': memory_mb_used,
                    'local_gb': local_gb,
                    'local_gb_used': local_gb_used,
                    'running_vms': running_vms,
                    'hypervisor_type': getattr(hypervisor, 'hypervisor_type', 'unknown'),
                    'hypervisor_version': getattr(hypervisor, 'hypervisor_version', 'unknown')
                }
                
                # Add to totals (now safe since all values are guaranteed integers)
                total_stats['count'] += 1
                total_stats['vcpus'] += vcpus
                total_stats['vcpus_used'] += vcpus_used
                total_stats['memory_mb'] += memory_mb
                total_stats['memory_mb_used'] += memory_mb_used
                total_stats['local_gb'] += local_gb
                total_stats['local_gb_used'] += local_gb_used
                total_stats['running_vms'] += running_vms
                
                hypervisors.append(hyp_data)
            
            # Try to get enhanced statistics from Nova API
            enhanced_stats = None
            try:
                stats_response = conn.compute.get('/os-hypervisors/statistics')
                if stats_response.status_code == 200:
                    stats_data = stats_response.json()
                    hypervisor_statistics = stats_data.get('hypervisor_statistics', {})
                    
                    if hypervisor_statistics:
                        enhanced_stats = {
                            'count': hypervisor_statistics.get('count', 0),
                            'vcpus': hypervisor_statistics.get('vcpus', 0),
                            'vcpus_used': hypervisor_statistics.get('vcpus_used', 0),
                            'memory_mb': hypervisor_statistics.get('memory_mb', 0),
                            'memory_mb_used': hypervisor_statistics.get('memory_mb_used', 0),
                            'local_gb': hypervisor_statistics.get('local_gb', 0),
                            'local_gb_used': hypervisor_statistics.get('local_gb_used', 0),
                            'running_vms': hypervisor_statistics.get('running_vms', 0),
                            'data_source': 'nova_hypervisor_statistics_api'
                        }
            except Exception as e:
                # Continue with regular response if statistics API fails
                pass
            
            return {
                'success': True,
                'hypervisors': hypervisors,
                'total_stats': total_stats,
                'enhanced_stats': enhanced_stats
            }
        else:
            # Get specific hypervisor
            for hypervisor in conn.compute.hypervisors(details=True):
                if getattr(hypervisor, 'name', '') == hypervisor_name:
                    # Safely get attributes with proper None handling
                    vcpus = getattr(hypervisor, 'vcpus', None) or 0
                    vcpus_used = getattr(hypervisor, 'vcpus_used', None) or 0
                    memory_mb = getattr(hypervisor, 'memory_mb', None) or getattr(hypervisor, 'memory_size_mb', None) or 0
                    memory_mb_used = getattr(hypervisor, 'memory_mb_used', None) or getattr(hypervisor, 'memory_used_mb', None) or 0
                    local_gb = getattr(hypervisor, 'local_gb', None) or getattr(hypervisor, 'local_disk_size_gb', None) or 0
                    local_gb_used = getattr(hypervisor, 'local_gb_used', None) or getattr(hypervisor, 'local_disk_used_gb', None) or 0
                    running_vms = getattr(hypervisor, 'running_vms', None) or 0
                    
                    return {
                        'success': True,
                        'hypervisor': {
                            'id': hypervisor.id,
                            'name': getattr(hypervisor, 'name', 'unknown'),
                            'host_ip': getattr(hypervisor, 'host_ip', 'unknown'),
                            'status': getattr(hypervisor, 'status', 'unknown'),
                            'state': getattr(hypervisor, 'state', 'unknown'),
                            'vcpus': vcpus,
                            'vcpus_used': vcpus_used,
                            'memory_mb': memory_mb,
                            'memory_mb_used': memory_mb_used,
                            'local_gb': local_gb,
                            'local_gb_used': local_gb_used,
                            'running_vms': running_vms,
                            'hypervisor_type': getattr(hypervisor, 'hypervisor_type', 'unknown'),
                            'hypervisor_version': getattr(hypervisor, 'hypervisor_version', 'unknown')
                        }
                    }
            
            return {
                'success': False,
                'error': f'Hypervisor "{hypervisor_name}" not found'
            }
            
    except Exception as e:
        logger.error(f"Failed to get hypervisor details: {e}")
        return {
            'success': False,
            'error': str(e),
            'message': 'Failed to retrieve hypervisor information'
        }


def get_availability_zones() -> Dict[str, Any]:
    """
    Get availability zones information.
    
    Returns:
        Dict containing availability zones data
    """
    try:
        # Import here to avoid circular imports
        from ..connection import get_openstack_connection
        conn = get_openstack_connection()
        
        zones_data = {
            'compute': [],
            'network': [],
            'volume': []
        }
        
        # Compute availability zones
        try:
            compute_zones = list(conn.compute.availability_zones())
            for zone in compute_zones:
                zones_data['compute'].append({
                    'name': getattr(zone, 'name', 'unknown'),
                    'available': getattr(zone, 'available', False),
                    'hosts': getattr(zone, 'hosts', {})
                })
        except Exception as e:
            zones_data['compute'] = [{'error': str(e)}]
        
        # Network availability zones
        try:
            network_zones = list(conn.network.availability_zones())
            for zone in network_zones:
                zones_data['network'].append({
                    'name': getattr(zone, 'name', 'unknown'),
                    'state': getattr(zone, 'state', 'unknown'),
                    'resource': getattr(zone, 'resource', 'network')
                })
        except Exception as e:
            zones_data['network'] = [{'error': str(e)}]
        
        # Volume availability zones
        try:
            volume_zones = list(conn.volume.availability_zones())
            for zone in volume_zones:
                zones_data['volume'].append({
                    'name': getattr(zone, 'name', 'unknown'),
                    'available': getattr(zone, 'available', False)
                })
        except Exception as e:
            zones_data['volume'] = [{'error': str(e)}]
        
        return {
            'success': True,
            'availability_zones': zones_data
        }
        
    except Exception as e:
        logger.error(f"Failed to get availability zones: {e}")
        return {
            'success': False,
            'error': str(e),
            'message': 'Failed to retrieve availability zones'
        }


def set_quota(project_name: str, service: str, **kwargs) -> Dict[str, Any]:
    """
    Set quota for a project.
    
    Args:
        project_name: Name of the project
        service: Service type (compute, network, volume)
        **kwargs: Quota parameters to set
    
    Returns:
        Result of the quota update operation
    """
    try:
        # Import here to avoid circular imports
        from ..connection import get_openstack_connection
        conn = get_openstack_connection()
        
        # Find project
        project = None
        for proj in conn.identity.projects():
            if proj.name == project_name or proj.id == project_name:
                project = proj
                break
        
        if not project:
            return {
                'success': False,
                'error': f'Project "{project_name}" not found'
            }
        
        service = service.lower()
        
        if service == 'compute':
            # Update compute quotas
            quota_updates = {}
            for key, value in kwargs.items():
                if key in ['instances', 'cores', 'ram', 'key_pairs', 'metadata_items', 'server_groups', 'server_group_members']:
                    quota_updates[key] = int(value)
            
            if quota_updates:
                conn.compute.update_quota_set(project.id, **quota_updates)
                return {
                    'success': True,
                    'message': f'Compute quotas updated for project "{project_name}"',
                    'updated_quotas': quota_updates
                }
            else:
                return {
                    'success': False,
                    'error': 'No valid compute quota parameters provided'
                }
                
        elif service == 'network':
            # Update network quotas
            quota_updates = {}
            for key, value in kwargs.items():
                if key in ['networks', 'subnets', 'ports', 'routers', 'floatingips', 'security_groups', 'security_group_rules']:
                    quota_updates[key] = int(value)
            
            if quota_updates:
                conn.network.update_quota(project.id, **quota_updates)
                return {
                    'success': True,
                    'message': f'Network quotas updated for project "{project_name}"',
                    'updated_quotas': quota_updates
                }
            else:
                return {
                    'success': False,
                    'error': 'No valid network quota parameters provided'
                }
                
        elif service == 'volume':
            # Update volume quotas
            quota_updates = {}
            for key, value in kwargs.items():
                if key in ['volumes', 'snapshots', 'gigabytes', 'backups', 'backup_gigabytes']:
                    quota_updates[key] = int(value)
            
            if quota_updates:
                conn.volume.update_quota_set(project.id, **quota_updates)
                return {
                    'success': True,
                    'message': f'Volume quotas updated for project "{project_name}"',
                    'updated_quotas': quota_updates
                }
            else:
                return {
                    'success': False,
                    'error': 'No valid volume quota parameters provided'
                }
        else:
            return {
                'success': False,
                'error': f'Unknown service "{service}". Supported: compute, network, volume'
            }
            
    except Exception as e:
        logger.error(f"Failed to set quota: {e}")
        return {
            'success': False,
            'error': str(e),
            'message': f'Failed to set {service} quota for project "{project_name}"'
        }