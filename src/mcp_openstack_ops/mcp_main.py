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
    get_network_details as _get_network_details,
    manage_instance as _manage_instance,
    manage_volume as _manage_volume,
    monitor_resources as _monitor_resources
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
        
        result = {
            "timestamp": datetime.now().isoformat(),
            "service_status": services,
            "summary": {
                "total_services": len(services.get('services', [])) if isinstance(services, dict) else 0,
                "status_check": services.get('status_check', 'unknown')
            }
        }
        
        return json.dumps(result, indent=2, ensure_ascii=False)
        
    except Exception as e:
        error_msg = f"Error: Failed to fetch OpenStack service status - {str(e)}"
        logger.error(error_msg)
        return error_msg


@mcp.tool()
async def get_instance_details(instance_name: str) -> str:
    """
    Provides detailed information and status for a specific OpenStack instance.
    
    Functions:
    - Query basic instance information (name, ID, status, image, flavor)
    - Collect network connection status and IP address information
    - Check CPU, memory, storage resource usage and allocation
    - Provide instance metadata, keypair, and security group settings
    
    Use when user requests specific instance information, VM details, server analysis, or instance troubleshooting.
    
    Args:
        instance_name: Name of the instance to query
        
    Returns:
        Instance detailed information in JSON format with instance, network, and resource data.
    """
    try:
        if not instance_name or not instance_name.strip():
            return "Error: Instance name is required"
            
        logger.info(f"Fetching details for instance: {instance_name}")
        details = _get_instance_details(instance_name.strip())
        
        result = {
            "timestamp": datetime.now().isoformat(),
            "requested_instance": instance_name,
            "instance_details": details
        }
        
        return json.dumps(result, indent=2, ensure_ascii=False)
        
    except Exception as e:
        error_msg = f"Error: Failed to fetch instance '{instance_name}' details - {str(e)}"
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
        if not volume_name or not volume_name.strip():
            return "Error: Volume name is required"
        if not action or not action.strip():
            return "Error: Action is required (create, delete, list)"
            
        logger.info(f"Managing volume '{volume_name}' with action '{action}'")
        
        # Prepare kwargs for manage_volume function
        kwargs = {'size': size}
        if instance_name:
            kwargs['instance_name'] = instance_name.strip()
            
        result = _manage_volume(volume_name.strip(), action.strip(), **kwargs)
        
        response = {
            "timestamp": datetime.now().isoformat(),
            "requested_volume": volume_name,
            "requested_action": action,
            "volume_result": result
        }
        
        return json.dumps(response, indent=2, ensure_ascii=False)
        
    except Exception as e:
        error_msg = f"Error: Failed to manage volume '{volume_name}' - {str(e)}"
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
