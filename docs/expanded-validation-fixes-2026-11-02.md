# Expanded validation fixes and final retest — 2026-11-02

## Result and scope

The network-create and legacy volume-attachment defects were fixed and verified
against the actual cluster. Search offset, case sensitivity and next-page
metadata were also corrected. The final source passed **199/199 local unit
cases (100%)** and **101/102 named live harness cases**. One fixture backup failed because of
Cinder NFS permissions, independently of MCP. After the operator corrected
the single directory permission, a separate recovery test created **6/6 fresh
backups successfully**, with two reader-side MCP checks. The original failure
remains recorded; it was not changed to a pass.
These are different denominators; live cases include fixture readiness,
positive/negative controls and load rounds, not unique tools or raw request counts.

**14 unique tools passed limited exercised scenarios; the remaining 91 of the
105 registered tools were not repeated in this final run.** This is a targeted
stabilization report, not complete production certification.

Actual Claude Code replay remains **blocked** by a model API credit/balance
error before any tool use. A same-URL registration defect was **not established**;
no speculative client/server workaround was applied.

[Sanitized final-source evidence and every named case](expanded-validation-fixes-2026-11-02.json)
contain source fingerprints, timings and cleanup. Earlier same-day evidence is
consolidated under `historical_evidence.earlier_runs` in that JSON, including
the pre-fix 60-example template classifications. Historical failures were not
retroactively replaced with passes. Superseded standalone reports were removed.

## What changed

| Finding | Fix | Final live verification |
| --- | --- | --- |
| Network default forced MTU 1500, rejected by a 1450 backend | `set_networks` defaults to `mtu=0`; the service omits this optional wire field. Explicit MTU is retained. | Both members created networks with automatic MTU 1450 and explicit MTU 1400, then removed them. |
| Legacy attach passed `instance_name` to a branch expecting IDs; SDK attach arguments were also wrong | Resolve name/ID through the existing server-volume service. Use SDK `(server, volume)` arguments. | Both projects' `set_volume` attach reached `in-use`, then detach reached `available`. |
| Attachment paths lacked consistent explicit endpoint ownership checks | Apply existing project-scoped lookup to server and volume; validate every detach target before mutation. | Foreign server attach, foreign volume attach/detach, and foreign VM stop were rejected. The other project's VM stayed `ACTIVE`. |
| Search `offset` and `case_sensitive` were ignored | Forward both flags through `search_instances` and `get_instance`; apply offset to matches and enrich only the selected page. | Both users and both tools returned ten distinct owned VMs across offsets 0/3/6/9; uppercase case-sensitive queries and foreign-project queries returned zero. |
| Search `has_more` was always false | Inspect one additional matching record; preserve default service list returns and existing MCP query fields. | Both tools reported true on the first page and false on the last page in both projects. |
| Prompt examples used unsupported parameter names or capabilities | Correct `names`, string-valued `instance_names`, `size`; remove nonexistent image/volume filters and `set_image(instance_id=...)` instructions. | **41 literal calls** checked against keyword names in four actual tool signatures; 0 invalid names. Not an LLM or full-template execution check. |

Default write gating, per-request authentication and project isolation remain
in place. No authentication cache, timeout expansion, administrator cross-project
access, new dependency or lockfile change was introduced. The SDK attachment
signature was also checked in the minimum supported SDK 4.1.0 source.

## Environment and users

- Source base: `6a36b6e`, uncommitted working tree; SHA-256 fingerprints are in JSON.
- After live testing, only the `set_volume` description and prompt documentation
  were clarified to stop advertising unsupported actions/parameters. Executable
  AST was confirmed unchanged. JSON records both the live-source and final-tree
  fingerprints; final descriptions were not replayed through Claude.
- Python 3.12.11, FastMCP 3.4.10, MCP SDK 1.30.0, OpenStack SDK 4.9.0, uvicorn 0.40.0.
- Isolated environment synchronized with `uv.lock`; original environment retained.
- Actual disposable project/user A: `mcp73x-20261102T064932Z-6ee1-a`.
- Actual disposable project/user B: `mcp73x-20261102T064932Z-6ee1-b`.
- Users had `member` plus implied `reader`; read credentials delegated only `reader`.
  Separate member credentials were used only in the explicit write-enabled child
  processes. Existing admin was used for fixture setup/cleanup only.
