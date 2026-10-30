# Main post-fix live retest — 2026-10-30

## Latest result

All **105 registered tools were invoked and classified again** after fixing the
10 tool defects recorded in the [pre-fix baseline](main-live-validation-2026-10-30.md).

| Unique-tool assessment | Result |
| --- | ---: |
| Observed pass within tested scenarios | 74 |
| Implemented, live unverified because a service/API was unavailable | 28 |
| Intentional capability limitation | 3 |
| Reproduced code defect in the retest | 0 |
| Asynchronous state timeout in the retest | 0 |
| Total tools | 105 |

The complete local suite passed: **160/160 (100%)**
with 12 SDK deprecation warnings
in 50.00 seconds. This includes 28 new regression cases. Unit-test counts and
unique-tool counts measure different things and must not be added together.
`OBSERVED PASS` covers only the scenarios listed below, not every supported action.
Unavailable backends are **not** classified as successful live functionality.

## Source and verification boundary

- Branch: `main` working tree, based on commit `dd98993564f9ca6f7978822e51caf6ee37185ce2`.
  The fixes are **uncommitted**; no Git write operation or push was performed.
- Final source snapshot SHA-256: `2512c6506ff96c9d4f8291a7f6a103eaa3aef2752b8f3e76b311db671efa8618`. The evidence JSON
  also retains the initial live-run fingerprint. Only help text and formatting
  changed after live setup; functional fixes were already loaded at startup.
  The final unit suite and fresh stdio server processes used the final source.
- Python 3.12.11, FastMCP 3.2.0, openstacksdk 4.9.0, keystoneauth1 5.13.0,
  httpx 0.28.1. No dependency changes or installations.
- All **105 public input schemas remained unchanged**, compared with the pre-fix
  inventory. A fresh default-mode stdio server exposed 50 read tools and no
  write tools; write-enabled discovery exposed all 105.
- Broad coverage used actual registered handler functions and live OpenStack API
  requests. Focused #73 tests used the real FastMCP stateless HTTP ASGI app plus
  authentication/audit middleware with `httpx.ASGITransport`. #82 additionally
  used a separate real stdio server process and schema-validated MCP calls.
- As before, the test platform did not provide direct usable identity HTTPS.
  Multi-user API calls used temporary certificate-verified loopback TLS relays
  to the HTTP OpenStack APIs. This does **not** validate production end-to-end
  HTTPS or external Claude client compatibility.
- API addresses, credentials, private IDs and raw resource responses are omitted.
  [Sanitized scenario evidence](main-live-retest-2026-10-30.json) includes all tool
  assessments, retries, negative input probes, source fingerprints and cleanup.
  Unsupported actions used in initial missing-service probes are marked
  `INPUT_REJECTED`, not counted as successful backend tests. Valid read-only
  probes also confirmed the missing Octavia endpoint for the corrected imports.

## Defects corrected and verified

Twenty new regression cases first failed on the pre-fix source. Those cases and
eight further safety/compatibility cases passed after the changes.

| Affected tools | Change | Evidence after the fix |
| --- | --- | --- |
| Four Octavia wrappers: health-monitor read, pool-member read, pool write, pool-member write | Import services from the parent package, instead of nonexistent `tools.functions` | Regression tests reach service exports; live probes reach the missing Octavia endpoint. Successful Octavia operations remain unverified. |
| `set_image` | Remove the inner import that shadowed `json` | Real list, scalar-name create, image API read-back and scalar-name deletion succeeded. |
| `set_heat_stack` | Remove `json` shadowing, use string tags and the SDK `status` attribute | Scalar-name empty-stack creation reached CREATE_COMPLETE; resources/events/template/outputs and deletion succeeded. |
| `set_quota` | Route read-only list to the getter; route supplied fields to their service; use SDK reset methods for delete; guard runtime writes | Changed cores, Floating IP and volume limits only in a disposable project; all three API read-backs matched, and deletion/reset restored all prior defaults. Regression cases cover partial failure and legacy `floatingips` callers. |
| `set_server_properties` | Omit empty default name/description; use Nova metadata endpoints | Metadata-only set preserved VM name/description; unset removed the requested key and preserved other keys. |
| `set_server_backup` | Call SDK `backup_server`; report acceptance without inventing an image ID | Tool created a real Glance backup image and polling observed `active`. No guest/data restoration is claimed. Custom backup metadata remains unsupported and is documented. |
| `set_floating_ip_port_forwarding` | Correct the parent-ID arguments for create/list/show/update/delete and stop masking list failures | All five SDK signatures and list-failure handling passed autospecced regressions. Real create/list now reach Neutron, which returns 404. No successful forwarding lifecycle is claimed. |

