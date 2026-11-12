"""
OpenStack Compute (Nova) Service Functions

This module contains functions for managing instances, flavors, server groups,
server events, and other compute-related components.
"""

import logging
from typing import Dict, List, Any, Optional

# Configure logging
logger = logging.getLogger(__name__)


def _get_server_image(conn: Any, server: Any, *,
                      check_ownership: bool = True) -> Dict[str, str]:
    """Resolve image references, including volume-backed instance provenance.

    ``check_ownership`` is False for cross-project reads, where the boot volume
    belongs to the server's project rather than the caller's.
    """
    from ..connection import validate_resource_ownership

    reference = getattr(server, 'image', None)
    image_id = (reference.get('id') if isinstance(reference, dict)
                else getattr(reference, 'id', None))
    info = {'id': image_id or 'unknown', 'name': 'unknown'}
    if not image_id:
        attachments = (getattr(server, 'attached_volumes', None)
                       or getattr(server, 'volumes_attached', None) or [])
        roots = [a for a in attachments if isinstance(a, dict)
                 and str(a.get('boot_index')) == '0']
        candidates = []
        for attachment in roots or attachments:
            if isinstance(attachment, dict):
                volume_id = attachment.get('volume_id') or attachment.get('id')
            else:
                volume_id = (getattr(attachment, 'volume_id', None)
                             or getattr(attachment, 'id', None))
            if not volume_id:
                return info
            try:
                volume = conn.block_storage.get_volume(volume_id)
                if check_ownership and not validate_resource_ownership(volume, 'Volume'):
                    return info
                if str(getattr(volume, 'is_bootable', False)).lower() == 'true':
                    candidates.append(volume.volume_image_metadata or {})
            except Exception as error:
                logger.warning("Could not get boot volume image metadata: %s", error)
                return info
        # Several bootable volumes can be attached; never guess which booted it.
        if len(candidates) != 1:
            return info
        image_id = candidates[0].get('image_id')
        if not image_id:
            return info
        info = {'id': image_id, 'name': candidates[0].get('image_name') or 'unknown'}
    try:
        image = conn.image.get_image(image_id)
        info['name'] = getattr(image, 'name', None) or info['name']
    except Exception as error:
        logger.warning("Could not get image details for %s: %s", image_id, error)
    return info


def _server_boot_source(server: Any) -> str:
    """Return 'image', or 'volume' when Nova reports no image (boot from volume)."""
    reference = getattr(server, 'image', None)
    image_id = (reference.get('id') if isinstance(reference, dict)
                else getattr(reference, 'id', None))
    return 'image' if image_id else 'volume'


def get_instance_details(
    instance_names: Optional[List[str]] = None,
    limit: int = 50,
    offset: int = 0,
    include_all: bool = False,
    *,
    enrich_images: bool = True,
    status_filter: Optional[str] = None,
    all_projects: bool = False,
) -> Dict[str, Any]:
    """
    Get detailed information about OpenStack instances with pagination support.
    
    Args:
        instance_names: List of instance names to filter (optional)
        limit: Maximum number of instances to return (default: 50, max: 200)
        offset: Number of instances to skip for pagination (default: 0)
        include_all: If True, return all instances ignoring limit (default: False)
        all_projects: List instances of every project the credential's
            OpenStack policy allows (requires ALLOW_CROSS_PROJECT_READ=true)
    
    Returns:
        Dictionary containing instances and metadata
    """
    try:
        # Import here to avoid circular imports
        from ..connection import (
            cross_project_scope, get_current_project_id, get_openstack_connection,
            get_project_names, raise_if_cross_project_denied,
            require_cross_project_read, validate_resource_ownership,
        )
        if all_projects:
            require_cross_project_read()
        conn = get_openstack_connection()
        
        # Validate and sanitize inputs
        if limit > 200:
            limit = 200
        if limit < 1:
            limit = 1
        if offset < 0:
            offset = 0
        
        instances = []
        
        # Get all servers with project filtering enabled
        filters = {"status": status_filter.upper()} if status_filter else {}
        try:
            all_servers = list(conn.compute.servers(
                details=True, all_projects=all_projects, **filters
            ))
        except Exception as e:
            if all_projects:
                raise_if_cross_project_denied(e)
            raise
        
        current_project_id = get_current_project_id()
        project_names: Dict[str, str] = {}
        if all_projects:
            # OpenStack policy already decided which projects are visible.
            project_names = get_project_names(conn)
        else:
            # Additional project validation for security
            validated_servers = []
            
            for server in all_servers:
                if validate_resource_ownership(server, "Instance"):
                    validated_servers.append(server)
                else:
                    logger.warning(f"Filtered out instance {getattr(server, 'id', 'unknown')} - not owned by current project")
            
            all_servers = validated_servers
        
        if status_filter:
            all_servers = [server for server in all_servers
                           if str(getattr(server, "status", "")).upper()
                           == status_filter.upper()]

        # Filter by instance names if provided
        if instance_names:
            filtered_servers = []
            for server in all_servers:
                server_name = getattr(server, 'name', 'unnamed')
                if server_name in instance_names or server.id in instance_names:
                    filtered_servers.append(server)
            all_servers = filtered_servers
        
        # Handle pagination
        total_count = len(all_servers)
        
        if include_all:
            paginated_servers = all_servers
        else:
            paginated_servers = all_servers[offset:offset + limit]
        
        for server in paginated_servers:
            try:
                # Get server flavor details - use embedded flavor info from server details
                flavor_info = {'id': 'unknown', 'name': 'unknown', 'vcpus': 0, 'ram': 0, 'disk': 0}
                if hasattr(server, 'flavor') and server.flavor:
                    if isinstance(server.flavor, dict):
                        # Flavor info is embedded in server details - use it directly
                        flavor_info = {
                            'id': server.flavor.get('id', 'unknown'),
                            'name': server.flavor.get('original_name', server.flavor.get('name', 'unknown')),
                            'vcpus': server.flavor.get('vcpus', 0),
                            'ram': server.flavor.get('ram', 0),
                            'disk': server.flavor.get('disk', 0)
                        }
                    else:
                        # If flavor is an object, try to get attributes
                        flavor_info = {
                            'id': getattr(server.flavor, 'id', 'unknown'),
                            'name': getattr(server.flavor, 'original_name', getattr(server.flavor, 'name', 'unknown')),
                            'vcpus': getattr(server.flavor, 'vcpus', 0),
                            'ram': getattr(server.flavor, 'ram', 0),
                            'disk': getattr(server.flavor, 'disk', 0)
                        }
                
                # Get server image details
                if enrich_images:
                    image_info = _get_server_image(
                        conn, server, check_ownership=not all_projects)
                else:
                    reference = getattr(server, "image", None)
                    image_id = (reference.get("id") if isinstance(reference, dict)
                                else getattr(reference, "id", None))
                    image_info = {"id": image_id or "unknown", "name": "unknown"}
                
                # Get network information
                networks = []
                addresses = getattr(server, 'addresses', {}) or {}
                for network_name, network_addresses in addresses.items():
                    network_info = {
                        'network': network_name,
                        'addresses': []
                    }
                    for addr in network_addresses:
                        if isinstance(addr, dict):
                            network_info['addresses'].append({
                                'addr': addr.get('addr', 'unknown'),
                                'type': addr.get('OS-EXT-IPS:type', 'unknown'),
                                'version': addr.get('version', 4),
                                'mac_addr': addr.get('OS-EXT-IPS-MAC:mac_addr', 'unknown')
                            })
                        else:
                            network_info['addresses'].append({'addr': str(addr), 'type': 'unknown'})
                    
                    networks.append(network_info)
                
                # Get security groups
                security_groups = []
                sg_list = getattr(server, 'security_groups', []) or []
                for sg in sg_list:
                    if isinstance(sg, dict):
                        security_groups.append(sg.get('name', 'unknown'))
                    else:
                        security_groups.append(getattr(sg, 'name', 'unknown'))
                
                # Build instance data
                instance_data = {
                    'id': server.id,
                    'name': getattr(server, 'name', 'unnamed'),
                    'status': getattr(server, 'status', 'unknown'),
                    'power_state': getattr(server, 'power_state', 0),
                    'task_state': getattr(server, 'task_state', None),
                    'vm_state': getattr(server, 'vm_state', 'unknown'),
                    'created': str(getattr(server, 'created_at', 'unknown')),
                    'updated': str(getattr(server, 'updated_at', 'unknown')),
                    'launched_at': str(getattr(server, 'launched_at', None)) if getattr(server, 'launched_at', None) else None,
                    'host': getattr(server, 'host', 'unknown'),
                    'hypervisor_hostname': getattr(server, 'hypervisor_hostname', 'unknown'),
                    'availability_zone': getattr(server, 'availability_zone', 'unknown'),
                    'flavor': flavor_info,
                    'image': image_info,
                    'boot_source': _server_boot_source(server),
                    'key_name': getattr(server, 'key_name', None),
                    'networks': networks,
                    'security_groups': security_groups,
                    'tenant_id': getattr(server, 'tenant_id', getattr(server, 'project_id', 'unknown')),
                    'user_id': getattr(server, 'user_id', 'unknown'),
                    'metadata': getattr(server, 'metadata', {}),
                    'fault': getattr(server, 'fault', None),
                    'progress': getattr(server, 'progress', 0),
                    'config_drive': getattr(server, 'config_drive', False),
                    'locked': getattr(server, 'is_locked', False)
                }
                if all_projects:
                    project_id = getattr(server, 'project_id', None)
                    instance_data['project_id'] = project_id
                    instance_data['project_name'] = project_names.get(project_id)
                
                # Add volume attachment info if available
                if hasattr(server, 'attached_volumes') or hasattr(server, 'volumes_attached'):
                    volumes = getattr(server, 'attached_volumes', getattr(server, 'volumes_attached', []))
                    instance_data['attached_volumes'] = [v.get('id', v) if isinstance(v, dict) else str(v) for v in volumes]
                else:
                    instance_data['attached_volumes'] = []
                
                instances.append(instance_data)
                
            except Exception as e:
                logger.error(f"Failed to process server {server.id}: {e}")
                # Add minimal error entry
                instances.append({
                    'id': server.id,
                    'name': getattr(server, 'name', 'unnamed'),
                    'status': 'error',
                    'error': f'Failed to get details: {str(e)}'
                })
        
        # Pagination metadata
        has_next = (offset + limit) < total_count
        has_prev = offset > 0
        next_offset = offset + limit if has_next else None
        prev_offset = max(0, offset - limit) if has_prev else None
        
        result = {
            'instances': instances,
            'count': len(instances),
            'total_count': total_count,
            'limit': limit,
            'offset': offset,
            'has_next': has_next,
            'has_prev': has_prev,
            'next_offset': next_offset,
            'prev_offset': prev_offset
        }
        
        if instance_names:
            result['filtered_by_names'] = instance_names
        if all_projects:
            result['scope'] = cross_project_scope(
                (getattr(server, 'project_id', None) for server in all_servers),
                current_project_id,
            )
            
        return result
        
    except Exception as e:
        from ..connection import CrossProjectReadError
        logger.error(f"Failed to get instance details: {e}")
        failure = {
            'instances': [],
            'count': 0,
            'total_count': 0,
            'error': str(e),
            'success': False
        }
        if isinstance(e, CrossProjectReadError):
            failure['error_type'] = 'cross_project'
        return failure


