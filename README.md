# MCP-OpenStack-Ops

> **MCP OpenStack Operations Server**: A comprehensive MCP (Model Context Protocol) server providing OpenStack cluster management and monitoring capabilities. Optimized for **OpenStack Epoxy (2025.1)** with SDK version 4.1.0-4.4.0.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Deploy to PyPI with tag](https://github.com/call518/MCP-OpenStack-Ops/actions/workflows/pypi-publish.yml/badge.svg)](https://github.com/call518/MCP-OpenStack-Ops/actions/workflows/pypi-publish.yml)
[![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/call518/MCP-OpenStack-Ops)
[![BuyMeACoffee](https://raw.githubusercontent.com/pachadotdev/buymeacoffee-badges/main/bmc-donate-yellow.svg)](https://www.buymeacoffee.com/call518)

---

> **🎯 Target Environment**: This MCP server is specifically designed and tested for **OpenStack Epoxy (2025.1)** using OpenStack SDK 4.1.0-4.4.0. For optimal compatibility and performance, ensure your OpenStack environment is running Epoxy release.

## Features

- ✅ **OpenStack Epoxy Integration**: Direct integration with OpenStack SDK 4.1.0-4.4.0 for real-time cluster operations.
- ✅ **Comprehensive Monitoring**: Enhanced cluster status reports with hypervisor health, resource utilization, and health scoring.
- ✅ **Complete Service Coverage**: 24 comprehensive tools covering Identity, Compute, Network, Storage, Image, and Orchestration services.
- ✅ **Advanced Instance Management**: Start, stop, restart, pause/unpause OpenStack instances with pagination support.
- ✅ **Large-Scale Environment Support**: Pagination and limits for environments with thousands of instances.
- ✅ **Enterprise Features**: User management, role assignments, keypair management, floating IP operations, volume snapshots.
- ✅ **Intelligent Search**: Flexible instance search with partial matching and case-sensitive options.
- ✅ **Network & Volume Operations**: Comprehensive network analysis and volume management capabilities.
- ✅ **Connection Optimization**: Global connection caching and automatic retry mechanisms.
- ✅ **Docker Support**: Containerized deployment optimized for OpenStack Epoxy environments.
- ✅ **Flexible Transport**: Support for both `stdio` and `streamable-http` transports with comprehensive logging.

> ⚠️ **Compatibility Notice**: This MCP server is developed and optimized for **OpenStack Epoxy (2025.1)** as the primary target environment. However, it is compatible with most modern OpenStack releases (Dalmatian, Caracal, Bobcat, etc.) as the majority of APIs remain consistent across versions. Only a few specific API endpoints may require adaptation for full compatibility with older releases.
> 
> 🚧 **Coming Soon**: Dynamic multi-version OpenStack API compatibility is actively under development and will be available in upcoming releases, providing seamless support for all major OpenStack deployments automatically.

---

## MCP Tools Available

### 🔍 Monitoring & Status Tools
1. **`get_cluster_status`** - **Enhanced comprehensive cluster analysis**
   - Compute nodes: hypervisor status, resource utilization (CPU/memory/disk)
   - Instance analysis: status distribution, availability zones, detailed info
   - Network resources: external networks, floating IPs, routers, security groups
   - Storage resources: volumes by status, snapshots, volume types
   - Service status: service health, compute services monitoring
   - **Health scoring**: overall cluster health with issue detection
2. **`get_service_status`** - OpenStack service health and API endpoint status
3. **`get_instance_details`** - Detailed information for specific instances with pagination support
   - Supports filtering by instance names or IDs
   - Pagination parameters: `limit` (default 50, max 200), `offset` (default 0)
   - Performance metrics and processing time tracking
4. **`search_instances`** - Advanced instance search with flexible criteria
   - Search fields: name, status, host, flavor, image, availability_zone, all
   - Partial string matching with case-sensitive options
   - Optimized 2-phase search for large environments
5. **`get_instance_by_name`** - Quick lookup for specific instance by name
6. **`get_instances_by_status`** - Filter instances by operational status
7. **`monitor_resources`** - Real-time resource usage and capacity monitoring

### 🌐 Network Management Tools  
8. **`get_network_details`** - Network, subnet, router, and security group details
9. **`get_floating_ips`** - Floating IP allocation and status information
10. **`manage_floating_ip`** - Create, delete, associate/disassociate floating IPs
11. **`get_routers`** - Router status and configuration details
12. **`get_security_groups`** - Security group rules and configuration

### 💾 Storage Management Tools
13. **`manage_volume`** - Volume management operations (create/delete/list/extend)
14. **`get_volume_types`** - Available volume types and specifications
15. **`get_volume_snapshots`** - Volume snapshot status and management
16. **`manage_snapshot`** - Create, delete, and manage volume snapshots

### ⚙️ Instance & Compute Management
17. **`manage_instance`** - Instance lifecycle operations (start/stop/restart/pause/unpause)
18. **`get_keypair_list`** - SSH keypair management and listing
19. **`manage_keypair`** - Create, delete SSH keypairs for instance access

### 👥 Identity & Access Management
20. **`get_user_list`** - OpenStack user accounts and details
21. **`get_role_assignments`** - User role assignments and permissions

### 🖼️ Image Management
22. **`manage_image`** - Create, delete, list, and manage OpenStack images

### 🔥 Orchestration (Heat) Tools
23. **`get_stacks`** - Heat stack status and information
24. **`manage_stack`** - Create, delete, and manage Heat orchestration stacks

---

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

### 2. OpenStack Requirements

**Supported OpenStack Version**: **Epoxy (2025.1)**

**Required OpenStack SDK Version**: `4.1.0 - 4.4.0`

```bash
# Install the correct SDK version (automatically handled by uv sync)
uv add "openstacksdk>=4.1.0,<=4.4.0"
```

**How to verify your OpenStack version:**
```bash
# Method 1: Check with OpenStack CLI (if installed)
openstack --version

# Method 2: Check API version directly
curl -s http://$OS_AUTH_HOST:$OS_AUTH_PORT

# Method 3: Check Horizon dashboard footer
# Look for version info at the bottom of your OpenStack web dashboard

# Method 4: Check deployment documentation
# Most reliable method - consult your cloud provider's documentation
```

**Environment Configuration**

Configure your `.env` file with OpenStack credentials:

```bash
# OpenStack Authentication (required)
OS_AUTH_HOST=your-openstack-host
OS_AUTH_PORT=5000
OS_IDENTITY_API_VERSION=3
OS_USERNAME=your-username
OS_PASSWORD=your-password
OS_PROJECT_NAME=your-project
OS_PROJECT_DOMAIN_NAME=default
OS_USER_DOMAIN_NAME=default
OS_REGION_NAME=RegionOne

# OpenStack Service Ports (customizable)
OS_COMPUTE_PORT=8774
OS_NETWORK_PORT=9696
OS_VOLUME_PORT=8776
OS_IMAGE_PORT=9292
OS_PLACEMENT_PORT=8780

# MCP Server Configuration (optional)
MCP_LOG_LEVEL=INFO
ALLOW_MODIFY_OPERATIONS=false
FASTMCP_TYPE=stdio
FASTMCP_HOST=127.0.0.1
FASTMCP_PORT=8080
```

### 3. Run Server

#### For Development & Testing
```bash
# Test with MCP Inspector
./scripts/run-mcp-inspector-local.sh

# Direct execution for debugging  
uv run python -m mcp_openstack_ops --log-level DEBUG
```

#### For Production (Docker)

```bash
# 1. Build the MCP server image for Epoxy
./build-mcp-server-docker-image.sh

# 2. Start all services
docker-compose up -d

# 3. Check logs
docker-compose logs -f mcp-server
```

**Container Architecture**:
- **mcp-server**: OpenStack MCP server with 24 tools
- **mcpo-proxy**: HTTP proxy for OpenStack APIs  
- **open-webui**: Web interface for testing and interaction

**Service URLs**:
- MCP Server: `localhost:8080` (HTTP transport)
- MCPO Proxy: `localhost:8000` (OpenStack API proxy)
- Open WebUI: `localhost:3000` (Web interface)

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

---

## Troubleshooting

### Common Issues

#### 1. Hypervisor Statistics Show Zero Values

**Problem**: The `monitor_resources` tool returns all zeros for CPU, memory, and VM counts.

**Possible Causes**:
- **Missing OpenStack credentials**: Ensure your `.env` file contains all required authentication variables
- **SDK version incompatibility**: Use the correct OpenStack SDK version for your deployment
- **Docker-based OpenStack (Kolla)**: Some containerized deployments may not expose hypervisor statistics
- **Nova-compute service issues**: Check if nova-compute is running and properly configured
- **Permission restrictions**: Ensure your user has sufficient privileges to access hypervisor details

**Solutions**:
```bash
# 1. Check OpenStack connectivity
openstack server list  # Should show your instances
openstack hypervisor list  # Should show hypervisors

# 2. Verify environment variables
env | grep OS_

# 3. Check Nova services
openstack compute service list

# 4. Test with admin credentials if available
export OS_USERNAME=admin
export OS_PROJECT_NAME=admin
```

#### 2. Connection Timeouts or Errors

**Problem**: Cannot connect to OpenStack API endpoints.

**Solutions**:
- Verify your `OS_AUTH_HOST` and `OS_AUTH_PORT` and network connectivity
- Check if you're using the correct proxy configuration
- Ensure firewall rules allow access to OpenStack ports (5000, 8774, 9696, etc.)
- Verify service ports configuration (`OS_AUTH_PORT`, `OS_COMPUTE_PORT`, etc.)

#### 3. SDK Compatibility Issues

**Problem**: Import errors, unexpected API responses, or version conflicts.

**Common Symptoms**:
```
ModuleNotFoundError: No module named 'openstack.xyz'
AttributeError: 'Resource' object has no attribute 'abc'
API version mismatch errors
```

**Solution for Epoxy**:
```bash
# Ensure correct SDK version for Epoxy (2025.1)
uv add "openstacksdk>=4.1.0,<=4.4.0"

# Check current version
pip show openstacksdk

# Verify installation
python -c "import openstack; print(openstack.__version__)"
```

---

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
| `OS_AUTH_HOST` | OpenStack Identity service host | Required | Authentication host address |
| `OS_AUTH_PORT` | OpenStack Identity service port | Required | Authentication port |
| `OS_USERNAME` | OpenStack username | Required | User credentials |
| `OS_PASSWORD` | OpenStack password | Required | User credentials |
| `OS_PROJECT_NAME` | OpenStack project name | Required | Project scope |
| `OS_IDENTITY_API_VERSION` | Identity API version | `3` | API version |
| `OS_PROJECT_DOMAIN_NAME` | Project domain name | `default` | Domain scope |
| `OS_USER_DOMAIN_NAME` | User domain name | `default` | Domain scope |
| `OS_REGION_NAME` | OpenStack region | `RegionOne` | Regional scope |
| **OpenStack Service Ports** |
| `OS_COMPUTE_PORT` | Compute service port | `8774` | Nova endpoint |
| `OS_NETWORK_PORT` | Network service port | `9696` | Neutron endpoint |
| `OS_VOLUME_PORT` | Volume service port | `8776` | Cinder endpoint |
| `OS_IMAGE_PORT` | Image service port | `9292` | Glance endpoint |
| `OS_PLACEMENT_PORT` | Placement service port | `8780` | Placement endpoint |
| **MCP Server Configuration** |
| `MCP_LOG_LEVEL` | Logging level | `INFO` | Development debugging |
| `ALLOW_MODIFY_OPERATIONS` | Enable modify operations | `false` | Safety control for state modifications |
| `FASTMCP_TYPE` | Transport type | `stdio` | Rarely needed to change |
| `FASTMCP_HOST` | HTTP host address | `127.0.0.1` | For HTTP mode only |
| `FASTMCP_PORT` | HTTP port number | `8080` | For HTTP mode only |
| **Authentication (Optional)** |
| `REMOTE_AUTH_ENABLE` | Enable Bearer token authentication for streamable-http mode | `false` | Production security |
| `REMOTE_SECRET_KEY` | Secret key for Bearer token authentication | Required when auth enabled | Production security |

**Note**: MCP servers typically use `stdio` transport. HTTP mode is mainly for testing and development.

---

## Safety Controls

### Modification Operations Protection

By default, all operations that can modify or delete OpenStack resources are **disabled** for safety:

```bash
# Default setting - Only read-only operations allowed
ALLOW_MODIFY_OPERATIONS=false
```

**Protected Operations (when `ALLOW_MODIFY_OPERATIONS=false`):**
- Instance management (start, stop, restart, pause, unpause)
- Volume operations (create, delete, attach, detach)
- Keypair management (create, delete, import)
- Floating IP operations (create, delete, associate, disassociate)
- Snapshot management (create, delete)
- Image management (create, delete, update)
- Stack operations (create, delete, update)

**Always Available (Read-Only Operations):**
- Cluster status and monitoring
- Resource listings (instances, volumes, networks, etc.)
- Service status checks
- Usage and quota information
- Search and filtering operations

**⚠️ To Enable Modify Operations:**
```bash
# Enable all operations (USE WITH CAUTION)
ALLOW_MODIFY_OPERATIONS=true
```

**Tool Registration Behavior:**
- When `ALLOW_MODIFY_OPERATIONS=false`: Only read-only tools are registered with the MCP server
- When `ALLOW_MODIFY_OPERATIONS=true`: All tools (read-only + modify operations) are registered
- Tool availability is determined at server startup - restart required after changing this setting

**Best Practices:**
- Keep `ALLOW_MODIFY_OPERATIONS=false` in production environments
- Enable modify operations only in development/testing environments
- Use separate configurations for different environments
- Review operations before enabling modify capabilities
- Restart the MCP server after changing the `ALLOW_MODIFY_OPERATIONS` setting

---

## Example Queries

For comprehensive tool usage examples and query patterns, see: **[Example Queries in Prompt Template](src/mcp_openstack_ops/prompt_template.md#7-example-queries)**

---

## Performance Optimization

### Large-Scale Environment Support

The MCP server is optimized for large OpenStack environments with thousands of instances:

**Pagination Features:**
- Default limits prevent memory overflow (50 instances per request)
- Configurable safety limits (maximum 200 instances per request)
- Offset-based pagination for browsing large datasets
- Performance metrics tracking (processing time, instances per second)

**Search Optimization:**
- 2-phase search process (basic info filtering → detailed info retrieval)
- Intelligent caching with connection reuse
- Selective API calls to minimize overhead
- Case-sensitive search options for precise filtering

**Connection Management:**
- Global connection caching with validity testing
- Automatic retry mechanisms for transient failures
- Connection pooling for high-throughput scenarios

**Usage Examples:**
```bash
# Safe large environment browsing
get_instance_details(limit=50, offset=0)     # First 50 instances
get_instance_details(limit=50, offset=50)    # Next 50 instances

# Emergency override for small environments
get_instance_details(include_all=True)       # All instances (use with caution)

# Optimized search for large datasets
search_instances("web", "name", limit=20)    # Search with reasonable limit
```

---

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

---

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

---

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
```

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
        "OS_AUTH_HOST": "your-openstack-host",
        "OS_AUTH_PORT": "5000",
        "OS_USERNAME": "your-username",
        "OS_PASSWORD": "your-password",
        "OS_PROJECT_NAME": "your-project",
        "OS_COMPUTE_PORT": "8774",
        "OS_NETWORK_PORT": "9696",
        "OS_VOLUME_PORT": "8776",
        "OS_IMAGE_PORT": "9292",
        "OS_PLACEMENT_PORT": "8780",
        "ALLOW_MODIFY_OPERATIONS": "false",
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

---

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

---

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

---

## Logging

The server provides structured logging with configurable levels:

```
2024-08-19 10:30:15 - mcp_main - INFO - Starting MCP server with stdio transport
2024-08-19 10:30:15 - mcp_main - INFO - Log level set via CLI to INFO
2024-08-19 10:30:16 - functions - DEBUG - Fetching data from source: example.com
```

---

## Notes

- The script replaces mcp_openstack_ops (underscore), mcp-openstack-ops (hyphen), and mcp-openstack-ops (display name)
- Configuration validation ensures proper setup before server start
- If you need to rename again, revert changes or re-clone and re-run
- A backup `pyproject.toml.bak` is created when overwriting pyproject
