import argparse
import logging
import os
import sys
from typing import Any, Optional, Dict, List
from fastmcp import FastMCP
from fastmcp.server.auth import StaticTokenVerifier

# Add the current directory to sys.path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from functions import (
    get_openstack_connection, 
    get_cluster_status as _get_cluster_status, 
    get_service_status as _get_service_status, 
    get_instance_details as _get_instance_details, 
    get_instance_by_name as _get_instance_by_name,
    get_instance_by_id as _get_instance_by_id,
    search_instances as _search_instances,
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
    set_subnets as _set_subnets,
    set_network_qos_policies as _set_network_qos_policies,
    set_network_agents as _set_network_agents,
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

@mcp.tool()
async def get_cluster_status() -> str:
    """
    Provides real-time cluster information by querying the overall status of OpenStack cluster.
    
    Functions: 
    - Query OpenStack cluster-wide instance list and status
    - Collect active network and subnet information  
    - Verify registered OpenStack service list
    - Validate cluster connection status and API responsiveness
    
    Use when user requests cluster overview, system status, infrastructure monitoring.
    
    Returns:
        Cluster status information in JSON format with instances, networks, services, and connection status.
    """
    try:
        logger.info("Fetching OpenStack cluster status")
        status = _get_cluster_status()
        
        result = {
            "timestamp": datetime.now().isoformat(),
            "cluster_status": status,
            "summary": {
                "total_instances": len(status.get('instances', [])),
                "total_networks": len(status.get('networks', [])),
                "total_services": len(status.get('services', []))
            }
        }
        
        return json.dumps(result, indent=2, ensure_ascii=False)
        
    except Exception as e:
        error_msg = f"Error: Failed to fetch OpenStack cluster status - {str(e)}"
        logger.error(error_msg)
        return error_msg


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
        if all_instances or (not names_list and not ids_list):
            details_result = _get_instance_details(
                limit=limit, 
                offset=offset, 
                include_all=include_all
            )
        else:
            details_result = _get_instance_details(
                instance_names=names_list, 
                instance_ids=ids_list,
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
            search_in=search_in,
            limit=limit,
            offset=offset,
            case_sensitive=case_sensitive
        )
        
        # Handle both old return format (list) and new return format (dict)
        if isinstance(search_result, dict):
            instances = search_result.get('instances', [])
            search_info = search_result.get('search_info', {})
            pagination_info = search_result.get('pagination', {})
            performance_info = search_result.get('performance', {})
        else:
            # Backward compatibility with old list return format
            instances = search_result
            search_info = {
                'search_term': search_term,
                'search_in': search_in,
                'case_sensitive': case_sensitive,
                'matches_found': len(instances)
            }
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
async def set_instance(instance_name: str, action: str) -> str:
    """
    Manages OpenStack instances with operations like start, stop, restart, pause, and unpause.
    
    Functions:
    - Start stopped instances
    - Stop running instances 
    - Restart/reboot instances (soft reboot)
    - Pause active instances (suspend to memory)
    - Unpause/resume paused instances
    
    Use when user requests instance management, VM control, server operations, or instance lifecycle management.
    
    Args:
        instance_name: Name of the instance to manage
        action: Management action (start, stop, restart, reboot, pause, unpause, resume)
        
    Returns:
        Management operation result in JSON format with success status, message, and state information.
    """
    try:
        if not instance_name or not instance_name.strip():
            return "Error: Instance name is required"
        if not action or not action.strip():
            return "Error: Action is required (start, stop, restart, pause, unpause)"
            
        logger.info(f"Managing instance '{instance_name}' with action '{action}'")
        result = _set_instance(instance_name.strip(), action.strip())
        
        response = {
            "timestamp": datetime.now().isoformat(),
            "requested_instance": instance_name,
            "requested_action": action,
            "management_result": result
        }
        
        return json.dumps(response, indent=2, ensure_ascii=False)
        
    except Exception as e:
        error_msg = f"Error: Failed to manage instance '{instance_name}' - {str(e)}"
        logger.error(error_msg)
        return error_msg


