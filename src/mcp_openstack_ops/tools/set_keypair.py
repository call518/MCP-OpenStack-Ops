"""Tool implementation for set_keypair."""

import json
from ..functions import (
    get_keypair_list as _get_keypair_list,
    set_keypair as _set_keypair,
)
from ..mcp_main import (
    _get_resource_status_by_name,
    conditional_tool,
    handle_operation_result,
    logger,
)

@conditional_tool
async def set_keypair(
    action: str,
    keypair_names: str = "",
    # Filtering parameters for automatic target identification  
    name_contains: str = "",
    # Keypair creation/import parameters
    public_key: str = ""
) -> str:
    """
    Manage SSH keypairs for secure instance access authentication.
    Supports both direct targeting and filter-based bulk operations.
    
    Functions:
    - Create new SSH keypairs with automatic key generation
    - Import existing public keys for keypair creation
    - Delete existing keypairs to remove access credentials
    - Bulk operations: Apply action to multiple keypairs at once
    - Filter-based targeting: Automatically find targets using filtering conditions
    
    Use when user requests:
    - "Create keypair [name]"
    - "Import public key as keypair [name]"
    - "Delete keypair [name]"  
    - "Delete all keypairs with name containing 'test'"
    - "Create keypairs key1,key2,key3"
    
    Targeting Methods:
    1. Direct: Specify keypair_names directly
    2. Filter-based: Use name_contains to auto-identify targets
    
    Args:
        action: Action to perform - create, delete, import
        keypair_names: Name(s) of keypairs to manage. Support formats:
                      - Single: "keypair1"
                      - Multiple: "keypair1,keypair2,keypair3"
                      - List format: '["keypair1", "keypair2"]'
                      - Leave empty to use filtering parameters
        
        # Filtering parameters (alternative to keypair_names)
        name_contains: Filter keypairs whose names contain this string
        
        # Creation/import parameters
        public_key: Public key content for import action (optional for create)
        
    Returns:
        Keypair management operation result with post-action status verification.
        
    Examples:
        # Direct targeting
        set_keypair(action="delete", keypair_names="key1,key2")
        
        # Filter-based targeting  
        set_keypair(action="delete", name_contains="test")
        set_keypair(action="create", keypair_names="new-key")
    """
    try:
        if not action or not action.strip():
            return "Error: Action is required (create, delete, import)"
            
        action = action.strip().lower()
        
        # Determine targeting method
        has_direct_targets = keypair_names and keypair_names.strip()
        has_filter_params = bool(name_contains)
        
        if not has_direct_targets and not has_filter_params:
            return "Error: Either specify keypair_names directly or provide filtering parameters (name_contains)"
        
        if has_direct_targets and has_filter_params:
            return "Error: Use either direct targeting (keypair_names) OR filtering parameters, not both"
        
        # Handle filter-based targeting
        if has_filter_params:
            logger.info(f"Using filter-based targeting for keypair action '{action}'")
            
            # Get all keypairs and filter
            all_keypairs_info = _get_keypair_list()
            if not isinstance(all_keypairs_info, list):
                return "Error: Failed to retrieve keypair list for filtering"
            
            target_names = []
            for keypair in all_keypairs_info:
                keypair_name = keypair.get('name', '')
                
                # Apply filters
                if name_contains and name_contains.lower() not in keypair_name.lower():
                    continue
                    
                target_names.append(keypair_name)
            
            if not target_names:
                return f"No keypairs found matching filter: name contains '{name_contains}'"
            
            logger.info(f"Filter-based targeting found {len(target_names)} keypairs: {target_names}")
            name_list = target_names
        
        else:
            # Handle direct targeting
            names_str = keypair_names.strip()
            
            # Handle JSON list format: ["name1", "name2"]
            if names_str.startswith('[') and names_str.endswith(']'):
                try:
                    import json
                    name_list = json.loads(names_str)
                    if not isinstance(name_list, list):
                        return "Error: Invalid JSON list format for keypair names"
                except json.JSONDecodeError:
                    return "Error: Invalid JSON format for keypair names"
            else:
                # Handle comma-separated format: "name1,name2" or "name1, name2"
                name_list = [name.strip() for name in names_str.split(',')]
            
            # Remove empty strings
            name_list = [name for name in name_list if name]
            
            if not name_list:
                return "Error: No valid keypair names provided"
        
        # Prepare kwargs for keypair operations
        kwargs = {}
        if public_key.strip():
            kwargs['public_key'] = public_key.strip()
        
        # Handle single keypair (backward compatibility)
        if len(name_list) == 1:
            logger.info(f"Managing keypair '{name_list[0]}' with action '{action}'")
            result = _set_keypair(name_list[0].strip(), action, **kwargs)
            
            # Post-action status verification for single keypair
            import time
            time.sleep(2)  # Allow time for OpenStack operation to complete
            
            post_status = _get_resource_status_by_name("keypair", name_list[0].strip())
            
            # Use centralized result handling with enhanced status info
            base_result = handle_operation_result(
                result,
                "Keypair Management",
                {
                    "Action": action,
                    "Keypair Name": name_list[0],
                    "Public Key": "Provided" if public_key.strip() else "Not provided"
                }
            )
            
            # Add post-action status
            status_indicator = "🟢" if post_status in ["Available", "Active"] else "🔴" if post_status in ["Not Found", "ERROR"] else "🟡"
            enhanced_result = f"{base_result}\n\nPost-Action Status:\n{status_indicator} {name_list[0]}: {post_status}"
            
            return enhanced_result
        
        # Handle bulk operations (multiple keypairs)
        else:
            logger.info(f"Managing {len(name_list)} keypairs with action '{action}': {name_list}")
            results = []
            successes = []
            failures = []
            
            for keypair_name in name_list:
                try:
                    result = _set_keypair(keypair_name.strip(), action, **kwargs)
                    
                    # Check if result indicates success or failure
                    if isinstance(result, dict):
                        if result.get('success', False):
                            successes.append(keypair_name)
                            results.append(f"✓ {keypair_name}: {result.get('message', 'Success')}")
                        else:
                            failures.append(keypair_name)
                            results.append(f"✗ {keypair_name}: {result.get('error', 'Unknown error')}")
                    elif isinstance(result, str):
                        # For string results, check if it contains error indicators
                        if 'error' in result.lower() or 'failed' in result.lower():
                            failures.append(keypair_name)
                            results.append(f"✗ {keypair_name}: {result}")
                        else:
                            successes.append(keypair_name)
                            results.append(f"✓ {keypair_name}: {result}")
                    else:
                        successes.append(keypair_name)
                        results.append(f"✓ {keypair_name}: Operation completed")
                        
                except Exception as e:
                    failures.append(keypair_name)
                    results.append(f"✗ {keypair_name}: {str(e)}")
            
            # Post-action status verification for all processed keypairs
            logger.info("Verifying post-action status for keypairs")
            post_action_status = {}
            
            # Allow some time for OpenStack operations to complete
            import time
            time.sleep(2)
            
            for keypair_name in name_list:
                post_action_status[keypair_name] = _get_resource_status_by_name("keypair", keypair_name.strip())
            
            # Prepare summary with post-action status
            summary_parts = [
                f"Bulk Keypair Management - Action: {action}",
                f"Total keypairs: {len(name_list)}",
                f"Successes: {len(successes)}",
                f"Failures: {len(failures)}"
            ]
            
            if successes:
                summary_parts.append(f"Successful keypairs: {', '.join(successes)}")
            if failures:
                summary_parts.append(f"Failed keypairs: {', '.join(failures)}")
                
            summary_parts.append("\nDetailed Results:")
            summary_parts.extend(results)
            
            # Add post-action status information
            summary_parts.append("\nPost-Action Status:")
            for keypair_name in name_list:
                current_status = post_action_status.get(keypair_name, 'Unknown')
                status_indicator = "🟢" if current_status in ["Available", "Active"] else "🔴" if current_status in ["Not Found", "ERROR"] else "🟡"
                summary_parts.append(f"{status_indicator} {keypair_name}: {current_status}")
            
            return "\n".join(summary_parts)
        
    except Exception as e:
        error_msg = f"Error: Failed to manage keypair(s) - {str(e)}"
        logger.error(error_msg)
        return error_msg
        logger.error(error_msg)
        return error_msg
