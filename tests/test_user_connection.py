"""Exercise per-user HTTP isolation without real credentials or cloud calls."""

import asyncio
import logging
from types import SimpleNamespace
from unittest.mock import Mock

import httpx
import pytest
from keystoneauth1 import exceptions

from mcp_openstack_ops import connection, user_connection as users


@pytest.fixture(autouse=True)
def isolated_mode(monkeypatch):
    monkeypatch.setattr(users, "enabled", True)
    yield
    assert users._identity.get() is None


def identity(name="alice", project="project-a"):
    conn = Mock()
    conn.current_project_id = project
    return users.RequestIdentity(
        conn, name, project, ("credential-id", "secret", "token")
    )


def headers(name="alice"):
    return {
        "X-OpenStack-Application-Credential-ID": name,
        "X-OpenStack-Application-Credential-Secret": "secret",
    }


@pytest.mark.asyncio
async def test_concurrent_requests_and_worker_threads_are_isolated(monkeypatch):
    connections = {name: identity(name, f"project-{name}") for name in ("alice", "bob")}
    monkeypatch.setattr(users, "authenticate", lambda key, secret: connections[key])
    entered = 0
    ready = asyncio.Event()

    async def app(scope, receive, send):
        nonlocal entered
        first = connection.get_openstack_connection()
        entered += 1
        if entered == 2:
            ready.set()
        await asyncio.wait_for(ready.wait(), 5)
        from anyio import to_thread
        second = await to_thread.run_sync(connection.get_openstack_connection)
        assert first is second
        await httpx_response(first.current_project_id, scope, receive, send)

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=users.UserConnectionMiddleware(app)),
        base_url="https://mcp.example",
    ) as client:
        replies = await asyncio.gather(*[
            client.post("/mcp", headers=headers(name)) for name in connections
        ])
    assert [reply.json() for reply in replies] == ["project-alice", "project-bob"]
    for item in connections.values():
        item.connection.close.assert_called_once()
        item.connection.session.session.close.assert_called_once()


async def httpx_response(value, scope, receive, send):
    from starlette.responses import JSONResponse
    await JSONResponse(value)(scope, receive, send)


@pytest.mark.asyncio
@pytest.mark.parametrize("request_headers", [{}, headers() | {
    "X-OpenStack-Application-Credential-Secret": ""
}, [("x-openstack-application-credential-id", "a"),
    ("x-openstack-application-credential-id", "b"),
    ("x-openstack-application-credential-secret", "secret")]])
async def test_missing_empty_or_duplicate_credentials_never_reach_tools(
    monkeypatch, request_headers
):
    auth = Mock()
    monkeypatch.setattr(users, "authenticate", auth)
    app = Mock()
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=users.UserConnectionMiddleware(app)),
        base_url="https://mcp.example",
    ) as client:
        reply = await client.post("/mcp", headers=request_headers)
    assert reply.status_code == 401
    auth.assert_not_called()
    app.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize("authorization", [
    None,
    "Basic shared-secret",
    "Bearer wrong-secret",
])
async def test_bearer_rejection_happens_before_keystone_authentication(
    monkeypatch, authorization
):
    auth = Mock()
    monkeypatch.setattr(users, "authenticate", auth)
    app = Mock()
    request_headers = headers()
    if authorization:
        request_headers["Authorization"] = authorization
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(
            app=users.UserConnectionMiddleware(app, bearer_secret="shared-secret")
        ),
        base_url="https://mcp.example",
    ) as client:
        reply = await client.post("/mcp", headers=request_headers)
    assert reply.status_code == 401
    assert reply.headers["www-authenticate"] == "Bearer"
    auth.assert_not_called()
    app.assert_not_called()


