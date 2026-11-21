**English** | [Korean](codex-guide.ko.md)

# Codex

Codex in the ChatGPT desktop app, Codex CLI, and the Codex IDE extension share
one configuration file, `~/.codex/config.toml` (the `.codex` folder in your home
directory). Add one `[mcp_servers.<name>]` table there; all three use it. A
`.codex/config.toml` inside a trusted project limits the server to that project.

Choose **one** of the following options:

| Option | Use when | Requirements on the Codex computer |
| --- | --- | --- |
| [1. PyPI package with `uvx`](#option-1-pypi-package-with-uvx) | Codex starts the released server locally over stdio | uv, network access to the OpenStack APIs |
| [2. Existing HTTP server](#option-2-existing-http-server) | Reuse the running Docker Compose `mcp-server`, or any Streamable HTTP server | Network access to the MCP server |

The file stores the values you put in it in plain text; keep it private and do
not commit it.

## Option 1: PyPI package with uvx

`uvx` is included with [uv](https://docs.astral.sh/uv/). It downloads the
`mcp-openstack-ops` package from [PyPI](https://pypi.org/project/mcp-openstack-ops/)
and runs it in a cached tool environment. Download it once before the first
Codex start:

```bash
uvx mcp-openstack-ops --help
```

Later runs reuse the cached version and do not check for updates. To upgrade,
run `uvx mcp-openstack-ops@latest --help` and restart Codex.

Add this to `~/.codex/config.toml`:

```toml
[mcp_servers.MCP-OpenStack-Ops]
command = "uvx"
args = ["mcp-openstack-ops", "--type", "stdio"]
startup_timeout_sec = 120

[mcp_servers.MCP-OpenStack-Ops.env]
# Required
OS_AUTH_HOST = "<keystone-host>"
OS_AUTH_PORT = "5000"
OS_PROJECT_NAME = "<project>"
OS_USERNAME = "<user>"
OS_PASSWORD = "<password>"
# Optional; set to the server defaults
OS_AUTH_PROTOCOL = "http"
OS_CACERT = ""
OS_USER_DOMAIN_NAME = "Default"
OS_PROJECT_DOMAIN_NAME = "Default"
OS_REGION_NAME = "RegionOne"
OS_IDENTITY_API_VERSION = "3"
OS_ENDPOINT_SOURCE = "configured"
OS_INTERFACE = "internal"
OS_COMPUTE_PORT = "8774"
OS_NETWORK_PORT = "9696"
OS_VOLUME_PORT = "8776"
OS_IMAGE_PORT = "9292"
OS_PLACEMENT_PORT = "8780"
OS_HEAT_STACK_PORT = "8004"
MCP_LOG_LEVEL = "INFO"
ALLOW_MODIFY_OPERATIONS = "false"
ALLOW_CROSS_PROJECT_READ = "false"
LIST_MAX_LIMIT = "100"
INSTANCE_FILTER_MAX_MATCHES = "100"
```

- Change the values your cloud needs, for example `OS_AUTH_PROTOCOL` and
  `OS_CACERT` for HTTPS or the ports. [Local stdio clients](configuration.md#local-stdio-clients)
  explains each group and which `.env` keys do not apply here.
- Codex waits 10 seconds for a server to start by default.
  `startup_timeout_sec = 120` leaves time for `uvx` to install Python and the
  dependencies when the package is not cached yet.
- With `ALLOW_MODIFY_OPERATIONS = "false"`, only read tools are registered.
- To run an unreleased source checkout instead, prepare it as in
  [Claude Desktop option 3](claude-desktop-guide.md#option-3-source-checkout-with-uv)
  and use `command = "uv"` with
  `args = ["--directory", "/path/to/MCP-OpenStack-Ops", "run", "mcp-openstack-ops", "--type", "stdio"]`.

Restart Codex after editing the file. Check the server with `/mcp` in the
desktop app composer or the Codex CLI, or with `codex mcp list`, then ask, for
example:

```text
Use MCP-OpenStack-Ops to list all instances in the project.
```

## Option 2: Existing HTTP server

Codex connects to a Streamable HTTP server directly; no bridge is needed.
Register the MCP server's `/mcp` URL, not the MCPO URL. Replace host port `8000`
if you changed it, and use HTTPS for a host other than loopback. The server's own
`.env` decides the OpenStack account and whether `set_*` tools are registered.

```toml
[mcp_servers.MCP-OpenStack-Ops]
url = "http://127.0.0.1:8000/mcp"
bearer_token_env_var = "OPENSTACK_MCP_TOKEN"
```

`bearer_token_env_var` names the environment variable that holds the server's
`REMOTE_SECRET_KEY` (without `Bearer `); Codex sends it in the `Authorization`
header. The variable must be set in the environment that starts Codex. If server
authentication is disabled (`REMOTE_AUTH_ENABLE=false`), remove that line.

For a server in [multi-user mode](multi-user-guide.md) (`MCP_MULTI_USER=true`),
send your own Application Credential from environment variables as well:

```toml
[mcp_servers.MCP-OpenStack-Ops]
url = "https://mcp.example.com/mcp"
env_http_headers = { "X-OpenStack-Application-Credential-ID" = "OS_AC_ID", "X-OpenStack-Application-Credential-Secret" = "OS_AC_SECRET" }
```

Keep `bearer_token_env_var` too if the server also requires Bearer
authentication.

## Verification status

Option 1 was checked on 2026-11-21 in Codex in the ChatGPT desktop app, which
started the server with `uvx` from PyPI using this `config.toml` layout and
`startup_timeout_sec = 120`; the app and package versions were not recorded.
Codex CLI and the IDE extension read the same file but were not tested
separately. Option 2, in single-account and multi-user mode, is **Live
unverified**.

See the [Codex MCP documentation](https://learn.chatgpt.com/docs/extend/mcp) and
the [configuration reference](https://learn.chatgpt.com/docs/config-file/config-reference).