Quota mutations across services are not transactional: partial completion is
reported rather than silently marked successful. The public tool signature and
existing direct service-call form are preserved. Quota reset was tested only on
a project created for this run, with no effect on existing project limits.

## Live scenarios and remaining limits

- Created a disposable network, subnet with explicit gateway, port, router and
  security group; verified network updates, VM interface and fixed-IP add/remove,
  and Floating IP association/disassociation by API read-back. The network used
  cloud-selected MTU 1450 instead of forcing the tool's 1500 default. Temporary
  routing changes affected only this run's router and subnet.
- Created a VM from an existing Cirros image and small existing flavor. Create,
  stop/start, pause/unpause, soft reboot and delete reached their expected states.
  Soft reboot completed in **131.66s** within a 180-second poll limit, requiring
  both ACTIVE status and no task state. The previous 90-second timeout is retained
  as historical evidence, not erased. No hard reboot was used.
- Tested blank 1 GiB volume create, snapshot, attach/in-use/detach/available,
  backup/show/restore/available, volume type/group, and Cinder QoS create/show/set
  with updated-value read-back. Empty-volume backup checks do not establish
  non-empty data integrity or guest I/O.
- Tested disposable project/user/domain/group/role creation, domain disable,
  identity-group update, flavor/keypair/server-group creation, and image
  metadata/visibility/member add/read-back/remove. Queued empty image objects
  do not validate image upload or bootability.
- Migration listing ran, but actual migration/evacuation was not attempted without
  a validated destination host. Existing global services and agents were not
  enabled, disabled or reconfigured. Guest SSH/network reachability, sustained
  load and every role/policy/backend combination remain unverified.
- Missing APIs: **24 Octavia tools**, two Neutron QoS tools, one Aodh alarm tool,
  and one Neutron port-forwarding tool account for the **28 live-unverified tools**.
  Octavia and alarming/metric were absent from the catalog; the two Neutron
  feature endpoints returned 404. Implemented paths have unit coverage where
  applicable, but no successful real-service operation is claimed for them.
- Three intentional limitations: `set_server_dump` explicitly returns unsupported;
  `set_metrics` and `set_service_logs` expose metadata rather than actual samples
  or log retrieval. They are not counted as fully working telemetry/logging tools.
- Runtime changes to the write flag do not unregister legacy tools already
  registered at startup; restart with writes disabled for the default read-only
  tool set. This pre-existing limit remains separate from #73's verified default.

## Per-tool results

Each row covers only the listed observed scenarios. A backend error is not an
application success, and a successful MCP envelope is not a successful API result.

