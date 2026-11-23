**English** | [Korean](claude-code-guide.ko.md)

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

This Bearer configuration uses the server's configured OpenStack account.

## Multi-user mode: Application Credential headers

When the server runs in multi-user mode (`MCP_MULTI_USER=true`; see the
[multi-user guide](multi-user-guide.md)), every request must carry your own
OpenStack Application Credential in two headers. Without them the server answers
HTTP 401 with `Application credential headers are required`, and `/mcp` shows the
connection as failed.

`/mcp` cannot add or edit headers: it only connects with the registration as it
is saved. Put the headers in the registration with `claude mcp add-json`, then
reconnect in `/mcp`. The VS Code extension reads the same user-scope
registration as the CLI.

1. Create an Application Credential for the user and project you want the tools
   to act as. Keystone shows the secret only once:

   ```bash
   openstack application credential create openstack-ops-mcp
   ```

2. Replace the registration with one that includes both credential headers. Keep
   the `Authorization` header when the server has `REMOTE_AUTH_ENABLE=true`; with
   authentication disabled the server ignores it:

   ```bash
   claude mcp remove --scope user openstack-ops
   claude mcp add-json --scope user openstack-ops '{"type":"http","url":"http://127.0.0.1:8000/mcp","headers":{"Authorization":"Bearer <shared-mcp-token>","X-OpenStack-Application-Credential-ID":"<application-credential-id>","X-OpenStack-Application-Credential-Secret":"<application-credential-secret>"}}'
   ```

3. In Claude Code, open `/mcp` and reconnect `openstack-ops`.

The values are stored in plain text in your user configuration, and a command
line with them stays in shell history unless you prevent it. The `${VARIABLE}`
form shown above for the Bearer token also works for these headers when the
variables are exported in the environment of the process that runs Claude Code;
for the VS Code extension that is the VS Code (or VS Code Server) process, not a
terminal, and this form was not checked with the extension. Delete the
Application Credential when you no longer need it:

```bash
openstack application credential delete openstack-ops-mcp
```

See also the [Claude Code MCP documentation](https://code.claude.com/docs/en/mcp).
