# Multi-user HTTP setup and usage guide

The server provides an opt-in, experimental multi-user HTTP mode. It keeps
existing project ownership checks and the default write restriction. The normal
single-account HTTP and stdio modes remain available without this option.

## Authentication

Clients send their own Keystone Application Credential ID and secret in two
dedicated HTTP headers on **every request**. The server authenticates against
the operator-configured Keystone, then executes the request with that user's
project-scoped connection. Authentication failure never falls back to the server's
environment account. This is custom header authentication, not an OAuth server or
Keystone token passthrough.

Shared Bearer authentication is optional and independent. With
`REMOTE_AUTH_ENABLE=true`, the server requires `Authorization: Bearer <token>`
before it attempts Keystone authentication. Every request must then pass both the
shared Bearer gate and the caller's Application Credential authentication.
`Authorization` is never forwarded to OpenStack. With Bearer authentication
disabled, a configured `REMOTE_SECRET_KEY` is ignored.

Application Credentials avoid LDAP passwords
and already specify a project and delegated roles. Raw Keystone tokens, browser
login, project switching, and administrator cross-project access are not supported. Use another Application Credential/client entry for another project.

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

## Create a client Application Credential

Each client user creates an Application Credential while authenticated to the
OpenStack project that the client should manage. For example, after loading that
project's OpenRC file:

```bash
source /path/to/project-openrc.sh
openstack application credential create mcp-openwebui \
  --description "MCP OpenWebUI access"
```

The create response contains `id` and `secret`. Configure them as
`X-OpenStack-Application-Credential-ID` and
`X-OpenStack-Application-Credential-Secret`, respectively. The secret is shown
only in the create response, but it is reusable until the credential expires or
is deleted. If it is lost, delete the credential and create another one:

```bash
openstack application credential delete mcp-openwebui
```

`openstack application credential list` and `show` can recover the ID, but never
the secret. Keep the create output private. Do not paste it into chat, commit it,
or store it in a shared OpenWebUI/MCPO configuration. Prefer a dedicated,
least-privileged OpenStack user, review the delegated roles in the create output,
and use `--role` and `--expiration` when the cloud's policy and operational
requirements are known. Do not create an administrator-scoped credential unless
administrator behavior is explicitly required.

