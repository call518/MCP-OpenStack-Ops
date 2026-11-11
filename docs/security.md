**English** | [Korean](security.ko.md)

# Security, isolation and safety controls

This guide covers how the server limits what it can see and change: project
isolation, the read-only default for modification tools, and Bearer token
authentication for HTTP access. For per-user OpenStack identities, see the
[multi-user guide](multi-user-guide.md).

## Project isolation

MCP-OpenStack-Ops operates within the project determined by the
`OS_PROJECT_NAME` environment variable (in multi-user mode, by each request's
Application Credential).

- **Project-scoped resources**: Operations are restricted to resources within
  the specified project, with project ownership validation.
- **Cross-project access prevention**: Resource lookups are project-scoped and
  verify ownership, which protects against accidental operations on
  similarly-named resources in other projects.
- **Service-level filtering**: Each service filters resources by the current
  project ID.
- **Shared resource access**: Shared and public resources (networks, images)
  are included where the project can use them.

Cloud-wide administrative APIs (for example hypervisors, services and agents)
are not project resources; their results depend on the account's OpenStack
policy.

**Filtered Resources by Project:**

| Service | Project-Scoped Resources | Notes |
|---------|-------------------------|-------|
| **Identity** | Users (via role assignments), Role assignments | Only users with roles in current project |
| **Compute** | Instances, Flavors (embedded data), Keypairs | All instances within project scope |
| **Image** | Private images (owned), Public/Community/Shared images | Smart filtering prevents zero-image issues |
| **Network** | Networks, Subnets, Security Groups, Floating IPs, Routers | Includes shared/external networks for access |
| **Storage** | Volumes, Snapshots, Backups | All storage resources within project |
| **Orchestration** | Heat Stacks, Stack Resources | All orchestration within project |
| **Load Balancer** | Load Balancers, Listeners, Pools | All load balancing within project |
| **Monitoring** | Resource usage, Project quotas | Project-specific monitoring data |

