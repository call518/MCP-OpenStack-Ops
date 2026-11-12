**English** | [Korean](ToDo.ko.md)

# TODO

Last reviewed: 2026-11-13

This file tracks only outstanding work. Completed items are removed.

## [Issue #86](https://github.com/call518/MCP-OpenStack-Ops/issues/86) Cross-project reads

The first phase is implemented: `all_projects=true` on six list tools, gated by
`ALLOW_CROSS_PROJECT_READ`, with OpenStack policy deciding access. See
[Cross-project reads](docs/security.md#cross-project-reads) and the 2026-11-13
records in [validation](docs/validation.md).

- [ ] **Remaining cross-project read work**

| Item | Detail |
|---|---|
| Policy rule names | Check the actual Nova, Cinder and Keystone all-projects rule names and defaults on the test cloud |
| Setup B validation | Add a dedicated role to those policy rules and confirm it reads across projects without `admin` |
| Setup C validation | Confirm a restricted Application Credential (role subset or access rules) in multi-user mode |
| Later services | Network, Image, Heat, and other services |
| Other-project details | `get_project_details` resource counts for a project other than the current one |

## [Issue #73](https://github.com/call518/MCP-OpenStack-Ops/issues/73) follow-up

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

