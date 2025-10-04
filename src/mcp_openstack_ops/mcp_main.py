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
from .functions import (
    get_instance_by_name as _get_instance_by_name,
    get_network_details as _get_network_details,
    get_volume_list as _get_volume_list,
    get_image_detail_list as _get_image_detail_list,
    get_keypair_list as _get_keypair_list,
)

import json
from datetime import datetime

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
    mcp = FastMCP("mcp-openstack-ops", auth=auth)
    logger.info("MCP instance initialized with authentication")
else:
    logger.info("Initializing MCP instance without authentication")
    mcp = FastMCP("mcp-openstack-ops")

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

from .tools import register_all_tools

# Register all MCP tool implementations
register_all_tools()

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
