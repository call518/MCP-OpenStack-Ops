**English** | [Korean](development.ko.md)

# Development

This guide covers local development, testing, and adding tools.

## Set up and run the tests

Requirements are Git and [uv](https://docs.astral.sh/uv/). uv installs Python
3.12 automatically if needed.

```bash
git clone https://github.com/call518/MCP-OpenStack-Ops.git
cd MCP-OpenStack-Ops
uv sync --locked --extra dev
uv run python -m pytest -q tests
```

The unit tests need no cloud credentials; CI runs the same command. Dependency
versions come from `uv.lock`; see
[OpenStack SDK version for older releases](configuration.md#openstack-sdk-version-for-older-releases)
for changing the openstacksdk version.

## Local testing against a cloud

```bash
# Test with MCP Inspector (recommended)
./scripts/run-mcp-inspector-local.sh

# Test with debug logging
MCP_LOG_LEVEL=DEBUG uv run python -m mcp_openstack_ops

# Validate OpenStack connection
uv run python -c "from src.mcp_openstack_ops.functions import get_openstack_connection; print(get_openstack_connection())"
```

To check project isolation, see
[Project isolation test](security.md#project-isolation-test).

## Live tool checks

`scripts/live_tool_check.py` calls every registered tool through a real MCP
client (in process, or over Streamable HTTP with `--url`), including negative
paths, polls asynchronous operations to their final state with openstacksdk,
and removes what it created. With modification tools enabled it creates and
deletes projects, domains, users, roles, flavors, networks, images and servers
named with `--prefix` (default `mcpval`), and its cleanup deletes every resource
whose name starts with that prefix. Run it only as an administrator against a
disposable test cloud; state-changing runs require
`--i-understand-this-is-destructive`.

```bash
# OS_* variables for the test cloud, plus OS_AUTH_HOST/OS_AUTH_PORT for the server
. admin-openrc.sh
ALLOW_MODIFY_OPERATIONS=true uv run python scripts/live_tool_check.py \
  --i-understand-this-is-destructive \
  --image cirros --flavor m1.tiny --resize-flavor m1.small \
  --network demo-net --external-network public1 --existing-server demo1 \
  --output live-tool-check.json
```

The summary reports call and final-state check counts and a unique-tool
classification (`passed`, `passed_partial_service`, `service_absent`,
`error_paths_only`, `partial`, `failed`). A tool whose service is not deployed
passes only by returning an explicit error, which is not live validation. Keep
result files out of the repository (`live-tool-check*.json` is ignored).

## Adding custom tools

This MCP server is designed for easy extensibility. Follow these steps to add your own custom tools:

### 1. Add helper functions (optional)

Add reusable data functions to `src/mcp_openstack_ops/functions.py`:

```python
async def get_your_custom_data(target_resource: str = None) -> List[Dict[str, Any]]:
    """Your custom data retrieval function."""
    # Example implementation - adapt to your OpenStack service
    conn = get_openstack_connection()
    results = []

    try:
        # Example: Custom query using OpenStack SDK
        resources = conn.your_service.list_resources(
            filters={'name': target_resource} if target_resource else {}
        )

        for resource in resources:
            results.append({
                'name': resource.name,
                'id': resource.id,
                'status': resource.status,
                'created_at': resource.created_at,
                # Add your custom fields
            })

    except Exception as e:
        logger.error(f"Failed to get custom data: {e}")
        return []

    return results
```

### 2. Create your MCP tool file

Create a new file `src/mcp_openstack_ops/tools/get_your_custom_analysis.py`:

```python
"""Tool implementation for get_your_custom_analysis."""

import json
from datetime import datetime
from typing import Optional
from ..functions import get_your_custom_data  # Import your helper function
from ..mcp_main import (
    logger,
    mcp,
)

@mcp.tool()
async def get_your_custom_analysis(limit: int = 50, target_name: Optional[str] = None) -> str:
    """
    [Tool Purpose]: Brief description of what your tool does

    [Exact Functionality]:
    - Feature 1: Data aggregation and analysis
    - Feature 2: Resource monitoring and insights
    - Feature 3: Performance metrics and reporting

    [Required Use Cases]:
    - When user asks "your specific analysis request"
    - Your business-specific monitoring needs

    Args:
        limit: Maximum results (1-100)
        target_name: Target resource/service name

    Returns:
        Formatted analysis results
    """
    try:
        limit = max(1, min(limit, 100))  # Always validate input

        logger.info(f"Getting custom analysis, limit: {limit}, target: {target_name}")

        results = await get_your_custom_data(target_resource=target_name)

        if not results:
            return f"No custom analysis data found" + (f" for '{target_name}'" if target_name else "")

        # Apply limit
        results = results[:limit]

        # Format results as table
        table_data = []
        for item in results:
            table_data.append({
                'Name': item.get('name', 'N/A'),
                'ID': item.get('id', 'N/A'),
                'Status': item.get('status', 'N/A'),
                'Created': item.get('created_at', 'N/A'),
            })

        # Return formatted JSON
        return json.dumps({
            'title': f'Custom Analysis (Top {len(results)})',
            'data': table_data,
            'total_count': len(results),
            'timestamp': datetime.now().isoformat()
        }, indent=2)

    except Exception as e:
        logger.error(f"Failed to get custom analysis: {e}")
        return f"Error: {str(e)}"
```

### 3. For modify operations (optional)

If your tool performs modify operations, use the `@conditional_tool` decorator instead:

```python
"""Tool implementation for set_your_custom_resource."""

from ..mcp_main import (
    conditional_tool,  # Use this instead of @mcp.tool()
    handle_operation_result,
    logger,
)
from ..functions import set_your_custom_resource

@conditional_tool  # Only registers when ALLOW_MODIFY_OPERATIONS=true
async def set_your_custom_resource(resource_name: str, action: str) -> str:
    """
    Manage your custom OpenStack resources.

    Use when user requests custom resource management.
    """
    try:
        result = set_your_custom_resource(resource_name, action)

        return handle_operation_result(
            result=result,
            operation_name="Custom Resource Management",
            details={
                'Resource': resource_name,
                'Action': action
            }
        )

    except Exception as e:
        logger.error(f"Custom resource operation failed: {e}")
        return f"Error: {str(e)}"
```

### 4. Describe the tool and add examples (recommended)

Clients choose tools from their descriptions, so put the purpose, key
parameters, and limits in the tool's docstring and parameter descriptions.
Add example requests for the tool to the
[usage guide](usage-guide.md#example-queries-by-area) in both languages.

`src/mcp_openstack_ops/server_instructions.md` holds the server instructions
that the server sends to clients when they connect. Change it only for rules
that span several tools, such as call order or scope. Keep it under 4,096
characters, the length Claude Code keeps; a unit test checks this limit.

### 5. Test your tool

```bash
# Local testing
./scripts/run-mcp-inspector-local.sh

# Or with Docker
docker compose up -d
docker compose logs -f mcp-server

# Test with natural language:
# "Show me your custom analysis"
# "Get custom analysis for target_name"
```

When the tool calls a new OpenStack service or changes what an existing tool
does, update the README
[CLI-to-tool mapping](../README.md#-openstack-cli-vs-mcp-tools-mapping) as
described in `AGENTS.md`.

### Tool registration system

The MCP server uses automatic tool discovery. When you create a new file in `src/mcp_openstack_ops/tools/`, it's automatically registered through the `register_all_tools()` function in `tools/__init__.py`. No manual import registration needed!

### Safety system

- **Read-only tools**: Use `@mcp.tool()` - always available
- **Modify tools**: Use `@conditional_tool` - only available when `ALLOW_MODIFY_OPERATIONS=true`
- **Connection**: Always use `get_openstack_connection()` for OpenStack API access
- **Project isolation**: All operations are automatically scoped to `OS_PROJECT_NAME`

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request
