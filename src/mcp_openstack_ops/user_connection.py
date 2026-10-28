"""Request-local Application Credential authentication for remote clients."""

import asyncio
import logging
import os
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlsplit
from uuid import uuid4

import anyio
import requests
from fastmcp.server.middleware import CallNext, Middleware, MiddlewareContext
from keystoneauth1 import exceptions as auth_exceptions
from keystoneauth1.identity.v3 import ApplicationCredential
from keystoneauth1.session import Session
from openstack.config.cloud_region import CloudRegion
from openstack.config.defaults import get_defaults
from openstack.connection import Connection
from starlette.datastructures import Headers
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

logger = logging.getLogger(__name__)
enabled = False


class HTTPSOnlySession(requests.Session):
    """Prevent catalog endpoints or redirects from sending tokens over HTTP."""

    def send(
        self, request: requests.PreparedRequest, **kwargs: Any
    ) -> requests.Response:
        """Check the final prepared URL before sending credentials."""
        if urlsplit(request.url).scheme != "https":
            raise ValueError("Multi-user OpenStack requests require HTTPS")
        kwargs["allow_redirects"] = False
        return super().send(request, **kwargs)


@dataclass
class RequestIdentity:
    """Keep connections and sensitive values out of object representations."""

    connection: Connection = field(repr=False)
    user_id: str
    project_id: str
    sensitive: tuple[str, ...] = field(repr=False)
    request_id: str = ""


_identity: ContextVar[RequestIdentity | None] = ContextVar(
    "openstack_request_identity", default=None
)


def get_connection() -> Connection | None:
    """Return only the calling request's connection in multi-user mode."""
    if not enabled:
        return None
    identity = _identity.get()
    if identity is None:
        raise RuntimeError("An authenticated HTTP request is required")
    return identity.connection


def _close_connection(conn: Connection) -> None:
    try:
        conn.close()
    finally:
        conn.session.session.close()


def _discard_authentication(task: asyncio.Task[RequestIdentity]) -> None:
    # A disconnected request may disappear before its authentication worker ends.
    try:
        identity = task.result()
    except (Exception, asyncio.CancelledError):
        return
    _close_connection(identity.connection)


class CredentialRedaction(logging.Filter):
    """Redact this request's credentials even from SDK debug messages."""

    def filter(self, record: logging.LogRecord) -> bool:
        identity = _identity.get()
        if identity:
            message = record.getMessage()
            for value in identity.sensitive:
                if value:
                    message = message.replace(value, "[REDACTED]")
            record.msg, record.args = message, ()
            # Tracebacks may include SDK exception text containing credentials.
            record.exc_info = None
            record.exc_text = None
        return True


def configure(active: bool) -> None:
    """Enable request isolation before serving requests."""
    global enabled
    enabled = active
    if active:
        for handler in logging.getLogger().handlers:
            if not any(isinstance(f, CredentialRedaction) for f in handler.filters):
                handler.addFilter(CredentialRedaction())
        # Authentication occurs before a validated identity exists. Do not emit
        # HTTP wire logs while exchanging application credentials for a token.
        for name in ("keystoneauth", "openstack", "urllib3", "httpx", "httpcore"):
            logging.getLogger(name).setLevel(logging.WARNING)


class UserAuditMiddleware(Middleware):
    """Attribute tool calls without logging tool arguments or results."""

    async def on_call_tool(
        self, context: MiddlewareContext[Any], call_next: CallNext[Any, Any]
    ) -> Any:
        """Audit the validated principal, tool name, and completion."""
        identity = _identity.get()
        if not enabled:
            return await call_next(context)
        if identity is None:
            raise RuntimeError("An authenticated HTTP request is required")
        logger.info(
            "OpenStack tool started request_id=%s user_id=%s project_id=%s tool=%s",
            identity.request_id, identity.user_id, identity.project_id,
            context.message.name,
        )
        try:
            result = await call_next(context)
        except Exception:
            logger.warning(
                "OpenStack tool failed request_id=%s user_id=%s project_id=%s tool=%s",
                identity.request_id, identity.user_id, identity.project_id,
                context.message.name,
            )
            raise
        logger.info(
            "OpenStack tool returned request_id=%s user_id=%s project_id=%s tool=%s",
            identity.request_id, identity.user_id, identity.project_id,
            context.message.name,
        )
        return result


