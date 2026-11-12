**English** | [Korean](usage-guide.ko.md)

# Usage guide

This guide shows how the tools are typically used: example requests, bulk and
filtered actions, post-action status, and pagination for large projects. For
every tool and the OpenStack CLI command it corresponds to, see the README
[CLI-to-tool mapping](../README.md#-openstack-cli-vs-mcp-tools-mapping).

## Example requests

Ask in natural language; the client chooses the tools. For example:

```text
Show me the overall cluster status
List all instances in the project
Find instances in SHUTOFF state
Show all networks and their subnets
List all volumes and their status
Show the vCPUs and memory allocated to my project and the remaining quota
Show CPU usage of web-01 over the last hour
Stop all instances with name containing 'test'
```

Requests that create, change or delete resources work only when modification
tools are enabled (`ALLOW_MODIFY_OPERATIONS=true`). Telemetry requests such as
CPU usage need Ceilometer and Gnocchi in the cloud.

More examples, grouped by area and with the tools each request uses, are in
[Example Queries & Usage Patterns](../src/mcp_openstack_ops/prompt_template.md#7-example-queries--usage-patterns):

- 🎯 Cluster overview and status queries
- 🖥️ Instance management operations
- 🌐 Network configuration tasks
- 💾 Storage management workflows
- 🗂️ Cross-project reads (opt-in, `ALLOW_CROSS_PROJECT_READ=true`)
- 🔥 Heat orchestration examples
- ⚖️ Load balancer operations
- 🔍 Advanced search patterns
- 📊 Monitoring and troubleshooting
- 🧠 Complex multi-tool query combinations

## Bulk operations and filter-based targeting

Several management tools act on many resources in one call, either from a list
of names or from filter criteria:

```bash
# One call per instance:
set_instance("vm1", "stop")
set_instance("vm2", "stop")

# One call for every instance whose name contains "test":
set_instance(action="stop", name_contains="test")
```

**Tools with bulk and filter support:**
- **`set_instance`**: Bulk lifecycle management with filtering (name_contains, status, flavor_contains, image_contains)
- **`set_volume`**: Bulk volume operations with filtering (name_contains, status, size filtering)
- **`set_image`**: Bulk image management with filtering (name_contains, status)
- **`set_networks`**: Bulk network operations with filtering (name_contains, status)
- **`set_keypair`**: Bulk keypair management with filtering (name_contains)
- **`set_snapshot`**: Bulk snapshot operations with filtering (name_contains, status)

**Input formats:**
```python
# Single resource
resource_names="vm1"

# Multiple resources (comma-separated)
resource_names="vm1,vm2,vm3"

# JSON array format
resource_names='["vm1", "vm2", "vm3"]'

# Filter-based (automatic target identification)
name_contains="test", status="ACTIVE"
```

## Post-action status

Management operations report the outcome per resource and the status read back
after the action:

```bash
✅ Bulk Instance Management - Action: stop
📊 Total instances: 3
✅ Successes: 2
❌ Failures: 1

Post-Action Status:
🟢 test-vm-1: SHUTOFF
🟢 test-vm-2: SHUTOFF
🔴 test-vm-3: ERROR
```

Many OpenStack operations are asynchronous: an accepted request is not a
finished operation. Check the final state with a read tool when it matters.

## Instance queries

`get_instance` combines lookup by name, ID, status and free-form search in one
tool, with pagination and summary or detailed output, for example
`get_instance(names="vm1,vm2")`. The dedicated tools `get_instance_details`,
`get_instance_by_name`, `get_instances_by_status` and `search_instances` are
also available.

## Large projects and pagination

Instance listings are paginated so that large projects do not return thousands
of instances at once:

- `get_instance_details` returns 50 instances per request by default, at most 200
- `limit` and `offset` page through the results
- `include_all=True` ignores the limit; use it with caution in large projects

```bash
# Browse a large project page by page
get_instance_details(limit=50, offset=0)     # First 50 instances
get_instance_details(limit=50, offset=50)    # Next 50 instances

# All instances (use with caution)
get_instance_details(include_all=True)

# Search with pagination
search_instances("web", "name", limit=20, offset=0, case_sensitive=False)
```