def get_instance_by_name(instance_name: str) -> Optional[Dict[str, Any]]:
    """
    Get a single instance by name.
    
    Args:
        instance_name: Name of the instance
        
    Returns:
        Instance details or None if not found
    """
    try:
        result = get_instance_details([instance_name], limit=1)
        instances = result.get('instances', [])
        return instances[0] if instances else None
    except Exception as e:
        logger.error(f"Failed to get instance by name: {e}")
        return None


def get_instance_by_id(instance_id: str) -> Optional[Dict[str, Any]]:
    """
    Get a single instance by ID.
    
    Args:
        instance_id: ID of the instance
        
    Returns:
        Instance details or None if not found
    """
    try:
        result = get_instance_details([instance_id], limit=1)
        instances = result.get('instances', [])
        return instances[0] if instances else None
    except Exception as e:
        logger.error(f"Failed to get instance by ID: {e}")
        return None


def _raise_cross_project_failure(result: Dict[str, Any]) -> None:
    """Re-raise a disabled or denied cross-project read with its message."""
    if result.get('error_type') == 'cross_project':
        from ..connection import CrossProjectReadError
        raise CrossProjectReadError(result['error'])


def search_instances(
    search_term: str,
    search_fields: Optional[List[str]] = None,
    limit: int = 50,
    include_inactive: bool = False,
    offset: int = 0,
    case_sensitive: bool = False,
    *,
    with_pagination: bool = False,
    all_projects: bool = False,
) -> List[Dict[str, Any]] | Dict[str, Any]:
    """
    Search for instances by various fields.
    
    Args:
        search_term: Term to search for
        search_fields: Fields to search in (default: name, id)
        limit: Maximum results to return
        include_inactive: Include non-active instances
        offset: Number of matches to skip
        case_sensitive: Match the original case when True
        with_pagination: Include page metadata for MCP callers
        all_projects: Search instances of every project the credential's
            OpenStack policy allows (requires ALLOW_CROSS_PROJECT_READ=true)
        
    Returns:
        Matching instances, optionally with pagination metadata
    """
    try:
        # Import here to avoid circular imports
        from ..connection import get_openstack_connection, require_cross_project_read
        if all_projects:
            require_cross_project_read()
        conn = get_openstack_connection()

        if search_fields is None:
            search_fields = ['name', 'id']
        
        aliases = {'flavor': 'flavor_name', 'image': 'image_name'}
        if 'all' in search_fields:
            search_fields = ['name', 'id', 'status', 'host', 'availability_zone',
                             'ip', 'flavor_name', 'image_name']
        else:
            search_fields = [aliases.get(field.strip(), field.strip())
                             for field in search_fields]
        needs_images = bool(search_term and 'image_name' in search_fields)
        matching_instances = []
        limit = max(1, min(limit, 200))
        all_instances_result = get_instance_details(
            include_all=True,
            enrich_images=needs_images,
            status_filter=None if include_inactive else 'ACTIVE',
            all_projects=all_projects,
        )
        _raise_cross_project_failure(all_instances_result)
        if all_instances_result.get('success') is False:
            raise RuntimeError('OpenStack instance search failed')
        all_instances = all_instances_result.get('instances', [])
        
        offset = max(0, offset)
        needle = search_term if case_sensitive else search_term.lower()

        def matches(value):
            text = str(value)
            return needle in (text if case_sensitive else text.lower())
        
        for instance in all_instances:
            # Skip inactive instances if not requested
            if not include_inactive and instance.get('status', '').lower() not in ['active', 'running']:
                continue
                
            match_found = False
            
            for field in search_fields:
                if matches(instance.get(field, '')):
                    match_found = True
                    break
                    
                # Special handling for nested fields
                if field == 'ip':
                    for network in instance.get('networks', []):
                        for addr in network.get('addresses', []):
                            if matches(addr.get('addr', '')):
                                match_found = True
                                break
                        if match_found:
                            break
                elif field == 'flavor_name':
                    flavor = instance.get('flavor', {})
                    if matches(flavor.get('name', '')):
                        match_found = True
                elif field == 'image_name':
                    image = instance.get('image', {})
                    if matches(image.get('name', '')):
                        match_found = True
            
            if match_found:
                matching_instances.append(instance)
                
            if len(matching_instances) >= offset + limit + int(with_pagination):
                break
        
        has_more = len(matching_instances) > offset + limit
        matching_instances = matching_instances[offset:offset + limit]
        if matching_instances and not needs_images:
            details = get_instance_details(
                instance_names=[row['id'] for row in matching_instances],
                include_all=True,
                all_projects=all_projects,
            )
            _raise_cross_project_failure(details)
            if details.get('success') is False:
                raise RuntimeError('OpenStack instance search failed')
            matching_instances = details['instances']
        if with_pagination:
            page = {
                'instances': matching_instances,
                'search_info': {
                    'search_term': search_term,
                    'search_in': ','.join(search_fields),
                    'case_sensitive': case_sensitive,
                    'matches_found': len(matching_instances),
                },
                'pagination': {
                    'limit': limit, 'offset': offset, 'has_more': has_more,
                },
            }
            if all_projects:
                page['scope'] = all_instances_result.get('scope')
            return page
        return matching_instances
        
    except Exception as e:
        from ..connection import CrossProjectReadError
        if isinstance(e, CrossProjectReadError):
            raise
        logger.error("Failed to search instances: %s", type(e).__name__)
        raise RuntimeError("OpenStack instance search failed") from None


# Nova server status values (API "status" field).
NOVA_SERVER_STATUSES = frozenset({
    'ACTIVE', 'BUILD', 'DELETED', 'ERROR', 'HARD_REBOOT', 'MIGRATING',
    'PASSWORD', 'PAUSED', 'REBOOT', 'REBUILD', 'RESCUE', 'RESIZE',
    'REVERT_RESIZE', 'SHELVED', 'SHELVED_OFFLOADED', 'SHUTOFF',
    'SOFT_DELETED', 'SUSPENDED', 'UNKNOWN', 'VERIFY_RESIZE',
})


def find_server_by_name_or_id(name_or_id: str) -> Optional[Any]:
    """Return the server whose name or ID matches, or None.

    API failures propagate so callers can report them instead of treating
    them as "not found".
    """
    from ..connection import get_openstack_connection
    conn = get_openstack_connection()
    for srv in conn.compute.servers():
        if getattr(srv, 'name', '') == name_or_id or getattr(srv, 'id', '') == name_or_id:
            return srv
    return None


def get_instances_by_status(
    status: str, *, enrich_images: bool = True, all_projects: bool = False
) -> List[Dict[str, Any]]:
    """
    Get instances filtered by status.
    
    Args:
        status: Status to filter by (ACTIVE, SHUTOFF, ERROR, etc.)
        all_projects: Include instances of every project the credential's
            OpenStack policy allows (requires ALLOW_CROSS_PROJECT_READ=true)
        
    Returns:
        List of instances with matching status

    Raises:
        ValueError: if ``status`` is not a Nova server status.
    """
    if str(status or '').strip().upper() not in NOVA_SERVER_STATUSES:
        raise ValueError(
            f'Invalid instance status "{status}". Valid statuses: '
            + ', '.join(sorted(NOVA_SERVER_STATUSES))
        )
    status = status.strip()
    try:
        result = get_instance_details(
            include_all=True, enrich_images=enrich_images, status_filter=status,
            all_projects=all_projects,
        )
        _raise_cross_project_failure(result)
        if result.get('success') is False:
            raise RuntimeError('OpenStack instance status query failed')
        instances = result.get('instances', [])
        
        status_lower = status.lower()
        return [
            instance for instance in instances 
            if instance.get('status', '').lower() == status_lower
        ]
        
    except Exception as e:
        from ..connection import CrossProjectReadError
        if isinstance(e, CrossProjectReadError):
            raise
        logger.error("Failed to get instances by status: %s", type(e).__name__)
        raise RuntimeError("OpenStack instance status query failed") from None


