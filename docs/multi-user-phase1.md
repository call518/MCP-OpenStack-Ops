# Multi-user HTTP: phase 1 testing

This branch adds an opt-in, experimental remote mode for issue #73. It keeps
existing project ownership checks and the default write restriction. The normal
single-account HTTP and stdio modes remain available without this option.

## Initial authentication approach

Clients send their own Keystone Application Credential ID and secret in two
dedicated HTTP headers on **every request**. The server authenticates against
the operator-configured Keystone, then executes the request with that user's
project-scoped connection. Authentication failure never falls back to the server's
environment account. `Authorization` is not forwarded to OpenStack; this is custom
header authentication, not an OAuth server or Keystone token passthrough.

Application Credentials are the initial method because they avoid LDAP passwords
and already specify a project and delegated roles. Raw Keystone tokens, browser
login, project switching, and administrator cross-project access are not provided
in phase 1. Use another Application Credential/client entry for another project.

The HTTP transport is stateless with JSON responses. Every HTTP request creates a
fresh Keystone authentication and SDK connection; there is no authentication or
connection cache between requests. Connections and HTTP pools are closed when
the response finishes, including tool failures. SDK keyring caching is disabled.
No credentials are deliberately written to files or databases. Closing releases
references; it does not promise cryptographic erasure of Python process memory.

This trades extra authentication traffic for a smaller initial security boundary.
Keystone may cache credential validation internally. There is **no verified
numeric revocation guarantee yet**: once Keystone rejects a revoked credential,
the next HTTP request is rejected. An already authenticated, in-flight operation
can finish; it is not cancelled or rolled back. Measure the actual interval in
the target cloud before documenting a supported bound. Request validation is not
the same as cancelling already submitted asynchronous OpenStack operations.

## Server setup

With Git, Python 3.12+, and uv installed on the server, clone and install the
test branch instead of using `main` or a published release:

```bash
git clone --branch feat/73-per-user-connections --single-branch \
  https://github.com/call518/MCP-OpenStack-Ops.git
cd MCP-OpenStack-Ops
uv sync --locked --extra dev
```

`uv sync` installs the checked-out source and its locked dependencies into the
project environment; a separate `pip install -e .` is not needed. The `dev` extra
includes the dependencies for the validation tests below.

From that directory, configure and start the server:

```bash
export OS_AUTH_HOST=cloud.example.com
export OS_AUTH_PORT=5000
export OS_AUTH_PROTOCOL=https
export OS_REGION_NAME=RegionOne
export ALLOW_MODIFY_OPERATIONS=false
# Optional for a private CA:
# export OS_CACERT=/path/to/cloud-ca.pem
uv run --locked python -m mcp_openstack_ops \
  --type streamable-http --multi-user --host 127.0.0.1 --port 8080
```

Alternatively set `MCP_MULTI_USER=true` instead of passing `--multi-user`.
These are process environment variables; the new mode does not load a server
credential `.env` or `clouds.yaml`. `OS_USERNAME`, `OS_PASSWORD`, and
`OS_PROJECT_NAME` are not used for user authentication. Unset `REMOTE_AUTH_ENABLE`
and `REMOTE_SECRET_KEY`: the shared Bearer mode cannot be combined with this mode.
DEBUG logging is rejected to avoid authentication wire dumps.

Expose `/mcp` through an HTTPS reverse proxy. Do not expose the plaintext backend
port to clients. Configure the proxy to redact both credential headers and
`Authorization`, avoid request/header dumps, and enforce rate and concurrency
limits before forwarding authentication attempts. Review APM, crash dumps,
swap, and external log collectors separately; application cleanup cannot control
those systems. Clients necessarily keep credentials in their own configuration
or secret store; the server's non-persistence rule does not cover client storage.

This follows the existing configured-host deployment layout: compute, network,
volume, image, placement, and Heat endpoints use `OS_AUTH_HOST` with the existing
`OS_*_PORT` variables, now over HTTPS with certificate verification. The identity
URL ends in `/v3`. Other SDK services use the Keystone catalog, whose endpoints
must also support HTTPS. Plaintext SDK requests, including redirected requests,
are rejected. Existing manual Heat/Octavia probes use HTTPS in this mode and do
not follow redirects. Deployments with HTTP-only internal services cannot use
this mode without HTTPS endpoints. Standard system trust applies if no CA path is
set; there is no implicit `verify=False` fallback.

## Client compatibility

| Client | Initial status |
| --- | --- |
| Claude Code CLI | Version 2.1.312 registered and tested against a real HTTPS MCP server |
| Claude Code IDE integration | Not separately tested |
| Claude Desktop individual connector | Conditional on request-header availability and an independently owned credential configuration; unverified |
| Claude Desktop organization-shared fixed headers | Not suitable for per-user identities; do not share one person's credential |
| Clients requiring OAuth | Not supported by this custom authentication mode |

