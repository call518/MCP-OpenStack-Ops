**English** | [Korean](configuration.ko.md)

# Server configuration

This guide covers command-line options, environment variables, OpenStack
endpoint and HTTPS setup, MCP client configuration templates, multiple
projects, and changing the openstacksdk version for older OpenStack releases.

## Command Line Options

```bash
uv run python -m mcp_openstack_ops --help

Options:
  --log-level {DEBUG,INFO,WARNING,ERROR,CRITICAL}
                        Logging level
  --type {stdio,streamable-http}
                        Transport type (default: stdio)
  --host HOST          Host address for HTTP transport (default: 127.0.0.1)
  --port PORT          Port number for HTTP transport (default: 8080)
  --auth-enable        Enable Bearer token authentication for streamable-http mode
  --secret-key SECRET  Secret key for Bearer token authentication
  --multi-user         Use request-local Application Credentials (streamable-http only)
```

## Environment Variables

| Variable | Description | Default | Usage |
|----------|-------------|---------|--------|
| **OpenStack Authentication** |
| `OS_AUTH_HOST` | OpenStack Identity service host | Required | Authentication host address |
| `OS_AUTH_PORT` | OpenStack Identity service port | Required | Authentication port |
| `OS_AUTH_PROTOCOL` | Connection protocol (http or https) | `http` | Use `https` for production with SSL/TLS |
| `OS_CACERT` | SSL CA certificate path for HTTPS | Optional | Required for secure HTTPS connections (e.g., `/etc/ssl/certs/ca.pem`). If not set with HTTPS, SSL verification is disabled (insecure) |
| `OS_USERNAME` | OpenStack username | Required in single-account mode | Unused for multi-user request authentication |
| `OS_PASSWORD` | OpenStack password | Required in single-account mode | Unused for multi-user request authentication |
| `OS_PROJECT_NAME` | OpenStack project name | Required in single-account mode | Multi-user scope comes from each Application Credential |
| `OS_IDENTITY_API_VERSION` | Identity API version | `3` | API version |
| `OS_PROJECT_DOMAIN_NAME` | Project domain name | `Default` | Domain scope |
| `OS_USER_DOMAIN_NAME` | User domain name | `Default` | Domain scope |
| `OS_REGION_NAME` | OpenStack region | `RegionOne` | Regional scope |
| `OS_ENDPOINT_SOURCE` | Where service endpoints come from: `configured` or `catalog` | `configured` | `catalog` uses the Keystone catalog for every service; see [OpenStack endpoint topology](#openstack-endpoint-topology) |
| `OS_INTERFACE` | Catalog interface: `public`, `internal` or `admin` | `internal` | Selects catalog endpoints; use `public` from outside the cloud's internal network |
| **OpenStack Service Ports** |
| `OS_COMPUTE_PORT` | Compute service port | `8774` | Nova endpoint |
| `OS_NETWORK_PORT` | Network service port | `9696` | Neutron endpoint |
| `OS_VOLUME_PORT` | Volume service port | `8776` | Cinder endpoint |
| `OS_IMAGE_PORT` | Image service port | `9292` | Glance endpoint |
| `OS_PLACEMENT_PORT` | Placement service port | `8780` | Placement endpoint. No current tool calls the Placement API |
| `OS_HEAT_STACK_PORT` | Heat orchestration service port | `8004` | Heat API endpoint |
| `OS_HEAT_STACK_CFN_PORT` | Heat CloudFormation (CFN) service port | None | Not read by the server; setting it has no effect |
| **MCP Server Configuration** |
| `MCP_LOG_LEVEL` | Logging level | `INFO` | Development debugging |
| `ALLOW_MODIFY_OPERATIONS` | Enable modify operations | `false` | Safety control for state modifications |
| `ALLOW_CROSS_PROJECT_READ` | Enable `all_projects=true` on supported list tools | `false` | Exposes the feature only; OpenStack policy decides access. Advanced; see the [cross-project reads guide](cross-project-guide.md) |
| `LIST_MAX_LIMIT` | Most items one call of a list tool with a `limit` parameter returns (`get_instance_details`, `search_instances`, `get_instance`, `get_load_balancer_list`) | `100` | Positive integer. One instance row is roughly 300-400 tokens; lower it for small-context models, which then read further pages with `offset`. An invalid value makes those calls fail |
| `INSTANCE_FILTER_MAX_MATCHES` | Most instances a filter-based `set_instance` call may act on (`name_contains`, `status`, `flavor_contains`, `image_contains`) | `100` | Positive integer. More matches are refused without acting on any instance; an invalid value makes such calls fail. Independent of `LIST_MAX_LIMIT`: matches are collected in one internal listing |
| `FASTMCP_TYPE` | Transport type | `stdio` | Rarely needed to change |
| `FASTMCP_HOST` | HTTP host address | `127.0.0.1` | For HTTP mode only |
| `FASTMCP_PORT` | HTTP port number | `8080` | For HTTP mode only |
| **Authentication (Optional)** |
| `MCP_MULTI_USER` | Enable request-scoped per-user Application Credential authentication | `false` | Streamable HTTP only; requires HTTPS OpenStack endpoints by default and can be combined with shared Bearer authentication |
| `MCP_MULTI_USER_ALLOW_INSECURE_HTTP` | Allow multi-user OpenStack API requests over HTTP | `false` | Development/testing only; requires `MCP_MULTI_USER=true` and transmits credentials and tokens in plaintext |
| `REMOTE_AUTH_ENABLE` | Enable Bearer token authentication for streamable-http mode | `false` | Production security |
| `REMOTE_SECRET_KEY` | Shared secret for Bearer token authentication | Required when auth enabled | Checked before per-user authentication when both modes are enabled |
| **Docker Compose** |
| `DOCKER_BIND_ADDRESS` | Published-port bind address | `127.0.0.1` | Keep local when HTTP authentication is disabled |
| `DOCKER_EXTERNAL_PORT_OPENWEBUI` | OpenWebUI host port | `3000` | Browser access |
| `DOCKER_EXTERNAL_PORT_MCP_SERVER` | MCP server host port | `8000` | Direct MCP clients |
| `DOCKER_EXTERNAL_PORT_MCPO_PROXY` | MCPO host port | `8080` | OpenAPI proxy and docs |
| `MCPO_CONFIG_FILE` | MCPO configuration mounted by Compose | `mcp-config.json.http.local` | Copy the tracked HTTP template to this ignored local file before starting Compose |

## Local stdio clients

Claude Desktop (options 2 and 3 of the [Claude Desktop guide](claude-desktop-guide.md))
and [Codex](codex-guide.md) start the server themselves over stdio and pass its
settings as the `env` values in their own configuration file. The variables
fall into four groups:

| Group | Variables | If omitted |
| --- | --- | --- |
| Required | `OS_AUTH_HOST`, `OS_AUTH_PORT`, `OS_PROJECT_NAME`, `OS_USERNAME`, `OS_PASSWORD` | The server starts, but every OpenStack tool call fails with `Missing required OpenStack environment variables` |
| Optional | `OS_AUTH_PROTOCOL`, `OS_CACERT`, `OS_USER_DOMAIN_NAME`, `OS_PROJECT_DOMAIN_NAME`, `OS_REGION_NAME`, `OS_IDENTITY_API_VERSION`, `OS_ENDPOINT_SOURCE`, `OS_INTERFACE`, `OS_COMPUTE_PORT`, `OS_NETWORK_PORT`, `OS_VOLUME_PORT`, `OS_IMAGE_PORT`, `OS_PLACEMENT_PORT`, `OS_HEAT_STACK_PORT`, `MCP_LOG_LEVEL`, `ALLOW_MODIFY_OPERATIONS`, `ALLOW_CROSS_PROJECT_READ`, `LIST_MAX_LIMIT`, `INSTANCE_FILTER_MAX_MATCHES` | The default in [Environment Variables](#environment-variables) applies |
| Not used over stdio | `FASTMCP_TYPE`, `FASTMCP_HOST`, `FASTMCP_PORT`, `REMOTE_AUTH_ENABLE`, `REMOTE_SECRET_KEY`, `MCP_MULTI_USER`, `MCP_MULTI_USER_ALLOW_INSECURE_HTTP`, the Docker Compose keys, `PYTHONPATH` | Leave them out. The `--type stdio` argument selects the transport; `MCP_MULTI_USER=true` stops the server from starting, because multi-user mode requires `streamable-http` |
| Not read by the server | `OS_HEAT_STACK_CFN_PORT`, `OS_TENANT_NAME`, `OS_ENDPOINT_TYPE`, `OS_AUTH_PLUGIN` | No effect |

The client examples list every required and optional variable, with the
optional ones set to their defaults, so you only change the values your cloud
needs. An invalid `OS_ENDPOINT_SOURCE` or `OS_INTERFACE` stops the server at
startup; an invalid `LIST_MAX_LIMIT` or `INSTANCE_FILTER_MAX_MATCHES` makes the
calls that use it fail.

Put every value in the client configuration. A server run from a source
checkout also reads the clone's `.env` when it first connects to OpenStack; that
file fills only variables missing from `env`, and values in `env` take
precedence.

## Access modes and `.env` settings

Choose one access mode for the Docker Compose stack, then set the `.env` keys
in its column. The keys must agree: the MCP server takes its mode from
`MCP_MULTI_USER` and `REMOTE_AUTH_ENABLE`, while MCPO sends the headers in the
file named by `MCPO_CONFIG_FILE`. If they disagree, the server answers MCPO with
`401 Unauthorized` and OpenWebUI shows no OpenStack tools.

| `.env` key | 1. Single account (Quick Start default) | 2. Single account + Bearer | 3. Multi-user | 4. Multi-user + Bearer |
| --- | --- | --- | --- | --- |
| Who OpenStack sees | The one account in `.env` | The one account in `.env` | The Application Credential sent with each request | The Application Credential sent with each request |
| Typical use | One person on the same host | MCP or MCPO reachable from other hosts | A private instance per user | A private instance per user, behind a shared token |
| `MCP_MULTI_USER` | `false` | `false` | `true` | `true` |
| `REMOTE_AUTH_ENABLE` | `false` | `true` | `false` | `true` |
| `REMOTE_SECRET_KEY` | Empty | Strong random value | Empty | Strong random value |
| `MCPO_CONFIG_FILE` | `mcp-config.json.http.local` | `mcp-config.json.http.local` | `mcp-config.json.multi-user.local` | `mcp-config.json.multi-user.local` |
| Headers in that MCPO file | `Authorization` placeholder, ignored | `Authorization: Bearer <REMOTE_SECRET_KEY>` with the same value | Application Credential ID and secret; `Authorization` removed or ignored | `Authorization: Bearer <REMOTE_SECRET_KEY>` plus the Application Credential ID and secret |
| `OS_USERNAME`, `OS_PASSWORD`, `OS_PROJECT_NAME` | Required; every tool works in this project | Required; every tool works in this project | Not used; the credential sets user and project | Not used; the credential sets user and project |
| `OS_AUTH_PROTOCOL` | `http` or `https`, as Keystone is served | `http` or `https`, as Keystone is served | `https` | `https` |
| `MCP_MULTI_USER_ALLOW_INSECURE_HTTP` | `false` | `false` | `false`; `true` only for tests with `OS_AUTH_PROTOCOL=http` | `false`; `true` only for tests with `OS_AUTH_PROTOCOL=http` |
| `DOCKER_BIND_ADDRESS` | `127.0.0.1` | Reachable address, behind HTTPS | `127.0.0.1`, or a reachable address behind HTTPS | Reachable address, behind HTTPS |

These keys do not depend on the mode: `FASTMCP_TYPE=streamable-http` (always
for Compose), `OS_AUTH_HOST`, `OS_AUTH_PORT`, `OS_REGION_NAME`,
`OS_ENDPOINT_SOURCE`, `OS_INTERFACE`, the service ports, `ALLOW_MODIFY_OPERATIONS`, `ALLOW_CROSS_PROJECT_READ`, `LIST_MAX_LIMIT`
and `INSTANCE_FILTER_MAX_MATCHES`.

- A shared OpenWebUI used by several people should use mode 1 or 2. MCPO sends
  one fixed header set, so in modes 3 and 4 every OpenWebUI user acts as the one
  Application Credential in the MCPO file. Modes 3 and 4 are described in the
  [multi-user guide](multi-user-guide.md).
- After changing any of these keys or the MCPO file, recreate both containers:
  `docker compose up -d --force-recreate mcp-server mcpo-proxy`.
- The Claude Desktop extension bundle does not use this table; it takes its
  settings from the extension form ([Claude Desktop guide](claude-desktop-guide.md)).
  Other stdio clients use [Local stdio clients](#local-stdio-clients).

## OpenStack endpoint topology

`OS_ENDPOINT_SOURCE` selects how both connection modes find service endpoints.
Keystone is always reached at `OS_AUTH_PROTOCOL://OS_AUTH_HOST:OS_AUTH_PORT`.

| `OS_ENDPOINT_SOURCE` | Compute, network, volume, image, placement and Heat | Other services | Use when |
| --- | --- | --- | --- |
| `configured` (default) | Built from `OS_AUTH_HOST`, `OS_AUTH_PROTOCOL` and the `OS_*_PORT` values | Keystone catalog, `OS_INTERFACE` | Every listed service is exposed on one host: compact deployments, API gateways, virtual IPs |
| `catalog` | Keystone catalog, `OS_INTERFACE` | Keystone catalog, `OS_INTERFACE` | Services have their own hostnames or URL paths, for example `https://nova.example.com/v2.1` |

`OS_INTERFACE` (`public`, `internal` or `admin`; default `internal`) picks the
catalog endpoint for `OS_REGION_NAME`. Use the interface that is reachable from
the MCP server: from a laptop that is usually `public`, the value in the
project's OpenRC file. With `catalog`, the `OS_*_PORT` settings are ignored.
List the endpoints with `openstack catalog list` and check that those of the
chosen interface are reachable; in multi-user mode they must also use HTTPS.

### Configured endpoints

With `configured`, confirm before starting that the built URLs are reachable
from the MCP server (inside the `mcp-server` container for Docker Compose). If
the cloud publishes different service hosts or paths, use
`OS_ENDPOINT_SOURCE=catalog`, or place a gateway or reverse proxy at
`OS_AUTH_HOST` that maps the configured ports to those endpoints. Do not proceed
by entering only the Keystone hostname; the MCP server may authenticate
successfully and then fail on the first service tool.

Every configured service URL is built even when the service is not deployed. If
a firewall silently drops traffic to such a port (for example `OS_VOLUME_PORT`
on a cloud without Cinder), calls to that service wait for the connection
timeout instead of failing immediately. Let the port be refused, or point it at
a reachable gateway, so that a missing service fails fast with an explicit
error. With `catalog`, a service missing from the catalog fails immediately.

Aodh (`alarming`), Gnocchi (`metric`), Barbican (`key-manager`) and Octavia
(`load-balancer`) have no `OS_*_PORT` setting and always use the Keystone
catalog endpoint for `OS_INTERFACE` and `OS_REGION_NAME`, which must also be
reachable from the MCP server.

## HTTPS and private CA setup

For HTTPS OpenStack endpoints signed by a public CA, use the system CA bundle
already present in the container:

```dotenv
OS_AUTH_PROTOCOL=https
OS_CACERT=/etc/pki/tls/certs/ca-bundle.crt
```

For a private CA, the certificate must exist inside the `mcp-server` container;
a host path in `.env` alone is not enough.

Uncomment and replace the CA volume example under `mcp-server` in
`docker-compose.yml`:

```yaml
volumes:
  - /absolute/host/path/openstack-ca.pem:/etc/ssl/certs/openstack-ca.pem:ro
```

Then configure the container path, recreate the MCP path, and check its logs:

```dotenv
OS_AUTH_PROTOCOL=https
OS_CACERT=/etc/ssl/certs/openstack-ca.pem
```

```bash
docker compose up -d --force-recreate mcp-server mcpo-proxy
docker compose logs mcp-server
```

Without `OS_CACERT`, single-account HTTPS disables certificate verification and
is not a secure production configuration. Multi-user mode fails closed unless
HTTPS is enabled, and its full requirements are documented in the
[multi-user guide](multi-user-guide.md).

## MCP client configuration templates

The tracked `mcp-config.json.*` files are reference templates. Before adding
credentials, copy only the template you need; all matching `.local` files are
ignored by Git:

```bash
cp mcp-config.json.http mcp-config.json.http.local
cp mcp-config.json.multi-user mcp-config.json.multi-user.local
cp mcp-config.json.multi-project mcp-config.json.multi-project.local
cp mcp-config.json.stdio mcp-config.json.stdio.local
chmod 600 mcp-config.json.*.local
```

For MCPO, select the copy in `.env`, for example
`MCPO_CONFIG_FILE=mcp-config.json.multi-user.local`. Point non-Compose clients
to their local copy separately. Never put real credentials in a tracked
template.

## Multi-project configuration

Each MCP server instance is scoped to one project (see
[Project isolation](security.md#project-isolation)). For managing multiple
OpenStack projects, deploy multiple MCP server instances with different
`OS_PROJECT_NAME` values:

**Example: Managing 3 Projects**

```bash
# Project 1: Production Environment
OS_PROJECT_NAME=production
# ... other config
uv run python -m mcp_openstack_ops --type stdio

# Project 2: Development Environment
OS_PROJECT_NAME=development
# ... other config
uv run python -m mcp_openstack_ops --type streamable-http --port 8001

# Project 3: Testing Environment
OS_PROJECT_NAME=testing
# ... other config
uv run python -m mcp_openstack_ops --type streamable-http --port 8002
```

**Claude Desktop Multi-Project Configuration Example:**

```json
{
  "mcpServers": {
    "openstack-production": {
      "command": "python",
      "args": ["-m", "mcp_openstack_ops", "--type", "stdio"],
      "env": {
        "OS_PROJECT_NAME": "production",
        "OS_USERNAME": "<user>",
        "OS_PASSWORD": "<password>",
        "OS_AUTH_HOST": "<keystone-host>"
      }
    },
    "openstack-development": {
      "command": "python",
      "args": ["-m", "mcp_openstack_ops", "--type", "stdio"],
      "env": {
        "OS_PROJECT_NAME": "development",
        "OS_USERNAME": "<user>",
        "OS_PASSWORD": "<password>",
        "OS_AUTH_HOST": "<keystone-host>"
      }
    },
    "openstack-testing": {
      "command": "python",
      "args": ["-m", "mcp_openstack_ops", "--type", "stdio"],
      "env": {
        "OS_PROJECT_NAME": "testing",
        "OS_USERNAME": "<user>",
        "OS_PASSWORD": "<password>",
        "OS_AUTH_HOST": "<keystone-host>"
      }
    }
  }
}
```

This allows Claude to access each project independently with complete isolation between environments.

**📁 Reference Configuration File:**

A complete multi-project configuration example is available at `mcp-config.json.multi-project`:
- **Production**: Read-only operations for safety (`ALLOW_MODIFY_OPERATIONS=false`)
- **Development**: Full operations enabled (`ALLOW_MODIFY_OPERATIONS=true`)
- **Testing**: Debug logging enabled (`MCP_LOG_LEVEL=DEBUG`)

```bash
# Preserve the tracked template and customize only the ignored local copy
cp mcp-config.json.multi-project mcp-config.json.multi-project.local
chmod 600 mcp-config.json.multi-project.local
# Point the client to this file, or merge its contents into the client's
# existing private configuration. Do not overwrite an existing client config.
```

## OpenStack SDK version for older releases

For older OpenStack releases (Wallaby, Caracal, Bobcat, etc.), you may need to
change the openstacksdk version to match your environment. The `uv`
environment, the Claude Desktop bundle and the `mcp-server` Docker image all
install the dependency versions recorded in `uv.lock`, so change the version in
`pyproject.toml` and regenerate the lock. The recommended versions per release
are in the README [compatibility table](../README.md#compatibility).

**Step 1: Modify `pyproject.toml`**
```toml
dependencies = [
    "openstacksdk==3.1.1",  # ← Change to your required version (e.g., 3.1.1 for Wallaby)
    # ... other dependencies unchanged
]
```

**Step 2: Update `uv.lock`**
```bash
uv lock --upgrade-package openstacksdk
uv run --extra dev python -m pytest -q tests
```

**Step 3: Rebuild the Docker image**

`Dockerfile.MCP-Server` installs exactly the packages in `uv.lock`. Change
`VERSION` in `build-mcp-server-docker-image.sh` and the `mcp-server` image tag in
`docker-compose.yml` to a new tag, then build and start:
```bash
./build-mcp-server-docker-image.sh
docker compose up -d
```

> ⚠️ **Important**: Do not edit package versions in `Dockerfile.MCP-Server`; the image build fails if `uv.lock` does not match `pyproject.toml`. The `mcpo-proxy` image (`Dockerfile.MCPO-Proxy`) pins its own packages: mcpo 0.0.20 needs mcp 1.x (it fails to start with mcp 2.x) and FastAPI 0.128.0 (it fails with FastAPI 0.162.2). An mcp 1.x proxy still connects to the mcp 2.x server.
