"""
OpenStack Storage (Cinder) Service Functions

This module contains functions for managing volumes, snapshots, backups,
volume types, and other storage-related components.
"""

import logging
from typing import Dict, List, Any, Optional

# Configure logging
logger = logging.getLogger(__name__)


def get_volume_list() -> List[Dict[str, Any]]:
    """
    Get list of volumes with detailed information for current project.
    
    Returns:
        List of volume dictionaries for current project
    """
    try:
        # Import here to avoid circular imports
        from ..connection import get_openstack_connection, get_current_project_id, validate_resource_ownership
        conn = get_openstack_connection()
        current_project_id = get_current_project_id()
        volumes = []
        
        for volume in conn.volume.volumes():
            # Enhanced project validation using utility functions
            if validate_resource_ownership(volume, "Volume"):
                # Get attachment information
                attachments = []
                for attachment in getattr(volume, 'attachments', []):
                    attachments.append({
                        'server_id': attachment.get('server_id', 'unknown'),
                        'attachment_id': attachment.get('attachment_id', 'unknown'),
                        'device': attachment.get('device', 'unknown'),
                        'attached_at': attachment.get('attached_at', 'unknown')
                    })
                
                volumes.append({
                    'id': volume.id,
                    'name': getattr(volume, 'name', 'unnamed'),
                    'status': getattr(volume, 'status', 'unknown'),
                    'size': getattr(volume, 'size', 0),
                    'volume_type': getattr(volume, 'volume_type', 'unknown'),
                    'bootable': getattr(volume, 'is_bootable', False),
                    'encrypted': getattr(volume, 'is_encrypted', False),
                    'multiattach': getattr(volume, 'multiattach', False),
                    'availability_zone': getattr(volume, 'availability_zone', 'unknown'),
                    'project_id': getattr(volume, 'project_id', current_project_id),
                    'created_at': str(getattr(volume, 'created_at', 'unknown')),
                    'updated_at': str(getattr(volume, 'updated_at', 'unknown')),
                    'description': getattr(volume, 'description', ''),
                    'metadata': getattr(volume, 'metadata', {}),
                    'source_volid': getattr(volume, 'source_volid', None),
                    'snapshot_id': getattr(volume, 'snapshot_id', None),
                    'image_id': getattr(volume, 'image_id', None),
                    'attachments': attachments,
                    'attachment_count': len(attachments)
                })
        
        logger.info(f"Retrieved {len(volumes)} volumes for project {current_project_id}")
        return volumes
    except Exception as e:
        logger.error(f"Failed to get volume list: {e}")
        return [
            {
                'id': 'vol-1', 'name': 'demo-volume', 'status': 'available',
                'size': 10, 'volume_type': 'unknown', 'attachments': [], 'error': str(e)
            }
        ]


