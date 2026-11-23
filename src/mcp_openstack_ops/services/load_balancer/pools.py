"""
Load Balancer Pool and Member Management Module

This module provides comprehensive load balancer pool and member management operations
including creating, updating, deleting, and querying pools and their members.
"""

import logging
from typing import Dict, Any, List, Optional
from ...connection import get_openstack_connection

logger = logging.getLogger(__name__)

POOL_TLS_FIELDS = ('tls_enabled', 'ca_tls_container_ref', 'crl_container_ref',
                   'tls_versions', 'tls_ciphers', 'alpn_protocols')


def _pool_tls_attrs(conn, tls_enabled: Optional[bool], tls_container_ref: str,
                    ca_tls_container_ref: str, crl_container_ref: str,
                    tls_versions: Optional[List[str]], tls_ciphers: str,
                    alpn_protocols: Optional[List[str]]) -> Dict[str, Any]:
    """Backend re-encryption attributes, with Barbican names resolved to hrefs."""
    from ..key_manager import resolve_secret_ref
    attrs: Dict[str, Any] = {}
    if tls_enabled is not None:
        attrs['tls_enabled'] = tls_enabled
    for key, value in (('tls_container_ref', tls_container_ref),
                       ('ca_tls_container_ref', ca_tls_container_ref),
                       ('crl_container_ref', crl_container_ref)):
        if value:
            attrs[key] = resolve_secret_ref(conn, value)
    if tls_versions:
        attrs['tls_versions'] = tls_versions
    if tls_ciphers:
        attrs['tls_ciphers'] = tls_ciphers
    if alpn_protocols:
        attrs['alpn_protocols'] = alpn_protocols
    return attrs


def _pool_tls_info(pool) -> Dict[str, Any]:
    return {key: getattr(pool, key, None) for key in POOL_TLS_FIELDS}


def _raw_pool(conn, pool_id: str) -> Dict[str, Any]:
    """Octavia's pool body; the SDK Pool resource has no tls_container_ref."""
    response = conn.load_balancer.get(f'/lbaas/pools/{pool_id}', raise_exc=True)
    return response.json().get('pool', {})


def _write_raw_pool(conn, method: str, path: str, body: Dict[str, Any]) -> Any:
    """Send a pool request through the Octavia API, then read it back via the SDK.

    Used only when tls_container_ref is set, which openstacksdk does not send.
    """
    response = getattr(conn.load_balancer, method)(
        path, json={'pool': body}, raise_exc=True)
    return conn.load_balancer.get_pool(response.json()['pool']['id'])


def _with_client_cert(conn, pool, info: Dict[str, Any]) -> Dict[str, Any]:
    try:
        info['tls_container_ref'] = _raw_pool(conn, pool.id).get('tls_container_ref')
    except Exception as e:
        info['tls_container_ref_error'] = str(e)
    return info


def resource_ref_ids(resource, id_attr: str, list_attr: str) -> list:
    """Return related resource IDs from a single-ID attribute and a reference list.

    Octavia accepts single IDs such as ``listener_id`` or ``pool_id`` only in
    create requests; GET responses report relations as lists of ``{'id': ...}``
    references (``listeners``, ``loadbalancers``, ``pools``).
    """
    ids = []
    single_id = getattr(resource, id_attr, None)
    if single_id:
        ids.append(single_id)
    for ref in getattr(resource, list_attr, None) or []:
        ref_id = ref.get('id') if isinstance(ref, dict) else getattr(ref, 'id', None)
        if ref_id and ref_id not in ids:
            ids.append(ref_id)
    return ids


def _pool_relations(pool) -> Dict[str, Any]:
    listener_ids = resource_ref_ids(pool, 'listener_id', 'listeners')
    return {
        'listener_id': listener_ids[0] if listener_ids else None,
        'listener_ids': listener_ids,
        'loadbalancer_ids': resource_ref_ids(pool, 'loadbalancer_id', 'loadbalancers'),
        'health_monitor_id': getattr(pool, 'health_monitor_id', None),
    }


