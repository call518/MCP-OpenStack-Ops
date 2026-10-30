# Main live validation — 2026-10-30

This is the historical **pre-fix baseline** at commit `dd98993`. For the fixes
and the latest validation snapshot, see the
[post-fix retest](main-live-retest-2026-10-30.md).

## Decision

**The entire toolset is not ready to be described as working.** All **105 registered
tools were invoked** against the test platform or through their actual handlers.
Ten tools have reproduced code defects. Other tools depend on services missing
from this platform, or deliberately provide limited capabilities. No application
source fixes, Git commits, or pushes were made during this validation.

The agreed phase-1 behavior for issue #73 and the allocation fix for issue #82
passed the focused live checks described at the end of this report. These results
do not certify every tool or client, production HTTPS, or sustained load.

## Source and method

- Branch: `main`; commit: `dd98993564f9ca6f7978822e51caf6ee37185ce2`.
- Application source, tests, `pyproject.toml`, and `uv.lock` remained identical to
  that commit. The only repository additions are this report and its evidence JSON.
- Python 3.12.11; FastMCP 3.2.0; openstacksdk 4.9.0; keystoneauth1 5.13.0;
  httpx 0.28.1. Existing project environment; no dependencies installed.
- Tool inventory: 105 with writes explicitly enabled. A fresh default-mode
  process exposed 50 read tools and **zero write tools**, verified via MCP discovery.
- The broad inventory exercised actual registered handler functions. Selected
  tools also ran through FastMCP protocol calls. Multi-user checks used the real
  stateless FastMCP HTTP ASGI application and authentication/audit middleware,
  with `httpx.ASGITransport`; this was not an external Claude client test.
- Issue #82 additionally ran through a **separate real stdio server process**
  launched from this checkout, using FastMCP Client and schema-validated calls.
- OpenStack calls were live, including disposable resources, API read-backs,
  asynchronous state polling, and deletion checks. An accepted request alone
  was not treated as proof that the resulting resource reached its target state.
- Identity HTTPS probes failed on ports 443/5000. Multi-user tests therefore used
  ephemeral certificate-verified TLS relays on loopback to the HTTP OpenStack
  APIs. Authentication, role enforcement, and resource operations were real;
  **production end-to-end HTTPS was not validated**.
- API addresses, credentials, user/project IDs, and raw resource responses are
  excluded. [Sanitized evidence](main-live-validation-2026-10-30.json) contains
  per-tool assessments, scenario records, and cleanup counts.

## Coverage

The following counts are **unique tools**, not API calls or feature counts.
`OBSERVED PASS` applies only to the exercised scenarios; it does not mean all
possible actions or edge cases of that tool passed. `DEFECT` takes precedence
over backend unavailability for the four broken Octavia imports.

| Assessment | Tools |
| --- | ---: |
| OBSERVED PASS | 68 |
| UNAVAILABLE | 23 |
| DEFECT | 10 |
| TIMING LIMIT | 1 |
| LIMITED | 3 |
| Total | 105 |

Attempts with incorrect harness arguments, assertions that inspected an echoed
request ID instead of returned resource data, and an omitted cleanup-verifier
mapping were corrected and rerun. They are marked `HARNESS_ERROR` in the evidence
and are excluded from application-defect conclusions. Retries and assertions are
not added together as independent feature coverage. Nested `success:false`
responses were inspected; a successful MCP envelope is not a successful API result.

## Reproduced defects