@pytest.mark.asyncio
async def test_valid_bearer_then_authenticates_application_credential(monkeypatch):
    item = identity()
    auth = Mock(return_value=item)
    monkeypatch.setattr(users, "authenticate", auth)

    async def run_sync(function, *args):
        return function(*args)

    monkeypatch.setattr(users.anyio.to_thread, "run_sync", run_sync)

    async def app(scope, receive, send):
        await httpx_response("ok", scope, receive, send)

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(
            app=users.UserConnectionMiddleware(app, bearer_secret="shared-secret")
        ),
        base_url="https://mcp.example",
    ) as client:
        reply = await client.post("/mcp", headers={
            **headers(), "Authorization": "Bearer shared-secret",
        })
    assert reply.status_code == 200
    auth.assert_called_once_with("alice", "secret")
    assert "shared-secret" in item.sensitive
    item.connection.close.assert_called_once()


@pytest.mark.asyncio
@pytest.mark.parametrize("error,code", [
    (exceptions.Unauthorized("secret"), 401),
    (exceptions.NotFound("secret"), 401),
    (RuntimeError("secret"), 503),
])
async def test_auth_failure_is_generic_and_never_falls_back(
    monkeypatch, caplog, error, code
):
    monkeypatch.setattr(users, "authenticate", Mock(side_effect=error))
    app = Mock()
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=users.UserConnectionMiddleware(app)),
        base_url="https://mcp.example",
    ) as client:
        reply = await client.post("/mcp", headers=headers())
    assert reply.status_code == code
    assert "secret" not in reply.text + caplog.text
    app.assert_not_called()


@pytest.mark.asyncio
async def test_revalidates_same_credential_and_rejects_revocation(monkeypatch):
    item = identity()
    auth = Mock(side_effect=[item, exceptions.Unauthorized("revoked")])
    monkeypatch.setattr(users, "authenticate", auth)

    async def app(scope, receive, send):
        await httpx_response("ok", scope, receive, send)

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=users.UserConnectionMiddleware(app)),
        base_url="https://mcp.example",
    ) as client:
        assert (await client.post("/mcp", headers=headers())).status_code == 200
        assert (await client.post("/mcp", headers=headers())).status_code == 401
    assert auth.call_count == 2
    item.connection.close.assert_called_once()


@pytest.mark.asyncio
async def test_connection_closed_when_tool_raises(monkeypatch):
    item = identity()
    monkeypatch.setattr(users, "authenticate", lambda *args: item)

    async def app(scope, receive, send):
        raise RuntimeError("tool failed")

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=users.UserConnectionMiddleware(app)),
        base_url="https://mcp.example",
    ) as client:
        with pytest.raises(RuntimeError, match="tool failed"):
            await client.post("/mcp", headers=headers())
    item.connection.close.assert_called_once()
    item.connection.session.session.close.assert_called_once()


@pytest.mark.asyncio
async def test_cancelled_authentication_closes_late_worker_result(monkeypatch):
    from threading import Event
    started, finish = Event(), Event()
    item = identity()

    def authenticate(*args):
        started.set()
        assert finish.wait(5)
        return item

    monkeypatch.setattr(users, "authenticate", authenticate)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=users.UserConnectionMiddleware(Mock())),
        base_url="https://mcp.example",
    ) as client:
        task = asyncio.create_task(client.post("/mcp", headers=headers()))
        try:
            for _ in range(500):
                if started.is_set():
                    break
                await asyncio.sleep(0.01)
            assert started.is_set()
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
        finally:
            finish.set()
        for _ in range(500):
            if item.connection.close.called:
                break
            await asyncio.sleep(0.01)
    item.connection.close.assert_called_once()
    item.connection.session.session.close.assert_called_once()


def test_no_environment_fallback_without_request(monkeypatch):
    monkeypatch.setattr(connection, "_connection_cache", Mock())
    with pytest.raises(RuntimeError, match="authenticated HTTP request"):
        connection.get_openstack_connection()


def test_legacy_connection_cache_is_preserved(monkeypatch):
    monkeypatch.setattr(users, "enabled", False)
    cached = Mock()
    monkeypatch.setattr(connection, "_connection_cache", cached)
    assert connection.get_openstack_connection() is cached


