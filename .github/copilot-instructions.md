# GitHub Copilot Instructions

## 🚫 CRITICAL RESTRICTIONS - ALWAYS ENFORCE

### **Never Execute These Operations Directly:**
- **Git operations**: Never run `git add`, `git commit`, `git push`, `git pull`, `git tag`, or any Git commands
- **Docker operations**: Never run `docker build`, `docker run`, `docker-compose up/down`, `docker push`, or any Docker commands
- **Instead**: Always ask the user to execute these commands manually

### **Python Execution Requirements:**
- **MANDATORY**: Always use `.venv/bin/python` for all Python execution
- **MANDATORY**: Always use `.venv/bin/pip` for all package management
- **NEVER use**: `python`, `python3`, `/usr/bin/python`, `pip`, `pip3`, or system Python/pip
- **Example**: Use `.venv/bin/python -m mcp_openstack_ops` instead of `python -m mcp_openstack_ops`
- **Example**: Use `.venv/bin/pip install package` instead of `pip install package`

### **MCP Tool Safety Control Requirements:**
- **MANDATORY**: When adding new MCP tools with modify operations, always use `@conditional_tool` decorator
- **MANDATORY**: Verify that ALLOW_MODIFY_OPERATIONS=false properly hides modify tools from registration
- **NEVER use**: `@mcp.tool()` for operations that can modify/delete OpenStack resources
- **Always test**: Tool visibility with both `ALLOW_MODIFY_OPERATIONS=true` and `ALLOW_MODIFY_OPERATIONS=false`
- **Pattern**: Read-only tools use `@mcp.tool()`, modify tools use `@conditional_tool`

---

## Architecture Overview
This is an **MCP (Model Context Protocol) Server for OpenStack Operations** - a Python service providing real-time OpenStack cluster management through 24+ tools. The architecture follows a layered pattern:

- **`src/mcp_openstack_ops/functions.py`** (3000+ lines): Core OpenStack SDK operations with connection caching
- **`src/mcp_openstack_ops/mcp_main.py`** (1400+ lines): FastMCP tool definitions and conditional safety system
- **`src/mcp_openstack_ops/prompt_template.md`**: AI assistant behavior guide with tool patterns

## Critical Safety System
The codebase implements a **conditional tool registration pattern** via `ALLOW_MODIFY_OPERATIONS` environment variable:

```python
@conditional_tool  # Only registers when ALLOW_MODIFY_OPERATIONS=true
async def set_instance(instance_name: str, action: str) -> str:
```

vs.

```python
@mcp.tool()  # Always available (read-only operations)
async def get_cluster_status() -> str:
```

**Never bypass this safety system** - it prevents destructive operations in production.

## Environment Configuration Patterns
Connection management uses **proxy-based routing** with service-specific ports:

```bash
# Required for OpenStack connection
OS_AUTH_HOST=192.168.35.2
OS_AUTH_PORT=5555

# Service-specific ports (Heat Stack naming convention)
OS_HEAT_STACK_PORT=8004
OS_HEAT_STACK_CFN_PORT=18888
```

## Key Development Workflows

### Testing MCP Server
```bash
# REQUIRED: Use virtual environment Python only
.venv/bin/python -m mcp_openstack_ops --stdio

# Connection validation
.venv/bin/python -c "from mcp_openstack_ops.functions import get_openstack_connection; print('OK')"

# NEVER use system Python
# ❌ python -m mcp_openstack_ops
# ❌ python3 -m mcp_openstack_ops
```

### Adding New OpenStack Services
1. Add core function to `functions.py` with connection caching pattern
2. Create MCP tool wrapper in `mcp_main.py` (use `@conditional_tool` for modify operations)
3. Update `prompt_template.md` with tool patterns and decision flows
4. Add environment variables for service ports if needed

## Connection Management Pattern
Global connection caching with automatic retry:

```python
_connection_cache = None

def get_openstack_connection():
    global _connection_cache
    if _connection_cache is not None:
        try:
            _connection_cache.identity.get_token()  # Test validity
            return _connection_cache
        except Exception:
            _connection_cache = None  # Reset on failure
```

## Resource Monitoring Conventions
Always distinguish **physical vs. virtual resources** in monitoring results:
- `pCPU` = physical CPU cores (hypervisor hardware)
- `vCPU` = virtual CPU allocation (project quota)
- Use separate table rows, never combine in single row

## Function Naming Conventions
- Core functions: `get_*()`, `set_*()`, `search_*()`, `monitor_*()`  
- Heat-specific: `get_heat_stacks()`, `set_heat_stack()` (not generic `stack`)
- Load Balancer: `get_load_balancer_*()`, `set_load_balancer*()` (Octavia operations)
- MCP tools: Must exactly match underlying function names

## Docker Multi-Service Architecture
The `docker-compose.yml` orchestrates three services:
- **mcp-server**: Main FastMCP server (port via `DOCKER_EXTERNAL_PORT_MCP_SERVER`)
- **mcpo-proxy**: HTTP proxy for web clients  
- **open-webui**: Chat interface for testing

**Critical**: MCP server ports must align across `.env`, `docker-compose.yml`, and `mcp-config.json.http`.

## Error Handling Pattern
All OpenStack operations use consistent error handling:

```python
try:
    conn = get_openstack_connection()
    # OpenStack SDK operations
    return result_data
except Exception as e:
    logger.error(f"Operation failed: {e}")
    return {"error": str(e), "success": False}
```

## Never Execute Directly
- **Git operations**: `git add`, `commit`, `push`, `pull`, `tag` - ask user to run manually
- **Docker operations**: `docker build`, `docker-compose up/down`, `docker push` - ask user to run manually  
- **Package management**: `uv add`, `pip install`, `uv sync` - ask user to run manually
- **Python execution**: Only use `.venv/bin/python`, never system Python
- **Pip commands**: Only use `.venv/bin/pip`, never system pip

## Pagination Support
Large-scale environments require pagination in data-heavy functions:

```python
def get_instance_details(instance_names=None, limit=50, offset=0, include_all=False):
```

Default limit: 50, max: 200, always include pagination metadata in responses.

## Transport Modes
- **stdio**: Direct pipe communication via `mcp-config.json.stdio`
- **streamable-http**: Web API via `mcp-config.json.http` with optional authentication

Both modes share the same environment variable structure but different client configurations.
