**English** | [Korean](cross-project-guide.ko.md)

# Cross-project reads (advanced)

**Most users do not need this guide.** By default every tool works inside the
one OpenStack project the server is configured for, and nothing here has to be
set up. Cross-project reads are an optional feature for administrators and
operators who need a view across projects, like the OpenStack CLI's
`--all-projects`. The feature is off by default.

## Enable it

1. Choose who may read across projects (setup A, B or C) in
   [Choose a setup](#choose-a-setup).
2. Configure OpenStack for that setup, as listed in
   [Required OpenStack configuration](#required-openstack-configuration).
3. Turn the feature on in this server: set `ALLOW_CROSS_PROJECT_READ=true`
   ([configuration](configuration.md)), or check **Allow cross-project reads**
   in the Claude Desktop extension settings.
4. Ask for all projects in a request, for example "List VMs per project". The
   client then passes `all_projects=true` to a supported tool.

## Supported tools

Some list tools accept `all_projects=true`, like the OpenStack CLI's
`--all-projects`, when the server sets `ALLOW_CROSS_PROJECT_READ=true`
(default `false`):

| Tool | With `all_projects=true` |
|---|---|
| `get_instance_details`, `search_instances`, `get_instances_by_status` | Instances of every visible project, each with `project_id` and `project_name` |
| `get_volume_list`, `get_volume_snapshots` | Volumes or snapshots of every visible project, each with `project_id` and `project_name` |
| `get_volume_backups`, `get_volume_groups` | Backups or generic volume groups of every visible project. Cinder shows their owner project only to administrators; when no row has an owner, `scope.warning` says the scope cannot be told |
| `get_server_groups` | Server groups of every visible project, each with `project_id` and `project_name` |
| `get_image_detail_list` | Every image Glance shows the credential, including other projects' private images for administrators. Public, community and shared images do not count toward the scope check, as for Neutron |
| `get_heat_stacks` | Stacks of every project through Heat's `global_tenant` query. Heat's default `stacks:global_index` policy denies it to everyone, administrators included |
| `get_load_balancer_list` | Load balancers of every visible project, each with `project_id` and `project_name`; `result.scope` covers every page |
| `get_network_details`, `get_routers`, `get_security_groups`, `get_floating_ips` | Networks, routers, security groups or floating IPs that Neutron shows the credential, each with `project_id` and `project_name`. Neutron never denies a list and shows other projects' shared and external resources to everyone, so `scope.warning` appears unless another project's unshared resource is in the result |
| `get_project_details` | A summary (ID, name, domain, enabled, `is_current`) of every visible project. With a `project_name` or ID that matches one project, that project's details and resource counts; network counts include only resources the credential can see |

## How it behaves

- **Who may read**: a credential may read across projects only when the target
  OpenStack service's policy authorizes the all-projects list API for its
  token. MCP-OpenStack-Ops does not define, store, or check roles or groups
  for this decision.
- **What the switch does**: `ALLOW_CROSS_PROJECT_READ` only exposes the
  parameter's behavior on this server; it grants no permission. In
  fixed-credential mode, every client of the server reads with the server
  credential's permissions. In multi-user mode, each request is decided by
  the caller's Application Credential.
- **Denials**: a policy denial (HTTP 403) is returned as an error, never as
  current-project results. Some services narrow an unauthorized request to
  the caller's project instead; a result that contains only the current
  project therefore carries a `scope.warning`. Each listing reports
  `scope.projects_in_result`.
- **Unchanged**: without `all_projects`, every tool stays current-project only.
  Modification tools and single-resource lookups by name (for example
  `get_instance_by_name`) always stay project-scoped. Only `get_project_details`
  with `all_projects=true` accepts another project's name or ID.

## Choose a setup

Cross-project read permission is configured in OpenStack, not in this server.
Choose one of these setups; the next section lists what each one requires:

| Setup | Who reads across projects | Note |
|---|---|---|
| A | A credential with the `admin` role | Simple, but grants full administration |
| B | A credential with a dedicated role (for example `cross_project_reader`) that service policies allow | Least privilege, but not every service can be delegated |
| C | A restricted Application Credential (role subset or access rules) sent in multi-user mode's request headers | Multi-user mode only |

## Required OpenStack configuration

Without these settings the switch still works, but OpenStack denies or narrows
the request as described in the reference tables below.

| Setup | Required | Without it |
|---|---|---|
| A | Nothing for most tools. Heat stack lists across projects need the `stacks:global_index` override (step 2) | `get_heat_stacks` with `all_projects` returns a policy denial, even for administrators |
| B | Steps 1 and 2 | Nova, Keystone and Heat deny the request (HTTP 403) |
| C, role subset | Step 3 (Cinder only) | A `reader`-only credential can still create volumes |
| C, access rules | Step 4 when a service's `service_type` is not a catalog type (Kolla-Ansible's Cinder) | That service rejects the credential with HTTP 401, reads included |

**Step 1: create the role and assign it** (setup B), with an administrator
credential:

```bash
openstack role create cross_project_reader
openstack role add --user <user> --project <project> cross_project_reader
```

**Step 2: add policy overrides.** With Kolla-Ansible, create these files on the
deployment host:

```yaml
# /etc/kolla/config/nova/policy.yaml
"os_compute_api:servers:detail:get_all_tenants": "rule:context_is_admin or role:cross_project_reader"
"os_compute_api:servers:index:get_all_tenants": "rule:context_is_admin or role:cross_project_reader"
```

```yaml
# /etc/kolla/config/keystone/policy.yaml (the 2025.1 default rule plus the role)
"identity:list_projects": "(rule:admin_required) or (role:reader and system_scope:all) or (role:reader and domain_id:%(target.domain_id)s) or role:cross_project_reader"
```

```yaml
# /etc/kolla/config/heat/policy.yaml (the default is rule:deny_everybody)
"stacks:global_index": "rule:context_is_admin or role:cross_project_reader"
```

For setup A only the Heat file is needed. Each override replaces the whole
rule, so keep the default part; check the defaults on your release, for example
with `oslopolicy-policy-generator --namespace keystone`.

**Step 3: enforce Cinder's new policy defaults** (setup C with a role subset).
Cinder 2025.1 defaults `[oslo_policy] enforce_new_defaults` to `false`, so its
deprecated rules still let a `reader`-only credential create volumes. This
setting was not checked live on the test cloud:

```ini
# /etc/kolla/config/cinder.conf
[oslo_policy]
enforce_new_defaults = true
```

**Step 4: give Cinder a catalog service type** (setup C with access rules).
keystonemiddleware checks access rules against `[keystone_authtoken]
service_type`, which must be a service type in the Keystone catalog.
Kolla-Ansible sets Cinder's to `volume`, which is not:

```ini
# /etc/kolla/config/cinder.conf
[keystone_authtoken]
service_type = block-storage
```

Access rules for volume tools then use `block-storage` as their `service`. If
both step 3 and step 4 apply, put both sections in the same `cinder.conf`.

**Apply** the files on the Kolla-Ansible deployment host. This restarts the
listed services:

```bash
kolla-ansible reconfigure -i <inventory> -t nova,keystone,heat,cinder
```

List only the services whose files you added. A new `kolla-ansible deploy`
applies files already in `/etc/kolla/config`; Kolla-Ansible has no
`globals.yml` variables for these settings. To revert, delete the files and run
the same command. Without Kolla-Ansible, put the same rules in each service's
policy file and the same options in its configuration file.

## Reference: policy rules and delegation

The policy rules that decide cross-project reads, with their defaults on
OpenStack 2025.1 (Epoxy):

| Service | Request | Policy rule and default | Without permission |
|---|---|---|---|
| Nova | Server list for all projects | `os_compute_api:servers:detail:get_all_tenants` and `os_compute_api:servers:index:get_all_tenants`: `rule:context_is_admin` (`role:admin`) | HTTP 403 |
| Cinder | Volume and snapshot lists for all projects | No dedicated rule. Cinder honors `all_tenants` only when `context_is_admin` (`role:admin`) passes | Silently narrowed to the caller's project |
| Keystone | Project list | `identity:list_projects`: `rule:admin_required`, a system-scoped reader, or a domain reader for its own domain | HTTP 403 |
| Neutron | Network, router, security group and floating IP lists | No all-projects flag; each resource's read policy decides what is listed, and other projects' shared and external resources are visible to everyone | Narrowed to what the credential can see |
| Glance | Image list | `get_images`: `rule:context_is_admin` or a project reader; administrators see other projects' private images | Narrowed to own, public and shared images |
| Heat | Stack list for all projects | `stacks:global_index`: `rule:deny_everybody` | HTTP 403, administrators included |
| Octavia | Load balancer list for all projects | `os_load-balancer_api:loadbalancer:get_all-global`: `rule:load-balancer:read-global` (`role:admin`) | Narrowed to the caller's project |

A dedicated role (setup B) works only where a policy rule alone decides the
request:

| Request | Delegable to a dedicated role | Why |
|---|---|---|
| Nova server list | Yes | The `get_all_tenants` rules decide |
| Keystone project list | Yes | `identity:list_projects` decides |
| Heat stack list | Yes | `stacks:global_index` decides |
| Nova server group list | No | Nova checks `context_is_admin` in code before its `os-server-groups:index:all_projects` rule |
| Cinder volume, snapshot, backup and group lists | No | Cinder checks `context_is_admin` in code |
| Glance private images, Octavia load balancers | Through those services' admin rules only | Their list policies grant other projects' resources to administrators |

For lists that cannot be delegated, use setup A or C, or accept the narrowed
result that carries `scope.warning`.