def test_probe_tls_options_preserve_legacy_behavior(monkeypatch):
    from mcp_openstack_ops.services.core import _probe_request_options
    conn = Mock()
    conn.session.verify = "/private-ca.pem"
    assert _probe_request_options(conn) == {
        "verify": "/private-ca.pem", "allow_redirects": False,
    }
    monkeypatch.setattr(users, "enabled", False)
    assert _probe_request_options(conn) == {}


def test_project_boundary_is_unchanged():
    item = identity()
    token = users._identity.set(item)
    try:
        assert connection.validate_resource_ownership(
            SimpleNamespace(project_id="project-a"), "Instance"
        )
        assert not connection.validate_resource_ownership(
            SimpleNamespace(project_id="project-b"), "Instance"
        )
    finally:
        users._identity.reset(token)


def test_credential_redaction():
    token = users._identity.set(identity())
    try:
        record = logging.LogRecord(
            "sdk", logging.INFO, "", 0, "headers %s %s %s",
            ("secret", "token", "credential-id"), None,
        )
        assert users.CredentialRedaction().filter(record)
        assert record.getMessage() == "headers [REDACTED] [REDACTED] [REDACTED]"
    finally:
        users._identity.reset(token)


@pytest.mark.parametrize("project", ["project-a", "project-b"])
def test_real_sdk_config_has_no_auth_or_disk_cache(monkeypatch, project):
    monkeypatch.setenv("OS_AUTH_HOST", "cloud.example")
    monkeypatch.setenv("OS_AUTH_PROTOCOL", "https")
    monkeypatch.setenv("OS_HEAT_STACK_PORT", "18004")
    monkeypatch.setenv("OS_USERNAME", "must-not-be-used")
    monkeypatch.setenv("OS_PASSWORD", "must-not-be-used")
    access = SimpleNamespace(
        user_id="alice", project_id=project, auth_token="token"
    )
    monkeypatch.setattr(users.ApplicationCredential, "get_access", lambda *args: access)
    item = users.authenticate("credential-id", "secret")
    try:
        assert item.connection.config.skip_auth_cache()
        assert item.connection.config.config["auth"] == {}
        assert item.connection.session.verify is not False
        assert item.connection.session.auth.reauthenticate is False
        endpoint = item.connection.config.config["compute_endpoint_override"]
        assert endpoint.startswith("https://")
        assert item.connection.config.get_api_version("block-storage") == "3"
        storage = item.connection.config.get_endpoint("block-storage")
        assert storage.endswith(f"/v3/{project}")
        assert item.connection.config.get_api_version("orchestration") == "1"
        heat = item.connection.config.get_endpoint("orchestration")
        assert heat == f"https://cloud.example:18004/v1/{project}"
    finally:
        item.connection.close()
        item.connection.session.session.close()


def test_unscoped_auth_closes_session(monkeypatch):
    monkeypatch.setenv("OS_AUTH_HOST", "cloud.example")
    monkeypatch.setenv("OS_AUTH_PROTOCOL", "https")
    monkeypatch.setattr(users.ApplicationCredential, "get_access", lambda *args:
                        SimpleNamespace(user_id="alice", project_id=None))
    session = Mock()
    monkeypatch.setattr(users, "Session", Mock(return_value=session))
    with pytest.raises(ValueError, match="project-scoped"):
        users.authenticate("credential-id", "secret")
    session.session.close.assert_called_once()


def test_catalog_or_redirect_cannot_send_token_over_http(monkeypatch):
    import requests
    request = requests.Request("GET", "http://cloud.example/servers",
                               headers={"X-Auth-Token": "token"}).prepare()
    send = Mock()
    monkeypatch.setattr(requests.Session, "send", send)
    with users.RestrictedSession("https") as session:
        with pytest.raises(ValueError, match="require HTTPS"):
            session.send(request)
    send.assert_not_called()


