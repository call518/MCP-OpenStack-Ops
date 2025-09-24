"""Tool implementation for set_networks."""

import json
from datetime import datetime
from ..functions import (
    get_network_details as _get_network_details,
    set_networks as _set_networks,
)
from ..mcp_main import (
    _get_resource_status_by_name,
    conditional_tool,
    handle_operation_result,
    logger,
)

@conditional_tool
async def set_networks(
    action: str,
    network_names: str = "",
    # Filtering parameters for automatic target identification  
    name_contains: str = "",
    status: str = "",
    # Network creation/modification parameters
    description: str = "",
    admin_state_up: bool = True,
    shared: bool = False,
    external: bool = False,
    provider_network_type: str = "",
    provider_physical_network: str = "",
    provider_segmentation_id: int = 0,
    mtu: int = 1500
) -> str:
    """
    Manage OpenStack networks for tenant isolation and connectivity.
    Supports both direct targeting and filter-based bulk operations.
    
    Functions:
    - Create new networks with provider settings and MTU configuration
    - Delete existing networks 
    - Update network properties (description, admin state, shared access)
    - List all networks with detailed configuration
    - Bulk operations: Apply action to multiple networks at once
    - Filter-based targeting: Automatically find targets using filtering conditions
    
    Use when user requests:
    - "Create network [name] with MTU [size]"
    - "Delete network [name]"
    - "Update network [name] description to [text]"
    - "Make network [name] shared/private"
    - "Delete all networks with name containing 'test'"
    - "List all networks"
    
    Targeting Methods:
    1. Direct: Specify network_names directly
    2. Filter-based: Use name_contains, status to auto-identify targets
    
    Args:
        action: Action to perform - list, create, delete, update
        network_names: Name(s) of networks to manage. Support formats:
                      - Single: "network1"
                      - Multiple: "network1,network2,network3"
                      - List format: '["network1", "network2"]'
                      - Leave empty to use filtering parameters
        
        # Filtering parameters (alternative to network_names)
        name_contains: Filter networks whose names contain this string
        status: Filter networks by status (e.g., "ACTIVE", "DOWN")
        
        # Creation/modification parameters
        description: Description for the network
        admin_state_up: Administrative state (default: True)
        shared: Allow sharing across tenants (default: False)
        external: Mark as external network for router gateway (default: False)
        provider_network_type: Provider network type (vlan, vxlan, flat, etc.)
        provider_physical_network: Physical network name for provider mapping
        provider_segmentation_id: VLAN ID or tunnel ID for network segmentation
        mtu: Maximum transmission unit size (default: 1500)
        
    Returns:
        Network management operation result with post-action status verification.
        
    Examples:
        # Direct targeting
        set_networks(action="delete", network_names="net1,net2")
        
        # Filter-based targeting
        set_networks(action="delete", name_contains="test")
        set_networks(action="create", network_names="new-net", description="New network")
    """
    try:
        if not action or not action.strip():
            return "Error: Action is required (create, delete, update, list)"
            
        action = action.strip().lower()
        
        # For list action, handle separately
        if action == 'list':
            logger.info("Listing all networks")
            result = _set_networks(action, "", **{
                'description': description,
                'admin_state_up': admin_state_up,
                'shared': shared,
                'external': external,
                'provider_network_type': provider_network_type,
                'provider_physical_network': provider_physical_network,
                'provider_segmentation_id': provider_segmentation_id,
                'mtu': mtu
            })
            return handle_operation_result(result, "Network Management", {"Action": action})
        
        # Determine targeting method
        has_direct_targets = network_names and network_names.strip()
        has_filter_params = any([name_contains, status])
        
        if not has_direct_targets and not has_filter_params:
            return "Error: Either specify network_names directly or provide filtering parameters (name_contains, status)"
        
        if has_direct_targets and has_filter_params:
            return "Error: Use either direct targeting (network_names) OR filtering parameters, not both"
        
        # Handle filter-based targeting
        if has_filter_params:
            logger.info(f"Using filter-based targeting for network action '{action}'")
            
            # Get all networks and filter
            all_networks_info = _get_network_details("all")
            if not isinstance(all_networks_info, list):
                return "Error: Failed to retrieve network list for filtering"
            
            target_names = []
            for network in all_networks_info:
                network_name = network.get('name', '')
                network_status = network.get('status', '')
                
                # Apply filters
                if name_contains and name_contains.lower() not in network_name.lower():
                    continue
                if status and status.upper() != network_status.upper():
                    continue
                    
                target_names.append(network_name)
            
            if not target_names:
                filter_desc = []
                if name_contains: filter_desc.append(f"name contains '{name_contains}'")
                if status: filter_desc.append(f"status = '{status}'")
                
                return f"No networks found matching filters: {', '.join(filter_desc)}"
            
            logger.info(f"Filter-based targeting found {len(target_names)} networks: {target_names}")
            name_list = target_names
        
        else:
            # Handle direct targeting
            names_str = network_names.strip()
            
            # Handle JSON list format: ["name1", "name2"]
            if names_str.startswith('[') and names_str.endswith(']'):
                try:
                    import json
                    name_list = json.loads(names_str)
                    if not isinstance(name_list, list):
                        return "Error: Invalid JSON list format for network names"
                except json.JSONDecodeError:
                    return "Error: Invalid JSON format for network names"
            else:
                # Handle comma-separated format: "name1,name2" or "name1, name2"
                name_list = [name.strip() for name in names_str.split(',')]
            
            # Remove empty strings
            name_list = [name for name in name_list if name]
            
            if not name_list:
                return "Error: No valid network names provided"
        
        # Prepare kwargs for network operations
        kwargs = {
            'description': description,
            'admin_state_up': admin_state_up,
            'shared': shared,
            'external': external,
            'provider_network_type': provider_network_type,
            'provider_physical_network': provider_physical_network,
            'provider_segmentation_id': provider_segmentation_id,
            'mtu': mtu
        }
        
        # Handle single network (backward compatibility)
        if len(name_list) == 1:
            logger.info(f"Managing network '{name_list[0]}' with action '{action}'")
            result = _set_networks(action, name_list[0].strip(), **kwargs)
            
            # Post-action status verification for single network
            import time
            time.sleep(2)  # Allow time for OpenStack operation to complete
            
            post_status = _get_resource_status_by_name("network", name_list[0].strip())
            
            # Use centralized result handling with enhanced status info
            base_result = handle_operation_result(
                result,
                "Network Management",
                {
                    "Action": action,
                    "Network": name_list[0],
                    "Description": description or "Not specified",
                    "MTU": mtu
                }
            )
            
            # Add post-action status
            status_indicator = "🟢" if post_status in ["ACTIVE", "Available"] else "🔴" if post_status in ["DOWN", "ERROR", "Not Found"] else "🟡"
            enhanced_result = f"{base_result}\n\nPost-Action Status:\n{status_indicator} {name_list[0]}: {post_status}"
            
            return enhanced_result
        
        # Handle bulk operations (multiple networks)
        else:
            logger.info(f"Managing {len(name_list)} networks with action '{action}': {name_list}")
            results = []
            successes = []
            failures = []
            
            for network_name in name_list:
                try:
                    result = _set_networks(action, network_name.strip(), **kwargs)
                    
                    # Check if result indicates success or failure
                    if isinstance(result, dict):
                        if result.get('success', False):
                            successes.append(network_name)
                            results.append(f"✓ {network_name}: {result.get('message', 'Success')}")
                        else:
                            failures.append(network_name)
                            results.append(f"✗ {network_name}: {result.get('error', 'Unknown error')}")
                    elif isinstance(result, str):
                        # For string results, check if it contains error indicators
                        if 'error' in result.lower() or 'failed' in result.lower():
                            failures.append(network_name)
                            results.append(f"✗ {network_name}: {result}")
                        else:
                            successes.append(network_name)
                            results.append(f"✓ {network_name}: {result}")
                    else:
                        successes.append(network_name)
                        results.append(f"✓ {network_name}: Operation completed")
                        
                except Exception as e:
                    failures.append(network_name)
                    results.append(f"✗ {network_name}: {str(e)}")
            
            # Post-action status verification for all processed networks
            logger.info("Verifying post-action status for networks")
            post_action_status = {}
            
            # Allow some time for OpenStack operations to complete
            import time
            time.sleep(2)
            
            for network_name in name_list:
                post_action_status[network_name] = _get_resource_status_by_name("network", network_name.strip())
            
            # Prepare summary with post-action status
            summary_parts = [
                f"Bulk Network Management - Action: {action}",
                f"Total networks: {len(name_list)}",
                f"Successes: {len(successes)}",
                f"Failures: {len(failures)}"
            ]
            
            if successes:
                summary_parts.append(f"Successful networks: {', '.join(successes)}")
            if failures:
                summary_parts.append(f"Failed networks: {', '.join(failures)}")
                
            summary_parts.append("\nDetailed Results:")
            summary_parts.extend(results)
            
            # Add post-action status information
            summary_parts.append("\nPost-Action Status:")
            for network_name in name_list:
                current_status = post_action_status.get(network_name, 'Unknown')
                status_indicator = "🟢" if current_status in ["ACTIVE", "Available"] else "🔴" if current_status in ["DOWN", "ERROR", "Not Found"] else "🟡"
                summary_parts.append(f"{status_indicator} {network_name}: {current_status}")
            
            return "\n".join(summary_parts)
        
    except Exception as e:
        error_msg = f"Error: Failed to manage network(s) - {str(e)}"
        logger.error(error_msg)
        return error_msg
    """
    Manage OpenStack networks for tenant isolation and connectivity
    
    Functions:
    - Create new networks with provider settings and MTU configuration
    - Delete existing networks 
    - Update network properties (description, admin state, shared access)
    - List all networks with detailed configuration
    
    Use when user requests:
    - "Create network [name] with MTU [size]"
    - "Delete network [name]"
    - "Update network [name] description to [text]"
    - "Make network [name] shared/private"
    - "List all networks"
    
    Args:
        action: Action to perform - list, create, delete, update
        network_name: Name of the network (required for create/delete/update)
        description: Description for the network
        admin_state_up: Administrative state (default: True)
        shared: Allow sharing across tenants (default: False)
        external: Mark as external network for router gateway (default: False)
        provider_network_type: Provider network type (vlan, vxlan, flat, etc.)
        provider_physical_network: Physical network name for provider mapping
        provider_segmentation_id: VLAN ID or tunnel ID for network segmentation
        mtu: Maximum transmission unit size (default: 1500)
        
    Returns:
        JSON string with network management operation results
    """
    try:
        logger.info(f"Managing network with action '{action}'" + (f" for network '{network_name}'" if network_name.strip() else ""))
        
        kwargs = {
            'description': description.strip() if description.strip() else None,
            'admin_state_up': admin_state_up,
            'shared': shared,
            'external': external,
            'mtu': mtu if mtu > 0 else 1500
        }
        
        # Provider network settings
        if provider_network_type.strip():
            kwargs['provider_network_type'] = provider_network_type.strip()
        if provider_physical_network.strip():
            kwargs['provider_physical_network'] = provider_physical_network.strip()
        if provider_segmentation_id > 0:
            kwargs['provider_segmentation_id'] = provider_segmentation_id
        
        # For list action, use empty string if no network_name provided
        result_data = _set_networks(
            action=action,
            network_name=network_name if network_name else None,
            **kwargs
        )
        
        result = {
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "parameters": {"network_name": network_name, **kwargs},
            "result": result_data
        }
        
        return json.dumps(result, indent=2)
        
    except Exception as e:
        return json.dumps({
            'success': False,
            'message': f'Failed to manage network: {str(e)}',
            'error': str(e)
        }, indent=2)