def _root_disk_option_error(options: Dict[str, Any]) -> Optional[str]:
    """Return why the create root-disk options conflict, or None if they fit."""
    boot_volume = options.get('boot_volume')
    boot_from_volume = bool(options.get('boot_from_volume'))
    volume_size = options.get('volume_size')
    if boot_volume and options.get('image', options.get('image_name')):
        return 'Use either image or boot_volume for create, not both.'
    if boot_volume and boot_from_volume:
        return ('boot_from_volume creates a new root volume from image; '
                'use it or boot_volume, not both.')
    if boot_from_volume:
        if (not isinstance(volume_size, int) or isinstance(volume_size, bool)
                or volume_size < 1):
            return ('volume_size (GB, at least 1) is required when '
                    'boot_from_volume is true.')
    elif volume_size is not None or options.get('volume_type'):
        return 'volume_size and volume_type apply only when boot_from_volume is true.'
    return None


def set_instance(instance_name: str, action: str, **kwargs) -> Dict[str, Any]:
    """
    Manage instances (start, stop, reboot, delete, create, etc.).
    
    Args:
        instance_name: Name of the instance
        action: Action to perform
        **kwargs: Additional parameters depending on action
    
    Returns:
        Result of the instance operation
    """
    try:
        # Import here to avoid circular imports
        from ..connection import get_openstack_connection, find_resource_by_name_or_id
        conn = get_openstack_connection()
        
        if action.lower() == 'list':
            result = get_instance_details(limit=kwargs.get('limit', 50))
            return {
                'success': True,
                'instances': result.get('instances', []),
                'count': result.get('count', 0),
                'total_count': result.get('total_count', 0)
            }
            
        elif action.lower() == 'create':
            # Required parameters
            flavor_name = kwargs.get('flavor', kwargs.get('flavor_name'))
            image_name = kwargs.get('image', kwargs.get('image_name'))
            network_names = kwargs.get('networks', kwargs.get('network_names', []))
            boot_volume_name = kwargs.get('boot_volume')
            delete_on_termination = bool(kwargs.get('delete_on_termination', True))

            if not flavor_name:
                return {
                    'success': False,
                    'message': 'Flavor parameter is required for create action. Please specify a flavor (e.g., m1.small, m1.medium).'
                }

            root_disk_error = _root_disk_option_error(kwargs)
            if root_disk_error:
                return {'success': False, 'message': root_disk_error}

            if not image_name and not boot_volume_name:
                # Get available images for error message
                try:
                    all_images = list(conn.image.images())
                    active_images = [img.name for img in all_images if img.status == 'active'][:10]  # Show first 10
                    available_list = '\n'.join(f"  • {img}" for img in active_images)
                    more_available = f"\n  ... and {len([img for img in all_images if img.status == 'active']) - 10} more" if len([img for img in all_images if img.status == 'active']) > 10 else ""
                    
                    return {
                        'success': False,
                        'message': f'Image parameter is required for VM creation.\n\n**Available Images:**\n{available_list}{more_available}\n\nPlease specify one using the image parameter (e.g., image="ubuntu-22.04").'
                    }
                except Exception as e:
                    logger.error(f"Failed to retrieve available images: {e}")
                    return {
                        'success': False,
                        'message': 'Image parameter is required for VM creation. Please specify an image name (e.g., ubuntu-22.04, rocky-9, centos-8).'
                    }
            
            # Find flavor using secure project-scoped lookup
            flavor = find_resource_by_name_or_id(
                conn.compute.flavors(), 
                flavor_name, 
                "Flavor"
            )

            if not flavor:
                return {
                    'success': False,
                    'message': f'Flavor "{flavor_name}" not found or not accessible in current project'
                }
            
            # Find image using secure project-scoped lookup
            image = None
            if image_name:
                image = find_resource_by_name_or_id(
                    conn.image.images(),
                    image_name,
                    "Image"
                )

                if not image:
                    return {
                        'success': False,
                        'message': f'Image "{image_name}" not found or not accessible in current project'
                    }

            # Root disk: the image on the flavor's local disk (default), a new
            # volume created from the image, or an existing bootable volume.
            block_device_mapping = None
            boot_source = 'image'
            if boot_volume_name:
                boot_volume = find_resource_by_name_or_id(
                    conn.volume.volumes(), boot_volume_name, "Volume"
                )
                if not boot_volume:
                    return {
                        'success': False,
                        'message': f'Volume "{boot_volume_name}" not found or not accessible in current project'
                    }
                volume_status = getattr(boot_volume, 'status', None)
                if volume_status != 'available':
                    return {
                        'success': False,
                        'message': f'Volume "{boot_volume_name}" must be available to boot from it; its status is {volume_status}'
                    }
                if str(getattr(boot_volume, 'is_bootable', False)).lower() != 'true':
                    return {
                        'success': False,
                        'message': f'Volume "{boot_volume_name}" is not bootable'
                    }
                block_device_mapping = [{
                    'boot_index': 0,
                    'uuid': boot_volume.id,
                    'source_type': 'volume',
                    'destination_type': 'volume',
                    'delete_on_termination': delete_on_termination,
                }]
                boot_source = 'volume'
            elif kwargs.get('boot_from_volume'):
                root_volume = {
                    'boot_index': 0,
                    'uuid': image.id,
                    'source_type': 'image',
                    'destination_type': 'volume',
                    'volume_size': kwargs['volume_size'],
                    'delete_on_termination': delete_on_termination,
                }
                if kwargs.get('volume_type'):
                    root_volume['volume_type'] = kwargs['volume_type']
                block_device_mapping = [root_volume]
                boot_source = 'new_volume'
            
            # Handle networks with secure project-scoped lookup
            networks = []
            if network_names:
                if isinstance(network_names, str):
                    network_names = [network_names]
                    
                for network_name in network_names:
                    network = find_resource_by_name_or_id(
                        conn.network.networks(), 
                        network_name, 
                        "Network"
                    )
                    
                    if network:
                        networks.append({'uuid': network.id})
                    else:
                        return {
                            'success': False,
                            'message': f'Network "{network_name}" not found or not accessible in current project'
                        }
            
            # Optional parameters
            key_name = kwargs.get('key_name', kwargs.get('keypair'))
            security_groups = kwargs.get('security_groups', kwargs.get('security_group'))
            availability_zone = kwargs.get('availability_zone', kwargs.get('az'))
            user_data = kwargs.get('user_data')
            metadata = kwargs.get('metadata', {})
            
            # Handle security groups
            if security_groups:
                if isinstance(security_groups, str):
                    security_groups = [security_groups]
            
            create_params = {
                'name': instance_name,
                'flavor_id': flavor.id,
            }
            if block_device_mapping:
                create_params['block_device_mapping'] = block_device_mapping
            else:
                create_params['image_id'] = image.id

            if networks:
                create_params['networks'] = networks
            if key_name:
                create_params['key_name'] = key_name
            if security_groups:
                create_params['security_groups'] = [{'name': sg} for sg in security_groups]
            if availability_zone:
                create_params['availability_zone'] = availability_zone
            if user_data:
                create_params['user_data'] = user_data
            if metadata:
                create_params['metadata'] = metadata
            
            try:
                server = conn.compute.create_server(**create_params)
                
                return {
                    'success': True,
                    'message': f'Instance "{instance_name}" creation started',
                    'instance': {
                        'id': server.id,
                        'name': getattr(server, 'name', 'unnamed'),
                        'status': getattr(server, 'status', 'unknown'),
                        'flavor': {'id': flavor.id, 'name': getattr(flavor, 'name', 'unknown')},
                        'image': ({'id': image.id, 'name': getattr(image, 'name', 'unknown')}
                                  if image else None),
                        'boot_source': boot_source,
                        'block_device_mapping': block_device_mapping or [],
                    }
                }
            except Exception as create_error:
                logger.error(f"Failed to create instance '{instance_name}': {create_error}")
                return {
                    'success': False,
                    'message': f'Instance creation failed: {str(create_error)}'
                }
            
        # Find existing instance for other actions using secure lookup
        server = find_resource_by_name_or_id(
            conn.compute.servers(), 
            instance_name, 
            "Instance"
        )
        
        if not server:
            return {
                'success': False,
                'message': f'Instance "{instance_name}" not found or not accessible in current project'
            }
        
        if action.lower() in ['start', 'boot', 'power_on']:
            conn.compute.start_server(server)
            return {
                'success': True,
                'message': f'Instance "{instance_name}" started'
            }
            
        elif action.lower() in ['stop', 'shutdown', 'power_off']:
            conn.compute.stop_server(server)
            return {
                'success': True,
                'message': f'Instance "{instance_name}" stopped'
            }
            
        elif action.lower() in ['reboot', 'restart']:
            reboot_type = kwargs.get('type', 'SOFT')  # SOFT or HARD
            conn.compute.reboot_server(server, reboot_type)
            return {
                'success': True,
                'message': f'Instance "{instance_name}" reboot initiated ({reboot_type})'
            }
            
        elif action.lower() == 'pause':
            conn.compute.pause_server(server)
            return {
                'success': True,
                'message': f'Instance "{instance_name}" paused'
            }
            
        elif action.lower() == 'unpause':
            conn.compute.unpause_server(server)
            return {
                'success': True,
                'message': f'Instance "{instance_name}" unpaused'
            }
            
        elif action.lower() == 'suspend':
            conn.compute.suspend_server(server)
            return {
                'success': True,
                'message': f'Instance "{instance_name}" suspended'
            }
            
        elif action.lower() == 'resume':
            conn.compute.resume_server(server)
            return {
                'success': True,
                'message': f'Instance "{instance_name}" resumed'
            }
            
        elif action.lower() in ['delete', 'terminate']:
            force = kwargs.get('force', False)
            if force:
                # openstacksdk exposes forceDelete as delete_server(force=True);
                # there is no force_delete_server() proxy method.
                conn.compute.delete_server(server, force=True)
                return {
                    'success': True,
                    'message': f'Instance "{instance_name}" force deleted'
                }
            else:
                conn.compute.delete_server(server)
                return {
                    'success': True,
                    'message': f'Instance "{instance_name}" deleted'
                }
                
        elif action.lower() == 'resize':
            new_flavor_name = kwargs.get('flavor', kwargs.get('new_flavor'))
            if not new_flavor_name:
                return {
                    'success': False,
                    'message': 'flavor parameter is required for resize action'
                }
            
            # Find new flavor
            new_flavor = None
            for flv in conn.compute.flavors():
                if getattr(flv, 'name', '') == new_flavor_name or flv.id == new_flavor_name:
                    new_flavor = flv
                    break
            
            if not new_flavor:
                return {
                    'success': False,
                    'message': f'New flavor "{new_flavor_name}" not found'
                }
            
            conn.compute.resize_server(server, new_flavor.id)
            return {
                'success': True,
                'message': f'Instance "{instance_name}" resize initiated to {new_flavor_name}'
            }
            
        elif action.lower() == 'confirm_resize':
            conn.compute.confirm_server_resize(server)
            return {
                'success': True,
                'message': f'Instance "{instance_name}" resize confirmed'
            }
            
        elif action.lower() == 'revert_resize':
            conn.compute.revert_server_resize(server)
            return {
                'success': True,
                'message': f'Instance "{instance_name}" resize reverted'
            }
            
        elif action.lower() == 'snapshot':
            snapshot_name = kwargs.get('snapshot_name', f'{instance_name}-snapshot')
            metadata = kwargs.get('metadata', {})
            
            snapshot = conn.compute.create_server_image(server, name=snapshot_name, metadata=metadata)
            return {
                'success': True,
                'message': f'Snapshot "{snapshot_name}" creation started',
                'snapshot_id': snapshot
            }
            
        elif action.lower() == 'console':
            # novnc, spice-html5, rdp-html5, serial, webmks (>= 2.8),
            # spice-direct (>= 2.99); xvpvnc is legacy-only.
            console_type = kwargs.get('type', 'novnc') or 'novnc'

            try:
                # create_console() uses the remote-consoles API
                # (POST /servers/{id}/remote-consoles) at microversion >= 2.6
                # and only falls back to the legacy os-get*Console server
                # actions on older clouds. The legacy actions are gone on
                # current Nova and return 404 there.
                console = conn.compute.create_console(server, console_type)
                console = dict(console or {})
                url = console.get('url')
                if not url:
                    return {
                        'success': False,
                        'message': f'Failed to get console URL: no URL returned for console type "{console_type}"'
                    }
                return {
                    'success': True,
                    'console': {
                        'type': console.get('type') or console_type,
                        'protocol': console.get('protocol'),
                        'url': url
                    }
                }
            except Exception as e:
                return {
                    'success': False,
                    'message': f'Failed to get console URL: {str(e)}'
                }
                
        elif action.lower() == 'shelve':
            conn.compute.shelve_server(server)
            return {
                'success': True,
                'message': f'Instance "{instance_name}" shelved'
            }
            
        elif action.lower() == 'unshelve':
            conn.compute.unshelve_server(server)
            return {
                'success': True,
                'message': f'Instance "{instance_name}" unshelved'
            }
            
        elif action.lower() == 'lock':
            conn.compute.lock_server(server)
            return {
                'success': True,
                'message': f'Instance "{instance_name}" locked'
            }
            
        elif action.lower() == 'unlock':
            conn.compute.unlock_server(server)
            return {
                'success': True,
                'message': f'Instance "{instance_name}" unlocked'
            }
            
        elif action.lower() == 'rescue':
            rescue_image_id = kwargs.get('rescue_image_id')
            admin_pass = kwargs.get('admin_pass')
            
            rescue_params = {}
            if rescue_image_id:
                rescue_params['image_id'] = rescue_image_id
            if admin_pass:
                rescue_params['admin_pass'] = admin_pass
                
            conn.compute.rescue_server(server, **rescue_params)
            return {
                'success': True,
                'message': f'Instance "{instance_name}" put in rescue mode'
            }
            
        elif action.lower() == 'unrescue':
            conn.compute.unrescue_server(server)
            return {
                'success': True,
                'message': f'Instance "{instance_name}" restored from rescue mode'
            }
            
        elif action.lower() == 'rebuild':
            image_name = kwargs.get('image', kwargs.get('image_name'))
            if not image_name:
                return {
                    'success': False,
                    'message': 'image parameter is required for rebuild action'
                }
                
            # Find image
            image = None
            for img in conn.image.images():
                if getattr(img, 'name', '') == image_name or img.id == image_name:
                    image = img
                    break
            
            if not image:
                return {
                    'success': False,
                    'message': f'Image "{image_name}" not found'
                }
                
            # Proxy.rebuild_server(server, image, **attrs): the image is a
            # required positional argument; attrs must use Server.rebuild()
            # keyword names (name, admin_password, preserve_ephemeral,
            # metadata, ...). Nova replaces server metadata on rebuild, so
            # only send it when the caller supplied a non-empty object.
            rebuild_params = {
                'preserve_ephemeral': bool(kwargs.get('preserve_ephemeral', False)),
            }
            if kwargs.get('new_name'):
                rebuild_params['name'] = kwargs['new_name']
            admin_password = kwargs.get('admin_password', kwargs.get('admin_pass'))
            if admin_password:
                rebuild_params['admin_password'] = admin_password
            if kwargs.get('metadata'):
                rebuild_params['metadata'] = kwargs['metadata']

            conn.compute.rebuild_server(server, image.id, **rebuild_params)
            return {
                'success': True,
                'message': f'Instance "{instance_name}" rebuild initiated with image {image_name}'
            }
                
        else:
            return {
                'success': False,
                'message': f'Unknown action "{action}". Supported: create, start, stop, reboot, pause, unpause, suspend, resume, delete, resize, confirm_resize, revert_resize, snapshot, console, shelve, unshelve, lock, unlock, rescue, unrescue, rebuild, list'
            }
            
    except Exception as e:
        logger.error(f"Failed to manage instance: {e}")
        return {
            'success': False,
            'message': f'Failed to manage instance: {str(e)}',
            'error': str(e)
        }