def test_insecure_http_mode_builds_http_endpoints(monkeypatch):
    monkeypatch.setenv("OS_AUTH_HOST", "cloud.example")
    monkeypatch.setenv("OS_AUTH_PROTOCOL", "http")
    monkeypatch.setenv("MCP_MULTI_USER_ALLOW_INSECURE_HTTP", "true")
    access = SimpleNamespace(
        user_id="alice", project_id="project-a", auth_token="token"
    )
    monkeypatch.setattr(users.ApplicationCredential, "get_access", lambda *args: access)

    item = users.authenticate("credential-id", "secret")
    try:
        assert item.connection.session.auth.auth_url.startswith("http://")
        endpoint = item.connection.config.config["compute_endpoint_override"]
        assert endpoint.startswith("http://")
    finally:
        item.connection.close()
        item.connection.session.session.close()


def test_multi_user_http_requires_explicit_insecure_opt_in(monkeypatch):
    monkeypatch.setenv("OS_AUTH_HOST", "cloud.example")
    monkeypatch.setenv("OS_AUTH_PROTOCOL", "http")
    monkeypatch.delenv("MCP_MULTI_USER_ALLOW_INSECURE_HTTP", raising=False)

    with pytest.raises(ValueError, match="requires OS_AUTH_PROTOCOL=https"):
        users.authenticate("credential-id", "secret")


def test_multi_user_startup_rejects_http_without_explicit_opt_in(monkeypatch):
    from mcp_openstack_ops.mcp_main import main
    monkeypatch.setenv("OS_AUTH_PROTOCOL", "http")
    monkeypatch.setenv("OS_AUTH_HOST", "cloud.example")
    monkeypatch.delenv("MCP_MULTI_USER_ALLOW_INSECURE_HTTP", raising=False)

    with pytest.raises(SystemExit) as error:
        main(["--multi-user", "--type", "streamable-http"])

    assert error.value.code == 2


@pytest.mark.parametrize("args", [["--multi-user"]])
def test_invalid_startup_modes(monkeypatch, args):
    from mcp_openstack_ops.mcp_main import main
    monkeypatch.setenv("FASTMCP_TYPE", "stdio")
    monkeypatch.setenv("OS_AUTH_PROTOCOL", "https")
    monkeypatch.setenv("OS_AUTH_HOST", "cloud.example")
    with pytest.raises(SystemExit) as error:
        main(args)
    assert error.value.code == 2


def test_multi_user_starts_stateless_and_keeps_writes_off(monkeypatch):
    from mcp_openstack_ops import mcp_main
    monkeypatch.setenv("OS_AUTH_PROTOCOL", "https")
    monkeypatch.setenv("OS_AUTH_HOST", "cloud.example")
    monkeypatch.setenv("REMOTE_SECRET_KEY", "ignored-when-disabled")
    monkeypatch.delenv("REMOTE_AUTH_ENABLE", raising=False)
    monkeypatch.delenv("ALLOW_MODIFY_OPERATIONS", raising=False)
    run = Mock()
    monkeypatch.setattr(mcp_main.mcp, "run", run)
    mcp_main.main(["--multi-user", "--type", "streamable-http"])
    assert run.call_args.kwargs["stateless_http"] is True
    assert run.call_args.kwargs["json_response"] is True
    middleware = run.call_args.kwargs["middleware"][0]
    assert middleware.kwargs["bearer_secret"] is None
    assert not mcp_main._is_modify_operation_allowed()


def test_multi_user_allows_explicit_insecure_http_test_mode(monkeypatch, caplog):
    from mcp_openstack_ops import mcp_main
    monkeypatch.setenv("OS_AUTH_PROTOCOL", "http")
    monkeypatch.setenv("OS_AUTH_HOST", "cloud.example")
    monkeypatch.setenv("MCP_MULTI_USER_ALLOW_INSECURE_HTTP", "true")
    run = Mock()
    monkeypatch.setattr(mcp_main.mcp, "run", run)

    with caplog.at_level("WARNING"):
        mcp_main.main(["--multi-user", "--type", "streamable-http"])

    run.assert_called_once()
    assert "INSECURE TEST MODE" in caplog.text