| Tool | Assessment | Evidence / limit |
| --- | --- | --- |
| `get_availability_zones` | OBSERVED PASS | read |
| `get_domains` | OBSERVED PASS | read |
| `get_floating_ip_pools` | OBSERVED PASS | read |
| `get_floating_ips` | OBSERVED PASS | read |
| `get_heat_stack_details` | OBSERVED PASS | resources; events; template; outputs |
| `get_heat_stacks` | OBSERVED PASS | read |
| `get_hypervisor_details` | OBSERVED PASS | read |
| `get_identity_groups` | OBSERVED PASS | read |
| `get_image_detail_list` | OBSERVED PASS | read |
| `get_image_members` | OBSERVED PASS | read; member read |
| `get_instance` | OBSERVED PASS | read; disposable VM read/capability |
| `get_instance_by_name` | OBSERVED PASS | disposable VM read/capability |
| `get_instance_details` | OBSERVED PASS | read; disposable VM read/capability |
| `get_instances_by_status` | OBSERVED PASS | read |
| `get_keypair_list` | OBSERVED PASS | read |
| `get_load_balancer_amphorae` | LIVE UNVERIFIED | Octavia not in service catalog; no successful service lifecycle tested. |
| `get_load_balancer_availability_zones` | LIVE UNVERIFIED | Octavia not in service catalog; no successful service lifecycle tested. |
| `get_load_balancer_details` | LIVE UNVERIFIED | Octavia not in service catalog; no successful service lifecycle tested. |
| `get_load_balancer_flavors` | LIVE UNVERIFIED | Octavia not in service catalog; no successful service lifecycle tested. |
| `get_load_balancer_health_monitors` | LIVE UNVERIFIED | Octavia not in service catalog; no successful service lifecycle tested. |
| `get_load_balancer_l7_policies` | LIVE UNVERIFIED | Octavia not in service catalog; no successful service lifecycle tested. |
| `get_load_balancer_l7_rules` | LIVE UNVERIFIED | Octavia not in service catalog; no successful service lifecycle tested. |
| `get_load_balancer_list` | LIVE UNVERIFIED | Octavia not in service catalog; no successful service lifecycle tested. |
| `get_load_balancer_listeners` | LIVE UNVERIFIED | Octavia not in service catalog; no successful service lifecycle tested. |
| `get_load_balancer_pool_members` | LIVE UNVERIFIED | Octavia not in service catalog; no successful service lifecycle tested. |
| `get_load_balancer_pools` | LIVE UNVERIFIED | Octavia not in service catalog; no successful service lifecycle tested. |
| `get_load_balancer_providers` | LIVE UNVERIFIED | Octavia not in service catalog; no successful service lifecycle tested. |
| `get_load_balancer_quotas` | LIVE UNVERIFIED | Octavia not in service catalog; no successful service lifecycle tested. |
| `get_network_details` | OBSERVED PASS | read |
| `get_network_qos_policies` | LIVE UNVERIFIED | Neutron QoS API returned HTTP 404. |
| `get_project_details` | OBSERVED PASS | read |
| `get_quota` | OBSERVED PASS | read |
| `get_resource_monitoring` | OBSERVED PASS | read |
| `get_role_assignments` | OBSERVED PASS | read |
| `get_routers` | OBSERVED PASS | read |
| `get_security_groups` | OBSERVED PASS | read |
| `get_server_events` | OBSERVED PASS | disposable VM read/capability |
| `get_server_groups` | OBSERVED PASS | read |
| `get_server_volumes` | OBSERVED PASS | disposable VM read/capability; attached volume read |
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
| `set_alarms` | LIVE UNVERIFIED | Aodh/Gnocchi unavailable. |
| `set_compute_agents` | OBSERVED PASS | read-only action |
| `set_domains` | OBSERVED PASS | read-only action; create; show; disable |
| `set_flavor` | OBSERVED PASS | read-only action; create; cleanup via tool |
| `set_floating_ip` | OBSERVED PASS | read-only action; release forwarding fixture; forwarding fixture released |
| `set_floating_ip_port_forwarding` | LIVE UNVERIFIED | Neutron port-forwarding API returned HTTP 404; SDK-correct paths covered by regression tests. |
| `set_heat_stack` | OBSERVED PASS | scalar create; API read-back; asynchronous state; cleanup via tool |
| `set_identity_groups` | OBSERVED PASS | read-only action; create; show; update |
| `set_image` | OBSERVED PASS | read-only action; scalar create; API read-back; cleanup via tool |
| `set_image_members` | OBSERVED PASS | add; API member read-back; remove |
| `set_image_metadata` | OBSERVED PASS | set |
| `set_image_visibility` | OBSERVED PASS | set |
| `set_instance` | OBSERVED PASS | create; stop; start; pause; unpause; restart; cleanup via tool |
| `set_keypair` | OBSERVED PASS | read-only action; create |
| `set_load_balancer` | LIVE UNVERIFIED | Octavia not in service catalog; no successful service lifecycle tested. |
| `set_load_balancer_amphora` | LIVE UNVERIFIED | Octavia not in service catalog; no successful service lifecycle tested. |
| `set_load_balancer_availability_zone` | LIVE UNVERIFIED | Octavia not in service catalog; no successful service lifecycle tested. |
| `set_load_balancer_flavor` | LIVE UNVERIFIED | Octavia not in service catalog; no successful service lifecycle tested. |
| `set_load_balancer_health_monitor` | LIVE UNVERIFIED | Octavia not in service catalog; no successful service lifecycle tested. |
| `set_load_balancer_l7_policy` | LIVE UNVERIFIED | Octavia not in service catalog; no successful service lifecycle tested. |
| `set_load_balancer_l7_rule` | LIVE UNVERIFIED | Octavia not in service catalog; no successful service lifecycle tested. |
| `set_load_balancer_listener` | LIVE UNVERIFIED | Octavia not in service catalog; no successful service lifecycle tested. |
| `set_load_balancer_pool` | LIVE UNVERIFIED | Octavia not in service catalog; no successful service lifecycle tested. |
| `set_load_balancer_pool_member` | LIVE UNVERIFIED | Octavia not in service catalog; no successful service lifecycle tested. |
| `set_load_balancer_quota` | LIVE UNVERIFIED | Octavia not in service catalog; no successful service lifecycle tested. |
| `set_metrics` | LIMITED | Metadata listing only; actual telemetry/log retrieval is unsupported. |
| `set_network_agents` | OBSERVED PASS | read-only action |
| `set_network_ports` | OBSERVED PASS | read-only action; create |
| `set_network_qos_policies` | LIVE UNVERIFIED | Neutron QoS API returned HTTP 404. |
| `set_networks` | OBSERVED PASS | read-only action; create; API read-back; update |
| `set_project` | OBSERVED PASS | create |
| `set_quota` | OBSERVED PASS | read-only action; set disposable project; three-service API read-back; reset disposable project; default limits restored |
| `set_roles` | OBSERVED PASS | read-only action; create |
| `set_routers` | OBSERVED PASS | create |
| `set_security_groups` | OBSERVED PASS | create; cleanup via tool |
| `set_server_backup` | OBSERVED PASS | create; Glance image read-back; asynchronous state |
| `set_server_dump` | LIMITED | Explicit unsupported response; no dump created. |
| `set_server_fixed_ip` | OBSERVED PASS | add; remove |
| `set_server_floating_ip` | OBSERVED PASS | associate; association read-back; disassociate; disassociation read-back |
| `set_server_group` | OBSERVED PASS | read-only action; create |
| `set_server_migration` | OBSERVED PASS | disposable VM read/capability |
| `set_server_network` | OBSERVED PASS | add port; attached port read-back; remove port |
| `set_server_properties` | OBSERVED PASS | metadata-only set; metadata read-back and unchanged name/description; metadata unset; unset read-back preserves other keys |
| `set_server_security_group` | OBSERVED PASS | add; remove |
| `set_server_volume` | OBSERVED PASS | attach; detach |
| `set_service_logs` | LIMITED | Metadata listing only; actual telemetry/log retrieval is unsupported. |
| `set_services` | OBSERVED PASS | read-only action |
| `set_snapshot` | OBSERVED PASS | read-only action; create; asynchronous state; cleanup via tool |
| `set_subnets` | OBSERVED PASS | read-only action; create |
| `set_users` | OBSERVED PASS | create |
| `set_volume` | OBSERVED PASS | read-only action; create; asynchronous state |
| `set_volume_backups` | OBSERVED PASS | read-only action; create; asynchronous state; show; restore; cleanup via tool |
| `set_volume_groups` | OBSERVED PASS | read-only action; create; asynchronous state; show; cleanup via tool |
| `set_volume_qos` | OBSERVED PASS | read-only action; create; show; set; updated API read-back |
| `set_volume_types` | OBSERVED PASS | create |