def set_volume(volume_name: str, action: str, **kwargs) -> Dict[str, Any]:
    """
    Manage volumes (create, delete, extend, attach, detach, snapshot).
    
    Args:
        volume_name: Name of the volume
        action: Action to perform
        **kwargs: Additional parameters depending on action
    
    Returns:
        Result of the volume operation
    """
    try:
        # Import here to avoid circular imports
        from ..connection import get_openstack_connection
        conn = get_openstack_connection()
        
        if action.lower() == 'list':
            volumes = []
            for volume in conn.volume.volumes():
                volumes.append({
                    'id': volume.id,
                    'name': getattr(volume, 'name', 'unnamed'),
                    'status': getattr(volume, 'status', 'unknown'),
                    'size': getattr(volume, 'size', 0),
                    'volume_type': getattr(volume, 'volume_type', 'unknown'),
                    'bootable': getattr(volume, 'is_bootable', False)
                })
            return {
                'success': True,
                'volumes': volumes,
                'count': len(volumes)
            }
            
        elif action.lower() == 'create':
            size = kwargs.get('size', 1)
            volume_type = kwargs.get('volume_type', kwargs.get('type'))
            description = kwargs.get('description', '')
            image_id = kwargs.get('image_id', kwargs.get('image'))
            snapshot_id = kwargs.get('snapshot_id', kwargs.get('snapshot'))
            availability_zone = kwargs.get('availability_zone', kwargs.get('az'))
            
            create_params = {
                'name': volume_name,
                'size': int(size),
                'description': description
            }
            
            if volume_type:
                create_params['volume_type'] = volume_type
            if image_id:
                create_params['image_id'] = image_id
            if snapshot_id:
                create_params['snapshot_id'] = snapshot_id
            if availability_zone:
                create_params['availability_zone'] = availability_zone
            
            volume = conn.volume.create_volume(**create_params)
            
            return {
                'success': True,
                'message': f'Volume "{volume_name}" created successfully',
                'volume': {
                    'id': volume.id,
                    'name': getattr(volume, 'name', 'unnamed'),
                    'status': getattr(volume, 'status', 'unknown'),
                    'size': getattr(volume, 'size', 0),
                    'volume_type': getattr(volume, 'volume_type', 'unknown')
                }
            }
            
        elif action.lower() == 'delete':
            # Find the volume using secure project-scoped lookup
            from ..connection import find_resource_by_name_or_id, get_openstack_connection
            conn = get_openstack_connection()
            
            volume = find_resource_by_name_or_id(
                conn.volume.volumes(), 
                volume_name, 
                "Volume"
            )

            if not volume:
                return {
                    'success': False,
                    'message': f'Volume "{volume_name}" not found or not accessible in current project'
                }
            
            # Check if volume is attached
            if getattr(volume, 'attachments', []):
                force = kwargs.get('force', False)
                if not force:
                    return {
                        'success': False,
                        'message': f'Volume "{volume_name}" is attached. Use force=True to delete anyway'
                    }
            
            conn.volume.delete_volume(volume, force=kwargs.get('force', False))
            
            return {
                'success': True,
                'message': f'Volume "{volume_name}" deleted successfully'
            }
            
        elif action.lower() == 'extend':
            new_size = kwargs.get('size', kwargs.get('new_size'))
            if not new_size:
                return {
                    'success': False,
                    'message': 'size parameter is required for extend action'
                }
            
            # Find the volume
            volume = None
            for vol in conn.volume.volumes():
                if getattr(vol, 'name', '') == volume_name or vol.id == volume_name:
                    volume = vol
                    break
            
            if not volume:
                return {
                    'success': False,
                    'message': f'Volume "{volume_name}" not found'
                }
            
            current_size = getattr(volume, 'size', 0)
            new_size = int(new_size)
            
            if new_size <= current_size:
                return {
                    'success': False,
                    'message': f'New size ({new_size}GB) must be greater than current size ({current_size}GB)'
                }
            
            conn.volume.extend_volume(volume, size=new_size)
            
            return {
                'success': True,
                'message': f'Volume "{volume_name}" extended from {current_size}GB to {new_size}GB'
            }
            
        elif action.lower() == 'attach':
            instance_id = kwargs.get('instance_id', kwargs.get('server_id'))
            device = kwargs.get('device')
            
            if not instance_id:
                return {
                    'success': False,
                    'message': 'instance_id parameter is required for attach action'
                }
            
            # Find the volume
            volume = None
            for vol in conn.volume.volumes():
                if getattr(vol, 'name', '') == volume_name or vol.id == volume_name:
                    volume = vol
                    break
            
            if not volume:
                return {
                    'success': False,
                    'message': f'Volume "{volume_name}" not found'
                }
            
            attach_params = {'server_id': instance_id}
            if device:
                attach_params['device'] = device
            
            conn.compute.create_volume_attachment(volume.id, **attach_params)
            
            return {
                'success': True,
                'message': f'Volume "{volume_name}" attached to instance "{instance_id}"'
            }
            
        elif action.lower() == 'detach':
            # Find the volume
            volume = None
            for vol in conn.volume.volumes():
                if getattr(vol, 'name', '') == volume_name or vol.id == volume_name:
                    volume = vol
                    break
            
            if not volume:
                return {
                    'success': False,
                    'message': f'Volume "{volume_name}" not found'
                }
            
            attachments = getattr(volume, 'attachments', [])
            if not attachments:
                return {
                    'success': False,
                    'message': f'Volume "{volume_name}" is not attached'
                }
            
            # Detach from all servers
            for attachment in attachments:
                server_id = attachment.get('server_id')
                if server_id:
                    conn.compute.delete_volume_attachment(volume.id, server_id)
            
            return {
                'success': True,
                'message': f'Volume "{volume_name}" detached successfully'
            }
            
        elif action.lower() == 'snapshot':
            snapshot_name = kwargs.get('snapshot_name', f'{volume_name}-snapshot')
            description = kwargs.get('description', f'Snapshot of {volume_name}')
            force = kwargs.get('force', False)
            
            # Find the volume
            volume = None
            for vol in conn.volume.volumes():
                if getattr(vol, 'name', '') == volume_name or vol.id == volume_name:
                    volume = vol
                    break
            
            if not volume:
                return {
                    'success': False,
                    'message': f'Volume "{volume_name}" not found'
                }
            
            snapshot = conn.volume.create_snapshot(
                volume_id=volume.id,
                name=snapshot_name,
                description=description,
                force=force
            )
            
            return {
                'success': True,
                'message': f'Snapshot "{snapshot_name}" created successfully',
                'snapshot': {
                    'id': snapshot.id,
                    'name': getattr(snapshot, 'name', 'unnamed'),
                    'status': getattr(snapshot, 'status', 'unknown'),
                    'volume_id': getattr(snapshot, 'volume_id', 'unknown')
                }
            }
            
        else:
            return {
                'success': False,
                'message': f'Unknown action "{action}". Supported: create, delete, extend, attach, detach, snapshot, list'
            }
            
    except Exception as e:
        logger.error(f"Failed to manage volume: {e}")
        return {
            'success': False,
            'message': f'Failed to manage volume: {str(e)}',
            'error': str(e)
        }