def get_load_balancer_pools(listener_name_or_id: str = None) -> Dict[str, Any]:
    """
    Get load balancer pools, optionally filtered by listener.
    
    Args:
        listener_name_or_id: Optional listener name or ID to filter pools
    
    Returns:
        Dictionary containing pools information
    """
    try:
        conn = get_openstack_connection()
        
        if listener_name_or_id:
            # Find listener and get its pools
            listener = conn.load_balancer.find_listener(listener_name_or_id)
            if not listener:
                return {
                    'success': False,
                    'message': f'Listener not found: {listener_name_or_id}'
                }
            
            # Octavia rejects ?listener_id= on GET /pools; filter client-side.
            pools = [
                pool for pool in conn.load_balancer.pools()
                if listener.id in resource_ref_ids(pool, 'listener_id', 'listeners')
            ]
        else:
            # Get all pools
            pools = list(conn.load_balancer.pools())
        
        pool_details = []
        for pool in pools:
            # Get members for this pool
            members = list(conn.load_balancer.members(pool.id))
            member_summary = []
            
            for member in members:
                member_info = {
                    'id': member.id,
                    'name': getattr(member, 'name', ''),
                    'address': member.address,
                    'protocol_port': member.protocol_port,
                    'weight': getattr(member, 'weight', 1),
                    'admin_state_up': member.is_admin_state_up,
                    'operating_status': getattr(member, 'operating_status', 'Unknown')
                }
                member_summary.append(member_info)
            
            pool_info = {
                'id': pool.id,
                'name': pool.name,
                'description': pool.description,
                'protocol': pool.protocol,
                'lb_algorithm': pool.lb_algorithm,
                'admin_state_up': pool.is_admin_state_up,
                **_pool_relations(pool),
                **_pool_tls_info(pool),
                'members': member_summary,
                'member_count': len(member_summary),
                'created_at': getattr(pool, 'created_at', None),
                'updated_at': getattr(pool, 'updated_at', None)
            }
            pool_details.append(pool_info)
        
        return {
            'success': True,
            'pools': pool_details,
            'pool_count': len(pool_details),
            'filter': f'listener: {listener_name_or_id}' if listener_name_or_id else 'all pools'
        }
        
    except Exception as e:
        logger.error(f"Failed to get pools: {e}")
        return {
            'success': False,
            'message': f'Failed to get pools: {str(e)}',
            'error': str(e)
        }


