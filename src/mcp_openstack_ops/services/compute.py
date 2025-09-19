"""
OpenStack Compute (Nova) Service Functions

This module contains functions for managing instances, flavors, server groups,
server events, and other compute-related components.
"""

import logging
from typing import Dict, List, Any, Optional

# Configure logging
logger = logging.getLogger(__name__)


def get_instance_details(
    instance_names: Optional[List[str]] = None,
    limit: int = 50,
    offset: int = 0,
    include_all: bool = False
) -> Dict[str, Any]:
    """
    Get detailed information about OpenStack instances with pagination support.
    
    Args:
        instance_names: List of instance names to filter (optional)
        limit: Maximum number of instances to return (default: 50, max: 200)
        offset: Number of instances to skip for pagination (default: 0)
        include_all: If True, return all instances ignoring limit (default: False)
    
    Returns:
        Dictionary containing instances and metadata
    """
    try:
        # Import here to avoid circular imports
        from ..connection import get_openstack_connection
        conn = get_openstack_connection()
        
        # Validate and sanitize inputs
        if limit > 200:
            limit = 200
        if limit < 1:
            limit = 1
        if offset < 0:
            offset = 0
        
        instances = []
        all_servers = list(conn.compute.servers(details=True))
        
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
                # Get server flavor details
                flavor_info = {'id': 'unknown', 'name': 'unknown', 'vcpus': 0, 'ram': 0, 'disk': 0}
                if hasattr(server, 'flavor') and server.flavor:
                    if isinstance(server.flavor, dict):
                        flavor_id = server.flavor.get('id')
                    else:
                        flavor_id = getattr(server.flavor, 'id', None)
                    
                    if flavor_id:
                        try:
                            flavor = conn.compute.get_flavor(flavor_id)
                            flavor_info = {
                                'id': flavor.id,
                                'name': getattr(flavor, 'name', 'unknown'),
                                'vcpus': getattr(flavor, 'vcpus', 0),
                                'ram': getattr(flavor, 'ram', 0),
                                'disk': getattr(flavor, 'disk', 0)
                            }
                        except Exception as e:
                            logger.warning(f"Could not get flavor details for {flavor_id}: {e}")
                
                # Get server image details
                image_info = {'id': 'unknown', 'name': 'unknown'}
                if hasattr(server, 'image') and server.image:
                    if isinstance(server.image, dict):
                        image_id = server.image.get('id')
                    else:
                        image_id = getattr(server.image, 'id', None)
                    
                    if image_id:
                        try:
                            image = conn.image.get_image(image_id)
                            image_info = {
                                'id': image.id,
                                'name': getattr(image, 'name', 'unknown')
                            }
                        except Exception as e:
                            logger.warning(f"Could not get image details for {image_id}: {e}")
                
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
                    'key_name': getattr(server, 'key_name', None),
                    'networks': networks,
                    'security_groups': security_groups,
                    'tenant_id': getattr(server, 'tenant_id', getattr(server, 'project_id', 'unknown')),
                    'user_id': getattr(server, 'user_id', 'unknown'),
                    'metadata': getattr(server, 'metadata', {}),
                    'fault': getattr(server, 'fault', None),
                    'progress': getattr(server, 'progress', 0),
                    'config_drive': getattr(server, 'config_drive', False),
                    'locked': getattr(server, 'locked', False)
                }
                
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
            
        return result
        
    except Exception as e:
        logger.error(f"Failed to get instance details: {e}")
        return {
            'instances': [],
            'count': 0,
            'total_count': 0,
            'error': str(e),
            'success': False
        }


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


def search_instances(
    search_term: str,
    search_fields: Optional[List[str]] = None,
    limit: int = 50,
    include_inactive: bool = False
) -> List[Dict[str, Any]]:
    """
    Search for instances by various fields.
    
    Args:
        search_term: Term to search for
        search_fields: Fields to search in (default: name, id)
        limit: Maximum results to return
        include_inactive: Include non-active instances
        
    Returns:
        List of matching instances
    """
    try:
        # Import here to avoid circular imports
        from ..connection import get_openstack_connection
        conn = get_openstack_connection()
        
        if search_fields is None:
            search_fields = ['name', 'id']
        
        matching_instances = []
        all_instances_result = get_instance_details(limit=limit*2, include_all=True)
        all_instances = all_instances_result.get('instances', [])
        
        search_term_lower = search_term.lower()
        
        for instance in all_instances:
            # Skip inactive instances if not requested
            if not include_inactive and instance.get('status', '').lower() not in ['active', 'running']:
                continue
                
            match_found = False
            
            for field in search_fields:
                field_value = str(instance.get(field, '')).lower()
                if search_term_lower in field_value:
                    match_found = True
                    break
                    
                # Special handling for nested fields
                if field == 'ip':
                    for network in instance.get('networks', []):
                        for addr in network.get('addresses', []):
                            if search_term_lower in addr.get('addr', '').lower():
                                match_found = True
                                break
                        if match_found:
                            break
                elif field == 'flavor_name':
                    flavor = instance.get('flavor', {})
                    if search_term_lower in str(flavor.get('name', '')).lower():
                        match_found = True
                elif field == 'image_name':
                    image = instance.get('image', {})
                    if search_term_lower in str(image.get('name', '')).lower():
                        match_found = True
            
            if match_found:
                matching_instances.append(instance)
                
            if len(matching_instances) >= limit:
                break
        
        return matching_instances
        
    except Exception as e:
        logger.error(f"Failed to search instances: {e}")
        return []


