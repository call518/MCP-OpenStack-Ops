# MCP-OpenStack-Ops

> **MCP OpenStack Operations Server**: A comprehensive MCP (Model Context Protocol) server providing OpenStack cluster management and monitoring capabilities. This server enables AI assistants to interact with OpenStack infrastructure through standardized tools for real-time monitoring, resource management, and operational tasks.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Deploy to PyPI with tag](https://github.com/call518/MCP-OpenStack-Ops/actions/workflows/pypi-publish.yml/badge.svg)](https://github.com/call518/MCP-OpenStack-Ops/actions/workflows/pypi-publish.yml)
[![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/call518/MCP-OpenStack-Ops)
[![BuyMeACoffee](https://raw.githubusercontent.com/pachadotdev/buymeacoffee-badges/main/bmc-donate-yellow.svg)](https://www.buymeacoffee.com/call518)

## Features

- ✅ **OpenStack Integration**: Direct integration with OpenStack SDK for real-time cluster operations
- ✅ **Comprehensive Monitoring**: Cluster status, service monitoring, resource utilization tracking
- ✅ **Instance Management**: Start, stop, restart, pause/unpause OpenStack instances
- ✅ **Volume Operations**: Create, delete, list, and manage OpenStack volumes
- ✅ **Network Analysis**: Detailed network, subnet, router, and security group information
- ✅ **Flexible Transport**: Support for both `stdio` and `streamable-http` transports
- ✅ **Comprehensive Logging**: Configurable logging levels with structured output  
- ✅ **Environment Configuration**: Support for environment variables and CLI arguments
- ✅ **Error Handling**: Robust error handling and configuration validation
- ✅ **Docker Support**: Containerized deployment with Docker Compose

## MCP Tools Available

### 🔍 Monitoring Tools
1. **`get_openstack_cluster_status`** - Overall cluster status with instances, networks, and services
2. **`get_openstack_service_status`** - OpenStack service health and API endpoint status
3. **`get_openstack_instance_details`** - Detailed information for specific instances
4. **`monitor_openstack_resources`** - Real-time resource usage and capacity monitoring

### 🌐 Network Tools  
5. **`get_openstack_network_details`** - Network, subnet, router, and security group details

### ⚙️ Management Tools
6. **`manage_openstack_instance`** - Instance lifecycle operations (start/stop/restart/pause/unpause)
7. **`manage_openstack_volume`** - Volume management operations (create/delete/list)

## Quick Start

### 1. Environment Setup

```bash
# Clone and navigate to project
cd MCP-OpenStack-Ops

# Install dependencies
uv sync

# Configure environment
cp .env.example .env
# Edit .env with your OpenStack credentials
```

### 2. OpenStack Configuration

Configure your `.env` file with OpenStack credentials:

```bash
# OpenStack Authentication
OS_AUTH_URL=https://your-openstack:5000/v3
OS_IDENTITY_API_VERSION=3
OS_USERNAME=your-username
OS_PASSWORD=your-password
OS_PROJECT_NAME=your-project
OS_PROJECT_DOMAIN_NAME=default
OS_USER_DOMAIN_NAME=default
OS_REGION_NAME=RegionOne

# MCP Server Configuration (optional)
MCP_LOG_LEVEL=INFO
FASTMCP_TYPE=stdio
FASTMCP_HOST=127.0.0.1
FASTMCP_PORT=8080
```

### 3. Run Server

#### For Development & Testing
```bash
# Local testing with MCP Inspector
./scripts/run-mcp-inspector-local.sh

# Direct execution for debugging
uv run python -m mcp_openstack_ops --log-level DEBUG
```

#### For Production (Docker)
```bash
# Build and run with Docker Compose
docker-compose up -d

# Check logs
docker-compose logs -f mcp-server
```

#### For Claude Desktop Integration
Add to your Claude Desktop configuration:
```json
{
  "mcpServers": {
    "openstack-ops": {
      "command": "uv",
      "args": ["run", "python", "-m", "mcp_openstack_ops"],
      "cwd": "/path/to/MCP-OpenStack-Ops"
    }
  }
}
```

## Server Configuration

### Command Line Options

```bash
uv run python -m mcp_openstack_ops --help

Options:
  --log-level {DEBUG,INFO,WARNING,ERROR,CRITICAL}
                        Logging level
  --type {stdio,streamable-http}
                        Transport type (default: stdio)
  --host HOST          Host address for HTTP transport (default: 127.0.0.1)
  --port PORT          Port number for HTTP transport (default: 8080)
  --auth-enable        Enable Bearer token authentication for streamable-http mode
  --secret-key SECRET  Secret key for Bearer token authentication
```

### Environment Variables

| Variable | Description | Default | Usage |
|----------|-------------|---------|--------|
| **OpenStack Authentication** |
| `OS_AUTH_URL` | OpenStack Identity service URL | Required | Authentication endpoint |
| `OS_USERNAME` | OpenStack username | Required | User credentials |
| `OS_PASSWORD` | OpenStack password | Required | User credentials |
| `OS_PROJECT_NAME` | OpenStack project name | Required | Project scope |
| `OS_IDENTITY_API_VERSION` | Identity API version | `3` | API version |
| `OS_PROJECT_DOMAIN_NAME` | Project domain name | `default` | Domain scope |
| `OS_USER_DOMAIN_NAME` | User domain name | `default` | Domain scope |
| `OS_REGION_NAME` | OpenStack region | `RegionOne` | Regional scope |
| **MCP Server Configuration** |
| `MCP_LOG_LEVEL` | Logging level | `INFO` | Development debugging |
| `FASTMCP_TYPE` | Transport type | `stdio` | Rarely needed to change |
| `FASTMCP_HOST` | HTTP host address | `127.0.0.1` | For HTTP mode only |
| `FASTMCP_PORT` | HTTP port number | `8080` | For HTTP mode only |
| **Authentication (Optional)** |
| `REMOTE_AUTH_ENABLE` | Enable Bearer token authentication for streamable-http mode | `false` | Production security |
| `REMOTE_SECRET_KEY` | Secret key for Bearer token authentication | Required when auth enabled | Production security |

**Note**: MCP servers typically use `stdio` transport. HTTP mode is mainly for testing and development.

## Project Structure

```
.
├── main.py                         # Main entry point
├── MANIFEST.in                     # Package manifest
├── pyproject.toml                  # Project configuration
├── README.md                       # This file
├── uv.lock                         # Dependency lock file
├── .env.example                    # Environment configuration template
├── Dockerfile.MCP-Server           # Docker container configuration
├── docker-compose.yml              # Docker Compose setup
├── docs/                           # Documentation
├── scripts/
│   ├── mcp-server-docker-cmd.sh    # Docker container startup script
│   ├── run-mcp-inspector-local.sh  # Development & testing
│   └── run-mcp-inspector-pypi.sh   # Test published package
└── src/
    └── mcp_openstack_ops/
        ├── __init__.py
        ├── __main__.py             # Module execution entry point
        ├── functions.py            # OpenStack utility functions
        ├── mcp_main.py             # FastMCP server implementation
        └── prompt_template.md      # AI assistant prompt template
```

## Tool Usage Examples

### 🔍 Monitoring Examples

```bash
# Get overall cluster status
→ "Show me the OpenStack cluster status"
→ Calls: get_openstack_cluster_status()

# Check service health
→ "Are all OpenStack services running properly?"
→ Calls: get_openstack_service_status()

# Monitor resource usage
→ "What's the current resource utilization?"
→ Calls: monitor_openstack_resources()

# Get instance details
→ "Show details for instance web-server-01"
→ Calls: get_openstack_instance_details("web-server-01")
```

### 🌐 Network Examples

```bash
# Check all networks
→ "Show me all network configurations"
→ Calls: get_openstack_network_details("all")

# Specific network details
→ "Get details for the internal network"
→ Calls: get_openstack_network_details("internal")
```

### ⚙️ Management Examples

```bash
# Instance management
→ "Start the web-server-01 instance"
→ Calls: manage_openstack_instance("web-server-01", "start")

→ "Restart the database server"
→ Calls: manage_openstack_instance("db-server", "restart")

# Volume management
→ "Create a 100GB volume named backup-vol"
→ Calls: manage_openstack_volume("backup-vol", "create", 100)

→ "List all volumes"
→ Calls: manage_openstack_volume("", "list")
```

## Development

### Adding New Tools

Edit `src/mcp_openstack_ops/mcp_main.py` to add new MCP tools:

```python
@mcp.tool()
async def my_openstack_tool(param: str) -> str:
    """
    Brief description of the tool's purpose.
    
    Functions:
    - List specific functions this tool performs
    - Describe the operations it enables
    - Mention when to use this tool
    
    Use when user requests [specific scenarios].
    
    Args:
        param: Description of the parameter
        
    Returns:
        Description of return value format.
    """
    try:
        logger.info(f"Tool called with param: {param}")
        # Implementation using functions.py helpers
        result = my_helper_function(param)
        
        response = {
            "timestamp": datetime.now().isoformat(),
            "result": result
        }
        
        return json.dumps(response, indent=2, ensure_ascii=False)
        
    except Exception as e:
        error_msg = f"Error: Failed to execute tool - {str(e)}"
        logger.error(error_msg)
        return error_msg
```

### Helper Functions

Add utility functions to `src/mcp_openstack_ops/functions.py`:

```python
def my_helper_function(param: str) -> dict:
    """Helper function for OpenStack operations"""
    try:
        conn = get_openstack_connection()
        
        # OpenStack SDK operations
        result = conn.some_service.some_operation(param)
        
        logger.info(f"Operation completed successfully")
        return {"success": True, "data": result}
        
    except Exception as e:
        logger.error(f"Helper function error: {e}")
        raise
```

## Testing & Validation

### Local Testing
```bash
# Test with MCP Inspector (recommended)
./scripts/run-mcp-inspector-local.sh

# Test with debug logging
MCP_LOG_LEVEL=DEBUG uv run python -m mcp_openstack_ops

# Validate OpenStack connection
uv run python -c "from src.mcp_openstack_ops.functions import get_openstack_connection; print(get_openstack_connection())"
```

### Docker Testing
```bash
# Build and test in container
docker-compose build
docker-compose up -d

# Check container logs
docker-compose logs -f mcp-server

# Test HTTP endpoint (if using HTTP transport)
curl -X POST http://localhost:18005/mcp \
  -H "Content-Type: application/json" \
  -d '{"method": "tools/list"}'
```

## 🔐 Security & Authentication

### Bearer Token Authentication

For `streamable-http` mode, this MCP server supports Bearer token authentication to secure remote access. This is especially important when running the server in production environments.

#### Configuration

**Enable Authentication:**

```bash
# In .env file
REMOTE_AUTH_ENABLE=true
REMOTE_SECRET_KEY=your-secure-secret-key-here
```

**Or via CLI:**

```bash
uv run python -m mcp_openstack_ops --type streamable-http --auth-enable --secret-key your-secure-secret-key-here
```

#### Security Levels

1. **stdio mode** (Default): Local-only access, no authentication needed
2. **streamable-http + REMOTE_AUTH_ENABLE=false/undefined**: Remote access without authentication ⚠️ **NOT RECOMMENDED for production**
3. **streamable-http + REMOTE_AUTH_ENABLE=true**: Remote access with Bearer token authentication ✅ **RECOMMENDED for production**

> **🔒 Default Policy**: `REMOTE_AUTH_ENABLE` defaults to `false` if undefined, empty, or null. This ensures the server starts even without explicit authentication configuration.

#### Client Configuration

When authentication is enabled, MCP clients must include the Bearer token in the Authorization header:

```json
{
  "mcpServers": {
    "openstack-ops": {
      "type": "streamable-http",
      "url": "http://your-server:8080/mcp",
      "headers": {
        "Authorization": "Bearer your-secure-secret-key-here"
      }
    }
  }
}
```

#### Security Best Practices

- **Always enable authentication** when using streamable-http mode in production
- **Use strong, randomly generated secret keys** (32+ characters recommended)
- **Use HTTPS** when possible (configure reverse proxy with SSL/TLS)
- **Restrict network access** using firewalls or network policies
- **Rotate secret keys regularly** for enhanced security
- **Monitor access logs** for unauthorized access attempts

#### Error Handling

When authentication fails, the server returns:
- **401 Unauthorized** for missing or invalid tokens
- **Detailed error messages** in JSON format for debugging

---

## Deployment

### Local Development
```bash
# Test with MCP Inspector (recommended)
./scripts/run-mcp-inspector-local.sh

# Test with debug logging
MCP_LOG_LEVEL=DEBUG uv run python -m mcp_openstack_ops

# Validate OpenStack connection
uv run python -c "from src.mcp_openstack_ops.functions import get_openstack_connection; print(get_openstack_connection())"
```

### Docker Testing
```bash
# Build and test in container
docker-compose build
docker-compose up -d

# Check container logs
docker-compose logs -f mcp-server

# Test HTTP endpoint (if using HTTP transport)
curl -X POST http://localhost:18005/mcp \
  -H "Content-Type: application/json" \
  -d '{"method": "tools/list"}'

### Claude Desktop Integration
Add to your Claude Desktop configuration (`claude_desktop_config.json`):

#### Method 1: Local MCP (transport="stdio")

```json
{
  "mcpServers": {
    "openstack-ops": {
      "command": "uv",
      "args": ["run", "python", "-m", "mcp_openstack_ops"],
      "cwd": "/path/to/MCP-OpenStack-Ops",
      "env": {
        "OS_AUTH_URL": "https://your-openstack:5000/v3",
        "OS_USERNAME": "your-username",
        "OS_PASSWORD": "your-password",
        "OS_PROJECT_NAME": "your-project",
        "MCP_LOG_LEVEL": "INFO"
      }
    }
  }
}
```

#### Method 2: Remote MCP (transport="streamable-http")

**Without Authentication:**
```json
{
  "mcpServers": {
    "openstack-ops": {
      "type": "streamable-http",
      "url": "http://localhost:18005/mcp"
    }
  }
}
```

**With Bearer Token Authentication (Recommended for production):**
```json
{
  "mcpServers": {
    "openstack-ops": {
      "type": "streamable-http", 
      "url": "http://localhost:18005/mcp",
      "headers": {
        "Authorization": "Bearer your-secure-secret-key-here"
      }
    }
  }
}
```

### Production Deployment
```bash
# Using Docker Compose (recommended)
docker-compose up -d

# Manual Docker run
docker build -f Dockerfile.MCP-Server -t mcp-openstack-ops .
docker run -d --name mcp-openstack-ops \
  --env-file .env \
  -p 18005:8000 \
  mcp-openstack-ops
```

## Troubleshooting

### Common Issues

1. **Authentication Errors**
   - Verify OpenStack credentials in `.env`
   - Check network connectivity to OpenStack API endpoints
   - Validate user permissions and project access

2. **Tool Execution Failures**
   - Review logs with `MCP_LOG_LEVEL=DEBUG`
   - Ensure OpenStack services are accessible
   - Verify instance/volume/network names exist

3. **Transport Issues**
   - Use `stdio` for Claude Desktop integration
   - Use `streamable-http` for testing and development
   - Check port availability for HTTP transport

4. **Authentication Issues (streamable-http mode)**
   - Verify `REMOTE_SECRET_KEY` matches between server and client
   - Ensure Bearer token is included in client Authorization header
   - Check server logs for authentication error details
   - Confirm `REMOTE_AUTH_ENABLE=true` is set when using authentication

### Getting Help

- Check logs for detailed error messages
- Validate OpenStack connectivity independently
- Test individual tools with MCP Inspector
- Review OpenStack SDK documentation for API requirements

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### HTTP Mode (Advanced)
For special testing scenarios only:

```bash
# Run HTTP server for testing
python -m src.mcp_openstack_ops.mcp_main \
  --type streamable-http \
  --host 127.0.0.1 \
  --port 8080 \
  --log-level DEBUG
```

### Testing & Development

```bash
# Test with MCP Inspector
./scripts/run-mcp-inspector-local.sh

# Direct execution for debugging
python -m src.mcp_openstack_ops.mcp_main --log-level DEBUG

# Run tests (if you add any)
uv run pytest
```

## Logging

The server provides structured logging with configurable levels:

```
2024-08-19 10:30:15 - mcp_main - INFO - Starting MCP server with stdio transport
2024-08-19 10:30:15 - mcp_main - INFO - Log level set via CLI to INFO
2024-08-19 10:30:16 - functions - DEBUG - Fetching data from source: example.com
```

## Notes

- The script replaces mcp_openstack_ops (underscore), mcp-openstack-ops (hyphen), and mcp-openstack-ops (display name)
- Configuration validation ensures proper setup before server start
- If you need to rename again, revert changes or re-clone and re-run
- A backup `pyproject.toml.bak` is created when overwriting pyproject
