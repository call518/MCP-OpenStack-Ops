"""Tool implementation for set_instance."""

import json
from typing import Optional
from ..functions import (
    get_instance_by_name as _get_instance_by_name,
    get_instances_by_status as _get_instances_by_status,
    set_instance as _set_instance,
)
from ..mcp_main import (
    conditional_tool,
    handle_operation_result,
    logger,
)
from ..services.compute import search_instances as _search_instances

@conditional_tool
async def set_instance(
    instance_names: str = "", 
    action: str = "",
    # Filtering parameters for automatic target identification
    name_contains: str = "",
    status: str = "",
    flavor_contains: str = "",
    image_contains: str = "",
    # Instance creation/modification parameters
    flavor: Optional[str] = None,
    image: Optional[str] = None,
    networks: Optional[str] = None,
    security_groups: Optional[str] = None,
    key_name: Optional[str] = None,
    availability_zone: Optional[str] = None
) -> str:
    """
    Manages OpenStack instances with operations like start, stop, restart, pause, unpause, and create.
    Supports both direct target specification and automatic filtering-based target identification.
    
    Functions:
    - Create new instances with specified configuration
    - Start stopped instances
    - Stop running instances 
    - Restart/reboot instances (soft reboot)
    - Pause active instances (suspend to memory)
    - Unpause/resume paused instances
    - Bulk operations: Apply action to multiple instances at once
    - Filter-based targeting: Automatically find targets using filtering conditions
    
    Use when user requests instance management, VM control, server operations, instance lifecycle management, or server creation.
    
    CRITICAL: For create action, both flavor AND image are REQUIRED. Operation will fail if either is missing.
    
    Targeting Methods:
    1. Direct: Specify instance_names directly
    2. Filter-based: Use name_contains, status, flavor_contains, image_contains to auto-identify targets
    
    Args:
        instance_names: Name(s) of instances to manage or create. Support formats:
                       - Single: "instance1" 
                       - Multiple: "instance1,instance2,instance3" or "instance1, instance2, instance3"
                       - List format: '["instance1", "instance2", "instance3"]'
                       - Leave empty to use filtering parameters
        action: Management action (create, start, stop, restart, reboot, pause, unpause, resume)
        
        # Filtering parameters (alternative to instance_names)
        name_contains: Filter instances whose names contain this string (e.g., "ttt", "dev", "test")
        status: Filter instances by status (e.g., "SHUTOFF", "ACTIVE", "ERROR")
        flavor_contains: Filter instances whose flavor names contain this string
        image_contains: Filter instances whose image names contain this string
        
        # Creation/modification parameters
        flavor: Flavor name for create action (e.g., 'm1.small', 'm1.medium') - REQUIRED for create
        image: Image name for create action (e.g., 'ubuntu-22.04', 'rocky-9') - REQUIRED for create
        networks: Network name(s) for create action (e.g., 'demo-net', 'private-net')
        security_groups: Security group name(s) for create action (e.g., 'default', 'web-sg')
        key_name: SSH keypair name for create action (optional)
        availability_zone: Availability zone for create action (optional)
        
    Returns:
        Clear success message with instance details OR clear error message if operation fails.
        For bulk operations, returns summary of successes and failures.
        For filter-based operations, shows identified targets before performing actions.
        NEVER returns false success claims - if operation fails, you'll get explicit error details.
        
    Examples:
        # Direct targeting
        set_instance(instance_names="vm1,vm2", action="start")
        
        # Filter-based targeting  
        set_instance(name_contains="ttt", action="stop")
        set_instance(status="SHUTOFF", action="start")
        set_instance(name_contains="dev", status="ACTIVE", action="restart")
    """
    try:
        if not action or not action.strip():
            return "Error: Action is required (create, start, stop, restart, pause, unpause)"
            
        action = action.strip().lower()
        
        # Determine targeting method
        has_direct_targets = instance_names and instance_names.strip()
        has_filter_params = any([name_contains, status, flavor_contains, image_contains])
        
        if not has_direct_targets and not has_filter_params:
            return "Error: Either specify instance_names directly or provide filtering parameters (name_contains, status, etc.)"
        
        if has_direct_targets and has_filter_params:
            return "Error: Use either direct targeting (instance_names) OR filtering parameters, not both"
        
        # Handle filter-based targeting
        if has_filter_params:
            logger.info(f"Using filter-based targeting for action '{action}'")
            
            # Build search criteria
            search_results = []
            
            if name_contains:
                result = _search_instances(
                    search_term=name_contains,
                    search_fields=['name'],
                    limit=200,
                    include_inactive=True
                )
                if isinstance(result, dict) and 'instances' in result:
                    search_results.extend(result['instances'])
                elif isinstance(result, list):
                    search_results.extend(result)
            
            if status:
                status_instances = _get_instances_by_status(status.upper())
                search_results.extend(status_instances)
            
            # Apply additional filters if specified
            if flavor_contains or image_contains:
                filtered_results = []
                for instance in search_results:
                    if flavor_contains and flavor_contains.lower() not in instance.get('flavor', '').lower():
                        continue
                    if image_contains and image_contains.lower() not in instance.get('image', '').lower():
                        continue
                    filtered_results.append(instance)
                search_results = filtered_results
            
            # Remove duplicates and extract names
            seen_ids = set()
            target_names = []
            for instance in search_results:
                instance_id = instance.get('id', '')
                if instance_id and instance_id not in seen_ids:
                    seen_ids.add(instance_id)
                    target_names.append(instance.get('name', ''))
            
            if not target_names:
                filter_desc = []
                if name_contains: filter_desc.append(f"name contains '{name_contains}'")
                if status: filter_desc.append(f"status = '{status}'")
                if flavor_contains: filter_desc.append(f"flavor contains '{flavor_contains}'")
                if image_contains: filter_desc.append(f"image contains '{image_contains}'")
                
                return f"No instances found matching filters: {', '.join(filter_desc)}"
            
            logger.info(f"Filter-based targeting found {len(target_names)} instances: {target_names}")
            
            # Use the found names as targets
            name_list = target_names
        
        else:
            # Handle direct targeting (existing logic)
            names_str = instance_names.strip()
            
            # Handle JSON list format: ["name1", "name2"]
            if names_str.startswith('[') and names_str.endswith(']'):
                try:
                    import json
                    name_list = json.loads(names_str)
                    if not isinstance(name_list, list):
                        return "Error: Invalid JSON list format for instance names"
                except json.JSONDecodeError:
                    return "Error: Invalid JSON format for instance names"
            else:
                # Handle comma-separated format: "name1,name2" or "name1, name2"
                name_list = [name.strip() for name in names_str.split(',')]
            
            # Remove empty strings
            name_list = [name for name in name_list if name]
            
            if not name_list:
                return "Error: No valid instance names provided"
            
        kwargs = {}
        if flavor:
            kwargs['flavor'] = flavor
        if image:
            kwargs['image'] = image
        if networks:
            kwargs['networks'] = networks.split(',') if ',' in networks else [networks]
        if security_groups:
            kwargs['security_groups'] = security_groups.split(',') if ',' in security_groups else [security_groups]
        if key_name:
            kwargs['key_name'] = key_name
        if availability_zone:
            kwargs['availability_zone'] = availability_zone
            
        # Handle single instance (backward compatibility)
        if len(name_list) == 1:
            logger.info(f"Managing instance '{name_list[0]}' with action '{action}'")
            result = _set_instance(name_list[0].strip(), action.strip(), **kwargs)
            
            # Post-action status verification for single instance
            import time
            time.sleep(2)  # Allow time for OpenStack operation to complete
            
            post_status = "Unknown"
            try:
                instance_info = _get_instance_by_name(name_list[0].strip())
                if instance_info:
                    post_status = instance_info.get('status', 'Unknown')
                else:
                    post_status = 'Not Found'
            except Exception as e:
                post_status = f'Status Check Failed: {str(e)}'
            
            # Use centralized result handling with enhanced status info
            base_result = handle_operation_result(
                result, 
                "Instance Management",
                {
                    "Action": action,
                    "Instance": name_list[0],
                    "Flavor": flavor or "Not specified",
                    "Image": image or "Not specified"
                }
            )
            
            # Add post-action status
            status_indicator = "🟢" if post_status in ["ACTIVE", "RUNNING"] else "🔴" if post_status in ["SHUTOFF", "STOPPED"] else "🟡"
            enhanced_result = f"{base_result}\n\nPost-Action Status:\n{status_indicator} {name_list[0]}: {post_status}"
            
            return enhanced_result
        
        # Handle bulk operations (multiple instances)
        else:
            logger.info(f"Managing {len(name_list)} instances with action '{action}': {name_list}")
            results = []
            successes = []
            failures = []
            
            for instance_name in name_list:
                try:
                    result = _set_instance(instance_name.strip(), action.strip(), **kwargs)
                    
                    # Check if result indicates success or failure
                    if isinstance(result, dict):
                        if result.get('success', False):
                            successes.append(instance_name)
                            results.append(f"✓ {instance_name}: {result.get('message', 'Success')}")
                        else:
                            failures.append(instance_name)
                            results.append(f"✗ {instance_name}: {result.get('error', 'Unknown error')}")
                    elif isinstance(result, str):
                        # For string results, check if it contains error indicators
                        if 'error' in result.lower() or 'failed' in result.lower():
                            failures.append(instance_name)
                            results.append(f"✗ {instance_name}: {result}")
                        else:
                            successes.append(instance_name)
                            results.append(f"✓ {instance_name}: {result}")
                    else:
                        successes.append(instance_name)
                        results.append(f"✓ {instance_name}: Operation completed")
                        
                except Exception as e:
                    failures.append(instance_name)
                    results.append(f"✗ {instance_name}: {str(e)}")
            
            # Post-action status verification for all processed instances
            logger.info("Verifying post-action status for instances")
            post_action_status = {}
            
            # Allow some time for OpenStack operations to complete
            import time
            time.sleep(2)
            
            for instance_name in name_list:
                try:
                    # Get current status of the instance
                    instance_info = _get_instance_by_name(instance_name.strip())
                    if instance_info:
                        current_status = instance_info.get('status', 'Unknown')
                        post_action_status[instance_name] = current_status
                    else:
                        post_action_status[instance_name] = 'Not Found'
                except Exception as e:
                    post_action_status[instance_name] = f'Status Check Failed: {str(e)}'
            
            # Prepare summary with post-action status
            summary_parts = [
                f"Bulk Instance Management - Action: {action}",
                f"Total instances: {len(name_list)}",
                f"Successes: {len(successes)}",
                f"Failures: {len(failures)}"
            ]
            
            if successes:
                summary_parts.append(f"Successful instances: {', '.join(successes)}")
            if failures:
                summary_parts.append(f"Failed instances: {', '.join(failures)}")
                
            summary_parts.append("\nDetailed Results:")
            summary_parts.extend(results)
            
            # Add post-action status information
            summary_parts.append("\nPost-Action Status:")
            for instance_name in name_list:
                current_status = post_action_status.get(instance_name, 'Unknown')
                status_indicator = "🟢" if current_status in ["ACTIVE", "RUNNING"] else "🔴" if current_status in ["SHUTOFF", "STOPPED"] else "🟡"
                summary_parts.append(f"{status_indicator} {instance_name}: {current_status}")
            
            return "\n".join(summary_parts)
        
    except Exception as e:
        error_msg = f"Error: Failed to manage instance(s) '{instance_names}' - {str(e)}"
        logger.error(error_msg)
        return error_msg
