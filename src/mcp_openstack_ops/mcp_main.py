import argparse
import logging
import os
import sys
from typing import Any, Optional, Dict, List
from fastmcp import FastMCP
from fastmcp.server.auth import StaticTokenVerifier

# Add the current directory to sys.path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def handle_operation_result(result: Dict[str, Any], operation_name: str, details: Dict[str, str] = None) -> str:
    """
    Handle operation results consistently across all MCP tools.
    
    Args:
        result: Result dictionary from core function
        operation_name: Name of the operation (e.g., "Instance Management", "Network Creation")
        details: Additional details to include in error message (optional)
    
    Returns:
        Success JSON or clear error message
    """
    # Check if result is None or empty
    if not result:
        error_response = f"❌ **{operation_name} Failed**\n\n**Error**: No response received from OpenStack API. The operation may have failed or timed out."
        
        if details:
            details_str = '\n'.join([f"**{k}**: {v}" for k, v in details.items()])
            error_response += f"\n\n{details_str}"
            error_response += "\n\n**Recommendation**: Please verify the operation status and try again if needed."
            
        return error_response
    
    # Check if operation failed and return clear error message
    if isinstance(result, dict) and result.get('success') is False:
        error_message = result.get('message', 'Unknown error occurred')
        
        error_response = f"❌ **{operation_name} Failed**\n\n**Error**: {error_message}"
        
        if details:
            details_str = '\n'.join([f"**{k}**: {v}" for k, v in details.items()])
            error_response += f"\n\n{details_str}"
            
        return error_response
    
    # Enhanced handling for successful operations with tool-specific async guidance
    if isinstance(result, dict) and result.get('success') is True:
        # Extract operation details from various parameter structures
        action = details.get('Action', 'operation') if details else 'operation'
        resource_name = (details.get('Instance') or details.get('Volume') or 
                        details.get('Network') or details.get('Stack') or 
                        details.get('Image') or details.get('Keypair') or 'resource') if details else 'resource'
        
        # Tool-specific async handling and verification commands
        async_operations = {
            "Instance Management": {
                "async_actions": ["start", "stop", "restart", "reboot", "create", "delete", "resize", "rebuild"],
                "timing": "30-60 seconds",
                "verify_cmd": f"Show instance status for {resource_name}"
            },
            "Volume Management": {
                "async_actions": ["create", "delete", "extend", "attach", "detach"],
                "timing": "10-30 seconds", 
                "verify_cmd": "List all volumes"
            },
            "Network Management": {
                "async_actions": ["create", "delete"],
                "timing": "5-15 seconds",
                "verify_cmd": "Show all networks"
            },
            "Heat Stack Management": {
                "async_actions": ["create", "update", "delete"],
                "timing": "2-10 minutes",
                "verify_cmd": "List all Heat stacks"
            },
            "Image Management": {
                "async_actions": ["create", "delete", "update"],
                "timing": "1-5 minutes",
                "verify_cmd": "List available images"
            },
            "Quota Management": {
                "async_actions": [],  # Usually synchronous
                "timing": "immediate",
                "verify_cmd": "Show quota usage and limits"
            },
            "Keypair Management": {
                "async_actions": [],  # Usually synchronous
                "timing": "immediate", 
                "verify_cmd": "List all keypairs"
            }
        }
        
        tool_config = async_operations.get(operation_name, {
            "async_actions": ["create", "delete", "update"],
            "timing": "variable",
            "verify_cmd": f"Check {operation_name.lower()} status"
        })
        
        # Only add async note for operations that are actually asynchronous
        if action.lower() in tool_config.get("async_actions", []):
            if "message" in result:
                timing = tool_config.get("timing", "variable")
                verify_cmd = tool_config.get("verify_cmd", f"Check {operation_name.lower()} status")
                
                result["message"] += f"\n\n📋 Note: This is an asynchronous operation. The {action} command has been initiated successfully (expected completion: {timing}). You can verify the status using '{verify_cmd}'."
            
            result["operation_type"] = "asynchronous"
            result["verification_needed"] = True
        else:
            # For synchronous operations, just mark as completed
            result["operation_type"] = "synchronous"
            result["verification_needed"] = False
    
    # Return formatted JSON response
    try:
        return json.dumps(result, indent=2, ensure_ascii=False)
    except Exception as e:
        # Fallback for JSON serialization issues
        return f"Operation completed but response formatting failed: {str(e)}"
        
        # Return formatted JSON for other successful dict results
        try:
            return json.dumps(result, indent=2, ensure_ascii=False)
        except Exception as json_error:
            return f"✅ **{operation_name} Successful**\n\nOperation completed but response formatting failed: {str(json_error)}"
    
    # Return string results as-is
    return str(result) if result else "❌ **Operation Failed**: Empty response"

from .connection import get_openstack_connection
from .services.compute import search_instances as _search_instances
from .functions import (
    get_service_status as _get_service_status, 
    get_instance_details as _get_instance_details, 
    get_instance_by_name as _get_instance_by_name,
    get_instance_by_id as _get_instance_by_id,
    get_instances_by_status as _get_instances_by_status,
    get_network_details as _get_network_details,
    set_instance as _set_instance,
    set_volume as _set_volume,
    get_resource_monitoring as _get_resource_monitoring,
    get_project_info as _get_project_info,
    get_flavor_list as _get_flavor_list,
    get_image_list as _get_image_list,
    reset_connection_cache,
    # Identity (Keystone) functions
    get_user_list as _get_user_list,
    get_role_assignments as _get_role_assignments,
    # Compute (Nova) enhanced functions
    get_keypair_list as _get_keypair_list,
    set_keypair as _set_keypair,
    get_security_groups as _get_security_groups,
    # Extended Server Management functions
    set_server_network as _set_server_network,
    set_server_floating_ip as _set_server_floating_ip,
    set_server_fixed_ip as _set_server_fixed_ip,
    set_server_security_group as _set_server_security_group,
    set_server_migration as _set_server_migration,
    set_server_properties as _set_server_properties,
    create_server_backup as _set_server_backup,
    create_server_dump as _set_server_dump,
    # Network (Neutron) enhanced functions
    get_floating_ips as _get_floating_ips,
    set_floating_ip as _set_floating_ip,
    get_routers as _get_routers,
    # Block Storage (Cinder) enhanced functions
    get_volume_types as _get_volume_types,
    get_volume_snapshots as _get_volume_snapshots,
    set_snapshot as _set_snapshot,
    set_volume_backups as _set_volume_backups,
    set_volume_groups as _set_volume_groups,
    set_volume_qos as _set_volume_qos,
    set_network_ports as _set_network_ports,
    set_networks as _set_networks,
    set_subnets as _set_subnets,
    get_floating_ip_pools as _get_floating_ip_pools,
    set_floating_ip_port_forwarding as _set_floating_ip_port_forwarding,
    set_network_qos_policies as _set_network_qos_policies,
    set_network_agents as _set_network_agents,
    # Load Balancer (Octavia) functions
    get_load_balancer_list as _get_load_balancer_list,
    get_load_balancer_details as _get_load_balancer_details,
    set_load_balancer as _set_load_balancer,
    get_load_balancer_listeners as _get_load_balancer_listeners,
    set_load_balancer_listener as _set_load_balancer_listener,
    get_load_balancer_pools as _get_load_balancer_pools,
    set_load_balancer_pool as _set_load_balancer_pool,
    get_load_balancer_pool_members as _get_load_balancer_pool_members,
    set_load_balancer_pool_member as _set_load_balancer_pool_member,
    get_load_balancer_health_monitors as _get_load_balancer_health_monitors,
    set_load_balancer_health_monitor as _set_load_balancer_health_monitor,
    # Load Balancer Advanced functions
    get_load_balancer_l7_policies as _get_load_balancer_l7_policies,
    set_load_balancer_l7_policy as _set_load_balancer_l7_policy,
    get_load_balancer_l7_rules as _get_load_balancer_l7_rules,
    set_load_balancer_l7_rule as _set_load_balancer_l7_rule,
    get_load_balancer_amphorae as _get_load_balancer_amphorae,
    set_load_balancer_amphora as _set_load_balancer_amphora,
    get_load_balancer_availability_zones as _get_load_balancer_availability_zones,
    set_load_balancer_availability_zone as _set_load_balancer_availability_zone,
    get_load_balancer_flavors as _get_load_balancer_flavors,
    set_load_balancer_flavor as _set_load_balancer_flavor,
    get_load_balancer_providers as _get_load_balancer_providers,
    get_load_balancer_quotas as _get_load_balancer_quotas,
    set_load_balancer_quota as _set_load_balancer_quota,
    get_load_balancer_amphorae as _get_load_balancer_amphorae,
    set_load_balancer_amphora as _set_load_balancer_amphora,
    set_image_members as _set_image_members,
    set_image_metadata as _set_image_metadata,
    set_image_visibility as _set_image_visibility,
    set_domains as _set_domains,
    set_identity_groups as _set_identity_groups,
    set_roles as _set_roles,
    set_services as _set_services,
    # Monitoring and operational functions
    set_service_logs as _set_service_logs,
    set_metrics as _set_metrics,
    set_alarms as _set_alarms,
    set_compute_agents as _set_compute_agents,
    # Image Service (Glance) enhanced functions
    set_image as _set_image,
    # Heat Stack functions
    get_heat_stacks as _get_heat_stacks,
    set_heat_stack as _set_heat_stack,
    # Read-only functions extracted from set_* functions
    get_volume_list as _get_volume_list,
    get_image_detail_list as _get_image_detail_list,
    get_usage_statistics as _get_usage_statistics,
    # Quota and Project Management
    get_quota as _get_quota,
    set_quota as _set_quota,
    get_project_details as _get_project_details,
    set_project as _set_project,
    # New enhanced server management functions
    get_server_events as _get_server_events,
    get_server_groups as _get_server_groups,
    set_server_group as _set_server_group,
    get_hypervisor_details as _get_hypervisor_details,
    get_availability_zones as _get_availability_zones,
    set_flavor as _set_flavor,
    get_server_volumes as _get_server_volumes,
    set_server_volume as _set_server_volume
)

import json
from datetime import datetime
from openstack import connection

