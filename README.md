**English** | [Korean](README.ko.md)

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

## What is MCP-OpenStack-Ops?

MCP-OpenStack-Ops lets an AI assistant such as Claude or a model in OpenWebUI
inspect and operate an OpenStack project in plain language. It is an
[MCP](https://modelcontextprotocol.io/) server that turns requests like "which
instances are stopped?" into OpenStack API calls and returns the results.

- **Read-only by default**: tools that create, change or delete resources are
  not even registered unless you enable them.
- **One project at a time**: each server works inside one OpenStack project and
  checks resource ownership. Operators can opt in to policy-checked
  cross-project reads for some list tools.
- **Broad coverage**: 111 tools (55 read-only, 56 management) for Nova,
  Neutron, Cinder, Glance, Keystone, Heat, Octavia, and Gnocchi/Aodh telemetry.

For an AI-generated walkthrough of the code, see
[![Ask DeepWiki](https://img.shields.io/badge/Ask-DeepWiki-blue)](https://deepwiki.com/call518/MCP-OpenStack-Ops).

## What can you do with it?

Ask questions and give instructions in natural language, for example:

```text
Show me the overall cluster status
Find instances in SHUTOFF state
Show all networks and their subnets
List all volumes and their status
Show the vCPUs and memory allocated to my project and the remaining quota
Show CPU usage of web-01 over the last hour
Stop all instances with name containing 'test'
```

The last request changes resources, so it works only after you enable
modification tools. Telemetry requests need Ceilometer and Gnocchi in the
cloud.

**More requests to try:** [Example queries by area](docs/usage-guide.md#example-queries-by-area)
lists copy-ready requests, with the tools each one uses, for cluster status,
instances, networks, storage, cross-project reads, images, identity, Heat, load
balancers, allocation and quotas, Gnocchi telemetry, Aodh alarms,
troubleshooting, security, batch actions, and multi-tool reports.

**Example: cluster status in Claude Desktop**

![Example Cluster Status](img/screenshot-claude-desktop.png)

**The same project in the OpenStack Dashboard (Epoxy 2025.1)**

![OpenStack Dashboard (Epoxy 2025.1)](img/screenshot-openstack-dashboard.png)

## Quick Start

You need an OpenStack account (Keystone host, project, user name, password)
whose APIs are reachable from the computer that runs the server. Pick one of
the two paths below; both start read-only.

<a id="claude-desktop-integration"></a>

### Option A: Claude Desktop with the extension bundle (fastest)

1. Download `mcp-openstack-ops-<version>.mcpb` from the latest
   [GitHub Release](https://github.com/call518/MCP-OpenStack-Ops/releases).
2. In Claude Desktop, open **Settings > Extensions > Advanced settings >
   Install Extension…** and select the file.
3. Fill in the settings form: Keystone host, project, user name and password
   are required; ports, domains and region are prefilled. Leave **Allow modify
   operations** off.
4. Ask Claude: `List the instances in my OpenStack project.`

Other Claude Desktop setups (`uvx`, a source checkout, the Docker server
through `mcp-remote`, a remote connector) are in the
[Claude Desktop guide](docs/claude-desktop-guide.md).

### Option B: OpenWebUI with Docker Compose

Requirements: Git, Docker with the Compose plugin, and a model provider for
OpenWebUI whose model supports tool calling.

**1. Configure**

```bash
git clone https://github.com/call518/MCP-OpenStack-Ops.git
cd MCP-OpenStack-Ops
cp .env.example .env
cp mcp-config.json.http mcp-config.json.http.local
chmod 600 mcp-config.json.http.local
openssl rand -hex 32   # use the output as WEBUI_SECRET_KEY
vi .env                # set WEBUI_SECRET_KEY and the OS_* values for your cloud
```

**2. Start**

```bash
docker compose up -d
docker compose ps      # wait until mcp-server is healthy
```

This starts OpenWebUI (`http://localhost:3000`), the MCP server
(`http://localhost:8000/mcp`) and MCPO (`http://localhost:8080`).

**3. Connect a model provider**

These steps apply to both the direct MCP connection and MCPO.

1. Open `http://localhost:3000` and create the administrator account.
2. Under **Settings → Admin → Connections**, add an OpenAI connection with URL
   `https://api.openai.com/v1`, **Auth** `Bearer` with your OpenAI API key, and
   **API Type** set to **Chat Completions**, then save it. For another provider,
   see the [OpenWebUI guide](docs/openwebui-guide.md#3-configure-openwebui-013).
3. The Quick Start calls tools through Chat Completions with model reasoning
   turned off, using this default already present in `.env.example`:

   ```dotenv
   DEFAULT_MODEL_PARAMS={"reasoning_effort":"none"}
   ```

   This value requires **API Type: Chat Completions**. With **Responses**,
   OpenWebUI 0.13.0 still sends `reasoning_effort`, and every request fails with
   `Unsupported parameter: 'reasoning_effort'`. If the `open-webui-data` volume
   already exists, set the same value under **Settings → Admin → Models → Model
   Defaults → Model Parameters** because its saved database value takes
   precedence. To keep model reasoning through **Responses** instead, see the
   [OpenWebUI guide](docs/openwebui-guide.md#33-configure-openai-reasoning-models).

**4. Connect the MCP server**

1. Under **Settings → Admin → Tools → Integrations → External Tool Servers**,
   add a connection of type `MCP (Streamable HTTP)` with URL
   `http://mcp-server:8000/mcp` and authentication `None`.
2. Under **Settings → Admin → System → Interface → Chat**, turn on **Tool
   Search** and **Defer Built-in Tools**, and set **Deferral Threshold** to `0`
   so that the full tool list fits the model's limits.
3. In a new chat, enable the connection under **Integrations → Tools** and ask:
   `Use mcp-openstack-ops to list the instances in my OpenStack project.`

> **MCPO is optional.** MCPO is a proxy that exposes the MCP tools as an
> OpenAPI (REST) server; OpenWebUI does not need it to use this server. The
> Compose file starts it so that you can choose either connection. To run
> without it, start only `docker compose up -d mcp-server open-webui`.

The [OpenWebUI guide](docs/openwebui-guide.md) explains the direct and MCPO
connections, every OpenWebUI setting, OpenAI reasoning models, and
troubleshooting.

### Other ways to install

| Setup | Guide |
| --- | --- |
| Claude Desktop with `uvx`, a source checkout, `mcp-remote`, or a remote connector | [Claude Desktop guide](docs/claude-desktop-guide.md) |
| Claude Code | [Claude Code guide](docs/claude-code-guide.md) |
| OpenWebUI through MCPO (OpenAPI) | [OpenWebUI guide](docs/openwebui-guide.md) |
| Each user signs in with their own OpenStack Application Credential (experimental) | [Multi-user guide](docs/multi-user-guide.md) |
| Several projects, HTTPS and private CAs, custom endpoints and ports | [Configuration guide](docs/configuration.md) |

To let the assistant create, change or delete resources, set
`ALLOW_MODIFY_OPERATIONS=true` (or turn on **Allow modify operations** in the
Claude Desktop form) and restart the server. OpenStack policy still decides
what the account may do.

## Features

- ✅ **Project-Scoped Operations**: Every tool enforces the configured `OS_PROJECT_NAME`, validating resource ownership so actions stay inside a single tenant.
- ✅ **Safety-Gated Writes**: Modify (`set_*`) tooling only registers when `ALLOW_MODIFY_OPERATIONS=true`, keeping default deployments read-only and auditable.
- ✅ **Broad Tool Coverage**: 111 tools across compute, networking, storage, images, identity, Heat, Octavia load balancing and telemetry. Project resources are scoped to the active project; cloud-wide administrative APIs remain subject to OpenStack policy.
- ✅ **Bulk & Filtered Actions**: Instance, volume, network, image, snapshot, and keypair managers accept comma-delimited targets or filter criteria to orchestrate bulk changes intentionally.
- ✅ **Post-Action Feedback & Async Guidance**: Management tools report per-resource results, the status read back after the action, and timing notes for asynchronous operations.
- ✅ **Monitoring & Usage Insights**: `get_service_status`, `get_resource_monitoring`, `get_usage_statistics`, and quota tools report service probes, project allocations, separate quota limits, and API-backed compute allocation-hours. These tools do not collect live utilization or trends; read-only `get_gnocchi_*` tools return telemetry time series when Ceilometer and Gnocchi are deployed.
- ✅ **Unified Instance Queries**: The `get_instance` tool consolidates name, ID, status, and free-form search paths with pagination plus summary/detailed modes.
- ✅ **Server Insight & Audit Trail**: Dedicated tools expose server events, hypervisor details, availability zones, quotas, and resource ownership to speed diagnostics.
- ✅ **Load Balancer Management**: Octavia tools cover listeners, pools, members, health monitors, flavors, quotas, and amphora operations with the same safety gates.
- ✅ **Connection & Deployment Flexibility**: Connection caching, configurable service endpoints, Docker packaging, a Claude Desktop extension, and both `stdio`/`streamable-http` transports support proxy/bastion and multi-project setups.

## Safety and security

- **Read-only by default.** Management tools are registered only with
  `ALLOW_MODIFY_OPERATIONS=true`.
- **One project per server.** Resources are filtered by the current project
  and checked for ownership; run one server per project to manage several.
  With `ALLOW_CROSS_PROJECT_READ=true`, some list tools accept
  `all_projects=true`; OpenStack policy decides who may read across projects,
  and modification tools stay project-scoped.
- **Protect HTTP access.** Over `streamable-http`, enable Bearer token
  authentication (`REMOTE_AUTH_ENABLE=true`) and HTTPS before exposing the
  server beyond localhost.

Details: [security guide](docs/security.md) and
[multi-user guide](docs/multi-user-guide.md).

## Authentication support by client

Each server authenticates to OpenStack with either one account's password (the
default) or per-user Application Credentials (multi-user mode, `streamable-http`
only). Support differs by client; for example, the Claude Desktop extension
bundle supports only the password. See
[Authentication support by client](docs/security.md#authentication-support-by-client).

## Compatibility

> ⚠️ **Compatibility Notice**: This MCP server is developed and optimized for **OpenStack Epoxy (2025.1)** as the primary target environment. However, it is compatible with most modern OpenStack releases (Dalmatian, Caracal, Bobcat, etc.) as the majority of APIs remain consistent across versions. Only a few specific API endpoints may require adaptation for full compatibility with older releases.
>
> 🚧 **Coming Soon**: Dynamic multi-version OpenStack API compatibility is actively under development and will be available in upcoming releases, providing seamless support for all major OpenStack deployments automatically.

**Officially Supported Releases:**
- ✅ OpenStack **Epoxy (2025.1)** - Fully tested
- ✅ OpenStack **Dalmatian (2024.2)** - Fully tested

**OpenStackSDK Version Reference:**
| OpenStack Release | Recommended SDK Version | Notes |
|-------------------|------------------------|-------|
| Epoxy (2025.1) | `>=4.1.0,<=4.22.0` | Current default range; `uv.lock` pins 4.22.0. Unit tests pass with 4.1.0, 4.9.0 and 4.22.0 |
| Dalmatian (2024.2) | `>=3.2.0` | Fully compatible |
| Caracal (2024.1) | `>=3.1.0` | May require testing |
| Bobcat (2023.2) | `>=3.0.0` | May require testing |
| Wallaby (2021.1) | `==3.1.1` | Downgrade required |

To change the SDK version for an older release, see
[OpenStack SDK version for older releases](docs/configuration.md#openstack-sdk-version-for-older-releases).

## Documentation

| Guide | Contents |
| --- | --- |
| [Usage guide](docs/usage-guide.md) | [Example queries by area](docs/usage-guide.md#example-queries-by-area), bulk and filtered actions, post-action status, pagination |
| [OpenWebUI guide](docs/openwebui-guide.md) | Docker Compose stack, direct MCP versus MCPO, OpenWebUI settings, troubleshooting |
| [Claude Desktop guide](docs/claude-desktop-guide.md) | Extension bundle, `uvx`, source checkout, `mcp-remote`, remote connector |
| [Claude Code guide](docs/claude-code-guide.md) | Registering the HTTP server in Claude Code |
| [Configuration guide](docs/configuration.md) | Command-line options, environment variables, endpoints, HTTPS, multiple projects, SDK version |
| [Security guide](docs/security.md) | Authentication support by client, project isolation, read-only default, Bearer authentication |
| [Multi-user guide](docs/multi-user-guide.md) | Per-user Application Credential authentication (experimental) |
| [Development guide](docs/development.md) | Tests, live tool checks, adding tools, contributing |
| [TODO](ToDo.md) | Outstanding implementation and live-validation work |
| [OpenStack CLI vs MCP tools mapping](#-openstack-cli-vs-mcp-tools-mapping) | Every tool, its CLI equivalent, and its validation status |
| [Validation evidence](docs/validation.md) | Dates, revisions, conditions and counts of the live and unit-test checks |

---

## 📊 OpenStack CLI vs MCP Tools Mapping

✅ denotes an implemented API path, not certification of every action or
OpenStack deployment. **⚠️ Live unverified** identifies paths without successful
live validation; **❌ Not implemented** identifies unavailable capabilities.
Service availability, permissions, and asynchronous completion affect results.
See [API prerequisites and result semantics](#api-prerequisites-and-result-semantics)
and the [multi-user setup guide](docs/multi-user-guide.md).

**Validation evidence:** the live checks, Claude Code prompt checks and
unit-test results behind the Status values below are recorded in
[docs/validation.md](docs/validation.md).

**Detailed Mapping by Category**

### 1. 🖥️ **Compute (Nova)**

| OpenStack CLI Command | MCP Tool | Status | Notes |
|---------------------|---------|------|------|
| `openstack server list` | `get_instance` | ✅ | Separate reader projects each returned exactly ten owned VMs; bounded lab validation only |
| `openstack server list --all-projects` | `get_instance_details`, `search_instances`, `get_instances_by_status` (`all_projects=true`) | ✅ | Requires `ALLOW_CROSS_PROJECT_READ=true`; OpenStack policy decides access ([cross-project reads](docs/security.md#cross-project-reads)). Rows carry `project_id` and `project_name`. 2026-11-13 targeted check: administrator listed three projects' servers; a `member` received an explicit Nova policy-denial error in fixed-credential and multi-user modes |
| `openstack server show` | `get_instance` | ✅ | Own fixture queries completed; foreign private ID returned no details; no 16-owned-ID batch claim. Each instance reports `boot_source` (`image` or `volume`); summary mode shows a volume-backed instance's image as unknown, and `detailed=true` resolves it from the boot volume. 2026-11-10 OpenStack 2026.1 check (3.7.6): `volume` for volume-backed servers in summary and detailed modes, `image` otherwise; detailed mode resolved the image name from the boot volume |
| `openstack server create` | `set_instance` (action="create") | ✅ | **ENHANCED** - Bulk creation support. Boots the image on the flavor's local disk unless a volume option below is given. 2026-11-10 targeted check: a server reached ACTIVE |
| `openstack server create --boot-from-volume <size>` | `set_instance` (action="create", `boot_from_volume`, `volume_size`) | ✅ | Root disk on a new Cinder volume created from the image; optional `volume_type` and `delete_on_termination`; bulk creation supported. 2026-11-10 targeted check: three servers created in one call reached ACTIVE, each on a bootable 10 GB volume at `/dev/vda`. 2026-11-10 OpenStack 2026.1 check (3.7.6): 1 GB root volumes with `volume_type`; the root volume was deleted with the server, and kept with `delete_on_termination=false` |
| `openstack server create --volume` | `set_instance` (action="create", `boot_volume`) | ✅ | Boots one server from an existing available, bootable volume, without an image. 2026-11-10 OpenStack 2026.1 check (3.7.6): the server reached ACTIVE on that volume; an in-use, non-bootable or missing volume, and two server names, were refused without creating a server |
| `openstack server start/stop/reboot` | `set_instance` | ✅ | Tool schema exposes all actions and `reboot_type`; bulk stop/start final states verified for two test VMs per project, but reboot was not retested in this round |
| `openstack server delete` | `set_instance` (action="delete") | ✅ | Tool schema exposes delete and optional force deletion; bulk deletion with `name_contains` filtering. `force=true` uses openstacksdk `delete_server(force=True)` (previously a non-existent SDK method); 2026-11-10 targeted check: forced deletion removed the server |
| `openstack server backup create` | `set_server_backup` | ✅ | Nova backup action with rotation; asynchronous, no custom metadata |
| `openstack server image create` | `set_instance` (action="snapshot") | ✅ | Accepts optional `snapshot_name` and JSON `metadata`; parameter forwarding is locally tested, not live-retested in this change |
| `openstack server shelve/unshelve` | `set_instance` | ✅ | Actions are exposed in the tool schema; instance shelving was not live-retested in this change |
| `openstack server lock/unlock` | `set_instance` | ✅ | Instance locking. `get_instance_details` reports `locked` from the SDK `is_locked` field (previously always false); 2026-11-10 targeted check: reported true after lock and false after unlock, matching Nova |
| `openstack console url show` | `set_instance` (action="console") | ✅ | Uses the Nova remote-consoles API (the legacy console actions return 404 on current Nova). `console_type`: novnc (default), spice-html5, rdp-html5, serial, webmks, spice-direct, subject to cloud support. 2026-11-10 targeted check: a noVNC URL was returned |
| `openstack server pause/unpause` | `set_instance` | ✅ | Instance pausing |
| `openstack server suspend/resume` | `set_instance` | ✅ | Instance suspension |
| `openstack server resize` | `set_instance` (action="resize") | ✅ | Uses the existing `flavor` parameter as the target flavor; action exposure is locally tested |
| `openstack server resize confirm` | `set_instance` (action="confirm_resize") | ✅ | Resize confirmation |
| `openstack server resize revert` | `set_instance` (action="revert_resize") | ✅ | Resize revert |
| `openstack server rebuild` | `set_instance` (action="rebuild") | ✅ | Uses `image` and supports optional `new_name`, JSON `metadata`, and `preserve_ephemeral`. The image is passed as openstacksdk expects (previously the rebuild failed), and `metadata` is sent only when given because Nova replaces server metadata on rebuild. 2026-11-10 targeted check: rebuilt to ACTIVE and existing metadata was kept |
| `openstack server rescue/unrescue` | `set_instance` | ✅ | Tool schema exposes both actions and optional `rescue_image_id`; not live-retested in this change |
| `openstack server migrate` | `set_server_migration` (action="migrate") | ✅ | Live migration |
| `openstack server evacuate` | `set_server_migration` (action="evacuate") | ⚠️ Live unverified | Server evacuation. `on_shared_storage` is sent only when explicitly true; Nova rejects that field from compute microversion 2.14. 2026-11-10 targeted check: on a single host whose compute service was up, Nova refused the request for that reason, not for a schema error, and the server stayed ACTIVE; an actual evacuation needs a failed host and a second compute host |
| `openstack server migration list` | `set_server_migration` (action="list") | ✅ | Migration listing. With `instance_name`, lists that server's migrations (previously always empty); a listing failure is reported instead of an empty success, and the all-migrations listing reads the SDK `server_id`. 2026-11-10 targeted check: per-server listing returned and an unknown server returned an error |
| `openstack server migration show` | `set_server_migration` (action="show") | ✅ | Migration details |
| `openstack server migration abort` | `set_server_migration` (action="abort") | ✅ | Migration abort |
| `openstack server migration confirm` | `set_server_migration` (action="confirm") | ✅ | Migration confirmation |
| `openstack server migration force complete` | `set_server_migration` (action="force_complete") | ✅ | Force migration completion |
| `openstack server add network` | `set_server_network` (action="add_network") | ✅ | Network attachment. Nova creates the interface port, so removing the network deletes it again. 2026-11-10 targeted check: attached |
| `openstack server remove network` | `set_server_network` (action="remove_network") | ✅ | Network detachment. 2026-11-10 targeted check: no interface port was left, and the network could be deleted afterwards |
| `openstack server add port` | `set_server_network` (action="add_port") | ✅ | Port attachment by port name or ID (a name was previously reported as not found). 2026-11-10 targeted check: attached by name |
| `openstack server remove port` | `set_server_network` (action="remove_port") | ✅ | Port detachment by name or ID; detaching does not delete a port you created. 2026-11-10 targeted check: detached by name and the port was kept |
| `openstack server add floating ip` | `set_server_floating_ip` (action="add") | ✅ | Floating IP association |
| `openstack server remove floating ip` | `set_server_floating_ip` (action="remove") | ✅ | Floating IP disassociation |
| `openstack server add fixed ip` | `set_server_fixed_ip` (action="add") | ✅ | Fixed IP addition through a new interface whose port Nova creates. 2026-11-10 targeted check: an address from the requested network was assigned |
| `openstack server remove fixed ip` | `set_server_fixed_ip` (action="remove") | ✅ | Detaches the whole interface that holds the address, which can be the primary interface. 2026-11-10 targeted check: removed and no interface port was left |
| `openstack server add security group` | `set_server_security_group` (action="add") | ✅ | Security group addition |
| `openstack server remove security group` | `set_server_security_group` (action="remove") | ✅ | Security group removal |
| `openstack server add volume` | `set_server_volume` (action="attach") | ✅ | Member attach reached in-use via set_server_volume; guest I/O not tested. The multiattach precheck reads the SDK `is_multiattach` field. 2026-11-10 targeted check (administrator): reached in-use |
| `openstack server remove volume` | `set_server_volume` (action="detach") | ✅ | Member detach reached available via set_server_volume. 2026-11-10 targeted check (administrator): reached available |
| `openstack server set` | `set_server_properties` (action="set") | ✅ | Server property setting |
| `openstack server unset` | `set_server_properties` (action="unset") | ✅ | Server property unsetting |
| `openstack server dump create` | `set_server_dump` | ❌ Unsupported | Returns an explicit unsupported result; no dump is created |
| `openstack server event list` | `get_server_events` | ✅ | Pass the server name or UUID via `instance_name`, not `server_id`. The action list has no completion time; set `include_event_details=true` to fetch per-action event results and derive the latest finish time. Detailed lookup is capped at 10 actions. Event visibility follows Nova policy |
| `openstack server group list` | `get_server_groups` | ✅ | Server group listing. Reads `member_ids` and, from compute microversion 2.64, `policy` instead of `policies`; a listing failure is reported instead of an empty list. 2026-11-10 targeted check: listed with its policy |
| `openstack server group list --all-projects` | `get_server_groups` (`all_projects=true`) | ✅ | Requires `ALLOW_CROSS_PROJECT_READ=true`; OpenStack policy decides access. Rows carry `project_id` and `project_name`. 2026-11-14 targeted check: administrator listed another project's server group; a `member` received only its own with `scope.warning` |
| `openstack server group create/delete` | `set_server_group` | ✅ | Server group management. 2026-11-10 targeted check: create and show reported the policy and members, then the group was deleted |
| `openstack flavor list` | `set_flavor` (action="list") | ✅ | Requires modification tools to be enabled for registration |
| `openstack flavor create/delete` | `set_flavor` | ✅ | Flavor management |
| `openstack keypair list` | `get_keypair_list` | ✅ | Empty scoped read completed; member keypair creation/deletion read-back tested separately |
| `openstack keypair create/delete` | `set_keypair` | ✅ | Explicit member MCP create/delete read-back passed; no successful Claude write workflow claimed |
| `openstack hypervisor list` | `get_hypervisor_details` | ✅ | Administrator lookup verified; missing per-host capacity and incomplete totals are null, not zero. Global enhanced statistics remain separate; when `/os-hypervisors/statistics` is unavailable (removed at compute microversion 2.88), `enhanced_stats_note` explains why. That note is unit-tested only; in the 2026-11-10 targeted check the statistics API still returned data |
| `openstack availability zone list` | `get_availability_zones` | ✅ | Compute/Cinder availability reads the SDK state mapping; missing availability is null. Actual available zones verified |

### 2. 🌐 **Network (Neutron)**

| OpenStack CLI Command | MCP Tool | Status | Notes |
|---------------------|---------|------|------|
| `openstack network list` | `get_network_details` | ✅ | Two owned private networks plus one policy-visible shared external network per reader; no other test project private networks |
| `openstack network list` (administrator, every project) | `get_network_details` (`all_projects=true`) | ✅ | Requires `ALLOW_CROSS_PROJECT_READ=true`. Neutron has no all-projects flag and never denies a list; it returns what the credential can see, so a result without another project's unshared resource carries `scope.warning`. Only with the default `network_name`; other projects' shared and external networks do not count. 2026-11-13 targeted check: administrator listed three projects' networks; a `member` received its own and the shared external network with the warning |
| `openstack network show` | `get_network_details` (network_name) | ✅ | Foreign-ID negative checked. A name that matches nothing returns an explicit error (previously an empty success). 2026-11-10 targeted check (administrator): named lookup returned the network and a missing name returned the error; a dual-project positive lookup by reader roles is still not asserted |
| `openstack network create` | `set_networks` (action="create") | ✅ | Default mtu=0 omits the wire field: backend MTU 1450 verified; explicit 1400 retained in both member projects |
| `openstack network delete` | `set_networks` (action="delete") | ✅ | Both default/explicit-MTU test networks removed through actual TCP MCP, API absence confirmed |
| `openstack network set` | `set_networks` (action="update") | ✅ | **ENHANCED** - Bulk updates |
| `openstack subnet list` | `get_network_details` (includes subnets) | ✅ | Owned and shared external network subnets returned; three visible subnets per test reader |
| `openstack subnet create/delete` | `set_subnets` | ✅ | Member TCP MCP subnet create read back; deletion allowed parent network removal in both projects |
| `openstack router list` | `get_routers` | ⚠️ Live unverified | Only part of composite error requests in this round; no independent reader result attribution |
| `openstack router list` (administrator, every project) | `get_routers` (`all_projects=true`) | ✅ | Requires `ALLOW_CROSS_PROJECT_READ=true`. Neutron has no all-projects flag and never denies a list; it returns what the credential can see, so a result without another project's unshared resource carries `scope.warning`. 2026-11-13 targeted check: administrator listed routers of two projects; a `member` received only its own router with the warning |
| `openstack router create/delete` | `set_routers` | ✅ | Project-owned routers; attached interfaces are not removed automatically |
| `openstack floating ip list` | `get_floating_ips` | ✅ | Floating IP listing. A failed query returns an error instead of a placeholder address. 2026-11-10 targeted check: listed |
| `openstack floating ip list` (administrator, every project) | `get_floating_ips` (`all_projects=true`) | ✅ | Requires `ALLOW_CROSS_PROJECT_READ=true`. Neutron has no all-projects flag and never denies a list; it returns what the credential can see, so a result without another project's unshared resource carries `scope.warning`. 2026-11-13 targeted check: administrator listed floating IPs of two projects; a `member` received only its own with the warning |
| `openstack floating ip create` | `set_floating_ip` (action="create") | ✅ | Floating IP creation. `description`, `port_id` and `floating_ip_address` are forwarded (previously dropped). 2026-11-10 targeted check: created with its description; `port_id` and `floating_ip_address` on create were not live-tested |
| `openstack floating ip delete` | `set_floating_ip` (action="delete") | ✅ | Floating IP deletion. 2026-11-10 targeted check: released |
| `openstack floating ip set` | `set_floating_ip` (action="set") | ✅ | Floating IP property setting |
| `openstack floating ip show` | `set_floating_ip` (action="show") | ✅ | Floating IP details. 2026-11-10 targeted check: shown by ID |
| `openstack floating ip unset` | `set_floating_ip` (action="unset") | ❌ Limitation | The tool exposes no parameter that selects what to unset, so this action always returns an error. Use `set` or `disassociate` |
| `openstack floating ip pool list` | `get_floating_ip_pools` | ✅ | Available global pool capacity remains unknown (`available_ips=null`). A failed query returns an error instead of a placeholder pool. 2026-11-10 targeted check: the external network pool was listed |
| `openstack floating ip port forwarding create` | `set_floating_ip_port_forwarding` (action="create") | ⚠️ Live unverified | Implemented; test platform port-forwarding endpoint returns HTTP 404 |
| `openstack floating ip port forwarding delete` | `set_floating_ip_port_forwarding` (action="delete") | ⚠️ Live unverified | Implemented; test platform port-forwarding endpoint returns HTTP 404 |
| `openstack floating ip port forwarding list` | `set_floating_ip_port_forwarding` (action="list") | ⚠️ Live unverified | Implemented; test platform port-forwarding endpoint returns HTTP 404 |
| `openstack floating ip port forwarding set` | `set_floating_ip_port_forwarding` (action="set") | ⚠️ Live unverified | Implemented; test platform port-forwarding endpoint returns HTTP 404 |
| `openstack floating ip port forwarding show` | `set_floating_ip_port_forwarding` (action="show") | ⚠️ Live unverified | Implemented; test platform port-forwarding endpoint returns HTTP 404 |
| `openstack security group list` | `get_security_groups` | ✅ | Scoped reader list completed; default and test groups visible. A failed query returns an error instead of a placeholder `default` group |
| `openstack security group list --all-projects` | `get_security_groups` (`all_projects=true`) | ✅ | Requires `ALLOW_CROSS_PROJECT_READ=true`. Neutron has no all-projects flag and never denies a list; it returns what the credential can see, so a result without another project's unshared resource carries `scope.warning`. Rows carry `shared`. 2026-11-13 targeted check: administrator listed three projects' groups, including Octavia's in the `service` project; a `member` received only its own with the warning |
| `openstack security group create/delete` | `set_security_groups` | ✅ | Project-owned security groups |
| `openstack security group rule create/delete` | `set_security_group_rules` | ⚠️ Live unverified | Implemented for project-owned groups. Create requires an explicit CIDR or project-owned remote group; delete verifies the rule belongs to the selected group. Not live-tested in this change |
| `openstack port list` | `set_network_ports` (action="list") | ⚠️ Live unverified | Implemented list action requires modification-tool registration; not exercised in this round |
| `openstack port create/delete` | `set_network_ports` | ✅ | Port management |
| `openstack network qos policy list` | `get_network_qos_policies` | ⚠️ Live unverified | Implemented; test platform QoS endpoint returns HTTP 404 |
| `openstack network qos policy create` | `set_network_qos_policies` | ⚠️ Live unverified | Implemented; test platform QoS endpoint returns HTTP 404. Policy containers only; no bandwidth rules |
| `openstack network agent list` | `get_service_status` (includes agents) | ⚠️ Live unverified | Reader service-policy restrictions; partial data is not proof of global health. 2026-11-10 targeted check returned agents as administrator only |
| `openstack network agent set` | `set_network_agents` | ✅ | Enable/disable cloud-wide agents; usually admin-only |

### 3. 💾 **Storage (Cinder)**

When the Block Storage service is not deployed, the Cinder volume, snapshot,
type, backup, group, QoS, transfer and server-volume paths report an explicit
"Block Storage (Cinder) service is not available" error with endpoint URLs
redacted. This was checked live on OpenStack 2026.1 without Cinder with
release 3.7.3 (see [validation](docs/validation.md)); the storage code is
unchanged since.

| OpenStack CLI Command | MCP Tool | Status | Notes |
|---------------------|---------|------|------|
| `openstack volume list` | `get_volume_list` | ✅ | Exactly ten owned volumes per reader; no other test project volume IDs returned. `multiattach` and `source_volid` read the SDK `is_multiattach` and `source_volume_id` fields. 2026-11-10 targeted check: listed with those fields |
| `openstack volume list --all-projects` | `get_volume_list` (`all_projects=true`) | ✅ | Requires `ALLOW_CROSS_PROJECT_READ=true`. Cinder narrows an unauthorized request to the caller's project instead of denying it, so a current-project-only result carries `scope.warning`. 2026-11-13 targeted check: administrator listed two projects' volumes; a `member` received only its own volume with the warning |
| `openstack volume show` | `get_volume_list` | ✅ | Listing-based client filtering; no dedicated get_volume_list filter argument |
| `openstack volume create/delete` | `set_volume` | ✅ | Volume creation/deletion. 2026-11-10 targeted check: a 1 GB volume reached available and two volumes were deleted |
| `openstack volume set --size` | `set_volume` (action="extend") | ✅ | Positive new_size takes precedence over size; size remains a fallback. A test volume reached the requested size and available state; API acceptance alone is not completion |
| `openstack volume set` (other properties) | — | ❌ Not implemented | set_volume has no modify/update action; do not send this unsupported action |
| `openstack volume type list` | `get_volume_types` | ✅ | Volume type listing. A failed query returns an error instead of a placeholder `standard` type. 2026-11-10 targeted check: listed |
| `openstack volume type create/delete` | `set_volume_types` | ✅ | Volume type management; usually admin-only |
| `openstack volume snapshot list` | `get_volume_snapshots` | ✅ | Two owned base snapshots per reader; API final states checked |
| `openstack volume snapshot list --all-projects` | `get_volume_snapshots` (`all_projects=true`) | ✅ | Requires `ALLOW_CROSS_PROJECT_READ=true`; narrowed results carry `scope.warning` as for volumes. 2026-11-13 targeted check: administrator listed another project's snapshot; a `member` received only its own snapshot with the warning |
| `openstack volume snapshot create/delete` | `set_snapshot` | ✅ | Explicit member MCP snapshots reached available and were deleted. Post-action status resolves snapshots instead of reporting an unknown resource type; no restore/I/O claim. 2026-11-10 targeted check (administrator): reached available and was deleted |
| `openstack backup list` | `get_volume_backups` | ✅ | Three owned available backups per reader; base backup creation used real Cinder APIs |
| `openstack volume backup list --all-projects` | `get_volume_backups` (`all_projects=true`) | ✅ | Requires `ALLOW_CROSS_PROJECT_READ=true`. Cinder narrows an unauthorized request to the caller's project and shows owner projects only to administrators, so a result without visible owners carries its own `scope.warning`. 2026-11-14 targeted check: administrator listed another project's backup with its project; a `member` received its own backup without an owner and the warning |
| `openstack backup create/delete` | `set_volume_backups` | ✅ | Volume backup management. 2026-11-10 targeted check: a backup reached available and was deleted |
| `openstack volume backup restore` | `set_volume_backups` (action="restore") | ✅ | Restores to a new volume named by `volume_name`, or to `volume_id`. Works with both the `volume_id=` and the `volume=` (openstacksdk 4.14+) restore signatures. 2026-11-10 targeted check (openstacksdk 4.22.0): restored to a new volume that reached available; restoring into an existing volume was not tested |
| `openstack volume transfer request list` | `get_volume_transfers` | ✅ | Request listing only; authorization keys are excluded |
| `openstack server volume list` | `get_server_volumes` | ✅ | Server volume listing. A server that does not exist returns an explicit error (previously an empty success). 2026-11-10 targeted check: listed the attached volume; a missing server returned the error |
| `openstack server add/remove volume` | `set_server_volume` / `set_volume` (action="attach"/"detach") | ✅ | Both paths reached in-use then available in both member projects; foreign endpoints rejected; guest I/O not tested |
| `openstack volume group list` | `get_volume_groups` | ✅ | Requires Cinder generic groups (API >= 3.13) |
| `openstack volume group list --all-projects` | `get_volume_groups` (`all_projects=true`) | ✅ | Requires `ALLOW_CROSS_PROJECT_READ=true`. Cinder narrows an unauthorized request to the caller's project and shows owner projects only to administrators, so a result without visible owners carries its own `scope.warning`. Owners are read at microversion 3.58. 2026-11-14 targeted check: administrator listed another project's group with its project; a `member` received its own group without an owner and the warning |
| `openstack volume group create` | `set_volume_groups` | ✅ | Create/list/show/delete; create requires group_type and volume_types |
| `openstack volume qos list` | `get_volume_qos` | ✅ | Cinder QoS specifications; subject to cloud policy |
| `openstack volume qos create` | `set_volume_qos` | ✅ | Create/list/show/set/delete specifications; no automatic type association |

### 4. 🖼️ **Image (Glance)**

| OpenStack CLI Command | MCP Tool | Status | Notes |
|---------------------|---------|------|------|
| `openstack image list` | `get_image_detail_list` | ✅ | Image listing. A failed query returns an error instead of an empty list. 2026-11-10 targeted check: listed |
| `openstack image list` (administrator, every project) | `get_image_detail_list` (`all_projects=true`) | ✅ | Requires `ALLOW_CROSS_PROJECT_READ=true`. Glance has no all-projects flag and returns other projects' private images only to administrators, while public images are visible to everyone; a result without another project's non-public image carries `scope.warning`. 2026-11-14 targeted check: administrator listed images of three projects; a `member` received its own and public images with the warning |
| `openstack image show` | `get_image_detail_list` (filtering) | ✅ | Specific image query |
| `openstack image create` | `set_image` (action="create") | ✅ | Enhanced image creation with min_disk, min_ram, properties |
| `openstack image delete` | `set_image` (action="delete") | ✅ | Image deletion |
| `openstack image set` | `set_image` (action="update") | ✅ | Image property modification |
| `openstack image save` | — | ❌ Not implemented | `set_image` supports create, delete, update and list only; there is no download action |
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
| `openstack project list` | `get_project_details` (`all_projects=true`) | ✅ | Without `all_projects`, only the current project with its resource counts. With `all_projects=true` and `ALLOW_CROSS_PROJECT_READ=true`, a summary of every project Keystone policy allows. 2026-11-13 targeted check: administrator listed three projects; a `member` received an explicit Keystone policy-denial failure |
| `openstack project show` | `get_project_details` (name param) | ✅ | Without `all_projects`, only the current project. With `all_projects=true` and a name or ID that matches one project, that project's details and resource counts, including another project's. 2026-11-13 targeted check: administrator's counts for two other projects matched direct API counts; a `member` received the Keystone policy-denial failure |
| `openstack project create/delete` | `set_project` | ✅ | Project management |
| `openstack role list` | `get_role_assignments` | ✅ | Role listing |
| `openstack role assignment list` | `get_role_assignments` | ✅ | A failed query returns an error instead of a placeholder assignment. 2026-11-10 targeted check: listed as administrator; reader roles were denied by Keystone policy in an earlier round |
| `openstack role create` | `set_roles` (action="create") | ✅ | Role creation; `set_roles` also lists roles |
| `openstack role delete` | — | ❌ Not implemented | `set_roles` supports list and create only |
| `openstack domain list` | `get_domains` | ✅ | Subject to Keystone policy |
| `openstack domain create/delete` | `set_domains` | ✅ | Disable explicitly with update before delete |
| `openstack group list` | `get_identity_groups` | ✅ | Subject to Keystone policy |
| `openstack group create/delete` | `set_identity_groups` | ✅ | Group management |
| `openstack service list` | `get_service_status` | ⚠️ Live unverified | Reader service-policy restrictions; partial data is not proof of global health. Compute and volume service zones read the SDK `availability_zone` field (previously always `unknown`); 2026-11-10 targeted check confirmed this as administrator only |
| `openstack service list` (Keystone catalog) | `set_services` (action="list") | ✅ | Reads the SDK `is_enabled` field (previously every service showed enabled). 2026-11-10 targeted check: enabled flags matched Keystone |
| `openstack service create/delete` | — | ❌ Not implemented | `set_services` supports list only |
| `openstack endpoint list` | `get_service_status` (includes endpoints) | ⚠️ Live unverified | Reader service-policy restrictions; partial data is not proof of global health |

### 6. 🔥 **Orchestration (Heat)**

| OpenStack CLI Command | MCP Tool | Status | Notes |
|---------------------|---------|------|------|
| `openstack stack list` | `get_heat_stacks` | ✅ | The stack's project ID or Heat self link must match the current project; unknown and foreign owners are excluded. Own and foreign test stacks were checked. `owner` reads the SDK `owner_id` field, and a failed query returns an error instead of a placeholder stack. 2026-11-10 targeted check: an owned test stack was listed |
| `openstack stack list --all-projects` | `get_heat_stacks` (`all_projects=true`) | ✅ | Requires `ALLOW_CROSS_PROJECT_READ=true`; sends Heat's `global_tenant` query. Heat's default `stacks:global_index` policy is `deny_everybody`, so the request returns a policy-denial error even for administrators unless the operator changes that policy. 2026-11-14 targeted check: administrator and `member` both received the policy-denial error; after `stacks:global_index` was allowed for a dedicated role, a `member` with that role listed stacks of two projects |
| `openstack stack show` | `get_heat_stacks` | ✅ Partial | Select the target from the returned list; no name/filter parameter. Resource/event/template/output queries use get_heat_stack_details |
| `openstack stack create` | `set_heat_stack` (action="create") | ✅ | Stack creation. 2026-11-10 targeted check: reached CREATE_COMPLETE |
| `openstack stack delete` | `set_heat_stack` (action="delete") | ✅ | Foreign-project deletion rejected; owned stack deletion completed after the ownership change. 2026-11-10 targeted check: deleted |
| `openstack stack update` | `set_heat_stack` (action="update") | ✅ | Requires matching stack ownership. The result reads the SDK `status` field (previously the tool reported a failure after Heat accepted the update). 2026-11-10 targeted check: an owned stack update was reported as accepted and reached UPDATE_COMPLETE |
| `openstack stack suspend/resume` | — | ❌ Not implemented | set_heat_stack supports create, delete and update only |
| `openstack stack resource list` | `get_heat_stack_details` (section="resources") | ✅ | Actual Heat resources |
| `openstack stack event list` | `get_heat_stack_details` (section="events") | ✅ | Owned stack events retrieved after the ownership change |
| `openstack stack template show` | `get_heat_stack_details` (section="template") | ✅ | Owned stack template retrieved after the ownership change |
| `openstack stack output list` | `get_heat_stack_details` (section="outputs") | ✅ | Owned stack outputs retrieved after the ownership change |

### 7. ⚖️ **Load Balancer (Octavia)**

The Octavia tools read the openstacksdk attribute names (`is_admin_state_up`,
`is_enabled`, the listener `load_balancer_id`, the L7 rule `rule_value` and
plural quota fields), list pool members with `members(pool)`, create L7 rules
with `create_l7_rule(policy, ...)`, and filter listeners by load balancer. These
corrections are unit-tested against real openstacksdk resource objects only;
Octavia was not available in any live test cloud.

| OpenStack CLI Command | MCP Tool | Status | Notes |
|---------------------|---------|------|------|
| `openstack loadbalancer list` | `get_load_balancer_list` | ⚠️ Live unverified | Implemented; Octavia unavailable in the test platform. Load balancer listing with pagination |
| `openstack loadbalancer list` (administrator, every project) | `get_load_balancer_list` (`all_projects=true`) | ✅ | Requires `ALLOW_CROSS_PROJECT_READ=true`. Octavia narrows an unauthorized request to the caller's project, so a current-project-only result carries `result.scope.warning`; the scope covers every page. 2026-11-14 targeted check: administrator listed load balancers of two projects; a `member` received only its own with the warning |
| `openstack loadbalancer show` | `get_load_balancer_details` | ✅ | 2026-11-12 targeted Octavia read check passed. Load balancer detailed information; pools are matched to listeners from each pool's `listeners` references |
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
| `openstack loadbalancer pool list` | `get_load_balancer_pools` | ✅ | 2026-11-12 targeted Octavia read check passed. Pool listing (all or by listener); reports `listener_ids`, `loadbalancer_ids` and `health_monitor_id` from the Octavia response |
| `openstack loadbalancer pool create` | `set_load_balancer_pool` (action="create") | ⚠️ Live unverified | Implemented; Octavia unavailable in the test platform. Pool creation with algorithms |
| `openstack loadbalancer pool delete` | `set_load_balancer_pool` (action="delete") | ⚠️ Live unverified | Implemented; Octavia unavailable in the test platform. Pool deletion |
| `openstack loadbalancer pool set` | `set_load_balancer_pool` (action="set") | ⚠️ Live unverified | Implemented; Octavia unavailable in the test platform. Pool property update |
| `openstack loadbalancer pool show` | `get_load_balancer_pools` | ✅ | 2026-11-12 targeted Octavia read check passed. Pool detailed information, including `listener_ids`, `loadbalancer_ids` and `health_monitor_id` |
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
| `openstack loadbalancer healthmonitor list` | `get_load_balancer_health_monitors` | ✅ | 2026-11-12 targeted Octavia read check passed. Health monitor listing (all or by pool); reports `pool_ids` from the Octavia response |
| `openstack loadbalancer healthmonitor create` | `set_load_balancer_health_monitor` (action="create") | ⚠️ Live unverified | Implemented; Octavia unavailable in the test platform. Health monitor creation |
| `openstack loadbalancer healthmonitor delete` | `set_load_balancer_health_monitor` (action="delete") | ⚠️ Live unverified | Implemented; Octavia unavailable in the test platform. Health monitor deletion |
| `openstack loadbalancer healthmonitor set` | `set_load_balancer_health_monitor` (action="set") | ⚠️ Live unverified | Implemented; Octavia unavailable in the test platform. Health monitor update |
| `openstack loadbalancer healthmonitor show` | `get_load_balancer_health_monitors` | ✅ | 2026-11-12 targeted Octavia read check passed. Health monitor detailed information, including `pool_ids` |
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
collected instead of substituting allocations. When the Keystone catalog has no
metric endpoint, the `get_gnocchi_*` tools report "Metric service (Gnocchi) is
not available in this cloud" (checked live on OpenStack 2026.1).

| OpenStack CLI Command | MCP Tool | Status | Notes |
|---------------------|---------|------|------|
| Resource monitoring | `get_resource_monitoring` | ⚠️ Live unverified | Reader physical-capacity policy restrictions; allocations are separate from capacity; no live utilization |
| Service status | `get_service_status` | ⚠️ Live unverified | Reader service-policy restrictions; partial data is not proof of global health |
| Cluster overview | `get_service_status` + `get_resource_monitoring` | ⚠️ Live unverified | Reader physical-capacity policy restrictions; allocations are separate from capacity; no live utilization |
| Service log metadata | `set_service_logs` | Partial | Service listing only; log retrieval is unavailable without a logging backend. Network agents are listed from the SDK `is_admin_state_up` field (previously omitted); 2026-11-10 targeted check: listed with network agents |
| Resource metadata | `set_metrics` | Partial | Nova/Neutron/Cinder list/summary only; does not call Gnocchi. Use `get_gnocchi_*` for telemetry |
| `gnocchi resource list/search/show/history` | `get_gnocchi_resources` | ✅ | Current-project resources; list, attribute filter, show with metrics map, and history passed live |
| `gnocchi metric list/show` | `get_gnocchi_metrics` | ✅ | List, per-resource details, show by resource + name, and show by metric UUID passed live |
| `gnocchi measures show` | `get_gnocchi_measures` | ✅ | By resource + name and by metric UUID passed live, including start, granularity, resample, refresh, latest-N limit, and `rate:mean` for `cpu`; `memory.usage`, disk, and network measures were read. Unsupported aggregation and missing metric returned failures |
| `gnocchi aggregates` | `get_gnocchi_aggregates` | ✅ | Current-project search is always applied. Passed live: project-wide `cpu` `rate:mean` mean, `top`, `groupby="flavor_name"`, and the `memory.usage`/`memory` ratio expression. Ranking across several resources is unit-tested only because the test project had one instance. A metric UUID owned outside the project returned 404 in expression mode. Mixed modes and missing metrics returned failures with hints. Unfilled gaps are returned as null |
| `gnocchi archive-policy/archive-policy-rule/resource-type list`, `gnocchi capabilities list`, `gnocchi status` | `get_gnocchi_service_info` | ✅ | All five sections returned live with the admin test account; a denied section is reported per section |
| Alarm management | `set_alarms` | ✅ | list/create/show/delete passed live, by name and by ID. Evaluation passed live: `cpu` alarms with `aggregation_method="rate:mean"` reached `ok` and `alarm` as expected, and a `vcpus` alarm reached `alarm`. Aodh accepted alarms for a nonexistent resource and for the default `cpu_util`, which current Ceilometer does not collect; check metrics with `get_gnocchi_metrics` first |
| Compute agents | `set_compute_agents` | ✅ | list/show of Nova services and hypervisors. `show` by `agent_id` looks the service up in the service listing (the SDK has no single-service lookup; this previously failed), and zones and hypervisor capacity read the SDK field names. 2026-11-10 targeted check (administrator): list with hypervisors, show by ID, show by host, and an explicit error for an unknown ID |
| Usage statistics | `get_usage_statistics` | ✅ | Period compute allocation-hours plus separately labeled current snapshots |

### 9. 📏 **Usage & Quota**

| OpenStack CLI Command | MCP Tool | Status | Notes |
|---------------------|---------|------|------|
| `openstack quota show` | `get_quota` | ✅ | Quota query. The network floating IP quota reads the SDK `floating_ips` field (previously always -1). 2026-11-10 targeted check: matched the Neutron quota |
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

---

## Contributing

Contributions are welcome. See the [development guide](docs/development.md) for
running the tests, adding tools, and the pull request workflow.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
