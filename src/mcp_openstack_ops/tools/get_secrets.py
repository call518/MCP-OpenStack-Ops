"""Tool implementation for get_secrets."""

import json
from ..services.key_manager import get_secrets as _query
from ..mcp_main import mcp


@mcp.tool()
async def get_secrets(name: str = "", secret_type: str = "", limit: int = 100) -> str:
    """List or show Barbican secrets of the current project (metadata only).

    Never returns a secret payload; payload retrieval is intentionally not
    provided so key material cannot reach the LLM. Use the secret_ref from this
    tool as a reference, for example in set_load_balancer_listener.

    Args:
        name: Secret name, ID or href to show one secret with its consumers.
            Empty lists secrets.
        secret_type: Filter for the list, e.g. opaque, certificate, private,
            symmetric, public, passphrase.
        limit: Maximum number of secrets to list (1-1000).
    """
    return json.dumps(_query(name=name, secret_type=secret_type, limit=limit),
                      indent=2, default=str)