def get_flavor_list() -> List[Dict[str, Any]]:
    """
    Get list of available flavors with detailed information.
    
    Returns:
        List of flavor dictionaries
    """
    try:
        # Import here to avoid circular imports
        from ..connection import get_openstack_connection
        conn = get_openstack_connection()
        flavors = []
        
        for flavor in conn.compute.flavors(details=True):
            # Get extra specs if available
            extra_specs = {}
            try:
                extra_specs = dict(getattr(flavor, 'extra_specs', {}))
            except Exception:
                pass
            
            flavors.append({
                'id': flavor.id,
                'name': getattr(flavor, 'name', 'unnamed'),
                'vcpus': getattr(flavor, 'vcpus', 0),
                'ram': getattr(flavor, 'ram', 0),  # MB
                'disk': getattr(flavor, 'disk', 0),  # GB
                'ephemeral': getattr(flavor, 'ephemeral', 0),
                'swap': getattr(flavor, 'swap', 0),
                'rxtx_factor': getattr(flavor, 'rxtx_factor', 1.0),
                'is_public': getattr(flavor, 'is_public', True),
                'extra_specs': extra_specs,
                'description': getattr(flavor, 'description', '')
            })
        
        return flavors
    except Exception as e:
        logger.error(f"Failed to get flavor list: {e}")
        raise RuntimeError("OpenStack resource query failed") from None


MAX_SERVER_EVENT_DETAILS = 10


