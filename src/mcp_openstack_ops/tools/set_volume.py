"""Tool implementation for set_volume."""

import json
from ..functions import set_volume as _set_volume
from ..mcp_main import (
    _get_resource_status_by_name,
    conditional_tool,
    handle_operation_result,
    logger,
)

@conditional_tool
async def set_volume(volume_names: str, action: str, size: int = 1, instance_name: str = "", 
                   new_size: int = 0, source_volume: str = "", backup_name: str = "",
                   snapshot_name: str = "", transfer_name: str = "", host: str = "",
                   description: str = "", volume_type: str = "", availability_zone: str = "",
                   force: bool = False, incremental: bool = False, force_host_copy: bool = False,
                   lock_volume: bool = False) -> str:
    """
    Manages OpenStack volumes with comprehensive operations including advanced features.
    Supports both single volume and bulk operations.
    
    Functions:
    - Create new volumes with specified size and type
    - Delete existing volumes
    - List all volumes with detailed status information
    - Extend volumes to larger sizes
    - Create volume backups (full or incremental)
    - Create volume snapshots
    - Clone volumes from existing volumes
    - Create volume transfers for ownership change
    - Migrate volumes between hosts/backends
    - Bulk operations: Apply action to multiple volumes at once
    
    Use when user requests volume management, storage operations, disk management, backup operations, or volume lifecycle tasks.
    
    Args:
        volume_names: Name(s) of volumes to manage. Support formats:
                     - Single: "volume1" 
                     - Multiple: "volume1,volume2,volume3" or "volume1, volume2, volume3"
                     - List format: '["volume1", "volume2", "volume3"]'
        action: Management action (create, delete, list, extend, backup, snapshot, clone, transfer, migrate)
        size: Volume size in GB (default: 1, used for create/clone actions)
        instance_name: Instance name for attach operations (optional)
        new_size: New size for extend action (required for extend)
        source_volume: Source volume name/ID for clone action
        backup_name: Custom backup name (auto-generated if not provided)
        snapshot_name: Custom snapshot name (auto-generated if not provided)
        transfer_name: Custom transfer name (auto-generated if not provided)
        host: Target host for migrate action (required for migrate)
        description: Description for create/backup/snapshot operations
        volume_type: Volume type for create operations
        availability_zone: Availability zone for create operations
        force: Force operations even when volume is attached
        incremental: Create incremental backup (default: False)
        force_host_copy: Force host copy during migration
        lock_volume: Lock volume during migration
        
    Returns:
        Volume management operation result in JSON format with success status and volume information.
        For bulk operations, returns summary of successes and failures.
    """
    
    try:
        if not action or not action.strip():
            return "Error: Action is required (create, delete, list)"
            
        action = action.strip().lower()
        
        # For list action, allow empty volume_names
        if action == 'list':
            # Special handling for list action
            logger.info(f"Managing volume with action '{action}'")
            
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
                'lock_volume': lock_volume
            }
            if instance_name:
                kwargs['instance_name'] = instance_name.strip()
            
            # Remove None values from kwargs
            kwargs = {k: v for k, v in kwargs.items() if v is not None}
            
            result = _set_volume("", action, **kwargs)
            return handle_operation_result(
                result,
                "Volume Management",
                {
                    "Action": action,
                    "Volume": "all",
                    "Size": f"{size}GB" if size else "Not specified",
                    "Instance": instance_name or "Not specified"
                }
            )
        
        # Parse volume names for non-list actions
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
            'lock_volume': lock_volume
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
