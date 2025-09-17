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
    manage_instance as _manage_instance,
    manage_volume as _manage_volume,
    monitor_resources as _monitor_resources,
    get_project_info as _get_project_info,
    get_flavor_list as _get_flavor_list,
    get_image_list as _get_image_list,
    reset_connection_cache,
    # Identity (Keystone) functions
    get_user_list as _get_user_list,
    get_role_assignments as _get_role_assignments,
    # Compute (Nova) enhanced functions
    get_keypair_list as _get_keypair_list,
    manage_keypair as _manage_keypair,
    get_security_groups as _get_security_groups,
    # Network (Neutron) enhanced functions
    get_floating_ips as _get_floating_ips,
    manage_floating_ip as _manage_floating_ip,
    get_routers as _get_routers,
    # Block Storage (Cinder) enhanced functions
    get_volume_types as _get_volume_types,
    get_volume_snapshots as _get_volume_snapshots,
    manage_snapshot as _manage_snapshot,
    # Image Service (Glance) enhanced functions
    manage_image as _manage_image,
    # Orchestration (Heat) functions
    get_stacks as _get_stacks,
    manage_stack as _manage_stack
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


@mcp.tool()
async def manage_instance(instance_name: str, action: str) -> str:
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
        result = _manage_instance(instance_name.strip(), action.strip())
        
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


@mcp.tool()
async def manage_volume(volume_name: str, action: str, size: int = 1, instance_name: str = "") -> str:
    """
    Manages OpenStack volumes with operations like create, delete, list, and attach.
    
    Functions:
    - Create new volumes with specified size
    - Delete existing volumes
    - List all volumes with status information
    - Attach volumes to instances (when supported)
    
    Use when user requests volume management, storage operations, disk management, or volume lifecycle tasks.
    
    Args:
        volume_name: Name of the volume to manage
        action: Management action (create, delete, list)  
        size: Volume size in GB (default: 1, used for create action)
        instance_name: Instance name for attach operations (optional)
        
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
        
        # Prepare kwargs for manage_volume function
        kwargs = {'size': size}
        if instance_name:
            kwargs['instance_name'] = instance_name.strip()
        
        # For list action, use empty string if no volume_name provided
        volume_name_param = volume_name.strip() if volume_name and volume_name.strip() else ""
        result = _manage_volume(volume_name_param, action, **kwargs)
        
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
async def monitor_resources() -> str:
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
        monitoring_data = _monitor_resources()
        
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


@mcp.tool()
async def manage_keypair(keypair_name: str, action: str, public_key: str = "") -> str:
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
            
        result_data = _manage_keypair(keypair_name, action, **kwargs)
        
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


@mcp.tool()
async def manage_floating_ip(action: str, floating_network_id: str = "", port_id: str = "", floating_ip_id: str = "") -> str:
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
            
        result_data = _manage_floating_ip(action, **kwargs)
        
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


@mcp.tool()
async def manage_snapshot(snapshot_name: str, action: str, volume_id: str = "", description: str = "") -> str:
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
        volume_id: Source volume ID for create action (optional)
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
            
        result_data = _manage_snapshot(snapshot_name, action, **kwargs)
        
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
@mcp.tool()
async def manage_image(image_name: str, action: str, container_format: str = "bare", disk_format: str = "qcow2", visibility: str = "private") -> str:
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
        image_name: Name or ID of the image to manage (not required for 'list' action)
        action: Action to perform (create, delete, update, list)
        container_format: Container format for create action (default: bare)
        disk_format: Disk format for create action (default: qcow2)
        visibility: Image visibility for create action (default: private)
        
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
        result_data = _manage_image(image_name_param, action, **kwargs)
        
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


# Orchestration (Heat) Tools
@mcp.tool()
async def get_stacks() -> str:
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
        stacks = _get_stacks()
        
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


@mcp.tool()
async def manage_stack(stack_name: str, action: str, template: str = "", parameters: str = "") -> str:
    """
    Manage Heat orchestration stacks (create, delete, update).
    
    Functions:
    - Create new stacks from Heat templates
    - Delete existing stacks and their resources
    - Update stack configurations with new templates
    - Handle infrastructure-as-code deployments
    
    Use when user requests stack deployment, infrastructure automation, or orchestration management.
    
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
            
        result_data = _manage_stack(stack_name, action, **kwargs)
        
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