To use several projects, run one server instance per project; see
[Multi-project configuration](configuration.md#multi-project-configuration).

### Project isolation test

To check project isolation against your cloud, run the included test with the
`OS_*` variables of the target project:

```bash
uv run python test_project_isolation.py
```

**Example output:**
```
🔒 OpenStack Project Isolation Security Test
==================================================
📋 Testing project isolation for: your-project

1️⃣ Testing Connection and Project ID...
✅ Connection successful
✅ Current project ID: abc123-def456-ghi789
✅ Project name 'your-project' matches project ID

2️⃣ Testing Resource Ownership Validation...
✅ Found 5 compute instances
   Instance web-server-01: ✅ Owned
   Instance db-server-01: ✅ Owned
✅ Found 3/8 owned networks
✅ Found 10/10 owned volumes

3️⃣ Testing Service-Level Project Filtering...
✅ Compute service returned 5 instances
✅ Network service returned 3 networks
✅ Storage service returned 10 volumes

4️⃣ Testing Secure Resource Lookup...
ℹ️  Network 'admin' not found or not accessible in current project
ℹ️  Instance 'demo' not found or not accessible in current project

🎯 Project Isolation Test Results
========================================
✅ All security tests passed!
✅ Project 'your-project' isolation verified
✅ Cross-project access prevention confirmed

🔒 Your OpenStack MCP Server is properly secured!
```

The test checks project ID verification and matching, resource ownership
validation, service-level project filtering, and secure resource lookup with
cross-project protection.

## Modification operations protection

By default, all operations that can modify or delete OpenStack resources are **disabled** for safety:

```bash
# Default setting - Only read-only operations allowed
ALLOW_MODIFY_OPERATIONS=false
```

**Protected Operations (when `ALLOW_MODIFY_OPERATIONS=false`):**
- Instance management (start, stop, restart, pause, unpause)
- Volume operations (create, delete, attach, detach)
- Keypair management (create, delete, import)
- Floating IP operations (create, delete, associate, disassociate)
- Snapshot management (create, delete)
- Image management (create, delete, update)
- Heat stack operations (create, delete, update)

**Always Available (Read-Only Operations):**
- Cluster status and monitoring
- Resource listings (instances, volumes, networks, etc.)
- Service status checks
- Usage and quota information
- Search and filtering operations

**⚠️ To Enable Modify Operations:**
```bash
# Enable all operations (USE WITH CAUTION)
ALLOW_MODIFY_OPERATIONS=true
```

**Tool Registration Behavior:**
- When `ALLOW_MODIFY_OPERATIONS=false`: Only read-only tools are registered with the MCP server
- When `ALLOW_MODIFY_OPERATIONS=true`: All tools (read-only + modify operations) are registered
- Tool availability is determined at server startup - restart required after changing this setting

**Best Practices:**
- Keep `ALLOW_MODIFY_OPERATIONS=false` in production environments
- Enable modify operations only in development/testing environments
- Use separate configurations for different environments
- Review operations before enabling modify capabilities
- Restart the MCP server after changing the `ALLOW_MODIFY_OPERATIONS` setting

## Bearer token authentication

For `streamable-http` mode, this MCP server supports Bearer token authentication to secure remote access. This is especially important when running the server in production environments.

### Configuration

**Enable Authentication:**

```bash
# In .env file
REMOTE_AUTH_ENABLE=true
REMOTE_SECRET_KEY=<REMOTE_SECRET_KEY>
```

Generate the secret with, for example, `openssl rand -hex 32`.

**Or via CLI:**

```bash
uv run python -m mcp_openstack_ops --type streamable-http --auth-enable --secret-key <REMOTE_SECRET_KEY>
```

### Security Levels

1. **stdio mode** (Default): Local-only access, no authentication needed
2. **streamable-http + REMOTE_AUTH_ENABLE=false/undefined**: Remote access without authentication ⚠️ **NOT RECOMMENDED for production**
3. **streamable-http + REMOTE_AUTH_ENABLE=true**: Remote access with Bearer token authentication ✅ **RECOMMENDED for production**
4. **streamable-http + MCP_MULTI_USER=true**: Each request authenticates with the caller's project-scoped Keystone Application Credential and requires HTTPS OpenStack endpoints by default. HTTP is available only for isolated development/testing with `MCP_MULTI_USER_ALLOW_INSECURE_HTTP=true`.
5. **streamable-http + MCP_MULTI_USER=true + REMOTE_AUTH_ENABLE=true**: Each request must pass shared Bearer authentication first and per-user Application Credential authentication second. See the [multi-user guide](multi-user-guide.md).

> **🔒 Default Policy**: `REMOTE_AUTH_ENABLE` and `MCP_MULTI_USER` both default to `false`. A configured `REMOTE_SECRET_KEY` is used only when `REMOTE_AUTH_ENABLE=true`; enabling both modes requires both forms of authentication.

### Client Configuration

When authentication is enabled, MCP clients must include the Bearer token in the Authorization header:

```json
{
  "mcpServers": {
    "mcp-openstack-ops": {
      "type": "streamable-http",
      "url": "http://your-server:8000/mcp",
      "headers": {
        "Authorization": "Bearer <REMOTE_SECRET_KEY>"
      }
    }
  }
}
```

### Security Best Practices

- **Always enable authentication** when using streamable-http mode in production
- **Use strong, randomly generated secret keys** (32+ characters recommended)
- **Use HTTPS** when possible (configure reverse proxy with SSL/TLS)
- **Restrict network access** using firewalls or network policies
- **Rotate secret keys regularly** for enhanced security
- **Monitor access logs** for unauthorized access attempts

### Error Handling

When authentication fails, the server returns:
- **401 Unauthorized** for missing or invalid tokens
- **Detailed error messages** in JSON format for debugging