- Secrets stayed in memory; no passwords, credential IDs/secrets, tokens, private
  endpoints or fixture resource IDs appear in this report/evidence.

| Main simultaneous fixture | Each project | Total |
| --- | ---: | ---: |
| Cirros VMs (`m1.tiny`: 512 MiB, 1 vCPU) | 10 | 20 |
| Image-backed / volume-backed VMs | 5 / 5 | 10 / 10 |
| Volumes, 1 GiB | 10 | 20 |
| Private networks / subnets | 2 / 2 | 4 / 4 |
| Base snapshots / backups | 2 / 3 | 4 / 6 |

All VMs reached `ACTIVE` and all four base snapshots reached `available`.
Five of six base backups reached `available`; the sixth reached `error` with
a confirmed Cinder storage permission failure. The later recovery run used
six fresh 1-GiB volumes and six backups across two new ordinary-user projects;
all six backups reached `available` and each reader's MCP reply matched exactly
its three available backups.
Each project additionally exercised temporary default/explicit-MTU networks,
a subnet, a keypair and a snapshot through write-enabled MCP. Both legacy and
server-volume attach/detach paths reached their final API states.

Read/load and write servers used actual loopback TCP HTTP MCP endpoints with
real authentication middleware. The write probes no longer used the earlier
in-process ASGI transport. SDK calls reached the actual OpenStack services.
Verified TLS relays bridged to the HTTP-only lab APIs; this does not prove
production end-to-end HTTPS. Production CLI/container startup was not retested.

## Separate verification groups

| Group | Result | Scope |
| --- | --- | --- |
| Live unique tools | **14/14 (100%)**, 0 failed/unverified in this targeted scope | Seven read and seven write tools; not all actions or the full 105-tool inventory |
| Named live harness cases | **101/102**, 1 infrastructure fixture failure, 0 skips | Includes fixture state, isolation, query, lifecycle and grouped load checks |
| Shared two-project bursts | **14/14**, 0 failed | 2/4/8 parallel requests; actual max overlapping tool spans 8 |
| Shared 120-second sustained load | **209/209**, 0 failed | Four workers, both projects on the same MCP backend |
| Backup recovery after operator permission correction | **6/6 backups available**, two reader MCP checks passed | Fresh resources; original failure retained |
| Local unit tests | **199/199 (100%)**, 0 failed/skipped | `tests/`; 21 added regressions; 12 existing SDK field-deprecation warnings |
| Literal template keyword check | **41/41**, 0 invalid parameter names | Four tool signatures; not full template functionality |
| Actual Claude model preflight | **Blocked**, exit 1, terminal error flag | Confirmed credit/balance category before tools; further paid calls stopped |

Read tools: `get_instance`, `get_instance_details`, `get_volume_list`, `get_network_details`, `get_volume_snapshots`, `get_volume_backups`, `search_instances`.

Write tools: `set_instance`, `set_networks`, `set_subnets`, `set_keypair`, `set_volume`, `set_server_volume`, `set_snapshot`.

The reader-only valid network request was denied while the corresponding member
request succeeded. Default read-server discovery exposed 50 reads and no
`set_*` tools for either reader. Each reader returned exactly its ten volumes,
ten VMs, two snapshots and three backup records (one B-side record was in
`error`); the recovery run checked three `available` backups per reader. Shared external network visibility
was allowed by cloud policy, while the other project's private resources were absent.

### Measured load timings

The sustained round produced 105 correct responses for A and
104 for B. Every response matched the caller's ten VM IDs and all ten
image references, including volume-backed VMs. Actual maximum tool overlap was
4.

Request latency median / p95 / max: **2.034 / 2.703 / 3.241 seconds**.

| Separately measured server phase in 14 burst calls | Samples | Median / p95 / max, ms |
| --- | ---: | ---: |
| burst_authentication | 14 | 291.562 / 611.486 / 611.486 |
| burst_tool_execution | 14 | 3635.475 / 3850.603 / 3850.603 |
| burst_request_server_total | 14 | 4027.633 / 4319.534 / 4319.534 |

