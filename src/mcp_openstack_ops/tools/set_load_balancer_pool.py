"""Tool implementation for set_load_balancer_pool."""

import json
from datetime import datetime
from typing import Optional
from ..mcp_main import (
    _read_action_error,
    conditional_tool,
    logger,
)

READ_ACTIONS = {'show': 'get_load_balancer_pools'}


@conditional_tool
async def set_load_balancer_pool(
    action: str,
    pool_name_or_id: str = "",
    name: str = "",
    listener_name_or_id: str = "",
    protocol: str = "",
    lb_algorithm: str = "",
    description: str = "",
    admin_state_up: Optional[bool] = None,
    tls_enabled: str = "",
    tls_container_ref: str = "",
    ca_tls_container_ref: str = "",
    crl_container_ref: str = "",
    tls_versions: str = "",
    tls_ciphers: str = "",
    alpn_protocols: str = ""
) -> str:
    """
    Manage OpenStack load balancer pool operations (create, delete, set).
    To list or inspect pools, use get_load_balancer_pools and
    get_load_balancer_pool_members.

    Functions:
    - Create new pools for listeners with specified protocols
    - Delete existing pools
    - Update pool properties (name, description, algorithm, admin state)
    - Backend re-encryption: TLS from the load balancer to the members

    TLS to members, by setup (Octavia cookbook terms):
    - Non-terminated HTTPS (TLS passthrough): HTTPS listener + HTTPS pool;
      members hold the certificates, no Barbican secret is needed (use a
      TLS-HELLO or HTTPS health monitor).
    - Backend re-encryption: usually a TERMINATED_HTTPS listener + HTTP pool
      with tls_enabled=true; set ca_tls_container_ref to verify member
      certificates. Adding tls_container_ref enables client authentication
      (mTLS), where the load balancer also presents a client certificate.

    Use when user requests:
    - "Create pool [name] for listener [listener] using HTTP"
    - "Delete pool [name/id]"
    - "Update pool [name] algorithm to LEAST_CONNECTIONS"
    - "Re-encrypt traffic to the members of pool [name] and verify them with CA [secret]"

    Args:
        action: Operation to perform (create, delete, set)
        pool_name_or_id: Pool name or ID (required for delete/set)
        name: Name for new pool (required for create)
        listener_name_or_id: Listener name or ID (required for create)
        protocol: Pool protocol - HTTP, HTTPS, TCP, UDP (required for create).
            Use HTTP with tls_enabled=true for backend re-encryption
        lb_algorithm: Load balancing algorithm (ROUND_ROBIN, LEAST_CONNECTIONS,
            SOURCE_IP). create defaults to ROUND_ROBIN; set changes it only
            when given
        description: Description for the pool
        admin_state_up: Administrative state. create defaults to True; set
            changes it only when given
        tls_enabled: true or false to turn backend re-encryption on or off
            (create/set); empty leaves it unchanged
        tls_container_ref: Client authentication: the client certificate the
            load balancer presents to members that require mutual TLS (mTLS).
            Optional; requires tls_enabled. A PKCS#12 secret or
            certificate container, by name, ID or href
        ca_tls_container_ref: CA certificate (PEM secret) used to verify member
            certificates; without it member certificates are not verified
        crl_container_ref: Certificate revocation list (PEM secret) for member
            certificates; requires ca_tls_container_ref
        tls_versions: Comma-separated TLS versions to members, e.g. TLSv1.2,TLSv1.3
        tls_ciphers: OpenSSL cipher string for connections to members
        alpn_protocols: Comma-separated ALPN protocols to members, e.g. h2,http/1.1

    Returns:
        JSON string with operation results and pool details
    """
    read_error = _read_action_error(action, READ_ACTIONS)
    if read_error:
        return read_error
    def split(value: str) -> list:
        return [item.strip() for item in value.split(',') if item.strip()]

    enabled = tls_enabled.strip().lower()
    if enabled not in ('', 'true', 'false'):
        return json.dumps({'success': False,
                           'message': 'tls_enabled must be true, false or empty'})
    try:
        from ..functions import set_load_balancer_pool

        result = set_load_balancer_pool(
            action=action,
            pool_name_or_id=pool_name_or_id,
            name=name,
            listener_name_or_id=listener_name_or_id,
            protocol=protocol,
            lb_algorithm=lb_algorithm,
            description=description,
            admin_state_up=admin_state_up,
            tls_enabled=None if not enabled else enabled == 'true',
            tls_container_ref=tls_container_ref,
            ca_tls_container_ref=ca_tls_container_ref,
            crl_container_ref=crl_container_ref,
            tls_versions=split(tls_versions) or None,
            tls_ciphers=tls_ciphers,
            alpn_protocols=split(alpn_protocols) or None,
        )
        
        response = {
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "result": result
        }
        
        return json.dumps(response, indent=2, ensure_ascii=False)
        
    except Exception as e:
        error_msg = f"Error: Failed to manage load balancer pool - {str(e)}"
        logger.error(error_msg)
        return json.dumps({
            "timestamp": datetime.now().isoformat(),
            "error": error_msg,
            "success": False
        }, indent=2)
