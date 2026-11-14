**English** | [Korean](claude-desktop-guide.ko.md)

# Claude Desktop

Choose **one** of the following options. Option 1 is the simplest: it installs
from a file and shows a settings form, with no configuration file to edit.
Options 2-4 add a server entry to `claude_desktop_config.json`. The README
[Quick Start](../README.md#quick-start) shows option 1 in condensed form.

| Option | Use when | Requirements on the Claude Desktop computer |
| --- | --- | --- |
| [1. Desktop extension (`.mcpb`) (recommended)](#option-1-desktop-extension-mcpb-recommended) | Install a released version in one step | Claude Desktop with extension support |
| [2. PyPI package with `uvx`](#option-2-pypi-package-with-uvx) | Run the released server from `claude_desktop_config.json` | uv |
| [3. Source checkout with `uv`](#option-3-source-checkout-with-uv) | Run unreleased or modified source | Git, uv |
| [4. Existing Docker HTTP server with `npx`](#option-4-existing-docker-http-server-with-npx) | Reuse the running Docker Compose `mcp-server` | Node.js 18+ |

In options 1-3, Claude Desktop starts a local MCP server on that computer,
which needs network access to the OpenStack APIs. In option 4, Claude Desktop
starts only the `mcp-remote` bridge; the MCP server is a separate HTTP server,
even when it runs on the same computer, and reaches OpenStack with its own `.env`.

The examples name the server entries `OpenStack-uvx`, `OpenStack-uv`, and
`OpenStack-npx`. Keep a server name at 21
characters or fewer: clients can prefix it to each tool name (Claude Code uses
`mcp__<server>__<tool>`), the Claude API limits tool names to 64 characters, and
the longest tool name here has 36 characters. A server on the public internet can
instead be added as a [remote custom connector](#remote-custom-connector), which
does not use `claude_desktop_config.json`.

## Option 1: Desktop extension (.mcpb) (recommended)

Each [GitHub Release](https://github.com/call518/MCP-OpenStack-Ops/releases)
from 3.7.1 on provides `mcp-openstack-ops-<version>.mcpb`. Earlier releases do
not have this file.

1. Download the `.mcpb` file from the release.
2. In Claude Desktop, open **Settings > Extensions > Advanced settings >
   Install Extension…** and select the file. On Windows, double-clicking the
   file or dragging it into a chat did not install it.
3. Fill in the settings form. Each field title shows the environment variable
   it sets, as listed in [Environment Variables](configuration.md#environment-variables).
   Keystone host, project, user name, and password are required. Ports,
   domains, and region are prefilled with the server defaults. The CA
   certificate is optional. **Allow modify operations** is off, so only read
   tools are registered. **Allow cross-project reads** is off; see
   [cross-project reads guide](cross-project-guide.md) before turning it on.

Claude Desktop stores the password as a sensitive value instead of writing it
to `claude_desktop_config.json`. The bundle contains the source, `pyproject.toml`,
and `uv.lock`; Claude Desktop installs Python and the locked dependencies with
uv. To upgrade, install the `.mcpb` file of a newer release. To build a bundle
from a checkout, run `scripts/build-mcpb.sh <version>`; it requires Python 3 and
Node.js and writes `dist/mcp-openstack-ops-<version>.mcpb`.

The bundle uses the MCPB `uv` server type (manifest version 0.4). The Claude
Desktop version that first supports it is not documented; if installation is
refused, update Claude Desktop or use option 2. The project supports Python 3.12
only (`requires-python = ">=3.12,<3.13"`), and uv installs a matching Python
version with the locked dependencies.

## Configuration file for options 2-4

Open Claude Desktop **Settings > Developer > Edit Config**, or edit the file
directly:

- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`
- Linux: `~/.config/Claude/claude_desktop_config.json`

Merge the entry into the existing `mcpServers` object, then quit and restart
Claude Desktop. MCP logs are in `~/Library/Logs/Claude` (macOS),
`%APPDATA%\Claude\logs` (Windows), or `~/.config/Claude/logs` (Linux). This file
stores the values you put in it in plain text; keep it private and do not commit
it.

## Option 2: PyPI package with uvx

`uvx` is included with [uv](https://docs.astral.sh/uv/). It downloads the
`mcp-openstack-ops` package from PyPI, installs a suitable Python if needed, and
runs it in a cached tool environment; no clone is needed. Download it once
before the first Claude Desktop launch:

```bash
uvx mcp-openstack-ops --help
```

The first run installs the latest release from
[PyPI](https://pypi.org/project/mcp-openstack-ops/); later runs reuse the cached
version and do not check for updates. To upgrade, run
`uvx mcp-openstack-ops@latest --help` and restart Claude Desktop. To keep the
same version on every computer, use an exact version such as
`mcp-openstack-ops@X.Y.Z` in both the command and `args`.

```json
{
  "mcpServers": {
    "OpenStack-uvx": {
      "command": "uvx",
      "args": ["mcp-openstack-ops", "--type", "stdio"],
      "env": {
        "OS_AUTH_HOST": "<keystone-host>",
        "OS_AUTH_PORT": "5000",
        "OS_PROJECT_NAME": "<project>",
        "OS_USERNAME": "<user>",
        "OS_PASSWORD": "<password>",
        "OS_USER_DOMAIN_NAME": "Default",
        "OS_PROJECT_DOMAIN_NAME": "Default",
        "OS_REGION_NAME": "RegionOne",
        "ALLOW_MODIFY_OPERATIONS": "false"
      }
    }
  }
}
```

Add the endpoint, HTTPS, and port variables your cloud needs from
[Environment Variables](configuration.md#environment-variables). With
`ALLOW_MODIFY_OPERATIONS=false`, only read tools are registered. The tracked
`mcp-config.json.stdio` template sets `PYTHONPATH=/app/src`, the source path inside
this project's containers; use its `env` values, not its `command`, for Claude
Desktop.

## Option 3: Source checkout with uv

Use this option for changes that are not released on PyPI. Requirements: Git
and [uv](https://docs.astral.sh/uv/); uv installs Python 3.12 and the locked
dependencies.

Clone this repository on the Claude Desktop computer. In the commands and configuration below,
`/path/to/MCP-OpenStack-Ops` is the absolute path of this clone: the directory
that contains `pyproject.toml`, `uv.lock`, and `src/`. Then prepare the
environment once so that the first Claude Desktop launch does not wait for
installation:

```bash
git clone https://github.com/call518/MCP-OpenStack-Ops.git /path/to/MCP-OpenStack-Ops
uv --directory /path/to/MCP-OpenStack-Ops sync
```

On Windows, use a Windows path such as `C:\work\MCP-OpenStack-Ops` in the
commands, and write it as `C:\\work\\MCP-OpenStack-Ops` in JSON. For Claude
Desktop on Windows, clone the repository on Windows rather than using a clone
inside WSL, whose `.venv` is built for Linux.

Add an entry with the absolute path of the clone. Only `command` and `args`
differ from option 2:

```json
{
  "mcpServers": {
    "OpenStack-uv": {
      "command": "uv",
      "args": ["--directory", "/path/to/MCP-OpenStack-Ops", "run",
               "mcp-openstack-ops", "--type", "stdio"],
      "env": {
        "OS_AUTH_HOST": "<keystone-host>",
        "OS_AUTH_PORT": "5000",
        "OS_PROJECT_NAME": "<project>",
        "OS_USERNAME": "<user>",
        "OS_PASSWORD": "<password>",
        "OS_USER_DOMAIN_NAME": "Default",
        "OS_PROJECT_DOMAIN_NAME": "Default",
        "OS_REGION_NAME": "RegionOne",
        "ALLOW_MODIFY_OPERATIONS": "false"
      }
    }
  }
}
```

After `git pull`, restart Claude Desktop to load the updated source.

## Option 4: Existing Docker HTTP server with npx

Claude Desktop starts local commands from `claude_desktop_config.json`; it does
not take an HTTP URL there. To use the Docker Compose `mcp-server`, use the
third-party [`mcp-remote`](https://github.com/geelen/mcp-remote) stdio-to-HTTP
bridge. It requires Node.js 18 or later; Claude Desktop uses the system Node.js.
Register the MCP server's `/mcp` URL, not the MCPO URL. Replace host port `8000`
if you changed it:

```json
{
  "mcpServers": {
    "OpenStack-npx": {
      "command": "npx",
      "args": ["-y", "mcp-remote@0.15.2", "http://127.0.0.1:8000/mcp",
               "--transport", "http-only",
               "--header", "Authorization:${REMOTE_SECRET_KEY}"],
      "env": {
        "REMOTE_SECRET_KEY": "Bearer <REMOTE_SECRET_KEY>"
      }
    }
  }
}
```

`mcp-remote` substitutes this `env` value into the `Authorization` header. Set it
to `Bearer `, a space, and the MCP server's `REMOTE_SECRET_KEY` value; without the
`Bearer ` prefix the server rejects the connection. Do not use `OS_PASSWORD`; the
OpenStack credentials stay in the server's `.env`. The prefix is kept in `env`
because Claude Desktop on Windows does not escape spaces in `args`. If server authentication is disabled
(`REMOTE_AUTH_ENABLE=false`), remove the `--header` arguments and `env`. Keep the
`mcp-remote` version pinned. Use plain HTTP only for a loopback address; for another
host, publish the server over HTTPS. The server's own `.env` decides the
OpenStack account and whether `set_*` tools are registered.

## Remote custom connector

This is not a `claude_desktop_config.json` option. Remote connectors are added in Claude **Customize > Connectors > Add custom
connector**, not in `claude_desktop_config.json`. Claude connects to the server
from Anthropic's cloud, not from your computer, so the server must have an HTTPS
URL reachable from the public internet; servers on a private network, VPN, or
behind a firewall cannot be reached without allowlisting or an MCP tunnel.

This server does not implement OAuth. With `REMOTE_AUTH_ENABLE=true`, choose
**No sign-in** and add an `authorization` request header whose value is
`Bearer <REMOTE_SECRET_KEY>`, including the scheme. Request-header
authentication is a beta feature that not every organization has. The token
grants the server's configured OpenStack account to anyone who holds it. Never
expose this server without authentication. Review
[Bearer Token Authentication](security.md#bearer-token-authentication) and keep
`ALLOW_MODIFY_OPERATIONS=false` unless writes are required. Multi-user mode
uses custom `X-OpenStack-*` headers, and custom header names need Anthropic
approval; see the [multi-user guide](multi-user-guide.md).

## Verification status

For option 1, a built bundle passed `mcpb validate`, and its unpacked
`mcp_config` ran with an MCP client after host-style variable substitution.
Releases 3.7.1 to 3.7.4 have the bundle attached by the release workflow.
Options 2-4 were checked with an MCP client using the same command, arguments,
and environment. Option 2 was checked by installing the package from a local
checkout with `uvx`, not by downloading it from PyPI. With server
authentication enabled, option 4 connected with the `Bearer ` value and was
rejected without the prefix or with a wrong key. The remote custom connector
path is unverified.

See the [Claude Desktop local MCP guide](https://modelcontextprotocol.io/docs/develop/connect-local-servers),
[desktop extensions (MCPB)](https://claude.com/docs/connectors/building/mcpb),
and [custom connectors](https://claude.com/docs/connectors/custom/remote-mcp).
