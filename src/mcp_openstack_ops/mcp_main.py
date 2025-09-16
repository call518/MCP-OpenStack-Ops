import argparse
import logging
import os
import sys
from typing import Any, Optional, Dict, List
from mcp.server.fastmcp import FastMCP

# Add the current directory to sys.path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from functions import (
    get_openstack_connection, 
    get_cluster_status, 
    get_service_status, 
    get_instance_details, 
    get_network_details,
    manage_instance,
    manage_volume,
    monitor_resources
)

import json
from datetime import datetime
from openstack import connection

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# OpenStack Operations MCP Server
mcp = FastMCP("openstack-ops")

# =============================================================================
# MCP Tools (OpenStack Operations and Monitoring)
# =============================================================================

@mcp.tool()
async def get_openstack_cluster_status() -> str:
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
        status = get_cluster_status()
        
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
async def get_openstack_service_status() -> str:
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
        services = get_service_status()
        
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
async def get_openstack_instance_details(instance_name: str) -> str:
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
        details = get_instance_details(instance_name.strip())
        
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
async def get_openstack_network_details(network_name: str = "all") -> str:
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
        details = get_network_details(network_name)
        
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
async def manage_openstack_instance(instance_name: str, action: str) -> str:
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
        result = manage_instance(instance_name.strip(), action.strip())
        
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
async def manage_openstack_volume(volume_name: str, action: str, size: int = 1, instance_name: str = "") -> str:
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
            
        result = manage_volume(volume_name.strip(), action.strip(), **kwargs)
        
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
async def monitor_openstack_resources() -> str:
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
        monitoring_data = monitor_resources()
        
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
    parser = argparse.ArgumentParser(
        prog="mcp-server",
        description="MCP Server with configurable transport",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        "--log-level",
        dest="log_level",
        help="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL). Overrides env var if provided.",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
    )
    parser.add_argument(
        "--type",
        dest="transport_type",
        help="Transport type. Default: stdio",
        choices=["stdio", "streamable-http"],
        default="stdio"
    )
    parser.add_argument(
        "--host",
        dest="host",
        help="Host address for streamable-http transport. Default: 127.0.0.1",
        default="127.0.0.1"
    )
    parser.add_argument(
        "--port",
        dest="port",
        type=int,
        help="Port number for streamable-http transport. Default: 8080",
        default=8080
    )
    
    try:
        args = parser.parse_args(argv)
        
        # Determine log level: CLI arg > environment variable > default
        log_level = args.log_level or os.getenv("MCP_LOG_LEVEL", "INFO")
        
        # Set logging level
        numeric_level = getattr(logging, log_level.upper(), None)
        if not isinstance(numeric_level, int):
            raise ValueError(f'Invalid log level: {log_level}')
        
        logger.setLevel(numeric_level)
        logging.getLogger().setLevel(numeric_level)
        
        # Reduce noise from external libraries at DEBUG level
        logging.getLogger("aiohttp.client").setLevel(logging.WARNING)
        logging.getLogger("asyncio").setLevel(logging.WARNING)
        
        if args.log_level:
            logger.info("Log level set via CLI to %s", args.log_level)
        elif os.getenv("MCP_LOG_LEVEL"):
            logger.info("Log level set via environment variable to %s", log_level)
        else:
            logger.info("Using default log level: %s", log_level)

        # Priority: CLI args > environment variables > defaults
        transport_type = args.transport_type or os.getenv("FASTMCP_TYPE", "stdio")
        host = args.host or os.getenv("FASTMCP_HOST", "127.0.0.1") 
        port = args.port if args.port != 8080 else int(os.getenv("FASTMCP_PORT", "8080"))
        
        # Validate configuration
        validate_config(transport_type, host, port)
        
        # Run based on transport mode
        if transport_type == "streamable-http":
            logger.info(f"Starting MCP server with streamable-http transport on {host}:{port}")
            mcp.run(transport="streamable-http", host=host, port=port)
        else:
            logger.info("Starting MCP server with stdio transport")
            mcp.run(transport='stdio')
            
    except KeyboardInterrupt:
        logger.info("Server shutdown requested by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Failed to start server: {e}")
        sys.exit(1)


if __name__ == "__main__":
    """Entrypoint for MCP server.

    Supports optional CLI arguments while remaining backward-compatible 
    with stdio launcher expectations.
    """
    main()
