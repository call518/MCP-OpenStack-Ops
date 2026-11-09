**English** | [Korean](openwebui-guide.ko.md)

# OpenWebUI with Docker Compose

This guide runs MCP-OpenStack-Ops and OpenWebUI with Docker Compose and
connects them. The README [Quick Start](../README.md#quick-start) is the
condensed version of the same procedure.

## Components and connection paths

The Compose file starts three services:

| Service | Image | Role |
| --- | --- | --- |
| `mcp-server` | `call518/mcp-server-openstack-ops` | The MCP server. Talks to OpenStack and serves MCP over Streamable HTTP at `/mcp` |
| `open-webui` | `ghcr.io/open-webui/open-webui` | Chat interface and model connections |
| `mcpo-proxy` | `call518/mcpo-proxy-openstack-ops` | Optional. [MCPO](https://github.com/open-webui/mcpo) exposes the MCP tools as an OpenAPI (REST) server |

OpenWebUI can reach the MCP server in either of two ways:

```text
Browser → OpenWebUI → MCP-OpenStack-Ops → OpenStack                (direct MCP)
Browser → OpenWebUI → MCPO (OpenAPI) → MCP-OpenStack-Ops → OpenStack (through MCPO)
```

### Direct MCP or MCPO?

MCPO is not required. OpenWebUI 0.13 connects to MCP servers natively, and the
direct connection has fewer components. Use MCPO when OpenAPI compatibility is
required.

| | Direct MCP | Through MCPO |
| --- | --- | --- |
| OpenWebUI connection type | `MCP (Streamable HTTP)` | `OpenAPI` |
| Connection URL inside Compose | `http://mcp-server:8000/mcp` | `http://mcpo-proxy:8000/mcp-openstack-ops` |
| Components in the request path | OpenWebUI and the MCP server | OpenWebUI, MCPO and the MCP server |
| Extra configuration | None | An MCPO configuration file (`MCPO_CONFIG_FILE`) |
| Browsable REST docs | No | Yes, at `http://localhost:8080/mcp-openstack-ops/docs` |
| After `mcp-server` restarts | Reconnect the client if it reports a session error | MCPO keeps its old MCP session; restart `mcpo-proxy` (see [Troubleshooting](#troubleshooting)) |
| Use when | You use OpenWebUI's native MCP support | You need an OpenAPI endpoint, the generated docs, or a client that only speaks OpenAPI |

To run without MCPO, start only the two services you need:

```bash
docker compose up -d mcp-server open-webui
```

The `mcpo-proxy` image pins mcpo 0.0.20 with mcp 1.30.0 and FastAPI 0.128.0;
mcpo 0.0.20 does not start with mcp 2.x or FastAPI 0.162.2. The mcp 1.x proxy
still connects to the mcp 2.x server. For per-user authentication through each
path, see [Client compatibility](multi-user-guide.md#client-compatibility) in the
multi-user guide.

## Prerequisites and defaults

Prerequisites are Git, Docker with the Compose plugin, a reachable OpenStack
environment, and a model provider supported by OpenWebUI. The model should
support reliable native tool calling.

This default path supports an OpenStack deployment whose Identity, Compute,
Network, Block Storage, Image, Placement, and Orchestration APIs are reachable
from the Docker host at one hostname with the configured service ports. If your
cloud uses different hostnames or URL paths per service, check
[OpenStack endpoint topology](configuration.md#openstack-endpoint-topology) before starting.

| Default | Value |
| --- | --- |
| OpenStack identity | One account from `.env` |
| Available tools | Read-only; modification tools are hidden |
| HTTP authentication | Disabled |
| Published network | Localhost only |
| MCPO configuration | `mcp-config.json.http.local` |

## 1. Clone and configure

```bash
git clone https://github.com/call518/MCP-OpenStack-Ops.git
cd MCP-OpenStack-Ops
cp .env.example .env
cp mcp-config.json.http mcp-config.json.http.local
chmod 600 mcp-config.json.http.local
openssl rand -hex 32
vi .env
```

In `.env`:

1. Replace `WEBUI_SECRET_KEY` with the generated value.
2. Set the `OS_*` authentication, domain, region, protocol, and service-port
   values for the target OpenStack environment.
3. Keep these local defaults:

```dotenv
ALLOW_MODIFY_OPERATIONS=false
MCP_MULTI_USER=false
REMOTE_AUTH_ENABLE=false
REMOTE_SECRET_KEY=
DOCKER_BIND_ADDRESS=127.0.0.1
MCPO_CONFIG_FILE=mcp-config.json.http.local
```

The local MCPO copy is needed only when `mcpo-proxy` runs. It contains no
credentials in this mode and connects to the MCP container through the private
Compose network. It is ignored by Git, so later authentication changes do not
modify the tracked reference template. The placeholder Authorization header is
ignored while `REMOTE_AUTH_ENABLE=false`. When enabling Bearer authentication,
replace `<REMOTE_SECRET_KEY>` in the local MCPO copy with the same value
configured in `.env`.

## 2. Start the stack

```bash
docker compose up -d
docker compose ps
```

Wait until `mcp-server` is healthy and `mcpo-proxy` and `open-webui` are running.

| Service | Local URL | Purpose |
| --- | --- | --- |
| OpenWebUI | `http://localhost:3000` | Chat interface |
| MCP server | `http://localhost:8000/mcp` | Direct MCP endpoint |
| MCPO docs | `http://localhost:8080/mcp-openstack-ops/docs` | Generated OpenAPI schema and test UI |

If `mcp-server` is unhealthy, inspect its log before continuing:

```bash
docker compose logs mcp-server
```

## 3. Configure OpenWebUI 0.13

Open `http://localhost:3000`, create the first administrator account, and add a
model provider. Use a model with reliable native function calling.

For the shortest first run, choose one provider:

- **OpenAI:** open **Settings → Admin → Connections**, add an OpenAI API
  connection, use `https://api.openai.com/v1`, enter the API key, and save it.
  See the [OpenWebUI OpenAI guide](https://docs.openwebui.com/getting-started/quick-start/connect-a-provider/starting-with-openai/).
- **Ollama on the Docker host:** the Compose configuration already points
  OpenWebUI to `http://host.docker.internal:11434`. Ensure Ollama listens where
  Docker can reach it and select a tool-capable model. See the
  [OpenWebUI Ollama guide](https://docs.openwebui.com/getting-started/quick-start/connect-a-provider/starting-with-ollama/).
- **Another OpenAI-compatible provider or local server:** add its base URL and
  API key under **Settings → Admin → Connections**. When the provider does not
  expose a model list, enter the model ID manually. See the
  [OpenAI-compatible provider guide](https://docs.openwebui.com/getting-started/quick-start/connect-a-provider/starting-with-openai-compatible/).

Confirm that the selected model appears in a new chat before configuring the
MCP integration.

### 3.1 Add an external tool-server connection

Choose one of the following connections. The direct MCP option has fewer
components; use MCPO when OpenAPI compatibility is required.

**Option A: Direct MCP connection**

Open **Settings → Admin → Tools → Integrations**, find **External Tool
Servers**, and add this connection:

| Field | Value |
| --- | --- |
| Type | `MCP (Streamable HTTP)` |
| Name | `MCP OpenStack Ops Direct` |
| ID | `mcp-openstack-ops-direct` or the generated value |
| URL | `http://mcp-server:8000/mcp` |
| Authentication | `None` |
| Function name filter list | Empty |
| Enabled | On |

Use `Bearer` authentication with the `REMOTE_SECRET_KEY` value instead when
`REMOTE_AUTH_ENABLE=true`. Save the connection and confirm that the connection
check succeeds. See the
[OpenWebUI native MCP guide](https://docs.openwebui.com/features/extensibility/mcp/)
for supported transports and current compatibility notes.

**Option B: MCPO OpenAPI connection**

Open **Settings → Admin → Tools → Integrations**, find **External Tool
Servers**, and add this connection:

| Field | Value |
| --- | --- |
| Type | `OpenAPI` |
| Name | `MCP OpenStack Ops` |
| ID | `mcp-openstack-ops` or the generated value |
| URL | `http://mcpo-proxy:8000/mcp-openstack-ops` |
| Authentication | `None` |
| Function name filter list | Empty |
| Enabled | On |

This is an administrator-managed connection, so OpenWebUI fetches the schema
from its own container. Use the Compose service address above, not
`http://localhost:8080`; inside the OpenWebUI container, `localhost` refers to
OpenWebUI itself. The UI automatically fetches `openapi.json` from the supplied
base URL. Save the connection and confirm that the connection check succeeds.

### 3.2 Enable Tool Search for the full tool inventory

The OpenStack server plus OpenWebUI's built-in tools can exceed a model
provider's maximum number of function definitions per request. Open
**Settings → Admin → System → Interface**. This is the administrator
**Interface** entry below **Authentication**, not the personal Interface entry
near the top of the settings menu. In the **Chat** section, set:

| Setting | Value |
| --- | --- |
| Tool Search | On |
| Defer Built-in Tools | On |
| Deferral Threshold (characters) | `0` |
| Always Loaded Tools | Empty |

Save the settings. Tool Search keeps the complete tool inventory available but
sends only `search_tools`, `call_tool`, and any explicitly always-loaded tools
to the model until a matching tool is needed. See the
[OpenWebUI tools documentation](https://docs.openwebui.com/features/extensibility/plugin/tools/).

### 3.3 Configure OpenAI reasoning models

This step applies only to an OpenAI reasoning model that needs both non-default
reasoning effort and function tools. In **Settings → Admin → AI → Connections**,
edit its OpenAI connection and select API type **Responses**. Chat Completions
does not support function tools together with a non-`none` reasoning effort on
newer reasoning models.

With OpenWebUI 0.13.0, leave the chat's **Model controls → Advanced Params →
Reasoning Effort** at **Default**. Selecting **Custom** initializes the field to
`medium` and sends the Chat Completions parameter `reasoning_effort`, which is
not valid in a Responses request. Default omits that override and lets the model
apply its own default effort. To force an explicit Responses value, add this
custom parameter instead:

```text
Name: reasoning
Value: {"effort":"medium"}
```

See the [OpenAI Responses migration guide](https://developers.openai.com/api/docs/guides/migrate-to-responses)
and the [OpenWebUI Open Responses guide](https://docs.openwebui.com/getting-started/quick-start/connect-a-provider/starting-with-open-responses/).

Models and providers without this constraint may keep their normal API type and
reasoning settings.

### 3.4 Enable the connection in a chat

Open a new chat, select the model, click the **Integrations** icon beside the
message input, and enable `MCP OpenStack Ops` under **Tools**. Global tool-server
connections are not automatically enabled in every chat.

## 4. Verify

Ask the model:

```text
Use mcp-openstack-ops to list the instances in my OpenStack project.
```

A successful response confirms either the OpenWebUI → MCP server → OpenStack
path or the OpenWebUI → MCPO → MCP server → OpenStack path, depending on the
connection selected in the chat. For the MCPO option, the documentation URL
above should also list the generated tool endpoints.

## Troubleshooting

For connection failures, inspect the services used by the selected path:

```bash
docker compose logs mcp-server mcpo-proxy open-webui
```

Common OpenWebUI 0.13 errors:

| Error | Cause | Fix |
| --- | --- | --- |
| `Cannot connect to host localhost` | An administrator connection used a browser/host URL from inside the OpenWebUI container | Use `http://mcp-server:8000/mcp` for direct MCP or `http://mcpo-proxy:8000/mcp-openstack-ops` for MCPO |
| `tools: array too long` | External and built-in tool definitions exceeded the model provider's request limit | Enable Tool Search with threshold `0` |
| `Function tools with reasoning_effort are not supported ... /v1/chat/completions` | Chat Completions received function tools and a non-`none` reasoning effort | Use Responses, or set reasoning effort to `none` if reasoning is not needed |
| `Unsupported parameter: reasoning_effort ... moved to reasoning.effort` | OpenWebUI 0.13.0 sent a custom Reasoning Effort through a Responses connection | Set Reasoning Effort to Default; use custom `reasoning={"effort":"medium"}` only when an explicit value is required |
| MCPO logs `POST http://mcp-server:8000/mcp "404 Not Found"` and `McpError: Session terminated`; `mcp-server` logs `Rejected request with unknown or expired session ID` | MCP sessions exist only in the running `mcp-server` process. After `mcp-server` restarts, MCPO keeps its old session and does not reconnect. `docker compose restart` does not wait for the `mcp-server` health check, so MCPO can connect to the old process just before it stops | With `mcp-server` running, run `docker compose restart mcpo-proxy`. To restart both, use `docker compose up -d --force-recreate mcp-server mcpo-proxy` instead of `docker compose restart`. If a direct MCP client reports the same session error, reconnect it |

## 5. Enable modifications only when needed

Create, update, and delete tools are intentionally absent by default. To enable
them, set `ALLOW_MODIFY_OPERATIONS=true` in `.env` and recreate the MCP path:

```bash
docker compose up -d --force-recreate mcp-server mcpo-proxy
```

OpenStack policy still controls what the configured account may change. For
Bearer authentication, non-local exposure, and custom configuration files, see
the [configuration guide](configuration.md). For request-scoped user accounts,
see the [multi-user guide](multi-user-guide.md).

Stop the stack without deleting the OpenWebUI data volume with:

```bash
docker compose down
```

## 6. Installation variants and detailed guides

The steps above are the local, single-account evaluation path. Use the matching
guide when your environment differs:

| Environment or requirement | Follow-up guide |
| --- | --- |
| OpenStack APIs use HTTPS with a public or private CA | [HTTPS and private CA setup](configuration.md#https-and-private-ca-setup) |
| OpenStack services use different hosts or URL paths | [OpenStack endpoint topology](configuration.md#openstack-endpoint-topology) |
| Host ports `3000`, `8000`, or `8080` are occupied | [Docker Compose environment variables](configuration.md#environment-variables) |
| MCP is exposed beyond localhost | [Bearer authentication and remote-access precautions](security.md#bearer-token-authentication) |
| Each user supplies a separate OpenStack identity | [Multi-user setup and usage guide](multi-user-guide.md) |
| Separate fixed accounts or projects need separate MCP entries | [Multi-project configuration](configuration.md#multi-project-configuration) |
| Claude Desktop or Claude Code is the client | [Claude Desktop guide](claude-desktop-guide.md) or [Claude Code guide](claude-code-guide.md) |
| OpenAI reasoning models need explicit reasoning effort | [OpenAI reasoning-model settings](#33-configure-openai-reasoning-models) |