def get_server_events(
    instance_name: str,
    limit: int = 50,
    include_event_details: bool = False,
) -> Dict[str, Any]:
    """
    Get server action/event history.
    
    Args:
        instance_name: Name or ID of the server
        limit: Maximum number of events to return
        include_event_details: Fetch each action's event details. This adds one
            Nova API request per returned action.
        
    Returns:
        Dictionary containing server events
    """
    try:
        # Import here to avoid circular imports
        from ..connection import get_openstack_connection
        conn = get_openstack_connection()
        
        # Find the server
        server = None
        for srv in conn.compute.servers():
            if getattr(srv, 'name', '') == instance_name or srv.id == instance_name:
                server = srv
                break
        
        if not server:
            return {
                'success': False,
                'message': f'Server "{instance_name}" not found',
                'events': []
            }
        
        events = []
        effective_limit = (
            min(limit, MAX_SERVER_EVENT_DETAILS)
            if include_event_details else limit
        )
        try:
            # Get server actions (events)
            for action in conn.compute.server_actions(server.id):
                detail_available = False
                if include_event_details:
                    try:
                        detail = conn.compute.get_server_action(
                            action.request_id,
                            server.id,
                            ignore_missing=True,
                        )
                        if detail is not None:
                            action = detail
                            detail_available = True
                    except Exception as error:
                        logger.warning(
                            "Could not get server action details: %s",
                            type(error).__name__,
                        )

                action_events = []
                finish_times = []
                for event in getattr(action, 'events', None) or []:
                    finish_time = getattr(event, 'finish_time', None)
                    if finish_time:
                        finish_times.append(str(finish_time))
                    action_events.append({
                        'event': getattr(event, 'event', 'unknown'),
                        'start_time': str(
                            getattr(event, 'start_time', 'unknown')
                        ),
                        'finish_time': (
                            str(finish_time) if finish_time else None
                        ),
                        'result': getattr(event, 'result', 'unknown'),
                        'traceback': getattr(event, 'traceback', None)
                    })

                finish_time = max(finish_times) if finish_times else None
                if finish_time:
                    finish_time_source = 'latest_event'
                elif include_event_details and detail_available:
                    finish_time_source = 'event_details_contain_no_finish_time'
                elif include_event_details:
                    finish_time_source = 'event_details_unavailable'
                else:
                    finish_time_source = (
                        'action_list_does_not_include_finish_time'
                    )

                event_data = {
                    'action': getattr(action, 'action', 'unknown'),
                    'instance_uuid': getattr(action, 'instance_uuid', server.id),
                    'request_id': getattr(action, 'request_id', 'unknown'),
                    'user_id': getattr(action, 'user_id', 'unknown'),
                    'project_id': getattr(action, 'project_id', 'unknown'),
                    'start_time': str(getattr(action, 'start_time', 'unknown')),
                    'finish_time': finish_time,
                    'finish_time_source': finish_time_source,
                    'message': getattr(action, 'message', ''),
                    'details': getattr(action, 'details', {}),
                    'events': action_events,
                }

                events.append(event_data)
                
                if len(events) >= effective_limit:
                    break
                    
        except Exception as e:
            logger.warning(f"Could not get server actions: {e}")
            # Fallback to basic server info
            events.append({
                'action': 'info',
                'message': f'Server actions not available: {str(e)}',
                'server_id': server.id,
                'server_name': getattr(server, 'name', 'unnamed'),
                'server_status': getattr(server, 'status', 'unknown'),
                'created': str(getattr(server, 'created_at', 'unknown')),
                'updated': str(getattr(server, 'updated_at', 'unknown'))
            })
        
        return {
            'success': True,
            'server_name': getattr(server, 'name', 'unnamed'),
            'server_id': server.id,
            'events': events,
            'count': len(events),
            'event_details_requested': include_event_details,
            'requested_limit': limit,
            'effective_limit': effective_limit,
            'detail_limit_applied': effective_limit != limit,
        }
        
    except Exception as e:
        logger.error(f"Failed to get server events: {e}")
        return {
            'success': False,
            'message': f'Failed to get server events for "{instance_name}": {str(e)}',
            'events': [],
            'error': str(e)
        }


def _server_group_policies(group) -> List[str]:
    """Return a server group's policies for any compute microversion.

    Nova 2.64+ returns a single ``policy`` instead of the ``policies`` list,
    so ``ServerGroup.policies`` is None on modern clouds.
    """
    policies = getattr(group, 'policies', None)
    if policies:
        return list(policies)
    policy = getattr(group, 'policy', None)
    return [policy] if policy else []


def get_server_groups() -> List[Dict[str, Any]]:
    """
    Get list of server groups.
    
    Returns:
        List of server group dictionaries
    """
    try:
        # Import here to avoid circular imports
        from ..connection import get_openstack_connection
        conn = get_openstack_connection()
        server_groups = []
        
        try:
            for group in conn.compute.server_groups():
                members = getattr(group, 'member_ids', []) or []
                
                server_groups.append({
                    'id': group.id,
                    'name': getattr(group, 'name', 'unnamed'),
                    'policies': _server_group_policies(group),
                    'members': list(members),
                    'member_count': len(members),
                    'metadata': getattr(group, 'metadata', {}),
                    'project_id': getattr(group, 'project_id', 'unknown'),
                    'user_id': getattr(group, 'user_id', 'unknown'),
                    'created_at': str(getattr(group, 'created_at', 'unknown')),
                    'updated_at': str(getattr(group, 'updated_at', 'unknown'))
                })
        except Exception as e:
            logger.error(f"Failed to list server groups: {e}")
            # An empty list would read as "no server groups"; report the error.
            raise

        return server_groups
    except Exception as e:
        logger.error(f"Failed to get server groups: {e}")
        raise


def set_server_group(group_name: str, action: str, **kwargs) -> Dict[str, Any]:
    """
    Manage server groups (create, delete, list, show).
    
    Args:
        group_name: Name of the server group
        action: Action to perform (create, delete, list, show)
        **kwargs: Additional parameters
        
    Returns:
        Result of the server group operation
    """
    try:
        # Import here to avoid circular imports
        from ..connection import get_openstack_connection
        conn = get_openstack_connection()
        
        if action.lower() == 'create':
            policies = kwargs.get('policies', kwargs.get('policy', ['affinity']))
            if isinstance(policies, str):
                policies = [policies]
                
            # Validate policies
            valid_policies = ['affinity', 'anti-affinity', 'soft-affinity', 'soft-anti-affinity']
            for policy in policies:
                if policy not in valid_policies:
                    return {
                        'success': False,
                        'message': f'Invalid policy "{policy}". Valid policies: {valid_policies}'
                    }
            
            server_group = conn.compute.create_server_group(
                name=group_name,
                policies=policies
            )
            
            return {
                'success': True,
                'message': f'Server group "{group_name}" created',
                'server_group': {
                    'id': server_group.id,
                    'name': getattr(server_group, 'name', 'unnamed'),
                    'policies': _server_group_policies(server_group) or policies,
                    'members': getattr(server_group, 'member_ids', [])
                }
            }
            
        elif action.lower() == 'delete':
            # Find server group using secure project-scoped lookup
            from ..connection import find_resource_by_name_or_id
            
            server_group = find_resource_by_name_or_id(
                conn.compute.server_groups(), 
                group_name, 
                "Server Group"
            )

            if not server_group:
                return {
                    'success': False,
                    'message': f'Server group "{group_name}" not found or not accessible in current project'
                }

            conn.compute.delete_server_group(server_group)
            return {
                'success': True,
                'message': f'Server group "{group_name}" deleted'
            }
            
        elif action.lower() == 'list':
            return {
                'success': True,
                'server_groups': get_server_groups()
            }
            
        elif action.lower() == 'show':
            # Find server group
            server_group = None
            for sg in conn.compute.server_groups():
                if getattr(sg, 'name', '') == group_name or sg.id == group_name:
                    server_group = sg
                    break
            
            if not server_group:
                return {
                    'success': False,
                    'message': f'Server group "{group_name}" not found'
                }
            
            return {
                'success': True,
                'server_group': {
                    'id': server_group.id,
                    'name': getattr(server_group, 'name', 'unnamed'),
                    'policies': _server_group_policies(server_group),
                    'members': getattr(server_group, 'member_ids', []),
                    'metadata': getattr(server_group, 'metadata', {}),
                    'project_id': getattr(server_group, 'project_id', 'unknown'),
                    'user_id': getattr(server_group, 'user_id', 'unknown')
                }
            }
        else:
            return {
                'success': False,
                'message': f'Unknown action "{action}". Supported: create, delete, list, show'
            }
            
    except Exception as e:
        logger.error(f"Failed to manage server group: {e}")
        return {
            'success': False,
            'message': f'Failed to manage server group: {str(e)}',
            'error': str(e)
        }


def _find_port_by_name_or_id(conn: Any, name_or_id: str):
    """Resolve a Neutron port by name or ID.

    Returns ``(port, None)`` or ``(None, error_message)``.
    """
    try:
        port = conn.network.find_port(name_or_id, ignore_missing=True)
    except Exception as e:
        # e.g. DuplicateResource when several ports share the name
        return None, f'Port "{name_or_id}" could not be resolved: {e}'
    if port is None:
        return None, f'Port "{name_or_id}" not found'
    return port, None


