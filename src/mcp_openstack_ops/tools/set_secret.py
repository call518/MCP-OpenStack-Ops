"""Tool implementation for set_secret."""

import json
from ..services.key_manager import set_secret as _set_secret
from ..mcp_main import (
    _is_modify_operation_allowed,
    conditional_tool,
)


@conditional_tool
async def set_secret(
    action: str,
    name: str = "",
    common_name: str = "",
    subject_alt_names: str = "",
    days: int = 365,
    key_size: int = 2048,
    expiration: str = ""
) -> str:
    """
    Create a self-signed TLS certificate secret in Barbican, or delete a secret.

    This tool has no payload parameter by design. Barbican can store any
    payload, but tool arguments and results pass through the LLM, so uploading
    user certificates or keys here would expose key material to an external
    model. Register user certificates through the CLI or another trusted path,
    then reference them by name or href.

    create_self_signed_tls generates the key and certificate inside the MCP
    server, stores them as one unencrypted PKCS#12 bundle (opaque secret, the
    format Octavia TERMINATED_HTTPS listeners accept) and returns only the
    secret href, the public certificate and its fingerprint. The private key is
    never returned.

    Args:
        action: create_self_signed_tls or delete
        name: Secret name (create_self_signed_tls), or secret name, ID or href (delete)
        common_name: Certificate subject CN, e.g. a host name or the VIP/FIP address
        subject_alt_names: Comma-separated DNS names and IP addresses for SAN
        days: Certificate validity in days (1-3650)
        key_size: RSA key size: 2048, 3072 or 4096
        expiration: Optional Barbican secret expiration (ISO 8601, UTC)

    Returns:
        JSON string with the operation result
    """
    if not _is_modify_operation_allowed():
        return json.dumps({
            'success': False,
            'message': f'Modify operations are not allowed in current environment for action: {action}',
            'error': 'MODIFY_OPERATIONS_DISABLED'
        })
    sans = [value.strip() for value in subject_alt_names.split(',') if value.strip()]
    return json.dumps(_set_secret(
        action=action, name=name, common_name=common_name,
        subject_alt_names=sans, days=days, key_size=key_size, expiration=expiration,
    ), indent=2, default=str)
