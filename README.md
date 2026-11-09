# MCP-OpenStack-Ops

> **MCP OpenStack Operations Server**: A comprehensive MCP (Model Context Protocol) server providing OpenStack project management and monitoring capabilities with built-in safety controls and single-project scope.

[![MCPVault: claimed](https://mcpvault.io/badge/mcp-openstack-ops.svg?theme=dark)](https://mcpvault.io/servers/mcp-openstack-ops/health?utm_source=external_badge&utm_medium=referral&utm_campaign=mcp_health_report)

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
![Python](https://img.shields.io/badge/Python-3776AB?style=flat&logo=python&logoColor=white)
![Docker Pulls](https://img.shields.io/docker/pulls/call518/mcp-server-openstack-ops)
[![BuyMeACoffee](https://raw.githubusercontent.com/pachadotdev/buymeacoffee-badges/main/bmc-donate-yellow.svg)](https://www.buymeacoffee.com/call518)

[![Deploy to PyPI with tag](https://github.com/call518/MCP-OpenStack-Ops/actions/workflows/pypi-publish.yml/badge.svg)](https://github.com/call518/MCP-OpenStack-Ops/actions/workflows/pypi-publish.yml)
![PyPI](https://img.shields.io/pypi/v/MCP-OpenStack-Ops?label=pypi%20package)
![PyPI - Downloads](https://img.shields.io/pypi/dm/MCP-OpenStack-Ops)

---

## Architecture & Internal (DeepWiki)

[![Ask DeepWiki](https://img.shields.io/badge/Ask-DeepWiki-blue)](https://deepwiki.com/call518/MCP-OpenStack-Ops)

---

## Features

Experimental per-user remote connections are available for testing with the
opt-in `--multi-user` mode. See the [multi-user setup and usage guide](docs/multi-user-guide.md)
for authentication, client limitations, and the test checklist. Administrator
cross-project queries are outside this phase.

- ✅ **Project-Scoped Operations**: Every tool enforces the configured `OS_PROJECT_NAME`, validating resource ownership so actions stay inside a single tenant.
- ✅ **Safety-Gated Writes**: Modify (`set_*`) tooling only registers when `ALLOW_MODIFY_OPERATIONS=true`, keeping default deployments read-only and auditable.
- ✅ **90+ Purpose-Built Tools**: Broad coverage across compute, networking, storage, images, identity, Heat, and Octavia load balancing tasks. Project resources are scoped to the active project; cloud-wide administrative APIs remain subject to OpenStack policy.
- ✅ **Bulk & Filtered Actions**: Instance, volume, network, image, snapshot, and keypair managers accept comma-delimited targets or filter criteria to orchestrate bulk changes intentionally.
- ✅ **Post-Action Feedback & Async Guidance**: Mutating tools reuse a shared result handler that adds emoji status checks, asynchronous timing notes, and follow-up verification commands.
- ✅ **Monitoring & Usage Insights**: `get_service_status`, `get_resource_monitoring`, `get_usage_statistics`, and quota tools report service probes, project allocations, separate quota limits, and API-backed compute allocation-hours. These tools do not collect live utilization or trends; read-only `get_gnocchi_*` tools return telemetry time series when Ceilometer and Gnocchi are deployed.
- ✅ **Unified Instance Queries**: The `get_instance` tool consolidates name, ID, status, and free-form search paths with pagination plus summary/detailed modes.
- ✅ **Server Insight & Audit Trail**: Dedicated tools expose server events, hypervisor details, availability zones, quotas, and resource ownership to speed diagnostics.
- ✅ **Load Balancer Management**: Octavia tools cover listeners, pools, members, health monitors, flavors, quotas, and amphora operations with the same safety gates.
- ✅ **Connection & Deployment Flexibility**: Connection caching, configurable service endpoints, Docker packaging, and both `stdio`/`streamable-http` transports support proxy/bastion and multi-project setups.

> ⚠️ **Compatibility Notice**: This MCP server is developed and optimized for **OpenStack Epoxy (2025.1)** as the primary target environment. However, it is compatible with most modern OpenStack releases (Dalmatian, Caracal, Bobcat, etc.) as the majority of APIs remain consistent across versions. Only a few specific API endpoints may require adaptation for full compatibility with older releases.
> 
> 🚧 **Coming Soon**: Dynamic multi-version OpenStack API compatibility is actively under development and will be available in upcoming releases, providing seamless support for all major OpenStack deployments automatically.

### 🔧 OpenStackSDK Version Customization for Older Releases

**Officially Supported Releases:**
- ✅ OpenStack **Epoxy (2025.1)** - Fully tested
- ✅ OpenStack **Dalmatian (2024.2)** - Fully tested

**For older OpenStack releases** (Wallaby, Caracal, Bobcat, etc.), you may need to customize the OpenStackSDK version to match your environment. The SDK version must be changed in **BOTH files**:

**Step 1: Modify `Dockerfile.MCP-Server`**
```dockerfile
RUN pip install \
        'uv>=0.8.5' \
        'mcpo>=0.0.17' \
        'fastmcp>=2.12.3' \
        'aiohttp>=3.12.0' \
        'openstacksdk==3.1.1' \  # ← Change to your required version (e.g., 3.1.1 for Wallaby)
        'python-dotenv>=1.0.0'
```

**Step 2: Modify `pyproject.toml`**
```toml
dependencies = [
    "fastmcp>=2.12.3",
    "openstacksdk==3.1.1",  # ← Must match Dockerfile version
    "python-dotenv>=1.1.1",
    # ... other dependencies
]
```

**Step 3: Rebuild Docker Image**
```bash
docker compose build --no-cache mcp-server
docker compose up -d
```

**OpenStackSDK Version Reference:**
| OpenStack Release | Recommended SDK Version | Notes |
|-------------------|------------------------|-------|
| Epoxy (2025.1) | `>=3.3.0` | Current default |
| Dalmatian (2024.2) | `>=3.2.0` | Fully compatible |
| Caracal (2024.1) | `>=3.1.0` | May require testing |
| Bobcat (2023.2) | `>=3.0.0` | May require testing |
| Wallaby (2021.1) | `==3.1.1` | Downgrade required |

> ⚠️ **Important**: Both `Dockerfile.MCP-Server` and `pyproject.toml` must have the **same version** to avoid dependency conflicts during container runtime.

---

### Screenshots

**OpenStack Dashboard (Epoxy 2025.1)**

![OpenStack Dashboard (Epoxy 2025.1)](img/screenshot-openstack-dashboard.png)

**MCP Query Example - Cluster Status**

![Example Cluster Status](img/screenshot-claude-desktop.png)

---

## 🆕 Latest Enhancements (v1.x)

### **Bulk Operations & Filter-based Targeting**
Revolutionary approach to resource management enabling one-step operations:

```bash
# Traditional approach (multiple steps):
1. search_instances("test") → get list
2. set_instance("vm1", "stop") → stop individually  
3. set_instance("vm2", "stop") → stop individually

# NEW enhanced approach (single step):
set_instance(action="stop", name_contains="test")  # ✨ Stops ALL instances containing "test"
```

**Supported Tools with Enhanced Capabilities:**
- **`set_instance`**: Bulk lifecycle management with filtering (name_contains, status, flavor_contains, image_contains)
- **`set_volume`**: Bulk volume operations with filtering (name_contains, status, size filtering)
- **`set_image`**: Bulk image management with filtering (name_contains, status)
- **`set_networks`**: Bulk network operations with filtering (name_contains, status)
- **`set_keypair`**: Bulk keypair management with filtering (name_contains)
- **`set_snapshot`**: Bulk snapshot operations with filtering (name_contains, status)

**Input Format Flexibility:**
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

### **Post-Action Status Verification**
Every operation now provides immediate feedback with visual indicators:

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

### **Unified Resource Queries**
New consolidated `get_instance` tool replaces multiple separate tools:
- ❌ Old: `get_instance_details`, `get_instance_info`, `get_instance_status`, `get_instance_network_info`
- ✅ New: `get_instance(names="vm1,vm2")` - Single tool, comprehensive information

---

## 📊 OpenStack CLI vs MCP Tools Mapping

✅ denotes an implemented API path, not certification of every action or
OpenStack deployment. **⚠️ Live unverified** identifies paths without successful
live validation; **❌ Not implemented** identifies unavailable capabilities.
Service availability, permissions, and asynchronous completion affect results.
See [API prerequisites and result semantics](#api-prerequisites-and-result-semantics)
and the [multi-user setup guide](docs/multi-user-guide.md).

**Validation evidence:**
- **Live snapshot (2026-11-04; working tree based on `a57b165`):** This live
  snapshot predates the current working-tree changes. Its live
  classifications remain historical evidence and were not rerun for this change.
- **Live tool checks:** 105/105 registered tools exercised. At least one live
  path passed for 76 tools; 28 tools were unavailable because the test cloud
  lacks Octavia, Aodh, Neutron QoS, or floating-IP port-forwarding APIs; one
  tool (`set_server_dump`) reached its documented platform limitation. The
  `set_snapshot` status fix was retested separately after the full run: an
  actual snapshot reached `available`, and its isolated test project was
  removed. These are unique-tool classifications, not individual call counts.
- **Claude Code prompt checks:** 118/118 documented examples were issued to the
  real MCP servers. 99 completed their tool workflows, including two
  successful retries after an initial bad placeholder; two of those 99 used
  disclosed test substitutions and are not exact request matches. Five
  composite reports were partial because optional APIs were unavailable;
  seven direct requests could not run because their cloud service or extension
  is absent; seven read-like requests were limited by the non-interactive
  Claude permission policy.
- **Follow-up targeted checks:** `/mcp/.well-known/openid-configuration`
  returned 404 without authentication. A real Nova action list explicitly
  reported that the list has no finish time; optional event-detail lookup
  returned an event result and derived its latest finish time. The new
  HTTP-only multi-user test override is **Live unverified**; only its fail-closed
  default, explicit opt-in, endpoint generation, and startup warning were tested
  locally.
- **Targeted telemetry check (2026-11-08 UTC; partial; uncommitted working tree
  based on `d954eba`):** After Ceilometer, Gnocchi, and Aodh were added to the
  test cloud, only `set_alarms` and the four new `get_gnocchi_*` tools were
  rerun through the MCP server. This partial check does not update the
  105-tool live summary above. All five tools passed at least one live path.
  A metric-ownership fix for metric-UUID-only lookups was retested live after
  the MCP server was recreated. Polled metrics were initially absent because
  the test cloud's ceilometer-compute agent had failed to reach libvirt at
  startup; after that agent was restarted, `cpu`, `memory.usage`, disk I/O,
  and network I/O measures were read through the tools. Aodh evaluated `cpu`
  `rate:mean` alarms to the expected `ok` and `alarm` states. Test alarms were
  deleted.
- **Targeted aggregation check (2026-11-09 UTC; partial; uncommitted working
  tree based on `a5115d3`):** only the new `get_gnocchi_aggregates` tool was
  run through the MCP server. The test project had one instance, so ranking
  and grouping returned one series each. After that run, null-gap output,
  metric-name validation, and the failure hint were changed; those changes
  and the core aggregation paths were rerun through a second streamable-HTTP
  MCP server started from the current working tree.
- **Local unit tests (current working tree, 2026-11-09):** 311/311 (100%); no
  failures or skipped tests. These tests include MCP action-description and
  advanced-parameter forwarding regressions, the insecure-HTTP opt-in
  regressions, and Gnocchi project-scoping and aggregation-input regressions; they do not replace
  live service validation.

**Detailed Mapping by Category**

### 1. 🖥️ **Compute (Nova)**

| OpenStack CLI Command | MCP Tool | Status | Notes |
|---------------------|---------|------|------|
| `openstack server list` | `get_instance` | ✅ | Separate reader projects each returned exactly ten owned VMs; bounded lab validation only |
| `openstack server show` | `get_instance` | ✅ | Own fixture queries completed; foreign private ID returned no details; no 16-owned-ID batch claim |
| `openstack server create` | `set_instance` (action="create") | ✅ | **ENHANCED** - Bulk creation support |
| `openstack server start/stop/reboot` | `set_instance` | ✅ | Tool schema exposes all actions and `reboot_type`; bulk stop/start final states verified for two test VMs per project, but reboot was not retested in this round |
| `openstack server delete` | `set_instance` (action="delete") | ✅ | Tool schema exposes delete and optional force deletion; bulk deletion with `name_contains` filtering |
| `openstack server backup create` | `set_server_backup` | ✅ | Nova backup action with rotation; asynchronous, no custom metadata |
| `openstack server image create` | `set_instance` (action="snapshot") | ✅ | Accepts optional `snapshot_name` and JSON `metadata`; parameter forwarding is locally tested, not live-retested in this change |
| `openstack server shelve/unshelve` | `set_instance` | ✅ | Actions are exposed in the tool schema; instance shelving was not live-retested in this change |
| `openstack server lock/unlock` | `set_instance` | ✅ | Instance locking |
| `openstack server pause/unpause` | `set_instance` | ✅ | Instance pausing |
| `openstack server suspend/resume` | `set_instance` | ✅ | Instance suspension |
| `openstack server resize` | `set_instance` (action="resize") | ✅ | Uses the existing `flavor` parameter as the target flavor; action exposure is locally tested |
| `openstack server resize confirm` | `set_instance` (action="confirm_resize") | ✅ | Resize confirmation |
| `openstack server resize revert` | `set_instance` (action="revert_resize") | ✅ | Resize revert |
| `openstack server rebuild` | `set_instance` (action="rebuild") | ✅ | Uses `image` and supports optional `new_name`, JSON `metadata`, and `preserve_ephemeral`; not live-retested in this change |
| `openstack server rescue/unrescue` | `set_instance` | ✅ | Tool schema exposes both actions and optional `rescue_image_id`; not live-retested in this change |
| `openstack server migrate` | `set_server_migration` (action="migrate") | ✅ | Live migration |
| `openstack server evacuate` | `set_server_migration` (action="evacuate") | ✅ | Server evacuation |
| `openstack server migration list` | `set_server_migration` (action="list") | ✅ | Migration listing |
| `openstack server migration show` | `set_server_migration` (action="show") | ✅ | Migration details |
| `openstack server migration abort` | `set_server_migration` (action="abort") | ✅ | Migration abort |
| `openstack server migration confirm` | `set_server_migration` (action="confirm") | ✅ | Migration confirmation |
| `openstack server migration force complete` | `set_server_migration` (action="force_complete") | ✅ | Force migration completion |
| `openstack server add network` | `set_server_network` (action="add_network") | ✅ | Network attachment |
| `openstack server remove network` | `set_server_network` (action="remove_network") | ✅ | Network detachment |
| `openstack server add port` | `set_server_network` (action="add_port") | ✅ | Port attachment |
| `openstack server remove port` | `set_server_network` (action="remove_port") | ✅ | Port detachment |
| `openstack server add floating ip` | `set_server_floating_ip` (action="add") | ✅ | Floating IP association |
| `openstack server remove floating ip` | `set_server_floating_ip` (action="remove") | ✅ | Floating IP disassociation |
| `openstack server add fixed ip` | `set_server_fixed_ip` (action="add") | ✅ | Fixed IP addition |
| `openstack server remove fixed ip` | `set_server_fixed_ip` (action="remove") | ✅ | Fixed IP removal |
| `openstack server add security group` | `set_server_security_group` (action="add") | ✅ | Security group addition |
| `openstack server remove security group` | `set_server_security_group` (action="remove") | ✅ | Security group removal |
| `openstack server add volume` | `set_server_volume` (action="attach") | ✅ | Member attach reached in-use via set_server_volume; guest I/O not tested |
| `openstack server remove volume` | `set_server_volume` (action="detach") | ✅ | Member detach reached available via set_server_volume |
| `openstack server set` | `set_server_properties` (action="set") | ✅ | Server property setting |
| `openstack server unset` | `set_server_properties` (action="unset") | ✅ | Server property unsetting |
| `openstack server dump create` | `set_server_dump` | ❌ Unsupported | Returns an explicit unsupported result; no dump is created |
| `openstack server event list` | `get_server_events` | ✅ | Pass the server name or UUID via `instance_name`, not `server_id`. The action list has no completion time; set `include_event_details=true` to fetch per-action event results and derive the latest finish time. Detailed lookup is capped at 10 actions. Event visibility follows Nova policy |
| `openstack server group list` | `get_server_groups` | ✅ | Server group listing |
| `openstack server group create/delete` | `set_server_group` | ✅ | Server group management |
| `openstack flavor list` | `set_flavor` (action="list") | ✅ | Requires modification tools to be enabled for registration |
| `openstack flavor create/delete` | `set_flavor` | ✅ | Flavor management |
| `openstack keypair list` | `get_keypair_list` | ✅ | Empty scoped read completed; member keypair creation/deletion read-back tested separately |
| `openstack keypair create/delete` | `set_keypair` | ✅ | Explicit member MCP create/delete read-back passed; no successful Claude write workflow claimed |
| `openstack hypervisor list` | `get_hypervisor_details` | ✅ | Administrator lookup verified; missing per-host capacity and incomplete totals are null, not zero. Global enhanced statistics remain separate |
| `openstack availability zone list` | `get_availability_zones` | ✅ | Compute/Cinder availability reads the SDK state mapping; missing availability is null. Actual available zones verified |

### 2. 🌐 **Network (Neutron)**

| OpenStack CLI Command | MCP Tool | Status | Notes |
|---------------------|---------|------|------|
| `openstack network list` | `get_network_details` | ✅ | Two owned private networks plus one policy-visible shared external network per reader; no other test project private networks |
| `openstack network show` | `get_network_details` (network_name) | ⚠️ Live unverified | Foreign-ID negative checked; dual-project positive named reader lookup not independently asserted |
| `openstack network create` | `set_networks` (action="create") | ✅ | Default mtu=0 omits the wire field: backend MTU 1450 verified; explicit 1400 retained in both member projects |
| `openstack network delete` | `set_networks` (action="delete") | ✅ | Both default/explicit-MTU test networks removed through actual TCP MCP, API absence confirmed |
| `openstack network set` | `set_networks` (action="update") | ✅ | **ENHANCED** - Bulk updates |
| `openstack subnet list` | `get_network_details` (includes subnets) | ✅ | Owned and shared external network subnets returned; three visible subnets per test reader |
| `openstack subnet create/delete` | `set_subnets` | ✅ | Member TCP MCP subnet create read back; deletion allowed parent network removal in both projects |
| `openstack router list` | `get_routers` | ⚠️ Live unverified | Only part of composite error requests in this round; no independent reader result attribution |
| `openstack router create/delete` | `set_routers` | ✅ | Project-owned routers; attached interfaces are not removed automatically |
| `openstack floating ip list` | `get_floating_ips` | ✅ | Floating IP listing |
| `openstack floating ip create` | `set_floating_ip` (action="create") | ✅ | Floating IP creation |
| `openstack floating ip delete` | `set_floating_ip` (action="delete") | ✅ | Floating IP deletion |
| `openstack floating ip set` | `set_floating_ip` (action="set") | ✅ | Floating IP property setting |
| `openstack floating ip show` | `set_floating_ip` (action="show") | ✅ | Floating IP details |
| `openstack floating ip unset` | `set_floating_ip` (action="unset") | ✅ | Floating IP property clearing |
| `openstack floating ip pool list` | `get_floating_ip_pools` | ⚠️ Live unverified | Composite result not independently attributed; available global pool capacity remains unknown |
| `openstack floating ip port forwarding create` | `set_floating_ip_port_forwarding` (action="create") | ⚠️ Live unverified | Implemented; test platform port-forwarding endpoint returns HTTP 404 |
| `openstack floating ip port forwarding delete` | `set_floating_ip_port_forwarding` (action="delete") | ⚠️ Live unverified | Implemented; test platform port-forwarding endpoint returns HTTP 404 |
| `openstack floating ip port forwarding list` | `set_floating_ip_port_forwarding` (action="list") | ⚠️ Live unverified | Implemented; test platform port-forwarding endpoint returns HTTP 404 |
| `openstack floating ip port forwarding set` | `set_floating_ip_port_forwarding` (action="set") | ⚠️ Live unverified | Implemented; test platform port-forwarding endpoint returns HTTP 404 |
| `openstack floating ip port forwarding show` | `set_floating_ip_port_forwarding` (action="show") | ⚠️ Live unverified | Implemented; test platform port-forwarding endpoint returns HTTP 404 |
| `openstack security group list` | `get_security_groups` | ✅ | Scoped reader list completed; default and test groups visible |
| `openstack security group create/delete` | `set_security_groups` | ✅ | Project-owned security groups |
| `openstack port list` | `set_network_ports` (action="list") | ⚠️ Live unverified | Implemented list action requires modification-tool registration; not exercised in this round |
| `openstack port create/delete` | `set_network_ports` | ✅ | Port management |
| `openstack network qos policy list` | `get_network_qos_policies` | ⚠️ Live unverified | Implemented; test platform QoS endpoint returns HTTP 404 |
| `openstack network qos policy create` | `set_network_qos_policies` | ⚠️ Live unverified | Implemented; test platform QoS endpoint returns HTTP 404. Policy containers only; no bandwidth rules |
| `openstack network agent list` | `get_service_status` (includes agents) | ⚠️ Live unverified | Reader service-policy restrictions; partial data is not proof of global health |
| `openstack network agent set` | `set_network_agents` | ✅ | Enable/disable cloud-wide agents; usually admin-only |

### 3. 💾 **Storage (Cinder)**

| OpenStack CLI Command | MCP Tool | Status | Notes |
|---------------------|---------|------|------|
| `openstack volume list` | `get_volume_list` | ✅ | Exactly ten owned volumes per reader; no other test project volume IDs returned |
| `openstack volume show` | `get_volume_list` | ✅ | Listing-based client filtering; no dedicated get_volume_list filter argument |
| `openstack volume create/delete` | `set_volume` | ✅ | Volume creation/deletion |
| `openstack volume set --size` | `set_volume` (action="extend") | ✅ | Positive new_size takes precedence over size; size remains a fallback. A test volume reached the requested size and available state; API acceptance alone is not completion |
| `openstack volume set` (other properties) | — | ❌ Not implemented | set_volume has no modify/update action; do not send this unsupported action |
| `openstack volume type list` | `get_volume_types` | ✅ | Volume type listing |
| `openstack volume type create/delete` | `set_volume_types` | ✅ | Volume type management; usually admin-only |
| `openstack volume snapshot list` | `get_volume_snapshots` | ✅ | Two owned base snapshots per reader; API final states checked |
| `openstack volume snapshot create/delete` | `set_snapshot` | ✅ | Explicit member MCP snapshots reached available and were deleted. Post-action status resolves snapshots instead of reporting an unknown resource type; no restore/I/O claim |
| `openstack backup list` | `get_volume_backups` | ✅ | Three owned available backups per reader; base backup creation used real Cinder APIs |
| `openstack backup create/delete` | `set_volume_backups` | ✅ | Volume backup management |
| `openstack volume transfer request list` | `get_volume_transfers` | ✅ | Request listing only; authorization keys are excluded |
| `openstack server volume list` | `get_server_volumes` | ✅ | Server volume listing |
| `openstack server add/remove volume` | `set_server_volume` / `set_volume` (action="attach"/"detach") | ✅ | Both paths reached in-use then available in both member projects; foreign endpoints rejected; guest I/O not tested |
| `openstack volume group list` | `get_volume_groups` | ✅ | Requires Cinder generic groups (API >= 3.13) |
| `openstack volume group create` | `set_volume_groups` | ✅ | Create/list/show/delete; create requires group_type and volume_types |
| `openstack volume qos list` | `get_volume_qos` | ✅ | Cinder QoS specifications; subject to cloud policy |
| `openstack volume qos create` | `set_volume_qos` | ✅ | Create/list/show/set/delete specifications; no automatic type association |

### 4. 🖼️ **Image (Glance)**

| OpenStack CLI Command | MCP Tool | Status | Notes |
|---------------------|---------|------|------|
| `openstack image list` | `get_image_detail_list` | ✅ | Image listing |
| `openstack image show` | `get_image_detail_list` (filtering) | ✅ | Specific image query |
| `openstack image create` | `set_image` (action="create") | ✅ | Enhanced image creation with min_disk, min_ram, properties |
| `openstack image delete` | `set_image` (action="delete") | ✅ | Image deletion |
| `openstack image set` | `set_image` (action="update") | ✅ | Image property modification |
| `openstack image save` | `set_image` (action="save") | ✅ | Image download |
| `openstack image add project` | `set_image_members` (action="add") | ✅ | Add a project to an image with shared visibility |
| `openstack image member list` | `get_image_members` | ✅ | Image member listing |
| `openstack image member create` | `set_image_members` | ✅ | Image member management |
| `openstack image set --property` | `set_image_metadata` | ✅ | Image metadata |
| `openstack image set --public/private` | `set_image_visibility` | ✅ | Image visibility setting |

### 5. 👥 **Identity (Keystone)**

| OpenStack CLI Command | MCP Tool | Status | Notes |
|---------------------|---------|------|------|
| `openstack user list` | `get_user_list` | ⚠️ Live unverified | Reader denied by Keystone; explicit MCP failure observed; successful listing not validated in this round |
| `openstack user show` | `get_user_list` | ⚠️ Live unverified | Depends on policy-limited user listing; not independently validated for the new readers |
| `openstack user create/delete` | `set_users` | ✅ | Password from a server environment variable; no role grants |
| `openstack project list` | `get_project_details` | ✅ | Project listing |
| `openstack project show` | `get_project_details` (name param) | ✅ | Specific project query |
| `openstack project create/delete` | `set_project` | ✅ | Project management |
| `openstack role list` | `get_role_assignments` | ✅ | Role listing |
| `openstack role assignment list` | `get_role_assignments` | ⚠️ Live unverified | Reader Keystone policy denial; not a successful data lookup |
| `openstack role create/delete` | `set_roles` | ✅ | Role management |
| `openstack domain list` | `get_domains` | ✅ | Subject to Keystone policy |
| `openstack domain create/delete` | `set_domains` | ✅ | Disable explicitly with update before delete |
| `openstack group list` | `get_identity_groups` | ✅ | Subject to Keystone policy |
| `openstack group create/delete` | `set_identity_groups` | ✅ | Group management |
| `openstack service list` | `get_service_status` | ⚠️ Live unverified | Reader service-policy restrictions; partial data is not proof of global health |
| `openstack service create/delete` | `set_services` | ✅ | Service management |
| `openstack endpoint list` | `get_service_status` (includes endpoints) | ⚠️ Live unverified | Reader service-policy restrictions; partial data is not proof of global health |

### 6. 🔥 **Orchestration (Heat)**

| OpenStack CLI Command | MCP Tool | Status | Notes |
|---------------------|---------|------|------|
| `openstack stack list` | `get_heat_stacks` | ✅ | The stack's project ID or Heat self link must match the current project; unknown and foreign owners are excluded. Own and foreign test stacks were checked |
| `openstack stack show` | `get_heat_stacks` | ✅ Partial | Select the target from the returned list; no name/filter parameter. Resource/event/template/output queries use get_heat_stack_details |
| `openstack stack create` | `set_heat_stack` (action="create") | ✅ | Stack creation |
| `openstack stack delete` | `set_heat_stack` (action="delete") | ✅ | Foreign-project deletion rejected; owned stack deletion completed after the ownership change |
| `openstack stack update` | `set_heat_stack` (action="update") | ⚠️ Live unverified | Requires matching stack ownership; owned update after the ownership change has not been live retested |
| `openstack stack suspend/resume` | — | ❌ Not implemented | set_heat_stack supports create, delete and update only |
| `openstack stack resource list` | `get_heat_stack_details` (section="resources") | ✅ | Actual Heat resources |
| `openstack stack event list` | `get_heat_stack_details` (section="events") | ✅ | Owned stack events retrieved after the ownership change |
| `openstack stack template show` | `get_heat_stack_details` (section="template") | ✅ | Owned stack template retrieved after the ownership change |
| `openstack stack output list` | `get_heat_stack_details` (section="outputs") | ✅ | Owned stack outputs retrieved after the ownership change |

### 7. ⚖️ **Load Balancer (Octavia)**

| OpenStack CLI Command | MCP Tool | Status | Notes |
|---------------------|---------|------|------|
| `openstack loadbalancer list` | `get_load_balancer_list` | ⚠️ Live unverified | Implemented; Octavia unavailable in the test platform. Load balancer listing with pagination |
| `openstack loadbalancer show` | `get_load_balancer_details` | ⚠️ Live unverified | Implemented; Octavia unavailable in the test platform. Load balancer detailed information |
| `openstack loadbalancer create` | `set_load_balancer` (action="create") | ⚠️ Live unverified | Implemented; Octavia unavailable in the test platform. Load balancer creation |
| `openstack loadbalancer delete` | `set_load_balancer` (action="delete") | ⚠️ Live unverified | Implemented; Octavia unavailable in the test platform. Load balancer deletion |
| `openstack loadbalancer set` | `set_load_balancer` (action="update") | ⚠️ Live unverified | Implemented; Octavia unavailable in the test platform. Load balancer property update |
| `openstack loadbalancer stats show` | `set_load_balancer` (action="stats") | ⚠️ Live unverified | Implemented; Octavia unavailable in the test platform. Load balancer statistics |
| `openstack loadbalancer status show` | `set_load_balancer` (action="status") | ⚠️ Live unverified | Implemented; Octavia unavailable in the test platform. Load balancer status tree |
| `openstack loadbalancer failover` | `set_load_balancer` (action="failover") | ⚠️ Live unverified | Implemented; Octavia unavailable in the test platform. Load balancer failover |
| `openstack loadbalancer unset` | `set_load_balancer` (action="unset") | ⚠️ Live unverified | Implemented; Octavia unavailable in the test platform. Load balancer property unset |
| **Listener Management** | | | |
| `openstack loadbalancer listener list` | `get_load_balancer_listeners` | ⚠️ Live unverified | Implemented; Octavia unavailable in the test platform. Listener listing for load balancer |
| `openstack loadbalancer listener create` | `set_load_balancer_listener` (action="create") | ⚠️ Live unverified | Implemented; Octavia unavailable in the test platform. Listener creation (HTTP/HTTPS/TCP/UDP) |
| `openstack loadbalancer listener delete` | `set_load_balancer_listener` (action="delete") | ⚠️ Live unverified | Implemented; Octavia unavailable in the test platform. Listener deletion |
| `openstack loadbalancer listener show` | `get_load_balancer_listeners` | ⚠️ Live unverified | Implemented; Octavia unavailable in the test platform. Listener detailed information |
| `openstack loadbalancer listener set` | `set_load_balancer_listener` (action="update") | ⚠️ Live unverified | Implemented; Octavia unavailable in the test platform. Listener property update |
| `openstack loadbalancer listener stats show` | `set_load_balancer_listener` (action="stats") | ⚠️ Live unverified | Implemented; Octavia unavailable in the test platform. Listener statistics |
| `openstack loadbalancer listener unset` | `set_load_balancer_listener` (action="unset") | ⚠️ Live unverified | Implemented; Octavia unavailable in the test platform. Listener property unset |
| **Pool Management** | | | |
| `openstack loadbalancer pool list` | `get_load_balancer_pools` | ⚠️ Live unverified | Implemented; Octavia unavailable in the test platform. Pool listing (all or by listener) |
| `openstack loadbalancer pool create` | `set_load_balancer_pool` (action="create") | ⚠️ Live unverified | Implemented; Octavia unavailable in the test platform. Pool creation with algorithms |
| `openstack loadbalancer pool delete` | `set_load_balancer_pool` (action="delete") | ⚠️ Live unverified | Implemented; Octavia unavailable in the test platform. Pool deletion |
| `openstack loadbalancer pool set` | `set_load_balancer_pool` (action="set") | ⚠️ Live unverified | Implemented; Octavia unavailable in the test platform. Pool property update |
| `openstack loadbalancer pool show` | `get_load_balancer_pools` | ⚠️ Live unverified | Implemented; Octavia unavailable in the test platform. Pool detailed information |
| `openstack loadbalancer pool stats show` | N/A | ❌ Not implemented | No registered tool/action for this CLI operation |
| `openstack loadbalancer pool unset` | N/A | ❌ Not implemented | No registered tool/action for this CLI operation |
| **Member Management** | | | |
| `openstack loadbalancer member list` | `get_load_balancer_pool_members` | ⚠️ Live unverified | Implemented; Octavia unavailable in the test platform. Pool member listing |
| `openstack loadbalancer member create` | `set_load_balancer_pool_member` (action="create") | ⚠️ Live unverified | Implemented; Octavia unavailable in the test platform. Pool member creation |
| `openstack loadbalancer member delete` | `set_load_balancer_pool_member` (action="delete") | ⚠️ Live unverified | Implemented; Octavia unavailable in the test platform. Pool member deletion |
| `openstack loadbalancer member set` | `set_load_balancer_pool_member` (action="set") | ⚠️ Live unverified | Implemented; Octavia unavailable in the test platform. Pool member property update |
| `openstack loadbalancer member show` | `get_load_balancer_pool_members` | ⚠️ Live unverified | Implemented; Octavia unavailable in the test platform. Pool member detailed information |
| `openstack loadbalancer member unset` | N/A | ❌ Not implemented | No registered tool/action for this CLI operation |
| **Health Monitor Management** | | | |
| `openstack loadbalancer healthmonitor list` | `get_load_balancer_health_monitors` | ⚠️ Live unverified | Implemented; Octavia unavailable in the test platform. Health monitor listing |
| `openstack loadbalancer healthmonitor create` | `set_load_balancer_health_monitor` (action="create") | ⚠️ Live unverified | Implemented; Octavia unavailable in the test platform. Health monitor creation |
| `openstack loadbalancer healthmonitor delete` | `set_load_balancer_health_monitor` (action="delete") | ⚠️ Live unverified | Implemented; Octavia unavailable in the test platform. Health monitor deletion |
| `openstack loadbalancer healthmonitor set` | `set_load_balancer_health_monitor` (action="set") | ⚠️ Live unverified | Implemented; Octavia unavailable in the test platform. Health monitor update |
| `openstack loadbalancer healthmonitor show` | `get_load_balancer_health_monitors` | ⚠️ Live unverified | Implemented; Octavia unavailable in the test platform. Health monitor detailed information |
| `openstack loadbalancer healthmonitor unset` | N/A | ❌ Not implemented | No registered tool/action for this CLI operation |
| **L7 Policy Management** | | | |
| `openstack loadbalancer l7policy list` | `get_load_balancer_l7_policies` | ⚠️ Live unverified | Implemented; Octavia unavailable in the test platform. L7 policy listing |
| `openstack loadbalancer l7policy create` | `set_load_balancer_l7_policy` (action="create") | ⚠️ Live unverified | Implemented; Octavia unavailable in the test platform. This management tool supports create/delete only |
| `openstack loadbalancer l7policy delete` | `set_load_balancer_l7_policy` (action="delete") | ⚠️ Live unverified | Implemented; Octavia unavailable in the test platform. L7 policy deletion |
| `openstack loadbalancer l7policy set` | N/A | ❌ Not implemented | No registered tool/action for this CLI operation |
| `openstack loadbalancer l7policy show` | `get_load_balancer_l7_policies` | ⚠️ Live unverified | Implemented; Octavia unavailable in the test platform. L7 policy details |
| `openstack loadbalancer l7policy unset` | N/A | ❌ Not implemented | No registered tool/action for this CLI operation |
| **L7 Rule Management** 🆕 | | | |
| `openstack loadbalancer l7rule list` | `get_load_balancer_l7_rules` | ⚠️ Live unverified | Implemented; Octavia unavailable in the test platform. L7 rule listing |
| `openstack loadbalancer l7rule create` | `set_load_balancer_l7_rule` (action="create") | ⚠️ Live unverified | Implemented; Octavia unavailable in the test platform. L7 rule creation |
| `openstack loadbalancer l7rule delete` | `set_load_balancer_l7_rule` (action="delete") | ⚠️ Live unverified | Implemented; Octavia unavailable in the test platform. L7 rule deletion |
| `openstack loadbalancer l7rule set` | N/A | ❌ Not implemented | No registered tool/action for this CLI operation |
| `openstack loadbalancer l7rule show` | `get_load_balancer_l7_rules` | ⚠️ Live unverified | Implemented; Octavia unavailable in the test platform. L7 rule details |
| `openstack loadbalancer l7rule unset` | N/A | ❌ Not implemented | No registered tool/action for this CLI operation |
| **Amphora Management** 🆕 | | | |
| `openstack loadbalancer amphora list` | `get_load_balancer_amphorae` | ⚠️ Live unverified | Implemented; Octavia unavailable in the test platform. Amphora listing |
| `openstack loadbalancer amphora show` | `set_load_balancer_amphora` (action="show") | ⚠️ Live unverified | Implemented; Octavia unavailable in the test platform. Amphora details |
| `openstack loadbalancer amphora configure` | `set_load_balancer_amphora` (action="configure") | ⚠️ Live unverified | Implemented; Octavia unavailable in the test platform. Amphora configuration |
| `openstack loadbalancer amphora failover` | `set_load_balancer_amphora` (action="failover") | ⚠️ Live unverified | Implemented; Octavia unavailable in the test platform. Amphora failover |
| `openstack loadbalancer amphora delete` | N/A | ❌ | Not supported by OpenStack SDK |
| `openstack loadbalancer amphora stats show` | N/A | ❌ | Not supported by OpenStack SDK |
| **Provider Management** | | | |
| `openstack loadbalancer provider list` | `get_load_balancer_providers` | ⚠️ Live unverified | Implemented; Octavia unavailable in the test platform. Provider listing |
| `openstack loadbalancer provider capability list` | N/A | ❌ Not implemented | No registered tool/action for this CLI operation |
| **Availability Zone Management** 🆕 | | | |
| `openstack loadbalancer availabilityzone list` | `get_load_balancer_availability_zones` | ⚠️ Live unverified | Implemented; Octavia unavailable in the test platform. Availability zone listing |
| `openstack loadbalancer availabilityzone show` | `get_load_balancer_availability_zones` | ⚠️ Live unverified | Implemented; Octavia unavailable in the test platform. Availability zone details |
| `openstack loadbalancer availabilityzone create` | `set_load_balancer_availability_zone` (action="create") | ⚠️ Live unverified | Implemented; Octavia unavailable in the test platform. Availability zone creation |
| `openstack loadbalancer availabilityzone delete` | `set_load_balancer_availability_zone` (action="delete") | ⚠️ Live unverified | Implemented; Octavia unavailable in the test platform. Availability zone deletion |
| `openstack loadbalancer availabilityzone set` | N/A | ❌ Not implemented | No registered tool/action for this CLI operation |
| `openstack loadbalancer availabilityzone unset` | N/A | ❌ Not implemented | No registered tool/action for this CLI operation |
| **Flavor Management** 🆕 | | | |
| `openstack loadbalancer flavor list` | `get_load_balancer_flavors` | ⚠️ Live unverified | Implemented; Octavia unavailable in the test platform. Flavor listing |
| `openstack loadbalancer flavor show` | `get_load_balancer_flavors` | ⚠️ Live unverified | Implemented; Octavia unavailable in the test platform. Flavor details |
| `openstack loadbalancer flavor create` | `set_load_balancer_flavor` (action="create") | ⚠️ Live unverified | Implemented; Octavia unavailable in the test platform. Flavor creation |
| `openstack loadbalancer flavor delete` | `set_load_balancer_flavor` (action="delete") | ⚠️ Live unverified | Implemented; Octavia unavailable in the test platform. Flavor deletion |
| `openstack loadbalancer flavor set` | N/A | ❌ Not implemented | No registered tool/action for this CLI operation |
| `openstack loadbalancer flavor unset` | N/A | ❌ Not implemented | No registered tool/action for this CLI operation |
| **Flavor Profile Management** | | | |
| `openstack loadbalancer flavorprofile list` | N/A | ❌ Not implemented | No registered tool/action for this CLI operation |
| `openstack loadbalancer flavorprofile show` | N/A | ❌ Not implemented | No registered tool/action for this CLI operation |
| `openstack loadbalancer flavorprofile create` | N/A | ❌ Not implemented | No registered tool/action for this CLI operation |
| `openstack loadbalancer flavorprofile set` | N/A | ❌ Not implemented | No registered tool/action for this CLI operation |
| `openstack loadbalancer flavorprofile unset` | N/A | ❌ Not implemented | No registered tool/action for this CLI operation |
| `openstack loadbalancer flavorprofile delete` | N/A | ❌ Not implemented | No registered tool/action for this CLI operation |
| **Quota Management** 🆕 | | | |
| `openstack loadbalancer quota list` | `get_load_balancer_quotas` | ⚠️ Live unverified | Implemented; Octavia unavailable in the test platform. Quota listing |
| `openstack loadbalancer quota show` | `get_load_balancer_quotas` | ⚠️ Live unverified | Implemented; Octavia unavailable in the test platform. Quota details |
| `openstack loadbalancer quota set` | `set_load_balancer_quota` (action="set") | ⚠️ Live unverified | Implemented; Octavia unavailable in the test platform. Quota setting |
| `openstack loadbalancer quota reset` | `set_load_balancer_quota` (action="reset") | ⚠️ Live unverified | Implemented; Octavia unavailable in the test platform. Quota reset |

### 8. 📊 **Monitoring & Logging**

Allocation and measured telemetry are separate. `get_resource_monitoring`,
`get_quota`, and `get_usage_statistics` report flavor allocations, quotas,
capacity, and allocation-hours from Nova. `get_gnocchi_*` tools report observed
time series collected by Ceilometer into Gnocchi. Tool descriptions cross-reference
each other so that requests for utilization, load, or trends use Gnocchi. They
also instruct the model to report an uncollected measured metric as not
collected instead of substituting allocations.

| OpenStack CLI Command | MCP Tool | Status | Notes |
|---------------------|---------|------|------|
| Resource monitoring | `get_resource_monitoring` | ⚠️ Live unverified | Reader physical-capacity policy restrictions; allocations are separate from capacity; no live utilization |
| Service status | `get_service_status` | ⚠️ Live unverified | Reader service-policy restrictions; partial data is not proof of global health |
| Cluster overview | `get_service_status` + `get_resource_monitoring` | ⚠️ Live unverified | Reader physical-capacity policy restrictions; allocations are separate from capacity; no live utilization |
| Service log metadata | `set_service_logs` | Partial | Service listing only; log retrieval is unavailable without a logging backend |
| Resource metadata | `set_metrics` | Partial | Nova/Neutron/Cinder list/summary only; does not call Gnocchi. Use `get_gnocchi_*` for telemetry |
| `gnocchi resource list/search/show/history` | `get_gnocchi_resources` | ✅ | Current-project resources; list, attribute filter, show with metrics map, and history passed live |
| `gnocchi metric list/show` | `get_gnocchi_metrics` | ✅ | List, per-resource details, show by resource + name, and show by metric UUID passed live |
| `gnocchi measures show` | `get_gnocchi_measures` | ✅ | By resource + name and by metric UUID passed live, including start, granularity, resample, refresh, latest-N limit, and `rate:mean` for `cpu`; `memory.usage`, disk, and network measures were read. Unsupported aggregation and missing metric returned failures |
| `gnocchi aggregates` | `get_gnocchi_aggregates` | ✅ | Current-project search is always applied. Passed live: project-wide `cpu` `rate:mean` mean, `top`, `groupby="flavor_name"`, and the `memory.usage`/`memory` ratio expression. Ranking across several resources is unit-tested only because the test project had one instance. A metric UUID owned outside the project returned 404 in expression mode. Mixed modes and missing metrics returned failures with hints. Unfilled gaps are returned as null |
| `gnocchi archive-policy/archive-policy-rule/resource-type list`, `gnocchi capabilities list`, `gnocchi status` | `get_gnocchi_service_info` | ✅ | All five sections returned live with the admin test account; a denied section is reported per section |
| Alarm management | `set_alarms` | ✅ | list/create/show/delete passed live, by name and by ID. Evaluation passed live: `cpu` alarms with `aggregation_method="rate:mean"` reached `ok` and `alarm` as expected, and a `vcpus` alarm reached `alarm`. Aodh accepted alarms for a nonexistent resource and for the default `cpu_util`, which current Ceilometer does not collect; check metrics with `get_gnocchi_metrics` first |
| Compute agents | `set_compute_agents` | ✅ | Compute agent management |
| Usage statistics | `get_usage_statistics` | ✅ | Period compute allocation-hours plus separately labeled current snapshots |

### 9. 📏 **Usage & Quota**

| OpenStack CLI Command | MCP Tool | Status | Notes |
|---------------------|---------|------|------|
| `openstack quota show` | `get_quota` | ✅ | Quota query |
| `openstack quota set` | `set_quota` (action="set") | ✅ | Routes supplied fields to Nova/Neutron/Cinder; partial failures are reported |
| `openstack quota delete` | `set_quota` (action="delete") | ✅ | Resets all three service quotas to defaults; requires modification tools |
| `openstack usage show` | `get_usage_statistics` | ✅ | Current-project Nova simple tenant usage; not monetary charges |
| `openstack limits show` | `get_quota` (includes limits) | ✅ | Limits query |
| Resource allocations | `get_resource_monitoring` | ⚠️ Live unverified | Reader physical-capacity policy restrictions; allocations are separate from capacity; no live utilization |

---

### API prerequisites and result semantics

The feature table marks implemented API paths, not verification against every OpenStack deployment. Service and policy requirements must be checked in the target deployment. A missing service, extension, required microversion, or permission is an operation failure, not an empty successful result.

- **Modification tools:** the MCP server registers `set_*` management tools only when `ALLOW_MODIFY_OPERATIONS=true`. Existing action guards also reject writes when disabled. Dedicated read-only `get_*` tools remain available. API authorization is enforced by the target cloud; agent, user, domain, type and QoS administration may require elevated OpenStack roles.
- **Alarms:** `set_alarms` calls the Keystone catalog's `alarming` endpoint for the configured interface/region. It supports list/create/show/delete of project alarms and creates `gnocchi_resources_threshold` alarms. Aodh, Gnocchi, the specified resource and a collected metric are required. The default metric `cpu_util` is kept for compatibility, but Ceilometer has not produced it since Stein, so such alarms stay `insufficient data`. For CPU alarms, use `metric="cpu"` with `aggregation_method="rate:mean"`; the threshold is CPU nanoseconds per granularity window (percent / 100 × granularity × 10⁹ × vCPUs; 80% of one vCPU over 300 s is `2.4e11`). `metric`, `resource_type`, `aggregation_method`, `granularity`, `evaluation_periods`, and `alarm_actions` can be supplied. An empty action list creates an alarm without notifications. There is no simulation fallback.
- **Usage:** `get_usage_statistics` calls Nova simple tenant usage for the current project. Requires Nova API microversion 2.40 or newer for complete pagination. Date bounds are UTC midnight, start inclusive and end exclusive; start must precede end. `usage_statistics.period_compute` contains paginated Nova allocation-hours, not actual CPU load, billed currency, or network/storage history. Nova accounts using VM lifetime and the latest flavor; stop/pause/resize history is not reconstructed. Existing `compute`, `network`, and `storage` fields are current snapshots, labeled by `snapshot_fields` and `snapshot_timestamp`. An unavailable period API returns failure. A failed snapshot section is reported as partial failure.
- **Capacity:** `get_resource_monitoring` separates flavor allocations from project quota limits and the physical totals of visible hypervisors. Missing physical totals or incomplete flavor allocations return `null`, not invented capacity or zero usage. Physical totals and project allocations have different scopes. This tool does not collect live utilization or trends.
- **Floating IP pools:** `total_ips` is the exact sum of visible subnet allocation ranges; `used_ips` counts visible Floating IP objects. Global `available_ips` is `null`: other projects and non-floating ports may consume addresses that are not visible to the caller.
- **Volume groups:** the cloud must support Cinder generic groups (microversion 3.13 or newer). Create requires an existing `group_type` and comma-delimited `volume_types`. Deletion does not delete member volumes unless `delete_volumes=true` is explicitly supplied. Async creation/deletion responses mean accepted, not finished.
- **Identity and images:** `set_users` reads a new user's password from the server variable named by `password_env`; never put passwords in prompts. It does not grant project roles. Disable a domain explicitly with `set_domains(action="update", enabled=false)` before deleting it. Image member modifications require an image owned by the current project, shared visibility, and appropriate Glance policy; adding a member does not automatically accept the recipient's membership.
- **Telemetry (Gnocchi):** the read-only `get_gnocchi_resources`, `get_gnocchi_metrics`, `get_gnocchi_measures`, `get_gnocchi_aggregates`, and `get_gnocchi_service_info` tools use `gnocchiclient` with the Keystone catalog's `metric` endpoint for the configured interface/region. Ceilometer must be collecting data into Gnocchi; it has no API of its own. Results are limited to resources whose `project_id` is the current project. Metrics are created by the Ceilometer service project, so ownership is checked through the embedded resource. Available metrics depend on deployment. Notification-based metrics such as `vcpus`, `memory`, and `disk.root.size` record flavor sizes. Polled metrics such as `cpu`, `memory.usage`, `disk.device.*`, and `network.*` require a working ceilometer-compute agent and a running instance. `cpu` is cumulative nanoseconds; use `aggregation="rate:mean"` when the archive policy supports it. Current Ceilometer does not produce `cpu_util`. Measures and aggregation methods are limited by each metric's archive policy. `get_gnocchi_aggregates` accepts either structured parameters or an operations expression; both add a current-project resource search, so expression metric references resolve as metric names on matched resources. Arithmetic between metrics returns points only where every operand has data. Gnocchi write operations (measure ingestion, resource/metric/archive policy changes) are not implemented.
- **Logs and telemetry:** `set_service_logs(action="show")` and `set_metrics(action="show")` return explicit unsupported errors. No centralized logging backend is implemented. `set_metrics` list/summary operations expose Nova/Neutron/Cinder resource metadata only; use the Gnocchi tools for telemetry samples.

## Quick Start

This starts the complete local evaluation stack. OpenWebUI can use either
integration path:

```text
Browser → OpenWebUI → MCP-OpenStack-Ops → OpenStack
Browser → OpenWebUI → MCPO (OpenAPI) → MCP-OpenStack-Ops → OpenStack
```

Prerequisites are Git, Docker with the Compose plugin, a reachable OpenStack
environment, and a model provider supported by OpenWebUI. The model should
support reliable native tool calling.

This default path supports an OpenStack deployment whose Identity, Compute,
Network, Block Storage, Image, Placement, and Orchestration APIs are reachable
from the Docker host at one hostname with the configured service ports. If your
cloud uses different hostnames or URL paths per service, check
[OpenStack endpoint topology](#openstack-endpoint-topology) before starting.

| Quick Start default | Value |
| --- | --- |
| OpenStack identity | One account from `.env` |
| Available tools | Read-only; modification tools are hidden |
| HTTP authentication | Disabled |
| Published network | Localhost only |
| MCPO configuration | `mcp-config.json.http.local` |

### 1. Clone and configure

```bash
git clone https://github.com/call518/MCP-OpenStack-Ops.git
cd MCP-OpenStack-Ops
cp .env.example .env
cp mcp-config.json.http mcp-config.json.http.local
chmod 600 mcp-config.json.http.local
openssl rand -hex 32
vi .env
```

In `.env`:

1. Replace `WEBUI_SECRET_KEY` with the generated value.
2. Set the `OS_*` authentication, domain, region, protocol, and service-port
   values for the target OpenStack environment.
3. Keep these local Quick Start defaults:

```dotenv
ALLOW_MODIFY_OPERATIONS=false
MCP_MULTI_USER=false
REMOTE_AUTH_ENABLE=false
REMOTE_SECRET_KEY=
DOCKER_BIND_ADDRESS=127.0.0.1
MCPO_CONFIG_FILE=mcp-config.json.http.local
```

The local MCPO copy contains no credentials in this mode and connects to the MCP
container through the private Compose network. It is ignored by Git, so later
authentication changes do not modify the tracked reference template.
The placeholder Authorization header is ignored while `REMOTE_AUTH_ENABLE=false`.
When enabling Bearer authentication, replace `<REMOTE_SECRET_KEY>` in the local
MCPO copy with the same value configured in `.env`.

### 2. Start the stack

```bash
docker compose up -d
docker compose ps
```

Wait until `mcp-server` is healthy and `mcpo-proxy` and `open-webui` are running.

| Service | Local URL | Purpose |
| --- | --- | --- |
| OpenWebUI | `http://localhost:3000` | Chat interface |
| MCP server | `http://localhost:8000/mcp` | Direct MCP endpoint |
| MCPO docs | `http://localhost:8080/mcp-openstack-ops/docs` | Generated OpenAPI schema and test UI |

If `mcp-server` is unhealthy, inspect its log before continuing:

```bash
docker compose logs mcp-server
```

### 3. Configure OpenWebUI 0.13

Open `http://localhost:3000`, create the first administrator account, and add a
model provider. Use a model with reliable native function calling.

For the shortest first run, choose one provider:

- **OpenAI:** open **Settings → Admin → Connections**, add an OpenAI API
  connection, use `https://api.openai.com/v1`, enter the API key, and save it.
  See the [OpenWebUI OpenAI guide](https://docs.openwebui.com/getting-started/quick-start/connect-a-provider/starting-with-openai/).
- **Ollama on the Docker host:** the Compose configuration already points
  OpenWebUI to `http://host.docker.internal:11434`. Ensure Ollama listens where
  Docker can reach it and select a tool-capable model. See the
  [OpenWebUI Ollama guide](https://docs.openwebui.com/getting-started/quick-start/connect-a-provider/starting-with-ollama/).
- **Another OpenAI-compatible provider or local server:** add its base URL and
  API key under **Settings → Admin → Connections**. When the provider does not
  expose a model list, enter the model ID manually. See the
  [OpenAI-compatible provider guide](https://docs.openwebui.com/getting-started/quick-start/connect-a-provider/starting-with-openai-compatible/).

Confirm that the selected model appears in a new chat before configuring the
MCP integration.

#### 3.1 Add an external tool-server connection

Choose one of the following connections. The direct MCP option has fewer
components; use MCPO when OpenAPI compatibility is required.

**Option A: Direct MCP connection**

Open **Settings → Admin → Tools → Integrations**, find **External Tool
Servers**, and add this connection:

| Field | Value |
| --- | --- |
| Type | `MCP (Streamable HTTP)` |
| Name | `MCP OpenStack Ops Direct` |
| ID | `mcp-openstack-ops-direct` or the generated value |
| URL | `http://mcp-server:8000/mcp` |
| Authentication | `None` |
| Function name filter list | Empty |
| Enabled | On |

Use `Bearer` authentication with the `REMOTE_SECRET_KEY` value instead when
`REMOTE_AUTH_ENABLE=true`. Save the connection and confirm that the connection
check succeeds. See the
[OpenWebUI native MCP guide](https://docs.openwebui.com/features/extensibility/mcp/)
for supported transports and current compatibility notes.

**Option B: MCPO OpenAPI connection**

Open **Settings → Admin → Tools → Integrations**, find **External Tool
Servers**, and add this connection:

| Field | Value |
| --- | --- |
| Type | `OpenAPI` |
| Name | `MCP OpenStack Ops` |
| ID | `mcp-openstack-ops` or the generated value |
| URL | `http://mcpo-proxy:8000/mcp-openstack-ops` |
| Authentication | `None` |
| Function name filter list | Empty |
| Enabled | On |

This is an administrator-managed connection, so OpenWebUI fetches the schema
from its own container. Use the Compose service address above, not
`http://localhost:8080`; inside the OpenWebUI container, `localhost` refers to
OpenWebUI itself. The UI automatically fetches `openapi.json` from the supplied
base URL. Save the connection and confirm that the connection check succeeds.

#### 3.2 Enable Tool Search for the full tool inventory

The OpenStack server plus OpenWebUI's built-in tools can exceed a model
provider's maximum number of function definitions per request. Open
**Settings → Admin → System → Interface**. This is the administrator
**Interface** entry below **Authentication**, not the personal Interface entry
near the top of the settings menu. In the **Chat** section, set:

| Setting | Value |
| --- | --- |
| Tool Search | On |
| Defer Built-in Tools | On |
| Deferral Threshold (characters) | `0` |
| Always Loaded Tools | Empty |

Save the settings. Tool Search keeps the complete tool inventory available but
sends only `search_tools`, `call_tool`, and any explicitly always-loaded tools
to the model until a matching tool is needed. See the
[OpenWebUI tools documentation](https://docs.openwebui.com/features/extensibility/plugin/tools/).

#### 3.3 Configure OpenAI reasoning models

This step applies only to an OpenAI reasoning model that needs both non-default
reasoning effort and function tools. In **Settings → Admin → AI → Connections**,
edit its OpenAI connection and select API type **Responses**. Chat Completions
does not support function tools together with a non-`none` reasoning effort on
newer reasoning models.

With OpenWebUI 0.13.0, leave the chat's **Model controls → Advanced Params →
Reasoning Effort** at **Default**. Selecting **Custom** initializes the field to
`medium` and sends the Chat Completions parameter `reasoning_effort`, which is
not valid in a Responses request. Default omits that override and lets the model
apply its own default effort. To force an explicit Responses value, add this
custom parameter instead:

```text
Name: reasoning
Value: {"effort":"medium"}
```

See the [OpenAI Responses migration guide](https://developers.openai.com/api/docs/guides/migrate-to-responses)
and the [OpenWebUI Open Responses guide](https://docs.openwebui.com/getting-started/quick-start/connect-a-provider/starting-with-open-responses/).

Models and providers without this constraint may keep their normal API type and
reasoning settings.

#### 3.4 Enable the connection in a chat

Open a new chat, select the model, click the **Integrations** icon beside the
message input, and enable `MCP OpenStack Ops` under **Tools**. Global tool-server
connections are not automatically enabled in every chat.

### 4. Verify

Ask the model:

```text
Use mcp-openstack-ops to list the instances in my OpenStack project.
```

A successful response confirms either the OpenWebUI → MCP server → OpenStack
path or the OpenWebUI → MCPO → MCP server → OpenStack path, depending on the
connection selected in the chat. For the MCPO option, the documentation URL
above should also list the generated tool endpoints. For connection failures,
inspect the services used by the selected path:

```bash
docker compose logs mcp-server mcpo-proxy open-webui
```

Common OpenWebUI 0.13 errors:

| Error | Cause | Fix |
| --- | --- | --- |
| `Cannot connect to host localhost` | An administrator connection used a browser/host URL from inside the OpenWebUI container | Use `http://mcp-server:8000/mcp` for direct MCP or `http://mcpo-proxy:8000/mcp-openstack-ops` for MCPO |
| `tools: array too long` | External and built-in tool definitions exceeded the model provider's request limit | Enable Tool Search with threshold `0` |
| `Function tools with reasoning_effort are not supported ... /v1/chat/completions` | Chat Completions received function tools and a non-`none` reasoning effort | Use Responses, or set reasoning effort to `none` if reasoning is not needed |
| `Unsupported parameter: reasoning_effort ... moved to reasoning.effort` | OpenWebUI 0.13.0 sent a custom Reasoning Effort through a Responses connection | Set Reasoning Effort to Default; use custom `reasoning={"effort":"medium"}` only when an explicit value is required |
| MCPO logs `POST http://mcp-server:8000/mcp "404 Not Found"` and `McpError: Session terminated`; `mcp-server` logs `Rejected request with unknown or expired session ID` | MCP sessions exist only in the running `mcp-server` process. After `mcp-server` restarts, MCPO keeps its old session and does not reconnect. `docker compose restart` does not wait for the `mcp-server` health check, so MCPO can connect to the old process just before it stops | With `mcp-server` running, run `docker compose restart mcpo-proxy`. To restart both, use `docker compose up -d --force-recreate mcp-server mcpo-proxy` instead of `docker compose restart`. If a direct MCP client reports the same session error, reconnect it |

### 5. Enable modifications only when needed

Create, update, and delete tools are intentionally absent by default. To enable
them, set `ALLOW_MODIFY_OPERATIONS=true` in `.env` and recreate the MCP path:

```bash
docker compose up -d --force-recreate mcp-server mcpo-proxy
```

OpenStack policy still controls what the configured account may change. For
Bearer authentication, non-local exposure, and custom configuration files, see
[Server Configuration](#server-configuration). For request-scoped user accounts,
see the [multi-user guide](docs/multi-user-guide.md).

Stop the stack without deleting the OpenWebUI data volume with:

```bash
docker compose down
```

### 6. Installation variants and detailed guides

The steps above are the local, single-account evaluation path. Use the matching
guide when your environment differs:

| Environment or requirement | Follow-up guide |
| --- | --- |
| OpenStack APIs use HTTPS with a public or private CA | [HTTPS and private CA setup](#https-and-private-ca-setup) |
| OpenStack services use different hosts or URL paths | [OpenStack endpoint topology](#openstack-endpoint-topology) |
| Host ports `3000`, `8000`, or `8080` are occupied | [Docker Compose environment variables](#environment-variables) |
| MCP is exposed beyond localhost | [Bearer authentication and remote-access precautions](#bearer-token-authentication) |
| Each user supplies a separate OpenStack identity | [Multi-user setup and usage guide](docs/multi-user-guide.md) |
| Separate fixed accounts or projects need separate MCP entries | [Multi-project configuration](#multi-project-configuration) |
| Claude Desktop or Claude Code is the client | [Claude Desktop](#claude-desktop-integration) or [Claude Code](#claude-code-integration) |
| OpenAI reasoning models need explicit reasoning effort | [OpenAI reasoning-model settings](#33-configure-openai-reasoning-models) |

## Claude Desktop Integration

Use `mcp-config.json.stdio` as a reference. Copy it to the ignored local file,
update the local copy, and merge it into Claude Desktop's private configuration:

```bash
cp mcp-config.json.stdio mcp-config.json.stdio.local
chmod 600 mcp-config.json.stdio.local
```

---

## Claude Code Integration

Install Claude Code and start the MCP server in `streamable-http` mode first.
Register the MCP server's `/mcp` URL, not the MCPO/OpenAPI proxy URL. The example
below uses the Docker host port `8000`; replace the host/port for your deployment
and use HTTPS for remote connections. Registration does not start the server.

For the existing single-account mode with `REMOTE_AUTH_ENABLE=true`, enter the
server's `REMOTE_SECRET_KEY` without saving its literal value in shell history:

```bash
read -rsp 'MCP Bearer token: ' OPENSTACK_MCP_TOKEN
echo
export OPENSTACK_MCP_TOKEN

claude mcp add-json --scope user openstack-ops '{"type":"http","url":"http://127.0.0.1:8000/mcp","headers":{"Authorization":"Bearer ${OPENSTACK_MCP_TOKEN}"}}'
claude mcp list
claude
```

Keep `OPENSTACK_MCP_TOKEN` exported in the terminal that launches Claude Code.
`--scope user` saves the registration in your normal user configuration. If server
authentication is disabled, use this registration command instead:

```bash
claude mcp add --transport http --scope user openstack-ops http://127.0.0.1:8000/mcp
```

In Claude Code, check `/mcp` and ask, for example:

```text
Use openstack-ops to list all instances in the project.
```

Remove the registration when no longer needed (this does not stop the server):

```bash
claude mcp remove --scope user openstack-ops
unset OPENSTACK_MCP_TOKEN
```

This Bearer configuration uses the server's configured OpenStack account. For
experimental per-user authentication, see the [multi-user guide](docs/multi-user-guide.md).
See also the [Claude Code MCP documentation](https://code.claude.com/docs/en/mcp).

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
  --multi-user         Use request-local Application Credentials (streamable-http only)
```

### Environment Variables

| Variable | Description | Default | Usage |
|----------|-------------|---------|--------|
| **OpenStack Authentication** |
| `OS_AUTH_HOST` | OpenStack Identity service host | Required | Authentication host address |
| `OS_AUTH_PORT` | OpenStack Identity service port | Required | Authentication port |
| `OS_AUTH_PROTOCOL` | Connection protocol (http or https) | `http` | Use `https` for production with SSL/TLS |
| `OS_CACERT` | SSL CA certificate path for HTTPS | Optional | Required for secure HTTPS connections (e.g., `/etc/ssl/certs/ca.pem`). If not set with HTTPS, SSL verification is disabled (insecure) |
| `OS_USERNAME` | OpenStack username | Required in single-account mode | Unused for multi-user request authentication |
| `OS_PASSWORD` | OpenStack password | Required in single-account mode | Unused for multi-user request authentication |
| `OS_PROJECT_NAME` | OpenStack project name | Required in single-account mode | Multi-user scope comes from each Application Credential |
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
| `OS_HEAT_STACK_PORT` | Heat orchestration service port | `8004` | Heat API endpoint |
| `OS_HEAT_STACK_CFN_PORT` | Heat CloudFormation service port | `18888` | Heat CFN API endpoint (default: 8000, changed to avoid Docker port conflicts) |
| **MCP Server Configuration** |
| `MCP_LOG_LEVEL` | Logging level | `INFO` | Development debugging |
| `ALLOW_MODIFY_OPERATIONS` | Enable modify operations | `false` | Safety control for state modifications |
| `FASTMCP_TYPE` | Transport type | `stdio` | Rarely needed to change |
| `FASTMCP_HOST` | HTTP host address | `127.0.0.1` | For HTTP mode only |
| `FASTMCP_PORT` | HTTP port number | `8080` | For HTTP mode only |
| **Authentication (Optional)** |
| `MCP_MULTI_USER` | Enable request-scoped per-user Application Credential authentication | `false` | Streamable HTTP only; requires HTTPS OpenStack endpoints by default and can be combined with shared Bearer authentication |
| `MCP_MULTI_USER_ALLOW_INSECURE_HTTP` | Allow multi-user OpenStack API requests over HTTP | `false` | Development/testing only; requires `MCP_MULTI_USER=true` and transmits credentials and tokens in plaintext |
| `REMOTE_AUTH_ENABLE` | Enable Bearer token authentication for streamable-http mode | `false` | Production security |
| `REMOTE_SECRET_KEY` | Shared secret for Bearer token authentication | Required when auth enabled | Checked before per-user authentication when both modes are enabled |
| **Docker Compose** |
| `DOCKER_BIND_ADDRESS` | Published-port bind address | `127.0.0.1` | Keep local when HTTP authentication is disabled |
| `DOCKER_EXTERNAL_PORT_OPENWEBUI` | OpenWebUI host port | `3000` | Browser access |
| `DOCKER_EXTERNAL_PORT_MCP_SERVER` | MCP server host port | `8000` | Direct MCP clients |
| `DOCKER_EXTERNAL_PORT_MCPO_PROXY` | MCPO host port | `8080` | OpenAPI proxy and docs |
| `MCPO_CONFIG_FILE` | MCPO configuration mounted by Compose | `mcp-config.json.http.local` | Copy the tracked HTTP template to this ignored local file before starting Compose |

### OpenStack endpoint topology

Single-account and multi-user connections currently construct service URLs from
one `OS_AUTH_HOST`, `OS_AUTH_PROTOCOL`, and the `OS_*_PORT` values. This works
for compact deployments, API gateways, and virtual IPs that expose every listed
service on one host. The server does not currently discover different service
hosts or custom URL paths from the Keystone service catalog.

Before starting, confirm that these URLs are reachable from inside the
`mcp-server` container. If the cloud publishes different service hosts or paths,
place a gateway or reverse proxy at `OS_AUTH_HOST` that maps the configured ports
to those endpoints. Do not proceed by entering only the Keystone hostname; the
MCP server may authenticate successfully and then fail on the first service tool.

`OS_INTERFACE` does not change these explicit endpoint URLs. The current
single-host configuration uses the internal interface convention.

Aodh (`alarming`) and Gnocchi (`metric`) have no `OS_*_PORT` setting. Their
tools use the Keystone catalog endpoint for `OS_INTERFACE` and
`OS_REGION_NAME`, which must also be reachable from the `mcp-server` container.


### HTTPS and private CA setup

For HTTPS OpenStack endpoints signed by a public CA, use the system CA bundle
already present in the container:

```dotenv
OS_AUTH_PROTOCOL=https
OS_CACERT=/etc/pki/tls/certs/ca-bundle.crt
```

For a private CA, the certificate must exist inside the `mcp-server` container;
a host path in `.env` alone is not enough.

Uncomment and replace the CA volume example under `mcp-server` in
`docker-compose.yml`:

```yaml
volumes:
  - /absolute/host/path/openstack-ca.pem:/etc/ssl/certs/openstack-ca.pem:ro
```

Then configure the container path, recreate the MCP path, and check its logs:

```dotenv
OS_AUTH_PROTOCOL=https
OS_CACERT=/etc/ssl/certs/openstack-ca.pem
```

```bash
docker compose up -d --force-recreate mcp-server mcpo-proxy
docker compose logs mcp-server
```

Without `OS_CACERT`, single-account HTTPS disables certificate verification and
is not a secure production configuration. Multi-user mode fails closed unless
HTTPS is enabled, and its full requirements are documented in the
[multi-user guide](docs/multi-user-guide.md).

The tracked `mcp-config.json.*` files are reference templates. Before adding
credentials, copy only the template you need; all matching `.local` files are
ignored by Git:

```bash
cp mcp-config.json.http mcp-config.json.http.local
cp mcp-config.json.multi-user mcp-config.json.multi-user.local
cp mcp-config.json.multi-project mcp-config.json.multi-project.local
cp mcp-config.json.stdio mcp-config.json.stdio.local
chmod 600 mcp-config.json.*.local
```

For MCPO, select the copy in `.env`, for example
`MCPO_CONFIG_FILE=mcp-config.json.multi-user.local`. Point non-Compose clients
to their local copy separately. Never put real credentials in a tracked
template.

---

## 🔒 Project Isolation & Security

### Single Project Scope Operation

**MCP-OpenStack-Ops operates within a strictly defined project scope** determined by the `OS_PROJECT_NAME` environment variable. This provides complete tenant isolation and data privacy in multi-tenant OpenStack environments.

**Key Security Features:**

- **100% Complete Resource Isolation**: All operations are restricted to resources within the specified project with enhanced security validation
- **Zero Cross-tenant Data Leakage**: Advanced project ownership validation prevents access to resources from other projects
- **Multi-layer Security Filtering**: Each service implements intelligent resource filtering by current project ID with additional validation
- **Secure Resource Lookup**: All resource searches use project-scoped lookup with ownership verification
- **Shared Resource Access**: Intelligently includes shared/public resources (networks, images) while maintaining strict security boundaries
- **Cross-Project Access Prevention**: Enhanced protection against accidental operations on similarly-named resources in other projects

**Filtered Resources by Project:**

| Service | Project-Scoped Resources | Notes |
|---------|-------------------------|-------|
| **Identity** | Users (via role assignments), Role assignments | Only users with roles in current project |
| **Compute** | Instances, Flavors (embedded data), Keypairs | All instances within project scope |
| **Image** | Private images (owned), Public/Community/Shared images | Smart filtering prevents zero-image issues |
| **Network** | Networks, Subnets, Security Groups, Floating IPs, Routers | Includes shared/external networks for access |
| **Storage** | Volumes, Snapshots, Backups | All storage resources within project |
| **Orchestration** | Heat Stacks, Stack Resources | All orchestration within project |
| **Load Balancer** | Load Balancers, Listeners, Pools | All load balancing within project |
| **Monitoring** | Resource usage, Project quotas | Project-specific monitoring data |

### Security Validation & Testing

**Project Isolation Security Test**

To verify that project isolation is working correctly, run the included security test:

```bash
# Run project isolation security test
python test_project_isolation.py
```

**Expected Test Results:**
```
🔒 OpenStack Project Isolation Security Test
==================================================
📋 Testing project isolation for: your-project

1️⃣ Testing Connection and Project ID...
✅ Connection successful
✅ Current project ID: abc123-def456-ghi789
✅ Project name 'your-project' matches project ID

2️⃣ Testing Resource Ownership Validation...
✅ Found 5 compute instances
   Instance web-server-01: ✅ Owned
   Instance db-server-01: ✅ Owned
✅ Found 3/8 owned networks
✅ Found 10/10 owned volumes

3️⃣ Testing Service-Level Project Filtering...
✅ Compute service returned 5 instances
✅ Network service returned 3 networks  
✅ Storage service returned 10 volumes

4️⃣ Testing Secure Resource Lookup...
ℹ️  Network 'admin' not found or not accessible in current project
ℹ️  Instance 'demo' not found or not accessible in current project

🎯 Project Isolation Test Results
========================================
✅ All security tests passed!
✅ Project 'your-project' isolation verified
✅ Cross-project access prevention confirmed

🔒 Your OpenStack MCP Server is properly secured!
```

**Security Features Validated:**
- ✅ Project ID verification and matching
- ✅ Resource ownership validation for all services
- ✅ Service-level project filtering
- ✅ Secure resource lookup with cross-project protection
- ✅ Prevention of accidental operations on other projects' resources

### Multi-project configuration

For managing multiple OpenStack projects, deploy multiple MCP server instances with different `OS_PROJECT_NAME` values:

**Example: Managing 3 Projects**

```bash
# Project 1: Production Environment
OS_PROJECT_NAME=production
# ... other config
python -m mcp_openstack_ops --type stdio

# Project 2: Development Environment  
OS_PROJECT_NAME=development
# ... other config  
python -m mcp_openstack_ops --type streamable-http --port 8001

# Project 3: Testing Environment
OS_PROJECT_NAME=testing  
# ... other config
python -m mcp_openstack_ops --type streamable-http --port 8002
```

**Claude Desktop Multi-Project Configuration Example:**

```json
{
  "mcpServers": {
    "openstack-production": {
      "command": "python",
      "args": ["-m", "mcp_openstack_ops", "--type", "stdio"],
      "env": {
        "OS_PROJECT_NAME": "production",
        "OS_USERNAME": "admin",
        "OS_PASSWORD": "your-password",
        "OS_AUTH_HOST": "192.168.35.2"
      }
    },
    "openstack-development": {
      "command": "python", 
      "args": ["-m", "mcp_openstack_ops", "--type", "stdio"],
      "env": {
        "OS_PROJECT_NAME": "development",
        "OS_USERNAME": "admin",
        "OS_PASSWORD": "your-password", 
        "OS_AUTH_HOST": "192.168.35.2"
      }
    },
    "openstack-testing": {
      "command": "python",
      "args": ["-m", "mcp_openstack_ops", "--type", "stdio"], 
      "env": {
        "OS_PROJECT_NAME": "testing",
        "OS_USERNAME": "admin",
        "OS_PASSWORD": "your-password",
        "OS_AUTH_HOST": "192.168.35.2"
      }
    }
  }
}
```

This allows Claude to access each project independently with complete isolation between environments.

**📁 Reference Configuration File:**

A complete multi-project configuration example is available at `mcp-config.json.multi-project`:
- **Production**: Read-only operations for safety (`ALLOW_MODIFY_OPERATIONS=false`)
- **Development**: Full operations enabled (`ALLOW_MODIFY_OPERATIONS=true`) 
- **Testing**: Debug logging enabled (`MCP_LOG_LEVEL=DEBUG`)

```bash
# Preserve the tracked template and customize only the ignored local copy
cp mcp-config.json.multi-project mcp-config.json.multi-project.local
chmod 600 mcp-config.json.multi-project.local
# Point the client to this file, or merge its contents into the client's
# existing private configuration. Do not overwrite an existing client config.
```

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
- Heat stack operations (create, delete, update)

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

## 💬 Example Queries & Usage Patterns

For comprehensive examples of how to interact with this MCP server, including natural language queries and their corresponding tool mappings, see:

**📖 [Example Queries & Usage Patterns](src/mcp_openstack_ops/prompt_template.md#7-example-queries--usage-patterns)**

This section includes:
- 🎯 Cluster overview and status queries
- �️ Instance management operations
- 🌐 Network configuration tasks
- � Storage management workflows
- 🔥 Heat orchestration examples
- ⚖️ Load balancer operations
- � Advanced search patterns
- 📊 Monitoring and troubleshooting
- 🧠 Complex multi-tool query combinations

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
search_instances("web", "name", limit=20, offset=0, case_sensitive=False)
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

---

## 🔐 Security & Authentication

### Bearer Token Authentication

For `streamable-http` mode, this MCP server supports Bearer token authentication to secure remote access. This is especially important when running the server in production environments.

#### Configuration

**Enable Authentication:**

```bash
# In .env file
REMOTE_AUTH_ENABLE=true
REMOTE_SECRET_KEY=my-test-secret-key-12345
```

**Or via CLI:**

```bash
uv run python -m mcp_openstack_ops --type streamable-http --auth-enable --secret-key your-secure-secret-key-here
```

#### Security Levels

1. **stdio mode** (Default): Local-only access, no authentication needed
2. **streamable-http + REMOTE_AUTH_ENABLE=false/undefined**: Remote access without authentication ⚠️ **NOT RECOMMENDED for production**
3. **streamable-http + REMOTE_AUTH_ENABLE=true**: Remote access with Bearer token authentication ✅ **RECOMMENDED for production**
4. **streamable-http + MCP_MULTI_USER=true**: Each request authenticates with the caller's project-scoped Keystone Application Credential and requires HTTPS OpenStack endpoints by default. HTTP is available only for isolated development/testing with `MCP_MULTI_USER_ALLOW_INSECURE_HTTP=true`.
5. **streamable-http + MCP_MULTI_USER=true + REMOTE_AUTH_ENABLE=true**: Each request must pass shared Bearer authentication first and per-user Application Credential authentication second. See the [multi-user guide](docs/multi-user-guide.md).

> **🔒 Default Policy**: `REMOTE_AUTH_ENABLE` and `MCP_MULTI_USER` both default to `false`. A configured `REMOTE_SECRET_KEY` is used only when `REMOTE_AUTH_ENABLE=true`; enabling both modes requires both forms of authentication.

#### Client Configuration

When authentication is enabled, MCP clients must include the Bearer token in the Authorization header:

```json
{
  "mcpServers": {
    "mcp-openstack-ops": {
      "type": "streamable-http",
      "url": "http://your-server:8000/mcp",
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

## 🎯 Recent Improvements & Enhancements

### **🔒 Complete Project Isolation Security Implementation** ✨

**100% Project Isolation Guarantee:**
- ✅ **Multi-layer Security Validation**: Added comprehensive project ownership validation for all resource operations
- ✅ **Enhanced Delete Operation Security**: All delete operations now use secure project-scoped lookup with ownership verification
- ✅ **Create Operation Security**: Resource references during creation (networks, images, etc.) verified for project ownership
- ✅ **Query Security Enhancement**: All list/get operations include explicit project validation with resource ownership checks
- ✅ **Cross-Project Access Prevention**: Advanced protection against accidental operations on similarly-named resources in other projects
- ✅ **Security Test Suite**: Added `test_project_isolation.py` for comprehensive security validation

**Technical Implementation:**
- ✅ **New Security Utilities**: Added `get_current_project_id()`, `validate_resource_ownership()`, `find_resource_by_name_or_id()` functions
- ✅ **Service-Level Security**: Enhanced all service modules (compute, network, storage, etc.) with project ownership validation
- ✅ **Secure Resource Lookup**: Replaced unsafe name-based loops with secure project-scoped resource lookup
- ✅ **Error Message Enhancement**: Improved error messages to clearly indicate project access restrictions

### **Complete Project Scoping Implementation** 

**Enhanced Security & Tenant Isolation:**
- ✅ **All Services Project-Scoped**: Identity, Compute, Network, Storage, Image, Orchestration, Load Balancer, and Monitoring services now filter resources by current project ID
- ✅ **Zero Cross-Tenant Data Leakage**: Automatic filtering at OpenStack SDK level using `current_project_id`
- ✅ **Smart Resource Access**: Intelligent handling of shared/public resources (networks, images) while maintaining security boundaries

### **Fixed Image Service Issues** 🖼️

**Resolved Zero-Image Count Problems:**
- ✅ **Enhanced Image Filtering**: Now includes public, community, shared, and project-owned images
- ✅ **Intelligent Visibility Handling**: Proper handling of different image visibility types
- ✅ **Prevented Empty Results**: Fixed filtering logic that was too restrictive

### **Improved vCPU/RAM Calculation** ⚡

**Fixed Instance Resource Display:**
- ✅ **Embedded Flavor Data Usage**: Uses server.flavor attributes directly, avoiding 404 API errors
- ✅ **Accurate Resource Reporting**: Proper vCPU and RAM values in cluster status reports
- ✅ **Eliminated API Failures**: No more flavor lookup failures causing zero resource values

### **Enhanced Documentation** 📚

**Comprehensive Project Scoping Documentation:**
- ✅ **Multi-Project Management Guide**: Complete setup instructions for managing multiple OpenStack projects
- ✅ **Security & Isolation Details**: Detailed explanation of tenant isolation features
- ✅ **Reference Configuration**: Copy `mcp-config.json.multi-project` to an ignored `.local` file before adding credentials
- ✅ **Updated Environment Variables**: Enhanced `.env.example` with project scoping guidance

---

## 🚀 Adding Custom Tools

This MCP server is designed for easy extensibility. Follow these steps to add your own custom tools:

### Step-by-Step Guide

#### 1. **Add Helper Functions (Optional)**

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

#### 2. **Create Your MCP Tool File**

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

#### 3. **For Modify Operations (Optional)**

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

#### 4. **Update Prompt Template (Recommended)**

Add your tool description to `src/mcp_openstack_ops/prompt_template.md` for better natural language recognition:

```markdown
### **Your Custom Analysis Tool**

### X. **get_your_custom_analysis**
**Purpose**: Brief description of what your tool does
**Usage**: "Show me your custom analysis" or "Get custom analysis for resource_name"
**Features**: Data aggregation, resource monitoring, performance metrics
**Optional**: `target_name` parameter for specific resource analysis
```

#### 5. **Test Your Tool**

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

### Tool Registration System

The MCP server uses automatic tool discovery. When you create a new file in `src/mcp_openstack_ops/tools/`, it's automatically registered through the `register_all_tools()` function in `tools/__init__.py`. No manual import registration needed!

### Safety System

- **Read-only tools**: Use `@mcp.tool()` - always available
- **Modify tools**: Use `@conditional_tool` - only available when `ALLOW_MODIFY_OPERATIONS=true`
- **Connection**: Always use `get_openstack_connection()` for OpenStack API access
- **Project isolation**: All operations are automatically scoped to `OS_PROJECT_NAME`

That's it! Your custom tool is ready to use with natural language queries.

---

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request
