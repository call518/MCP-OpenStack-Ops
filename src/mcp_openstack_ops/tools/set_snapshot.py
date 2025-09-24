"""Tool implementation for set_snapshot."""

import json
from ..functions import (
    get_volume_snapshots as _get_volume_snapshots,
    set_snapshot as _set_snapshot,
)
from ..mcp_main import (
    _get_resource_status_by_name,
    conditional_tool,
    handle_operation_result,
    logger,
)

@conditional_tool
async def set_snapshot(
    action: str,
    snapshot_names: str = "",
    # Filtering parameters for automatic target identification  
    name_contains: str = "",
    status: str = "",
    # Snapshot creation/modification parameters
    volume_id: str = "",
    description: str = ""
) -> str:
    """
    Manage volume snapshots for backup and recovery operations.
    Supports both direct targeting and filter-based bulk operations.
    
    Functions:
    - Create snapshots from existing volumes for backup
    - Delete existing snapshots to reclaim storage
    - Handle snapshot lifecycle management with descriptions
    - Bulk operations: Apply action to multiple snapshots at once
    - Filter-based targeting: Automatically find targets using filtering conditions
    
    Use when user requests:
    - "Create snapshot [name] from volume [volume_id]"
    - "Delete snapshot [name]"
    - "Delete all snapshots with name containing 'old'"
    - "Create snapshots snap1,snap2,snap3"
    
    Targeting Methods:
    1. Direct: Specify snapshot_names directly
    2. Filter-based: Use name_contains, status to auto-identify targets
    
    Args:
        action: Action to perform - create, delete
        snapshot_names: Name(s) of snapshots to manage. Support formats:
                       - Single: "snapshot1"
                       - Multiple: "snapshot1,snapshot2,snapshot3"
                       - List format: '["snapshot1", "snapshot2"]'
                       - Leave empty to use filtering parameters
        
        # Filtering parameters (alternative to snapshot_names)
        name_contains: Filter snapshots whose names contain this string
        status: Filter snapshots by status (e.g., "available", "creating", "error")
        
        # Creation/modification parameters
        volume_id: Volume ID for snapshot creation (required for create action)
        description: Description for the snapshot (optional)
        
    Returns:
        Snapshot management operation result with post-action status verification.
        
    Examples:
        # Direct targeting
        set_snapshot(action="delete", snapshot_names="snap1,snap2")
        
        # Filter-based targeting  
        set_snapshot(action="delete", name_contains="old", status="available")
        set_snapshot(action="create", snapshot_names="backup-snap", volume_id="vol-123")
    """
    try:
        if not action or not action.strip():
            return "Error: Action is required (create, delete)"
            
        action = action.strip().lower()
        
        # Determine targeting method
        has_direct_targets = snapshot_names and snapshot_names.strip()
        has_filter_params = any([name_contains, status])
        
        if not has_direct_targets and not has_filter_params:
            return "Error: Either specify snapshot_names directly or provide filtering parameters (name_contains, status)"
        
        if has_direct_targets and has_filter_params:
            return "Error: Use either direct targeting (snapshot_names) OR filtering parameters, not both"
        
        # Handle filter-based targeting
        if has_filter_params:
            logger.info(f"Using filter-based targeting for snapshot action '{action}'")
            
            # Get all snapshots and filter
            all_snapshots_info = _get_volume_snapshots()
            if not isinstance(all_snapshots_info, list):
                return "Error: Failed to retrieve snapshot list for filtering"
            
            target_names = []
            for snapshot in all_snapshots_info:
                snapshot_name = snapshot.get('name', '')
                snapshot_status = snapshot.get('status', '')
                
                # Apply filters
                if name_contains and name_contains.lower() not in snapshot_name.lower():
                    continue
                if status and status.lower() != snapshot_status.lower():
                    continue
                    
                target_names.append(snapshot_name)
            
            if not target_names:
                filter_desc = []
                if name_contains: filter_desc.append(f"name contains '{name_contains}'")
                if status: filter_desc.append(f"status = '{status}'")
                
                return f"No snapshots found matching filters: {', '.join(filter_desc)}"
            
            logger.info(f"Filter-based targeting found {len(target_names)} snapshots: {target_names}")
            name_list = target_names
        
        else:
            # Handle direct targeting
            names_str = snapshot_names.strip()
            
            # Handle JSON list format: ["name1", "name2"]
            if names_str.startswith('[') and names_str.endswith(']'):
                try:
                    import json
                    name_list = json.loads(names_str)
                    if not isinstance(name_list, list):
                        return "Error: Invalid JSON list format for snapshot names"
                except json.JSONDecodeError:
                    return "Error: Invalid JSON format for snapshot names"
            else:
                # Handle comma-separated format: "name1,name2" or "name1, name2"
                name_list = [name.strip() for name in names_str.split(',')]
            
            # Remove empty strings
            name_list = [name for name in name_list if name]
            
            if not name_list:
                return "Error: No valid snapshot names provided"
        
        # Prepare kwargs for snapshot operations
        kwargs = {}
        if volume_id.strip():
            kwargs['volume_id'] = volume_id.strip()
        if description.strip():
            kwargs['description'] = description.strip()
        
        # Handle single snapshot (backward compatibility)
        if len(name_list) == 1:
            logger.info(f"Managing snapshot '{name_list[0]}' with action '{action}'")
            result = _set_snapshot(name_list[0].strip(), action, **kwargs)
            
            # Post-action status verification for single snapshot
            import time
            time.sleep(2)  # Allow time for OpenStack operation to complete
            
            post_status = _get_resource_status_by_name("snapshot", name_list[0].strip())
            
            # Use centralized result handling with enhanced status info
            base_result = handle_operation_result(
                result,
                "Snapshot Management",
                {
                    "Action": action,
                    "Snapshot Name": name_list[0],
                    "Volume ID": volume_id or "Not specified",
                    "Description": description or "Not specified"
                }
            )
            
            # Add post-action status
            status_indicator = "🟢" if post_status in ["available", "Available"] else "🔴" if post_status in ["error", "ERROR", "Not Found"] else "🟡"
            enhanced_result = f"{base_result}\n\nPost-Action Status:\n{status_indicator} {name_list[0]}: {post_status}"
            
            return enhanced_result
        
        # Handle bulk operations (multiple snapshots)
        else:
            logger.info(f"Managing {len(name_list)} snapshots with action '{action}': {name_list}")
            results = []
            successes = []
            failures = []
            
            for snapshot_name in name_list:
                try:
                    result = _set_snapshot(snapshot_name.strip(), action, **kwargs)
                    
                    # Check if result indicates success or failure
                    if isinstance(result, dict):
                        if result.get('success', False):
                            successes.append(snapshot_name)
                            results.append(f"✓ {snapshot_name}: {result.get('message', 'Success')}")
                        else:
                            failures.append(snapshot_name)
                            results.append(f"✗ {snapshot_name}: {result.get('error', 'Unknown error')}")
                    elif isinstance(result, str):
                        # For string results, check if it contains error indicators
                        if 'error' in result.lower() or 'failed' in result.lower():
                            failures.append(snapshot_name)
                            results.append(f"✗ {snapshot_name}: {result}")
                        else:
                            successes.append(snapshot_name)
                            results.append(f"✓ {snapshot_name}: {result}")
                    else:
                        successes.append(snapshot_name)
                        results.append(f"✓ {snapshot_name}: Operation completed")
                        
                except Exception as e:
                    failures.append(snapshot_name)
                    results.append(f"✗ {snapshot_name}: {str(e)}")
            
            # Post-action status verification for all processed snapshots
            logger.info("Verifying post-action status for snapshots")
            post_action_status = {}
            
            # Allow some time for OpenStack operations to complete
            import time
            time.sleep(2)
            
            for snapshot_name in name_list:
                post_action_status[snapshot_name] = _get_resource_status_by_name("snapshot", snapshot_name.strip())
            
            # Prepare summary with post-action status
            summary_parts = [
                f"Bulk Snapshot Management - Action: {action}",
                f"Total snapshots: {len(name_list)}",
                f"Successes: {len(successes)}",
                f"Failures: {len(failures)}"
            ]
            
            if successes:
                summary_parts.append(f"Successful snapshots: {', '.join(successes)}")
            if failures:
                summary_parts.append(f"Failed snapshots: {', '.join(failures)}")
                
            summary_parts.append("\nDetailed Results:")
            summary_parts.extend(results)
            
            # Add post-action status information
            summary_parts.append("\nPost-Action Status:")
            for snapshot_name in name_list:
                current_status = post_action_status.get(snapshot_name, 'Unknown')
                status_indicator = "🟢" if current_status in ["available", "Available"] else "🔴" if current_status in ["error", "ERROR", "Not Found"] else "🟡"
                summary_parts.append(f"{status_indicator} {snapshot_name}: {current_status}")
            
            return "\n".join(summary_parts)
        
    except Exception as e:
        error_msg = f"Error: Failed to manage snapshot(s) - {str(e)}"
        logger.error(error_msg)
        return error_msg