def set_server_network(instance_name: str, action: str, **kwargs) -> Dict[str, Any]:
    """
    Manage server network operations (add network, remove network, add port, remove port).
    
    Args:
        instance_name: Name or ID of the server
        action: Action to perform (add_network, remove_network, add_port, remove_port)
        **kwargs: Additional parameters
        
    Returns:
        Result of the network operation
    """
    try:
        # Import here to avoid circular imports
        from ..connection import get_openstack_connection
        conn = get_openstack_connection()
        
        # Find the server
        server = None
        for srv in conn.compute.servers():
            if getattr(srv, 'name', '') == instance_name or srv.id == instance_name:
                server = srv
                break
        
        if not server:
            return {
                'success': False,
                'message': f'Server "{instance_name}" not found'
            }
        
        if action.lower() == 'add_network':
            network_name = kwargs.get('network', kwargs.get('network_name'))
            if not network_name:
                return {
                    'success': False,
                    'message': 'network parameter is required for add_network action'
                }
            
            # Find network
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
            
            # Let Nova create (and therefore own) the port: a port Nova
            # creates for an interface attach is deleted by Nova when the
            # interface is detached, so remove_network does not leave an
            # orphaned port behind that blocks network/subnet deletion.
            interface_params = {'net_id': network.id}

            # Optional fixed IP
            fixed_ip = kwargs.get('fixed_ip')
            if fixed_ip:
                interface_params['fixed_ips'] = [{'ip_address': fixed_ip}]

            interface = conn.compute.create_server_interface(server, **interface_params)

            return {
                'success': True,
                'message': f'Network "{network_name}" added to server "{instance_name}"',
                'port_id': getattr(interface, 'port_id', None)
            }
            
        elif action.lower() == 'remove_network':
            network_name = kwargs.get('network', kwargs.get('network_name'))
            if not network_name:
                return {
                    'success': False,
                    'message': 'network parameter is required for remove_network action'
                }
            
            # Find network
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
            
            # Get server interfaces and remove ports from this network
            removed_ports = []
            for interface in conn.compute.server_interfaces(server):
                if getattr(interface, 'net_id', '') == network.id:
                    conn.compute.delete_server_interface(interface, server)
                    removed_ports.append(interface.port_id)
            
            if not removed_ports:
                return {
                    'success': False,
                    'message': f'No interfaces found for network "{network_name}" on server "{instance_name}"'
                }
            
            return {
                'success': True,
                'message': f'Network "{network_name}" removed from server "{instance_name}"',
                'removed_ports': removed_ports
            }
            
        elif action.lower() == 'add_port':
            port_id = kwargs.get('port', kwargs.get('port_id'))
            if not port_id:
                return {
                    'success': False,
                    'message': 'port parameter is required for add_port action'
                }
            
            # Resolve the port by name or ID. get_port() only accepts an ID,
            # so a port given by name was always reported as not found.
            port, error = _find_port_by_name_or_id(conn, port_id)
            if error:
                return {'success': False, 'message': error}

            conn.compute.create_server_interface(server, port_id=port.id)
            
            return {
                'success': True,
                'message': f'Port "{port_id}" added to server "{instance_name}"',
                'port_id': port.id
            }
            
        elif action.lower() == 'remove_port':
            port_id = kwargs.get('port', kwargs.get('port_id'))
            if not port_id:
                return {
                    'success': False,
                    'message': 'port parameter is required for remove_port action'
                }
            
            # Accept a port name or ID; match the attached interface by ID.
            port_ids = {port_id}
            port, _ = _find_port_by_name_or_id(conn, port_id)
            if port is not None:
                port_ids.add(port.id)

            # Find interface with this port
            interface = None
            for intf in conn.compute.server_interfaces(server):
                if getattr(intf, 'port_id', '') in port_ids:
                    interface = intf
                    break
            
            if not interface:
                return {
                    'success': False,
                    'message': f'Port "{port_id}" not found on server "{instance_name}"'
                }
            
            # Detach only. Nova keeps ports that were created outside Nova
            # (preserve_on_delete) and removes only the ports it created.
            conn.compute.delete_server_interface(interface, server)
            
            return {
                'success': True,
                'message': f'Port "{port_id}" removed from server "{instance_name}"',
                'port_id': interface.port_id
            }
        else:
            return {
                'success': False,
                'message': f'Unknown action "{action}". Supported: add_network, remove_network, add_port, remove_port'
            }
            
    except Exception as e:
        logger.error(f"Failed to manage server network: {e}")
        return {
            'success': False,
            'message': f'Failed to manage server network: {str(e)}',
            'error': str(e)
        }


def set_server_floating_ip(instance_name: str, action: str, **kwargs) -> Dict[str, Any]:
    """
    Manage server floating IP operations (add, remove).
    
    Args:
        instance_name: Name or ID of the server
        action: Action to perform (add, remove)
        **kwargs: Additional parameters
        
    Returns:
        Result of the floating IP operation
    """
    try:
        # Import here to avoid circular imports
        from ..connection import get_openstack_connection
        conn = get_openstack_connection()
        
        # Find the server
        server = None
        for srv in conn.compute.servers():
            if getattr(srv, 'name', '') == instance_name or srv.id == instance_name:
                server = srv
                break
        
        if not server:
            return {
                'success': False,
                'message': f'Server "{instance_name}" not found'
            }
        
        if action.lower() == 'add':
            floating_ip = kwargs.get('floating_ip', kwargs.get('ip'))
            fixed_ip = kwargs.get('fixed_ip')
            
            if not floating_ip:
                return {
                    'success': False,
                    'message': 'floating_ip parameter is required for add action'
                }
            
            # Find floating IP
            fip_obj = None
            for fip in conn.network.ips():
                if getattr(fip, 'floating_ip_address', '') == floating_ip or fip.id == floating_ip:
                    fip_obj = fip
                    break
            
            if not fip_obj:
                return {
                    'success': False,
                    'message': f'Floating IP "{floating_ip}" not found'
                }
            
            # Get server ports to find target fixed IP
            if not fixed_ip:
                # Use first available private IP
                addresses = getattr(server, 'addresses', {})
                for network_name, addrs in addresses.items():
                    for addr in addrs:
                        if addr.get('OS-EXT-IPS:type') == 'fixed':
                            fixed_ip = addr['addr']
                            break
                    if fixed_ip:
                        break
            
            if not fixed_ip:
                return {
                    'success': False,
                    'message': 'Could not determine fixed IP address. Please specify fixed_ip parameter'
                }
            
            # Find port with this fixed IP
            port_id = None
            for interface in conn.compute.server_interfaces(server):
                port = conn.network.get_port(interface.port_id)
                for fixed_ip_info in getattr(port, 'fixed_ips', []):
                    if fixed_ip_info.get('ip_address') == fixed_ip:
                        port_id = port.id
                        break
                if port_id:
                    break
            
            if not port_id:
                return {
                    'success': False,
                    'message': f'Could not find port with fixed IP "{fixed_ip}" on server'
                }
            
            # Associate floating IP
            conn.network.update_ip(fip_obj, port_id=port_id, fixed_ip_address=fixed_ip)
            
            return {
                'success': True,
                'message': f'Floating IP "{floating_ip}" added to server "{instance_name}" (fixed IP: {fixed_ip})'
            }
            
        elif action.lower() == 'remove':
            floating_ip = kwargs.get('floating_ip', kwargs.get('ip'))
            
            if not floating_ip:
                return {
                    'success': False,
                    'message': 'floating_ip parameter is required for remove action'
                }
            
            # Find floating IP
            fip_obj = None
            for fip in conn.network.ips():
                if getattr(fip, 'floating_ip_address', '') == floating_ip or fip.id == floating_ip:
                    fip_obj = fip
                    break
            
            if not fip_obj:
                return {
                    'success': False,
                    'message': f'Floating IP "{floating_ip}" not found'
                }
            
            # Disassociate floating IP
            conn.network.update_ip(fip_obj, port_id=None, fixed_ip_address=None)
            
            return {
                'success': True,
                'message': f'Floating IP "{floating_ip}" removed from server "{instance_name}"'
            }
        else:
            return {
                'success': False,
                'message': f'Unknown action "{action}". Supported: add, remove'
            }
            
    except Exception as e:
        logger.error(f"Failed to manage server floating IP: {e}")
        return {
            'success': False,
            'message': f'Failed to manage server floating IP: {str(e)}',
            'error': str(e)
        }


def set_server_fixed_ip(instance_name: str, action: str, **kwargs) -> Dict[str, Any]:
    """
    Manage server fixed IP operations (add, remove).
    
    Args:
        instance_name: Name or ID of the server
        action: Action to perform (add, remove)
        **kwargs: Additional parameters
        
    Returns:
        Result of the fixed IP operation
    """
    try:
        # Import here to avoid circular imports
        from ..connection import get_openstack_connection
        conn = get_openstack_connection()
        
        # Find the server
        server = None
        for srv in conn.compute.servers():
            if getattr(srv, 'name', '') == instance_name or srv.id == instance_name:
                server = srv
                break
        
        if not server:
            return {
                'success': False,
                'message': f'Server "{instance_name}" not found'
            }
        
        if action.lower() == 'add':
            network_name = kwargs.get('network', kwargs.get('network_name'))
            fixed_ip = kwargs.get('fixed_ip', kwargs.get('ip'))
            
            if not network_name:
                return {
                    'success': False,
                    'message': 'network parameter is required for add action'
                }
            
            # Find network
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
            
            # Let Nova create (and own) the port so that removing the fixed
            # IP (detaching the interface) also deletes the port instead of
            # leaking it.
            interface_params = {'net_id': network.id}
            if fixed_ip:
                interface_params['fixed_ips'] = [{'ip_address': fixed_ip}]
            
            interface = conn.compute.create_server_interface(server, **interface_params)
            
            # Get assigned IP
            fixed_ips = getattr(interface, 'fixed_ips', None) or []
            assigned_ip = fixed_ips[0].get('ip_address', 'unknown') if fixed_ips else (fixed_ip or 'unknown')
            
            return {
                'success': True,
                'message': f'Fixed IP "{assigned_ip}" added to server "{instance_name}" on network "{network_name}"',
                'fixed_ip': assigned_ip,
                'port_id': getattr(interface, 'port_id', None)
            }
            
        elif action.lower() == 'remove':
            fixed_ip = kwargs.get('fixed_ip', kwargs.get('ip'))
            
            if not fixed_ip:
                return {
                    'success': False,
                    'message': 'fixed_ip parameter is required for remove action'
                }
            
            # Find port with this fixed IP
            port_to_remove = None
            for interface in conn.compute.server_interfaces(server):
                port = conn.network.get_port(interface.port_id)
                for fixed_ip_info in getattr(port, 'fixed_ips', []):
                    if fixed_ip_info.get('ip_address') == fixed_ip:
                        port_to_remove = interface
                        break
                if port_to_remove:
                    break
            
            if not port_to_remove:
                return {
                    'success': False,
                    'message': f'Fixed IP "{fixed_ip}" not found on server "{instance_name}"'
                }
            
            # Remove interface and port
            conn.compute.delete_server_interface(port_to_remove, server)
            
            return {
                'success': True,
                'message': f'Fixed IP "{fixed_ip}" removed from server "{instance_name}"'
            }
        else:
            return {
                'success': False,
                'message': f'Unknown action "{action}". Supported: add, remove'
            }
            
    except Exception as e:
        logger.error(f"Failed to manage server fixed IP: {e}")
        return {
            'success': False,
            'message': f'Failed to manage server fixed IP: {str(e)}',
            'error': str(e)
        }