See the official [OpenStack Application Credential CLI documentation](https://docs.openstack.org/python-openstackclient/latest/cli/command-objects/identity/v3/index.html#application-credential).

## Server setup

With Git, Python 3.12+, and uv installed on the server, clone and install
`main` to use this mode from source:

```bash
git clone --branch main --single-branch \
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
export MCP_MULTI_USER=true
export REMOTE_AUTH_ENABLE=false
export REMOTE_SECRET_KEY=
# Optional for a private CA:
# export OS_CACERT=/path/to/cloud-ca.pem
uv run --locked python -m mcp_openstack_ops \
  --type streamable-http --host 127.0.0.1 --port 8080
```

Alternatively set `MCP_MULTI_USER=true` instead of passing `--multi-user`.
These are process environment variables; the new mode does not load a server
credential `.env` or `clouds.yaml`. `OS_USERNAME`, `OS_PASSWORD`, and
`OS_PROJECT_NAME` are not used for user authentication. DEBUG logging is rejected
to avoid authentication wire dumps.

To require shared Bearer authentication before per-user authentication, configure:

```bash
export MCP_MULTI_USER=true
export REMOTE_AUTH_ENABLE=true
export REMOTE_SECRET_KEY='<strong-random-secret>'
```

The two checks use AND semantics, never fallback or OR semantics. A missing or
invalid Bearer token returns 401 without contacting Keystone. A valid Bearer token
is followed by the normal Application Credential check. Bearer-only and unauthenticated
single-account HTTP modes remain available when `MCP_MULTI_USER=false`.

Unsupported OAuth metadata routes (`/.well-known/oauth-protected-resource`,
`/.well-known/oauth-authorization-server`, `/.well-known/openid-configuration`,
including their path suffixes) and `/register` return 404 without Keystone
authentication. This mode does not provide OAuth discovery or registration;
`/mcp` still requires both application-credential headers and, when enabled, the
shared Bearer header.

HTTP 400 responses from the MCP transport produce an INFO diagnostic with a
server-generated `request_id` and a fixed `reason` classification:
`invalid_json`, `invalid_jsonrpc`, `unsupported_protocol`, `missing_session_id`,
or `unclassified`. Request bodies, header values, and raw error messages are not
included in this diagnostic. Unknown, oversized, or non-JSON error responses
may remain unclassified. A 400 alone does not establish an authentication failure
or explain the reported first-connection behavior; correlate its request ID
with the client response before drawing a conclusion. A client may probe with a
newer protocol version, receive `unsupported_protocol`, and then negotiate a
supported version successfully. Check whether initialization and subsequent
requests succeed before treating that rejection as a connection failure. Do not
bypass protocol validation merely to suppress the initial 400 response.


Expose `/mcp` through an HTTPS reverse proxy. Do not expose the plaintext backend
port to clients. Configure the proxy to redact both credential headers and
`Authorization`, avoid request/header dumps, and enforce rate and concurrency
limits before forwarding authentication attempts. Review APM, crash dumps,
swap, and external log collectors separately; application cleanup cannot control
those systems. Clients necessarily keep credentials in their own configuration
or secret store; the server's non-persistence rule does not cover client storage.

This follows the existing configured-host deployment layout: compute, network,
volume, image, placement, and Heat endpoints use `OS_AUTH_HOST` with the existing
`OS_*_PORT` variables, using HTTPS with certificate verification by default. The
identity URL ends in `/v3`. Other SDK services use the Keystone catalog, whose
endpoints must use the same protocol. Plaintext SDK requests are rejected unless
the explicit test-only override below is enabled. Redirected requests are always
rejected. Existing manual Heat/Octavia probes use the validated configured
protocol and do not follow redirects. Deployments with HTTP-only internal
services cannot use this mode securely without HTTPS endpoints. Standard system
trust applies if no CA path is set; there is no implicit `verify=False` fallback.

For isolated development or functional testing against an HTTP-only OpenStack
cloud, the HTTPS guard can be explicitly disabled:

```bash
export MCP_MULTI_USER=true
export MCP_MULTI_USER_ALLOW_INSECURE_HTTP=true
export OS_AUTH_PROTOCOL=http
```

This sends Application Credential secrets and issued tokens in plaintext. Use
only an isolated test network and a disposable, least-privileged credential with
a short expiration, then delete it after testing. The option defaults to `false`,
emits an `INSECURE TEST MODE` warning at startup, and must never be enabled in
production. Redirects remain disabled in both modes.

## Client compatibility

| Client | Initial status |
| --- | --- |
| Claude Code CLI | Version 2.1.312 registered and tested against a real HTTPS MCP server |
| Claude Code IDE integration | Not separately tested |
| Claude Desktop individual connector | Conditional on request-header availability and an independently owned credential configuration; unverified |
| Claude Desktop organization-shared fixed headers | Not suitable for per-user identities; do not share one person's credential |
| OpenWebUI/MCPO, independent instance per user | Compatible when its fixed upstream headers contain only that user's Application Credential; unverified |
| OpenWebUI/MCPO, one shared connection for multiple users | Not suitable: its fixed upstream headers would give every UI user the same OpenStack identity |
| Clients requiring OAuth | Not supported by this custom authentication mode |

Claude Code example (user configuration; placeholders only):

```json
{
  "mcpServers": {
    "openstack-personal": {
      "type": "http",
      "url": "https://mcp.example.com/mcp",
      "headers": {
        "Authorization": "Bearer <shared-mcp-token>",
        "X-OpenStack-Application-Credential-ID": "<your-application-credential-id>",
        "X-OpenStack-Application-Credential-Secret": "<your-application-credential-secret>"
      }
    }
  }
}
```

The placeholder `Authorization` header may remain when
`REMOTE_AUTH_ENABLE=false`; the server ignores it. When authentication is
enabled, replace the placeholder so every client receives the shared MCP token
separately from its own Application Credential.

The Docker Compose Quick Start uses an ignored `mcp-config.json.http.local` copy
of `mcp-config.json.http` for unauthenticated single-account access. For an
independent multi-user OpenWebUI/MCPO instance, the repository provides this
separate template:

```json
{
  "mcpServers": {
    "mcp-openstack-ops": {
      "type": "streamable-http",
      "url": "http://mcp-server:8000/mcp",
      "headers": {
        "Authorization": "Bearer <REMOTE_SECRET_KEY>",
        "X-OpenStack-Application-Credential-ID": "<APPLICATION_CREDENTIAL_ID>",
        "X-OpenStack-Application-Credential-Secret": "<APPLICATION_CREDENTIAL_SECRET>"
      }
    }
  }
}
```

This is the content of `mcp-config.json.multi-user`. It can technically be
edited and selected directly, but replacing its placeholders would put reusable
secrets in a version-controlled file and expose them in Git diffs or accidental
commits. The recommended workflow preserves the tracked template:

```bash
cp mcp-config.json.multi-user mcp-config.json.multi-user.local
chmod 600 mcp-config.json.multi-user.local
```

Put that user's Application Credential ID and secret in the ignored `.local`
copy. Keep or remove its `Authorization` entry according to
`REMOTE_AUTH_ENABLE`, then set these values in the private `.env` file:

```dotenv
MCP_MULTI_USER=true
MCPO_CONFIG_FILE=mcp-config.json.multi-user.local
```

Recreate the affected services with `docker compose up -d --force-recreate
mcp-server mcpo-proxy`. Do not use this pattern for a shared OpenWebUI
connection: all UI users would inherit the same OpenStack identity. The local
file contains reusable secrets; keep it private and never commit it. The
Quick Start's plaintext local MCP hop is for isolated evaluation only; use TLS
between the client/proxy and MCP server in production.

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

## Deployment validation checklist

Use disposable test projects and independently created credentials. Record client
versions, service versions, and results without posting secrets or resource data.

1. Connect from Claude Code with a project-scoped Application Credential. List
   tools and resources; confirm expected project data is returned.
2. Keep users A and B in different projects active concurrently. Query each
   project's instances repeatedly; neither response should contain the other
   project's private resources. Public/shared resources remain governed by the
   existing checks and service policy. Project isolation is not ownership per user.
3. Look up a known private resource ID from the other project: access must fail.
   Even an admin credential remains subject to the same project ownership checks.
4. Connect the same user with two separate project credentials/client entries;
   verify each entry sees only its intended project.
5. Omit, invalidate, or duplicate either credential header. No tool must execute,
   even if the server has valid legacy credentials configured in its environment.
   When shared Bearer authentication is enabled, also omit or invalidate its header
   and verify that Keystone authentication is not attempted.
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
including synchronous tools, Bearer-before-Keystone ordering, cleanup, default
write gating, project checks, and legacy cache behavior. They do not establish
actual Keystone revocation timing, service policy enforcement, or Claude client
compatibility.
