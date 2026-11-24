"""Tool implementation for set_volume."""

import json
from typing import Optional

from ..functions import set_volume as _set_volume
from ..mcp_main import (
    _get_resource_status_by_name,
    _read_action_error,
    conditional_tool,
    handle_operation_result,
    logger,
)

READ_ACTIONS = {'list': 'get_volume_list'}


@conditional_tool
async def set_volume(volume_names: str, action: str, size: int = 1, instance_name: str = "", 
                   new_size: int = 0, source_volume: str = "", backup_name: str = "",
                   snapshot_name: str = "", transfer_name: str = "", host: str = "",
                   description: str = "", volume_type: str = "", availability_zone: str = "",
                   force: bool = False, incremental: bool = False, force_host_copy: bool = False,
                   lock_volume: bool = False, source_snapshot: str = "",
                   image_name: str = "", disk_format: str = "",
                   container_format: str = "", visibility: str = "",
                   protected: Optional[bool] = None) -> str:
    """
    Changes project-scoped OpenStack volumes and attachments.
    Supports both single volume and bulk operations. To list volumes, use
    get_volume_list.
    
    Functions:
    - Create new volumes with specified size and type
    - Delete existing volumes
    - Extend volumes to larger sizes
    - Create volume snapshots
    - Create volumes from a project snapshot (source_snapshot)
    - Copy a volume into a new Glance image (upload_to_image), e.g. to turn the
      Cinder snapshot behind a boot-from-volume server snapshot into a
      bootable image with data
    - Bulk operations: Apply action to multiple volumes at once
    
    Use for volume lifecycle tasks. Use set_volume_backups for backups.
    Transfer, clone and migration actions are not exposed here.
    
    Args:
        volume_names: Name(s) of volumes to manage. Support formats:
                     - Single: "volume1" 
                     - Multiple: "volume1,volume2,volume3" or "volume1, volume2, volume3"
                     - List format: '["volume1", "volume2", "volume3"]'
        action: Management action (create, delete, extend, attach, detach,
            snapshot, upload_to_image)
        size: Volume size in GB (default: 1); fallback for extend if new_size is omitted
        instance_name: Instance name or ID (required for attach)
        new_size: Target size for extend; takes precedence over size when positive
        source_volume: Not implemented (clone); a value is rejected
        backup_name: Not implemented; a value is rejected. Use set_volume_backups
        snapshot_name: Custom snapshot name (auto-generated if not provided)
        transfer_name: Not implemented (transfer); a value is rejected
        host: Not implemented (migration); a value is rejected
        description: Description for create/snapshot operations
        volume_type: Volume type for create operations. With source_snapshot,
            Cinder may reject a type other than the snapshot's ("requested type
            is not compatible"); omit it, then upload_to_image and create the
            volume from that image with the desired type
        availability_zone: Availability zone for create operations
        force: Force operations even when volume is attached. For
            upload_to_image it allows an in-use volume, whose image may be
            inconsistent, only when Cinder sets enable_force_upload=True (the
            default is False); otherwise Cinder refuses it and the result
            names the alternative through a server snapshot. For snapshot it
            allows an in-use volume (crash-consistent)
        source_snapshot: Project snapshot name or ID to create the volume from
            (create). size is sent only when larger than the snapshot;
            otherwise the volume takes the snapshot's size
        image_name: Name of the new image (required for upload_to_image; one
            volume per call)
        disk_format: Image disk format for upload_to_image (e.g. raw, qcow2);
            Cinder's default is raw
        container_format: Image container format for upload_to_image (default bare)
        visibility: Image visibility for upload_to_image (private, shared,
            community, public); Glance policy decides who may set public
        protected: Mark the new image protected (upload_to_image)

    upload_to_image is asynchronous: Cinder copies the data to Glance itself
    (no image data passes through this server). The result carries the image
    ID with its current status; confirm that the image reached active with
    get_image_detail_list before using it. Glance needs room for a full copy
    of the volume.
        incremental: Not implemented; true is rejected. Use set_volume_backups
        force_host_copy: Not implemented (migration); true is rejected
        lock_volume: Not implemented (migration); true is rejected
        
    Returns:
        Volume management operation result in JSON format with success status and volume information.
        For bulk operations, returns summary of successes and failures.
    """

    read_error = _read_action_error(action, READ_ACTIONS)
    if read_error:
        return read_error
    try:
        if not action or not action.strip():
            return "Error: Action is required (create, delete, extend, attach, detach, snapshot, upload_to_image)"

        unsupported = [name for name, value in (
            ('source_volume', source_volume), ('backup_name', backup_name),
            ('transfer_name', transfer_name), ('host', host),
            ('incremental', incremental), ('force_host_copy', force_host_copy),
            ('lock_volume', lock_volume),
        ) if value]
        if unsupported:
            return (f"Error: Not implemented by set_volume: {', '.join(unsupported)}. "
                    "Use set_volume_backups for backups; clone, transfer and "
                    "migration are not available. Nothing was changed.")

        action = action.strip().lower()
        
        # Parse volume names
        if not volume_names or not volume_names.strip():
            return "Error: Volume name(s) are required for this action"
            
        names_str = volume_names.strip()
        
        # Handle JSON list format: ["name1", "name2"]
        if names_str.startswith('[') and names_str.endswith(']'):
            try:
                import json
                name_list = json.loads(names_str)
                if not isinstance(name_list, list):
                    return "Error: Invalid JSON list format for volume names"
            except json.JSONDecodeError:
                return "Error: Invalid JSON format for volume names"
        else:
            # Handle comma-separated format: "name1,name2" or "name1, name2"
            name_list = [name.strip() for name in names_str.split(',')]
        
        # Remove empty strings
        name_list = [name for name in name_list if name]
        
        if not name_list:
            return "Error: No valid volume names provided"
            
        if action == 'upload_to_image' and len(name_list) != 1:
            return "Error: upload_to_image takes exactly one volume per call"

        # Prepare kwargs for set_volume function
        kwargs = {
            'size': size,
            'new_size': new_size if new_size > 0 else None,
            'source_volume': source_volume if source_volume else None,
            'backup_name': backup_name if backup_name else None,
            'snapshot_name': snapshot_name if snapshot_name else None,
            'transfer_name': transfer_name if transfer_name else None,
            'host': host if host else None,
            'description': description if description else None,
            'volume_type': volume_type if volume_type else None,
            'availability_zone': availability_zone if availability_zone else None,
            'force': force,
            'incremental': incremental,
            'force_host_copy': force_host_copy,
            'lock_volume': lock_volume,
            'source_snapshot': source_snapshot.strip() or None,
            'image_name': image_name.strip() or None,
            'disk_format': disk_format.strip() or None,
            'container_format': container_format.strip() or None,
            'visibility': visibility.strip() or None,
            'protected': protected,
        }
        if instance_name:
            kwargs['instance_name'] = instance_name.strip()
        
        # Remove None values from kwargs
        kwargs = {k: v for k, v in kwargs.items() if v is not None}
        
        # Handle single volume (backward compatibility)
        if len(name_list) == 1:
            logger.info(f"Managing volume '{name_list[0]}' with action '{action}'")
            result = _set_volume(name_list[0].strip(), action, **kwargs)
            
            return handle_operation_result(
                result,
                "Volume Management",
                {
                    "Action": action,
                    "Volume": name_list[0],
                    "Size": f"{size}GB" if size else "Not specified",
                    "Instance": instance_name or "Not specified"
                }
            )
        
        # Handle bulk operations (multiple volumes)
        else:
            logger.info(f"Managing {len(name_list)} volumes with action '{action}': {name_list}")
            results = []
            successes = []
            failures = []
            
            for volume_name in name_list:
                try:
                    result = _set_volume(volume_name.strip(), action, **kwargs)
                    
                    # Check if result indicates success or failure
                    if isinstance(result, dict):
                        if result.get('success', False):
                            successes.append(volume_name)
                            results.append(f"✓ {volume_name}: {result.get('message', 'Success')}")
                        else:
                            failures.append(volume_name)
                            results.append(f"✗ {volume_name}: {result.get('error', 'Unknown error')}")
                    elif isinstance(result, str):
                        # For string results, check if it contains error indicators
                        if 'error' in result.lower() or 'failed' in result.lower():
                            failures.append(volume_name)
                            results.append(f"✗ {volume_name}: {result}")
                        else:
                            successes.append(volume_name)
                            results.append(f"✓ {volume_name}: {result}")
                    else:
                        successes.append(volume_name)
                        results.append(f"✓ {volume_name}: Operation completed")
                        
                except Exception as e:
                    failures.append(volume_name)
                    results.append(f"✗ {volume_name}: {str(e)}")
            
            # Post-action status verification for all processed volumes
            logger.info("Verifying post-action status for volumes")
            post_action_status = {}
            
            # Allow some time for OpenStack operations to complete
            import time
            time.sleep(2)
            
            for volume_name in name_list:
                post_action_status[volume_name] = _get_resource_status_by_name("volume", volume_name.strip())
            
            # Prepare summary with post-action status
            summary_parts = [
                f"Bulk Volume Management - Action: {action}",
                f"Total volumes: {len(name_list)}",
                f"Successes: {len(successes)}",
                f"Failures: {len(failures)}"
            ]
            
            if successes:
                summary_parts.append(f"Successful volumes: {', '.join(successes)}")
            if failures:
                summary_parts.append(f"Failed volumes: {', '.join(failures)}")
                
            summary_parts.append("\nDetailed Results:")
            summary_parts.extend(results)
            
            # Add post-action status information
            summary_parts.append("\nPost-Action Status:")
            for volume_name in name_list:
                current_status = post_action_status.get(volume_name, 'Unknown')
                status_indicator = "🟢" if current_status.lower() in ["available", "active"] else "🔴" if current_status.lower() in ["error", "deleted"] else "🟡"
                summary_parts.append(f"{status_indicator} {volume_name}: {current_status}")
            
            return "\n".join(summary_parts)
        
    except Exception as e:
        error_msg = f"Error: Failed to manage volume(s) '{volume_names}' - {str(e)}"
        logger.error(error_msg)
        return error_msg