| Tools | Confirmed behavior / cause |
| --- | --- |
| `get_load_balancer_health_monitors`, `get_load_balancer_pool_members`, `set_load_balancer_pool`, `set_load_balancer_pool_member` | `from .functions` resolves to nonexistent `mcp_openstack_ops.tools.functions`. All four paths reproduced `ModuleNotFoundError`, independently of the missing Octavia service. |
| `set_image` | An inner `import json` makes `json` local throughout the function. `list` and scalar-name creation raise `UnboundLocalError`. The documented JSON-array name form initializes the variable and successfully created an image. |
| `set_heat_stack` | Scalar names with a JSON template hit the same local-`json` error. JSON-array names bypass it, but creation still returns HTTP 400. An SDK control with the same empty template and `tags=[]` failed; changing tags to an empty string succeeded. The tool supplies `tags=[]` through the service default. |
| `set_quota` | The public wrapper does not supply the service function's required `service` argument. Documented `list` fails with `TypeError` before cloud access. |
| `set_server_properties` | Metadata-only calls fail because the wrapper forwards an empty server name. Supplying the current name exposes a second error: `metadata` is sent to Nova's server-update endpoint, which rejects it as an additional property. Read-back confirmed metadata was not applied. |
| `set_server_backup` | The installed SDK Compute Proxy has no `create_server_backup` method. The real tool call fails with `AttributeError`; no backup image was created. |
| `set_floating_ip_port_forwarding` | Create uses `floatingip` instead of the SDK resource's required `floatingip_id`, failing with `KeyError`. List calls `port_forwardings` without its required `floating_ip` argument and suppresses the exception as an empty success response. Successful forwarding is unverified. |

These are observations against the checked-out main source and installed SDK;
this report does not change their implementation.

## Verified lifecycle areas and limits

- **Networking:** disposable network, subnet, port, router, and security group
  creation; network description update; explicit API read-backs; VM interface
  add/remove; fixed-IP interface add/remove; Floating IP allocation, description,
  show, association/disassociation, and release. The cloud MTU is 1450: the
  tool's 1500 default was rejected, while `mtu=0` allowed cloud selection. Routing
  fixtures explicitly set a gateway outside the allocation pool. No existing
  router or network configuration was changed.
- **Compute:** disposable VM reached ACTIVE; stop/start and pause/unpause reached
  their expected states; delete succeeded. Soft reboot was accepted but did not
  reach ACTIVE within 90 seconds. A later read showed ACTIVE and no task state;
  no hard reboot was performed. Guest networking/SSH and application behavior
  were not tested. Migration listing ran; actual migration/evacuation was not
  attempted without a validated destination host.
- **Storage:** blank 1 GiB volume creation; ready-state snapshot; volume attach,
  in-use state, detach and available state; backup/show/restore; restored-volume
  available state; volume type, generic group type and empty volume group;
  QoS create/show/set with updated-value read-back. Backup validation covers blank
  storage and API/ready states, not non-empty data integrity or guest I/O.
- **Identity and images:** disposable projects/users, domain create/show/disable,
  group create/show/update, role creation, flavor/keypair/server-group creation;
  shared-image metadata/visibility operations; member add/list/read-back/remove.
  SDK fixtures were explicitly distinguished from successful creator-tool calls
  when a broken tool prevented downstream tests. Empty image objects do not
  establish image-upload or bootability support.
- **Heat:** SDK-created empty stack reached CREATE_COMPLETE. Resources, events,
  template, and outputs queries succeeded. This validates the project-scoped
  endpoint and query paths; the tool's create defects above remain unresolved.
- **Environment limits:** Octavia and Aodh/Gnocchi were absent from the service
  catalog. Neutron QoS returned HTTP 404. No successful lifecycle is claimed for
  those backends. Compute/network agent state changes and existing global service
  settings were not altered. Logs/metrics list calls cover metadata, not an
  actual logging/telemetry backend. Server dump returns an explicit unsupported
  response.
- **Runtime flag limit:** starting with writes disabled hides every write tool.
  Changing the environment flag after a server was started with writes enabled
  does not unregister legacy tools; a disposable network creation demonstrated
  this. The guarded `set_users` path did reject the runtime-disabled request.
  This is a runtime-toggle limitation, distinct from the verified default-startup
  write restriction.

## Per-tool results

Each row describes only observed scenarios. SDK fixture creation and cleanup do
not establish that the corresponding MCP creator/deleter works. See the defect
and lifecycle sections for partial coverage and backend restrictions.

