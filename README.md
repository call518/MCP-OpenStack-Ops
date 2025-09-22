# MCP-OpenStack-Ops

> **MCP OpenStack Operations Server**: A comprehensive MCP (Model Context Protocol) server providing OpenStack project management and monitoring capabilities with built-in safety controls and single-project scope.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Deploy to PyPI with tag](https://github.com/call518/MCP-OpenStack-Ops/actions/workflows/pypi-publish.yml/badge.svg)](https://github.com/call518/MCP-OpenStack-Ops/actions/workflows/pypi-publish.yml)
[![BuyMeACoffee](https://raw.githubusercontent.com/pachadotdev/buymeacoffee-badges/main/bmc-donate-yellow.svg)](https://www.buymeacoffee.com/call518)

---

## Architecture & Internal (DeepWiki)

[![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/call518/MCP-OpenStack-Ops)

---

## Features

- ✅ **Single Project Scope**: Operates within the configured `OS_PROJECT_NAME` project scope for complete tenant isolation. All operations are restricted to resources within the specified project, ensuring data privacy and security in multi-tenant environments.
- ✅ **OpenStack SDK Integration**: Direct integration with OpenStack SDK for real-time project operations.
- ✅ **Enhanced Operation Safety**: Built-in safety controls with `ALLOW_MODIFY_OPERATIONS` environment variable and comprehensive error handling that prevents false success claims and provides clear guidance for asynchronous operations.
- ✅ **Smart Async Operation Handling**: Intelligent detection and guidance for OpenStack asynchronous operations (instance management, volume operations, network changes) with tool-specific timing expectations and verification commands.
- ✅ **Enhanced Project Monitoring**: Comprehensive project status reports with health scoring system, resource utilization analysis, instance state tracking, and detailed health breakdown by service categories.
- ✅ **Complete Service Coverage**: 93+ comprehensive tools covering Identity, Compute, Network, Storage, Image, Orchestration, Load Balancer, and Monitoring services within project scope.
- ✅ **Advanced Instance Management**: Enhanced server lifecycle operations with backup, migration, rescue, and administrative functions including state analysis.
- ✅ **Server Event Tracking**: Detailed server event history and lifecycle monitoring with comprehensive logging.
- ✅ **Network Analysis**: Comprehensive network operations with external/private network classification, floating IP management, and port operations within project scope.
- ✅ **Volume Management**: Comprehensive volume attachment/detachment operations with state analysis and capacity tracking.
- ✅ **Smart Image Filtering**: Access to public, community, shared, and project-owned images with intelligent visibility filtering that prevents zero-image count issues.
- ✅ **Enterprise Features**: User management, role assignments, keypair management, floating IP operations, volume snapshots within project boundaries.
- ✅ **Intelligent Search**: Flexible instance search with partial matching and case-sensitive options.
- ✅ **Load Balancer Integration**: Complete load balancer management with health monitoring within project scope.
- ✅ **Connection Optimization**: Global connection caching and automatic retry mechanisms.
- ✅ **Multi-Project Support**: Deploy multiple MCP servers with different `OS_PROJECT_NAME` values for complete multi-tenant project management with full isolation.
- ✅ **Docker Support**: Containerized deployment optimized for OpenStack Epoxy environments.
- ✅ **Flexible Transport**: Support for both `stdio` and `streamable-http` transports with comprehensive logging.

> ⚠️ **Compatibility Notice**: This MCP server is developed and optimized for **OpenStack Epoxy (2025.1)** as the primary target environment. However, it is compatible with most modern OpenStack releases (Dalmatian, Caracal, Bobcat, etc.) as the majority of APIs remain consistent across versions. Only a few specific API endpoints may require adaptation for full compatibility with older releases.
> 
> 🚧 **Coming Soon**: Dynamic multi-version OpenStack API compatibility is actively under development and will be available in upcoming releases, providing seamless support for all major OpenStack deployments automatically.

---

### Screenshots

**OpenStack Dashboard (Epoxy 2025.1)**

![OpenStack Dashboard (Epoxy 2025.1)](img/screenshot-openstack-dashboard.png)

**MCP Query Example - Cluster Status**

![Example Cluster Status](img/screenshot-claude-desktop.png)

---

## 📊 OpenStack CLI vs MCP Tools Mapping

**Detailed Mapping by Category**

### 1. 🖥️ **Compute (Nova)**

| OpenStack CLI Command | MCP Tool | Status | Notes |
|---------------------|---------|------|------|
| `openstack server list` | `get_instance_details` | ✅ | Pagination, filtering support |
| `openstack server show` | `get_instance_by_name`, `get_instance_by_id` | ✅ | ID/name search |
| `openstack server create` | `set_instance` (action="create") | ✅ | Instance creation |
| `openstack server start/stop/reboot` | `set_instance` | ✅ | Full lifecycle management |
| `openstack server delete` | `set_instance` (action="delete") | ✅ | Instance deletion |
| `openstack server backup create` | `set_server_backup` | ✅ | Backup creation with rotation |
| `openstack server image create` | `set_instance` (action="snapshot") | ✅ | Image/snapshot creation |
| `openstack server shelve/unshelve` | `set_instance` | ✅ | Instance shelving |
| `openstack server lock/unlock` | `set_instance` | ✅ | Instance locking |
| `openstack server pause/unpause` | `set_instance` | ✅ | Instance pausing |
| `openstack server suspend/resume` | `set_instance` | ✅ | Instance suspension |
| `openstack server resize` | `set_instance` (action="resize") | ✅ | Instance resizing |
| `openstack server resize confirm` | `set_instance` (action="confirm_resize") | ✅ | Resize confirmation |
| `openstack server resize revert` | `set_instance` (action="revert_resize") | ✅ | Resize revert |
| `openstack server rebuild` | `set_instance` (action="rebuild") | ✅ | Instance rebuilding |
| `openstack server rescue/unrescue` | `set_instance` | ✅ | Recovery mode |
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
| `openstack server add volume` | `set_server_volume` (action="attach") | ✅ | Volume attachment |
| `openstack server remove volume` | `set_server_volume` (action="detach") | ✅ | Volume detachment |
| `openstack server set` | `set_server_properties` (action="set") | ✅ | Server property setting |
| `openstack server unset` | `set_server_properties` (action="unset") | ✅ | Server property unsetting |
| `openstack server dump create` | `set_server_dump` | ✅ | Server dump creation |
| `openstack server event list` | `get_server_events` | ✅ | Server event tracking |
| `openstack server group list` | `get_server_groups` | ✅ | Server group listing |
| `openstack server group create/delete` | `set_server_group` | ✅ | Server group management |
| `openstack flavor list` | `get_flavor_list` (via cluster_status) | ✅ | Flavor listing |
| `openstack flavor create/delete` | `set_flavor` | ✅ | Flavor management |
| `openstack keypair list` | `get_keypair_list` | ✅ | Keypair listing |
| `openstack keypair create/delete` | `set_keypair` | ✅ | Keypair management |
| `openstack hypervisor list` | `get_hypervisor_details` | ✅ | Hypervisor querying |
| `openstack availability zone list` | `get_availability_zones` | ✅ | Availability zone listing |

### 2. 🌐 **Network (Neutron)**

| OpenStack CLI Command | MCP Tool | Status | Notes |
|---------------------|---------|------|------|
| `openstack network list` | `get_network_details` | ✅ | Detailed network information |
| `openstack network show` | `get_network_details` (name param) | ✅ | Specific network query |
| `openstack network create` | `set_networks` (action="create") | ✅ | Network creation |
| `openstack network delete` | `set_networks` (action="delete") | ✅ | Network deletion |
| `openstack network set` | `set_networks` (action="update") | ✅ | Network property updates |
| `openstack subnet list` | `get_network_details` (includes subnets) | ✅ | Subnet information included |
| `openstack subnet create/delete` | `set_subnets` | ✅ | Subnet management |
| `openstack router list` | `get_routers` | ✅ | Router listing |
| `openstack router create/delete` | (Not yet implemented) | 🚧 | Router management |
| `openstack floating ip list` | `get_floating_ips` | ✅ | Floating IP listing |
| `openstack floating ip create` | `set_floating_ip` (action="create") | ✅ | Floating IP creation |
| `openstack floating ip delete` | `set_floating_ip` (action="delete") | ✅ | Floating IP deletion |
| `openstack floating ip set` | `set_floating_ip` (action="set") | ✅ | Floating IP property setting |
| `openstack floating ip show` | `set_floating_ip` (action="show") | ✅ | Floating IP details |
| `openstack floating ip unset` | `set_floating_ip` (action="unset") | ✅ | Floating IP property clearing |
| `openstack floating ip pool list` | `get_floating_ip_pools` | ✅ | Floating IP pool listing |
| `openstack floating ip port forwarding create` | `set_floating_ip_port_forwarding` (action="create") | ✅ | Port forwarding creation |
| `openstack floating ip port forwarding delete` | `set_floating_ip_port_forwarding` (action="delete") | ✅ | Port forwarding deletion |
| `openstack floating ip port forwarding list` | `set_floating_ip_port_forwarding` (action="list") | ✅ | Port forwarding listing |
| `openstack floating ip port forwarding set` | `set_floating_ip_port_forwarding` (action="set") | ✅ | Port forwarding updates |
| `openstack floating ip port forwarding show` | `set_floating_ip_port_forwarding` (action="show") | ✅ | Port forwarding details |
| `openstack security group list` | `get_security_groups` | ✅ | Security group listing |
| `openstack security group create/delete` | (Not yet implemented) | 🚧 | Security group management |
| `openstack port list` | `get_network_details` (includes ports) | ✅ | Port information included |
| `openstack port create/delete` | `set_network_ports` | ✅ | Port management |
| `openstack network qos policy list` | (Not yet implemented) | 🚧 | QoS policy listing |
| `openstack network qos policy create` | `set_network_qos_policies` | ✅ | QoS policy management |
| `openstack network agent list` | `get_service_status` (includes agents) | ✅ | Network agents |
| `openstack network agent set` | `set_network_agents` | ✅ | Network agent management |

### 3. 💾 **Storage (Cinder)**

| OpenStack CLI Command | MCP Tool | Status | Notes |
|---------------------|---------|------|------|
| `openstack volume list` | `get_volume_list` | ✅ | Volume listing |
| `openstack volume show` | `get_volume_list` (filtering) | ✅ | Specific volume query |
| `openstack volume create/delete` | `set_volume` | ✅ | Volume creation/deletion |
| `openstack volume set` | `set_volume` (action="modify") | ✅ | Volume property modification |
| `openstack volume type list` | `get_volume_types` | ✅ | Volume type listing |
| `openstack volume type create/delete` | (Not yet implemented) | 🚧 | Volume type management |
| `openstack volume snapshot list` | `get_volume_snapshots` | ✅ | Snapshot listing |
| `openstack volume snapshot create/delete` | `set_snapshot` | ✅ | Snapshot management |
| `openstack backup list` | (Not yet implemented) | 🚧 | Backup listing |
| `openstack backup create/delete` | `set_volume_backups` | ✅ | Volume backup management |
| `openstack volume transfer request list` | (Not yet implemented) | 🚧 | Volume transfer |
| `openstack server volume list` | `get_server_volumes` | ✅ | Server volume listing |
| `openstack server add/remove volume` | `set_server_volume` | ✅ | Server volume attach/detach |
| `openstack volume group list` | (Not yet implemented) | 🚧 | Volume group listing |
| `openstack volume group create` | `set_volume_groups` | ✅ | Volume group management |
| `openstack volume qos list` | (Not yet implemented) | 🚧 | QoS listing |
| `openstack volume qos create` | `set_volume_qos` | ✅ | QoS management |

### 4. 🖼️ **Image (Glance)**

| OpenStack CLI Command | MCP Tool | Status | Notes |
|---------------------|---------|------|------|
| `openstack image list` | `get_image_detail_list` | ✅ | Image listing |
| `openstack image show` | `get_image_detail_list` (filtering) | ✅ | Specific image query |
| `openstack image create` | `set_image` (action="create") | ✅ | Enhanced image creation with min_disk, min_ram, properties |
| `openstack image delete` | `set_image` (action="delete") | ✅ | Image deletion |
| `openstack image set` | `set_image` (action="update") | ✅ | Image property modification |
| `openstack image save` | `set_image` (action="save") | ✅ | Image download |
| `openstack image add project` | (Not yet implemented) | 🚧 | Project sharing |
| `openstack image member list` | (Not yet implemented) | 🚧 | Member listing |
| `openstack image member create` | `set_image_members` | ✅ | Image member management |
| `openstack image set --property` | `set_image_metadata` | ✅ | Image metadata |
| `openstack image set --public/private` | `set_image_visibility` | ✅ | Image visibility setting |

### 5. 👥 **Identity (Keystone)**

| OpenStack CLI Command | MCP Tool | Status | Notes |
|---------------------|---------|------|------|
| `openstack user list` | `get_user_list` | ✅ | User listing |
| `openstack user show` | `get_user_list` (filtering) | ✅ | Specific user query |
| `openstack user create/delete` | (Not yet implemented) | 🚧 | User management |
| `openstack project list` | `get_project_details` | ✅ | Project listing |
| `openstack project show` | `get_project_details` (name param) | ✅ | Specific project query |
| `openstack project create/delete` | `set_project` | ✅ | Project management |
| `openstack role list` | `get_role_assignments` | ✅ | Role listing |
| `openstack role assignment list` | `get_role_assignments` | ✅ | Role assignment listing |
| `openstack role create/delete` | `set_roles` | ✅ | Role management |
| `openstack domain list` | (Not yet implemented) | 🚧 | Domain listing |
| `openstack domain create/delete` | `set_domains` | ✅ | Domain management |
| `openstack group list` | (Not yet implemented) | 🚧 | Group listing |
| `openstack group create/delete` | `set_identity_groups` | ✅ | Group management |
| `openstack service list` | `get_service_status` | ✅ | Service listing |
| `openstack service create/delete` | `set_services` | ✅ | Service management |
| `openstack endpoint list` | `get_service_status` (includes endpoints) | ✅ | Endpoint information |

### 6. 🔥 **Orchestration (Heat)**

| OpenStack CLI Command | MCP Tool | Status | Notes |
|---------------------|---------|------|------|
| `openstack stack list` | `get_heat_stacks` | ✅ | Stack listing |
| `openstack stack show` | `get_heat_stacks` (filtering) | ✅ | Specific stack query |
| `openstack stack create` | `set_heat_stack` (action="create") | ✅ | Stack creation |
| `openstack stack delete` | `set_heat_stack` (action="delete") | ✅ | Stack deletion |
| `openstack stack update` | `set_heat_stack` (action="update") | ✅ | Stack update |
| `openstack stack suspend/resume` | `set_heat_stack` | ✅ | Stack suspend/resume |
| `openstack stack resource list` | (Not yet implemented) | 🚧 | Stack resource listing |
| `openstack stack event list` | (Not yet implemented) | 🚧 | Stack event listing |
| `openstack stack template show` | (Not yet implemented) | 🚧 | Template query |
| `openstack stack output list` | (Not yet implemented) | 🚧 | Stack output listing |

### 7. ⚖️ **Load Balancer (Octavia)**

| OpenStack CLI Command | MCP Tool | Status | Notes |
|---------------------|---------|------|------|
| `openstack loadbalancer list` | `get_load_balancer_status` | ✅ | Load balancer listing with pagination |
| `openstack loadbalancer show` | `get_load_balancer_status` | ✅ | Load balancer detailed information |
| `openstack loadbalancer create` | `set_load_balancer` (action="create") | ✅ | Load balancer creation |
| `openstack loadbalancer delete` | `set_load_balancer` (action="delete") | ✅ | Load balancer deletion |
| `openstack loadbalancer set` | `set_load_balancer` (action="update") | ✅ | Load balancer property update |
| `openstack loadbalancer stats show` | `get_load_balancer_status` | ✅ | Load balancer statistics |
| `openstack loadbalancer status show` | `get_load_balancer_status` | ✅ | Load balancer status tree |
| `openstack loadbalancer failover` | `set_load_balancer` (action="failover") | ✅ | Load balancer failover |
| `openstack loadbalancer unset` | `set_load_balancer` (action="unset") | ✅ | Load balancer property unset |
| **Listener Management** | | | |
| `openstack loadbalancer listener list` | `get_load_balancer_listeners` | ✅ | Listener listing for load balancer |
| `openstack loadbalancer listener create` | `set_load_balancer_listener` (action="create") | ✅ | Listener creation (HTTP/HTTPS/TCP/UDP) |
| `openstack loadbalancer listener delete` | `set_load_balancer_listener` (action="delete") | ✅ | Listener deletion |
| `openstack loadbalancer listener show` | `get_load_balancer_listeners` | ✅ | Listener detailed information |
| `openstack loadbalancer listener set` | `set_load_balancer_listener` (action="update") | ✅ | Listener property update |
| `openstack loadbalancer listener stats show` | `get_load_balancer_listeners` | ✅ | Listener statistics |
| `openstack loadbalancer listener unset` | `set_load_balancer_listener` (action="unset") | ✅ | Listener property unset |
| **Pool Management** | | | |
| `openstack loadbalancer pool list` | `get_load_balancer_pools` | ✅ | Pool listing (all or by listener) |
| `openstack loadbalancer pool create` | `set_load_balancer_pool` (action="create") | ✅ | Pool creation with algorithms |
| `openstack loadbalancer pool delete` | `set_load_balancer_pool` (action="delete") | ✅ | Pool deletion |
| `openstack loadbalancer pool set` | `set_load_balancer_pool` (action="update") | ✅ | Pool property update |
| `openstack loadbalancer pool show` | `get_load_balancer_pools` | ✅ | Pool detailed information |
| `openstack loadbalancer pool stats show` | `get_load_balancer_pools` | ✅ | Pool statistics |
| `openstack loadbalancer pool unset` | `set_load_balancer_pool` (action="unset") | ✅ | Pool property unset |
| **Member Management** | | | |
| `openstack loadbalancer member list` | `get_load_balancer_members` | ✅ | Pool member listing |
| `openstack loadbalancer member create` | `set_load_balancer_member` (action="create") | ✅ | Pool member creation |
| `openstack loadbalancer member delete` | `set_load_balancer_member` (action="delete") | ✅ | Pool member deletion |
| `openstack loadbalancer member set` | `set_load_balancer_member` (action="update") | ✅ | Pool member property update |
| `openstack loadbalancer member show` | `get_load_balancer_members` | ✅ | Pool member detailed information |
| `openstack loadbalancer member unset` | `set_load_balancer_member` (action="unset") | ✅ | Pool member property unset |
| **Health Monitor Management** | | | |
| `openstack loadbalancer healthmonitor list` | `get_load_balancer_health_monitors` | ✅ | Health monitor listing |
| `openstack loadbalancer healthmonitor create` | `set_load_balancer_health_monitor` (action="create") | ✅ | Health monitor creation |
| `openstack loadbalancer healthmonitor delete` | `set_load_balancer_health_monitor` (action="delete") | ✅ | Health monitor deletion |
| `openstack loadbalancer healthmonitor set` | `set_load_balancer_health_monitor` (action="update") | ✅ | Health monitor update |
| `openstack loadbalancer healthmonitor show` | `get_load_balancer_health_monitors` | ✅ | Health monitor detailed information |
| `openstack loadbalancer healthmonitor unset` | `set_load_balancer_health_monitor` (action="unset") | ✅ | Health monitor property unset |
| **L7 Policy Management** | | | |
| `openstack loadbalancer l7policy list` | `get_load_balancer_l7_policies` | ✅ | L7 policy listing |
| `openstack loadbalancer l7policy create` | `set_load_balancer_l7_policy` (action="create") | ✅ | L7 policy creation |
| `openstack loadbalancer l7policy delete` | `set_load_balancer_l7_policy` (action="delete") | ✅ | L7 policy deletion |
| `openstack loadbalancer l7policy set` | `set_load_balancer_l7_policy` (action="update") | ✅ | L7 policy update |
| `openstack loadbalancer l7policy show` | `get_load_balancer_l7_policies` | ✅ | L7 policy details |
| `openstack loadbalancer l7policy unset` | `set_load_balancer_l7_policy` (action="unset") | ✅ | L7 policy property unset |
| **L7 Rule Management** 🆕 | | | |
| `openstack loadbalancer l7rule list` | `get_load_balancer_l7_rules` | ✅ | L7 rule listing |
| `openstack loadbalancer l7rule create` | `set_load_balancer_l7_rule` (action="create") | ✅ | L7 rule creation |
| `openstack loadbalancer l7rule delete` | `set_load_balancer_l7_rule` (action="delete") | ✅ | L7 rule deletion |
| `openstack loadbalancer l7rule set` | `set_load_balancer_l7_rule` (action="update") | ✅ | L7 rule update |
| `openstack loadbalancer l7rule show` | `get_load_balancer_l7_rules` | ✅ | L7 rule details |
| `openstack loadbalancer l7rule unset` | `set_load_balancer_l7_rule` (action="unset") | ✅ | L7 rule property unset |
| **Amphora Management** 🆕 | | | |
| `openstack loadbalancer amphora list` | `get_load_balancer_amphorae` | ✅ | Amphora listing |
| `openstack loadbalancer amphora show` | `set_load_balancer_amphora` (action="show") | ✅ | Amphora details |
| `openstack loadbalancer amphora configure` | `set_load_balancer_amphora` (action="configure") | ✅ | Amphora configuration |
| `openstack loadbalancer amphora failover` | `set_load_balancer_amphora` (action="failover") | ✅ | Amphora failover |
| `openstack loadbalancer amphora delete` | N/A | ❌ | Not supported by OpenStack SDK |
| `openstack loadbalancer amphora stats show` | N/A | ❌ | Not supported by OpenStack SDK |
| **Provider Management** | | | |
| `openstack loadbalancer provider list` | `get_load_balancer_providers` | ✅ | Provider listing |
| `openstack loadbalancer provider capability list` | `get_load_balancer_providers` | ✅ | Provider capability listing |
| **Availability Zone Management** 🆕 | | | |
| `openstack loadbalancer availabilityzone list` | `get_load_balancer_availability_zones` | ✅ | Availability zone listing |
| `openstack loadbalancer availabilityzone show` | `get_load_balancer_availability_zones` | ✅ | Availability zone details |
| `openstack loadbalancer availabilityzone create` | `set_load_balancer_availability_zone` (action="create") | ✅ | Availability zone creation |
| `openstack loadbalancer availabilityzone delete` | `set_load_balancer_availability_zone` (action="delete") | ✅ | Availability zone deletion |
| `openstack loadbalancer availabilityzone set` | `set_load_balancer_availability_zone` (action="update") | ✅ | Availability zone update |
| `openstack loadbalancer availabilityzone unset` | `set_load_balancer_availability_zone` (action="unset") | ✅ | Availability zone property unset |
| **Flavor Management** 🆕 | | | |
| `openstack loadbalancer flavor list` | `get_load_balancer_flavors` | ✅ | Flavor listing |
| `openstack loadbalancer flavor show` | `get_load_balancer_flavors` | ✅ | Flavor details |
| `openstack loadbalancer flavor create` | `set_load_balancer_flavor` (action="create") | ✅ | Flavor creation |
| `openstack loadbalancer flavor delete` | `set_load_balancer_flavor` (action="delete") | ✅ | Flavor deletion |
| `openstack loadbalancer flavor set` | `set_load_balancer_flavor` (action="update") | ✅ | Flavor update |
| `openstack loadbalancer flavor unset` | `set_load_balancer_flavor` (action="unset") | ✅ | Flavor property unset |
| **Flavor Profile Management** | | | |
| `openstack loadbalancer flavorprofile list` | `get_load_balancer_flavor_profiles` | ✅ | Flavor profile listing |
| `openstack loadbalancer flavorprofile show` | `get_load_balancer_flavor_profiles` | ✅ | Flavor profile details |
| `openstack loadbalancer flavorprofile create` | `set_load_balancer_flavor_profile` (action="create") | ✅ | Flavor profile creation |
| `openstack loadbalancer flavorprofile set` | `set_load_balancer_flavor_profile` (action="update") | ✅ | Flavor profile update |
| `openstack loadbalancer flavorprofile unset` | `set_load_balancer_flavor_profile` (action="unset") | ✅ | Flavor profile property unset |
| `openstack loadbalancer flavorprofile delete` | `set_load_balancer_flavor_profile` (action="delete") | 🚧 | Pending implementation |
| **Quota Management** 🆕 | | | |
| `openstack loadbalancer quota list` | `get_load_balancer_quotas` | ✅ | Quota listing |
| `openstack loadbalancer quota show` | `get_load_balancer_quotas` | ✅ | Quota details |
| `openstack loadbalancer quota set` | `set_load_balancer_quota` (action="set") | ✅ | Quota setting |
| `openstack loadbalancer quota reset` | `set_load_balancer_quota` (action="reset") | ✅ | Quota reset |

### 8. 📊 **Monitoring & Logging**

| OpenStack CLI Command | MCP Tool | Status | Notes |
|---------------------|---------|------|------|
| Resource monitoring | `get_resource_monitoring` | ✅ | Resource monitoring |
| Service status | `get_service_status` | ✅ | Service status query |
| Cluster overview | `get_cluster_status` | ✅ | Cluster overview |
| Service logs | `set_service_logs` | ✅ | Service log management |
| System metrics | `set_metrics` | ✅ | Metrics management |
| Alarm management | `set_alarms` | ✅ | Alarm management |
| Compute agents | `set_compute_agents` | ✅ | Compute agent management |
| Usage statistics | `get_usage_statistics` | ✅ | Usage statistics |

### 9. 📏 **Usage & Quota**

| OpenStack CLI Command | MCP Tool | Status | Notes |
|---------------------|---------|------|------|
| `openstack quota show` | `get_quota` | ✅ | Quota query |
| `openstack quota set` | `set_quota` | ✅ | Quota setting |
| `openstack usage show` | `get_usage_statistics` | ✅ | Usage query |
| `openstack limits show` | `get_quota` (includes limits) | ✅ | Limits query |
| Resource utilization | `get_resource_monitoring` | ✅ | Resource utilization |

---

## Quick Start

![Flow Diagram of Quickstart/Tutorial](img/MCP-Workflow-of-Quickstart-Tutorial.png)

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
OS_HEAT_STACK_PORT=8004
OS_HEAT_STACK_CFN_PORT=8000

# MCP Server Configuration (optional)
MCP_LOG_LEVEL=INFO
ALLOW_MODIFY_OPERATIONS=false
FASTMCP_TYPE=stdio
FASTMCP_HOST=127.0.0.1
FASTMCP_PORT=8080
```

### 2. Run Server

```bash
# Start all services
docker-compose up -d

# Check logs
docker-compose logs mcp-server
docker-compose logs mcpo-proxy
```

**Container Architecture**:
- **mcp-server**: OpenStack MCP server with tools
- **mcpo-proxy**: OpenAPI (REST-API)
- **open-webui**: Web interface for testing and interaction

**Service URLs - Docker Internal**:
- MCP Server: `localhost:8080` (HTTP transport)
- MCPO Proxy: `localhost:8000` (OpenStack API proxy)
- Open WebUI: `localhost:3000` (Web interface)

**Service URLs - Docker External**:
- MCP Server: `host.docker.internal:18005` (HTTP transport)
- MCPO Proxy: `host.docker.internal:8005` (OpenStack API proxy)
- Open WebUI: `host.docker.internal:3005` (Web interface)

#### For Claude Desktop Integration
Add to your Claude Desktop configuration:
```json
{
  "mcpServers": {
    "openstack-ops": {
      "command": "uvx",
      "args": ["--python", "3.11", "mcp-openstack-ops"],
      "env": {
        "OS_AUTH_HOST": "your-openstack-host",
        "OS_AUTH_PORT": "5000",
        "OS_PROJECT_NAME": "your-project",
        "OS_USERNAME": "your-username",
        "OS_PASSWORD": "your-password",
        "OS_USER_DOMAIN_NAME": "Default",
        "OS_PROJECT_DOMAIN_NAME": "Default",
        "OS_REGION_NAME": "RegionOne",
        "OS_IDENTITY_API_VERSION": "3",
        "OS_INTERFACE": "internal",
        "OS_COMPUTE_PORT": "8774",
        "OS_NETWORK_PORT": "9696",
        "OS_VOLUME_PORT": "8776",
        "OS_IMAGE_PORT": "9292",
        "OS_PLACEMENT_PORT": "8780",
        "OS_HEAT_STACK_PORT": "8004",
        "OS_HEAT_STACK_CFN_PORT": "18888",
        "ALLOW_MODIFY_OPERATIONS": "false",
        "MCP_LOG_LEVEL": "INFO"
      }
    }
  }
}
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
| `OS_HEAT_STACK_PORT` | Heat orchestration service port | `8004` | Heat API endpoint |
| `OS_HEAT_STACK_CFN_PORT` | Heat CloudFormation service port | `18888` | Heat CFN API endpoint |
| **MCP Server Configuration** |
| `MCP_LOG_LEVEL` | Logging level | `INFO` | Development debugging |
| `ALLOW_MODIFY_OPERATIONS` | Enable modify operations | `false` | Safety control for state modifications |
| `FASTMCP_TYPE` | Transport type | `stdio` | Rarely needed to change |
| `FASTMCP_HOST` | HTTP host address | `127.0.0.1` | For HTTP mode only |
| `FASTMCP_PORT` | HTTP port number | `8080` | For HTTP mode only |
| **Authentication (Optional)** |
| `REMOTE_AUTH_ENABLE` | Enable Bearer token authentication for streamable-http mode | `false` | Production security |
| `REMOTE_SECRET_KEY` | Secret key for Bearer token authentication | Required when auth enabled | Production security |

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

**📁 Ready-to-use Configuration File:**

A complete multi-project configuration example is available at `mcp-config.json.multi-project`:
- **Production**: Read-only operations for safety (`ALLOW_MODIFY_OPERATIONS=false`)
- **Development**: Full operations enabled (`ALLOW_MODIFY_OPERATIONS=true`) 
- **Testing**: Debug logging enabled (`MCP_LOG_LEVEL=DEBUG`)

```bash
# Copy and customize the multi-project configuration
cp mcp-config.json.multi-project ~/.config/claude-desktop/mcp_servers.json
# Edit with your OpenStack credentials
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
- ✅ **Ready-to-Use Configuration**: Pre-configured `mcp-config.json.multi-project` for quick setup
- ✅ **Updated Environment Variables**: Enhanced `.env.example` with project scoping guidance

---

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request