@conditional_tool
async def set_volume(volume_name: str, action: str, size: int = 1, instance_name: str = "", 
                   new_size: int = 0, source_volume: str = "", backup_name: str = "",
                   snapshot_name: str = "", transfer_name: str = "", host: str = "",
                   description: str = "", volume_type: str = "", availability_zone: str = "",
                   force: bool = False, incremental: bool = False, force_host_copy: bool = False,
                   lock_volume: bool = False) -> str:
    """
    Manages OpenStack volumes with comprehensive operations including advanced features.
    
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
    
    Use when user requests volume management, storage operations, disk management, backup operations, or volume lifecycle tasks.
    
    Args:
        volume_name: Name of the volume to manage
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
    """
    
    try:
        if not action or not action.strip():
            return "Error: Action is required (create, delete, list)"
            
        action = action.strip().lower()
        
        # Volume name is not required for 'list' action
        if action != 'list' and (not volume_name or not volume_name.strip()):
            return "Error: Volume name is required for this action"
            
        logger.info(f"Managing volume with action '{action}'" + (f" for volume '{volume_name}'" if volume_name and volume_name.strip() else ""))
        
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
        
        # For list action, use empty string if no volume_name provided
        volume_name_param = volume_name.strip() if volume_name and volume_name.strip() else ""
        result = _set_volume(volume_name_param, action, **kwargs)
        
        response = {
            "timestamp": datetime.now().isoformat(),
            "requested_volume": volume_name if volume_name else "all",
            "requested_action": action,
            "volume_result": result
        }
        
        return json.dumps(response, indent=2, ensure_ascii=False)
        
    except Exception as e:
        error_msg = f"Error: Failed to manage volume" + (f" '{volume_name}'" if volume_name and volume_name.strip() else "") + f" - {str(e)}"
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

    # 우선순위: 실행옵션 > 환경변수 > 기본값
    # Transport type 결정
    transport_type = args.transport_type or os.getenv("FASTMCP_TYPE", "stdio")
    
    # Host 결정
    host = args.host or os.getenv("FASTMCP_HOST", "127.0.0.1")
    
    # Port 결정 (간결하게)
    port = args.port or int(os.getenv("FASTMCP_PORT", 8080))
    
    # Authentication 설정 결정
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

    # Transport 모드에 따른 실행
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
async def set_keypair(keypair_name: str, action: str, public_key: str = "") -> str:
    """
    Manage SSH keypairs (create, delete, import).
    
    Functions:
    - Create new SSH keypairs with automatic key generation
    - Import existing public keys
    - Delete existing keypairs
    - Provide private key for created keypairs (secure handling required)
    
    Use when user requests keypair creation, deletion, or import operations.
    
    Args:
        keypair_name: Name of the keypair to manage
        action: Action to perform (create, delete, import)
        public_key: Public key content for import action (optional)
        
    Returns:
        Result of keypair management operation in JSON format.
    """
    try:
        logger.info(f"Managing keypair '{keypair_name}' with action '{action}'")
        
        kwargs = {}
        if public_key.strip():
            kwargs['public_key'] = public_key.strip()
            
        result_data = _set_keypair(keypair_name, action, **kwargs)
        
        result = {
            "timestamp": datetime.now().isoformat(),
            "keypair_name": keypair_name,
            "action": action,
            "result": result_data
        }
        
        return json.dumps(result, indent=2, ensure_ascii=False)
        
    except Exception as e:
        error_msg = f"Error: Failed to manage keypair - {str(e)}"
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
async def set_floating_ip(action: str, floating_network_id: str = "", port_id: str = "", floating_ip_id: str = "") -> str:
    """
    Manage floating IPs (create, delete, associate, disassociate).
    
    Functions:
    - Create new floating IPs from external networks
    - Delete existing floating IPs
    - Associate floating IPs with instance ports
    - Disassociate floating IPs from instances
    
    Use when user requests floating IP management, external connectivity setup, or IP allocation tasks.
    
    Args:
        action: Action to perform (create, delete, associate, disassociate)
        floating_network_id: ID of external network for create action (optional)
        port_id: Port ID for association operations (optional)
        floating_ip_id: Floating IP ID for delete/associate/disassociate actions (optional)
        
    Returns:
        Result of floating IP management operation in JSON format.
    """
    try:
        logger.info(f"Managing floating IP with action '{action}'")
        
        kwargs = {}
        if floating_network_id.strip():
            kwargs['floating_network_id'] = floating_network_id.strip()
        if port_id.strip():
            kwargs['port_id'] = port_id.strip()
        if floating_ip_id.strip():
            kwargs['floating_ip_id'] = floating_ip_id.strip()
            
        result_data = _set_floating_ip(action, **kwargs)
        
        result = {
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "parameters": kwargs,
            "result": result_data
        }
        
        return json.dumps(result, indent=2, ensure_ascii=False)
        
    except Exception as e:
        error_msg = f"Error: Failed to manage floating IP - {str(e)}"
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
async def set_snapshot(snapshot_name: str, action: str, volume_id: str = "", description: str = "") -> str:
    """
    Manage volume snapshots (create, delete).
    
    Functions:
    - Create snapshots from existing volumes
    - Delete existing snapshots
    - Provide snapshot creation with custom descriptions
    - Handle snapshot lifecycle management
    
    Use when user requests snapshot creation, deletion, or backup management tasks.
    
    Args:
        snapshot_name: Name of the snapshot to manage
        action: Action to perform (create, delete)
        volume_id: Volume ID for snapshot creation (optional)
        description: Description for the snapshot (optional)
        
    Returns:
        Result of snapshot management operation in JSON format.
    """
    
    try:
        logger.info(f"Managing snapshot '{snapshot_name}' with action '{action}'")
        
        kwargs = {}
        if volume_id.strip():
            kwargs['volume_id'] = volume_id.strip()
        if description.strip():
            kwargs['description'] = description.strip()
            
        result_data = _set_snapshot(snapshot_name, action, **kwargs)
        
        result = {
            "timestamp": datetime.now().isoformat(),
            "snapshot_name": snapshot_name,
            "action": action,
            "parameters": kwargs,
            "result": result_data
        }
        
        return json.dumps(result, indent=2, ensure_ascii=False)
        
    except Exception as e:
        error_msg = f"Error: Failed to manage snapshot - {str(e)}"
        logger.error(error_msg)
        return error_msg