def set_server_security_group(instance_name: str, action: str, **kwargs) -> Dict[str, Any]:
    """
    Manage server security group operations (add, remove).
    
    Args:
        instance_name: Name or ID of the server
        action: Action to perform (add, remove)
        **kwargs: Additional parameters
        
    Returns:
        Result of the security group operation
    """
    try:
        # Import here to avoid circular imports
        from ..connection import get_openstack_connection
        conn = get_openstack_connection()
        
        # Find the server
        server = None
        for srv in conn.compute.servers():
            if getattr(srv, 'name', '') == instance_name or srv.id == instance_name:
                server = srv
                break
        
        if not server:
            return {
                'success': False,
                'message': f'Server "{instance_name}" not found'
            }
        
        security_group = kwargs.get('security_group', kwargs.get('group'))
        if not security_group:
            return {
                'success': False,
                'message': 'security_group parameter is required'
            }
        
        # Find security group
        sg_obj = None
        for sg in conn.network.security_groups():
            if getattr(sg, 'name', '') == security_group or sg.id == security_group:
                sg_obj = sg
                break
        
        if not sg_obj:
            return {
                'success': False,
                'message': f'Security group "{security_group}" not found'
            }
        
        if action.lower() == 'add':
            conn.compute.add_security_group_to_server(server, sg_obj)
            return {
                'success': True,
                'message': f'Security group "{security_group}" added to server "{instance_name}"'
            }
            
        elif action.lower() == 'remove':
            conn.compute.remove_security_group_from_server(server, sg_obj)
            return {
                'success': True,
                'message': f'Security group "{security_group}" removed from server "{instance_name}"'
            }
        else:
            return {
                'success': False,
                'message': f'Unknown action "{action}". Supported: add, remove'
            }
            
    except Exception as e:
        logger.error(f"Failed to manage server security group: {e}")
        return {
            'success': False,
            'message': f'Failed to manage server security group: {str(e)}',
            'error': str(e)
        }


def set_flavor(flavor_name: str, action: str, **kwargs) -> Dict[str, Any]:
    """
    Manage flavors (create, delete, set properties).
    
    Args:
        flavor_name: Name of the flavor
        action: Action to perform
        **kwargs: Additional parameters
        
    Returns:
        Result of the flavor operation
    """
    try:
        # Import here to avoid circular imports
        from ..connection import get_openstack_connection
        conn = get_openstack_connection()
        
        if action.lower() == 'list':
            flavors = get_flavor_list()
            return {
                'success': True,
                'flavors': flavors,
                'count': len(flavors)
            }
            
        elif action.lower() == 'create':
            # Required parameters
            vcpus = kwargs.get('vcpus', kwargs.get('cpu', 1))
            ram = kwargs.get('ram', kwargs.get('memory', 512))  # MB
            disk = kwargs.get('disk', kwargs.get('root_disk', 1))  # GB
            
            # Optional parameters
            ephemeral = kwargs.get('ephemeral', 0)
            swap = kwargs.get('swap', 0)
            rxtx_factor = kwargs.get('rxtx_factor', 1.0)
            is_public = kwargs.get('is_public', True)
            flavor_id = kwargs.get('flavor_id', kwargs.get('id'))
            description = kwargs.get('description', '')
            
            try:
                create_params = {
                    'name': flavor_name,
                    'ram': int(ram),
                    'vcpus': int(vcpus),
                    'disk': int(disk),
                    'ephemeral': int(ephemeral),
                    'swap': int(swap),
                    'rxtx_factor': float(rxtx_factor),
                    'is_public': bool(is_public)
                }
                
                if flavor_id:
                    create_params['flavorid'] = str(flavor_id)
                if description:
                    create_params['description'] = description
                
                flavor = conn.compute.create_flavor(**create_params)
                
                # Set extra specs if provided
                extra_specs = kwargs.get('extra_specs', {})
                if extra_specs and isinstance(extra_specs, dict):
                    try:
                        conn.compute.create_flavor_extra_specs(flavor, extra_specs)
                    except Exception as e:
                        logger.warning(f"Failed to set extra specs: {e}")
                
                return {
                    'success': True,
                    'message': f'Flavor "{flavor_name}" created',
                    'flavor': {
                        'id': flavor.id,
                        'name': getattr(flavor, 'name', 'unnamed'),
                        'vcpus': getattr(flavor, 'vcpus', 0),
                        'ram': getattr(flavor, 'ram', 0),
                        'disk': getattr(flavor, 'disk', 0),
                        'is_public': getattr(flavor, 'is_public', True)
                    }
                }
            except Exception as e:
                return {
                    'success': False,
                    'message': f'Failed to create flavor: {str(e)}'
                }
                
        elif action.lower() == 'delete':
            # Find the flavor using secure project-scoped lookup
            from ..connection import find_resource_by_name_or_id
            
            flavor = find_resource_by_name_or_id(
                conn.compute.flavors(), 
                flavor_name, 
                "Flavor"
            )

            if not flavor:
                return {
                    'success': False,
                    'message': f'Flavor "{flavor_name}" not found or not accessible in current project'
                }

            try:
                conn.compute.delete_flavor(flavor)
                return {
                    'success': True,
                    'message': f'Flavor "{flavor_name}" deleted'
                }
            except Exception as e:
                return {
                    'success': False,
                    'message': f'Failed to delete flavor: {str(e)}'
                }
                
        elif action.lower() == 'set_extra_specs':
            # Find the flavor
            flavor = None
            for flv in conn.compute.flavors():
                if getattr(flv, 'name', '') == flavor_name or flv.id == flavor_name:
                    flavor = flv
                    break
            
            if not flavor:
                return {
                    'success': False,
                    'message': f'Flavor "{flavor_name}" not found'
                }
            
            extra_specs = kwargs.get('extra_specs', {})
            if not extra_specs or not isinstance(extra_specs, dict):
                return {
                    'success': False,
                    'message': 'extra_specs parameter is required and must be a dictionary'
                }
            
            try:
                conn.compute.create_flavor_extra_specs(flavor, extra_specs)
                return {
                    'success': True,
                    'message': f'Extra specs set for flavor "{flavor_name}"',
                    'extra_specs': extra_specs
                }
            except Exception as e:
                return {
                    'success': False,
                    'message': f'Failed to set extra specs: {str(e)}'
                }
                
        else:
            return {
                'success': False,
                'message': f'Unknown action "{action}". Supported: list, create, delete, set_extra_specs'
            }
            
    except Exception as e:
        logger.error(f"Failed to manage flavor: {e}")
        return {
            'success': False,
            'message': f'Failed to manage flavor: {str(e)}',
            'error': str(e)
        }


