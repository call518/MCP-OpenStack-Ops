**English** | [Korean](ToDo.ko.md)

# TODO

Last reviewed: 2026-11-15

This file tracks only outstanding work. Completed items are removed.

## [Issue #86](https://github.com/call518/MCP-OpenStack-Ops/issues/86) Cross-project reads

Cross-project reads are implemented for 16 read tools, gated by
`ALLOW_CROSS_PROJECT_READ`, with OpenStack policy deciding access, and setups
A, B and C were checked live. See
[cross-project reads guide](docs/cross-project-guide.md) and the 2026-11-13
and 2026-11-14 records in [validation](docs/validation.md).

- [ ] **Octavia-managed resources (undecided)**

With `all_projects=true`, instance lists also show Octavia amphora VMs in the
service project. Amphorae, and their ports and security groups, are managed by
Octavia, not by operators directly. Whether to show them is not decided yet.

| Item | Detail |
|---|---|
| Listing | Show or exclude amphorae in `all_projects` instance lists; one option is to exclude them by default, report the excluded count, and include them on request |
| Modification | When modification tools support multiple projects, decide whether to refuse amphorae and their ports and security groups |
| Identification | Prefer the Octavia API (amphora `compute_id`, VRRP and VIP ports) over name prefixes or the service project name; check the real values on the test cloud |
| Current state | Read tools show amphorae as `openstack server list --all-projects` does; modification tools reach only the current project, so service-project amphorae are out of reach |

## Application Credential in single-account mode

- [ ] **Accept an Application Credential in single-account mode (on hold, undecided)**

Single-account mode (MCPB, stdio, and HTTP without `--multi-user`) accepts only
`OS_USERNAME` and `OS_PASSWORD`. Application Credentials work only in
multi-user mode, through request headers. Adding
`OS_APPLICATION_CREDENTIAL_ID` and `OS_APPLICATION_CREDENTIAL_SECRET` would
change only the Keystone authentication step; endpoints, caching, and tools
would stay the same. The work is on hold because the risk that a user believes
the wrong account is in use may outweigh the benefit. Nothing is decided.

| Item | Detail |
|---|---|
| Both sets configured | Undecided: fail at startup, prefer the Application Credential with a warning, or select with `OS_AUTH_TYPE`. A local check showed that openstacksdk without `auth_type` picks password authentication and silently ignores the Application Credential |
| Scope variables | The project comes from the credential. `OS_PROJECT_NAME` and the domain variables must not be sent; a local check showed the Application Credential plugin keeps them as scope parameters. Keystone's response to that is live unverified |
| Partial input | Only the ID or only the secret must fail, without falling back to password authentication |
| Project lookup | Skip the `OS_PROJECT_NAME` fallback in `get_current_project_id` and use the token's project |
| Restricted credential | A role subset or access rules can make some tools return policy denials (HTTP 403); document this in the mapping Notes |
| Expiry | Report an expired or deleted credential clearly; reauthentication cannot recover it |
| MCPB | `os_username`, `os_password`, and `os_project_name` are `required: true`; they would become optional and the server would validate the combination |

## Concurrent tool calls in multi-user mode

- [ ] **Stop tool calls from blocking the event loop (on hold)**

114 of the 121 tools are `async def` functions that call the synchronous
OpenStack SDK directly, so one running tool call blocks the server's event
loop. In stdio and single-account HTTP this changes nothing for tool calls,
which run one at a time either way. In multi-user HTTP, one user's slow call
delays every other user. On hold because it is a performance issue only, and
correct behavior comes first.

| Item | Detail |
|---|---|
| Proposed change | Declare the 114 tools with `def`; fastmcp 4.1.6 runs `def` tools in a thread pool and passes contextvars. Add one middleware that runs calls with the same key one at a time in arrival order (`anyio.Lock`, FIFO): one global key in stdio and single-account HTTP, `project_id` in multi-user HTTP |
| Guarantee to keep | Today every call runs alone, in arrival order, after the previous one finishes. The lock keeps this within a project, including calls from different users of the same project. Running all calls concurrently was rejected: chained synchronous calls sent in parallel (network then subnet) could fail |
| Expected effect | Multi-user HTTP: calls for different projects no longer wait for each other. stdio and single-account HTTP: no change for tool calls |
| Tests to change | 21 calls in 6 test files that `await` tool functions |
| Release condition | Run the same requests on 3.9.2 and the new build (simple load balancer, network → subnet → router → security group rule chain) in Claude Desktop and OpenWebUI, plus concurrent calls from two projects in multi-user mode. Do not release if any result differs from 3.9.2 |

## Service status reporting

- [ ] **Report real service state in `get_service_status`**
  - Glance and Heat rows are not service records: they come from a list probe,
    with `host: unknown` and `updated_at` set to the server's local time, while
    Nova, Neutron and Cinder rows carry UTC heartbeats.
  - heat-engine, Octavia and Aodh are not reported. In a 2026-11-14 lab
    failure, heat-engine lost its database connection while `heat-api` was
    reported as up.
  - `running_services` counts the probe rows as running.

## Barbican and TLS listeners

- [ ] **Live-check the Barbican tools and `TERMINATED_HTTPS` listeners**
  - Checked live on 2026-11-15 (admin account): `set_secret`
    `create_self_signed_tls`, and a `TERMINATED_HTTPS` listener created with
    `default_tls_container_ref` by name that reached `ACTIVE`/`ONLINE` and
    served HTTPS (`curl -vk`: TLSv1.3, HTTP 200 from both members).
  - Still unit-tested only: the other Barbican tools and actions,
    `sni_container_refs`, listener `set` with TLS references, and the pool
    backend re-encryption parameters (including the client authentication
    `tls_container_ref`, sent through the Octavia API).
  - Also check non-terminated HTTPS (`HTTPS` listener and pool, `TLS-HELLO`
    monitor) and backend re-encryption with a CA-verified member, with and
    without client authentication.
  - Check on a cloud with Barbican: the role a project `member` needs to create
    secrets, whether Octavia grants its own ACL at listener creation (the
    2026-11-15 check used an admin account).

## [Issue #73](https://github.com/call518/MCP-OpenStack-Ops/issues/73) follow-up

### Validation follow-ups

These were listed as unconfirmed when #73 was closed.

- [ ] **Concurrent isolation of project-scoped credentials**
  - Isolation between two project-scoped Application Credentials was checked
    only in our lab with two disposable projects, not in a real deployment.
- [ ] **Credential revocation timing**
  - Revocation was observed once in our lab: the next request after deletion
    was rejected. No revocation bound has been measured.
- [ ] **Unreachable OpenStack service**
  - Check the reported error and that the server recovers once the service
    is reachable again.
- [ ] **End-to-end HTTPS**
  - The MCP side used HTTPS, but the test cloud's OpenStack APIs were
    HTTP-only behind temporary TLS proxies.
- [ ] **Cluster-status findings reported on 2026-10-28**
  - Permission-denied service checks, availability-zone field handling, and
    the floating-IP pool capacity calculation. The code changed afterwards
    (2026-10-30 and 2026-11-08); a live recheck is still pending.

### Optional follow-ups

- [ ] **OAuth or browser login**
  - Provide an alternative to manually configured Application Credential
    headers when browser-based onboarding is required.
  - This is not required for the existing Application Credential flow.

- [ ] **Claude Desktop remote connector per-user header validation**
  - `mcp-remote` in each user's `claude_desktop_config.json` was checked on
    2026-11-14. Remaining: verify that a remote custom connector can send each user's Application
    Credential headers without sharing them through an organization-level
    connector.
  - Record client version, header restrictions, and the live result without
    exposing credentials.

