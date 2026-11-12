**English** | [Korean](validation.ko.md)

# Validation evidence

This file records how the tools were validated: live checks against test
clouds, Claude Code prompt checks, and local unit tests. The Status column of
the README [OpenStack CLI vs MCP Tools Mapping](../README.md#-openstack-cli-vs-mcp-tools-mapping)
summarizes these results per command; this file keeps the dates, source
revisions, test conditions and counts behind them.

Live classifications count unique tools; unit-test results count test cases.
A partial or targeted check covers only the paths it names and does not update
an earlier full summary.

## Validation records

- **Live snapshot (2026-11-04; working tree based on `a57b165`):** This live
  snapshot predates the current working-tree changes. Its live
  classifications remain historical evidence and were not rerun for this change.
- **Live tool checks:** 105/105 tools registered at that revision exercised. At least one live
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
- **Targeted openstacksdk-usage check (2026-11-10 UTC; partial; commit
  `c2de34c`, which merges PR #83 and locks openstacksdk 4.22.0):** only the
  paths changed by that merge were run, through an in-process MCP client with
  modification tools enabled, as an administrator, with the locked
  dependencies (openstacksdk 4.22.0, fastmcp 3.4.10). The test cloud was a
  single-node deployment (compute microversion up to 2.100) with Nova,
  Neutron, Cinder (with backup), Glance and Heat; Octavia, Neutron QoS and
  port forwarding were absent, and only one compute host was available.
  Asynchronous operations were polled with openstacksdk until their final
  state (300 s per state; 600 s for backups). 73 checks ran: 68 passed; the
  5 failures came from the test script (output parsing, a metadata argument
  passed as a string, and a check aimed at the wrong tool). A retest of those
  paths passed for lock/unlock reporting, metadata set and metadata kept after
  rebuild. `get_project_details` reports resource counts, not quotas, so it
  does not cover the corrected quota field of `get_project_info()`, which no
  registered tool calls; that fix is unit-tested only. All test resources were
  deleted. This partial check does not update the 105-tool summary above.
- **fastmcp 4 dependency check (2026-11-10 UTC; partial; uncommitted working
  tree based on `aa668de`):** `uv.lock` moved to fastmcp 4.1.6 and mcp 2.3.0,
  and the `mcp-server` image now installs exactly the `uv.lock` packages. The
  same targeted check as above was repeated with these dependencies through an
  in-process MCP client, with three test-script errors corrected and the
  `get_project_details` check removed; it also read `get_gnocchi_service_info`
  and `get_gnocchi_metrics`. 74/74 checks passed, and all test resources were
  deleted. A locally built `mcp-server` image served 110 tools over Streamable
  HTTP, and 13 read tools, including the two Gnocchi read tools named above
  plus `get_gnocchi_resources`, returned results. A locally built `mcpo-proxy`
  image (mcpo 0.0.20, mcp 1.30.0, FastAPI 0.128.0) connected to that server,
  exposed 110 tools, and returned results for `get_service_status`,
  `get_gnocchi_resources` and `get_volume_list`. Neither image was published.
  This partial check does not update the 105-tool summary above.
- **Targeted boot-from-volume check (2026-11-10; working tree based on
  `84c346d` with the `set_instance` boot-from-volume change, served by a
  locally rebuilt `mcp-server` image):** one `set_instance` create call with
  `boot_from_volume` and `volume_size=10` created three servers on
  `private-net`. `get_instance` reported all three ACTIVE, and
  `get_server_volumes` reported for each a bootable, in-use 10 GB volume of
  type `__DEFAULT__` at `/dev/vda`. Booting from an existing volume
  (`boot_volume`) and volume deletion with the server were not exercised. The
  three servers were left running for the user. This partial check does not
  update the 105-tool summary above.
- **OpenStack 2026.1 live checks (2026-11-10 UTC; disposable OzarLand
  openstack-quick-lab cloud, Kolla-Ansible 22.2.0 all-in-one, compute
  microversion up to 2.103; administrator account):** `scripts/live_tool_check.py`
  ran with modification tools enabled, in process with openstacksdk 4.22.0 and
  4.9.0, and over Streamable HTTP with the PyPI package as the server. Final
  states were polled with openstacksdk, and no test resource was left behind.
  - **Release 3.7.3 (`aa668de`), cloud without Cinder:** 238/242 calls and
    54/54 final-state checks in each modification run; 72/76 calls read-only.
    57 tools passed, 5 passed with their Cinder section reported unavailable,
    40 needed an absent service, and 3 reached error paths only. The 4
    failures were `get_gnocchi_*` calls on a cloud without Gnocchi, and
    `get_gnocchi_measures` was not called (109 of 110 tools). The 13
    Cinder tools called reported "Block Storage (Cinder) service is not
    available" in about 0.01 s, without endpoint URLs.
  - **Release 3.7.6 (`f528b03`), Cinder added (LVM, NFS backups):** 248/253
    calls and 59/59 final-state checks in each modification run (the PyPI
    install resolved fastmcp 4.1.7). 74 tools passed, 27 needed an absent
    service (Octavia, Aodh, Neutron QoS), and 3 reached error paths only.
    `set_volume_backups` was partial and 4 `get_gnocchi_*` tools failed; both
    came from test-script errors fixed in the next record, which also calls
    `get_gnocchi_measures` (109 of 110 tools called here).
  - **Targeted Cinder and boot-from-volume checks on 3.7.6** (openstacksdk
    4.22.0 and 4.9.0): attach and detach, full and incremental backups of an
    attached volume, restore to a new volume and onto the source volume,
    snapshots, transfers and composite reports with Cinder passed (30/30 calls,
    24/24 checks). `set_instance` create from a new 1 GB root volume with
    `volume_type`, from an existing bootable volume, and for two servers in one
    call reached ACTIVE; `boot_source` was right in summary and detailed modes;
    the root volume was deleted with the server and kept with
    `delete_on_termination=false`; six invalid option combinations were
    refused without creating a server (19/19 calls, 20/20 checks), and a
    separate call with an in-use boot volume was refused the same way.
  - **Gnocchi error and live-script fixes (working tree based on `f528b03`):**
    256/256 calls and 61/61 final-state checks with openstacksdk 4.22.0 and
    4.9.0, all 110 tools called: 75 passed, 32 needed an absent service
    (including the five `get_gnocchi_*` tools, which now report "Metric service
    (Gnocchi) is not available"), 3 reached error paths only, none partial or
    failed.
  - **Multi-user HTTP mode (PyPI 3.7.6 server, HTTP-only test override):** two
    projects, each with a non-admin `member` user and an Application
    Credential. Missing, wrong or mismatched credentials returned 401 while the
    server's administrator `OS_*` variables were still set (no fallback). OAuth
    discovery routes and `/register` returned 404. Each user saw only its own
    project's servers and networks, could neither find nor stop the other
    project's server, and stopped and started its own; 20 concurrent requests
    from both users kept their identities. With shared Bearer authentication, a
    missing or wrong token returned 401. A deleted credential was rejected on
    the next request while the other user kept working. No credential secret
    appeared in the server logs, and the `INSECURE TEST MODE` warning was
    logged (28/28 checks).
  - **Docker:** the published image `call518/mcp-server-openstack-ops:1.0.5`
    (fastmcp 4.1.6, mcp 2.3.0 and openstacksdk 4.22.0, as in `uv.lock`) with
    the 3.7.6 source mounted as in `docker-compose.yml`: 78/78 calls read-only,
    and 256/256 calls and 61/61 final-state checks with modification tools,
    using the live script of the next record. `Dockerfile.MCP-Server` could
    not be rebuilt from the test network, whose proxy blocks the Rocky Linux
    mirrors.

  These checks are partial for Octavia, Aodh, Neutron QoS, port forwarding,
  Gnocchi with data, and paths that need a second compute host, and do not
  update the 105-tool summary above.
- **Local unit tests (2026-11-10; working tree based on `f528b03` with the
  Gnocchi error and live-script fixes):** 479/479 (100%) with fastmcp 4.1.6
  and openstacksdk 4.1.0, 4.9.0 and 4.22.0; no failures or skipped tests. The
  three new Gnocchi regressions fail on the previous code.
- **Local unit tests (2026-11-10; working tree based on `f528b03`, with two
  corrupted headings in `prompt_template.md` repaired):** 476/476 (100%) with fastmcp
  4.1.6 and openstacksdk 4.1.0, 4.9.0 and 4.22.0, run as
  `python -m pytest -q tests`; no failures or skipped tests. These tests
  include the `set_instance` create root-disk regressions (local disk, a new
  volume from the image, an existing bootable volume, and refused option
  combinations), the instance `boot_source` regressions, the
  `services.core.get_service_status` identity-endpoint fallback regression,
  MCP action-description and
  advanced-parameter forwarding regressions, the insecure-HTTP opt-in
  regressions, Gnocchi project-scoping and aggregation-input regressions,
  Claude Desktop bundle manifest and release-asset checks, regression tests
  built on real openstacksdk resource objects, and a static check that every
  `conn.<service>.<method>()` call and keyword exists in the installed
  openstacksdk; they do not replace live service validation.
- **Local security-group-rule tests (2026-11-11; uncommitted working tree
  based on `e522451`):** 492/492 (100%) with fastmcp 4.1.6 and the locked
  openstacksdk 4.22.0, run as `python -m pytest -q tests`; no failures or
  skipped tests. The new 16-case security-group-rule regression set covers
  exact create/delete SDK calls, single-port normalization, explicit CIDR or
  project-owned remote-group selection, protocol, port-range and IPv4/IPv6
  validation, and rejection of cross-project groups or rules belonging to
  another security group. Existing registration tests also verify the new
  tool's read-only write guard. No live OpenStack rule was created or deleted,
  so `set_security_group_rules` remains **Live unverified**.
- **Local integration tests (2026-11-11; uncommitted merge of PR #85 into
  `c8d4f51`, including live-harness integration fixes):** 497/497 (100%) with
  fastmcp 4.1.6 and the locked openstacksdk 4.22.0, run as
  `python -m pytest -q tests`; no failures or skipped tests. Two new harness
  regressions verify optional-service routing for Gnocchi, Aodh, Heat, Cinder
  and Cinder Backup. The harness now calls the 111th tool,
  `set_security_group_rules`, and checks restricted-CIDR rule creation and
  deletion, but those harness paths were not run against a live cloud in this
  integration, so their existing live statuses do not change.
- **Targeted Octavia read check (2026-11-12; partial; uncommitted working
  tree based on `05dfd12`):** Octavia GET responses report pool and
  health-monitor relations only as `listeners`, `loadbalancers`,
  `healthmonitor_id` and `pools`; the create-only `listener_id` and `pool_id`
  were `None`. Octavia also rejected `GET /v2.0/lbaas/pools?listener_id=...`
  with 400, which made `get_load_balancer_details` fail. After the fix, the
  service functions were called in the running `mcp-server` container (source
  mounted, openstacksdk Octavia proxy) against one HTTP load balancer with one
  listener, one pool of two members and one TCP health monitor:
  `get_load_balancer_details`, `get_load_balancer_pools` (all and by
  listener), `set_load_balancer_pool` (show),
  `get_load_balancer_health_monitors` (all and by pool) and
  `set_load_balancer_health_monitor` (show) all returned the expected
  relations (7/7 read calls). Calls went through the service layer, not the
  MCP transport. After the `mcp-server` container was restarted,
  `get_load_balancer_details` also succeeded through OpenWebUI and the MCP
  server for the same load balancer. No resource
  was created or changed. This partial check does not update the 105-tool
  summary above.
- **Local load-balancer relation tests (2026-11-12; same working tree):**
  500/500 (100%) with fastmcp 4.1.6 and the locked openstacksdk 4.22.0, run as
  `uv run pytest -q`; no failures or skipped tests. Two new regressions build
  pools and health monitors in the Octavia GET response shape, and existing
  tests now assert that no `listener_id` filter is sent to the pool list. The
  two new regressions failed on the previous code.
- **Targeted cross-project read check (2026-11-13 UTC; partial; uncommitted
  working tree based on `3882adc`):** issue #86's `all_projects` parameter was
  run on a Kolla-Ansible single-node OpenStack Epoxy cloud (compute
  microversion up to 2.100) with openstacksdk 4.22.0 and fastmcp 4.1.6. A test
  project held one `member` user with a server, a 1 GB volume and a snapshot;
  the administrator's project held two servers and two volumes, and the
  `service` project one Octavia amphora. The six tools
  `get_instance_details`, `search_instances`, `get_instances_by_status`,
  `get_volume_list`, `get_volume_snapshots` and `get_project_details` were
  called in fixed-credential mode (tool functions in process, administrator and
  `member`, switch on and off; 36 calls) and in multi-user mode (a local
  Streamable HTTP server with the HTTP-only test override and an Application
  Credential per user; 14 calls). All 50 calls returned the expected outcome.
  With the switch off, every `all_projects=true` call returned the
  "Cross-project reads are disabled" error. With it on, the administrator
  listed servers of three projects, volumes of two, the other project's
  snapshot, and three projects, each row with its project name. For `member`,
  Nova and Keystone denied the request (HTTP 403) and the tools returned the
  policy-denial error; Cinder instead returned only the member's own volume and
  snapshot, which carried `scope.warning`. Calls without `all_projects` stayed
  current-project only. No credential secret appeared in the multi-user server
  log. Not covered: setup B (a dedicated role with a policy override), a
  restricted Application Credential (setup C), and the policy rule names and
  defaults on this cloud. The test project, user, Application Credentials and
  resources were left for further checks. This partial check does not update
  the 105-tool summary above.
- **Local cross-project read tests (2026-11-13; same working tree):** 523/523
  (100%) with fastmcp 4.1.6 and the locked openstacksdk 4.22.0, run as
  `uv run pytest -q`; no failures or skipped tests. The 23 new cases cover the
  disabled switch (no OpenStack connection), policy denial as an error,
  the narrowed-result warning, project-name fallback to IDs, boot-volume image
  resolution for another project's server, project summaries, and
  current-project-only defaults for listings and name lookups.
- **Local server-instructions tests (2026-11-13; uncommitted working tree
  based on `86ac7f6`):** 526/526 (100%) with fastmcp 4.1.6 and the locked
  openstacksdk 4.22.0, run as `uv run pytest -q`; no failures or skipped
  tests. The server now sends `server_instructions.md` as MCP server
  instructions and no longer registers the three `prompt_template_*` prompts.
  The three new cases check that the instructions stay within 4,096
  characters and that in-process FastMCP clients in the legacy (`initialize`)
  and current (`server/discover`) protocol modes receive the instructions and
  an empty prompt list. Whether Claude Code, Claude Desktop or Open WebUI
  shows the instructions to the model was not checked live.
