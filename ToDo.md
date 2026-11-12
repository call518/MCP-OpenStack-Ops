**English** | [Korean](ToDo.ko.md)

# TODO

Last reviewed: 2026-11-12

This file tracks only outstanding work. Completed items are removed.

## [Issue #86](https://github.com/call518/MCP-OpenStack-Ops/issues/86) Cross-project reads

This item also completes the required follow-up of
[Issue #73](https://github.com/call518/MCP-OpenStack-Ops/issues/73).

- [ ] **Read across projects with sufficiently privileged credentials**

**Design**

| Topic | Decision |
|---|---|
| Authorization criterion | Allowed only when the target OpenStack service's policy authorizes the all-projects list API for the credential's token. The MCP server does not define, store, or check roles or groups. |
| Feature switch | Add `ALLOW_CROSS_PROJECT_READ` (default `false`). It enables the feature on this server only and grants no permissions. |
| Tool interface | Add `all_projects` (default `False`) to existing list tools; no new tools. The default stays current-project only. |
| Results | Each item includes `project_id` and, when available, the project name. Keep `limit`/`offset` pagination. |
| Policy denial (403) | Return a failure; never fall back to current-project results. |
| Narrowed result | When a successful response contains only the current project, add a warning that policy may have narrowed the scope. |
| Token roles | Diagnostics only; never used to decide access. |
| Authentication modes | Fixed-credential mode and multi-user Application Credential mode share one code path. |

**Tool scope**

| Scope | Tools | Behavior |
|---|---|---|
| First phase | `get_project_details` (project list), `get_instance_details`, `search_instances`, `get_instances_by_status`, `get_volume_list`, `get_volume_snapshots` | Accept `all_projects` |
| Later phases | Network, Image, Heat, and other services | Not started |
| Unchanged | `set_*` tools, single-resource lookups by name (for example `get_instance_by_name`) | Current project only; `ALLOW_MODIFY_OPERATIONS=false` stays the default |

**Operator setups to document** (configured in OpenStack, not in the MCP server)

| Setup | Configuration | Note |
|---|---|---|
| A | `admin` role | Simple, over-privileged |
| B | Dedicated role with a policy override | Least privilege, recommended |
| C | Restricted Application Credential (role subset or access rules) in multi-user mode's request headers | Multi-user mode |

Fixed-credential mode warning: every client of the server reads with the server
credential's permissions.

**Validation**

| Type | Checks |
|---|---|
| Unit tests | Switch off makes no OpenStack call; 403 returns a failure; a single-project result adds the warning; modification tools stay project-scoped. |
| Live | Check actual policy rule names and defaults on the target cloud; compare `admin` (allowed) and `member` (denied), plus setup B when the test cloud's policy can be changed; record per service whether a denial is a 403 or a silently narrowed result; mark unmeasured setups as Live unverified. |

**Documents to update with the change** (each with its `.ko.md` file): README.md
(project scope wording, CLI-to-tool mapping), `docs/security.md`,
`docs/configuration.md`, `docs/multi-user-guide.md`, `docs/validation.md`.

## [Issue #73](https://github.com/call518/MCP-OpenStack-Ops/issues/73) follow-up

### Required to complete the full requested scope

- [ ] **Administrator cross-project reads**: tracked under
  [Issue #86](#issue-86-cross-project-reads) above.

### Optional follow-ups

- [ ] **OAuth or browser login**
  - Provide an alternative to manually configured Application Credential
    headers when browser-based onboarding is required.
  - This is not required for the existing Application Credential flow.

- [ ] **Claude Desktop per-user custom-header validation**
  - Verify that an individual connector can send each user's Application
    Credential headers without sharing them through an organization-level
    connector.
  - Record client version, header restrictions, and the live result without
    exposing credentials.