def set_server_migration(instance_name: str, action: str, **kwargs) -> Dict[str, Any]:
    """
    Manage server migration operations (migrate, evacuate, confirm, revert, etc.).
    
    Args:
        instance_name: Name or ID of the server
        action: Action to perform (migrate, evacuate, confirm, revert, list, show, abort, force_complete)
        **kwargs: Additional parameters
        
    Returns:
        Result of the migration operation
    """
    try:
        # Import here to avoid circular imports
        from ..connection import get_openstack_connection
        conn = get_openstack_connection()
        
        # Find the server for most actions (and for a server-scoped list)
        if action.lower() not in ['list'] or instance_name:
            server = None
            for srv in conn.compute.servers():
                if getattr(srv, 'name', '') == instance_name or srv.id == instance_name:
                    server = srv
                    break
            
            if not server:
                return {
                    'success': False,
                    'message': f'Server "{instance_name}" not found'
                }
        
        if action.lower() == 'migrate':
            host = kwargs.get('host')
            block_migration = kwargs.get('block_migration', 'auto')
            
            # Live migrate server
            migrate_params = {}
            if host:
                migrate_params['host'] = host
            if block_migration != 'auto':
                migrate_params['block_migration'] = block_migration
            
            conn.compute.live_migrate_server(server, **migrate_params)
            
            return {
                'success': True,
                'message': f'Live migration initiated for server "{instance_name}"' + (f' to host "{host}"' if host else '')
            }
            
        elif action.lower() == 'evacuate':
            host = kwargs.get('host')
            admin_pass = kwargs.get('admin_pass')
            on_shared_storage = kwargs.get('on_shared_storage', False)
            
            evacuate_params = {}
            if host:
                evacuate_params['host'] = host
            if admin_pass:
                evacuate_params['admin_pass'] = admin_pass
            # onSharedStorage exists only before compute microversion 2.14;
            # the SDK negotiates a newer microversion, where Nova rejects the
            # field. Send it only when explicitly requested (legacy clouds).
            if on_shared_storage:
                evacuate_params['on_shared_storage'] = True
            
            conn.compute.evacuate_server(server, **evacuate_params)
            
            return {
                'success': True,
                'message': f'Evacuation initiated for server "{instance_name}"' + (f' to host "{host}"' if host else '')
            }
            
        elif action.lower() == 'confirm':
            # This is for confirming resize, but can be extended for migration confirm
            conn.compute.confirm_server_resize(server)
            return {
                'success': True,
                'message': f'Migration/resize confirmed for server "{instance_name}"'
            }
            
        elif action.lower() == 'revert':
            # This is for reverting resize, but can be extended for migration revert
            conn.compute.revert_server_resize(server)
            return {
                'success': True,
                'message': f'Migration/resize reverted for server "{instance_name}"'
            }
            
        elif action.lower() == 'list':
            # List migrations for a specific server or all servers
            migrations = []
            try:
                if instance_name:
                    # Get migrations for specific server
                    for migration in conn.compute.server_migrations(server.id):
                        migrations.append({
                            'id': getattr(migration, 'id', 'unknown'),
                            'server_id': getattr(migration, 'server_id', server.id),
                            'status': getattr(migration, 'status', 'unknown'),
                            'migration_type': getattr(migration, 'migration_type', 'unknown'),
                            'source_node': getattr(migration, 'source_node', 'unknown'),
                            'dest_node': getattr(migration, 'dest_node', 'unknown'),
                            'created_at': str(getattr(migration, 'created_at', 'unknown')),
                            'updated_at': str(getattr(migration, 'updated_at', 'unknown'))
                        })
                else:
                    # Get all migrations (admin required)
                    for migration in conn.compute.migrations():
                        migrations.append({
                            'id': getattr(migration, 'id', 'unknown'),
                            'server_id': getattr(migration, 'server_id', None) or 'unknown',
                            'status': getattr(migration, 'status', 'unknown'),
                            'migration_type': getattr(migration, 'migration_type', 'unknown'),
                            'source_node': getattr(migration, 'source_node', 'unknown'),
                            'dest_node': getattr(migration, 'dest_node', 'unknown'),
                            'created_at': str(getattr(migration, 'created_at', 'unknown')),
                            'updated_at': str(getattr(migration, 'updated_at', 'unknown'))
                        })
            except Exception as e:
                logger.warning(f"Could not list migrations: {e}")
                return {
                    'success': False,
                    'message': f'Could not list migrations: {e}'
                }

            return {
                'success': True,
                'migrations': migrations,
                'count': len(migrations)
            }
            
        elif action.lower() == 'show':
            migration_id = kwargs.get('migration_id')
            if not migration_id:
                return {
                    'success': False,
                    'message': 'migration_id parameter is required for show action'
                }
            
            try:
                migration = conn.compute.get_server_migration(server.id, migration_id)
                return {
                    'success': True,
                    'migration': {
                        'id': getattr(migration, 'id', 'unknown'),
                        'server_id': getattr(migration, 'server_id', server.id),
                        'status': getattr(migration, 'status', 'unknown'),
                        'migration_type': getattr(migration, 'migration_type', 'unknown'),
                        'source_node': getattr(migration, 'source_node', 'unknown'),
                        'dest_node': getattr(migration, 'dest_node', 'unknown'),
                        'created_at': str(getattr(migration, 'created_at', 'unknown')),
                        'updated_at': str(getattr(migration, 'updated_at', 'unknown')),
                        'links': getattr(migration, 'links', [])
                    }
                }
            except Exception as e:
                return {
                    'success': False,
                    'message': f'Migration "{migration_id}" not found: {str(e)}'
                }
                
        elif action.lower() == 'abort':
            migration_id = kwargs.get('migration_id')
            if not migration_id:
                return {
                    'success': False,
                    'message': 'migration_id parameter is required for abort action'
                }
            
            try:
                conn.compute.abort_server_migration(server.id, migration_id)
                return {
                    'success': True,
                    'message': f'Migration "{migration_id}" aborted for server "{instance_name}"'
                }
            except Exception as e:
                return {
                    'success': False,
                    'message': f'Failed to abort migration "{migration_id}": {str(e)}'
                }
                
        elif action.lower() == 'force_complete':
            migration_id = kwargs.get('migration_id')
            if not migration_id:
                return {
                    'success': False,
                    'message': 'migration_id parameter is required for force_complete action'
                }
            
            try:
                conn.compute.force_complete_server_migration(server.id, migration_id)
                return {
                    'success': True,
                    'message': f'Migration "{migration_id}" force completed for server "{instance_name}"'
                }
            except Exception as e:
                return {
                    'success': False,
                    'message': f'Failed to force complete migration "{migration_id}": {str(e)}'
                }
        else:
            return {
                'success': False,
                'message': f'Unknown action "{action}". Supported: migrate, evacuate, confirm, revert, list, show, abort, force_complete'
            }
            
    except Exception as e:
        logger.error(f"Failed to manage server migration: {e}")
        return {
            'success': False,
            'message': f'Failed to manage server migration: {str(e)}',
            'error': str(e)
        }


def set_server_properties(instance_name: str, action: str, **kwargs) -> Dict[str, Any]:
    """
    Manage server properties and metadata (set, unset).
    
    Args:
        instance_name: Name or ID of the server
        action: Action to perform (set, unset)
        **kwargs: Additional parameters
        
    Returns:
        Result of the property operation
    """
    try:
        # Import here to avoid circular imports
        from ..connection import get_openstack_connection
        conn = get_openstack_connection()
        
        # Find the server
        server = None
        for srv in conn.compute.servers():
            if getattr(srv, 'name', '') == instance_name or srv.id == instance_name:
                server = srv
                break
        
        if not server:
            return {
                'success': False,
                'message': f'Server "{instance_name}" not found'
            }
        
        if action.lower() == 'set':
            # Server properties that can be updated
            update_params = {}
            
            if 'name' in kwargs:
                update_params['name'] = kwargs['name']
            if 'description' in kwargs:
                update_params['description'] = kwargs['description']
            
            # Metadata updates
            metadata_updates = kwargs.get('metadata', {})
            if not isinstance(metadata_updates, dict):
                return {
                    'success': False,
                    'message': 'metadata parameter must be a dictionary'
                }
            metadata_updates = metadata_updates.copy()
            
            # Individual property updates
            for key in kwargs:
                if key.startswith('property_'):
                    prop_name = key[9:]  # Remove 'property_' prefix
                    metadata_updates[prop_name] = kwargs[key]
            
            if not update_params and not metadata_updates:
                return {
                    'success': False,
                    'message': 'No properties to update. Specify name, description, metadata, or property_* parameters'
                }

            if update_params:
                conn.compute.update_server(server, **update_params)
            if metadata_updates:
                conn.compute.set_server_metadata(server, **metadata_updates)

            updated_fields = list(update_params.keys())
            if metadata_updates:
                updated_fields.append('metadata')
            return {
                'success': True,
                'message': f'Server "{instance_name}" properties updated: {", ".join(updated_fields)}'
            }
            
        elif action.lower() == 'unset':
            # Properties to unset
            unset_metadata = kwargs.get('metadata') or kwargs.get('properties', [])
            if isinstance(unset_metadata, str):
                unset_metadata = [unset_metadata]
            
            if not unset_metadata:
                return {
                    'success': False,
                    'message': 'No properties to unset. Specify metadata or properties parameter'
                }
            
            # Get current metadata
            current_metadata = getattr(server, 'metadata', {})
            
            # Remove specified keys
            removed_keys = []
            for key in unset_metadata:
                if key in current_metadata:
                    removed_keys.append(key)
            
            if not removed_keys:
                return {
                    'success': False,
                    'message': f'None of the specified properties were found: {unset_metadata}'
                }
            
            # Update server with new metadata
            conn.compute.delete_server_metadata(server, keys=removed_keys)
            
            return {
                'success': True,
                'message': f'Server "{instance_name}" properties unset: {", ".join(removed_keys)}'
            }
        else:
            return {
                'success': False,
                'message': f'Unknown action "{action}". Supported: set, unset'
            }
            
    except Exception as e:
        logger.error(f"Failed to manage server properties: {e}")
        return {
            'success': False,
            'message': f'Failed to manage server properties: {str(e)}',
            'error': str(e)
        }


def create_server_backup(instance_name: str, backup_name: str, **kwargs) -> Dict[str, Any]:
    """
    Create a backup image of a server.
    
    Args:
        instance_name: Name or ID of the server
        backup_name: Name for the backup image
        **kwargs: Additional parameters
        
    Returns:
        Result of the backup operation
    """
    try:
        # Import here to avoid circular imports
        from ..connection import get_openstack_connection
        conn = get_openstack_connection()
        
        # Find the server
        server = None
        for srv in conn.compute.servers():
            if getattr(srv, 'name', '') == instance_name or srv.id == instance_name:
                server = srv
                break
        
        if not server:
            return {
                'success': False,
                'message': f'Server "{instance_name}" not found'
            }
        
        backup_type = kwargs.get('backup_type', 'daily')
        rotation = kwargs.get('rotation', 1)
        
        conn.compute.backup_server(
            server,
            name=backup_name,
            backup_type=backup_type,
            rotation=rotation
        )
        
        return {
            'success': True,
            'message': f'Backup "{backup_name}" creation started for server "{instance_name}"',
            # Nova's backup action returns no image ID; inspect Glance by name.
            'backup_id': None,
            'backup_type': backup_type,
            'rotation': rotation
        }
        
    except Exception as e:
        logger.error(f"Failed to create server backup: {e}")
        return {
            'success': False,
            'message': f'Failed to create server backup: {str(e)}',
            'error': str(e)
        }


def create_server_dump(instance_name: str, **kwargs) -> Dict[str, Any]:
    """
    Create a dump file for a server (if supported by the compute driver).
    
    Args:
        instance_name: Name or ID of the server
        **kwargs: Additional parameters
        
    Returns:
        Result of the dump operation
    """
    try:
        # Import here to avoid circular imports
        from ..connection import get_openstack_connection
        conn = get_openstack_connection()
        
        # Find the server
        server = None
        for srv in conn.compute.servers():
            if getattr(srv, 'name', '') == instance_name or srv.id == instance_name:
                server = srv
                break
        
        if not server:
            return {
                'success': False,
                'message': f'Server "{instance_name}" not found'
            }
        
        # Note: Server dump is not directly supported by OpenStack SDK
        # This would typically require direct API calls or vendor-specific implementations
        return {
            'success': False,
            'message': 'Server dump creation is not supported by the current OpenStack SDK. This feature requires vendor-specific implementation.',
            'note': 'Consider using server backup or snapshot instead'
        }
        
    except Exception as e:
        logger.error(f"Failed to create server dump: {e}")
        return {
            'success': False,
            'message': f'Failed to create server dump: {str(e)}',
            'error': str(e)
        }