| Tool | Assessment | Evidence / limit |
| --- | --- | --- |
| `get_availability_zones` | OBSERVED PASS | read |
| `get_domains` | OBSERVED PASS | read; MCP protocol call |
| `get_floating_ip_pools` | OBSERVED PASS | read |
| `get_floating_ips` | OBSERVED PASS | read; MCP protocol call |
| `get_heat_stack_details` | OBSERVED PASS | resources; events; template; outputs |
| `get_heat_stacks` | OBSERVED PASS | read |
| `get_hypervisor_details` | OBSERVED PASS | read |
| `get_identity_groups` | OBSERVED PASS | read |
| `get_image_detail_list` | OBSERVED PASS | read |
| `get_image_members` | OBSERVED PASS | read; added member read |
| `get_instance` | OBSERVED PASS | read; disposable VM read |
| `get_instance_by_name` | OBSERVED PASS | read; disposable VM read |
| `get_instance_details` | OBSERVED PASS | read; disposable VM read |
| `get_instances_by_status` | OBSERVED PASS | read |
| `get_keypair_list` | OBSERVED PASS | read |
| `get_load_balancer_amphorae` | UNAVAILABLE | Octavia endpoint absent; successful functionality could not be tested. |
| `get_load_balancer_availability_zones` | UNAVAILABLE | Octavia endpoint absent; successful functionality could not be tested. |
| `get_load_balancer_details` | UNAVAILABLE | Octavia endpoint absent; successful functionality could not be tested. |
| `get_load_balancer_flavors` | UNAVAILABLE | Octavia endpoint absent; successful functionality could not be tested. |
| `get_load_balancer_health_monitors` | DEFECT | Wrong relative import: tools.functions does not exist. |
| `get_load_balancer_l7_policies` | UNAVAILABLE | Octavia endpoint absent; successful functionality could not be tested. |
| `get_load_balancer_l7_rules` | UNAVAILABLE | Octavia endpoint absent; successful functionality could not be tested. |
| `get_load_balancer_list` | UNAVAILABLE | Octavia endpoint absent; successful functionality could not be tested. |
| `get_load_balancer_listeners` | UNAVAILABLE | Octavia endpoint absent; successful functionality could not be tested. |
| `get_load_balancer_pool_members` | DEFECT | Wrong relative import: tools.functions does not exist. |
| `get_load_balancer_pools` | UNAVAILABLE | Octavia endpoint absent; successful functionality could not be tested. |
| `get_load_balancer_providers` | UNAVAILABLE | Octavia endpoint absent; successful functionality could not be tested. |
| `get_load_balancer_quotas` | UNAVAILABLE | Octavia endpoint absent; successful functionality could not be tested. |
| `get_network_details` | OBSERVED PASS | read; MCP protocol call |
| `get_network_qos_policies` | UNAVAILABLE | Neutron QoS endpoint returned HTTP 404. |
| `get_project_details` | OBSERVED PASS | read |
| `get_quota` | OBSERVED PASS | read |
| `get_resource_monitoring` | OBSERVED PASS | read |
| `get_role_assignments` | OBSERVED PASS | read |
| `get_routers` | OBSERVED PASS | read |
| `get_security_groups` | OBSERVED PASS | read |
| `get_server_events` | OBSERVED PASS | corrected schema read; disposable VM read |
| `get_server_groups` | OBSERVED PASS | read |
| `get_server_volumes` | OBSERVED PASS | corrected schema read; disposable VM read; attached volume read |
| `get_service_status` | OBSERVED PASS | read |
| `get_usage_statistics` | OBSERVED PASS | read |
| `get_user_list` | OBSERVED PASS | read |
| `get_volume_backups` | OBSERVED PASS | read |
| `get_volume_groups` | OBSERVED PASS | read |
| `get_volume_list` | OBSERVED PASS | read |
| `get_volume_qos` | OBSERVED PASS | read |
| `get_volume_snapshots` | OBSERVED PASS | read |
| `get_volume_transfers` | OBSERVED PASS | read |
| `get_volume_types` | OBSERVED PASS | read |
| `search_instances` | OBSERVED PASS | read |
| `set_alarms` | UNAVAILABLE | No alarming/metric catalog services. |
| `set_compute_agents` | OBSERVED PASS | read-only action; read |
| `set_domains` | OBSERVED PASS | read-only action; read; create; show; update disable |
| `set_flavor` | OBSERVED PASS | read-only action; create; cleanup via tool |
| `set_floating_ip` | OBSERVED PASS | read-only action; read; #82 create; #82 API allocation read-back; show; update; #82 delete; #82 deletion read-back; #82 allocate; delete final allocation; final allocation absence |
| `set_floating_ip_port_forwarding` | DEFECT | Creation fails with missing floatingip_id; list uses wrong floating_ip argument and masks the error as empty results. |
| `set_heat_stack` | DEFECT | Scalar-name JSON template fails with unbound json. JSON-array names bypass that error but tags=[] causes HTTP 400; SDK string-tags control succeeded. |
| `set_identity_groups` | OBSERVED PASS | read-only action; read; create; show; update |
| `set_image` | DEFECT | Local json import shadows module import; list and scalar-name create fail. JSON-array-name creation succeeded. |
| `set_image_members` | OBSERVED PASS | add; API sharing read-back; remove |
| `set_image_metadata` | OBSERVED PASS | set |
| `set_image_visibility` | OBSERVED PASS | set |
| `set_instance` | TIMING LIMIT | Create, stop/start, pause/unpause and delete succeeded. Soft reboot exceeded 90s, later ACTIVE with no task. |
| `set_keypair` | OBSERVED PASS | read-only action; create |
| `set_load_balancer` | UNAVAILABLE | Octavia endpoint absent; successful functionality could not be tested. |
| `set_load_balancer_amphora` | UNAVAILABLE | Octavia endpoint absent; successful functionality could not be tested. |
| `set_load_balancer_availability_zone` | UNAVAILABLE | Octavia endpoint absent; successful functionality could not be tested. |
| `set_load_balancer_flavor` | UNAVAILABLE | Octavia endpoint absent; successful functionality could not be tested. |
| `set_load_balancer_health_monitor` | UNAVAILABLE | Octavia endpoint absent; successful functionality could not be tested. |
| `set_load_balancer_l7_policy` | UNAVAILABLE | Octavia endpoint absent; successful functionality could not be tested. |
| `set_load_balancer_l7_rule` | UNAVAILABLE | Octavia endpoint absent; successful functionality could not be tested. |
| `set_load_balancer_listener` | UNAVAILABLE | Octavia endpoint absent; successful functionality could not be tested. |
| `set_load_balancer_pool` | DEFECT | Wrong relative import: tools.functions does not exist. |
| `set_load_balancer_pool_member` | DEFECT | Wrong relative import: tools.functions does not exist. |
| `set_load_balancer_quota` | UNAVAILABLE | Octavia endpoint absent; successful functionality could not be tested. |
| `set_metrics` | LIMITED | Metadata list succeeded; telemetry samples / actual log retrieval not validated. |
| `set_network_agents` | OBSERVED PASS | read-only action; read |
| `set_network_ports` | OBSERVED PASS | read-only action; read; create; API read-back |
| `set_network_qos_policies` | UNAVAILABLE | Neutron QoS endpoint returned HTTP 404. |
| `set_networks` | OBSERVED PASS | read-only action; create with cloud-selected MTU; API read-back after MTU retry; update |
| `set_project` | OBSERVED PASS | create disposable identity project |
| `set_quota` | DEFECT | Wrapper omits required service argument; documented list fails before an API request. |
| `set_roles` | OBSERVED PASS | read-only action; read; create |
| `set_routers` | OBSERVED PASS | create |
| `set_security_groups` | OBSERVED PASS | create; cleanup via tool |
| `set_server_backup` | DEFECT | Calls create_server_backup, absent from the installed Compute Proxy. |
| `set_server_dump` | LIMITED | Explicitly unsupported by the implementation; no dump created. |
| `set_server_fixed_ip` | OBSERVED PASS | add; remove |
| `set_server_floating_ip` | OBSERVED PASS | associate; association API read-back; disassociate; disassociation API read-back |
| `set_server_group` | OBSERVED PASS | read-only action; correct policy input |
| `set_server_migration` | OBSERVED PASS | read-only list |
| `set_server_network` | OBSERVED PASS | add port; attached port read-back; remove port |
| `set_server_properties` | DEFECT | Metadata-only call sends empty name; explicit-name retry sends metadata to the server-update API, which rejects that field. |
| `set_server_security_group` | OBSERVED PASS | add; remove |
| `set_server_volume` | OBSERVED PASS | attach; asynchronous state; detach |
| `set_service_logs` | LIMITED | Metadata list succeeded; telemetry samples / actual log retrieval not validated. |
| `set_services` | OBSERVED PASS | read-only action; read |
| `set_snapshot` | OBSERVED PASS | read-only action; create; asynchronous state; cleanup via tool |
| `set_subnets` | OBSERVED PASS | read-only action; read; create; API read-back; default gateway observation |
| `set_users` | OBSERVED PASS | create disposable identity user |
| `set_volume` | OBSERVED PASS | read-only action; create; asynchronous state |
| `set_volume_backups` | OBSERVED PASS | read-only action; read; create valid volume_id; asynchronous state; show; restore with tracked name; cleanup via tool |
| `set_volume_groups` | OBSERVED PASS | read-only action; read; create; asynchronous state; show; cleanup via tool |
| `set_volume_qos` | OBSERVED PASS | read-only action; read; create; show; set; updated API read-back |
| `set_volume_types` | OBSERVED PASS | create |