def get_volume_types() -> List[Dict[str, Any]]:
    """
    Get list of volume types.
    
    Returns:
        List of volume type dictionaries
    """
    try:
        # Import here to avoid circular imports
        from ..connection import get_openstack_connection
        conn = get_openstack_connection()
        volume_types = []
        
        for vol_type in conn.volume.types():
            volume_types.append({
                'id': vol_type.id,
                'name': getattr(vol_type, 'name', 'unnamed'),
                'description': getattr(vol_type, 'description', ''),
                'is_public': getattr(vol_type, 'is_public', True),
                'extra_specs': getattr(vol_type, 'extra_specs', {}),
                'created_at': str(getattr(vol_type, 'created_at', 'unknown')),
                'updated_at': str(getattr(vol_type, 'updated_at', 'unknown'))
            })
        
        return volume_types
    except Exception as e:
        logger.error(f"Failed to get volume types: {e}")
        return [
            {
                'id': 'type-1', 'name': 'standard', 'description': 'Standard volume type',
                'is_public': True, 'extra_specs': {}, 'error': str(e)
            }
        ]


def get_volume_snapshots() -> List[Dict[str, Any]]:
    """
    Get list of volume snapshots for current project.
    
    Returns:
        List of snapshot dictionaries for current project
    """
    try:
        # Import here to avoid circular imports
        from ..connection import get_openstack_connection
        conn = get_openstack_connection()
        current_project_id = conn.current_project_id
        snapshots = []
        
        for snapshot in conn.volume.snapshots():
            # Filter by current project
            snapshot_project_id = getattr(snapshot, 'project_id', None)
            if snapshot_project_id == current_project_id:
                snapshots.append({
                    'id': snapshot.id,
                    'name': getattr(snapshot, 'name', 'unnamed'),
                    'description': getattr(snapshot, 'description', ''),
                    'status': getattr(snapshot, 'status', 'unknown'),
                    'size': getattr(snapshot, 'size', 0),
                    'volume_id': getattr(snapshot, 'volume_id', 'unknown'),
                    'project_id': snapshot_project_id,
                    'created_at': str(getattr(snapshot, 'created_at', 'unknown')),
                    'updated_at': str(getattr(snapshot, 'updated_at', 'unknown')),
                    'metadata': getattr(snapshot, 'metadata', {})
                })
        
        logger.info(f"Retrieved {len(snapshots)} snapshots for project {current_project_id}")
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
    Manage volume snapshots (create, delete, restore).
    
    Args:
        snapshot_name: Name of the snapshot
        action: Action to perform
        **kwargs: Additional parameters
    
    Returns:
        Result of the snapshot operation
    """
    try:
        # Import here to avoid circular imports
        from ..connection import get_openstack_connection
        conn = get_openstack_connection()
        
        if action.lower() == 'list':
            snapshots = []
            for snapshot in conn.volume.snapshots():
                snapshots.append({
                    'id': snapshot.id,
                    'name': getattr(snapshot, 'name', 'unnamed'),
                    'status': getattr(snapshot, 'status', 'unknown'),
                    'size': getattr(snapshot, 'size', 0),
                    'volume_id': getattr(snapshot, 'volume_id', 'unknown')
                })
            return {
                'success': True,
                'snapshots': snapshots,
                'count': len(snapshots)
            }
            
        elif action.lower() == 'create':
            volume_id = kwargs.get('volume_id')
            description = kwargs.get('description', f'Snapshot {snapshot_name}')
            force = kwargs.get('force', False)
            
            if not volume_id:
                return {
                    'success': False,
                    'message': 'volume_id is required for create action'
                }
            
            snapshot = conn.volume.create_snapshot(
                volume_id=volume_id,
                name=snapshot_name,
                description=description,
                force=force
            )
            
            return {
                'success': True,
                'message': f'Snapshot "{snapshot_name}" created successfully',
                'snapshot': {
                    'id': snapshot.id,
                    'name': getattr(snapshot, 'name', 'unnamed'),
                    'status': getattr(snapshot, 'status', 'unknown'),
                    'volume_id': getattr(snapshot, 'volume_id', 'unknown')
                }
            }
            
        elif action.lower() == 'delete':
            # Find the snapshot
            snapshot = None
            for snap in conn.volume.snapshots():
                if getattr(snap, 'name', '') == snapshot_name or snap.id == snapshot_name:
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
                'message': f'Snapshot "{snapshot_name}" deleted successfully'
            }
            
        elif action.lower() == 'restore':
            volume_name = kwargs.get('volume_name', kwargs.get('name'))
            volume_size = kwargs.get('volume_size', kwargs.get('size'))
            
            if not volume_name:
                return {
                    'success': False,
                    'message': 'volume_name is required for restore action'
                }
            
            # Find the snapshot
            snapshot = None
            for snap in conn.volume.snapshots():
                if getattr(snap, 'name', '') == snapshot_name or snap.id == snapshot_name:
                    snapshot = snap
                    break
            
            if not snapshot:
                return {
                    'success': False,
                    'message': f'Snapshot "{snapshot_name}" not found'
                }
            
            create_params = {
                'name': volume_name,
                'size': volume_size or getattr(snapshot, 'size', 1),
                'snapshot_id': snapshot.id
            }
            
            volume = conn.volume.create_volume(**create_params)
            
            return {
                'success': True,
                'message': f'Volume "{volume_name}" created from snapshot "{snapshot_name}"',
                'volume': {
                    'id': volume.id,
                    'name': getattr(volume, 'name', 'unnamed'),
                    'status': getattr(volume, 'status', 'unknown'),
                    'size': getattr(volume, 'size', 0)
                }
            }
            
        else:
            return {
                'success': False,
                'message': f'Unknown action "{action}". Supported: create, delete, restore, list'
            }
            
    except Exception as e:
        logger.error(f"Failed to manage snapshot: {e}")
        return {
            'success': False,
            'message': f'Failed to manage snapshot: {str(e)}',
            'error': str(e)
        }


def set_volume_backups(action: str, backup_name: Optional[str] = None, **kwargs) -> Dict[str, Any]:
    """List, create, show, delete or restore real Cinder backups."""
    from ..connection import get_openstack_connection

    try:
        action = action.lower()
        if action not in {'list', 'create', 'show', 'delete', 'restore'}:
            raise ValueError('Supported actions: list, create, show, delete, restore')
        if action != 'list' and not (backup_name and backup_name.strip()):
            raise ValueError('backup_name is required')
        api = get_openstack_connection().block_storage
        if action == 'list':
            backups = [b.to_dict() for b in api.backups()]
            return {'success': True, 'backups': backups, 'count': len(backups)}
        if action == 'create':
            if not kwargs.get('volume_id'):
                raise ValueError('volume_id is required for create')
            backup = api.create_backup(
                volume_id=kwargs['volume_id'], name=backup_name,
                description=kwargs.get('description', ''),
                is_incremental=kwargs.get('incremental', False),
                force=kwargs.get('force', False),
            )
            return {'success': True, 'backup': backup.to_dict(),
                    'message': 'Backup creation accepted; check status before use'}
        backup = api.find_backup(backup_name, ignore_missing=False)
        if action == 'show':
            return {'success': True, 'backup': backup.to_dict()}
        if action == 'delete':
            api.delete_backup(backup, ignore_missing=False)
            return {'success': True, 'message': 'Backup deletion accepted'}
        restored = api.restore_backup(
            backup, volume_id=kwargs.get('volume_id'),
                name=kwargs.get('volume_name') or None,
        )
        return {'success': True, 'restore': restored.to_dict(),
                'message': 'Backup restoration accepted; check status before use'}
    except Exception as exc:
        return {'success': False, 'message': 'Backup operation failed',
            'error': str(exc)}


def set_volume_groups(action: str, group_name: Optional[str] = None, **kwargs) -> Dict[str, Any]:
    """List, create, show or delete Cinder generic volume groups (API >= 3.13)."""
    from ..connection import get_openstack_connection

    try:
        action = action.lower()
        if action not in {'list', 'create', 'show', 'delete'}:
            raise ValueError('Supported actions: list, create, show, delete')
        if action != 'list' and not (group_name and group_name.strip()):
            raise ValueError('group_name is required')
        conn = get_openstack_connection()
        api = conn.block_storage
        if action == 'list':
            groups = [g.to_dict() for g in api.groups()]
            return {'success': True, 'groups': groups, 'count': len(groups)}
        if action == 'create':
            volume_types = kwargs.get('volume_types') or []
            if not volume_types:
                raise ValueError('At least one volume_type is required')
            group_type = api.find_group_type(kwargs.get('group_type', 'default'),
                ignore_missing=False)
            types = [api.find_type(t, ignore_missing=False).id for t in volume_types]
            attrs = {'name': group_name, 'group_type': group_type.id,
                     'volume_types': types, 'description': kwargs.get('description',
                         '')}
            if kwargs.get('availability_zone'):
                attrs['availability_zone'] = kwargs['availability_zone']
            group = api.create_group(**attrs)
            return {'success': True, 'group': group.to_dict(),
                    'message': 'Group creation accepted; check status before use'}
        # Cinder group details may omit project_id on older microversions;
        # the default listing is scoped to the authenticated project by Cinder.
        groups = list(api.groups())
        matches = [g for g in groups if g.id == group_name]
        if not matches:
            matches = [g for g in groups if g.name == group_name]
        if len(matches) != 1:
            raise ValueError('Group not found or name is ambiguous; use an ID')
        group = matches[0]
        if action == 'show':
            return {'success': True, 'group': api.get_group(group.id).to_dict()}
        api.delete_group(group, delete_volumes=kwargs.get('delete_volumes', False))
        return {'success': True, 'message': 'Group deletion accepted'}
    except Exception as exc:
        return {'success': False, 'message': 'Volume group operation failed',
            'error': str(exc)}


def set_volume_qos(action: str, qos_name: Optional[str] = None, **kwargs) -> Dict[str, Any]:
    """Manage Cinder QoS specifications through its authenticated REST proxy."""
    from urllib.parse import quote
    from ..connection import get_openstack_connection

    try:
        action = action.lower()
        if action not in {'list', 'create', 'show', 'delete', 'set'}:
            raise ValueError('Supported actions: list, create, show, delete, set')
        if action != 'list' and not (qos_name and qos_name.strip()):
            raise ValueError('qos_name is required')
        specs = kwargs.get('specs', {})
        if not isinstance(specs, dict):
            raise ValueError('specs must be a JSON object')
        if {'name', 'consumer'} & specs.keys():
            raise ValueError('Use qos_name/consumer instead of reserved spec keys')
        api = get_openstack_connection().block_storage
        if action == 'create':
            consumer = kwargs.get('consumer', 'back-end')
            if consumer not in {'front-end', 'back-end', 'both'}:
                raise ValueError('Invalid consumer')
            response = api.post('/qos-specs', json={
                'qos_specs': {**specs, 'name': qos_name, 'consumer': consumer},
            })
            response.raise_for_status()
            return {'success': True, 'qos_policy': response.json()['qos_specs']}
        response = api.get('/qos-specs')
        response.raise_for_status()
        policies = response.json()['qos_specs']
        if action == 'list':
            return {'success': True, 'qos_policies': policies, 'count': len(policies)}
        matches = [q for q in policies if q['id'] == qos_name]
        if not matches:
            matches = [q for q in policies if q['name'] == qos_name]
        if len(matches) != 1:
            raise ValueError(
                'QoS specification not found or name is ambiguous; use an ID')
        path = '/qos-specs/' + quote(matches[0]['id'], safe='')
        if action == 'delete':
            response = api.delete(path, params={'force': str(kwargs.get('force',
                False)).lower()})
            response.raise_for_status()
            return {'success': True, 'message': 'QoS deletion accepted'}
        if action == 'set':
            response = api.put(path, json={'qos_specs': specs})
        else:
            response = api.get(path)
        response.raise_for_status()
        return {'success': True, 'qos_policy': response.json()['qos_specs']}
    except Exception as exc:
        return {'success': False, 'message': 'Volume QoS operation failed',
            'error': str(exc)}


def get_server_volumes(instance_name: str) -> List[Dict[str, Any]]:
    """
    Get volumes attached to a specific server/instance.
    
    Args:
        instance_name: Name or ID of the server
        
    Returns:
        List of attached volumes
    """
    try:
        # Import here to avoid circular imports
        from ..connection import get_openstack_connection
        conn = get_openstack_connection()
        
        # Find the server first
        server = None
        for srv in conn.compute.servers():
            if getattr(srv, 'name', '') == instance_name or srv.id == instance_name:
                server = srv
                break
        
        if not server:
            return []
        
        attached_volumes = []
        
        # Get volume attachments for this server
        try:
            for attachment in conn.compute.volume_attachments(server.id):
                # Get detailed volume information
                volume_id = getattr(attachment, 'volume_id', attachment.get('volumeId', 'unknown'))
                
                try:
                    volume = conn.volume.get_volume(volume_id)
                    volume_info = {
                        'volume_id': volume_id,
                        'volume_name': getattr(volume, 'name', 'unnamed'),
                        'device': getattr(attachment, 'device', 'unknown'),
                        'size': getattr(volume, 'size', 0),
                        'status': getattr(volume, 'status', 'unknown'),
                        'volume_type': getattr(volume, 'volume_type', 'unknown'),
                        'bootable': getattr(volume, 'is_bootable', False),
                        'encrypted': getattr(volume, 'is_encrypted', False),
                        'attachment_id': getattr(attachment, 'id', 'unknown'),
                        'attached_at': str(getattr(attachment, 'attached_at', 'unknown'))
                    }
                except Exception as e:
                    # If we can't get volume details, use basic info
                    volume_info = {
                        'volume_id': volume_id,
                        'volume_name': 'unknown',
                        'device': getattr(attachment, 'device', 'unknown'),
                        'size': 0,
                        'status': 'unknown',
                        'attachment_id': getattr(attachment, 'id', 'unknown'),
                        'error': f'Could not retrieve volume details: {e}'
                    }
                
                attached_volumes.append(volume_info)
                
        except Exception as e:
            logger.error(f"Failed to get volume attachments: {e}")
            # Fallback: check volume attachments from volume side
            for volume in conn.volume.volumes():
                attachments = getattr(volume, 'attachments', [])
                for attachment in attachments:
                    if attachment.get('server_id') == server.id:
                        attached_volumes.append({
                            'volume_id': volume.id,
                            'volume_name': getattr(volume, 'name', 'unnamed'),
                            'device': attachment.get('device', 'unknown'),
                            'size': getattr(volume, 'size', 0),
                            'status': getattr(volume, 'status', 'unknown'),
                            'volume_type': getattr(volume, 'volume_type', 'unknown'),
                            'bootable': getattr(volume, 'is_bootable', False),
                            'attachment_id': attachment.get('attachment_id', 'unknown'),
                            'method': 'volume_fallback'
                        })
        
        return attached_volumes
        
    except Exception as e:
        logger.error(f"Failed to get server volumes: {e}")
        return [{'error': str(e), 'instance_name': instance_name}]


def set_server_volume(instance_name: str, action: str, **kwargs) -> Dict[str, Any]:
    """
    Manage server volume attachments (attach, detach, list).
    
    Args:
        instance_name: Name or ID of the server
        action: Action to perform (attach, detach, list)
        **kwargs: Additional parameters (volume_name, device, etc.)
        
    Returns:
        Result of the volume attachment operation
    """
    try:
        # Import here to avoid circular imports
        from ..connection import get_openstack_connection
        conn = get_openstack_connection()
        
        # Find the server first
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
        
        if action.lower() == 'list':
            attached_volumes = get_server_volumes(instance_name)
            return {
                'success': True,
                'server_name': getattr(server, 'name', 'unnamed'),
                'server_id': server.id,
                'attached_volumes': attached_volumes,
                'count': len(attached_volumes)
            }
            
        elif action.lower() == 'attach':
            volume_name = kwargs.get('volume_name', kwargs.get('volume_id'))
            device = kwargs.get('device')
            
            if not volume_name:
                return {
                    'success': False,
                    'message': 'volume_name or volume_id is required for attach action'
                }
            
            # Find the volume
            volume = None
            for vol in conn.volume.volumes():
                if getattr(vol, 'name', '') == volume_name or vol.id == volume_name:
                    volume = vol
                    break
            
            if not volume:
                return {
                    'success': False,
                    'message': f'Volume "{volume_name}" not found'
                }
            
            # Check if volume is available
            volume_status = getattr(volume, 'status', 'unknown')
            if volume_status not in ['available', 'in-use'] and not getattr(volume, 'multiattach', False):
                return {
                    'success': False,
                    'message': f'Volume "{volume_name}" is not available (status: {volume_status})'
                }
            
            # Attach the volume
            attach_params = {
                'volume_id': volume.id,
                'instance_uuid': server.id
            }
            
            if device:
                attach_params['device'] = device
            
            try:
                attachment = conn.compute.create_volume_attachment(server.id, **attach_params)
                return {
                    'success': True,
                    'message': f'Volume "{volume_name}" attached to server "{instance_name}"',
                    'attachment': {
                        'volume_id': volume.id,
                        'volume_name': getattr(volume, 'name', 'unnamed'),
                        'server_id': server.id,
                        'server_name': getattr(server, 'name', 'unnamed'),
                        'device': getattr(attachment, 'device', device or 'auto'),
                        'attachment_id': getattr(attachment, 'id', 'unknown')
                    }
                }
            except Exception as e:
                return {
                    'success': False,
                    'message': f'Failed to attach volume: {str(e)}'
                }
                
        elif action.lower() == 'detach':
            volume_name = kwargs.get('volume_name', kwargs.get('volume_id'))
            
            if not volume_name:
                return {
                    'success': False,
                    'message': 'volume_name or volume_id is required for detach action'
                }
            
            # Find the volume
            volume = None
            for vol in conn.volume.volumes():
                if getattr(vol, 'name', '') == volume_name or vol.id == volume_name:
                    volume = vol
                    break
            
            if not volume:
                return {
                    'success': False,
                    'message': f'Volume "{volume_name}" not found'
                }
            
            # Check if volume is attached to this server
            volume_attachments = getattr(volume, 'attachments', [])
            attached_to_server = False
            
            for attachment in volume_attachments:
                if attachment.get('server_id') == server.id:
                    attached_to_server = True
                    break
            
            if not attached_to_server:
                return {
                    'success': False,
                    'message': f'Volume "{volume_name}" is not attached to server "{instance_name}"'
                }
            
            try:
                conn.compute.delete_volume_attachment(volume.id, server.id)
                return {
                    'success': True,
                    'message': f'Volume "{volume_name}" detached from server "{instance_name}"'
                }
            except Exception as e:
                return {
                    'success': False,
                    'message': f'Failed to detach volume: {str(e)}'
                }
                
        else:
            return {
                'success': False,
                'message': f'Unknown action "{action}". Supported: attach, detach, list'
            }
            
    except Exception as e:
        logger.error(f"Failed to manage server volume: {e}")
        return {
            'success': False,
            'message': f'Failed to manage server volume: {str(e)}',
            'error': str(e)
        }

def set_volume_types(action: str, type_name: str, description: str = '') -> Dict[str,
    Any]:
    """Create or delete volume types; requires the cloud's administrative policy."""
    from ..connection import get_openstack_connection

    try:
        if action.lower() not in {'create', 'delete'} or not type_name.strip():
            raise ValueError('Use create/delete and provide type_name')
        api = get_openstack_connection().block_storage
        if action.lower() == 'create':
            resource = api.create_type(name=type_name, description=description)
            return {'success': True, 'volume_type': resource.to_dict()}
        resource = api.find_type(type_name, ignore_missing=False)
        api.delete_type(resource, ignore_missing=False)
        return {'success': True, 'message': 'Volume type deletion accepted'}
    except Exception as exc:
        return {'success': False, 'message': 'Volume type operation failed',
            'error': str(exc)}


def get_volume_transfers() -> Dict[str, Any]:
    """List transfer requests visible in the authenticated Cinder project."""
    from ..connection import get_openstack_connection

    try:
        # Exclude transfer authorization keys from inventory responses.
        transfers = [{key: value for key,
            value in t.to_dict().items() if key != 'auth_key'}
                     for t in get_openstack_connection().block_storage.transfers()]
        return {'success': True, 'transfers': transfers, 'count': len(transfers)}
    except Exception as exc:
        return {'success': False, 'message': 'Volume transfer listing failed',
            'error': str(exc)}