Claude Code example (user configuration; placeholders only):

```json
{
  "mcpServers": {
    "openstack-personal": {
      "type": "http",
      "url": "https://mcp.example.com/mcp",
      "headers": {
        "X-OpenStack-Application-Credential-ID": "<your-application-credential-id>",
        "X-OpenStack-Application-Credential-Secret": "<your-application-credential-secret>"
      }
    }
  }
}
```

Keep real values in private user configuration, never a committed `.mcp.json` or
an issue comment. Header values must be sent on initialize, discovery, and tool
requests. The user and project come from Keystone, never client-supplied role or
project headers. No local OpenStack SDK, CLI, bridge, or server is required on
the client machine.

Claude Desktop's remote connector headers are a limited beta. Custom header names
may require Anthropic approval, and organization-level fixed credentials can be
shared by everyone using a connector. Do not substitute an organization-wide
credential for per-user access. If independent per-user header configuration is
unavailable, Desktop is not yet supported for this phase; an OAuth flow would be
a separate design decision, not a silent fallback to shared credentials.

Sources checked while designing this branch:

- [Claude Code HTTP configuration](https://code.claude.com/docs/en/mcp)
- [Claude connector request-header limitations](https://claude.com/docs/connectors/custom/add-unlisted#authenticate-with-request-headers)
- [Keystone Application Credentials](https://docs.openstack.org/keystone/latest/user/application_credentials.html)

## Validation checklist for the issue author

Use disposable test projects and independently created credentials. Record client
versions, service versions, and results without posting secrets or resource data.

1. Connect from Claude Code with a project-scoped Application Credential. List
   tools and resources; confirm expected project data is returned.
2. Keep users A and B in different projects active concurrently. Query each
   project's instances repeatedly; neither response should contain the other
   project's private resources. Public/shared resources remain governed by the
   existing checks and service policy. Project isolation is not ownership per user.
3. Look up a known private resource ID from the other project: access must fail.
   Even an admin credential remains under the existing project checks in phase 1.
4. Connect the same user with two separate project credentials/client entries;
   verify each entry sees only its intended project.
5. Omit, invalidate, or duplicate either credential header. No tool must execute,
   even if the server has valid legacy credentials configured in its environment.
6. Confirm write tools are absent by default, including for administrators. Only
   in a disposable environment, explicitly enable writes and verify a credential
   delegated only `reader` cannot modify resources under the cloud's actual policy.
7. Revoke an Application Credential during use. Repeat calls and record the last
   accepted and first rejected request times. Verify a fresh connection also fails.
8. Verify server/proxy logs identify user ID, project ID, tool name, and HTTP
   completion without credential ID/secret or Keystone tokens. HTTP 200 indicates
   delivery, not necessarily success of the OpenStack operation.
9. Re-run a legacy stdio and single-account HTTP deployment without the new flag.
10. Test Desktop only if independent personal header configuration is available;
    report unavailable UI/header approval restrictions rather than sharing a key.

Automated checks (no real OpenStack calls):

```bash
uv run --locked --extra dev python -m pytest -q tests
```

Automated tests cover authentication rejection/revalidation, concurrent contexts
including synchronous tools, cleanup, default write gating, project checks, and
legacy cache behavior. They do not establish actual Keystone revocation timing,
service policy enforcement, or Claude client compatibility.

## Local cloud validation (2026-10-29)

Real-cloud testing used two disposable projects, two non-admin users, and one
private network per project. An additional reader-only Application Credential
verified delegated role enforcement. Initial empty-list validation passed 36
checks. Follow-up validation added one Cirros VM (`m1.tiny`: 1 vCPU, 512 MB RAM,
1 GB disk) and one empty 1 GB volume per project. All 66 recorded follow-up checks
passed; the latest unit-test run passed 46 tests.

The test used real Keystone, Nova, Neutron, and Cinder APIs through temporary
loopback TLS proxies with certificate verification. The proxy-to-cluster leg was
HTTP because the test cluster has no TLS on its API ports. MCP calls went through
the actual FastMCP ASGI HTTP application using an HTTP test client; this was not a
Claude Code or Desktop session and does not validate a production TLS deployment.

Validated behavior:

- Concurrent users retained their own project identity and private network view.
- Lookup of the other project's private network ID returned 403/404.
- Registered instance, network, and volume read tools returned only the expected
  project resources. Own-instance detail queries succeeded; SDK detail queries
  for the other project's VM and volume IDs returned 403/404.
- Write tools were absent by default; a test-only SDK write probe with reader
  credentials was rejected with HTTP 403 by Neutron.
- Missing, invalid, and deleted credentials were rejected with HTTP 401.
- After credential deletion, the very next request was rejected. This observation
  is not a deployment-independent revocation SLA.
- Captured application logs identified users and tools without any known test
  passwords, Application Credential IDs/secrets, or issued tokens appearing.
- All test Application Credentials were deleted and both test users disabled.
  The two isolated projects and private networks were retained for follow-up.
- Both VMs reached `ACTIVE`, and both volumes reached `available`. All four were
  deleted after testing; Nova instance/core/RAM and Cinder volume/GB quota usage
  and reservations returned to zero in both projects.

Testing exposed and fixed Cinder's SDK service-name/version/project-URL setup and
classification of Keystone's deleted-credential `NotFound` response as 401 rather
than 503. The populated-resource follow-up required no additional application
changes. Claude Desktop/IDE, sustained load, guest networking/SSH, volume
attachment/I/O, and a complete production HTTPS path remain unverified.

## Actual Claude Code validation (2026-10-29)

Claude Code 2.1.312 was used as the real MCP client, not an ASGI test client.
Two isolated Claude configuration directories registered the server with
`claude mcp add-json --scope user`. The server ran on a real HTTPS TCP listener
with certificate verification; the temporary cloud-side TLS proxies described
above remained necessary. No tools or OpenStack responses were mocked.

Both clients executed the request "Show me the overall cluster status" through
the actual configured Claude API. Initialization reported the user-scoped MCP
server as `connected`; CLI stream events and server audit logs confirmed actual
calls to registered service-status, monitoring, instance, network, and volume
tools. A second request for each user's named private network confirmed that
the actual client returned its own network ID rather than the other project's.
All 28 connection/isolation/cleanup checks passed. Temporary registrations were
removed, credentials deleted, and test users disabled afterward. Original Claude
configuration was left unchanged; test credentials were not found in client
configuration files or captured server logs.

**Connection validation is not a complete status-report accuracy pass.** The
real prompt exposed existing reporting defects outside the connection layer:

- `functions.get_service_status` omits some services after permission failures
  and uses a fixed "skipped" Heat entry without actually checking Heat.
- Compute/volume availability zones read a nonexistent `available` attribute
  rather than the SDK's `state['available']`, incorrectly defaulting to false.
- Resource-monitoring capacity zeros cannot establish physical capacity when
  hypervisor access is denied. A project-scoped user cannot assess global health.

These findings were identified during validation and have not been repaired in
this test step. Do not treat the model's successful completion or its availability
summary as proof that the whole cluster is healthy or unavailable.

## Ordinary-user Claude Code queries (2026-10-29)

Administrator-only API denials are expected for ordinary users and are not a
phase-1 authentication/connection failure. Each of the two real, registered
Claude Code clients therefore executed these ordinary project requests:

| Request | Actual tool | Observed result for both users |
| --- | --- | --- |
| List all instances in the project | `get_instance` | Empty after VM cleanup |
| Show all networks and their subnets | `get_network_details` | Own private network and shared external network; no other test project's private network |
| List all volumes and their status | `get_volume_list` | Empty after volume cleanup |

All six actual Claude requests completed, and all 52 recorded connection,
tool-execution, isolation, credential/logging, and cleanup checks passed. Own
fixture networks have no subnets because none were created. Missing subnet
details for a shared network do not establish that the network has no subnets.
The earlier populated VM/volume test remains the evidence for nonempty resource
isolation. Test registrations and credentials were removed and users disabled.

These results validate the phase-1 project-user workflow separately from global
administrator reporting. They do not certify every legacy reporting field: an
optional `get_floating_ip_pools` call exposed an existing placeholder calculation
of 100 IPs per allocation pool. That is not a measured pool capacity and was not
counted as a verified result. The status/AZ reporting findings above also remain.

## Default WSL Claude configuration validation (2026-10-29)

A further test used the actual default WSL Claude user configuration at
`/root/.claude.json`, without a `CLAUDE_CONFIG_DIR` override or `--mcp-config`.
`claude mcp add-json --scope user` registered `openstack73-a` and `openstack73-b`
sequentially. Plain `claude mcp list` confirmed `Connected`; an independent plain
CLI invocation also confirmed the active registration. Each registration was
kept visible briefly for inspection before executing the three project queries.

All six actual Claude queries and all 57 recorded checks passed, including
correct server selection, real tool results, private-network isolation, and
cleanup. These registrations used the real server on WSL-only HTTP loopback;
the cloud-side TLS proxies remained as above. A same-user, permission-restricted
Unix-socket helper supplied credential headers from memory, so no credential
values were stored in the normal user registration or command arguments.

The initial attempt with both entries simultaneously present did not validate
both clients: one remained `pending`. The successful default-configuration test
therefore establishes sequential registrations, not simultaneous same-profile
multi-entry support. Earlier simultaneous-client tests used separate profiles.

Only the test registrations were removed afterward. Existing MCP registrations
were preserved, test credentials deleted, and test users disabled. The temporary
helper/server stopped after the test, so saved commands are an execution record,
not sufficient to reconnect without restarting the test infrastructure.