## Cleanup

Cleanup used the IDs of resources created by this run, not broad deletion of
pre-existing resources. Tool deletion paths were exercised, followed by SDK
fallbacks/read-backs and asynchronous absence checks. Temporary-project default
security groups were also removed.

- 47 tracked resource entries processed (includes allocations already
  released during scenario checks).
- Final independent inventory checks: **24 resource categories, zero remaining
  test resources in every category**. This covers servers, networks, subnets,
  ports, routers, security groups, images, flavors, keypairs, server groups,
  volumes, snapshots, backups, volume types/groups/group types, stacks, users,
  projects, domains, identity groups, roles, volume QoS, and tracked Floating IPs.
- Application Credentials were deleted; their disposable owning users/projects
  were also confirmed absent. TLS relays were shut down, temporary certificate
  and private-key files removed, and the credential-holding runner exited.

## Local verification

The final unit run on the unchanged main source completed with **132 passed,
12 SDK deprecated-field warnings, 0 failed**, in 40.92 seconds (exit code 0):

```bash
UV_CACHE_DIR=/tmp/mcp-openstack-uv-cache \
  uv run --locked --extra dev --no-sync python -m pytest -q tests
```

The 12 warnings concern the SDK's deprecated `local_gb`, `memory_mb`, and `vcpus`
fields. They are separate from the live failures reported above. Source equivalence
was checked with:

```bash
git diff --exit-code HEAD -- src tests pyproject.toml uv.lock
```

## Final issue assessment

### Issue #73 — agreed phase 1: passed in this test setup

- Three disposable identities authenticated with project-scoped Application
  Credentials: two member users in distinct projects and one reader-only user.
- Concurrent actual HTTP tool requests returned each user's own populated private
  network and 1 GiB volume, and excluded the other user's private resources.
- Foreign-network lookup payloads excluded the resource. Direct Neutron ID
  lookups were denied with 403/404. An echoed requested ID was not counted as
  disclosed resource data.
- Missing/invalid credentials returned HTTP 401 without environment-account
  fallback. After confirmed credential deletion and API absence, the next HTTP
  request returned **401 within 0.25 seconds from deletion start** in this run.
  Another user's request continued to work. This observation is not a universal
  revocation SLA or cancellation of already authenticated operations.
- Reader-only Neutron network creation returned 403. A default-mode process
  exposed no write tools. Connection-close callbacks were observed for successful
  requests, and application audit capture included user/project attribution
  without any observed test credentials/tokens.
- Scope remains phase 1 as agreed in the issue. Administrator cross-project reads,
  raw-token/OAuth authentication, Desktop/IDE compatibility, external Claude Code
  client validation for this merged build, sustained load, external proxy/APM logs,
  and production HTTPS are not certified by this run.

### Issue #82 — allocation fix: passed in this test setup

- Both `create` and `allocate`, with surrounding whitespace in
  `floating_network_id`, allocated a real address from the external network;
  API read-back confirmed the resulting allocation, then deletion was confirmed.
- Both actions also passed through a **real stdio server subprocess**, covering
  the transport in the original report and the public tool schema.
- Two normal users also exercised allocation/release through the phase-1 HTTP
  authentication path, using their own project-scoped connections. Allocation
  project IDs matched the calling projects.
- The existing VM Floating IP association/disassociation tool also succeeded with
  API read-backs. Successful guest connectivity was not tested.

**Conclusion:** the two focused issue paths passed within these stated limits.
The separate tool defects above remain reasons to avoid calling the entire
105-tool suite healthy before push/release.
