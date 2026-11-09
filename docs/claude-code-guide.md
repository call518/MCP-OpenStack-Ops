# Claude Code

Install Claude Code and start the MCP server in `streamable-http` mode first,
for example with the Docker Compose stack in the
[OpenWebUI guide](openwebui-guide.md). Register the MCP server's `/mcp` URL, not
the MCPO/OpenAPI proxy URL. The example below uses the Docker host port `8000`;
replace the host/port for your deployment and use HTTPS for remote connections.
Registration does not start the server.

For the existing single-account mode with `REMOTE_AUTH_ENABLE=true`, enter the
server's `REMOTE_SECRET_KEY` without saving its literal value in shell history:

```bash
read -rsp 'MCP Bearer token: ' OPENSTACK_MCP_TOKEN
echo
export OPENSTACK_MCP_TOKEN

claude mcp add-json --scope user openstack-ops '{"type":"http","url":"http://127.0.0.1:8000/mcp","headers":{"Authorization":"Bearer ${OPENSTACK_MCP_TOKEN}"}}'
claude mcp list
claude
```

Keep `OPENSTACK_MCP_TOKEN` exported in the terminal that launches Claude Code.
`--scope user` saves the registration in your normal user configuration. If server
authentication is disabled, use this registration command instead:

```bash
claude mcp add --transport http --scope user openstack-ops http://127.0.0.1:8000/mcp
```

In Claude Code, check `/mcp` and ask, for example:

```text
Use openstack-ops to list all instances in the project.
```

Remove the registration when no longer needed (this does not stop the server):

```bash
claude mcp remove --scope user openstack-ops
unset OPENSTACK_MCP_TOKEN
```

This Bearer configuration uses the server's configured OpenStack account. For
experimental per-user authentication, see the [multi-user guide](multi-user-guide.md).
See also the [Claude Code MCP documentation](https://code.claude.com/docs/en/mcp).
