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
| `OS_PROJECT_DOMAIN_NAME` | Project domain name | `default` | Domain scope |
| `OS_USER_DOMAIN_NAME` | User domain name | `default` | Domain scope |
| `OS_REGION_NAME` | OpenStack region | `RegionOne` | Regional scope |
| **OpenStack Service Ports** |
| `OS_COMPUTE_PORT` | Compute service port | `8774` | Nova endpoint |
| `OS_NETWORK_PORT` | Network service port | `9696` | Neutron endpoint |
| `OS_VOLUME_PORT` | Volume service port | `8776` | Cinder endpoint |
| `OS_IMAGE_PORT` | Image service port | `9292` | Glance endpoint |
| `OS_PLACEMENT_PORT` | Placement service port | `8780` | Placement endpoint |
| `OS_HEAT_STACK_PORT` | Heat orchestration service port | `8004` | Heat API endpoint |
| `OS_HEAT_STACK_CFN_PORT` | Heat CloudFormation service port | `18888` | Heat CFN API endpoint (default: 8000, changed to avoid Docker port conflicts) |
| **MCP Server Configuration** |
| `MCP_LOG_LEVEL` | Logging level | `INFO` | Development debugging |
| `ALLOW_MODIFY_OPERATIONS` | Enable modify operations | `false` | Safety control for state modifications |
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

## OpenStack endpoint topology

Single-account and multi-user connections currently construct service URLs from
one `OS_AUTH_HOST`, `OS_AUTH_PROTOCOL`, and the `OS_*_PORT` values. This works
for compact deployments, API gateways, and virtual IPs that expose every listed
service on one host. The server does not currently discover different service
hosts or custom URL paths from the Keystone service catalog.

Before starting, confirm that these URLs are reachable from inside the
`mcp-server` container. If the cloud publishes different service hosts or paths,
place a gateway or reverse proxy at `OS_AUTH_HOST` that maps the configured ports
to those endpoints. Do not proceed by entering only the Keystone hostname; the
MCP server may authenticate successfully and then fail on the first service tool.

`OS_INTERFACE` does not change these explicit endpoint URLs. The current
single-host configuration uses the internal interface convention.

Every service URL is built even when the service is not deployed. If a firewall
silently drops traffic to such a port (for example `OS_VOLUME_PORT` on a cloud
without Cinder), calls to that service wait for the connection timeout instead
of failing immediately. Let the port be refused, or point it at a reachable
gateway, so that a missing service fails fast with an explicit error.

Aodh (`alarming`) and Gnocchi (`metric`) have no `OS_*_PORT` setting. Their
tools use the Keystone catalog endpoint for `OS_INTERFACE` and
`OS_REGION_NAME`, which must also be reachable from the `mcp-server` container.

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
python -m mcp_openstack_ops --type stdio

# Project 2: Development Environment
OS_PROJECT_NAME=development
# ... other config
python -m mcp_openstack_ops --type streamable-http --port 8001

# Project 3: Testing Environment
OS_PROJECT_NAME=testing
# ... other config
python -m mcp_openstack_ops --type streamable-http --port 8002
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
