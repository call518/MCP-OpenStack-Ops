"""Tool implementation for set_routers."""

import json
from ..functions import (
    get_routers as _get_routers,
    set_routers as _set_routers,
)
from ..mcp_main import (
    _get_resource_status_by_name,
    conditional_tool,
    handle_operation_result,
    logger,
)

@conditional_tool
async def set_routers(
    action: str,
    router_names: str = "",
    # Filtering parameters for automatic target identification
    name_contains: str = "",
    # Router creation/update parameters
    description: str = "",
    admin_state_up: bool = True,
    ha: bool = False,
    distributed: bool = False,
    external_network_id: str = "",
    mtu: int = 1442,
    gateway_ip: str = "",
    subnet_id: str = "",
) -> str:
    """
    Manage OpenStack routers for network routing.
    Supports both direct targeting and filter-based bulk operations.

    Functions:
    - Create new routers with optional external gateway attachment
    - Update router properties including MTU and gateway configuration
    - Delete existing routers
    - Show router details
    - List all routers with filtering
    - Interface management: add/remove subnets from routers
    - Filter-based targeting: Automatically find targets using filtering conditions

    Use when user requests:
    - "Create router [name]"
    - "Delete router [name]"
    - "Update router [name]"
    - "Show router [name]"
    - "List all routers"
    - "Delete all routers with name containing 'test'"
    - "Create routers router1,router2,router3"
    - "Add subnet to router"

    Targeting Methods:
    1. Direct: Specify router_names directly
    2. Filter-based: Use name_contains to auto-identify targets

    Args:
        action: Action to perform - create, delete, update, set, show, list
        router_names: Name(s) of routers to manage. Support formats:
                      - Single: "router1"
                      - Multiple: "router1,router2,router3"
                      - List format: '["router1", "router2"]'
                      - Leave empty to use filtering parameters

        # Filtering parameters (alternative to router_names)
        name_contains: Filter routers whose names contain this string

        # Router creation parameters
        description: Description for the router
        admin_state_up: Administrative state (default: True)
        ha: Enable high availability (default: False)
        distributed: Enable distributed routing (default: False)
        external_network_id: External network ID for gateway attachment
        mtu: Explicit MTU value (≤1442)
        gateway_ip: Optional custom gateway IP
        subnet_id: Subnet ID for interface management

    Returns:
        Router management operation result with post-action status verification.

    Examples:
        # Direct targeting
        set_routers(action="delete", router_names="router1,router2")

        # Filter-based targeting
        set_routers(action="delete", name_contains="test")
        set_routers(action="create", router_names="new-router")

        # Create with gateway
        set_routers(action="create", router_names="gw-router", external_network_id="ext-net-1")
    """
    try:
        if not action or not action.strip():
            return "Error: Action is required (create, delete, update, set, show, list)"

        action = action.strip().lower()

        # Determine targeting method
        has_direct_targets = router_names and router_names.strip()
        has_filter_params = bool(name_contains)

        if not has_direct_targets and not has_filter_params:
            return "Error: Either specify router_names directly or provide filtering parameters (name_contains)"

        if has_direct_targets and has_filter_params:
            return "Error: Use either direct targeting (router_names) OR filtering parameters, not both"

        # Handle filter-based targeting
        if has_filter_params:
            logger.info(f"Using filter-based targeting for router action '{action}'")

            # Get all routers and filter
            all_routers_info = _get_routers()
            if not isinstance(all_routers_info, list):
                return "Error: Failed to retrieve router list for filtering"

            target_names = []
            for router in all_routers_info:
                router_name = router.get('name', '')

                # Apply filters
                if name_contains and name_contains.lower() not in router_name.lower():
                    continue

                target_names.append(router_name)

            if not target_names:
                return f"No routers found matching filter: name contains '{name_contains}'"

            logger.info(f"Filter-based targeting found {len(target_names)} routers: {target_names}")
            name_list = target_names

        else:
            # Handle direct targeting
            names_str = router_names.strip()

            # Handle JSON list format: ["name1", "name2"]
            if names_str.startswith('[') and names_str.endswith(']'):
                try:
                    import json
                    name_list = json.loads(names_str)
                    if not isinstance(name_list, list):
                        return "Error: Invalid JSON list format for router names"
                except json.JSONDecodeError:
                    return "Error: Invalid JSON format for router names"
            else:
                # Handle comma-separated format: "name1,name2" or "name1, name2"
                name_list = [name.strip() for name in names_str.split(',')]

            # Remove empty strings
            name_list = [name for name in name_list if name]

            if not name_list:
                return "Error: No valid router names provided"

        # Prepare kwargs for router operations
        kwargs = {}
        if description.strip():
            kwargs['description'] = description.strip()
        if external_network_id.strip():
            kwargs['external_network_id'] = external_network_id.strip()
        if mtu:
            kwargs['mtu'] = mtu
        if gateway_ip.strip():
            kwargs['gateway_ip'] = gateway_ip.strip()
        if subnet_id.strip():
            kwargs['subnet_id'] = subnet_id.strip()
        kwargs['admin_state_up'] = admin_state_up
        kwargs['ha'] = ha
        kwargs['distributed'] = distributed

        # Handle single router (backward compatibility)
        if len(name_list) == 1:
            router_name = name_list[0].strip()
            logger.info(f"Managing router '{router_name}' with action '{action}'")
            result = _set_routers(action, router_name, **kwargs)

            # Post-action status verification for single router
            import time
            time.sleep(2)  # Allow time for OpenStack operation to complete

            post_status = _get_resource_status_by_name("router", router_name)

            # Use centralized result handling with enhanced status info
            base_result = handle_operation_result(
                result,
                "Router Management",
                {
                    "Action": action,
                    "Router Name": router_name,
                    "Description": description.strip() or "Not provided",
                    "External Network": external_network_id.strip() or "Not attached",
                    "MTU": str(mtu) if mtu else "Default"
                }
            )

            # Add post-action status
            status_indicator = "🟢" if post_status in ["Available", "Active"] else "🔴" if post_status in ["Not Found", "ERROR"] else "🟡"
            enhanced_result = f"{base_result}\n\nPost-Action Status:\n{status_indicator} {router_name}: {post_status}"

            return enhanced_result

        # Handle bulk operations (multiple routers)
        else:
            logger.info(f"Managing {len(name_list)} routers with action '{action}': {name_list}")
            results = []
            successes = []
            failures = []

            for router_name in name_list:
                try:
                    result = _set_routers(action, router_name.strip(), **kwargs)

                    # Check if result indicates success or failure
                    if isinstance(result, dict):
                        if result.get('success', False):
                            successes.append(router_name.strip())
                            results.append(f"✓ {router_name.strip()}: {result.get('message', 'Success')}")
                        else:
                            failures.append(router_name.strip())
                            results.append(f"✗ {router_name.strip()}: {result.get('error', 'Unknown error')}")
                    elif isinstance(result, str):
                        # For string results, check if it contains error indicators
                        if 'error' in result.lower() or 'failed' in result.lower():
                            failures.append(router_name.strip())
                            results.append(f"✗ {router_name.strip()}: {result}")
                        else:
                            successes.append(router_name.strip())
                            results.append(f"✓ {router_name.strip()}: {result}")
                    else:
                        successes.append(router_name.strip())
                        results.append(f"✓ {router_name.strip()}: Operation completed")

                except Exception as e:
                    failures.append(router_name.strip())
                    results.append(f"✗ {router_name.strip()}: {str(e)}")

            # Post-action status verification for all processed routers
            logger.info("Verifying post-action status for routers")
            post_action_status = {}

            # Allow some time for OpenStack operations to complete
            import time
            time.sleep(2)

            for router_name in name_list:
                post_action_status[router_name.strip()] = _get_resource_status_by_name("router", router_name.strip())

            # Prepare summary with post-action status
            summary_parts = [
                f"Bulk Router Management - Action: {action}",
                f"Total routers: {len(name_list)}",
                f"Successes: {len(successes)}",
                f"Failures: {len(failures)}"
            ]

            if successes:
                summary_parts.append(f"Successful routers: {', '.join(successes)}")
            if failures:
                summary_parts.append(f"Failed routers: {', '.join(failures)}")

            summary_parts.append("\nDetailed Results:")
            summary_parts.extend(results)

            # Add post-action status information
            summary_parts.append("\nPost-Action Status:")
            for router_name in name_list:
                current_status = post_action_status.get(router_name.strip(), 'Unknown')
                status_indicator = "🟢" if current_status in ["Available", "Active"] else "🔴" if current_status in ["Not Found", "ERROR"] else "🟡"
                summary_parts.append(f"{status_indicator} {router_name.strip()}: {current_status}")

            return "\n".join(summary_parts)

    except Exception as e:
        error_msg = f"Error: Failed to manage router(s) - {str(e)}"
        logger.error(error_msg)
        return error_msg