def authenticate(credential_id: str, secret: str) -> RequestIdentity:
    """Authenticate afresh; never consult environment credentials or keyrings."""
    host = os.environ["OS_AUTH_HOST"]
    port = int(os.environ.get("OS_AUTH_PORT", "5000"))
    if os.environ.get("OS_AUTH_PROTOCOL", "http").lower() != "https":
        raise ValueError("Multi-user mode requires OS_AUTH_PROTOCOL=https")
    if any(char in host for char in "/@?#"):
        raise ValueError("OS_AUTH_HOST must be a hostname or IP address")
    auth = ApplicationCredential(
        auth_url=f"https://{host}:{port}/v3",
        application_credential_id=credential_id,
        application_credential_secret=secret,
        reauthenticate=False,
    )
    session = Session(
        auth=auth, session=HTTPSOnlySession(),
        verify=os.getenv("OS_CACERT") or True, timeout=10, redirect=0,
    )
    conn = None
    try:
        access = auth.get_access(session)
        if not access.project_id or not access.user_id:
            raise ValueError("A user and project-scoped credential is required")
        # Service endpoints come only from operator configuration, never headers.
        config = {
            **get_defaults(),
            "auth": {},
            "interface": "internal",
            "region_name": os.getenv("OS_REGION_NAME", "RegionOne"),
            "identity_api_version": "3",
            "block_storage_api_version": "3",
            "identity_endpoint_override": f"https://{host}:{port}/v3",
        }
        for service, variable, default, path in (
            ("compute", "OS_COMPUTE_PORT", "8774", "/v2.1"),
            ("network", "OS_NETWORK_PORT", "9696", ""),
            ("block_storage", "OS_VOLUME_PORT", "8776", f"/v3/{access.project_id}"),
            ("image", "OS_IMAGE_PORT", "9292", ""),
            ("placement", "OS_PLACEMENT_PORT", "8780", ""),
            ("orchestration", "OS_HEAT_STACK_PORT", "8004", "/v1"),
        ):
            service_port = int(os.getenv(variable, default))
            config[f"{service}_endpoint_override"] = (
                f"https://{host}:{service_port}{path}"
            )
        conn = Connection(config=CloudRegion(
            config=config, session=session, auth_plugin=auth,
            cache_auth=False,
        ))
        return RequestIdentity(
            conn, access.user_id, access.project_id,
            (credential_id, secret, access.auth_token),
        )
    except Exception:
        try:
            if conn:
                conn.close()
        finally:
            session.session.close()
        raise


class UserConnectionMiddleware:
    """Authenticate every HTTP request and close its connection after delivery.

    Used with stateless HTTP so no long-lived MCP task inherits another
    request's identity. No server-side credential or authentication cache.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        headers = Headers(scope=scope)
        ids = headers.getlist("x-openstack-application-credential-id")
        secrets = headers.getlist("x-openstack-application-credential-secret")
        if (
            len(ids) != 1 or len(secrets) != 1 or not ids[0] or not secrets[0]
            or len(ids[0]) > 256 or len(secrets[0]) > 4096
        ):
            await JSONResponse(
                {"error": "Application credential headers are required"},
                status_code=401,
            )(scope, receive, send)
            return
        request_id = str(uuid4())
        authentication = asyncio.create_task(
            anyio.to_thread.run_sync(authenticate, ids[0], secrets[0])
        )
        try:
            identity = await asyncio.shield(authentication)
        except asyncio.CancelledError:
            authentication.add_done_callback(_discard_authentication)
            raise
        except (
            auth_exceptions.Unauthorized,
            auth_exceptions.Forbidden,
            auth_exceptions.NotFound,
        ):
            logger.warning(
                "OpenStack authentication rejected request_id=%s", request_id
            )
            await JSONResponse({"error": "Authentication failed"}, status_code=401)(
                scope, receive, send
            )
            return
        except Exception:
            logger.warning(
                "OpenStack authentication unavailable request_id=%s", request_id
            )
            await JSONResponse(
                {"error": "OpenStack authentication unavailable"}, status_code=503
            )(scope, receive, send)
            return
        identity.request_id = request_id
        token = _identity.set(identity)
        logger.info(
            "OpenStack request started request_id=%s user_id=%s project_id=%s",
            request_id, identity.user_id, identity.project_id,
        )
        status = 500

        async def audit_send(message: Message) -> None:
            nonlocal status
            if message["type"] == "http.response.start":
                status = message["status"]
            await send(message)

        try:
            await self.app(scope, receive, audit_send)
        finally:
            try:
                # Connection.close unregisters its atexit hook. cache_auth=False
                # prevents SDK keyring writes, and the HTTP pool is closed too.
                _close_connection(identity.connection)
            finally:
                logger.info(
                    "OpenStack request finished request_id=%s user_id=%s "
                    "project_id=%s http_status=%s", request_id,
                    identity.user_id, identity.project_id, status,
                )
                _identity.reset(token)