# Image Service (Glance) Enhanced Tools
@conditional_tool
async def set_image(image_name: str, action: str, container_format: str = "bare", disk_format: str = "qcow2", visibility: str = "private") -> str:
    """
    Manage images (create, delete, update, list).
    
    Functions:
    - Create new images with specified formats and properties
    - Delete existing images
    - Update image metadata and visibility settings
    - List all available images in the project
    - Handle image lifecycle management
    
    Use when user requests image management, custom image creation, image listing, or image metadata updates.
    
    Args:
        image_name: Name of the image to manage
        action: Action to perform (create, delete, update, list)
        container_format: Container format (bare, ovf, etc.)
        disk_format: Disk format (qcow2, raw, vmdk, etc.)
        visibility: Image visibility (private, public, shared, community)
        
    Returns:
        Result of image management operation in JSON format.
    """
    
    try:
        # Image name is not required for 'list' action
        if action.lower() != 'list' and (not image_name or not image_name.strip()):
            return "Error: Image name is required for this action"
        
        logger.info(f"Managing image with action '{action}'" + (f" for image '{image_name}'" if image_name and image_name.strip() else ""))
        
        kwargs = {
            'container_format': container_format,
            'disk_format': disk_format,
            'visibility': visibility
        }
        
        # For list action, use empty string if no image_name provided
        image_name_param = image_name.strip() if image_name and image_name.strip() else ""
        result_data = _set_image(image_name_param, action, **kwargs)
        
        result = {
            "timestamp": datetime.now().isoformat(),
            "image_name": image_name if image_name else "all",
            "action": action,
            "parameters": kwargs,
            "result": result_data
        }
        
        return json.dumps(result, indent=2, ensure_ascii=False)
        
    except Exception as e:
        error_msg = f"Error: Failed to manage image - {str(e)}"
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
async def set_heat_stack(stack_name: str, action: str, template: str = "", parameters: str = "") -> str:
    """
    Manage Heat orchestration stacks (create, delete, update).
    
    Functions:
    - Create new stacks from Heat templates
    - Delete existing stacks
    - Update stack configurations and parameters
    - Handle complex infrastructure deployments
    
    Use when user requests Heat stack management, infrastructure orchestration, or template deployment tasks.
    
    Args:
        stack_name: Name of the stack to manage
        action: Action to perform (create, delete, update)
        template: Heat template content for create/update actions (optional)
        parameters: Stack parameters in JSON format (optional)
        
    Returns:
        Result of stack management operation in JSON format.
    """
    
    try:
        logger.info(f"Managing stack '{stack_name}' with action '{action}'")
        
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
            
        result_data = _set_heat_stack(stack_name, action, **kwargs)
        
        result = {
            "timestamp": datetime.now().isoformat(),
            "stack_name": stack_name,
            "action": action,
            "result": result_data
        }
        
        return json.dumps(result, indent=2, ensure_ascii=False)
        
    except Exception as e:
        error_msg = f"Error: Failed to manage stack - {str(e)}"
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
        
        response = {
            "timestamp": datetime.now().isoformat(),
            "operation": "set_quota",
            "parameters": {
                "project_name": project_name,
                "action": action,
                "quota_params": quota_params if quota_params else "none"
            },
            "result": quota_result
        }
        
        return json.dumps(response, indent=2, ensure_ascii=False)
        
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
        
        response = {
            "timestamp": datetime.now().isoformat(),
            "operation": "set_project",
            "parameters": {
                "project_name": project_name,
                "action": action,
                "project_params": project_params if project_params else "none"
            },
            "result": project_result
        }
        
        return json.dumps(response, indent=2, ensure_ascii=False)
        
    except Exception as e:
        error_msg = f"Error: Failed to manage project - {str(e)}"
        logger.error(error_msg)
        return error_msg