## Cleanup and local checks

- 43 tracked resource entries processed; tool deletion calls followed by
  idempotent SDK cleanup and API absence checks.
- **24 resource categories audited; zero remaining test resources in every
  category.** Temporary-project default security groups were included.
- Credentials and their temporary users/projects were deleted; TLS relays were
  stopped, temporary TLS key/certificate files removed, and the runner exited.
- Application source, tests and README were not staged, committed or pushed.
- Local command (exit 0):

```bash
UV_CACHE_DIR=/tmp/mcp-openstack-uv-cache \
  uv run --locked --extra dev --no-sync python -m pytest -q tests
```

Result: **160/160 (100%)**; 12 warnings in 50.00s. The warnings are the SDK's deprecated
`local_gb`, `memory_mb` and `vcpus` fields. Scoped diff/whitespace checks, unchanged
public input-schema comparison and README tool-name checks were also performed.

## Final issue assessment

### #73 — agreed phase 1 passed again

Two member users in distinct projects and one reader-only user authenticated
with their own Application Credentials. Concurrent HTTP queries included each
member's populated private network and 1 GiB volume while excluding the other's.
Foreign-network payloads excluded the resource and direct foreign-ID Neutron
lookups were denied. Missing/invalid credentials returned 401 without environment
fallback; after confirmed credential deletion the next request was rejected in
**0.15s from deletion start** in this run. Another user remained authenticated. This is an
observed timing, not a universal revocation SLA or cancellation of in-flight work.

Reader creation was denied with 403. A fresh default server exposed no write
tools. Request connection-close counts matched authentication counts, and audit
capture attributed users/projects while excluding all observed credentials/tokens.
Administrator cross-project reads remain a separate phase. Desktop/IDE, external
Claude Code for this build, production HTTPS, external proxy/APM logs and load
are outside this result.

### #82 — allocation fix passed again

Both `create` and `allocate`, with whitespace around `floating_network_id`, passed
through a real stdio subprocess with allocation read-back and confirmed deletion.
Both actions also passed under distinct normal-user HTTP connections, and the
allocation project matched the caller's project. Existing VM Floating IP
association/disassociation also passed with API read-backs. Guest connectivity
was not tested.