def get_instances_by_status(status: str) -> List[Dict[str, Any]]:
    """
    Get instances filtered by status.
    
    Args:
        status: Status to filter by (ACTIVE, SHUTOFF, ERROR, etc.)
        
    Returns:
        List of instances with matching status
    """
    try:
        result = get_instance_details(include_all=True)
        instances = result.get('instances', [])
        
        status_lower = status.lower()
        return [
            instance for instance in instances 
            if instance.get('status', '').lower() == status_lower
        ]
        
    except Exception as e:
        logger.error(f"Failed to get instances by status: {e}")
        return []


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
        from ..connection import get_openstack_connection
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
            
            if not flavor_name:
                return {
                    'success': False,
                    'message': 'flavor parameter is required for create action'
                }
                
            if not image_name:
                return {
                    'success': False,
                    'message': 'image parameter is required for create action'
                }
            
            # Find flavor
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
            
            # Handle networks
            networks = []
            if network_names:
                if isinstance(network_names, str):
                    network_names = [network_names]
                    
                for network_name in network_names:
                    network = None
                    for net in conn.network.networks():
                        if getattr(net, 'name', '') == network_name or net.id == network_name:
                            network = net
                            break
                    
                    if network:
                        networks.append({'uuid': network.id})
                    else:
                        logger.warning(f"Network '{network_name}' not found, skipping")
            
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
                'image_id': image.id
            }
            
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
            
            server = conn.compute.create_server(**create_params)
            
            return {
                'success': True,
                'message': f'Instance "{instance_name}" creation started',
                'instance': {
                    'id': server.id,
                    'name': getattr(server, 'name', 'unnamed'),
                    'status': getattr(server, 'status', 'unknown'),
                    'flavor': {'id': flavor.id, 'name': getattr(flavor, 'name', 'unknown')},
                    'image': {'id': image.id, 'name': getattr(image, 'name', 'unknown')}
                }
            }
            
        # Find existing instance for other actions
        server = None
        for srv in conn.compute.servers():
            if getattr(srv, 'name', '') == instance_name or srv.id == instance_name:
                server = srv
                break
        
        if not server:
            return {
                'success': False,
                'message': f'Instance "{instance_name}" not found'
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
                conn.compute.force_delete_server(server)
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
            console_type = kwargs.get('type', 'novnc')  # novnc, xvpvnc, spice-html5, rdp-html5, serial
            
            try:
                console = conn.compute.get_server_console_url(server, console_type)
                return {
                    'success': True,
                    'console': {
                        'type': console_type,
                        'url': console.get('url', 'unknown')
                    }
                }
            except Exception as e:
                return {
                    'success': False,
                    'message': f'Failed to get console URL: {str(e)}'
                }
                
        else:
            return {
                'success': False,
                'message': f'Unknown action "{action}". Supported: create, start, stop, reboot, pause, unpause, suspend, resume, delete, resize, confirm_resize, revert_resize, snapshot, console, list'
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
        return [
            {
                'id': 'flavor-1', 'name': 'demo-flavor', 'vcpus': 1, 'ram': 512, 
                'disk': 1, 'is_public': True, 'error': str(e)
            }
        ]


def get_server_events(instance_name: str, limit: int = 50) -> Dict[str, Any]:
    """
    Get server action/event history.
    
    Args:
        instance_name: Name or ID of the server
        limit: Maximum number of events to return
        
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
        try:
            # Get server actions (events)
            for action in conn.compute.server_actions(server.id):
                event_data = {
                    'action': getattr(action, 'action', 'unknown'),
                    'instance_uuid': getattr(action, 'instance_uuid', server.id),
                    'request_id': getattr(action, 'request_id', 'unknown'),
                    'user_id': getattr(action, 'user_id', 'unknown'),
                    'project_id': getattr(action, 'project_id', 'unknown'),
                    'start_time': str(getattr(action, 'start_time', 'unknown')),
                    'finish_time': str(getattr(action, 'finish_time', None)) if getattr(action, 'finish_time', None) else None,
                    'message': getattr(action, 'message', ''),
                    'details': getattr(action, 'details', {})
                }
                
                # Add events for this action if available
                if hasattr(action, 'events'):
                    action_events = []
                    for event in getattr(action, 'events', []):
                        action_events.append({
                            'event': getattr(event, 'event', 'unknown'),
                            'start_time': str(getattr(event, 'start_time', 'unknown')),
                            'finish_time': str(getattr(event, 'finish_time', None)) if getattr(event, 'finish_time', None) else None,
                            'result': getattr(event, 'result', 'unknown'),
                            'traceback': getattr(event, 'traceback', None)
                        })
                    event_data['events'] = action_events
                
                events.append(event_data)
                
                if len(events) >= limit:
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
            'count': len(events)
        }
        
    except Exception as e:
        logger.error(f"Failed to get server events: {e}")
        return {
            'success': False,
            'message': f'Failed to get server events for "{instance_name}": {str(e)}',
            'events': [],
            'error': str(e)
        }


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
                members = getattr(group, 'members', []) or []
                
                server_groups.append({
                    'id': group.id,
                    'name': getattr(group, 'name', 'unnamed'),
                    'policies': list(getattr(group, 'policies', [])),
                    'members': list(members),
                    'member_count': len(members),
                    'metadata': getattr(group, 'metadata', {}),
                    'project_id': getattr(group, 'project_id', 'unknown'),
                    'user_id': getattr(group, 'user_id', 'unknown'),
                    'created_at': str(getattr(group, 'created_at', 'unknown')),
                    'updated_at': str(getattr(group, 'updated_at', 'unknown'))
                })
        except Exception as e:
            logger.warning(f"Server groups may not be supported: {e}")
            return []
        
        return server_groups
    except Exception as e:
        logger.error(f"Failed to get server groups: {e}")
        return []


def set_server_group(group_name: str, action: str, **kwargs) -> Dict[str, Any]:
    """
    Manage server groups.
    
    Args:
        group_name: Name of the server group
        action: Action to perform (list, create, delete, show)
        **kwargs: Additional parameters
        
    Returns:
        Result of the server group operation
    """
    try:
        # Import here to avoid circular imports
        from ..connection import get_openstack_connection
        conn = get_openstack_connection()
        
        if action.lower() == 'list':
            server_groups = get_server_groups()
            return {
                'success': True,
                'server_groups': server_groups,
                'count': len(server_groups)
            }
            
        elif action.lower() == 'create':
            policies = kwargs.get('policies', ['anti-affinity'])
            if isinstance(policies, str):
                policies = [policies]
            
            try:
                group = conn.compute.create_server_group(
                    name=group_name,
                    policies=policies
                )
                
                return {
                    'success': True,
                    'message': f'Server group "{group_name}" created',
                    'server_group': {
                        'id': group.id,
                        'name': getattr(group, 'name', 'unnamed'),
                        'policies': list(getattr(group, 'policies', [])),
                        'members': []
                    }
                }
            except Exception as e:
                return {
                    'success': False,
                    'message': f'Failed to create server group: {str(e)}'
                }
                
        elif action.lower() == 'delete':
            # Find the server group
            server_group = None
            for group in conn.compute.server_groups():
                if getattr(group, 'name', '') == group_name or group.id == group_name:
                    server_group = group
                    break
            
            if not server_group:
                return {
                    'success': False,
                    'message': f'Server group "{group_name}" not found'
                }
            
            try:
                conn.compute.delete_server_group(server_group)
                return {
                    'success': True,
                    'message': f'Server group "{group_name}" deleted'
                }
            except Exception as e:
                return {
                    'success': False,
                    'message': f'Failed to delete server group: {str(e)}'
                }
                
        elif action.lower() == 'show':
            # Find and show specific server group
            server_group = None
            for group in conn.compute.server_groups():
                if getattr(group, 'name', '') == group_name or group.id == group_name:
                    server_group = group
                    break
            
            if not server_group:
                return {
                    'success': False,
                    'message': f'Server group "{group_name}" not found'
                }
            
            members = getattr(server_group, 'members', []) or []
            return {
                'success': True,
                'server_group': {
                    'id': server_group.id,
                    'name': getattr(server_group, 'name', 'unnamed'),
                    'policies': list(getattr(server_group, 'policies', [])),
                    'members': list(members),
                    'member_count': len(members),
                    'metadata': getattr(server_group, 'metadata', {}),
                    'project_id': getattr(server_group, 'project_id', 'unknown'),
                    'user_id': getattr(server_group, 'user_id', 'unknown'),
                    'created_at': str(getattr(server_group, 'created_at', 'unknown')),
                    'updated_at': str(getattr(server_group, 'updated_at', 'unknown'))
                }
            }
            
        else:
            return {
                'success': False,
                'message': f'Unknown action "{action}". Supported: list, create, delete, show'
            }
            
    except Exception as e:
        logger.error(f"Failed to manage server group: {e}")
        return {
            'success': False,
            'message': f'Failed to manage server group: {str(e)}',
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