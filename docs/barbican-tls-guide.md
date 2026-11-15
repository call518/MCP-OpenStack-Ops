**English** | [Korean](barbican-tls-guide.ko.md)

# Barbican secrets and TLS load balancers

The Barbican (key-manager) tools manage secret **metadata and references**:
they list secrets, containers and orders, change read ACLs, generate keys
inside Barbican, create self-signed certificates, and attach certificates to
Octavia `TERMINATED_HTTPS` listeners. Secret contents never pass through the
MCP server's tool arguments or results.

## Why the tools never carry secret payloads

Barbican can store and return any payload, and the MCP server could pass one
through. It deliberately does not: tool arguments and results go through the
client's LLM, so a private key, certificate bundle or password sent that way
would reach an external model and its conversation history. To rule this out:

- No tool has a payload parameter. Register your own certificates and keys
  through the CLI or another trusted path (see
  [Register your own certificate](#register-your-own-certificate)).
- No tool returns a payload. Secrets are read through the metadata API only;
  the openstacksdk calls that download payloads (`get_secret`, `find_secret`)
  are not used.
- Keys are created where they are used: `set_secret`
  (`create_self_signed_tls`) generates the key inside the MCP server and stores
  it directly in Barbican, and `set_secret_order` lets Barbican generate keys
  itself. Only hrefs, the public certificate and its fingerprint are returned.

## Prerequisites

These are deployment and account settings, the same for any Octavia and
Barbican user. Prepare them outside MCP.

1. **Barbican is deployed.** The Keystone catalog has a `key-manager`
   endpoint:

   ```bash
   openstack endpoint list --service key-manager
   ```

   Without it, every Barbican tool returns
   `Barbican (key-manager) service is not available`.
2. **Octavia uses Barbican for certificates.** In `octavia.conf`, the
   `[certificates]` defaults are `cert_manager = barbican_cert_manager` and
   `barbican_auth = barbican_acl_auth`. With them, the Octavia API grants its
   own service user read access to the referenced secret (an ACL entry) when
   the listener is created, using the requesting user's token. Users do not
   need the Octavia service user's ID.
3. **The account may create secrets and change their ACLs.** This depends on
   Barbican's policy: with the legacy policy, the `admin` or `creator` role is
   needed; with the Secure RBAC defaults, the project `member` role is enough.
   The user who creates the listener must be allowed to change the ACL of the
   referenced secret.
4. **Only if the deployment does not grant ACLs automatically:** give the
   Octavia service user read access yourself, with `set_secret_acl`
   (`add_users`) or `openstack acl user add`. An administrator can look up that
   user's ID.

## Register your own certificate

Do this outside MCP, on a host you trust. Octavia accepts a PKCS#12 bundle
stored as an `opaque` secret:

```bash
openssl pkcs12 -export -inkey server.key -in server.crt -certfile ca-chain.crt \
  -passout pass: -out server.p12
openstack secret store --name web-tls -t opaque -e base64 \
  -p "$(base64 -w0 < server.p12)"
```

Then refer to the secret by name (`web-tls`), ID or href in the tools.

## Create a self-signed certificate

For tests and internal services, ask for a self-signed certificate:

> Create a self-signed TLS secret named web-tls for 192.168.35.169 with SANs
> 192.168.35.169 and 10.40.40.185.

`set_secret` (`action="create_self_signed_tls"`) takes `name`, `common_name`,
`subject_alt_names` (DNS names and IP addresses, comma-separated), `days`
(1-3650), `key_size` (2048, 3072 or 4096) and an optional Barbican
`expiration`. It returns the secret href, the public certificate in PEM, its
SHA-256 fingerprint and expiry. Clients do not trust a self-signed certificate
unless you add it to their trust store.

## Create a TERMINATED_HTTPS listener

`set_load_balancer_listener` accepts the certificate references Octavia
needs:

| Parameter | Meaning |
| --- | --- |
| `default_tls_container_ref` | Default server certificate: a PKCS#12 secret or a certificate container, by name, ID or href. Required for `TERMINATED_HTTPS`. Octavia uses it when the client sends no host name (SNI) or no SNI certificate matches |
| `sni_container_refs` | Optional comma-separated certificates that Octavia picks by the requested host name |

Names are resolved to hrefs in the current project; a secret is tried first,
then a certificate container. Both parameters also work with `action="set"`.
Example:

> On web-lb, add a TERMINATED_HTTPS listener web-listener-https on port 443
> with certificate web-tls and default pool web-pool.

Listener creation is asynchronous. Check that the listener reaches
`ACTIVE`/`ONLINE` with `get_load_balancer_listeners`, then test with
`curl -vk https://<address>/`. Listener results report
`default_tls_container_ref` and `sni_container_refs`.

## TLS to the members

The Octavia cookbook describes three ways to handle HTTPS: a
**TLS-terminated HTTPS** load balancer, a **non-terminated HTTPS** load
balancer (commonly called TLS passthrough) and a load balancer with **backend
re-encryption**. The `TERMINATED_HTTPS` listener above is TLS-terminated
HTTPS; the other two are set on the listener and pool protocols and the pool's
TLS fields. Backend re-encryption can add **client authentication**, in which
the load balancer also presents a client certificate to the members (mutual
TLS, mTLS); without it, only the load balancer verifies the members.

| Setup | Listener / pool | Certificates | What the load balancer can do |
| --- | --- | --- | --- |
| TLS-terminated HTTPS | `TERMINATED_HTTPS` / `HTTP` | Server certificate in Barbican | L7 policies, `X-Forwarded-For`, cookie persistence; traffic to members is plain HTTP |
| Non-terminated HTTPS (TLS passthrough) | `HTTPS` / `HTTPS` | Each member holds its own; no Barbican secret | Forward the encrypted stream only: no L7 policies or inserted headers, `SOURCE_IP` persistence only |
| Backend re-encryption | `TERMINATED_HTTPS` / `HTTP` with `tls_enabled=true` | Server certificate in Barbican; optionally a CA and CRL, and a client certificate for client authentication | L7 features, and traffic to members is encrypted again |

Feature by feature:

| Feature | TLS-terminated HTTPS | Non-terminated HTTPS | Backend re-encryption |
| --- | --- | --- | --- |
| Client → load balancer encrypted | ✅ | ✅ | ✅ |
| Load balancer → member encrypted | ❌ Plain HTTP | ✅ | ✅ |
| Load balancer sees HTTP content | ✅ | ❌ | ✅ |
| L7 policies, `X-Forwarded-For` | ✅ | ❌ | ✅ |
| Session persistence | Cookies possible | `SOURCE_IP` only | Cookies possible |
| Server certificate location | Barbican | Each member | Barbican and each member |
| Member certificate verification | Not applicable | ❌ | ✅ Optional (`ca_tls_container_ref`) |
| Client authentication to members (mTLS) | Not applicable | ❌ | ✅ Optional (`tls_container_ref`) |
| Certificates installed on members | Not needed | Needed | Needed |
| Suited to | A trusted internal network, with certificates managed centrally on the load balancer | Certificates that cannot be handed to the load balancer, or end-to-end encryption to the members | Both L7 features and encryption on every hop |

**Non-terminated HTTPS** needs no new parameters: create an `HTTPS` listener with
`set_load_balancer_listener` and an `HTTPS` pool with `set_load_balancer_pool`.
For health checks, `set_load_balancer_health_monitor` with
`monitor_type="TLS-HELLO"` checks the TLS handshake.

**Backend re-encryption** uses these `set_load_balancer_pool` parameters
(create and set):

| Parameter | Meaning |
| --- | --- |
| `tls_enabled` | `true` encrypts traffic to the members again; `false` turns it off |
| `ca_tls_container_ref` | CA certificate (a PEM secret) that verifies member certificates. Without it, member certificates are not verified |
| `crl_container_ref` | Certificate revocation list (a PEM secret); requires `ca_tls_container_ref` |
| `tls_container_ref` | Client certificate for client authentication: the load balancer presents it to members that require mutual TLS (mTLS). A PKCS#12 secret or certificate container |
| `tls_versions`, `tls_ciphers`, `alpn_protocols` | TLS versions (`TLSv1.2,TLSv1.3`), OpenSSL cipher string and ALPN protocols (`h2,http/1.1`) towards the members |

Certificate references take a name, ID or href, as for listeners.
openstacksdk 4.22.0 has no pool `tls_container_ref` field, so a create or set
request with it is sent to the Octavia API directly; `show` reads it from the
Octavia response. Register CA and CRL secrets outside MCP, like other user
certificates.

## Backend re-encryption with client authentication (mTLS), step by step

On the load balancer to member hop, the roles are reversed from the client's
view: the load balancer (amphora) is the **TLS client** and each member is the
**TLS server**. With client authentication (mutual TLS, mTLS), both prove their
identity:

| Certificate | Proves | Where it goes | Who installs it |
| --- | --- | --- | --- |
| Member server certificate and key | The member to the load balancer | Each member's web server | You, on every member |
| CA certificate | That the load balancer's client certificate is trusted | Each member's web server | You, on every member |
| Load balancer client certificate and key (PKCS#12) | The load balancer to the members | Barbican, then the pool's `tls_container_ref` | You register it; Octavia installs it on the amphorae |
| CA certificate | That the member certificates are trusted | Barbican, then the pool's `ca_tls_container_ref` | You register it; Octavia installs it on the amphorae |

Members usually have private addresses, so a public CA cannot issue their
certificates. Use one private CA (openssl, an in-house PKI or a tool such as
HashiCorp Vault) for both the member and the client certificates.
`set_secret` (`create_self_signed_tls`) makes a single self-signed
certificate; it is not a CA and cannot issue these certificates.

Steps 1 to 4 handle private keys, so do them outside MCP on a host you trust.

**1. Create a private CA.** Keep `ca.key` offline; only `ca.crt` is
distributed.

```bash
openssl req -x509 -newkey rsa:4096 -nodes -days 3650 \
  -keyout ca.key -out ca.crt -subj "/CN=web-backend-ca"
```

**2. Issue a server certificate for each member**, with the member address in
the SAN (repeat per member):

```bash
openssl req -newkey rsa:2048 -nodes -keyout member1.key -out member1.csr \
  -subj "/CN=10.40.40.11"
openssl x509 -req -in member1.csr -CA ca.crt -CAkey ca.key -CAcreateserial \
  -days 365 -out member1.crt \
  -extfile <(printf "subjectAltName=IP:10.40.40.11\nextendedKeyUsage=serverAuth")
```

**3. Issue the load balancer client certificate** and bundle it as PKCS#12:

```bash
openssl req -newkey rsa:2048 -nodes -keyout lb-client.key -out lb-client.csr \
  -subj "/CN=web-lb"
openssl x509 -req -in lb-client.csr -CA ca.crt -CAkey ca.key -CAcreateserial \
  -days 365 -out lb-client.crt -extfile <(printf "extendedKeyUsage=clientAuth")
openssl pkcs12 -export -inkey lb-client.key -in lb-client.crt \
  -passout pass: -out lb-client.p12
```

**4. Configure each member** to serve its certificate and require a client
certificate signed by the CA. nginx example:

```nginx
server {
    listen 443 ssl;
    ssl_certificate        /etc/nginx/tls/member1.crt;
    ssl_certificate_key    /etc/nginx/tls/member1.key;
    ssl_client_certificate /etc/nginx/tls/ca.crt;
    ssl_verify_client      on;
}
```

**5. Register the client certificate and the CA in Barbican** with the CLI:

```bash
openstack secret store --name web-lb-client -t opaque -e base64 \
  -p "$(base64 -w0 < lb-client.p12)"
openstack secret store --name web-backend-ca -t opaque -e base64 \
  -p "$(base64 -w0 < ca.crt)"
```

**6. Create the pool and members through MCP**, behind a
`TERMINATED_HTTPS` listener:

> On listener web-listener-https, create pool web-pool-mtls with protocol HTTP,
> tls_enabled true, client certificate web-lb-client and CA web-backend-ca,
> then add members 10.40.40.11 and 10.40.40.12 on port 443.

This calls `set_load_balancer_pool` (`tls_enabled="true"`,
`tls_container_ref="web-lb-client"`, `ca_tls_container_ref="web-backend-ca"`)
and `set_load_balancer_pool_member`. An existing pool can be switched with
`action="set"` and the same parameters.

**7. Verify.**

- `set_load_balancer_pool` (`action="show"`) reports `tls_enabled`,
  `tls_container_ref` and `ca_tls_container_ref`, and the members become
  `ONLINE` in `get_load_balancer_pool_members`.
- `curl -vk https://<address>/` through the load balancer returns the page.
- From another host, `curl -v --cacert ca.crt https://10.40.40.11/` without a
  client certificate is refused by the member (nginx answers 400 "No required
  SSL certificate was sent"), which shows the member enforces mTLS.

To rotate the client certificate, register a new secret and point the pool at
it with `action="set"` and `tls_container_ref`.

Client authentication of end clients by the listener (a TLS-terminated HTTPS
load balancer with client authentication: the listener's
`client_ca_tls_container_ref`, `client_authentication` and
`client_crl_container_ref`) is a different feature and is not implemented.

## Tools and actions

| Tool | Actions | Purpose |
| --- | --- | --- |
| `get_secrets` | list, or show with `name` | Secret metadata and consumers; filter by `secret_type` |
| `get_secret_containers` | list, or show with `name` | Containers and the secret hrefs they group |
| `get_secret_orders` | list, or show with `order_id` | Key-generation orders and their result references |
| `get_secret_acl` | show | Read ACL of a secret or container |
| `get_key_manager_quotas` | show | Effective project quotas (-1 means unlimited) |
| `get_secret_stores` | list | Secret store backends; served only when multiple backends are enabled |
| `set_secret` | `create_self_signed_tls`, `delete` | Self-signed PKCS#12 secret; delete a secret |
| `set_secret_container` | `create`, `delete` | Group existing secrets (`generic`, `certificate`, `rsa`); deleting keeps the secrets |
| `set_secret_order` | `create`, `delete` | Barbican-generated symmetric (`key`) or RSA (`asymmetric`) keys |
| `set_secret_acl` | `add_users`, `remove_users`, `set`, `delete` | Read ACL users and project-wide access of a secret or container |

`set_*` tools exist only with `ALLOW_MODIFY_OPERATIONS=true`. Secret, container
and order names are not unique; when a name matches several, use an ID or
href.

## Troubleshooting

| Symptom | Cause and action |
| --- | --- |
| `Barbican (key-manager) service is not available` | No `key-manager` endpoint in the Keystone catalog for the server's interface and `OS_REGION_NAME`. Barbican has no `OS_*_PORT` setting; the catalog endpoint must also be reachable from the MCP server |
| HTTP 403 when creating a secret | The account lacks the role Barbican's policy requires (see [Prerequisites](#prerequisites)) |
| Listener creation fails with a certificate error | The result adds a hint. Check that the secret exists in this project, is `ACTIVE`, holds a PKCS#12 bundle or is a certificate container, and that Octavia can read it (ACL) |
| `get_secret_stores` fails | Barbican serves this API only when multiple secret store backends are enabled |
| `not found or name is ambiguous` | Several secrets share the name, or none exists; use the ID or href from `get_secrets` |