# Set up logging (initial level from env; may be overridden by --log-level)
logging.basicConfig(
    level=os.environ.get("MCP_LOG_LEVEL", "INFO"),
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("OpenStackService")

# =============================================================================
# Authentication Setup
# =============================================================================

# Check environment variables for authentication early
_auth_enable = os.environ.get("REMOTE_AUTH_ENABLE", "false").lower() == "true"
_secret_key = os.environ.get("REMOTE_SECRET_KEY", "")

# Initialize the main MCP instance with authentication if configured
if _auth_enable and _secret_key:
    logger.info("Initializing MCP instance with Bearer token authentication (from environment)")
    
    # Create token configuration
    tokens = {
        _secret_key: {
            "client_id": "openstack-ops-client",
            "user": "admin",
            "scopes": ["read", "write"],
            "description": "OpenStack operations access token"
        }
    }
    
    auth = StaticTokenVerifier(tokens=tokens)
    mcp = FastMCP("openstack-ops", auth=auth)
    logger.info("MCP instance initialized with authentication")
else:
    logger.info("Initializing MCP instance without authentication")
    mcp = FastMCP("openstack-ops")

# =============================================================================
# Safety Control Functions
# =============================================================================

def _get_resource_status_by_name(resource_type: str, resource_name: str) -> str:
    """Helper function to get current status of a resource by name."""
    try:
        if resource_type == "instance":
            instance_info = _get_instance_by_name(resource_name.strip())
            return instance_info.get('status', 'Unknown') if instance_info else 'Not Found'
        
        elif resource_type == "volume":
            volumes = _get_volume_list()
            for volume in volumes:
                if volume.get('name') == resource_name.strip():
                    return volume.get('status', 'Unknown')
            return 'Not Found'
            
        elif resource_type == "image":
            images = _get_image_detail_list()
            if isinstance(images, list):
                for image in images:
                    if image.get('name') == resource_name.strip():
                        return image.get('status', 'Unknown')
            return 'Not Found'
        
        elif resource_type == "network":
            # Get network details from network listing
            network_info = _get_network_details(resource_name.strip())
            if isinstance(network_info, list) and network_info:
                return network_info[0].get('status', 'Unknown')
            return 'Not Found'
            
        elif resource_type == "keypair":
            keypairs = _get_keypair_list()
            if isinstance(keypairs, list):
                for keypair in keypairs:
                    if keypair.get('name') == resource_name.strip():
                        return 'Available'  # Keypairs don't have status, just exist or not
            return 'Not Found'
            
        else:
            return 'Unknown Resource Type'
            
    except Exception as e:
        return f'Status Check Failed: {str(e)}'

def _is_modify_operation_allowed() -> bool:
    """Check if modify operations are allowed based on environment variable."""
    return os.environ.get("ALLOW_MODIFY_OPERATIONS", "false").lower() == "true"

def _check_modify_operation_permission() -> str:
    """Check and return error message if modify operations are not allowed."""
    if not _is_modify_operation_allowed():
        return """
❌ **MODIFY OPERATION BLOCKED**

This operation can modify or delete OpenStack resources and has been disabled for safety.

To enable modify operations, set the following in your .env file:
```
ALLOW_MODIFY_OPERATIONS=true
```

**⚠️  WARNING**: Only enable this in development or testing environments where data loss is acceptable.

**Read-only operations available:**
- get_cluster_status, get_service_status
- get_instance_details, search_instances
- get_network_details, get_project_info
- get_flavor_list, get_image_list, get_user_list
- get_keypair_list, get_security_groups
- get_floating_ips, get_routers, get_volume_types
- get_volume_snapshots, get_heat_stacks
- get_resource_monitoring, get_usage_statistics, get_quota
- get_volume_list, get_image_detail_list, get_project_details
"""
    return ""

def conditional_tool(func):
    """
    Decorator that conditionally registers tools based on ALLOW_MODIFY_OPERATIONS setting.
    Modify operations are only registered when explicitly enabled.
    """
    if _is_modify_operation_allowed():
        return mcp.tool()(func)
    else:
        # Return the function without registering it as a tool
        return func

# =============================================================================
# MCP Tools (OpenStack Operations and Monitoring)
# =============================================================================

# get_cluster_status tool removed - use combination of get_* tools for comprehensive cluster reports


@mcp.tool()
async def get_service_status() -> str:
    """
    Provides status and health check information for each OpenStack service.
    
    Functions:
    - Check active status of all OpenStack services
    - Verify API endpoint responsiveness for each service
    - Collect detailed status and version information per service
    - Detect and report service failures or error conditions
    
    Use when user requests service status, API status, health checks, or service troubleshooting.
    
    Returns:
        Service status information in JSON format with service details and health summary.
    """
    try:
        logger.info("Fetching OpenStack service status")
        services = _get_service_status()
        
        # services is a list, not a dict
        enabled_services = [s for s in services if s.get('status') == 'enabled']
        running_services = [s for s in services if s.get('state') == 'up']
        
        result = {
            "timestamp": datetime.now().isoformat(),
            "service_status": services,
            "summary": {
                "total_services": len(services),
                "enabled_services": len(enabled_services),
                "running_services": len(running_services),
                "service_types": list(set(s.get('service_type', 'unknown') for s in services))
            }
        }
        
        return json.dumps(result, indent=2, ensure_ascii=False)
        
    except Exception as e:
        error_msg = f"Error: Failed to fetch OpenStack service status - {str(e)}"
        logger.error(error_msg)
        return error_msg


# ===== UNIFIED INSTANCE QUERY TOOL =====
@mcp.tool()
async def get_instance(
    names: str = "",
    ids: str = "",
    status: str = "",
    search_term: str = "",
    search_in: str = "name",
    all_instances: bool = False,
    detailed: bool = True,
    limit: int = 50,
    offset: int = 0,
    case_sensitive: bool = False
) -> str:
    """
    Unified instance query tool supporting all instance retrieval patterns.
    Consolidates functionality from get_instance_details, get_instance_by_name, get_instances_by_status, and search_instances.
    
    Functions:
    - Get specific instances by names or IDs
    - Filter instances by status (ACTIVE, SHUTOFF, ERROR, etc.)
    - Search instances across multiple fields (name, flavor, image, host, etc.)
    - List all instances with pagination
    - Support both summary and detailed information modes
    
    Use when user requests instance information, status checks, or instance searches.
    
    Args:
        names: Specific instance name(s) to retrieve (comma-separated: "vm1,vm2,vm3")
        ids: Specific instance ID(s) to retrieve (comma-separated)
        status: Filter by instance status (e.g., "ACTIVE", "SHUTOFF", "ERROR")
        search_term: Search term for partial matching across fields
        search_in: Fields to search in ("name", "status", "host", "flavor", "image", "availability_zone", "all")
        all_instances: If True, retrieve all instances (ignores other filters)
        detailed: If True, return detailed information; if False, return summary only
        limit: Maximum instances to return (default: 50, max: 200)
        offset: Number of instances to skip for pagination
        case_sensitive: Case-sensitive search (default: False)
        
    Returns:
        Instance information in JSON format with metadata and pagination info.
        
    Examples:
        get_instance(names="vm1,vm2")                    # Get specific instances
        get_instance(status="SHUTOFF")                   # Get all stopped instances
        get_instance(search_term="web", search_in="name") # Search by name
        get_instance(all_instances=True, detailed=False) # List all (summary)
    """
    try:
        # Determine query method
        has_direct_names = names and names.strip()
        has_direct_ids = ids and ids.strip()
        has_status_filter = status and status.strip()
        has_search = search_term and search_term.strip()
        
        result_data = None
        query_description = ""
        
        if all_instances:
            # Get all instances
            logger.info("Fetching all instances")
            result_data = _get_instance_details(
                instance_names=None,
                limit=limit,
                offset=offset,
                include_all=True
            )
            query_description = "All instances"
            
        elif has_direct_names:
            # Get specific instances by names
            logger.info(f"Fetching instances by names: {names}")
            names_list = [name.strip() for name in names.split(',') if name.strip()]
            result_data = _get_instance_details(
                instance_names=names_list,
                limit=limit,
                offset=offset,
                include_all=True
            )
            query_description = f"Instances by names: {names}"
            
        elif has_direct_ids:
            # Get specific instances by IDs
            logger.info(f"Fetching instances by IDs: {ids}")
            # For IDs, we need to use names parameter since the function doesn't support IDs directly
            ids_list = [id.strip() for id in ids.split(',') if id.strip()]
            result_data = _get_instance_details(
                instance_names=ids_list,  # Use IDs as names for now
                limit=limit,
                offset=offset,
                include_all=True
            )
            query_description = f"Instances by IDs: {ids}"
            
        elif has_status_filter:
            # Filter by status
            logger.info(f"Fetching instances with status: {status}")
            instances = _get_instances_by_status(status.upper())
            
            # Apply pagination
            total_count = len(instances)
            paginated_instances = instances[offset:offset + limit] if instances else []
            
            result_data = {
                "timestamp": datetime.now().isoformat(),
                "query_type": "status_filter",
                "status_filter": status.upper(),
                "total_instances": total_count,
                "instances_returned": len(paginated_instances),
                "limit": limit,
                "offset": offset,
                "instances": paginated_instances
            }
            query_description = f"Instances with status: {status}"
            
        elif has_search:
            # Search instances
            logger.info(f"Searching instances for '{search_term}' in '{search_in}'")
            result_data = _search_instances(
                search_term=search_term,
                search_fields=search_in.split(',') if search_in else ['name'],
                limit=limit,
                include_inactive=True
            )
            
            # Enhance result with metadata
            if isinstance(result_data, list):
                result_data = {
                    "timestamp": datetime.now().isoformat(),
                    "query_type": "search",
                    "search_term": search_term,
                    "search_in": search_in,
                    "case_sensitive": case_sensitive,
                    "total_instances": len(result_data),
                    "instances": result_data
                }
            elif isinstance(result_data, dict) and 'instances' not in result_data:
                result_data["query_type"] = "search"
                result_data["search_term"] = search_term
                result_data["search_in"] = search_in
                
            query_description = f"Search results for '{search_term}' in '{search_in}'"
            
        else:
            return "Error: Specify at least one query parameter (names, ids, status, search_term, or all_instances=True)"
        
        # Handle detailed vs summary mode
        if not detailed and isinstance(result_data, dict) and 'instances' in result_data:
            # Convert to summary mode
            summary_instances = []
            for instance in result_data['instances']:
                summary_instances.append({
                    'id': instance.get('id', ''),
                    'name': instance.get('name', ''),
                    'status': instance.get('status', ''),
                    'flavor': instance.get('flavor', ''),
                    'image': instance.get('image', '')
                })
            result_data['instances'] = summary_instances
            result_data['mode'] = 'summary'
        elif detailed and isinstance(result_data, dict):
            result_data['mode'] = 'detailed'
        
        # Add query metadata
        if isinstance(result_data, dict):
            result_data['query_description'] = query_description
            result_data['detailed'] = detailed
        
        return json.dumps(result_data, indent=2, ensure_ascii=False)
        
    except Exception as e:
        error_msg = f"Error: Failed to query instances - {str(e)}"
        logger.error(error_msg)
        return error_msg


# ===== LEGACY INSTANCE TOOLS (Deprecated - Use get_instance instead) =====
@mcp.tool()
async def get_instance_details(
    instance_names: str = "", 
    instance_ids: str = "", 
    all_instances: bool = False,
    limit: int = 50,
    offset: int = 0,
    include_all: bool = False
) -> str:
    """
    Provides detailed information and status for OpenStack instances with pagination support.
    
    Functions:
    - Query basic instance information (name, ID, status, image, flavor) with efficient pagination
    - Collect network connection status and IP address information
    - Check CPU, memory, storage resource usage and allocation
    - Provide instance metadata, keypair, and security group settings
    - Support large-scale environments with configurable limits
    
    Use when user requests specific instance information, VM details, server analysis, or instance troubleshooting.
    
    Args:
        instance_names: Comma-separated list of instance names to query (optional)
        instance_ids: Comma-separated list of instance IDs to query (optional)
        all_instances: If True, returns all instances (default: False)
        limit: Maximum number of instances to return (default: 50, max: 200)
        offset: Number of instances to skip for pagination (default: 0)
        include_all: If True, ignore pagination limits (use with caution in large environments)
        
    Returns:
        Instance detailed information in JSON format with instance, network, resource data, and pagination info.
    """
    try:
        logger.info(f"Fetching instance details - names: {instance_names}, ids: {instance_ids}, all: {all_instances}, limit: {limit}, offset: {offset}")
        
        names_list = None
        ids_list = None
        
        if instance_names.strip():
            names_list = [name.strip() for name in instance_names.split(',') if name.strip()]
            
        if instance_ids.strip():
            ids_list = [id.strip() for id in instance_ids.split(',') if id.strip()]
        
        # Call the updated function with pagination parameters
        combined_names_ids = []
        if names_list:
            combined_names_ids.extend(names_list)
        if ids_list:
            combined_names_ids.extend(ids_list)
        
        if all_instances or (not names_list and not ids_list):
            details_result = _get_instance_details(
                instance_names=None,
                limit=limit, 
                offset=offset, 
                include_all=include_all
            )
        else:
            details_result = _get_instance_details(
                instance_names=combined_names_ids,
                limit=limit, 
                offset=offset, 
                include_all=include_all
            )
        
        # Handle both old return format (list) and new return format (dict)
        if isinstance(details_result, dict):
            instances = details_result.get('instances', [])
            pagination_info = details_result.get('pagination', {})
            performance_info = details_result.get('performance', {})
        else:
            # Backward compatibility with old list return format
            instances = details_result
            pagination_info = {}
            performance_info = {}
        
        result = {
            "timestamp": datetime.now().isoformat(),
            "filter_applied": {
                "instance_names": names_list,
                "instance_ids": ids_list,
                "all_instances": all_instances
            },
            "pagination": {
                "limit": limit,
                "offset": offset,
                "include_all": include_all,
                **pagination_info
            },
            "instances_found": len(instances),
            "instance_details": instances,
            "performance": performance_info
        }
        
        return json.dumps(result, indent=2, ensure_ascii=False)
        
    except Exception as e:
        error_msg = f"Error: Failed to fetch instance details - {str(e)}"
        logger.error(error_msg)
        return error_msg


@mcp.tool()
async def search_instances(
    search_term: str, 
    search_in: str = "name",
    limit: int = 50,
    offset: int = 0,
    case_sensitive: bool = False
) -> str:
    """
    Search for OpenStack instances based on various criteria with efficient pagination.
    
    Functions:
    - Search instances by name, status, host, flavor, image, or availability zone
    - Support partial matching with configurable case sensitivity
    - Return detailed information for matching instances with pagination
    - Optimized for large-scale environments with intelligent filtering
    
    Args:
        search_term: Term to search for (supports partial matching)
        search_in: Field to search in ('name', 'status', 'host', 'flavor', 'image', 'availability_zone', 'all')
        limit: Maximum number of matching instances to return (default: 50, max: 200)
        offset: Number of matching instances to skip for pagination (default: 0)
        case_sensitive: If True, performs case-sensitive search (default: False)
        
    Returns:
        List of matching instances with detailed information and pagination metadata
    """
    try:
        logger.info(f"Searching instances for '{search_term}' in '{search_in}' with limit {limit}, offset {offset}")
        
        search_result = _search_instances(
            search_term=search_term, 
            search_fields=search_in.split(',') if search_in else ['name', 'id'],
            limit=limit,
            include_inactive=True  # 모든 인스턴스를 검색하기 위해
        )
        
        # Handle both old return format (list) and new return format (dict)
        if isinstance(search_result, list):
            instances = search_result
            search_info = {
                'search_term': search_term,
                'search_in': search_in,
                'case_sensitive': case_sensitive,
                'matches_found': len(instances)
            }
            pagination_info = {'limit': limit, 'offset': offset, 'has_more': False}
            performance_info = {}
        elif isinstance(search_result, dict):
            instances = search_result.get('instances', [])
            search_info = search_result.get('search_info', {})
            pagination_info = search_result.get('pagination', {})
            performance_info = search_result.get('performance', {})
        else:
            # Fallback for unexpected format
            instances = []
            search_info = {'search_term': search_term, 'matches_found': 0}
            pagination_info = {'limit': limit, 'offset': offset, 'has_more': False}
            performance_info = {}
        
        result = {
            "timestamp": datetime.now().isoformat(),
            "search_info": search_info,
            "pagination": pagination_info,
            "instances_found": len(instances),
            "matching_instances": instances,
            "performance": performance_info
        }
        
        return json.dumps(result, indent=2, ensure_ascii=False)
        
    except Exception as e:
        error_msg = f"Error: Failed to search instances - {str(e)}"
        logger.error(error_msg)
        return error_msg
        
    except Exception as e:
        error_msg = f"Error: Failed to search instances - {str(e)}"
        logger.error(error_msg)
        return error_msg


@mcp.tool()
async def get_instance_by_name(instance_name: str) -> str:
    """
    Get detailed information for a specific instance by name.
    
    Args:
        instance_name: Name of the instance to retrieve
        
    Returns:
        Instance detailed information or error message if not found
    """
    try:
        logger.info(f"Getting instance by name: {instance_name}")
        
        instance = _get_instance_by_name(instance_name)
        
        if not instance:
            return f"Instance '{instance_name}' not found"
        
        result = {
            "timestamp": datetime.now().isoformat(),
            "instance_name": instance_name,
            "instance_details": instance
        }
        
        return json.dumps(result, indent=2, ensure_ascii=False)
        
    except Exception as e:
        error_msg = f"Error: Failed to get instance '{instance_name}' - {str(e)}"
        logger.error(error_msg)
        return error_msg


@mcp.tool()
async def get_instances_by_status(status: str) -> str:
    """
    Get instances filtered by status.
    
    Args:
        status: Instance status to filter by (ACTIVE, SHUTOFF, ERROR, BUILDING, etc.)
        
    Returns:
        List of instances with the specified status
    """
    try:
        logger.info(f"Getting instances with status: {status}")
        
        instances = _get_instances_by_status(status.upper())
        
        result = {
            "timestamp": datetime.now().isoformat(),
            "status_filter": status.upper(),
            "instances_found": len(instances),
            "instances": instances
        }
        
        return json.dumps(result, indent=2, ensure_ascii=False)
        
    except Exception as e:
        error_msg = f"Error: Failed to get instances with status '{status}' - {str(e)}"
        logger.error(error_msg)
        return error_msg


@mcp.tool()  
async def get_network_details(network_name: str = "all") -> str:
    """
    Provides detailed information for OpenStack networks, subnets, routers, and security groups.
    
    Functions:
    - Query configuration information for specified network or all networks
    - Check subnet configuration and IP allocation status per network
    - Collect router connection status and gateway configuration
    - Analyze security group rules and port information
    
    Use when user requests network information, subnet details, router configuration, or network troubleshooting.
    
    Args:
        network_name: Name of network to query or "all" for all networks (default: "all")
        
    Returns:
        Network detailed information in JSON format with networks, subnets, routers, and security groups.
    """
    try:
        logger.info(f"Fetching network details: {network_name}")
        details = _get_network_details(network_name)
        
        result = {
            "timestamp": datetime.now().isoformat(), 
            "requested_network": network_name,
            "network_details": details
        }
        
        return json.dumps(result, indent=2, ensure_ascii=False)
        
    except Exception as e:
        error_msg = f"Error: Failed to fetch network information - {str(e)}"
        logger.error(error_msg)
        return error_msg


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


# ===== EXTENDED SERVER MANAGEMENT TOOLS =====

@conditional_tool
async def set_server_network(
    instance_name: str,
    action: str,
    network: str = "",
    port: str = "",
    fixed_ip: str = ""
) -> str:
    """
    Manage server network operations (add/remove networks and ports).
    
    Functions:
    - Add network to server with optional fixed IP
    - Remove network from server (removes all ports on that network)
    - Add specific port to server
    - Remove specific port from server
    
    Use when user requests:
    - "Add network X to server Y"
    - "Remove network X from server Y"
    - "Attach port X to server Y"
    - "Detach port X from server Y"
    
    Args:
        instance_name: Name or ID of the server
        action: Action to perform (add_network, remove_network, add_port, remove_port)
        network: Network name or ID (for network operations)
        port: Port ID (for port operations)
        fixed_ip: Optional fixed IP address when adding network
        
    Returns:
        JSON string containing operation results
    """
    try:
        logger.info(f"Managing server network: {instance_name}, action: {action}")
        
        kwargs = {
            'network': network,
            'port': port,
            'fixed_ip': fixed_ip
        }
        
        result = _set_server_network(instance_name.strip(), action.strip(), **kwargs)
        
        # Use centralized result handling
        return handle_operation_result(
            result,
            "Server Network Management", 
            {
                "Action": action,
                "Instance": instance_name,
                "Network": network or "Not specified",
                "Port": port or "Not specified"
            }
        )
        
    except Exception as e:
        error_msg = f"Error: Failed to manage server network - {str(e)}"
        logger.error(error_msg)
        return json.dumps({
            "timestamp": datetime.now().isoformat(),
            "error": error_msg,
            "success": False
        }, indent=2)


@conditional_tool
async def set_server_floating_ip(
    instance_name: str,
    action: str,
    floating_ip: str,
    fixed_ip: str = ""
) -> str:
    """
    Manage server floating IP operations (add/remove).
    
    Functions:
    - Associate floating IP to server
    - Disassociate floating IP from server
    - Automatically find target fixed IP if not specified
    
    Use when user requests:
    - "Add floating IP X to server Y"
    - "Remove floating IP X from server Y"
    - "Associate floating IP X with server Y"
    - "Disassociate floating IP X from server Y"
    
    Args:
        instance_name: Name or ID of the server
        action: Action to perform (add, remove)
        floating_ip: Floating IP address or ID
        fixed_ip: Target fixed IP address (auto-detected if not specified)
        
    Returns:
        JSON string containing operation results
    """
    try:
        logger.info(f"Managing server floating IP: {instance_name}, action: {action}")
        
        kwargs = {
            'floating_ip': floating_ip,
            'fixed_ip': fixed_ip
        }
        
        result = _set_server_floating_ip(instance_name.strip(), action.strip(), **kwargs)
        
        # Use centralized result handling
        return handle_operation_result(
            result,
            "Server Floating IP Management",
            {
                "Action": action,
                "Instance": instance_name,
                "Floating IP": floating_ip or "Not specified",
                "Fixed IP": fixed_ip or "Not specified"
            }
        )
        
    except Exception as e:
        error_msg = f"Error: Failed to manage server floating IP - {str(e)}"
        logger.error(error_msg)
        return json.dumps({
            "timestamp": datetime.now().isoformat(),
            "error": error_msg,
            "success": False
        }, indent=2)


@conditional_tool
async def set_server_fixed_ip(
    instance_name: str,
    action: str,
    network: str = "",
    fixed_ip: str = ""
) -> str:
    """
    Manage server fixed IP operations (add/remove).
    
    Functions:
    - Add fixed IP to server on specified network
    - Remove specific fixed IP from server
    - Create new port with specified or auto-assigned fixed IP
    
    Use when user requests:
    - "Add fixed IP X to server Y on network Z"
    - "Remove fixed IP X from server Y"
    - "Assign fixed IP to server on network"
    
    Args:
        instance_name: Name or ID of the server
        action: Action to perform (add, remove)
        network: Network name or ID (required for add action)
        fixed_ip: Fixed IP address (optional for add, required for remove)
        
    Returns:
        JSON string containing operation results
    """
    try:
        logger.info(f"Managing server fixed IP: {instance_name}, action: {action}")
        
        kwargs = {
            'network': network,
            'fixed_ip': fixed_ip
        }
        
        result = _set_server_fixed_ip(instance_name.strip(), action.strip(), **kwargs)
        
        # Use centralized result handling
        return handle_operation_result(
            result,
            "Server Fixed IP Management",
            {
                "Action": action,
                "Instance": instance_name,
                "Network": network or "Not specified",
                "Fixed IP": fixed_ip or "Not specified"
            }
        )
        
    except Exception as e:
        error_msg = f"Error: Failed to manage server fixed IP - {str(e)}"
        logger.error(error_msg)
        return json.dumps({
            "timestamp": datetime.now().isoformat(),
            "error": error_msg,
            "success": False
        }, indent=2)


@conditional_tool
async def set_server_security_group(
    instance_name: str,
    action: str,
    security_group: str
) -> str:
    """
    Manage server security group operations (add/remove).
    
    Functions:
    - Add security group to server
    - Remove security group from server
    - Manage server firewall rules and access control
    
    Use when user requests:
    - "Add security group X to server Y"
    - "Remove security group X from server Y"
    - "Apply security group to server"
    - "Remove firewall rules from server"
    
    Args:
        instance_name: Name or ID of the server
        action: Action to perform (add, remove)
        security_group: Security group name or ID
        
    Returns:
        JSON string containing operation results
    """
    try:
        logger.info(f"Managing server security group: {instance_name}, action: {action}")
        
        kwargs = {
            'security_group': security_group
        }
        
        result = _set_server_security_group(instance_name.strip(), action.strip(), **kwargs)
        
        # Use centralized result handling
        return handle_operation_result(
            result,
            "Server Security Group Management",
            {
                "Action": action,
                "Instance": instance_name,
                "Security Group": security_group or "Not specified"
            }
        )
        
    except Exception as e:
        error_msg = f"Error: Failed to manage server security group - {str(e)}"
        logger.error(error_msg)
        return json.dumps({
            "timestamp": datetime.now().isoformat(),
            "error": error_msg,
            "success": False
        }, indent=2)


@conditional_tool
async def set_server_migration(
    instance_name: str,
    action: str,
    host: str = "",
    migration_id: str = "",
    block_migration: str = "auto",
    admin_pass: str = "",
    on_shared_storage: bool = False
) -> str:
    """
    Manage server migration and evacuation operations.
    
    Functions:
    - Live migrate server to different host
    - Evacuate server from failed host
    - Confirm/revert migration operations
    - List server migrations
    - Show migration details
    - Abort ongoing migrations
    - Force complete migrations
    
    Use when user requests:
    - "Migrate server X to host Y"
    - "Evacuate server X"
    - "List migrations for server X"
    - "Abort migration Y for server X"
    - "Confirm migration for server X"
    
    Args:
        instance_name: Name or ID of the server
        action: Action to perform (migrate, evacuate, confirm, revert, list, show, abort, force_complete)
        host: Target host for migration/evacuation
        migration_id: Migration ID for show/abort/force_complete actions
        block_migration: Block migration mode (auto, true, false)
        admin_pass: Admin password for evacuation
        on_shared_storage: Whether using shared storage for evacuation
        
    Returns:
        JSON string containing operation results
    """
    try:
        logger.info(f"Managing server migration: {instance_name}, action: {action}")
        
        kwargs = {
            'host': host,
            'migration_id': migration_id,
            'block_migration': block_migration,
            'admin_pass': admin_pass,
            'on_shared_storage': on_shared_storage
        }
        
        result = _set_server_migration(instance_name.strip(), action.strip(), **kwargs)
        
        # Use centralized result handling
        return handle_operation_result(
            result,
            "Server Migration Management",
            {
                "Action": action,
                "Instance": instance_name,
                "Host": host or "Not specified",
                "Migration ID": migration_id or "Not specified"
            }
        )
        
    except Exception as e:
        error_msg = f"Error: Failed to manage server migration - {str(e)}"
        logger.error(error_msg)
        return json.dumps({
            "timestamp": datetime.now().isoformat(),
            "error": error_msg,
            "success": False
        }, indent=2)


@conditional_tool
async def set_server_properties(
    instance_name: str,
    action: str,
    name: str = "",
    description: str = "",
    metadata: dict = {},
    properties: list = []
) -> str:
    """
    Manage server properties and metadata (set/unset).
    
    Functions:
    - Set server name and description
    - Add/update server metadata properties
    - Remove server metadata properties
    - Manage server tags and labels
    
    Use when user requests:
    - "Set server X name to Y"
    - "Update server X description"
    - "Add metadata to server X"
    - "Remove property Y from server X"
    - "Set server property"
    
    Args:
        instance_name: Name or ID of the server
        action: Action to perform (set, unset)
        name: New server name
        description: Server description
        metadata: Dictionary of metadata properties to set
        properties: List of property names to unset
        
    Returns:
        JSON string containing operation results
    """
    try:
        logger.info(f"Managing server properties: {instance_name}, action: {action}")
        
        kwargs = {
            'name': name,
            'description': description,
            'metadata': metadata,
            'properties': properties
        }
        
        result = _set_server_properties(instance_name.strip(), action.strip(), **kwargs)
        
        # Use centralized result handling
        return handle_operation_result(
            result,
            "Server Properties Management",
            {
                "Action": action,
                "Instance": instance_name,
                "Name": name or "Not specified",
                "Description": description or "Not specified"
            }
        )
        
    except Exception as e:
        error_msg = f"Error: Failed to manage server properties - {str(e)}"
        logger.error(error_msg)
        return json.dumps({
            "timestamp": datetime.now().isoformat(),
            "error": error_msg,
            "success": False
        }, indent=2)


@conditional_tool
async def set_server_backup(
    instance_name: str,
    backup_name: str,
    backup_type: str = "daily",
    rotation: int = 1,
    metadata: dict = {}
) -> str:
    """
    Create a backup image of a server.
    
    Functions:
    - Create server backup with rotation policy
    - Set backup type (daily, weekly, etc.)
    - Add backup metadata and labels
    - Manage backup lifecycle
    
    Use when user requests:
    - "Create backup of server X"
    - "Backup server X as Y"
    - "Create daily backup of server"
    - "Backup server with rotation policy"
    
    Args:
        instance_name: Name or ID of the server
        backup_name: Name for the backup image
        backup_type: Type of backup (daily, weekly, monthly)
        rotation: Number of backups to keep
        metadata: Additional metadata for the backup
        
    Returns:
        JSON string containing backup operation results
    """
    try:
        logger.info(f"Creating server backup: {instance_name} -> {backup_name}")
        
        kwargs = {
            'backup_type': backup_type,
            'rotation': rotation,
            'metadata': metadata
        }
        
        result = _set_server_backup(instance_name.strip(), backup_name.strip(), **kwargs)
        
        # Use centralized result handling
        return handle_operation_result(
            result,
            "Server Backup Creation",
            {
                "Instance": instance_name,
                "Backup Name": backup_name,
                "Backup Type": backup_type or "Not specified",
                "Rotation": str(rotation) if rotation else "Not specified"
            }
        )
        
    except Exception as e:
        error_msg = f"Error: Failed to create server backup - {str(e)}"
        logger.error(error_msg)
        return json.dumps({
            "timestamp": datetime.now().isoformat(),
            "error": error_msg,
            "success": False
        }, indent=2)


@conditional_tool
async def set_server_dump(instance_name: str) -> str:
    """
    Create a dump file for a server (vendor-specific feature).
    
    Functions:
    - Attempt to create server memory/disk dump
    - Provide alternative backup suggestions
    - Explain dump limitations
    
    Use when user requests:
    - "Create dump of server X"
    - "Generate server dump file"
    - "Create server core dump"
    
    Args:
        instance_name: Name or ID of the server
        
    Returns:
        JSON string containing dump operation results or alternatives
    """
    try:
        logger.info(f"Attempting to create server dump: {instance_name}")
        
        result = _set_server_dump(instance_name.strip())
        
        # Use centralized result handling
        return handle_operation_result(
            result,
            "Server Dump Creation",
            {
                "Instance": instance_name
            }
        )
        
    except Exception as e:
        error_msg = f"Error: Failed to create server dump - {str(e)}"
        logger.error(error_msg)
        return json.dumps({
            "timestamp": datetime.now().isoformat(),
            "error": error_msg,
            "success": False
        }, indent=2)


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


@mcp.tool()
async def get_resource_monitoring() -> str:
    """
    Monitors real-time resource usage across the OpenStack cluster.
    
    Functions:
    - Monitor cluster-wide CPU, memory, and storage usage rates
    - Collect hypervisor statistics and resource allocation
    - Track resource utilization trends and capacity planning data
    - Provide resource usage summaries and utilization percentages
    
    Use when user requests resource monitoring, capacity planning, usage analysis, or performance monitoring.
    
    Returns:
        Resource monitoring data in JSON format with cluster summary, hypervisor details, and usage statistics.
    """
    try:
        logger.info("Monitoring OpenStack cluster resources")
        monitoring_data = _get_resource_monitoring()
        
        result = {
            "timestamp": datetime.now().isoformat(),
            "resource_monitoring": monitoring_data
        }
        
        return json.dumps(result, indent=2, ensure_ascii=False)
        
    except Exception as e:
        error_msg = f"Error: Failed to monitor OpenStack resources - {str(e)}"
        logger.error(error_msg)
        return error_msg


# =============================================================================
# Prompt Template Helper Functions
# =============================================================================

def read_prompt_template(file_path: str) -> str:
    """Read the prompt template file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        logger.warning(f"Prompt template file not found: {file_path}")
        return "# OpenStack Operations Guide\n\nPrompt template file not found."
    except Exception as e:
        logger.error(f"Error reading prompt template: {e}")
        return f"# Error\n\nFailed to read prompt template: {str(e)}"


def parse_prompt_sections(template: str) -> tuple[List[str], List[str]]:
    """Parse the prompt template into sections."""
    lines = template.split('\n')
    headings = []
    sections = []
    current_section = []
    
    for line in lines:
        if line.startswith('## '):
            if current_section:
                sections.append('\n'.join(current_section))
                current_section = []
            heading = line[3:].strip()
            headings.append(heading)
            current_section.append(line)
        else:
            current_section.append(line)
    
    if current_section:
        sections.append('\n'.join(current_section))
    
    return headings, sections


# Define the prompt template path
PROMPT_TEMPLATE_PATH = os.path.join(os.path.dirname(__file__), "prompt_template.md")


# =============================================================================
# MCP Prompts (for prompts/list exposure)
# =============================================================================

@mcp.prompt("prompt_template_full")
def prompt_template_full_prompt() -> str:
    """Return the full canonical prompt template."""
    return read_prompt_template(PROMPT_TEMPLATE_PATH)


@mcp.prompt("prompt_template_headings")
def prompt_template_headings_prompt() -> str:
    """Return compact list of section headings."""
    template = read_prompt_template(PROMPT_TEMPLATE_PATH)
    headings, _ = parse_prompt_sections(template)
    lines = ["Section Headings:"]
    for idx, title in enumerate(headings, 1):
        lines.append(f"{idx}. {title}")
    return "\n".join(lines)


@mcp.prompt("prompt_template_section")
def prompt_template_section_prompt(section: Optional[str] = None) -> str:
    """Return a specific prompt template section by number or keyword."""
    if not section:
        template = read_prompt_template(PROMPT_TEMPLATE_PATH)
        headings, _ = parse_prompt_sections(template)
        lines = ["[HELP] Missing 'section' argument."]
        lines.append("Specify a section number or keyword.")
        lines.append("Examples: 1 | overview | tool map | usage")
        lines.append("")
        lines.append("Available sections:")
        for idx, title in enumerate(headings, 1):
            lines.append(f"{idx}. {title}")
        return "\n".join(lines)

    template = read_prompt_template(PROMPT_TEMPLATE_PATH)
    headings, sections = parse_prompt_sections(template)

    # Try by number
    try:
        idx = int(section) - 1
        if 0 <= idx < len(headings):
            return sections[idx + 1]  # +1 to skip the title section
    except Exception:
        pass

    # Try by keyword
    section_lower = section.strip().lower()
    for i, heading in enumerate(headings):
        if section_lower in heading.lower():
            return sections[i + 1]  # +1 to skip the title section

    return f"Section '{section}' not found."


# =============================================================================
# Configuration Validation
# =============================================================================

def validate_config(transport_type: str, host: str, port: int) -> None:
    """Validates the configuration parameters."""
    if transport_type not in ["stdio", "streamable-http"]:
        raise ValueError(f"Invalid transport type: {transport_type}")
    
    if transport_type == "streamable-http":
        if not host:
            raise ValueError("Host is required for streamable-http transport")
        if not (1 <= port <= 65535):
            raise ValueError(f"Port must be between 1-65535, got: {port}")
    
    logger.info(f"Configuration validated for {transport_type} transport")


# =============================================================================
# Main Function
# =============================================================================

def main(argv: Optional[List[str]] = None) -> None:
    """Main entry point for the MCP server."""
    global mcp
    
    parser = argparse.ArgumentParser(
        prog="mcp-openstack-ops", 
        description="MCP OpenStack Operations Server",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        "--log-level",
        dest="log_level",
        help="Logging level override (DEBUG, INFO, WARNING, ERROR, CRITICAL). Overrides MCP_LOG_LEVEL env if provided.",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
    )
    parser.add_argument(
        "--type",
        dest="transport_type",
        help="Transport type (stdio or streamable-http). Default: stdio",
        choices=["stdio", "streamable-http"],
    )
    parser.add_argument(
        "--host",
        dest="host",
        help="Host address for streamable-http transport. Default: 127.0.0.1",
    )
    parser.add_argument(
        "--port",
        dest="port",
        type=int,
        help="Port number for streamable-http transport. Default: 8080",
    )
    parser.add_argument(
        "--auth-enable",
        dest="auth_enable",
        action="store_true",
        help="Enable Bearer token authentication for streamable-http mode. Default: False",
    )
    parser.add_argument(
        "--secret-key",
        dest="secret_key",
        help="Secret key for Bearer token authentication. Required when auth is enabled.",
    )
    
    # Allow future extension without breaking unknown args usage
    args = parser.parse_args(argv)

    # Determine log level: CLI arg > environment variable > default
    log_level = args.log_level or os.getenv("MCP_LOG_LEVEL", "INFO")
    
    # Set logging level
    logging.getLogger().setLevel(log_level)
    logger.setLevel(log_level)
    logging.getLogger("aiohttp.client").setLevel("WARNING")  # reduce noise at DEBUG
    
    if args.log_level:
        logger.info("Log level set via CLI to %s", args.log_level)
    elif os.getenv("MCP_LOG_LEVEL"):
        logger.info("Log level set via environment variable to %s", log_level)
    else:
        logger.info("Using default log level: %s", log_level)

    # Priority: command line args > environment variables > defaults
    # Transport type determination
    transport_type = args.transport_type or os.getenv("FASTMCP_TYPE", "stdio")
    
    # Host determination
    host = args.host or os.getenv("FASTMCP_HOST", "127.0.0.1")
    
    # Port determination (simplified)
    port = args.port or int(os.getenv("FASTMCP_PORT", 8080))
    
    # Authentication setting determination
    auth_enable = args.auth_enable or os.getenv("REMOTE_AUTH_ENABLE", "false").lower() in ("true", "1", "yes", "on")
    secret_key = args.secret_key or os.getenv("REMOTE_SECRET_KEY", "")
    
    # Validation for streamable-http mode with authentication
    if transport_type == "streamable-http":
        if auth_enable:
            if not secret_key:
                logger.error("ERROR: Authentication is enabled but no secret key provided.")
                logger.error("Please set REMOTE_SECRET_KEY environment variable or use --secret-key argument.")
                return
            logger.info("Authentication enabled for streamable-http transport")
        else:
            logger.warning("WARNING: streamable-http mode without authentication enabled!")
            logger.warning("This server will accept requests without Bearer token verification.")
            logger.warning("Set REMOTE_AUTH_ENABLE=true and REMOTE_SECRET_KEY to enable authentication.")

    # Note: MCP instance with authentication is already initialized at module level
    # based on environment variables. CLI arguments will override if different.
    if auth_enable != _auth_enable or secret_key != _secret_key:
        logger.warning("CLI authentication settings differ from environment variables.")
        logger.warning("Environment settings take precedence during module initialization.")

    # Execution based on transport mode
    if transport_type == "streamable-http":
        logger.info(f"Starting streamable-http server on {host}:{port}")
        mcp.run(transport="streamable-http", host=host, port=port)
    else:
        logger.info("Starting stdio transport for local usage")
        mcp.run(transport='stdio')

if __name__ == "__main__":
    """Entrypoint for MCP server.

    Supports optional CLI arguments while remaining backward-compatible 
    with stdio launcher expectations.
    """
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Server shutdown requested by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Failed to start server: {e}")
        sys.exit(1)


# =============================================================================
# Additional MCP Tools - Enhanced Functionality
# =============================================================================

# Identity (Keystone) Tools
@mcp.tool()
async def get_user_list() -> str:
    """
    Get list of OpenStack users in the current domain.
    
    Functions:
    - Query user accounts and their basic information
    - Display user status (enabled/disabled)
    - Show user email and domain information
    - Provide user creation and modification timestamps
    
    Use when user requests user management information, identity queries, or user administration tasks.
    
    Returns:
        List of users with detailed information in JSON format.
    """
    try:
        logger.info("Fetching user list")
        users = _get_user_list()
        
        result = {
            "timestamp": datetime.now().isoformat(),
            "total_users": len(users),
            "users": users
        }
        
        return json.dumps(result, indent=2, ensure_ascii=False)
        
    except Exception as e:
        error_msg = f"Error: Failed to fetch user list - {str(e)}"
        logger.error(error_msg)
        return error_msg


@mcp.tool()
async def get_role_assignments() -> str:
    """
    Get role assignments for the current project.
    
    Functions:
    - Query role assignments for users and groups
    - Display project-level and domain-level permissions
    - Show scope of role assignments
    - Provide comprehensive access control information
    
    Use when user requests permission information, access control queries, or security auditing.
    
    Returns:
        List of role assignments with detailed scope information in JSON format.
    """
    try:
        logger.info("Fetching role assignments")
        assignments = _get_role_assignments()
        
        result = {
            "timestamp": datetime.now().isoformat(),
            "total_assignments": len(assignments),
            "role_assignments": assignments
        }
        
        return json.dumps(result, indent=2, ensure_ascii=False)
        
    except Exception as e:
        error_msg = f"Error: Failed to fetch role assignments - {str(e)}"
        logger.error(error_msg)
        return error_msg


# Compute (Nova) Enhanced Tools
@mcp.tool()
async def get_keypair_list() -> str:
    """
    Get list of SSH keypairs for the current user.
    
    Functions:
    - Query SSH keypairs and their fingerprints
    - Display keypair types and creation dates
    - Show public key information (truncated for security)
    - Provide keypair management information
    
    Use when user requests SSH key management, keypair information, or security key queries.
    
    Returns:
        List of SSH keypairs with detailed information in JSON format.
    """
    try:
        logger.info("Fetching keypair list")
        keypairs = _get_keypair_list()
        
        result = {
            "timestamp": datetime.now().isoformat(),
            "total_keypairs": len(keypairs),
            "keypairs": keypairs
        }
        
        return json.dumps(result, indent=2, ensure_ascii=False)
        
    except Exception as e:
        error_msg = f"Error: Failed to fetch keypair list - {str(e)}"
        logger.error(error_msg)
        return error_msg


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


@mcp.tool()
async def get_security_groups() -> str:
    """
    Get list of security groups with their rules.
    
    Functions:
    - Query security groups and their rule configurations
    - Display ingress and egress rules with protocols and ports
    - Show remote IP prefixes and security group references
    - Provide comprehensive network security information
    
    Use when user requests security group information, firewall rules, or network security queries.
    
    Returns:
        List of security groups with detailed rules in JSON format.
    """
    try:
        logger.info("Fetching security groups")
        security_groups = _get_security_groups()
        
        result = {
            "timestamp": datetime.now().isoformat(),
            "total_security_groups": len(security_groups),
            "security_groups": security_groups
        }
        
        return json.dumps(result, indent=2, ensure_ascii=False)
        
    except Exception as e:
        error_msg = f"Error: Failed to fetch security groups - {str(e)}"
        logger.error(error_msg)
        return error_msg


# Network (Neutron) Enhanced Tools
@mcp.tool()
async def get_floating_ips() -> str:
    """
    Get list of floating IPs with their associations.
    
    Functions:
    - Query floating IPs and their current status
    - Display associated fixed IPs and ports
    - Show floating IP pool and router associations
    - Provide floating IP allocation and usage information
    
    Use when user requests floating IP information, external connectivity queries, or IP management tasks.
    
    Returns:
        List of floating IPs with detailed association information in JSON format.
    """
    try:
        logger.info("Fetching floating IPs")
        floating_ips = _get_floating_ips()
        
        result = {
            "timestamp": datetime.now().isoformat(),
            "total_floating_ips": len(floating_ips),
            "floating_ips": floating_ips
        }
        
        return json.dumps(result, indent=2, ensure_ascii=False)
        
    except Exception as e:
        error_msg = f"Error: Failed to fetch floating IPs - {str(e)}"
        logger.error(error_msg)
        return error_msg


@conditional_tool
async def set_floating_ip(action: str, floating_network_id: str = "", port_id: str = "", floating_ip_id: str = "", 
                         floating_ip_address: str = "", description: str = "") -> str:
    """
    Manage floating IPs (create, delete, associate, disassociate, set, show, unset, list).
    
    Functions:
    - Create new floating IPs from external networks (allocate)
    - Delete existing floating IPs (release)
    - Associate floating IPs with instance ports
    - Disassociate floating IPs from instances
    - Set floating IP properties (description, fixed IP)
    - Show detailed floating IP information
    - Unset floating IP properties (clear description)
    - List all floating IPs
    
    Use when user requests floating IP management, external connectivity setup, or IP allocation tasks.
    
    Args:
        action: Action to perform (create/allocate, delete/release, associate, disassociate, set, show, unset, list)
        floating_network_id: ID of external network for create action
        port_id: Port ID for association operations
        floating_ip_id: Floating IP ID for operations
        floating_ip_address: Floating IP address (alternative to floating_ip_id)
        description: Description for the floating IP (for set action)
        
    Returns:
        Result of floating IP management operation in JSON format.
    """
    try:
        logger.info(f"Managing floating IP with action '{action}'")
        
        # Map CLI-style actions to internal actions
        action_map = {
            'create': 'allocate',
            'delete': 'release',
            'allocate': 'allocate',
            'release': 'release'
        }
        internal_action = action_map.get(action.lower(), action.lower())
        
        kwargs = {}
        if floating_network_id.strip():
            kwargs['floating_network_id'] = floating_network_id.strip()
        if port_id.strip():
            kwargs['port_id'] = port_id.strip()
        if floating_ip_id.strip():
            kwargs['floating_ip_id'] = floating_ip_id.strip()
        if floating_ip_address.strip():
            kwargs['floating_ip_address'] = floating_ip_address.strip()
        if description.strip():
            kwargs['description'] = description.strip()
            
        result_data = _set_floating_ip(internal_action, **kwargs)
        
        # Use centralized result handling
        return handle_operation_result(
            result_data,
            "Floating IP Management",
            {
                "Action": action,
                "Network ID": floating_network_id or "Not specified",
                "Port ID": port_id or "Not specified",
                "IP Address": floating_ip_address or "Not specified"
            }
        )
        
    except Exception as e:
        error_msg = f"Error: Failed to manage floating IP - {str(e)}"
        logger.error(error_msg)
        return error_msg


@mcp.tool()
async def get_floating_ip_pools() -> str:
    """
    Get list of floating IP pools (external networks).
    
    Functions:
    - List all external networks that can provide floating IPs
    - Show available and used IP counts for each pool
    - Display network configuration for floating IP allocation
    - Provide pool capacity and utilization information
    
    Use when user requests:
    - "Show floating IP pools"
    - "List available floating IP networks"
    - "Check floating IP capacity"
    - "What external networks are available?"
    
    Returns:
        List of floating IP pools with capacity information in JSON format.
    """
    try:
        result_data = _get_floating_ip_pools()
        
        result = {
            "timestamp": datetime.now().isoformat(),
            "pools": result_data,
            "total_pools": len(result_data)
        }
        
        return json.dumps(result, indent=2)
        
    except Exception as e:
        error_msg = f"Error: Failed to get floating IP pools - {str(e)}"
        logger.error(error_msg)
        return error_msg


@conditional_tool
async def set_floating_ip_port_forwarding(
    action: str,
    floating_ip_id: str = "",
    floating_ip_address: str = "",
    port_forwarding_id: str = "",
    protocol: str = "tcp",
    external_port: int = 0,
    internal_port: int = 0,
    internal_ip_address: str = "",
    internal_port_id: str = "",
    description: str = ""
) -> str:
    """
    Manage floating IP port forwarding rules for NAT translation.
    
    Functions:
    - Create port forwarding rules to redirect external traffic to internal IPs
    - Delete existing port forwarding rules
    - List all port forwarding rules for a floating IP
    - Show detailed configuration of specific port forwarding rule
    - Update port forwarding settings (description, internal target)
    
    Use when user requests:
    - "Create port forwarding rule for floating IP [ip] from port [ext] to [int:internal]"
    - "Delete port forwarding rule [id] from floating IP [ip]"
    - "List port forwarding rules for floating IP [ip]"
    - "Show port forwarding rule [id] details"
    - "Update port forwarding rule [id] description to [text]"
    
    Args:
        action: Action to perform (create, delete, list, show, set)
        floating_ip_id: Floating IP ID (alternative to floating_ip_address)
        floating_ip_address: Floating IP address (alternative to floating_ip_id)
        port_forwarding_id: Port forwarding rule ID (for delete/show/set actions)
        protocol: Protocol for port forwarding (tcp, udp, icmp) - default: tcp
        external_port: External port number (for create action)
        internal_port: Internal port number (for create action)
        internal_ip_address: Internal IP address target (for create/set actions)
        internal_port_id: Internal port ID target (optional)
        description: Description for the port forwarding rule
        
    Returns:
        Result of port forwarding management operation in JSON format.
    """
    try:
        logger.info(f"Managing floating IP port forwarding with action '{action}'")
        
        kwargs = {
            'floating_ip_id': floating_ip_id.strip() if floating_ip_id.strip() else None,
            'floating_ip_address': floating_ip_address.strip() if floating_ip_address.strip() else None,
            'port_forwarding_id': port_forwarding_id.strip() if port_forwarding_id.strip() else None,
            'protocol': protocol.lower() if protocol.strip() else 'tcp',
            'description': description.strip() if description.strip() else None
        }
        
        if external_port > 0:
            kwargs['external_port'] = external_port
        if internal_port > 0:
            kwargs['internal_port'] = internal_port
        if internal_ip_address.strip():
            kwargs['internal_ip_address'] = internal_ip_address.strip()
        if internal_port_id.strip():
            kwargs['internal_port_id'] = internal_port_id.strip()
        
        result_data = _set_floating_ip_port_forwarding(action, **kwargs)
        
        result = {
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "parameters": kwargs,
            "result": result_data
        }
        
        return json.dumps(result, indent=2)
        
    except Exception as e:
        error_msg = f"Error: Failed to manage floating IP port forwarding - {str(e)}"
        logger.error(error_msg)
        return error_msg


@mcp.tool()
async def get_routers() -> str:
    """
    Get list of routers with their configuration.
    
    Functions:
    - Query routers and their external gateway configurations
    - Display router interfaces and connected networks
    - Show routing table entries and static routes
    - Provide comprehensive network routing information
    
    Use when user requests router information, network connectivity queries, or routing configuration.
    
    Returns:
        List of routers with detailed configuration in JSON format.
    """
    try:
        logger.info("Fetching routers")
        routers = _get_routers()
        
        result = {
            "timestamp": datetime.now().isoformat(),
            "total_routers": len(routers),
            "routers": routers
        }
        
        return json.dumps(result, indent=2, ensure_ascii=False)
        
    except Exception as e:
        error_msg = f"Error: Failed to fetch routers - {str(e)}"
        logger.error(error_msg)
        return error_msg


# Block Storage (Cinder) Enhanced Tools
@mcp.tool()
async def get_volume_types() -> str:
    """
    Get list of volume types with their specifications.
    
    Functions:
    - Query volume types and their capabilities
    - Display extra specifications and backend configurations
    - Show public/private volume type settings
    - Provide storage backend information
    
    Use when user requests volume type information, storage backend queries, or volume creation planning.
    
    Returns:
        List of volume types with detailed specifications in JSON format.
    """
    try:
        logger.info("Fetching volume types")
        volume_types = _get_volume_types()
        
        result = {
            "timestamp": datetime.now().isoformat(),
            "total_volume_types": len(volume_types),
            "volume_types": volume_types
        }
        
        return json.dumps(result, indent=2, ensure_ascii=False)
        
    except Exception as e:
        error_msg = f"Error: Failed to fetch volume types - {str(e)}"
        logger.error(error_msg)
        return error_msg


@mcp.tool()
async def get_volume_snapshots() -> str:
    """
    Get list of volume snapshots.
    
    Functions:
    - Query volume snapshots and their status
    - Display source volume information
    - Show snapshot creation and modification dates
    - Provide snapshot size and usage information
    
    Use when user requests snapshot information, backup queries, or volume restoration planning.
    
    Returns:
        List of volume snapshots with detailed information in JSON format.
    """
    try:
        logger.info("Fetching volume snapshots")
        snapshots = _get_volume_snapshots()
        
        result = {
            "timestamp": datetime.now().isoformat(),
            "total_snapshots": len(snapshots),
            "snapshots": snapshots
        }
        
        return json.dumps(result, indent=2, ensure_ascii=False)
        
    except Exception as e:
        error_msg = f"Error: Failed to fetch volume snapshots - {str(e)}"
        logger.error(error_msg)
        return error_msg


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


# Image Service (Glance) Enhanced Tools
@conditional_tool
async def set_image(image_names: str, action: str, container_format: str = "bare", disk_format: str = "qcow2", 
                   visibility: str = "private", min_disk: int = 0, min_ram: int = 0, properties: str = "{}") -> str:
    """
    Manage images (create, delete, update, list).
    Supports both single image and bulk operations.
    
    Functions:
    - Create new images with specified formats and properties
    - Delete existing images
    - Update image metadata and visibility settings
    - List all available images in the project
    - Handle image lifecycle management
    - Bulk operations: Apply action to multiple images at once
    
    Use when user requests image management, custom image creation, image listing, or image metadata updates.
    
    Args:
        image_names: Name(s) of images to manage. Support formats:
                    - Single: "image1" 
                    - Multiple: "image1,image2,image3" or "image1, image2, image3"
                    - List format: '["image1", "image2", "image3"]'
        action: Action to perform (create, delete, update, list)
        container_format: Container format (bare, ovf, etc.)
        disk_format: Disk format (qcow2, raw, vmdk, etc.)
        visibility: Image visibility (private, public, shared, community)
        min_disk: Minimum disk space required in GB (for create action)
        min_ram: Minimum RAM required in MB (for create action)
        properties: Additional image properties as JSON string (for create action)
        
    Returns:
        Result of image management operation in JSON format.
        For bulk operations, returns summary of successes and failures.
    """
    
    try:
        # For list action, allow empty image_names
        if action.lower() == 'list':
            logger.info(f"Managing image with action '{action}'")
            
            kwargs = {
                'container_format': container_format,
                'disk_format': disk_format,
                'visibility': visibility,
                'min_disk': min_disk,
                'min_ram': min_ram
            }
            
            # Parse properties JSON if provided
            if properties.strip():
                try:
                    kwargs['properties'] = json.loads(properties)
                except json.JSONDecodeError:
                    return json.dumps({
                        "timestamp": datetime.now().isoformat(),
                        "error": "Invalid JSON format for properties",
                        "message": "Properties must be valid JSON format"
                    })
            
            result_data = _set_image("", action, **kwargs)
            return handle_operation_result(
                result_data,
                "Image Management",
                {
                    "Action": action,
                    "Image Name": "all",
                    "Container Format": container_format,
                    "Disk Format": disk_format,
                    "Visibility": visibility
                }
            )
        
        # Parse image names for non-list actions
        if not image_names or not image_names.strip():
            return "Error: Image name(s) are required for this action"
            
        names_str = image_names.strip()
        
        # Handle JSON list format: ["name1", "name2"]
        if names_str.startswith('[') and names_str.endswith(']'):
            try:
                import json
                name_list = json.loads(names_str)
                if not isinstance(name_list, list):
                    return "Error: Invalid JSON list format for image names"
            except json.JSONDecodeError:
                return "Error: Invalid JSON format for image names"
        else:
            # Handle comma-separated format: "name1,name2" or "name1, name2"
            name_list = [name.strip() for name in names_str.split(',')]
        
        # Remove empty strings
        name_list = [name for name in name_list if name]
        
        if not name_list:
            return "Error: No valid image names provided"
        
        kwargs = {
            'container_format': container_format,
            'disk_format': disk_format,
            'visibility': visibility,
            'min_disk': min_disk,
            'min_ram': min_ram
        }
        
        # Parse properties JSON if provided
        if properties.strip():
            try:
                kwargs['properties'] = json.loads(properties)
            except json.JSONDecodeError:
                return json.dumps({
                    "timestamp": datetime.now().isoformat(),
                    "error": "Invalid JSON format for properties",
                    "message": "Properties must be valid JSON format"
                })
        
        # Handle single image (backward compatibility)
        if len(name_list) == 1:
            logger.info(f"Managing image '{name_list[0]}' with action '{action}'")
            result_data = _set_image(name_list[0].strip(), action, **kwargs)
            
            return handle_operation_result(
                result_data,
                "Image Management",
                {
                    "Action": action,
                    "Image Name": name_list[0],
                    "Container Format": container_format,
                    "Disk Format": disk_format,
                    "Visibility": visibility
                }
            )
        
        # Handle bulk operations (multiple images)
        else:
            logger.info(f"Managing {len(name_list)} images with action '{action}': {name_list}")
            results = []
            successes = []
            failures = []
            
            for image_name in name_list:
                try:
                    result = _set_image(image_name.strip(), action, **kwargs)
                    
                    # Check if result indicates success or failure
                    if isinstance(result, dict):
                        if result.get('success', False):
                            successes.append(image_name)
                            results.append(f"✓ {image_name}: {result.get('message', 'Success')}")
                        else:
                            failures.append(image_name)
                            results.append(f"✗ {image_name}: {result.get('error', 'Unknown error')}")
                    elif isinstance(result, str):
                        # For string results, check if it contains error indicators
                        if 'error' in result.lower() or 'failed' in result.lower():
                            failures.append(image_name)
                            results.append(f"✗ {image_name}: {result}")
                        else:
                            successes.append(image_name)
                            results.append(f"✓ {image_name}: {result}")
                    else:
                        successes.append(image_name)
                        results.append(f"✓ {image_name}: Operation completed")
                        
                except Exception as e:
                    failures.append(image_name)
                    results.append(f"✗ {image_name}: {str(e)}")
            
            # Post-action status verification for all processed images
            logger.info("Verifying post-action status for images")
            post_action_status = {}
            
            # Allow some time for OpenStack operations to complete
            import time
            time.sleep(2)
            
            for image_name in name_list:
                post_action_status[image_name] = _get_resource_status_by_name("image", image_name.strip())
            
            # Prepare summary with post-action status
            summary_parts = [
                f"Bulk Image Management - Action: {action}",
                f"Total images: {len(name_list)}",
                f"Successes: {len(successes)}",
                f"Failures: {len(failures)}"
            ]
            
            if successes:
                summary_parts.append(f"Successful images: {', '.join(successes)}")
            if failures:
                summary_parts.append(f"Failed images: {', '.join(failures)}")
                
            summary_parts.append("\nDetailed Results:")
            summary_parts.extend(results)
            
            # Add post-action status information
            summary_parts.append("\nPost-Action Status:")
            for image_name in name_list:
                current_status = post_action_status.get(image_name, 'Unknown')
                status_indicator = "🟢" if current_status.lower() in ["active", "available"] else "🔴" if current_status.lower() in ["deleted", "error", "killed"] else "🟡"
                summary_parts.append(f"{status_indicator} {image_name}: {current_status}")
            
            return "\n".join(summary_parts)
        
    except Exception as e:
        error_msg = f"Error: Failed to manage image(s) '{image_names}' - {str(e)}"
        logger.error(error_msg)
        return error_msg


# Heat Stack Tools
@mcp.tool()
async def get_heat_stacks() -> str:
    """
    Get list of Heat orchestration stacks.
    
    Functions:
    - Query Heat stacks and their current status
    - Display stack creation and update timestamps
    - Show stack templates and resource information
    - Provide orchestration deployment information
    
    Use when user requests stack information, orchestration queries, or infrastructure-as-code status.
    
    Returns:
        List of Heat stacks with detailed information in JSON format.
    """
    try:
        logger.info("Fetching Heat stacks")
        stacks = _get_heat_stacks()
        
        result = {
            "timestamp": datetime.now().isoformat(),
            "total_stacks": len(stacks),
            "stacks": stacks
        }
        
        return json.dumps(result, indent=2, ensure_ascii=False)
        
    except Exception as e:
        error_msg = f"Error: Failed to fetch Heat stacks - {str(e)}"
        logger.error(error_msg)
        return error_msg


@conditional_tool
async def set_heat_stack(stack_names: str, action: str, template: str = "", parameters: str = "") -> str:
    """
    Manage Heat orchestration stacks (create, delete, update).
    Supports both single stack and bulk operations.
    
    Functions:
    - Create new stacks from Heat templates
    - Delete existing stacks
    - Update stack configurations and parameters
    - Handle complex infrastructure deployments
    - Bulk operations: Apply action to multiple stacks at once
    
    Use when user requests Heat stack management, infrastructure orchestration, or template deployment tasks.
    
    Args:
        stack_names: Name(s) of stacks to manage. Support formats:
                    - Single: "stack1" 
                    - Multiple: "stack1,stack2,stack3" or "stack1, stack2, stack3"
                    - List format: '["stack1", "stack2", "stack3"]'
        action: Action to perform (create, delete, update)
        template: Heat template content for create/update actions (optional)
        parameters: Stack parameters in JSON format (optional)
        
    Returns:
        Result of stack management operation in JSON format.
        For bulk operations, returns summary of successes and failures.
    """
    
    try:
        if not stack_names or not stack_names.strip():
            return "Error: Stack name(s) are required"
            
        names_str = stack_names.strip()
        
        # Handle JSON list format: ["name1", "name2"]
        if names_str.startswith('[') and names_str.endswith(']'):
            try:
                import json
                name_list = json.loads(names_str)
                if not isinstance(name_list, list):
                    return "Error: Invalid JSON list format for stack names"
            except json.JSONDecodeError:
                return "Error: Invalid JSON format for stack names"
        else:
            # Handle comma-separated format: "name1,name2" or "name1, name2"
            name_list = [name.strip() for name in names_str.split(',')]
        
        # Remove empty strings
        name_list = [name for name in name_list if name]
        
        if not name_list:
            return "Error: No valid stack names provided"
        
        kwargs = {}
        if template.strip():
            try:
                kwargs['template'] = json.loads(template.strip())
            except json.JSONDecodeError:
                # If not JSON, treat as YAML or plain text template
                kwargs['template'] = template.strip()
        
        if parameters.strip():
            try:
                kwargs['parameters'] = json.loads(parameters.strip())
            except json.JSONDecodeError:
                return json.dumps({
                    "timestamp": datetime.now().isoformat(),
                    "error": "Invalid JSON format for parameters",
                    "message": "Parameters must be valid JSON format"
                }, indent=2, ensure_ascii=False)
        
        # Handle single stack (backward compatibility)
        if len(name_list) == 1:
            logger.info(f"Managing stack '{name_list[0]}' with action '{action}'")
            result_data = _set_heat_stack(name_list[0], action, **kwargs)
            
            return handle_operation_result(
                result_data,
                "Heat Stack Management",
                {
                    "Action": action,
                    "Stack Name": name_list[0],
                    "Template": "Provided" if template.strip() else "Not provided",
                    "Parameters": "Provided" if parameters.strip() else "Not provided"
                }
            )
        
        # Handle bulk operations (multiple stacks)
        else:
            logger.info(f"Managing {len(name_list)} stacks with action '{action}': {name_list}")
            results = []
            successes = []
            failures = []
            
            for stack_name in name_list:
                try:
                    result = _set_heat_stack(stack_name.strip(), action, **kwargs)
                    
                    # Check if result indicates success or failure
                    if isinstance(result, dict):
                        if result.get('success', False):
                            successes.append(stack_name)
                            results.append(f"✓ {stack_name}: {result.get('message', 'Success')}")
                        else:
                            failures.append(stack_name)
                            results.append(f"✗ {stack_name}: {result.get('error', 'Unknown error')}")
                    elif isinstance(result, str):
                        # For string results, check if it contains error indicators
                        if 'error' in result.lower() or 'failed' in result.lower():
                            failures.append(stack_name)
                            results.append(f"✗ {stack_name}: {result}")
                        else:
                            successes.append(stack_name)
                            results.append(f"✓ {stack_name}: {result}")
                    else:
                        successes.append(stack_name)
                        results.append(f"✓ {stack_name}: Operation completed")
                        
                except Exception as e:
                    failures.append(stack_name)
                    results.append(f"✗ {stack_name}: {str(e)}")
            
            # Prepare summary
            summary_parts = [
                f"Bulk Heat Stack Management - Action: {action}",
                f"Total stacks: {len(name_list)}",
                f"Successes: {len(successes)}",
                f"Failures: {len(failures)}"
            ]
            
            if successes:
                summary_parts.append(f"Successful stacks: {', '.join(successes)}")
            if failures:
                summary_parts.append(f"Failed stacks: {', '.join(failures)}")
                
            summary_parts.append("\nDetailed Results:")
            summary_parts.extend(results)
            
            return "\n".join(summary_parts)
        
    except Exception as e:
        error_msg = f"Error: Failed to manage stack(s) '{stack_names}' - {str(e)}"
        logger.error(error_msg)
        return error_msg


# =============================================================================
# Read-only Tools (Always Available - Extracted from set_* functions)
# =============================================================================

@mcp.tool()
async def get_volume_list() -> str:
    """
    Get list of all volumes with detailed information.
    
    Functions:
    - List all volumes in the project
    - Show volume status, size, and type information
    - Display attachment information for volumes
    - Provide detailed metadata for each volume
    
    Use when user requests volume listing, volume information, or storage overview.
    
    Returns:
        Detailed volume list in JSON format with volume information, attachments, and metadata.
    """
    try:
        logger.info("Fetching volume list")
        volumes = _get_volume_list()
        
        response = {
            "timestamp": datetime.now().isoformat(),
            "volumes": volumes,
            "count": len(volumes),
            "operation": "list_volumes"
        }
        
        return json.dumps(response, indent=2, ensure_ascii=False)
        
    except Exception as e:
        error_msg = f"Error: Failed to fetch volume list - {str(e)}"
        logger.error(error_msg)
        return error_msg


@mcp.tool()
async def get_image_detail_list() -> str:
    """
    Get detailed list of all images with comprehensive metadata.
    
    Functions:
    - List all images available in the project
    - Show image status, size, and format information
    - Display image properties and metadata
    - Provide ownership and visibility details
    
    Use when user requests image listing, image information, or image metadata details.
    
    Returns:
        Comprehensive image list in JSON format with detailed metadata, properties, and status information.
    """
    try:
        logger.info("Fetching detailed image list")
        images = _get_image_detail_list()
        
        response = {
            "timestamp": datetime.now().isoformat(),
            "images": images,
            "count": len(images),
            "operation": "list_images_detailed"
        }
        
        return json.dumps(response, indent=2, ensure_ascii=False)
        
    except Exception as e:
        error_msg = f"Error: Failed to fetch detailed image list - {str(e)}"
        logger.error(error_msg)
        return error_msg


@mcp.tool()
async def get_usage_statistics(start_date: str = "", end_date: str = "") -> str:
    """
    Get usage statistics for projects (similar to 'openstack usage list' command).
    
    Functions:
    - Show project usage statistics over a specified time period
    - Display servers, RAM MB-Hours, CPU Hours, and Disk GB-Hours
    - Provide detailed server usage breakdown when available
    - Calculate usage summary across all projects
    
    Use when user requests usage statistics, billing information, resource consumption analysis, or project usage reports.
    
    Args:
        start_date: Start date in YYYY-MM-DD format (optional, defaults to 30 days ago)
        end_date: End date in YYYY-MM-DD format (optional, defaults to today)
        
    Returns:
        Usage statistics in JSON format with project usage data, server details, and summary information.
    """
    try:
        logger.info(f"Fetching usage statistics from {start_date or 'default'} to {end_date or 'default'}")
        usage_stats = _get_usage_statistics(start_date=start_date, end_date=end_date)
        
        response = {
            "timestamp": datetime.now().isoformat(),
            "operation": "get_usage_statistics",
            "parameters": {
                "start_date": start_date or "auto (30 days ago)",
                "end_date": end_date or "auto (today)"
            },
            "usage_data": usage_stats
        }
        
        return json.dumps(response, indent=2, ensure_ascii=False)
        
    except Exception as e:
        error_msg = f"Error: Failed to fetch usage statistics - {str(e)}"
        logger.error(error_msg)
        return error_msg


@mcp.tool()
async def get_quota(project_name: str = "") -> str:
    """
    Get quota information for projects (similar to 'openstack quota show').
    
    Args:
        project_name: Name of the project (optional, defaults to current project if empty)
    
    Returns:
        JSON string containing quota information for the specified project or current project
    """
    try:
        if not project_name.strip():
            logger.info("Getting quota for current project (no project name specified)")
        else:
            logger.info(f"Getting quota for project: {project_name}")
            
        quota_info = _get_quota(project_name=project_name)
        
        response = {
            "timestamp": datetime.now().isoformat(),
            "operation": "get_quota",
            "parameters": {
                "project_name": project_name or "current project"
            },
            "quota_data": quota_info
        }
        
        return json.dumps(response, indent=2, ensure_ascii=False)
        
    except Exception as e:
        error_msg = f"Error: Failed to get quota information - {str(e)}"
        logger.error(error_msg)
        return error_msg


@conditional_tool
async def set_quota(
    project_name: str, 
    action: str, 
    cores: int = None,
    instances: int = None,
    ram: int = None,
    volumes: int = None,
    snapshots: int = None,
    gigabytes: int = None,
    networks: int = None,
    ports: int = None,
    routers: int = None,
    floating_ips: int = None,
    security_groups: int = None,
    security_group_rules: int = None
) -> str:
    """
    Manage project quotas (set, delete, list).
    
    Args:
        project_name: Name of the project (required for set/delete, optional for list)
        action: Action to perform (set, delete, list)
        cores: Compute cores quota (optional, for set action)
        instances: Instance count quota (optional, for set action)
        ram: RAM in MB quota (optional, for set action)
        volumes: Volume count quota (optional, for set action)
        snapshots: Snapshot count quota (optional, for set action)
        gigabytes: Storage in GB quota (optional, for set action)
        networks: Network count quota (optional, for set action)
        ports: Port count quota (optional, for set action)
        routers: Router count quota (optional, for set action)
        floating_ips: Floating IP count quota (optional, for set action)
        security_groups: Security group count quota (optional, for set action)
        security_group_rules: Security group rules count quota (optional, for set action)
    
    Returns:
        JSON string containing the result of the quota management operation
    """
    try:
        logger.info(f"Managing quota - Action: {action}, Project: {project_name}")
        
        # Build quota parameters for set action
        quota_params = {}
        if cores is not None:
            quota_params['cores'] = cores
        if instances is not None:
            quota_params['instances'] = instances
        if ram is not None:
            quota_params['ram'] = ram
        if volumes is not None:
            quota_params['volumes'] = volumes
        if snapshots is not None:
            quota_params['snapshots'] = snapshots
        if gigabytes is not None:
            quota_params['gigabytes'] = gigabytes
        if networks is not None:
            quota_params['networks'] = networks
        if ports is not None:
            quota_params['ports'] = ports
        if routers is not None:
            quota_params['routers'] = routers
        if floating_ips is not None:
            quota_params['floating_ips'] = floating_ips
        if security_groups is not None:
            quota_params['security_groups'] = security_groups
        if security_group_rules is not None:
            quota_params['security_group_rules'] = security_group_rules
        
        quota_result = _set_quota(project_name=project_name, action=action, **quota_params)
        
        # Use centralized result handling
        return handle_operation_result(
            quota_result,
            "Quota Management",
            {
                "Action": action,
                "Project": project_name or "Current project",
                "Parameters": f"{len(quota_params)} quota limits" if quota_params else "No limits specified"
            }
        )
        
    except Exception as e:
        error_msg = f"Error: Failed to manage quota - {str(e)}"
        logger.error(error_msg)
        return error_msg


@mcp.tool()
async def get_project_details(project_name: str = "") -> str:
    """
    Get OpenStack project details (similar to 'openstack project list/show').
    
    Args:
        project_name: Name of specific project to show details for (optional, lists all if empty)
    
    Returns:
        JSON string containing project information including details, roles, and quotas
    """
    try:
        if not project_name.strip():
            logger.info("Getting list of all projects")
        else:
            logger.info(f"Getting project details for: {project_name}")
            
        project_info = _get_project_details(project_name=project_name)
        
        response = {
            "timestamp": datetime.now().isoformat(),
            "operation": "get_project_details",
            "parameters": {
                "project_name": project_name or "all projects"
            },
            "project_data": project_info
        }
        
        return json.dumps(response, indent=2, ensure_ascii=False)
        
    except Exception as e:
        error_msg = f"Error: Failed to get project details - {str(e)}"
        logger.error(error_msg)
        return error_msg


@conditional_tool
async def set_project(
    project_name: str, 
    action: str, 
    description: str = "",
    enable: bool = None,
    disable: bool = None,
    domain: str = "",
    parent: str = "",
    tags: str = ""
) -> str:
    """
    Manage OpenStack projects (create, delete, set, cleanup).
    
    Args:
        project_name: Name of the project (required)
        action: Action to perform (create, delete, set, cleanup)
        description: Project description (optional, for create/set)
        enable: Enable project (optional, for set action)
        disable: Disable project (optional, for set action)
        domain: Domain name or ID (optional, for create)
        parent: Parent project name or ID (optional, for create)
        tags: Comma-separated list of tags (optional, for create/set)
    
    Returns:
        JSON string containing the result of the project management operation
    """
    try:
        logger.info(f"Managing project - Action: {action}, Project: {project_name}")
        
        # Build project parameters
        project_params = {}
        if description:
            project_params['description'] = description
        if enable is not None:
            project_params['enable'] = enable
        if disable is not None:
            project_params['disable'] = disable
        if domain:
            project_params['domain'] = domain
        if parent:
            project_params['parent'] = parent
        if tags:
            project_params['tags'] = [tag.strip() for tag in tags.split(',')]
        
        project_result = _set_project(project_name=project_name, action=action, **project_params)
        
        # Use centralized result handling
        return handle_operation_result(
            project_result,
            "Project Management",
            {
                "Action": action,
                "Project Name": project_name,
                "Description": description or "Not specified",
                "Domain": domain or "Default"
            }
        )
        
    except Exception as e:
        error_msg = f"Error: Failed to manage project - {str(e)}"
        logger.error(error_msg)
        return error_msg


@mcp.tool()
async def get_server_events(
    instance_name: str,
    limit: int = 50
) -> str:
    """
    Get recent events for a specific server
    
    Args:
        instance_name: Name or ID of the server instance
        limit: Maximum number of events to return (default: 50)
    
    Returns:
        JSON string with server events information
    """
    try:
        logger.info(f"Getting events for server: {instance_name}")
        
        events_result = _get_server_events(instance_name=instance_name, limit=limit)
        
        response = {
            "timestamp": datetime.now().isoformat(),
            "operation": "get_server_events",
            "parameters": {
                "instance_name": instance_name,
                "limit": limit
            },
            "result": events_result
        }
        
        return json.dumps(response, indent=2, ensure_ascii=False)
        
    except Exception as e:
        error_msg = f"Error: Failed to get server events - {str(e)}"
        logger.error(error_msg)
        return error_msg


@mcp.tool()
async def get_server_groups() -> str:
    """
    List all server groups with their details
    
    Returns:
        JSON string with server groups information
    """
    try:
        logger.info("Getting server groups list")
        
        groups_result = _get_server_groups()
        
        response = {
            "timestamp": datetime.now().isoformat(),
            "operation": "get_server_groups",
            "result": {
                "server_groups_count": len(groups_result),
                "server_groups": groups_result
            }
        }
        
        return json.dumps(response, indent=2, ensure_ascii=False)
        
    except Exception as e:
        error_msg = f"Error: Failed to get server groups - {str(e)}"
        logger.error(error_msg)
        return error_msg


@conditional_tool
async def set_server_group(
    group_name: str,
    action: str,
    policies: Optional[str] = None,
    metadata: Optional[str] = None
) -> str:
    """
    Manage server groups (create, delete, show)
    
    Args:
        group_name: Name of the server group
        action: Action to perform (create, delete, show)
        policies: Comma-separated list of policies for create (e.g., "affinity" or "anti-affinity")
        metadata: JSON string of metadata for create
    
    Returns:
        JSON string with server group operation result
    """
    try:
        logger.info(f"Managing server group: {group_name}, action: {action}")
        
        group_params = {}
        
        if policies:
            group_params['policies'] = [p.strip() for p in policies.split(',')]
            
        if metadata:
            import json as json_module
            group_params['metadata'] = json_module.loads(metadata)
        
        group_result = _set_server_group(group_name=group_name, action=action, **group_params)
        
        # Use centralized result handling
        return handle_operation_result(
            group_result,
            "Server Group Management",
            {
                "Action": action,
                "Group Name": group_name,
                "Policies": policies or "Not specified"
            }
        )
        
    except Exception as e:
        error_msg = f"Error: Failed to manage server group - {str(e)}"
        logger.error(error_msg)
        return error_msg


@mcp.tool()
async def get_hypervisor_details(
    hypervisor_name: str = "all"
) -> str:
    """
    Get detailed information about hypervisors
    
    Args:
        hypervisor_name: Name/ID of specific hypervisor or "all" for all hypervisors
    
    Returns:
        JSON string with hypervisor details and statistics
    """
    try:
        logger.info(f"Getting hypervisor details for: {hypervisor_name}")
        
        hypervisor_result = _get_hypervisor_details(hypervisor_name=hypervisor_name)
        
        response = {
            "timestamp": datetime.now().isoformat(),
            "operation": "get_hypervisor_details",
            "parameters": {
                "hypervisor_name": hypervisor_name
            },
            "result": hypervisor_result
        }
        
        return json.dumps(response, indent=2, ensure_ascii=False)
        
    except Exception as e:
        error_msg = f"Error: Failed to get hypervisor details - {str(e)}"
        logger.error(error_msg)
        return error_msg


@mcp.tool()
async def get_availability_zones() -> str:
    """
    List availability zones and their status
    
    Returns:
        JSON string with availability zones information
    """
    try:
        logger.info("Getting availability zones")
        
        zones_result = _get_availability_zones()
        
        response = {
            "timestamp": datetime.now().isoformat(),
            "operation": "get_availability_zones",
            "result": zones_result
        }
        
        return json.dumps(response, indent=2, ensure_ascii=False)
        
    except Exception as e:
        error_msg = f"Error: Failed to get availability zones - {str(e)}"
        logger.error(error_msg)
        return error_msg


@conditional_tool
async def set_flavor(
    flavor_name: str,
    action: str,
    vcpus: Optional[int] = None,
    ram: Optional[int] = None,
    disk: Optional[int] = None,
    ephemeral: Optional[int] = None,
    swap: Optional[int] = None,
    rxtx_factor: Optional[float] = None,
    is_public: Optional[bool] = None,
    properties: Optional[str] = None
) -> str:
    """
    Manage OpenStack flavors (create, delete, set properties, list)
    
    Args:
        flavor_name: Name of the flavor
        action: Action to perform (create, delete, show, list, set)
        vcpus: Number of virtual CPUs (for create)
        ram: Amount of RAM in MB (for create)
        disk: Disk size in GB (for create)
        ephemeral: Ephemeral disk size in GB (for create)
        swap: Swap size in MB (for create)
        rxtx_factor: RX/TX factor (for create)
        is_public: Whether flavor is public (for create)
        properties: JSON string of extra properties (for create/set)
    
    Returns:
        JSON string with flavor operation result
    """
    try:
        logger.info(f"Managing flavor: {flavor_name}, action: {action}")
        
        flavor_params = {}
        
        if vcpus is not None:
            flavor_params['vcpus'] = vcpus
        if ram is not None:
            flavor_params['ram'] = ram
        if disk is not None:
            flavor_params['disk'] = disk
        if ephemeral is not None:
            flavor_params['ephemeral'] = ephemeral
        if swap is not None:
            flavor_params['swap'] = swap
        if rxtx_factor is not None:
            flavor_params['rxtx_factor'] = rxtx_factor
        if is_public is not None:
            flavor_params['is_public'] = is_public
            
        if properties:
            import json as json_module
            flavor_params['properties'] = json_module.loads(properties)
        
        flavor_result = _set_flavor(flavor_name=flavor_name, action=action, **flavor_params)
        
        # Use centralized result handling
        return handle_operation_result(
            flavor_result,
            "Flavor Management",
            {
                "Action": action,
                "Flavor Name": flavor_name,
                "vCPUs": vcpus or "Not specified",
                "RAM": ram or "Not specified",
                "Disk": disk or "Not specified"
            }
        )
        
    except Exception as e:
        error_msg = f"Error: Failed to manage flavor - {str(e)}"
        logger.error(error_msg)
        return error_msg


@mcp.tool()
async def get_server_volumes(
    instance_name: str
) -> str:
    """
    Get all volumes attached to a specific server
    
    Args:
        instance_name: Name or ID of the server instance
    
    Returns:
        JSON string with server volumes information
    """
    try:
        logger.info(f"Getting volumes for server: {instance_name}")
        
        volumes_result = _get_server_volumes(instance_name=instance_name)
        
        response = {
            "timestamp": datetime.now().isoformat(),
            "operation": "get_server_volumes",
            "parameters": {
                "instance_name": instance_name
            },
            "result": volumes_result
        }
        
        return json.dumps(response, indent=2, ensure_ascii=False)
        
    except Exception as e:
        error_msg = f"Error: Failed to get server volumes - {str(e)}"
        logger.error(error_msg)
        return error_msg


@conditional_tool
async def set_server_volume(
    instance_name: str,
    action: str,
    volume_id: Optional[str] = None,
    volume_name: Optional[str] = None,
    device: Optional[str] = None,
    attachment_id: Optional[str] = None
) -> str:
    """
    Manage server volume attachments (attach, detach, list)
    
    Args:
        instance_name: Name or ID of the server instance
        action: Action to perform (attach, detach, list)
        volume_id: Volume ID for attach/detach operations
        volume_name: Volume name for attach/detach operations (alternative to volume_id)
        device: Device path for attach operation (optional, e.g., /dev/vdb)
        attachment_id: Attachment ID for detach operation (alternative to volume_id/name)
    
    Returns:
        JSON string with server volume operation result
    """
    try:
        logger.info(f"Managing server volume: {instance_name}, action: {action}")
        
        volume_params = {}
        
        if volume_id:
            volume_params['volume_id'] = volume_id
        if volume_name:
            volume_params['volume_name'] = volume_name
        if device:
            volume_params['device'] = device
        if attachment_id:
            volume_params['attachment_id'] = attachment_id
        
        volume_result = _set_server_volume(
            instance_name=instance_name, 
            action=action, 
            **volume_params
        )
        
        # Use centralized result handling
        return handle_operation_result(
            volume_result,
            "Server Volume Management",
            {
                "Action": action,
                "Instance Name": instance_name,
                "Volume Name": volume_name or "Not specified",
                "Device": device or "Not specified"
            }
        )
        
    except Exception as e:
        error_msg = f"Error: Failed to manage server volume - {str(e)}"
        logger.error(error_msg)
        return error_msg


# =============================================================================
# Main execution
# =============================================================================

if __name__ == "__main__":
    import asyncio
    
    parser = argparse.ArgumentParser(description="OpenStack MCP Server")
    parser.add_argument("--log-level", choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], 
                        default=os.environ.get("MCP_LOG_LEVEL", "INFO"), help="Logging level")
    parser.add_argument("--type", choices=["stdio", "streamable-http"], default="stdio", 
                        help="Transport type (default: stdio)")
    parser.add_argument("--host", default="127.0.0.1", help="Host address for HTTP transport (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8080, help="Port number for HTTP transport (default: 8080)")
    parser.add_argument("--auth-enable", action="store_true", 
                        help="Enable Bearer token authentication for streamable-http mode")
    parser.add_argument("--secret-key", help="Secret key for Bearer token authentication")
    
    args = parser.parse_args()
    
    # Set log level (CLI overrides environment)
    logger.setLevel(args.log_level)
    
    # Update authentication if provided via CLI
    if args.auth_enable and args.secret_key:
        logger.info("Authentication enabled via CLI arguments")
        
        tokens = {
            args.secret_key: {
                "client_id": "openstack-ops-client",
                "user": "admin",
                "scopes": ["read", "write"],
                "description": "CLI-provided access token"
            }
        }
        
        auth = StaticTokenVerifier(tokens=tokens)
        # Note: CLI auth override requires server restart to take full effect
        logger.warning("CLI auth override requires server restart to take full effect")
    
    # Validate OpenStack connection early
    try:
        conn = get_openstack_connection()
        logger.info("✓ OpenStack connection validated successfully")
    except Exception as e:
        logger.error(f"✗ Failed to connect to OpenStack: {e}")
        logger.error("Please check your OpenStack credentials in .env file")
        sys.exit(1)
    
    logger.info(f"Starting MCP server with {args.type} transport")
    logger.info(f"Log level set via {'CLI' if 'log-level' in sys.argv else 'environment'} to {args.log_level}")
    logger.info(f"Modify operations allowed: {_is_modify_operation_allowed()}")
    
    # Get auth status for logging
    auth_enabled = _auth_enable or (args.auth_enable and args.secret_key)
    logger.info(f"Authentication: {'Enabled' if auth_enabled else 'Disabled'}")
    
    if args.type == "stdio":
        logger.info("MCP server running with stdio transport")
        mcp.run()
    elif args.type == "streamable-http":
        logger.info(f"MCP server running with HTTP transport on {args.host}:{args.port}")
        mcp.run(transport="streamable-http", host=args.host, port=args.port)
    else:
        logger.error(f"Unknown transport type: {args.type}")
        sys.exit(1)


@conditional_tool
async def set_volume_backups(
    action: str,
    backup_name: str = "",
    volume_name: str = "",
    description: str = "",
    incremental: bool = False,
    force: bool = False
) -> str:
    """
    Manage OpenStack volume backups with comprehensive backup operations
    
    Args:
        action: Action to perform - list, show, delete, restore
        backup_name: Name or ID of the backup (required for show/delete/restore)
        volume_name: Name for restored volume (required for restore action)
        description: Description for backup operations
        incremental: Create incremental backup (default: False)
        force: Force backup creation even if volume is attached
        
    Returns:
        JSON string with backup operation results
    """
    
    if not _is_modify_operation_allowed() and action.lower() in ['delete', 'restore']:
        return json.dumps({
            'success': False,
            'message': f'Modify operations are not allowed in current environment for action: {action}',
            'error': f'MODIFY_OPERATIONS_DISABLED'
        })
    
    try:
        result = _set_volume_backups(
            action=action,
            backup_name=backup_name if backup_name else None,
            volume_name=volume_name,
            description=description,
            incremental=incremental,
            force=force
        )
        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({
            'success': False,
            'message': f'Failed to manage volume backup: {str(e)}',
            'error': str(e)
        }, indent=2)


@conditional_tool
async def set_volume_groups(
    action: str,
    group_name: str = "",
    description: str = "",
    group_type: str = "default",
    availability_zone: str = "",
    delete_volumes: bool = False
) -> str:
    """
    Manage OpenStack volume groups for consistent group operations
    
    Args:
        action: Action to perform - list, create, delete, show
        group_name: Name or ID of the volume group
        description: Description for the volume group
        group_type: Type of volume group (default: 'default')
        availability_zone: Availability zone for the group
        delete_volumes: Delete volumes when deleting group (default: False)
        
    Returns:
        JSON string with volume group operation results
    """
    
    if not _is_modify_operation_allowed() and action.lower() in ['create', 'delete']:
        return json.dumps({
            'success': False,
            'message': f'Modify operations are not allowed in current environment for action: {action}',
            'error': f'MODIFY_OPERATIONS_DISABLED'
        })
    
    try:
        result = _set_volume_groups(
            action=action,
            group_name=group_name if group_name else None,
            description=description,
            group_type=group_type,
            availability_zone=availability_zone if availability_zone else None,
            delete_volumes=delete_volumes
        )
        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({
            'success': False,
            'message': f'Failed to manage volume group: {str(e)}',
            'error': str(e)
        }, indent=2)


@conditional_tool
async def set_volume_qos(
    action: str,
    qos_name: str = "",
    consumer: str = "back-end",
    specs: str = "{}",
    force: bool = False
) -> str:
    """
    Manage OpenStack volume QoS specifications for performance control
    
    Args:
        action: Action to perform - list, create, delete, show, set
        qos_name: Name or ID of the QoS specification
        consumer: QoS consumer type - 'front-end', 'back-end', or 'both'
        specs: JSON string of QoS specifications (e.g., '{"read_iops_sec": 1000}')
        force: Force deletion even if QoS is associated with volume types
        
    Returns:
        JSON string with QoS operation results
    """
    
    if not _is_modify_operation_allowed() and action.lower() in ['create', 'delete', 'set']:
        return json.dumps({
            'success': False,
            'message': f'Modify operations are not allowed in current environment for action: {action}',
            'error': f'MODIFY_OPERATIONS_DISABLED'
        })
    
    try:
        # Parse specs from JSON string
        import json as json_lib
        parsed_specs = json_lib.loads(specs) if specs != "{}" else {}
        
        result = _set_volume_qos(
            action=action,
            qos_name=qos_name if qos_name else None,
            consumer=consumer,
            specs=parsed_specs,
            force=force
        )
        return json.dumps(result, indent=2)
    except json_lib.JSONDecodeError as e:
        return json.dumps({
            'success': False,
            'message': f'Invalid JSON in specs parameter: {str(e)}',
            'error': str(e)
        }, indent=2)
    except Exception as e:
        return json.dumps({
            'success': False,
            'message': f'Failed to manage volume QoS: {str(e)}',
            'error': str(e)
        }, indent=2)


@conditional_tool
async def set_network_ports(
    action: str,
    port_name: str = "",
    network_id: str = "",
    description: str = "",
    admin_state_up: bool = True,
    security_groups: str = "[]"
) -> str:
    """
    Manage OpenStack network ports for VM and network connectivity
    
    Args:
        action: Action to perform - list, create, delete
        port_name: Name or ID of the port
        network_id: Network ID for port creation (required for create)
        description: Description for the port
        admin_state_up: Administrative state (default: True)
        security_groups: JSON array of security group IDs (e.g., '["sg1", "sg2"]')
        
    Returns:
        JSON string with port management operation results
    """
    
    if not _is_modify_operation_allowed() and action.lower() in ['create', 'delete']:
        return json.dumps({
            'success': False,
            'message': f'Modify operations are not allowed in current environment for action: {action}',
            'error': f'MODIFY_OPERATIONS_DISABLED'
        })
    
    try:
        # Parse security groups from JSON string
        import json as json_lib
        parsed_security_groups = json_lib.loads(security_groups) if security_groups != "[]" else []
        
        result = _set_network_ports(
            action=action,
            port_name=port_name if port_name else None,
            network_id=network_id if network_id else None,
            description=description,
            admin_state_up=admin_state_up,
            security_groups=parsed_security_groups
        )
        return json.dumps(result, indent=2)
    except json_lib.JSONDecodeError as e:
        return json.dumps({
            'success': False,
            'message': f'Invalid JSON in security_groups parameter: {str(e)}',
            'error': str(e)
        }, indent=2)
    except Exception as e:
        return json.dumps({
            'success': False,
            'message': f'Failed to manage network port: {str(e)}',
            'error': str(e)
        }, indent=2)


@conditional_tool
async def set_subnets(
    action: str,
    subnet_name: str = "",
    network_id: str = "",
    cidr: str = "",
    description: str = "",
    ip_version: int = 4,
    enable_dhcp: bool = True,
    gateway_ip: str = "",
    dns_nameservers: str = "[]"
) -> str:
    """
    Manage OpenStack network subnets for IP address allocation
    
    Args:
        action: Action to perform - list, create, delete
        subnet_name: Name or ID of the subnet
        network_id: Network ID for subnet creation (required for create)
        cidr: CIDR notation for subnet (required for create, e.g., '192.168.1.0/24')
        description: Description for the subnet
        ip_version: IP version 4 or 6 (default: 4)
        enable_dhcp: Enable DHCP for the subnet (default: True)
        gateway_ip: Gateway IP address (auto-assigned if not provided)
        dns_nameservers: JSON array of DNS server IPs (e.g., '["8.8.8.8", "1.1.1.1"]')
        
    Returns:
        JSON string with subnet management operation results
    """
    
    if not _is_modify_operation_allowed() and action.lower() in ['create', 'delete']:
        return json.dumps({
            'success': False,
            'message': f'Modify operations are not allowed in current environment for action: {action}',
            'error': f'MODIFY_OPERATIONS_DISABLED'
        })
    
    try:
        # Parse DNS nameservers from JSON string
        import json as json_lib
        parsed_dns_nameservers = json_lib.loads(dns_nameservers) if dns_nameservers != "[]" else []
        
        result = _set_subnets(
            action=action,
            subnet_name=subnet_name if subnet_name else None,
            network_id=network_id if network_id else None,
            cidr=cidr if cidr else None,
            description=description,
            ip_version=ip_version,
            enable_dhcp=enable_dhcp,
            gateway_ip=gateway_ip if gateway_ip else None,
            dns_nameservers=parsed_dns_nameservers
        )
        return json.dumps(result, indent=2)
    except json_lib.JSONDecodeError as e:
        return json.dumps({
            'success': False,
            'message': f'Invalid JSON in dns_nameservers parameter: {str(e)}',
            'error': str(e)
        }, indent=2)
    except Exception as e:
        return json.dumps({
            'success': False,
            'message': f'Failed to manage subnet: {str(e)}',
            'error': str(e)
        }, indent=2)


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


@conditional_tool
async def set_network_qos_policies(
    action: str,
    policy_name: str = "",
    description: str = "",
    shared: bool = False
) -> str:
    """
    Manage OpenStack network QoS policies for bandwidth and traffic control
    
    Args:
        action: Action to perform - list, create, delete
        policy_name: Name or ID of the QoS policy
        description: Description for the QoS policy
        shared: Make policy available to other projects (default: False)
        
    Returns:
        JSON string with network QoS policy management operation results
    """
    
    if not _is_modify_operation_allowed() and action.lower() in ['create', 'delete']:
        return json.dumps({
            'success': False,
            'message': f'Modify operations are not allowed in current environment for action: {action}',
            'error': f'MODIFY_OPERATIONS_DISABLED'
        })
    
    try:
        result = _set_network_qos_policies(
            action=action,
            policy_name=policy_name if policy_name else None,
            description=description,
            shared=shared
        )
        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({
            'success': False,
            'message': f'Failed to manage network QoS policy: {str(e)}',
            'error': str(e)
        }, indent=2)


@conditional_tool
async def set_network_agents(
    action: str,
    agent_id: str = ""
) -> str:
    """
    Manage OpenStack network agents for network service monitoring and control
    
    Args:
        action: Action to perform - list, enable, disable
        agent_id: ID of the network agent (required for enable/disable)
        
    Returns:
        JSON string with network agent management operation results
    """
    
    if not _is_modify_operation_allowed() and action.lower() in ['enable', 'disable']:
        return json.dumps({
            'success': False,
            'message': f'Modify operations are not allowed in current environment for action: {action}',
            'error': f'MODIFY_OPERATIONS_DISABLED'
        })
    
    try:
        result = _set_network_agents(
            action=action,
            agent_id=agent_id if agent_id else None
        )
        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({
            'success': False,
            'message': f'Failed to manage network agent: {str(e)}',
            'error': str(e)
        }, indent=2)


@conditional_tool
async def set_image_members(
    action: str,
    image_name: str,
    member_project: str = ""
) -> str:
    """
    Manage OpenStack image members for sharing images between projects
    
    Args:
        action: Action to perform - list, add, remove
        image_name: Name or ID of the image
        member_project: Project ID to add/remove as member (required for add/remove)
        
    Returns:
        JSON string with image member management operation results
    """
    
    if not _is_modify_operation_allowed() and action.lower() in ['add', 'remove']:
        return json.dumps({
            'success': False,
            'message': f'Modify operations are not allowed in current environment for action: {action}',
            'error': f'MODIFY_OPERATIONS_DISABLED'
        })
    
    try:
        result = _set_image_members(
            action=action,
            image_name=image_name,
            member_project=member_project if member_project else None
        )
        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({
            'success': False,
            'message': f'Failed to manage image members: {str(e)}',
            'error': str(e)
        }, indent=2)


@conditional_tool
async def set_image_metadata(
    action: str,
    image_name: str,
    properties: str = "{}"
) -> str:
    """
    Manage OpenStack image metadata and properties
    
    Args:
        action: Action to perform - show, set
        image_name: Name or ID of the image
        properties: JSON string of properties to set (e.g., '{"os_type": "linux", "architecture": "x86_64"}')
        
    Returns:
        JSON string with image metadata management operation results
    """
    
    if not _is_modify_operation_allowed() and action.lower() in ['set']:
        return json.dumps({
            'success': False,
            'message': f'Modify operations are not allowed in current environment for action: {action}',
            'error': f'MODIFY_OPERATIONS_DISABLED'
        })
    
    try:
        # Parse properties from JSON string
        import json as json_lib
        parsed_properties = json_lib.loads(properties) if properties != "{}" else {}
        
        result = _set_image_metadata(
            action=action,
            image_name=image_name,
            properties=parsed_properties
        )
        return json.dumps(result, indent=2)
    except json_lib.JSONDecodeError as e:
        return json.dumps({
            'success': False,
            'message': f'Invalid JSON in properties parameter: {str(e)}',
            'error': str(e)
        }, indent=2)
    except Exception as e:
        return json.dumps({
            'success': False,
            'message': f'Failed to manage image metadata: {str(e)}',
            'error': str(e)
        }, indent=2)


@conditional_tool
async def set_image_visibility(
    action: str,
    image_name: str,
    visibility: str = ""
) -> str:
    """
    Manage OpenStack image visibility settings for access control
    
    Args:
        action: Action to perform - show, set
        image_name: Name or ID of the image
        visibility: Visibility setting - public, private, shared, community (required for set)
        
    Returns:
        JSON string with image visibility management operation results
    """
    
    if not _is_modify_operation_allowed() and action.lower() in ['set']:
        return json.dumps({
            'success': False,
            'message': f'Modify operations are not allowed in current environment for action: {action}',
            'error': f'MODIFY_OPERATIONS_DISABLED'
        })
    
    try:
        result = _set_image_visibility(
            action=action,
            image_name=image_name,
            visibility=visibility if visibility else None
        )
        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({
            'success': False,
            'message': f'Failed to manage image visibility: {str(e)}',
            'error': str(e)
        }, indent=2)


@conditional_tool
async def set_domains(
    action: str,
    domain_name: str = "",
    description: str = "",
    enabled: bool = True
) -> str:
    """
    Manage OpenStack domains for multi-tenancy organization
    
    Args:
        action: Action to perform - list, create
        domain_name: Name of the domain (required for create)
        description: Description for the domain
        enabled: Enable the domain (default: True)
        
    Returns:
        JSON string with domain management operation results
    """
    
    if not _is_modify_operation_allowed() and action.lower() in ['create']:
        return json.dumps({
            'success': False,
            'message': f'Modify operations are not allowed in current environment for action: {action}',
            'error': f'MODIFY_OPERATIONS_DISABLED'
        })
    
    try:
        result = _set_domains(
            action=action,
            domain_name=domain_name if domain_name else None,
            description=description,
            enabled=enabled
        )
        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({
            'success': False,
            'message': f'Failed to manage domain: {str(e)}',
            'error': str(e)
        }, indent=2)


@conditional_tool
async def set_identity_groups(
    action: str,
    group_name: str = "",
    description: str = "",
    domain_id: str = "default"
) -> str:
    """
    Manage OpenStack identity groups for user organization
    
    Args:
        action: Action to perform - list, create
        group_name: Name of the group (required for create)
        description: Description for the group
        domain_id: Domain ID for the group (default: 'default')
        
    Returns:
        JSON string with identity group management operation results
    """
    
    if not _is_modify_operation_allowed() and action.lower() in ['create']:
        return json.dumps({
            'success': False,
            'message': f'Modify operations are not allowed in current environment for action: {action}',
            'error': f'MODIFY_OPERATIONS_DISABLED'
        })
    
    try:
        result = _set_identity_groups(
            action=action,
            group_name=group_name if group_name else None,
            description=description,
            domain_id=domain_id
        )
        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({
            'success': False,
            'message': f'Failed to manage identity group: {str(e)}',
            'error': str(e)
        }, indent=2)


@conditional_tool
async def set_roles(
    action: str,
    role_name: str = "",
    description: str = "",
    domain_id: str = ""
) -> str:
    """
    Manage OpenStack roles for access control and permissions
    
    Args:
        action: Action to perform - list, create
        role_name: Name of the role (required for create)
        description: Description for the role
        domain_id: Domain ID for domain-scoped roles (optional)
        
    Returns:
        JSON string with role management operation results
    """
    
    if not _is_modify_operation_allowed() and action.lower() in ['create']:
        return json.dumps({
            'success': False,
            'message': f'Modify operations are not allowed in current environment for action: {action}',
            'error': f'MODIFY_OPERATIONS_DISABLED'
        })
    
    try:
        result = _set_roles(
            action=action,
            role_name=role_name if role_name else None,
            description=description,
            domain_id=domain_id if domain_id else None
        )
        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({
            'success': False,
            'message': f'Failed to manage role: {str(e)}',
            'error': str(e)
        }, indent=2)


@conditional_tool
async def set_services(
    action: str,
    service_name: str = ""
) -> str:
    """
    Manage OpenStack services for service catalog and endpoint management
    
    Args:
        action: Action to perform - list
        service_name: Name or ID of the service
        
    Returns:
        JSON string with service management operation results
    """
    
    try:
        result = _set_services(
            action=action,
            service_name=service_name if service_name else None
        )
        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({
            'success': False,
            'message': f'Failed to manage service: {str(e)}',
            'error': str(e)
        }, indent=2)


@conditional_tool
async def set_service_logs(
    action: str,
    service_name: str = "",
    log_level: str = "INFO"
) -> str:
    """
    Manage OpenStack service logs and logging configuration
    
    Args:
        action: Action to perform - list, show
        service_name: Name of the service to get logs for
        log_level: Log level filter (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        
    Returns:
        JSON string with service logs management operation results
    """
    
    try:
        result = _set_service_logs(
            action=action,
            service_name=service_name if service_name else None,
            log_level=log_level
        )
        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({
            'success': False,
            'message': f'Failed to manage service logs: {str(e)}',
            'error': str(e)
        }, indent=2)


@conditional_tool
async def set_metrics(
    action: str,
    resource_type: str = "compute",
    resource_id: str = ""
) -> str:
    """
    Manage OpenStack metrics collection and monitoring
    
    Args:
        action: Action to perform - list, show, summary
        resource_type: Type of resource (compute, network, storage, identity)
        resource_id: Specific resource ID to get metrics for
        
    Returns:
        JSON string with metrics management operation results
    """
    
    try:
        result = _set_metrics(
            action=action,
            resource_type=resource_type,
            resource_id=resource_id if resource_id else None
        )
        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({
            'success': False,
            'message': f'Failed to manage metrics: {str(e)}',
            'error': str(e)
        }, indent=2)


@conditional_tool
async def set_alarms(
    action: str,
    alarm_name: str = "",
    resource_id: str = "",
    threshold: float = 0.0,
    comparison: str = "gt"
) -> str:
    """
    Manage OpenStack alarms and alerting (requires Aodh service)
    
    Args:
        action: Action to perform - list, create, show, delete
        alarm_name: Name of the alarm
        resource_id: Resource ID to monitor
        threshold: Threshold value for alarm
        comparison: Comparison operator (gt, lt, eq, ne, ge, le)
        
    Returns:
        JSON string with alarm management operation results
    """
    
    if not _is_modify_operation_allowed() and action.lower() in ['create', 'delete']:
        return json.dumps({
            'success': False,
            'message': f'Modify operations are not allowed in current environment for action: {action}',
            'error': f'MODIFY_OPERATIONS_DISABLED'
        })
    
    try:
        result = _set_alarms(
            action=action,
            alarm_name=alarm_name if alarm_name else None,
            resource_id=resource_id if resource_id else None,
            threshold=threshold if threshold > 0.0 else None,
            comparison=comparison
        )
        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({
            'success': False,
            'message': f'Failed to manage alarms: {str(e)}',
            'error': str(e)
        }, indent=2)


@conditional_tool
async def set_compute_agents(
    action: str,
    agent_id: str = "",
    host: str = ""
) -> str:
    """
    Manage OpenStack compute agents and hypervisor monitoring
    
    Args:
        action: Action to perform - list, show
        agent_id: ID of specific agent
        host: Host name to filter agents
        
    Returns:
        JSON string with compute agent management operation results
    """
    
    try:
        result = _set_compute_agents(
            action=action,
            agent_id=agent_id if agent_id else None,
            host=host if host else None
        )
        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({
            'success': False,
            'message': f'Failed to manage compute agents: {str(e)}',
            'error': str(e)
        }, indent=2)


# =============================================================================
# LOAD BALANCER (OCTAVIA) TOOLS
# =============================================================================

@mcp.tool()
async def get_load_balancer_list(
    limit: int = 50,
    offset: int = 0,
    include_all: bool = False
) -> str:
    """
    Retrieve comprehensive list of OpenStack load balancers with detailed information.
    
    Functions:
    - Lists all load balancers in the OpenStack cluster
    - Provides detailed load balancer information including VIP, status, listeners
    - Supports pagination for large environments (limit/offset)
    - Shows listener count and basic listener information for each load balancer
    - Displays provisioning and operating status for troubleshooting
    
    Use when user requests:
    - "Show me all load balancers"
    - "List load balancers with details"
    - "What load balancers are available?"
    - "Show load balancer status"
    
    Args:
        limit: Maximum load balancers to return (1-200, default: 50)
        offset: Number of load balancers to skip for pagination (default: 0)  
        include_all: Return all load balancers ignoring limit/offset (default: False)
        
    Returns:
        JSON string containing load balancer details with summary statistics
    """
    try:
        logger.info(f"Getting load balancer list (limit={limit}, offset={offset}, include_all={include_all})")
        result = _get_load_balancer_list(
            limit=limit,
            offset=offset, 
            include_all=include_all
        )
        
        response = {
            "timestamp": datetime.now().isoformat(),
            "result": result
        }
        
        return json.dumps(response, indent=2, ensure_ascii=False)
        
    except Exception as e:
        error_msg = f"Error: Failed to get load balancer list - {str(e)}"
        logger.error(error_msg)
        return json.dumps({
            "timestamp": datetime.now().isoformat(),
            "error": error_msg,
            "success": False
        }, indent=2)


@mcp.tool()
async def get_load_balancer_details(lb_name_or_id: str) -> str:
    """
    Get detailed information about a specific OpenStack load balancer.
    
    Functions:
    - Shows comprehensive load balancer details including VIP configuration
    - Lists all listeners with their protocols and ports
    - Shows pools and members for each listener
    - Displays health monitor information if configured
    - Provides provisioning and operating status
    
    Use when user requests:
    - "Show details for load balancer [name/id]"
    - "Get load balancer configuration"
    - "Show load balancer listeners and pools"
    - "What's the status of load balancer [name]?"
    
    Args:
        lb_name_or_id: Load balancer name or ID to query
        
    Returns:
        JSON string containing detailed load balancer information
    """
    try:
        logger.info(f"Getting load balancer details for: {lb_name_or_id}")
        result = _get_load_balancer_details(lb_name_or_id)
        
        response = {
            "timestamp": datetime.now().isoformat(),
            "result": result
        }
        
        return json.dumps(response, indent=2, ensure_ascii=False)
        
    except Exception as e:
        error_msg = f"Error: Failed to get load balancer details - {str(e)}"
        logger.error(error_msg)
        return json.dumps({
            "timestamp": datetime.now().isoformat(),
            "error": error_msg,
            "success": False
        }, indent=2)


@conditional_tool
async def set_load_balancer(
    action: str,
    lb_name_or_id: str = "",
    name: str = "",
    vip_subnet_id: str = "",
    description: str = "",
    admin_state_up: bool = True,
    provider: str = "",
    flavor_id: str = "",
    availability_zone: str = "",
    cascade: bool = False
) -> str:
    """
    Comprehensive load balancer management operations (create, delete, set, unset, failover, stats, status).
    
    Functions:
    - Create new load balancers with VIP configuration and flavor/AZ options
    - Delete existing load balancers (with optional cascade delete)
    - Update/set load balancer properties (name, description, admin state)
    - Clear/unset load balancer settings (description)
    - Trigger load balancer failover operations
    - Get load balancer statistics (bytes in/out, connections)
    - Get load balancer status tree (detailed operational status)
    
    Use when user requests:
    - "Create a load balancer named [name] on subnet [id]"
    - "Delete load balancer [name/id] with cascade"
    - "Update load balancer [name] description to [text]"
    - "Clear load balancer [name] description"
    - "Failover load balancer [name/id]"
    - "Show load balancer [name] statistics"
    - "Get load balancer [name] status tree"
    
    Args:
        action: Operation to perform (create, delete, set, unset, failover, stats, status)
        lb_name_or_id: Load balancer name or ID (required for most operations)
        name: Name for new load balancer (required for create)
        vip_subnet_id: VIP subnet ID (required for create)
        description: Description for load balancer
        admin_state_up: Administrative state (default: True)
        provider: Load balancer provider (optional)
        flavor_id: Flavor ID for load balancer (optional)
        availability_zone: Availability zone (optional)
        cascade: Whether to cascade delete (for delete action)
        
    Returns:
        JSON string with operation results and load balancer details
    """
    if not _is_modify_operation_allowed() and action.lower() in ['create', 'delete', 'set', 'unset', 'failover']:
        return json.dumps({
            'success': False,
            'message': f'Modify operations are not allowed in current environment for action: {action}',
            'error': f'MODIFY_OPERATIONS_DISABLED'
        })
    
    try:
        logger.info(f"Managing load balancer with action: {action}")
        
        kwargs = {
            'lb_name_or_id': lb_name_or_id if lb_name_or_id else None,
            'name': name if name else None,
            'vip_subnet_id': vip_subnet_id if vip_subnet_id else None,
            'description': description if description else None,
            'admin_state_up': admin_state_up,
            'provider': provider if provider else None,
            'flavor_id': flavor_id if flavor_id else None,
            'availability_zone': availability_zone if availability_zone else None,
            'cascade': cascade
        }
        
        # Remove None values
        kwargs = {k: v for k, v in kwargs.items() if v is not None}
        
        result = _set_load_balancer(action=action, **kwargs)
        
        response = {
            "timestamp": datetime.now().isoformat(),
            "result": result
        }
        
        return json.dumps(response, indent=2, ensure_ascii=False)
        
    except Exception as e:
        error_msg = f"Error: Failed to manage load balancer - {str(e)}"
        logger.error(error_msg)
        return json.dumps({
            "timestamp": datetime.now().isoformat(),
            "error": error_msg,
            "success": False
        }, indent=2)


@mcp.tool()
async def get_load_balancer_listeners(lb_name_or_id: str) -> str:
    """
    Get listeners for a specific OpenStack load balancer.
    
    Functions:
    - Lists all listeners attached to a load balancer
    - Shows listener protocols, ports, and configurations
    - Displays admin state and default pool associations
    - Provides creation and update timestamps
    
    Use when user requests:
    - "Show listeners for load balancer [name/id]"
    - "List load balancer listeners"
    - "What ports are configured on load balancer [name]?"
    - "Show listener configuration for [lb_name]"
    
    Args:
        lb_name_or_id: Load balancer name or ID
        
    Returns:
        JSON string containing listener details for the load balancer
    """
    try:
        logger.info(f"Getting listeners for load balancer: {lb_name_or_id}")
        result = _get_load_balancer_listeners(lb_name_or_id)
        
        response = {
            "timestamp": datetime.now().isoformat(),
            "result": result
        }
        
        return json.dumps(response, indent=2, ensure_ascii=False)
        
    except Exception as e:
        error_msg = f"Error: Failed to get load balancer listeners - {str(e)}"
        logger.error(error_msg)
        return json.dumps({
            "timestamp": datetime.now().isoformat(),
            "error": error_msg,
            "success": False
        }, indent=2)


@conditional_tool
async def set_load_balancer_listener(
    action: str,
    listener_name_or_id: str = "",
    name: str = "",
    lb_name_or_id: str = "",
    protocol: str = "",
    protocol_port: int = 0,
    description: str = "",
    admin_state_up: bool = True,
    connection_limit: int = 0,
    default_pool_id: str = ""
) -> str:
    """
    Comprehensive load balancer listener management (create, delete, set, unset, show, stats).
    
    Functions:
    - Create new listeners on load balancers with protocol configuration
    - Delete existing listeners
    - Set/update listener properties (name, description, connection limits)
    - Unset/clear listener settings (description, connection limits, default pool)
    - Show detailed listener information
    - Get listener statistics (traffic and connection metrics)
    
    Use when user requests:
    - "Create listener [name] on load balancer [lb_name] for HTTP on port 80"
    - "Delete listener [name/id]"
    - "Update listener [name] connection limit to 1000"
    - "Clear listener [name] description"
    - "Show listener [name/id] details"
    - "Get listener [name] statistics"
    
    Args:
        action: Operation to perform (create, delete, set, unset, show, stats)
        listener_name_or_id: Listener name or ID (required for delete/set/unset/show/stats)
        name: Name for new listener (required for create)
        lb_name_or_id: Load balancer name or ID (required for create)
        protocol: Listener protocol - HTTP, HTTPS, TCP, UDP (required for create)
        protocol_port: Port number for listener (required for create)
        description: Description for listener
        admin_state_up: Administrative state (default: True)
        connection_limit: Maximum number of connections (0 = unlimited)
        default_pool_id: Default pool ID for the listener
        
    Returns:
        JSON string with operation results and listener details
    """
    if not _is_modify_operation_allowed() and action.lower() in ['create', 'delete', 'set', 'unset']:
        return json.dumps({
            'success': False,
            'message': f'Modify operations are not allowed in current environment for action: {action}',
            'error': f'MODIFY_OPERATIONS_DISABLED'
        })
    
    try:
        logger.info(f"Managing load balancer listener with action: {action}")
        
        kwargs = {
            'listener_name_or_id': listener_name_or_id if listener_name_or_id else None,
            'name': name if name else None,
            'lb_name_or_id': lb_name_or_id if lb_name_or_id else None,
            'protocol': protocol.upper() if protocol else None,
            'protocol_port': protocol_port if protocol_port > 0 else None,
            'description': description if description else None,
            'admin_state_up': admin_state_up,
            'connection_limit': connection_limit if connection_limit > 0 else None,
            'default_pool_id': default_pool_id if default_pool_id else None
        }
        
        # Remove None values
        kwargs = {k: v for k, v in kwargs.items() if v is not None}
        
        result = _set_load_balancer_listener(action=action, **kwargs)
        
        response = {
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "result": result
        }
        
        return json.dumps(response, indent=2, ensure_ascii=False)
        
    except Exception as e:
        error_msg = f"Error: Failed to manage load balancer listener - {str(e)}"
        logger.error(error_msg)
        return json.dumps({
            "timestamp": datetime.now().isoformat(),
            "error": error_msg,
            "success": False
        }, indent=2)


@mcp.tool()
async def get_load_balancer_pools(listener_name_or_id: str = "") -> str:
    """
    Get load balancer pools, optionally filtered by listener.
    
    Functions:
    - Lists all pools or pools for a specific listener
    - Shows pool protocols, load balancing algorithms
    - Displays members in each pool with their status
    - Provides health monitor associations
    
    Use when user requests:
    - "Show all load balancer pools"
    - "List pools for listener [name/id]"
    - "What pools are configured on [listener_name]?"
    - "Show pool members and their status"
    
    Args:
        listener_name_or_id: Optional listener name or ID to filter pools
        
    Returns:
        JSON string containing pool details with member information
    """
    try:
        logger.info(f"Getting load balancer pools (listener filter: {listener_name_or_id if listener_name_or_id else 'none'})")
        result = _get_load_balancer_pools(
            listener_name_or_id=listener_name_or_id if listener_name_or_id else None
        )
        
        response = {
            "timestamp": datetime.now().isoformat(),
            "result": result
        }
        
        return json.dumps(response, indent=2, ensure_ascii=False)
        
    except Exception as e:
        error_msg = f"Error: Failed to get load balancer pools - {str(e)}"
        logger.error(error_msg)
        return json.dumps({
            "timestamp": datetime.now().isoformat(),
            "error": error_msg,
            "success": False
        }, indent=2)


@conditional_tool
async def set_load_balancer_pool(
    action: str,
    pool_name_or_id: str = "",
    name: str = "",
    listener_name_or_id: str = "",
    protocol: str = "",
    lb_algorithm: str = "ROUND_ROBIN",
    description: str = "",
    admin_state_up: bool = True
) -> str:
    """
    Manage OpenStack load balancer pool operations (create, delete, show, set).

    Functions:
    - Create new pools for listeners with specified protocols
    - Delete existing pools
    - Show detailed pool information including members
    - Update pool properties (name, description, algorithm, admin state)

    Use when user requests:
    - "Create pool [name] for listener [listener] using HTTP"
    - "Delete pool [name/id]"
    - "Show pool [name/id] details"
    - "Update pool [name] algorithm to LEAST_CONNECTIONS"

    Args:
        action: Operation to perform (create, delete, show, set)
        pool_name_or_id: Pool name or ID (required for delete/show/set)
        name: Name for new pool (required for create)
        listener_name_or_id: Listener name or ID (required for create)
        protocol: Pool protocol - HTTP, HTTPS, TCP, UDP (required for create)
        lb_algorithm: Load balancing algorithm (ROUND_ROBIN, LEAST_CONNECTIONS, SOURCE_IP)
        description: Description for the pool
        admin_state_up: Administrative state (default: True)
        
    Returns:
        JSON string with operation results and pool details
    """
    try:
        from .functions import set_load_balancer_pool
        
        result = set_load_balancer_pool(
            action=action,
            pool_name_or_id=pool_name_or_id,
            name=name,
            listener_name_or_id=listener_name_or_id,
            protocol=protocol,
            lb_algorithm=lb_algorithm,
            description=description,
            admin_state_up=admin_state_up
        )
        
        response = {
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "result": result
        }
        
        return json.dumps(response, indent=2, ensure_ascii=False)
        
    except Exception as e:
        error_msg = f"Error: Failed to manage load balancer pool - {str(e)}"
        logger.error(error_msg)
        return json.dumps({
            "timestamp": datetime.now().isoformat(),
            "error": error_msg,
            "success": False
        }, indent=2)


@mcp.tool()
async def get_load_balancer_pool_members(pool_name_or_id: str) -> str:
    """
    Get members for a specific OpenStack load balancer pool.

    Functions:
    - Lists all members in a specific pool
    - Shows member addresses, ports, weights, and health status
    - Displays member admin state and operational status
    - Provides monitor configuration for each member

    Use when user requests:
    - "Show members for pool [name/id]"
    - "List pool members"
    - "What members are in pool [name]?"
    - "Show pool member status"

    Args:
        pool_name_or_id: Pool name or ID to query members for
        
    Returns:
        JSON string containing member details for the pool
    """
    try:
        from .functions import get_load_balancer_pool_members
        
        result = get_load_balancer_pool_members(pool_name_or_id)
        
        response = {
            "timestamp": datetime.now().isoformat(),
            "pool": pool_name_or_id,
            "result": result
        }
        
        return json.dumps(response, indent=2, ensure_ascii=False)
        
    except Exception as e:
        error_msg = f"Error: Failed to get pool members - {str(e)}"
        logger.error(error_msg)
        return json.dumps({
            "timestamp": datetime.now().isoformat(),
            "error": error_msg,
            "success": False
        }, indent=2)


@conditional_tool
async def set_load_balancer_pool_member(
    action: str,
    pool_name_or_id: str,
    member_id: str = "",
    name: str = "",
    address: str = "",
    protocol_port: int = 0,
    weight: int = 1,
    admin_state_up: bool = True,
    backup: bool = False,
    monitor_address: str = "",
    monitor_port: int = 0
) -> str:
    """
    Manage OpenStack load balancer pool member operations (create, delete, show, set).

    Functions:
    - Add new members to pools with IP address and port
    - Remove existing members from pools
    - Show detailed member information
    - Update member properties (weight, admin state, backup status)

    Use when user requests:
    - "Add member 192.168.1.10:80 to pool [name] with weight 5"
    - "Remove member [id] from pool [name]"
    - "Show member [id] details in pool [name]"
    - "Set member [id] as backup in pool [name]"

    Args:
        action: Operation to perform (create, delete, show, set)
        pool_name_or_id: Pool name or ID (required)
        member_id: Member ID (required for delete/show/set)
        name: Name for the member
        address: IP address of the member (required for create)
        protocol_port: Port number (required for create)
        weight: Member weight (1-256, default: 1)
        admin_state_up: Administrative state (default: True)
        backup: Backup member flag (default: False)
        monitor_address: Monitor IP address
        monitor_port: Monitor port
        
    Returns:
        JSON string with operation results and member details
    """
    try:
        from .functions import set_load_balancer_pool_member
        
        result = set_load_balancer_pool_member(
            action=action,
            pool_name_or_id=pool_name_or_id,
            member_id=member_id,
            name=name,
            address=address,
            protocol_port=protocol_port,
            weight=weight,
            admin_state_up=admin_state_up,
            backup=backup,
            monitor_address=monitor_address,
            monitor_port=monitor_port
        )
        
        response = {
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "pool": pool_name_or_id,
            "result": result
        }
        
        return json.dumps(response, indent=2, ensure_ascii=False)
        
    except Exception as e:
        error_msg = f"Error: Failed to manage pool member - {str(e)}"
        logger.error(error_msg)
        return json.dumps({
            "timestamp": datetime.now().isoformat(),
            "error": error_msg,
            "success": False
        }, indent=2)


@mcp.tool()
async def get_load_balancer_health_monitors(pool_name_or_id: str = "") -> str:
    """
    Get health monitors, optionally filtered by pool.

    Functions:
    - Lists all health monitors or monitors for a specific pool
    - Shows monitor types (HTTP, HTTPS, TCP, PING, UDP-CONNECT)
    - Displays health check intervals, timeouts, and retry settings
    - Provides HTTP-specific settings (method, URL path, expected codes)

    Use when user requests:
    - "Show all health monitors"
    - "List health monitors for pool [name/id]"
    - "What health checks are configured?"
    - "Show health monitor configuration"

    Args:
        pool_name_or_id: Optional pool name or ID to filter monitors (empty for all)
        
    Returns:
        JSON string containing health monitor details
    """
    try:
        from .functions import get_load_balancer_health_monitors
        
        result = get_load_balancer_health_monitors(pool_name_or_id)
        
        response = {
            "timestamp": datetime.now().isoformat(),
            "filter": pool_name_or_id if pool_name_or_id else "all monitors",
            "result": result
        }
        
        return json.dumps(response, indent=2, ensure_ascii=False)
        
    except Exception as e:
        error_msg = f"Error: Failed to get health monitors - {str(e)}"
        logger.error(error_msg)
        return json.dumps({
            "timestamp": datetime.now().isoformat(),
            "error": error_msg,
            "success": False
        }, indent=2)


@conditional_tool
async def set_load_balancer_health_monitor(
    action: str,
    monitor_name_or_id: str = "",
    name: str = "",
    pool_name_or_id: str = "",
    monitor_type: str = "HTTP",
    delay: int = 10,
    timeout: int = 5,
    max_retries: int = 3,
    max_retries_down: int = 3,
    admin_state_up: bool = True,
    http_method: str = "GET",
    url_path: str = "/",
    expected_codes: str = "200"
) -> str:
    """
    Comprehensive health monitor management operations (create, delete, set, unset, show).

    Functions:
    - Create new health monitors for pools with various protocols (HTTP, HTTPS, TCP, UDP, PING)
    - Delete existing health monitors
    - Set/update monitor settings (timing, HTTP parameters, admin state)
    - Unset/clear monitor settings (HTTP parameters, expected codes)
    - Show detailed health monitor configuration and status

    Use when user requests:
    - "Create HTTP health monitor for pool [name] checking /health every 30 seconds"
    - "Delete health monitor [name/id]"
    - "Update health monitor [name] timeout to 10 seconds"
    - "Clear health monitor [name] expected codes"
    - "Show health monitor [name/id] details"

    Args:
        action: Operation to perform (create, delete, set, unset, show)
        monitor_name_or_id: Monitor name or ID (required for delete/set/unset/show)
        name: Name for the monitor
        pool_name_or_id: Pool name or ID (required for create)
        monitor_type: Monitor type (HTTP, HTTPS, TCP, PING, UDP-CONNECT, SCTP)
        delay: Delay between health checks in seconds (default: 10)
        timeout: Timeout for health check in seconds (default: 5)
        max_retries: Maximum retries before marking unhealthy (default: 3)
        max_retries_down: Maximum retries before marking down (default: 3)
        admin_state_up: Administrative state (default: True)
        http_method: HTTP method for HTTP/HTTPS monitors (default: GET)
        url_path: URL path for HTTP/HTTPS monitors (default: /)
        expected_codes: Expected HTTP status codes (default: 200)
        
    Returns:
        JSON string with operation results and health monitor details
    """
    if not _is_modify_operation_allowed() and action.lower() in ['create', 'delete', 'set', 'unset']:
        return json.dumps({
            'success': False,
            'message': f'Modify operations are not allowed in current environment for action: {action}',
            'error': f'MODIFY_OPERATIONS_DISABLED'
        })
    
    try:
        logger.info(f"Managing health monitor with action: {action}")
        
        result = _set_load_balancer_health_monitor(
            action=action,
            monitor_name_or_id=monitor_name_or_id,
            name=name,
            pool_name_or_id=pool_name_or_id,
            monitor_type=monitor_type,
            delay=delay,
            timeout=timeout,
            max_retries=max_retries,
            max_retries_down=max_retries_down,
            admin_state_up=admin_state_up,
            http_method=http_method,
            url_path=url_path,
            expected_codes=expected_codes
        )
        
        response = {
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "result": result
        }
        
        return json.dumps(response, indent=2, ensure_ascii=False)
        
    except Exception as e:
        error_msg = f"Error: Failed to manage health monitor - {str(e)}"
        logger.error(error_msg)
        return json.dumps({
            "timestamp": datetime.now().isoformat(),
            "error": error_msg,
            "success": False
        }, indent=2)


# ===== LOAD BALANCER L7 POLICY TOOLS =====

@mcp.tool()
async def get_load_balancer_l7_policies(listener_name_or_id: str = "") -> str:
    """
    Get L7 policies for a listener or all L7 policies.
    
    Args:
        listener_name_or_id: Optional listener name or ID to filter policies. If empty, shows all policies.
    
    Returns:
        JSON string containing L7 policies information including policy details, actions, and rules
    """
    try:
        logger.info(f"Getting L7 policies for listener: {listener_name_or_id}")
        
        result = _get_load_balancer_l7_policies(listener_name_or_id)
        
        response = {
            "timestamp": datetime.now().isoformat(),
            "result": result
        }
        
        return json.dumps(response, indent=2, ensure_ascii=False)
        
    except Exception as e:
        error_msg = f"Error: Failed to get L7 policies - {str(e)}"
        logger.error(error_msg)
        return json.dumps({
            "timestamp": datetime.now().isoformat(),
            "error": error_msg,
            "success": False
        }, indent=2)


@conditional_tool
async def set_load_balancer_l7_policy(
    action: str,
    listener_name_or_id: str = "",
    policy_name_or_id: str = "",
    name: str = "",
    action_type: str = "REJECT",
    description: str = "",
    position: int = 1,
    redirect_pool_id: str = "",
    redirect_url: str = "",
    admin_state_up: bool = True
) -> str:
    """
    Manage L7 policy operations (create, delete, set, unset, show).
    
    Args:
        action: Action to perform (create, delete, set, unset, show)
        listener_name_or_id: Listener name or ID (required for create)
        policy_name_or_id: Policy name or ID (required for delete/update operations)
        name: Policy name (for create)
        action_type: Policy action (REJECT, REDIRECT_TO_POOL, REDIRECT_TO_URL)
        description: Policy description
        position: Policy position in the list (1-based)
        redirect_pool_id: Pool ID for REDIRECT_TO_POOL action
        redirect_url: URL for REDIRECT_TO_URL action
        admin_state_up: Administrative state
    
    Returns:
        JSON string with operation results
    """
    try:
        logger.info(f"Managing L7 policy with action: {action}")
        
        kwargs = {
            'listener_name_or_id': listener_name_or_id,
            'policy_name_or_id': policy_name_or_id,
            'name': name,
            'action_type': action_type,
            'description': description,
            'position': position,
            'redirect_pool_id': redirect_pool_id if redirect_pool_id else None,
            'redirect_url': redirect_url if redirect_url else None,
            'admin_state_up': admin_state_up
        }
        
        result = _set_load_balancer_l7_policy(action, **kwargs)
        
        response = {
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "result": result
        }
        
        return json.dumps(response, indent=2, ensure_ascii=False)
        
    except Exception as e:
        error_msg = f"Error: Failed to manage L7 policy - {str(e)}"
        logger.error(error_msg)
        return json.dumps({
            "timestamp": datetime.now().isoformat(),
            "error": error_msg,
            "success": False
        }, indent=2)


# ===== LOAD BALANCER AMPHORA TOOLS =====

@mcp.tool()
async def get_load_balancer_amphorae(lb_name_or_id: str = "") -> str:
    """
    Get amphora instances for a load balancer or all amphorae.
    
    Args:
        lb_name_or_id: Optional load balancer name or ID. If empty, shows all amphorae.
    
    Returns:
        JSON string containing amphora information including compute instances and network details
    """
    try:
        logger.info(f"Getting amphorae for load balancer: {lb_name_or_id}")
        
        result = _get_load_balancer_amphorae(lb_name_or_id)
        
        response = {
            "timestamp": datetime.now().isoformat(),
            "result": result
        }
        
        return json.dumps(response, indent=2, ensure_ascii=False)
        
    except Exception as e:
        error_msg = f"Error: Failed to get amphorae - {str(e)}"
        logger.error(error_msg)
        return json.dumps({
            "timestamp": datetime.now().isoformat(),
            "error": error_msg,
            "success": False
        }, indent=2)


@conditional_tool
async def set_load_balancer_amphora(
    action: str,
    amphora_id: str = ""
) -> str:
    """
    Manage amphora operations (configure, failover, show).
    
    NOTE: 'delete' and 'stats' operations are NOT supported by OpenStack SDK.
    Only configure, failover, and show operations are available.
    
    Args:
        action: Action to perform (configure, failover, show)
        amphora_id: Amphora ID (required)
    
    Returns:
        JSON string with operation results
    """
    if not _is_modify_operation_allowed() and action.lower() in ['configure', 'failover']:
        return json.dumps({
            'success': False,
            'message': f'Modify operations are not allowed in current environment for action: {action}',
            'error': f'MODIFY_OPERATIONS_DISABLED'
        })
    
    try:
        logger.info(f"Managing amphora with action: {action}")
        
        if action in ['delete', 'stats']:
            return json.dumps({
                'success': False,
                'message': f'Action "{action}" is not supported by OpenStack SDK. Available actions: configure, failover, show',
                'error': 'UNSUPPORTED_OPERATION'
            })
        
        result = _set_load_balancer_amphora(action, amphora_id=amphora_id)
        
        response = {
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "result": result
        }
        
        return json.dumps(response, indent=2, ensure_ascii=False)
        
    except Exception as e:
        error_msg = f"Error: Failed to manage amphora - {str(e)}"
        logger.error(error_msg)
        return json.dumps({
            "timestamp": datetime.now().isoformat(),
            "error": error_msg,
            "success": False
        }, indent=2)


# ===== LOAD BALANCER ADVANCED INFO TOOLS =====

@mcp.tool()
async def get_load_balancer_availability_zones() -> str:
    """
    Get load balancer availability zones.
    
    Returns:
        JSON string containing availability zones information
    """
    try:
        logger.info("Getting load balancer availability zones")
        
        result = _get_load_balancer_availability_zones()
        
        response = {
            "timestamp": datetime.now().isoformat(),
            "result": result
        }
        
        return json.dumps(response, indent=2, ensure_ascii=False)
        
    except Exception as e:
        error_msg = f"Error: Failed to get availability zones - {str(e)}"
        logger.error(error_msg)
        return json.dumps({
            "timestamp": datetime.now().isoformat(),
            "error": error_msg,
            "success": False
        }, indent=2)


@mcp.tool()
async def get_load_balancer_flavors() -> str:
    """
    Get load balancer flavors.
    
    Returns:
        JSON string containing flavors information
    """
    try:
        logger.info("Getting load balancer flavors")
        
        result = _get_load_balancer_flavors()
        
        response = {
            "timestamp": datetime.now().isoformat(),
            "result": result
        }
        
        return json.dumps(response, indent=2, ensure_ascii=False)
        
    except Exception as e:
        error_msg = f"Error: Failed to get flavors - {str(e)}"
        logger.error(error_msg)
        return json.dumps({
            "timestamp": datetime.now().isoformat(),
            "error": error_msg,
            "success": False
        }, indent=2)


@mcp.tool()
async def get_load_balancer_providers() -> str:
    """
    Get load balancer providers.
    
    Returns:
        JSON string containing providers information
    """
    try:
        logger.info("Getting load balancer providers")
        
        result = _get_load_balancer_providers()
        
        response = {
            "timestamp": datetime.now().isoformat(),
            "result": result
        }
        
        return json.dumps(response, indent=2, ensure_ascii=False)
        
    except Exception as e:
        error_msg = f"Error: Failed to get providers - {str(e)}"
        logger.error(error_msg)
        return json.dumps({
            "timestamp": datetime.now().isoformat(),
            "error": error_msg,
            "success": False
        }, indent=2)


@mcp.tool()
async def get_load_balancer_quotas(project_id: str = "") -> str:
    """
    Get load balancer quotas for a project or all projects.
    
    Args:
        project_id: Optional project ID. If empty, shows quotas for all projects.
    
    Returns:
        JSON string containing quota information
    """
    try:
        logger.info(f"Getting load balancer quotas for project: {project_id}")
        
        result = _get_load_balancer_quotas(project_id)
        
        response = {
            "timestamp": datetime.now().isoformat(),
            "result": result
        }
        
        return json.dumps(response, indent=2, ensure_ascii=False)
        
    except Exception as e:
        error_msg = f"Error: Failed to get quotas - {str(e)}"
        logger.error(error_msg)
        return json.dumps({
            "timestamp": datetime.now().isoformat(),
            "error": error_msg,
            "success": False
        }, indent=2)


# ===== LOAD BALANCER L7 RULE TOOLS =====

@mcp.tool()
async def get_load_balancer_l7_rules(policy_name_or_id: str) -> str:
    """
    Get L7 rules for a specific L7 policy.
    
    Args:
        policy_name_or_id: L7 policy name or ID (required)
    
    Returns:
        JSON string containing L7 rules information including rule types, values, and conditions
    """
    try:
        logger.info(f"Getting L7 rules for policy: {policy_name_or_id}")
        
        result = _get_load_balancer_l7_rules(policy_name_or_id)
        
        response = {
            "timestamp": datetime.now().isoformat(),
            "result": result
        }
        
        return json.dumps(response, indent=2, ensure_ascii=False)
        
    except Exception as e:
        error_msg = f"Error: Failed to get L7 rules - {str(e)}"
        logger.error(error_msg)
        return json.dumps({
            "timestamp": datetime.now().isoformat(),
            "error": error_msg,
            "success": False
        }, indent=2)


@conditional_tool
async def set_load_balancer_l7_rule(
    action: str,
    policy_name_or_id: str = "",
    rule_id: str = "",
    type: str = "PATH",
    compare_type: str = "STARTS_WITH",
    value: str = "",
    key: str = "",
    invert: bool = False,
    admin_state_up: bool = True
) -> str:
    """
    Manage L7 rule operations (create, delete, set, unset, show).
    
    Args:
        action: Action to perform (create, delete, set, unset, show)
        policy_name_or_id: L7 policy name or ID (required for create)
        rule_id: L7 rule ID (required for delete/update operations)
        type: Rule type (PATH, HOST_NAME, HEADER, COOKIE, FILE_TYPE, SSL_CONN_HAS_CERT, SSL_VERIFY_RESULT, SSL_DN_FIELD)
        compare_type: Comparison type (STARTS_WITH, ENDS_WITH, CONTAINS, EQUAL_TO, REGEX)
        value: Rule value to match against
        key: Key for HEADER/COOKIE types
        invert: Whether to invert the rule logic
        admin_state_up: Administrative state
    
    Returns:
        JSON string with operation results
    """
    try:
        logger.info(f"Managing L7 rule with action: {action}")
        
        kwargs = {
            'policy_name_or_id': policy_name_or_id,
            'rule_id': rule_id,
            'type': type,
            'compare_type': compare_type,
            'value': value,
            'key': key if key else None,
            'invert': invert,
            'admin_state_up': admin_state_up
        }
        
        result = _set_load_balancer_l7_rule(action, **kwargs)
        
        response = {
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "result": result
        }
        
        return json.dumps(response, indent=2, ensure_ascii=False)
        
    except Exception as e:
        error_msg = f"Error: Failed to manage L7 rule - {str(e)}"
        logger.error(error_msg)
        return json.dumps({
            "timestamp": datetime.now().isoformat(),
            "error": error_msg,
            "success": False
        }, indent=2)


# ===== ADVANCED LOADBALANCER MANAGEMENT TOOLS =====

@conditional_tool
async def set_load_balancer_availability_zone(
    action: str,
    az_name: str = "",
    name: str = "",
    availability_zone_profile_id: str = "",
    description: str = "",
    enabled: bool = True
) -> str:
    """
    Manage availability zone operations (create, delete, set, unset, show).
    
    Args:
        action: Action to perform (create, delete, set, unset, show)
        az_name: Availability zone name (required for delete/update)
        name: Name for new availability zone (required for create)
        availability_zone_profile_id: Profile ID (required for create)
        description: Description
        enabled: Whether the availability zone is enabled
    
    Returns:
        JSON string with operation results
    """
    try:
        logger.info(f"Managing availability zone with action: {action}")
        
        kwargs = {
            'az_name': az_name,
            'name': name,
            'availability_zone_profile_id': availability_zone_profile_id,
            'description': description,
            'enabled': enabled
        }
        
        result = _set_load_balancer_availability_zone(action, **kwargs)
        
        response = {
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "result": result
        }
        
        return json.dumps(response, indent=2, ensure_ascii=False)
        
    except Exception as e:
        error_msg = f"Error: Failed to manage availability zone - {str(e)}"
        logger.error(error_msg)
        return json.dumps({
            "timestamp": datetime.now().isoformat(),
            "error": error_msg,
            "success": False
        }, indent=2)


@conditional_tool
async def set_load_balancer_flavor(
    action: str,
    flavor_name_or_id: str = "",
    name: str = "",
    flavor_profile_id: str = "",
    description: str = "",
    enabled: bool = True
) -> str:
    """
    Manage flavor operations (create, delete, set, unset, show).
    
    Args:
        action: Action to perform (create, delete, set, unset, show)
        flavor_name_or_id: Flavor name or ID (required for delete/update)
        name: Name for new flavor (required for create)
        flavor_profile_id: Profile ID (required for create)
        description: Description
        enabled: Whether the flavor is enabled
    
    Returns:
        JSON string with operation results
    """
    try:
        logger.info(f"Managing flavor with action: {action}")
        
        kwargs = {
            'flavor_name_or_id': flavor_name_or_id,
            'name': name,
            'flavor_profile_id': flavor_profile_id,
            'description': description,
            'enabled': enabled
        }
        
        result = _set_load_balancer_flavor(action, **kwargs)
        
        response = {
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "result": result
        }
        
        return json.dumps(response, indent=2, ensure_ascii=False)
        
    except Exception as e:
        error_msg = f"Error: Failed to manage flavor - {str(e)}"
        logger.error(error_msg)
        return json.dumps({
            "timestamp": datetime.now().isoformat(),
            "error": error_msg,
            "success": False
        }, indent=2)


@conditional_tool
async def set_load_balancer_quota(
    action: str,
    project_id: str = "",
    load_balancer: int = -1,
    listener: int = -1,
    pool: int = -1,
    health_monitor: int = -1,
    member: int = -1
) -> str:
    """
    Manage quota operations (set, reset, unset).
    
    Args:
        action: Action to perform (set, reset, unset)
        project_id: Project ID (required)
        load_balancer: Load balancer quota limit
        listener: Listener quota limit
        pool: Pool quota limit
        health_monitor: Health monitor quota limit
        member: Member quota limit
    
    Returns:
        JSON string with operation results
    """
    try:
        logger.info(f"Managing quota with action: {action}")
        
        kwargs = {
            'project_id': project_id,
            'load_balancer': load_balancer if load_balancer >= 0 else None,
            'listener': listener if listener >= 0 else None,
            'pool': pool if pool >= 0 else None,
            'health_monitor': health_monitor if health_monitor >= 0 else None,
            'member': member if member >= 0 else None
        }
        
        # Remove None values
        kwargs = {k: v for k, v in kwargs.items() if v is not None}
        
        result = _set_load_balancer_quota(action, **kwargs)
        
        response = {
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "result": result
        }
        
        return json.dumps(response, indent=2, ensure_ascii=False)
        
    except Exception as e:
        error_msg = f"Error: Failed to manage quota - {str(e)}"
        logger.error(error_msg)
        return json.dumps({
            "timestamp": datetime.now().isoformat(),
            "error": error_msg,
            "success": False
        }, indent=2)


# ===== MCP SERVER STARTUP =====