# =============================================================================
# Enhanced Server Management Tools
# =============================================================================

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
        
        response = {
            "timestamp": datetime.now().isoformat(),
            "operation": "set_server_group",
            "parameters": {
                "group_name": group_name,
                "action": action,
                "group_params": group_params if group_params else "none"
            },
            "result": group_result
        }
        
        return json.dumps(response, indent=2, ensure_ascii=False)
        
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
        
        response = {
            "timestamp": datetime.now().isoformat(),
            "operation": "set_flavor",
            "parameters": {
                "flavor_name": flavor_name,
                "action": action,
                "flavor_params": flavor_params if flavor_params else "none"
            },
            "result": flavor_result
        }
        
        return json.dumps(response, indent=2, ensure_ascii=False)
        
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
        
        response = {
            "timestamp": datetime.now().isoformat(),
            "operation": "set_server_volume",
            "parameters": {
                "instance_name": instance_name,
                "action": action,
                "volume_params": volume_params if volume_params else "none"
            },
            "result": volume_result
        }
        
        return json.dumps(response, indent=2, ensure_ascii=False)
        
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


@mcp.tool()
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


@mcp.tool()
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


@mcp.tool()
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


@mcp.tool()
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


@mcp.tool()
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


@mcp.tool()
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


@mcp.tool()
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


@mcp.tool()
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


@mcp.tool()
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


@mcp.tool()
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


@mcp.tool()
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


@mcp.tool()
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


@mcp.tool()
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


@mcp.tool()
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


@mcp.tool()
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


@mcp.tool()
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


@mcp.tool()
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


@mcp.tool()
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
