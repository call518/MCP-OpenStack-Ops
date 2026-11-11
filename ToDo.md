**English** | [Korean](ToDo.ko.md)

# TODO

Last reviewed: 2026-11-11

This file tracks only outstanding work. Completed items are removed.

## [Issue #73](https://github.com/call518/MCP-OpenStack-Ops/issues/73) follow-up

### Required to complete the full requested scope

- [ ] **Administrator cross-project reads**
  - Keep regular users strictly limited to the project in their Application
    Credential.
  - Allow only policy-authorized administrators to list and look up resources
    across projects.
  - Keep cross-project modifications unavailable and preserve the global
    write-tool default of `ALLOW_MODIFY_OPERATIONS=false`.
  - Validate regular-user denial and administrator read behavior against a
    real multi-project OpenStack deployment.

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