def set_load_balancer_pool(action: str, pool_name_or_id: str = "", name: str = "", 
                          listener_name_or_id: str = "", protocol: str = "", 
                          lb_algorithm: str = "", description: str = "",
                          admin_state_up: Optional[bool] = None,
                          tls_enabled: Optional[bool] = None,
                          tls_container_ref: str = "",
                          ca_tls_container_ref: str = "",
                          crl_container_ref: str = "",
                          tls_versions: Optional[List[str]] = None,
                          tls_ciphers: str = "",
                          alpn_protocols: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Manage load balancer pool operations.

    Args:
        action: Operation to perform (create, delete, show, set)
        pool_name_or_id: Pool name or ID (required for delete/show/set)
        name: Name for new pool (required for create)
        listener_name_or_id: Listener name or ID (required for create)
        protocol: Pool protocol - HTTP, HTTPS, TCP, UDP (required for create)
        lb_algorithm: Load balancing algorithm (ROUND_ROBIN, LEAST_CONNECTIONS,
            SOURCE_IP); create defaults to ROUND_ROBIN, set leaves it unchanged
            when empty
        description: Description for the pool
        admin_state_up: Administrative state; create defaults to True, set
            leaves it unchanged when None
        tls_enabled .. alpn_protocols: Backend re-encryption settings (create/set);
            certificate references accept Barbican names, IDs or hrefs

    Returns:
        Dictionary with operation results
    """
    try:
        conn = get_openstack_connection()
        tls_attrs = _pool_tls_attrs(
            conn, tls_enabled, tls_container_ref, ca_tls_container_ref,
            crl_container_ref, tls_versions, tls_ciphers, alpn_protocols,
        ) if action in ('create', 'set') else {}

        if action == "create":
            if not name or not listener_name_or_id or not protocol:
                return {
                    'success': False,
                    'message': 'Pool name, listener, and protocol are required for create action'
                }
            
            # Find listener
            listener = None
            for lb_listener in conn.load_balancer.listeners():
                if lb_listener.name == listener_name_or_id or lb_listener.id == listener_name_or_id:
                    listener = lb_listener
                    break
            
            if not listener:
                return {
                    'success': False,
                    'message': f'Listener not found: {listener_name_or_id}'
                }
            
            # Create pool
            pool_attrs = {
                'name': name,
                'listener_id': listener.id,
                'protocol': protocol.upper(),
                'lb_algorithm': (lb_algorithm or 'ROUND_ROBIN').upper(),
                'admin_state_up': True if admin_state_up is None else admin_state_up
            }
            
            if description:
                pool_attrs['description'] = description
            pool_attrs.update(tls_attrs)

            if 'tls_container_ref' in pool_attrs:
                pool = _write_raw_pool(conn, 'post', '/lbaas/pools', pool_attrs)
            else:
                pool = conn.load_balancer.create_pool(**pool_attrs)

            return {
                'success': True,
                'message': f'Pool creation accepted: {pool.name}; check provisioning_status before use',
                'pool': {
                    'id': pool.id,
                    'name': pool.name,
                    'protocol': pool.protocol,
                    'lb_algorithm': pool.lb_algorithm,
                    'listener_id': pool.listener_id,
                    'admin_state_up': pool.is_admin_state_up,
                    'provisioning_status': pool.provisioning_status,
                    'operating_status': pool.operating_status,
                    **_pool_tls_info(pool),
                    **({'tls_container_ref': pool_attrs['tls_container_ref']}
                       if 'tls_container_ref' in pool_attrs else {}),
                }
            }
            
        elif action == "delete":
            if not pool_name_or_id:
                return {
                    'success': False,
                    'message': 'Pool name or ID is required for delete action'
                }
            
            # Find pool
            pool = None
            for lb_pool in conn.load_balancer.pools():
                if lb_pool.name == pool_name_or_id or lb_pool.id == pool_name_or_id:
                    pool = lb_pool
                    break
            
            if not pool:
                return {
                    'success': False,
                    'message': f'Pool not found: {pool_name_or_id}'
                }
            
            conn.load_balancer.delete_pool(pool)
            
            return {
                'success': True,
                'message': f'Pool deletion accepted: {pool.name}'
            }
            
        elif action == "show":
            if not pool_name_or_id:
                return {
                    'success': False,
                    'message': 'Pool name or ID is required for show action'
                }
            
            # Find pool
            pool = None
            for lb_pool in conn.load_balancer.pools():
                if lb_pool.name == pool_name_or_id or lb_pool.id == pool_name_or_id:
                    pool = lb_pool
                    break
            
            if not pool:
                return {
                    'success': False,
                    'message': f'Pool not found: {pool_name_or_id}'
                }
            
            # Get pool members
            members = []
            try:
                for member in conn.load_balancer.members(pool):
                    members.append({
                        'id': member.id,
                        'name': getattr(member, 'name', ''),
                        'address': member.address,
                        'protocol_port': member.protocol_port,
                        'weight': member.weight,
                        'admin_state_up': member.is_admin_state_up,
                        'operating_status': member.operating_status
                    })
            except Exception as e:
                logger.warning(f"Failed to get pool members: {e}")
            
            return {
                'success': True,
                'pool': {
                    'id': pool.id,
                    'name': pool.name,
                    'description': pool.description,
                    'protocol': pool.protocol,
                    'lb_algorithm': pool.lb_algorithm,
                    'admin_state_up': pool.is_admin_state_up,
                    'provisioning_status': pool.provisioning_status,
                    'operating_status': pool.operating_status,
                    **_pool_relations(pool),
                    **_with_client_cert(conn, pool, _pool_tls_info(pool)),
                    'members': members,
                    'member_count': len(members),
                    'created_at': getattr(pool, 'created_at', None),
                    'updated_at': getattr(pool, 'updated_at', None)
                }
            }
            
        elif action == "set":
            if not pool_name_or_id:
                return {
                    'success': False,
                    'message': 'Pool name or ID is required for set action'
                }
            
            # Find pool
            pool = None
            for lb_pool in conn.load_balancer.pools():
                if lb_pool.name == pool_name_or_id or lb_pool.id == pool_name_or_id:
                    pool = lb_pool
                    break
            
            if not pool:
                return {
                    'success': False,
                    'message': f'Pool not found: {pool_name_or_id}'
                }
            
            # Update pool attributes
            update_attrs = {}
            if name:
                update_attrs['name'] = name
            if description:
                update_attrs['description'] = description
            if lb_algorithm:
                update_attrs['lb_algorithm'] = lb_algorithm.upper()
            if admin_state_up is not None:
                update_attrs['admin_state_up'] = admin_state_up
            update_attrs.update(tls_attrs)
            if not update_attrs:
                return {
                    'success': False,
                    'message': 'No update parameters provided'
                }

            if 'tls_container_ref' in update_attrs:
                updated_pool = _write_raw_pool(
                    conn, 'put', f'/lbaas/pools/{pool.id}', update_attrs)
            else:
                updated_pool = conn.load_balancer.update_pool(pool, **update_attrs)

            return {
                'success': True,
                'message': f'Pool update accepted: {updated_pool.name}; check provisioning_status before use',
                'pool': {
                    'id': updated_pool.id,
                    'name': updated_pool.name,
                    'description': updated_pool.description,
                    'protocol': updated_pool.protocol,
                    'lb_algorithm': updated_pool.lb_algorithm,
                    'admin_state_up': updated_pool.is_admin_state_up,
                    'provisioning_status': updated_pool.provisioning_status,
                    'operating_status': updated_pool.operating_status,
                    **_pool_tls_info(updated_pool),
                    **({'tls_container_ref': update_attrs['tls_container_ref']}
                       if 'tls_container_ref' in update_attrs else {}),
                }
            }
        
        else:
            return {
                'success': False,
                'message': f'Invalid action: {action}. Supported actions: create, delete, show, set'
            }
            
    except Exception as e:
        from .listeners import _with_tls_hint
        logger.error(f"Failed to manage pool: {e}")
        return {
            'success': False,
            'message': _with_tls_hint(f'Failed to manage pool: {str(e)}'),
            'error': str(e)
        }


def get_load_balancer_pool_members(pool_name_or_id: str) -> Dict[str, Any]:
    """
    Get members for a specific load balancer pool.
    
    Args:
        pool_name_or_id: Pool name or ID
        
    Returns:
        Dictionary with pool members information
    """
    try:
        conn = get_openstack_connection()
        
        # Find pool
        pool = None
        for lb_pool in conn.load_balancer.pools():
            if lb_pool.name == pool_name_or_id or lb_pool.id == pool_name_or_id:
                pool = lb_pool
                break
        
        if not pool:
            return {
                'success': False,
                'message': f'Pool not found: {pool_name_or_id}'
            }
        
        # Get pool members
        member_details = []
        for member in conn.load_balancer.members(pool):
            member_info = {
                'id': member.id,
                'name': getattr(member, 'name', ''),
                'address': member.address,
                'protocol_port': member.protocol_port,
                'weight': member.weight,
                'admin_state_up': member.is_admin_state_up,
                'provisioning_status': member.provisioning_status,
                'operating_status': member.operating_status,
                'backup': getattr(member, 'backup', False),
                'monitor_address': getattr(member, 'monitor_address', None),
                'monitor_port': getattr(member, 'monitor_port', None),
                'created_at': getattr(member, 'created_at', None),
                'updated_at': getattr(member, 'updated_at', None)
            }
            member_details.append(member_info)
        
        return {
            'success': True,
            'pool': {
                'id': pool.id,
                'name': pool.name,
                'protocol': pool.protocol
            },
            'members': member_details,
            'member_count': len(member_details)
        }
        
    except Exception as e:
        logger.error(f"Failed to get pool members: {e}")
        return {
            'success': False,
            'message': f'Failed to get pool members: {str(e)}',
            'error': str(e)
        }


def set_load_balancer_pool_member(action: str, pool_name_or_id: str, member_id: str = "", 
                                 name: str = "", address: str = "", protocol_port: int = 0,
                                 weight: Optional[int] = None,
                                 admin_state_up: Optional[bool] = None,
                                 backup: Optional[bool] = None, monitor_address: str = "",
                                 monitor_port: int = 0) -> Dict[str, Any]:
    """
    Manage load balancer pool member operations.
    
    Args:
        action: Operation to perform (create, delete, show, set)
        pool_name_or_id: Pool name or ID (required)
        member_id: Member ID (required for delete/show/set)
        name: Name for the member
        address: IP address of the member (required for create)
        protocol_port: Port number (required for create)
        weight: Member weight (0-256; 0 stops new traffic); create default 1
        admin_state_up: Administrative state; create default True
        backup: Backup member flag; create default False

        set sends only the values given (None leaves a field unchanged).
        monitor_address: Monitor IP address
        monitor_port: Monitor port
        
    Returns:
        Dictionary with operation results
    """
    try:
        conn = get_openstack_connection()
        
        # Find pool
        pool = None
        for lb_pool in conn.load_balancer.pools():
            if lb_pool.name == pool_name_or_id or lb_pool.id == pool_name_or_id:
                pool = lb_pool
                break
        
        if not pool:
            return {
                'success': False,
                'message': f'Pool not found: {pool_name_or_id}'
            }
        
        if action == "create":
            if not address or protocol_port <= 0:
                return {
                    'success': False,
                    'message': 'Member address and protocol_port are required for create action'
                }
            
            # Create member
            member_attrs = {
                'address': address,
                'protocol_port': protocol_port,
                'weight': 1 if weight is None else weight,
                'admin_state_up': True if admin_state_up is None else admin_state_up,
                'backup': False if backup is None else backup
            }
            
            if name:
                member_attrs['name'] = name
            if monitor_address:
                member_attrs['monitor_address'] = monitor_address
            if monitor_port > 0:
                member_attrs['monitor_port'] = monitor_port
                
            member = conn.load_balancer.create_member(pool, **member_attrs)
            
            return {
                'success': True,
                'message': f'Pool member creation accepted; check provisioning_status before use',
                'member': {
                    'id': member.id,
                    'name': getattr(member, 'name', ''),
                    'address': member.address,
                    'protocol_port': member.protocol_port,
                    'weight': member.weight,
                    'admin_state_up': member.is_admin_state_up,
                    'provisioning_status': member.provisioning_status,
                    'operating_status': member.operating_status,
                    'pool_id': pool.id
                }
            }
            
        elif action == "delete":
            if not member_id:
                return {
                    'success': False,
                    'message': 'Member ID is required for delete action'
                }
            
            # Find member
            member = None
            try:
                member = conn.load_balancer.get_member(member_id, pool)
            except Exception as e:
                return {
                    'success': False,
                    'message': f'Member not found: {member_id}'
                }
            
            conn.load_balancer.delete_member(member, pool)
            
            return {
                'success': True,
                'message': f'Pool member deletion accepted: {member.address}:{member.protocol_port}'
            }
            
        elif action == "show":
            if not member_id:
                return {
                    'success': False,
                    'message': 'Member ID is required for show action'
                }
            
            # Find member
            try:
                member = conn.load_balancer.get_member(member_id, pool)
            except Exception as e:
                return {
                    'success': False,
                    'message': f'Member not found: {member_id}'
                }
            
            return {
                'success': True,
                'member': {
                    'id': member.id,
                    'name': getattr(member, 'name', ''),
                    'address': member.address,
                    'protocol_port': member.protocol_port,
                    'weight': member.weight,
                    'admin_state_up': member.is_admin_state_up,
                    'provisioning_status': member.provisioning_status,
                    'operating_status': member.operating_status,
                    'backup': getattr(member, 'backup', False),
                    'monitor_address': getattr(member, 'monitor_address', None),
                    'monitor_port': getattr(member, 'monitor_port', None),
                    'pool_id': pool.id,
                    'created_at': getattr(member, 'created_at', None),
                    'updated_at': getattr(member, 'updated_at', None)
                }
            }
            
        elif action == "set":
            if not member_id:
                return {
                    'success': False,
                    'message': 'Member ID is required for set action'
                }
            
            # Find member
            try:
                member = conn.load_balancer.get_member(member_id, pool)
            except Exception as e:
                return {
                    'success': False,
                    'message': f'Member not found: {member_id}'
                }
            
            # Update member attributes
            update_attrs = {}
            if name:
                update_attrs['name'] = name
            for key, value in (('weight', weight), ('admin_state_up', admin_state_up),
                               ('backup', backup)):
                if value is not None:
                    update_attrs[key] = value
            if monitor_address:
                update_attrs['monitor_address'] = monitor_address
            if monitor_port > 0:
                update_attrs['monitor_port'] = monitor_port

            if not update_attrs:
                return {
                    'success': False,
                    'message': 'No update parameters provided'
                }

            updated_member = conn.load_balancer.update_member(member, pool, **update_attrs)
            
            return {
                'success': True,
                'message': f'Pool member update accepted; check provisioning_status before use',
                'member': {
                    'id': updated_member.id,
                    'name': getattr(updated_member, 'name', ''),
                    'address': updated_member.address,
                    'protocol_port': updated_member.protocol_port,
                    'weight': updated_member.weight,
                    'admin_state_up': updated_member.is_admin_state_up,
                    'provisioning_status': updated_member.provisioning_status,
                    'operating_status': updated_member.operating_status
                }
            }
        
        else:
            return {
                'success': False,
                'message': f'Invalid action: {action}. Supported actions: create, delete, show, set'
            }
            
    except Exception as e:
        logger.error(f"Failed to manage pool member: {e}")
        return {
            'success': False,
            'message': f'Failed to manage pool member: {str(e)}',
            'error': str(e)
        }