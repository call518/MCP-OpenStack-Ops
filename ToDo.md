**English** | [Korean](ToDo.ko.md)

# TODO

Last reviewed: 2026-11-13

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

## [Issue #73](https://github.com/call518/MCP-OpenStack-Ops/issues/73) follow-up

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

