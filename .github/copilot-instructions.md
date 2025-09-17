# MCP OpenStack Operations - AI Coding Instructions

## Architecture Overview

**MCP OpenStack Ops** is a Model Context Protocol (MCP) server providing 24 OpenStack management tools via FastMCP framework. Key components:

- **Core Engine**: `src/mcp_openstack_ops/functions.py` - OpenStack SDK wrapper with global connection caching
- **MCP Interface**: `src/mcp_openstack_ops/mcp_main.py` - FastMCP tool definitions and JSON serialization
- **AI Guidance**: `src/mcp_openstack_ops/prompt_template.md` - Tool selection patterns for AI assistants
- **Containerized Deployment**: Docker Compose with MCP server, MCPO proxy, and Open WebUI integration

## Critical Development Patterns

### 1. OpenStack Connection Management
**ALWAYS use global connection caching** in `functions.py`:
```python
# Pattern: Test cached connection validity before use
global _connection_cache
if _connection_cache is not None:
    try:
        _connection_cache.identity.get_token()  # Validity test
        return _connection_cache
    except Exception:
        _connection_cache = None  # Force reconnection
```

### 2. MCP Tool Structure (Required Pattern)
**Every MCP tool** in `mcp_main.py` must follow this exact structure:
```python
@mcp.tool()
async def tool_name(param: str) -> str:
    """
    Brief description.
    
    Functions:
    - List specific functions this tool performs
    
    Use when user requests [specific scenarios].
    """
    try:
        result = helper_function_from_functions_py(param)
        return json.dumps({
            "timestamp": datetime.now().isoformat(),
            "result": result
        }, indent=2, ensure_ascii=False)
    except Exception as e:
        return f"Error: Failed to execute tool - {str(e)}"
```

### 3. Error Handling Strategy
**Defensive programming** required for OpenStack SDK unpredictability:
```python
# Pattern: Use getattr() with defaults for hypervisor attributes
vcpus = getattr(hypervisor, 'vcpus', 0)
memory_mb = getattr(hypervisor, 'memory_mb', 0)
# Never assume OpenStack objects have all expected attributes
```

### 4. Large-Scale Environment Support
**Pagination is mandatory** for production environments:
```python
def get_instance_details(limit: int = 50, offset: int = 0, include_all: bool = False):
    # Default: 50 instances, max: 200, safety override: include_all=True
    if limit > 200: limit = 200  # Hard safety limit
```

## Development Workflows

### Testing & Debugging
```bash
# Local development with MCP Inspector
./scripts/run-mcp-inspector-local.sh

# Direct debugging with detailed logging  
uv run python -m mcp_openstack_ops --log-level DEBUG

# Container rebuild after code changes
docker-compose down && docker-compose up -d --build
```

### Adding New Tools
1. **Helper function** in `functions.py` with OpenStack SDK operations
2. **MCP tool wrapper** in `mcp_main.py` with JSON serialization
3. **Update prompt template** in `prompt_template.md` with tool mapping
4. **Test with MCP Inspector** before production deployment

## Project-Specific Conventions

### File Organization
- `src/mcp_openstack_ops/functions.py` - Core OpenStack operations (2200+ lines)
- `src/mcp_openstack_ops/mcp_main.py` - MCP tool definitions (1300+ lines) 
- `src/mcp_openstack_ops/prompt_template.md` - AI guidance with priority patterns
- `docker-compose.yml` - 3-service deployment (MCP server, proxy, WebUI)

### Configuration Layers
1. **Environment variables** (`.env` file) - OpenStack credentials
2. **CLI arguments** - Transport type, logging level, authentication
3. **Docker environment** - Port mapping, volume mounts, networking

### Transport Modes
- **stdio** (default) - For Claude Desktop integration
- **streamable-http** - For web integration via MCPO proxy
- **Docker services** - Production deployment with external access

## OpenStack SDK Integration Points

### Connection Configuration
Uses proxy-based endpoints in `get_openstack_connection()`:
- Identity: `http://{proxy_host}:5555`
- Compute: `http://{proxy_host}:8774/v2.1`
- Network: `http://{proxy_host}:9696`
- Storage: `http://{proxy_host}:8776/v3`

### Service Coverage (24 Tools)
- **Identity (Keystone)**: User management, role assignments
- **Compute (Nova)**: Instance lifecycle, flavors, keypairs, hypervisors
- **Network (Neutron)**: Networks, floating IPs, routers, security groups
- **Storage (Cinder)**: Volumes, snapshots, volume types
- **Image (Glance)**: Image management operations
- **Orchestration (Heat)**: Stack management and templates

### Performance Optimizations
- **2-phase search**: Basic info filtering → detailed info retrieval
- **Selective API calls**: Minimize overhead in large environments
- **Connection pooling**: Reuse validated connections
- **Safety limits**: Prevent memory overflow with large datasets

## AI Integration Patterns

The `prompt_template.md` defines HIGH PRIORITY patterns:
- **Instance details**: "Show details for instance X" → `get_instance_details(instance_names=["X"])`
- **Cluster analysis**: "detailed cluster analysis" → `get_cluster_status()` 
- **Tool routing**: Decision flow based on user intent keywords

**Critical**: When modifying tool behavior, update both the function implementation AND the prompt template patterns to ensure proper AI tool selection.