Authentication/tool spans are nested phases, not independent end-to-end samples.
Differences from earlier runs are not a controlled performance comparison.
This bounded single-hypervisor control-plane workload does not certify sustained
production capacity, guest CPU/I/O performance or a large LDAP-backed cloud.

## Separate OpenStack storage incident and recovery

Cinder returned errno 13 (`Permission denied`) while creating a backup through
its API, before any MCP write tool was involved. Operator-provided container
output showed cinder-backup running as UID/GID `42407:42407`, while the failing
NFS parent directory was owned by `42436:42407` with mode `755`: its group
could not create the next child directory. The operator changed only that
parent to mode `775`, retaining ownership. MCP code did not change for this
infrastructure correction.

The original failed backup and its fixtures were deleted. A separate targeted
recovery used two fresh projects, three 1-GiB volumes and three backups each.
All six backups reached `available`; actual TCP MCP reader checks verified
project-specific IDs and all three available states per project. This is a
fresh-resource recovery, not an in-place retry or an audit of every old NFS
shard. Other pre-existing directories with different owners need a separate
storage-layout/permission review. No recursive ownership/permission change
was made by this agent.

## Claude Code: what is and is not known

Earlier multiple-entry same-URL sessions sometimes stopped without tools.
Distinct forwarding URLs and single-entry sessions also failed before tools,
so the URL arrangement was not isolated as the cause. The latest minimal actual
WSL Claude Code preflight exited 1 with a terminal error and credit/balance
category, with no tool calls. No new MCP registration was needed for that
model-only diagnostic. OpenAI/Codex usage reset is separate from that model API
account condition.

There is no evidence supporting a server patch for duplicate URLs at this point.
After model API access is restored, controlled same-URL/distinct-URL/single-entry
comparisons and final-source natural-language queries must be rerun. Earlier
41 template CLI attempts and 73 tool calls belong to the pre-fix source, not
this final source or revised prompt. They are retained in the consolidated JSON historical evidence.

## Local test execution and cleanup

The authoritative local command was:

```bash
UV_PROJECT_ENVIRONMENT=/tmp/mcp73-locked-env \
UV_CACHE_DIR=/tmp/mcp73-uv-cache \
uv run --locked --no-sync python -m pytest -q tests
```

The environment had first been synchronized from the lockfile. Of the first
16 added regressions, 13 failed before the fixes and all subsequently passed.
Three pagination-metadata regressions also failed before that refinement;
two additional wrapper checks protect existing query metadata. The final
21 new cases supplement the previous 178 cases; repeated runs are not summed.

A direct `pytest -q tests` attempt had two `scripts` import collection errors;
`python -m pytest` includes the repository root and completed. A broad root
collection also included a manual bool-returning script; it is excluded from
this unit denominator. An initial sandbox-restricted thread test was interrupted
and rerun outside that restriction. These attempts were not counted as passes.

Readiness polling allowed 240 seconds per VM batch/storage collection and
180 seconds per backup. Write state polling allowed 180 seconds. Cleanup waited
240 seconds for VM deletion and 120 seconds per storage deletion. Accepted
requests alone were not counted as confirmed final states.

Cleanup deleted only tracked disposable resources, including automatic default
security groups, credentials, users and projects. Both final projects returned
Nova instance/core/RAM usage to zero. Independent admin API inspection found
zero remaining test servers, networks, subnets, ports, security groups, volumes,
snapshots or backups across the expanded runs. Cinder reserved quota counters
were not separately asserted. Existing project inventory retained one `SHUTOFF`
VM, one volume, two networks and one security group; this is an inventory/state
check, not a byte-for-byte audit. Detailed capacity and deletion evidence is in JSON.

No Git write or external comment was performed. Previous uncommitted changes
were preserved. Remaining validation needs are actual Claude replay, the author's
LDAP environment, production end-to-end TLS, backup restore/checksums and guest
reachability/I/O. Administrator cross-project reads remain a separate phase.
