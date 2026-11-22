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
[Example queries by area](#example-queries-by-area).

## Example queries by area

Copy any request below into your client. The tools listed under each group are
the ones the client typically calls.

### 🎯 Cluster overview and status

```
"Show me the overall cluster status"
"Create a comprehensive cluster report"
"What's the current infrastructure health?"
"Give me a cluster overview with resource allocation and capacity"
```

**Tools used:** `get_service_status()`, `get_resource_monitoring()`

### 🖥️ Instance management

```
"List all instances in the project"
"Show details for instance web-server-01"
"Create an instance named test-vm with flavor m1.small and image ubuntu-20.04"
"Start instance web-server-01"
"Stop all instances with name containing 'test'"
"Delete instance old-server"
```

**Tools used:** `get_instance_details()`, `set_instance()`, `search_instances()`

### 🌐 Network operations

```
"Show all networks and their subnets"
"List floating IPs and their assignments"
"Create a network named private-net with subnet 192.168.100.0/24"
"Associate floating IP 203.0.113.10 to instance web-server"
"Show network topology"
```

**Tools used:** `get_network_details()`, `get_floating_ips()`, `set_networks()`, `set_floating_ip()`

### 💾 Storage management

```
"List all volumes and their status"
"Show volume details for data-volume-01"
"Create a 50GB volume named backup-storage"
"Attach volume data-vol to instance web-server-01"
"Create a snapshot of volume database-storage"
```

**Tools used:** `get_volume_list()`, `set_volume()`, `set_snapshot()`

### 🗂️ Cross-project reads (advanced, opt-in)

Off by default. These requests need `ALLOW_CROSS_PROJECT_READ=true` and
OpenStack permissions; see the [cross-project reads guide](cross-project-guide.md).

```
"List all projects in the cloud"
"Show a table of VMs per project"
"Which projects have SHUTOFF instances?"
"Find instances named 'web' in every project"
"List volumes across all projects with size and status"
"Which project uses the most volume storage?"
"Show volume snapshots in every project"
"How many instances and volumes does each project have?"
"Show the resource counts of project 'dev'"
"List networks and floating IPs of every project"
"Show volume backups and server groups in all projects"
"List load balancers and private images of every project"
```

**Tools used:** `get_project_details(all_projects=true)`, `get_instance_details(all_projects=true)`, `get_instances_by_status(all_projects=true)`, `search_instances(all_projects=true)`, `get_volume_list(all_projects=true)`, `get_volume_snapshots(all_projects=true)`, `get_network_details(all_projects=true)`, `get_routers(all_projects=true)`, `get_security_groups(all_projects=true)`, `get_floating_ips(all_projects=true)`, `get_volume_backups(all_projects=true)`, `get_volume_groups(all_projects=true)`, `get_server_groups(all_projects=true)`, `get_image_detail_list(all_projects=true)`, `get_heat_stacks(all_projects=true)`, `get_load_balancer_list(all_projects=true)`

**Flow:** Pass `all_projects=true` only when the user asks about all or other projects. Group rows by `project_name` (fall back to `project_id`), and for `get_instance_details` use `include_all=true` or pagination so no project is cut off. Report `scope.projects_in_result`; when `scope.warning` is present, say the result may cover only the current project. A "Cross-project reads are disabled" error means the operator has not set `ALLOW_CROSS_PROJECT_READ=true`; a policy-denial error means the credential lacks permission. Never retry such a request without `all_projects` and present it as cloud-wide. For one project's resource counts, call `get_project_details` with that project's name or ID and `all_projects=true`; if the name matches several projects, retry with the ID.

### 🖼️ Image operations

```
"List available images"
"Show details for Ubuntu images"
"Create an image from instance web-server-01 named custom-web-image"
"Delete image old-snapshot-image"
```

**Tools used:** `get_image_detail_list()`, `set_image()`

### 👥 Identity and access

```
"Show project details and quotas"
"List users in current project"
"Show role assignments"
"Create keypair named my-key"
```

**Tools used:** `get_project_details()`, `get_user_list()`, `get_role_assignments()`, `set_keypair()`

### 🔥 Orchestration (Heat)

```
"List all Heat stacks"
"Show stack status for production-stack"
"Create stack from template with parameters"
"Delete stack old-deployment"
```

**Tools used:** `get_heat_stacks()`, `set_heat_stack()`

<a id="heat-request-examples"></a>

#### Full-stack requests: autoscaling web tier

A request can describe a whole stack in plain language; the client designs
the templates, creates what the stack needs, and reports the result. The
[Heat autoscaling tutorial](heat-autoscaling-tutorial.md) walks through what
the client builds from a basic request like the first one.

Basic request:

```text
Use the web-01 VM (web server) as the source for a new base image. Create and bring up a Heat stack with a TLS-terminating load balancer and autoscaling web servers.
Run 2 web servers normally, with a maximum of 4. Scale out by 1 when average CPU utilization stays above 60% for 1 minute, and scale in by 1 when it stays below 40% for 5 minutes, down to 2. Use a 900-second cooldown and set the stack's timeout_mins to 60.
```

Advanced request, adding storage and network QoS:

```text
Use the web-01 VM (web server) as the source for a new base image. Create and bring up a Heat stack with a TLS-terminating load balancer and autoscaling web servers.
Run 2 web servers normally, with a maximum of 4. Scale out by 1 when average CPU utilization stays above 60% for 5 minutes, and scale in by 1 when it stays below 40% for 5 minutes, down to 2. Use a 900-second cooldown and set the stack's timeout_mins to 60.

Base image:
- Make the base image a Glance image that contains the data, so that root volumes can be created with any volume type.

Storage and network QoS:
- Create a volume QoS spec and volume type for the web servers' root and data volumes, a bandwidth limit policy for the web server ports, and a DSCP marking policy for the load balancer VIP. Choose the names, rules and values yourself, but use only rules that this environment's Cinder backend and Neutron QoS driver actually enforce.
- Create these resources in the same Heat stack where possible, so they share the stack's lifecycle and can be identified by the stack name. Do not modify existing QoS policies or volume types.
- Boot the web servers from volumes, and give each web server a 20 GB root volume and a 5 GB data volume of the new volume type.
- Apply the bandwidth limit policy to the web server ports. Instances added by scale-out must get the same volume type and QoS automatically.
- Apply the DSCP marking policy to the load balancer VIP. If Heat cannot set it, apply it after the stack is created through Octavia's vip_qos_policy_id; if the tools cannot do that, give me the command to run. If it still cannot be applied, tell me why.

Completion report:
- Check load balancer member health only after the members have had time to settle after boot.
- In the final report, include:
  1) The names, rules, values and reasons for the new volume QoS spec, volume type and network QoS policies
  2) The volume type and QoS attachment of each instance
  3) Whether each port has its QoS policy, including the VIP and VRRP ports
  4) Anything that could not be applied and why, and any remaining manual steps
```

Notes for the advanced request:

- The base image is made with `set_volume`: `create` with `source_snapshot`
  turns the snapshot of a boot-from-volume server into a volume, and
  `upload_to_image` copies that volume into a Glance image with data.
- Under Cinder's default policy, creating volume types and QoS specs requires
  the administrator role.
- Heat's `OS::Octavia::LoadBalancer` has no QoS property, so the client
  attaches the VIP policy after the stack is created with `set_load_balancer`
  (`vip_qos_policy`). With the amphora provider, Octavia applies it to the
  amphora VRRP ports, which is why the report covers those ports.

**Tools used:** `set_instance()`, `set_volume()`, `set_secret()`, `set_heat_stack()`, `get_heat_stack_details()`, `set_load_balancer()`, `get_load_balancer_details()`, `get_network_qos_policies()`, `get_server_volumes()`

### ⚖️ Load balancer

```
"Show load balancer status"
"List all load balancers and listeners"
"Create load balancer for web tier"
"Show health monitor status"
```

**Tools used:** `get_load_balancer_details()`, `set_load_balancer()`, `get_load_balancer_listeners()`

### 🔐 Barbican secrets and TLS listeners

```
"List Barbican secrets and show which services use web-tls"
"Create a self-signed TLS secret named web-tls for 192.168.35.169"
"Add a TERMINATED_HTTPS listener on port 443 to web-lb with certificate web-tls"
"Show the ACL of secret web-tls"
```

**Tools used:** `get_secrets()`, `set_secret()`, `set_load_balancer_listener()`, `get_secret_acl()`

Secret payloads never pass through these tools; register your own certificates
outside MCP. See the [Barbican and TLS guide](barbican-tls-guide.md).

### 🔍 Advanced search and filtering

```
"Find all instances with 'web' in the name"
"Search for running instances"
"Show instances created in the last 7 days"
"Find volumes larger than 100GB"
```

**Tools used:** `search_instances()`, `get_instances_by_status()`

### 📊 Resource allocation and capacity

```
"Show resource allocation and capacity by hypervisor"
"How many vCPUs and how much RAM are allocated in my project?"
"Show quota usage and limits"
"Display storage capacity statistics"
"Show the vCPUs and memory allocated to my project and the remaining quota"
```

**Tools used:** `get_resource_monitoring()`, `get_quota()`, `get_usage_statistics()`

Results are allocations, quotas, and capacity, not measured utilization.

### 📡 Telemetry metrics (Gnocchi)

```
"Monitor CPU and memory usage of web-01"
"Show the actual CPU utilization trend of web-01"
"Show the telemetry metrics collected for server web-01"
"Show memory measures of web-01 since 2026-11-08T00:00:00, resampled hourly"
"List all Gnocchi metrics in my project"
"Show the archive policies and supported aggregation methods"
"Is Gnocchi measure processing backlogged?"
"Show the latest 10 vcpus measures of web-01"
"What is the average CPU usage across all instances in my project?"
"Show the top 5 instances by CPU usage"
"Show mean memory usage per flavor"
"Show the memory.usage to flavor memory ratio across my instances"
```

**Tools used:** `get_gnocchi_resources()`, `get_gnocchi_metrics()`, `get_gnocchi_measures()`, `get_gnocchi_aggregates()`, `get_gnocchi_service_info()`

**Flow:** Resolve the server UUID with `get_instance_by_name()`, find metric names with `get_gnocchi_resources(resource_type="instance", resource_id=UUID)`, then call `get_gnocchi_measures(metric=name, resource_id=UUID)`. Use a granularity and aggregation from the metric's archive policy. `cpu` is cumulative nanoseconds: request `aggregation="rate:mean"` and divide by granularity × 10^9 × vCPUs for a utilization fraction. Report a missing metric as not collected; never estimate values.

**Cross-resource flow:** Use `get_gnocchi_aggregates` in ONE mode. Simple mode examples: project average CPU → `metric="cpu", aggregation="rate:mean", reaggregation="mean"`; top 5 CPU → `metric="cpu", aggregation="rate:mean", top=5`; per-flavor memory → `metric="memory.usage", reaggregation="mean", groupby="flavor_name"`. Use expression mode (`operations` only) just for arithmetic such as `(/ (metric memory.usage mean) (metric memory mean))`; write metric names, never metric UUIDs. Report `resource_name` from the series and state that results cover only the current project. A "Metric ... does not exist" failure can also mean no current-project resource matched.

### 🚨 Alarms (Aodh)

```
"List alarms in my project"
"Create an alarm when web-01 memory.usage exceeds 1500 MB"
"Create an alarm when web-01 CPU exceeds 80%"
"Show details and current state of alarm mem-high"
"Delete alarm mem-high"
"Create a threshold alarm on the vcpus metric of web-01"
```

**Tools used:** `set_alarms()` (requires `ALLOW_MODIFY_OPERATIONS=true`), `get_gnocchi_metrics()`

**Flow:** Before `set_alarms(action="create")`, confirm the metric exists on the resource with `get_gnocchi_metrics(resource_id=UUID)`. Aodh accepts nonexistent resources and uncollected metrics such as the default `cpu_util`, and such alarms stay `insufficient data`. Never rely on the `cpu_util` default: for CPU percentage alarms, pass `metric="cpu"`, `aggregation_method="rate:mean"`, and `threshold = percent / 100 × granularity × 10^9 × vCPUs` (80% of 1 vCPU at 300 s = 2.4e11). A new alarm is `insufficient data` until evaluated, which can take several minutes; report the returned state, not an assumed one.

### 🛠️ Troubleshooting

```
"Check OpenStack service status"
"Show instance events for server-01"
"Display hypervisor details"
"Show network agent status"
```

**Tools used:** `get_service_status()`, `get_server_events()`, `get_hypervisor_details()`

### 🔒 Security operations

```
"List security groups and rules"
"Show keypair information"
"Display floating IP associations"
"Check role assignments for current project"
```

**Tools used:** `get_security_groups()`, `get_keypair_list()`, `get_floating_ips()`, `get_role_assignments()`

### 📈 Performance and optimization

```
"Show top 10 instances by allocated vCPU and RAM"
"Display flavor allocation statistics"
"Monitor network resource counts and status"
"Check disk I/O telemetry of web-01"
```

**Tools used:** `get_instance_details()`, `get_resource_monitoring()` (allocation), `get_gnocchi_measures()` (measured I/O, if collected)

### 🎛️ Batch operations

```
"Stop all instances with tag 'development'"
"Create multiple volumes with names vol-01, vol-02, vol-03"
"Delete all snapshots older than 30 days"
"Update all instances with new security group"
```

**Tools used:** Multiple tools combined with filtering parameters

### 🧠 Advanced query patterns

#### Multi-tool combinations for complex queries

```
"Show complete infrastructure overview" →
1. get_service_status() (service health)
2. get_resource_monitoring() (allocation and capacity)
3. get_instance_details() (compute resources)
4. get_network_details() (network topology)
5. get_volume_list() (storage resources)
6. get_project_details() (quotas & usage)
```

```
"Troubleshoot performance issues" →
1. get_instance_details() (instance status & specs)
2. get_gnocchi_measures() (measured load, if collected)
3. get_resource_monitoring() + get_hypervisor_details() (allocation and host capacity)
4. get_service_status() (service health)
```

```
"Security audit report" →
1. get_security_groups() (security rules)
2. get_floating_ips() (external access points)
3. get_keypair_list() (SSH access keys)
4. get_role_assignments() (user permissions)
5. get_user_list() (project members)
```

#### Natural language to tool translation examples

- **"Show me everything"** → Comprehensive cluster report using multiple tools
- **"What's broken?"** → Service status + resource monitoring + instance health checks
- **"Can I create a new VM?"** → Project quotas + available flavors + network options
- **"Why is my instance slow?"** → Instance details + resource monitoring + hypervisor status
- **"Show network connectivity"** → Network details + security groups + floating IPs + routers
- **"Open public TCP port 80 on security group web"** → `set_security_group_rules(action="create", security_group="web", protocol="tcp", port_range_min=80, port_range_max=80, remote_ip_prefix="0.0.0.0/0")`

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
- **`set_instance`**: Bulk lifecycle management with filtering (name_contains, status, flavor_contains, image_contains). Every given filter must match. More matches than the server's `INSTANCE_FILTER_MAX_MATCHES` (default 100; see [Configuration](configuration.md#environment-variables)) are refused without acting on any instance; narrow the filters
- **`set_volume`**: Bulk volume operations on a list of names; no filter parameters
- **`set_image`**: Bulk image management on a list of names; no filter parameters
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

- `get_instance_details` returns 50 instances per request by default, at most the server's `LIST_MAX_LIMIT` (default 100)
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