def test_multi_user_and_bearer_start_as_layered_authentication(monkeypatch):
    from mcp_openstack_ops import mcp_main
    monkeypatch.setenv("OS_AUTH_PROTOCOL", "https")
    monkeypatch.setenv("OS_AUTH_HOST", "cloud.example")
    run = Mock()
    monkeypatch.setattr(mcp_main.mcp, "run", run)

    mcp_main.main([
        "--multi-user", "--type", "streamable-http",
        "--auth-enable", "--secret-key", "shared-secret",
    ])

    assert mcp_main.mcp.auth is None
    middleware = run.call_args.kwargs["middleware"][0]
    assert middleware.kwargs["bearer_secret"] == "shared-secret"


@pytest.mark.parametrize("bearer_enabled", [False, True])
def test_single_account_http_keeps_optional_bearer_authentication(
    monkeypatch, bearer_enabled
):
    from mcp_openstack_ops import mcp_main
    monkeypatch.delenv("MCP_MULTI_USER", raising=False)
    monkeypatch.delenv("REMOTE_AUTH_ENABLE", raising=False)
    monkeypatch.delenv("REMOTE_SECRET_KEY", raising=False)
    run = Mock()
    monkeypatch.setattr(mcp_main.mcp, "run", run)
    args = ["--type", "streamable-http"]
    if bearer_enabled:
        args += ["--auth-enable", "--secret-key", "shared-secret"]

    mcp_main.main(args)

    assert (mcp_main.mcp.auth is not None) is bearer_enabled
    assert "middleware" not in run.call_args.kwargs


@pytest.mark.asyncio
async def test_real_mcp_http_tools_receive_request_identity(monkeypatch):
    from fastmcp import FastMCP
    from starlette.middleware import Middleware

    server = FastMCP("isolation-test")
    server.add_middleware(users.UserAuditMiddleware())
    created = []

    def authenticate(key, secret):
        item = identity(key, f"project-{key}")
        created.append(item)
        return item

    monkeypatch.setattr(users, "authenticate", authenticate)

    @server.tool
    def who_am_i() -> str:
        return connection.get_openstack_connection().current_project_id

    app = server.http_app(
        stateless_http=True, json_response=True,
        middleware=[Middleware(users.UserConnectionMiddleware)],
    )
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="https://mcp.example",
        ) as client:
            async def call(name):
                return await client.post("/mcp", headers={
                    **headers(name), "Accept": "application/json, text/event-stream",
                }, json={"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                         "params": {"name": "who_am_i", "arguments": {}}})
            replies = await asyncio.gather(call("alice"), call("bob"))
    for name, reply in zip(("alice", "bob"), replies):
        assert reply.status_code == 200, reply.text
        assert reply.json()["result"]["content"][0]["text"] == f"project-{name}"
    assert len(created) == 2
    for item in created:
        item.connection.close.assert_called_once()


@pytest.mark.asyncio
@pytest.mark.parametrize('path', [
    '/.well-known/oauth-protected-resource',
    '/.well-known/oauth-protected-resource/mcp',
    '/.well-known/oauth-authorization-server',
    '/.well-known/openid-configuration',
    '/mcp/.well-known/openid-configuration',
    '/register', '/register/',
])
@pytest.mark.parametrize('method', ['GET', 'POST'])
async def test_unsupported_oauth_routes_do_not_authenticate(monkeypatch, path, method):
    auth, app = Mock(), Mock()
    monkeypatch.setattr(users, 'authenticate', auth)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=users.UserConnectionMiddleware(app)),
        base_url='https://mcp.example',
    ) as client:
        response = await client.request(method, path, headers=headers())
    assert response.status_code == 404
    auth.assert_not_called()
    app.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize('path', ['/mcp', '/mcp/', '/register-tool',
                                  '/.well-known/oauth-protected-resource-other'])
async def test_other_routes_still_require_credentials(monkeypatch, path):
    auth, app = Mock(), Mock()
    monkeypatch.setattr(users, 'authenticate', auth)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=users.UserConnectionMiddleware(app)),
        base_url='https://mcp.example',
    ) as client:
        response = await client.post(path)
    assert response.status_code == 401
    auth.assert_not_called()
    app.assert_not_called()


@pytest.mark.parametrize('body,reason', [
    (b'{"error":{"message":"Parse error: private-value"}}', 'invalid_json'),
    (b'{"error":{"message":"Validation error: private-value"}}', 'invalid_jsonrpc'),
    (b'{"error":{"message":"Bad Request: Unsupported protocol version: private-value"}}', 'unsupported_protocol'),
    (b'{"error":{"message":"params._meta must be an object carrying the required '
     b"'io.modelcontextprotocol/protocolVersion' and 'io.modelcontextprotocol/clientCapabilities' "
     b'envelope keys"}}', 'unsupported_protocol'),
    (b'{"error":{"message":"Bad Request: Missing session ID"}}', 'missing_session_id'),
    (b'{"error":{"message":"private-value"}}', 'unclassified'),
    (b'[]', 'unclassified'), (b'null', 'unclassified'),
    (b'{"error":[]}', 'unclassified'), (b'\xff', 'unclassified'),
])
def test_bad_request_classification_is_safe(body, reason):
    assert users._bad_request_reason(body) == reason


@pytest.mark.asyncio
async def test_real_transport_rejections_are_diagnosed_without_request_values(
    monkeypatch, caplog,
):
    from fastmcp import FastMCP
    from starlette.middleware import Middleware

    monkeypatch.setattr(users, 'authenticate', lambda *args: identity())
    caplog.set_level(logging.INFO, logger=users.__name__)
    server = FastMCP('transport-diagnostic-test')
    app = server.http_app(stateless_http=True, json_response=True,
                         middleware=[Middleware(users.UserConnectionMiddleware)])
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),
                                     base_url='https://mcp.example') as client:
            base_headers = {**headers(), 'Accept': 'application/json',
                            'Content-Type': 'application/json'}
            replies = [await client.post('/mcp', headers=base_headers,
                                         content='private-value')]
            replies.append(await client.post('/mcp', headers=base_headers,
                                             json={'private-value': True}))
            replies.append(await client.post('/mcp', headers={
                **base_headers, 'MCP-Protocol-Version': 'private-value',
            }, json={'jsonrpc': '2.0', 'id': 1, 'method': 'ping'}))
            ok = await client.post('/mcp', headers=base_headers,
                                   json={'jsonrpc': '2.0', 'id': 2, 'method': 'ping'})
    assert [r.status_code for r in replies] == [400, 400, 400]
    assert ok.status_code == 200
    messages = '\n'.join(r.getMessage() for r in caplog.records
                         if r.name == users.__name__)
    for reason in ('invalid_json', 'invalid_jsonrpc', 'unsupported_protocol'):
        assert f'reason={reason}' in messages
    assert 'private-value' not in messages


@pytest.mark.asyncio
@pytest.mark.parametrize('body', [
    b'{"error":{"message":"Validation error: private-value"}}',
    b'private-value' * 2000,
    b'[' * 2000 + b']' * 2000,
])
async def test_chunked_bad_response_is_forwarded_unchanged(monkeypatch, caplog, body):
    monkeypatch.setattr(users, 'authenticate', lambda *args: identity())
    caplog.set_level(logging.INFO, logger=users.__name__)

    async def app(scope, receive, send):
        await send({'type': 'http.response.start', 'status': 400, 'headers': []})
        await send({'type': 'http.response.body', 'body': body[:15], 'more_body': True})
        await send({'type': 'http.response.body', 'body': body[15:]})

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=users.UserConnectionMiddleware(app)),
        base_url='https://mcp.example',
    ) as client:
        reply = await client.post('/mcp', headers=headers())
    assert reply.status_code == 400
    assert reply.content == body
    assert 'OpenStack transport rejected' in caplog.text
    assert 'private-value' not in caplog.text
