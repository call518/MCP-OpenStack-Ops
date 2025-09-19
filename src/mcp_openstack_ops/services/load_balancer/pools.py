"""
Load Balancer Pool and Member Management Module

This module provides comprehensive load balancer pool and member management operations
including creating, updating, deleting, and querying pools and their members.
"""

import logging
from typing import Dict, Any
from ...connection import get_openstack_connection

logger = logging.getLogger(__name__)


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
            
            pools = list(conn.load_balancer.pools(listener_id=listener.id))
        else:
            # Get all pools
            pools = list(conn.load_balancer.pools())
        
        pool_details = []
        for pool in pools:
            # Get members for this pool
            members = list(conn.load_balancer.members(pool_id=pool.id))
            member_summary = []
            
            for member in members:
                member_info = {
                    'id': member.id,
                    'name': getattr(member, 'name', ''),
                    'address': member.address,
                    'protocol_port': member.protocol_port,
                    'weight': getattr(member, 'weight', 1),
                    'admin_state_up': member.admin_state_up,
                    'operating_status': getattr(member, 'operating_status', 'Unknown')
                }
                member_summary.append(member_info)
            
            pool_info = {
                'id': pool.id,
                'name': pool.name,
                'description': pool.description,
                'protocol': pool.protocol,
                'lb_algorithm': pool.lb_algorithm,
                'admin_state_up': pool.admin_state_up,
                'listener_id': getattr(pool, 'listener_id', None),
                'members': member_summary,
                'member_count': len(member_summary),
                'created_at': str(pool.created_at) if hasattr(pool, 'created_at') else 'N/A',
                'updated_at': str(pool.updated_at) if hasattr(pool, 'updated_at') else 'N/A'
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
                          lb_algorithm: str = "ROUND_ROBIN", description: str = "", 
                          admin_state_up: bool = True) -> Dict[str, Any]:
    """
    Manage load balancer pool operations.
    
    Args:
        action: Operation to perform (create, delete, show, set)
        pool_name_or_id: Pool name or ID (required for delete/show/set)
        name: Name for new pool (required for create)
        listener_name_or_id: Listener name or ID (required for create)
        protocol: Pool protocol - HTTP, HTTPS, TCP, UDP (required for create)
        lb_algorithm: Load balancing algorithm (ROUND_ROBIN, LEAST_CONNECTIONS, SOURCE_IP)
        description: Description for the pool
        admin_state_up: Administrative state
        
    Returns:
        Dictionary with operation results
    """
    try:
        conn = get_openstack_connection()
        
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
                'lb_algorithm': lb_algorithm.upper(),
                'admin_state_up': admin_state_up
            }
            
            if description:
                pool_attrs['description'] = description
                
            pool = conn.load_balancer.create_pool(**pool_attrs)
            
            return {
                'success': True,
                'message': f'Pool created successfully: {pool.name}',
                'pool': {
                    'id': pool.id,
                    'name': pool.name,
                    'protocol': pool.protocol,
                    'lb_algorithm': pool.lb_algorithm,
                    'listener_id': pool.listener_id,
                    'admin_state_up': pool.admin_state_up,
                    'provisioning_status': pool.provisioning_status,
                    'operating_status': pool.operating_status
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
                'message': f'Pool deleted successfully: {pool.name}'
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
                        'admin_state_up': member.admin_state_up,
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
                    'admin_state_up': pool.admin_state_up,
                    'provisioning_status': pool.provisioning_status,
                    'operating_status': pool.operating_status,
                    'listener_id': getattr(pool, 'listener_id', None),
                    'members': members,
                    'member_count': len(members),
                    'created_at': str(pool.created_at) if hasattr(pool, 'created_at') else 'N/A',
                    'updated_at': str(pool.updated_at) if hasattr(pool, 'updated_at') else 'N/A'
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
            update_attrs['admin_state_up'] = admin_state_up
            
            updated_pool = conn.load_balancer.update_pool(pool, **update_attrs)
            
            return {
                'success': True,
                'message': f'Pool updated successfully: {updated_pool.name}',
                'pool': {
                    'id': updated_pool.id,
                    'name': updated_pool.name,
                    'description': updated_pool.description,
                    'protocol': updated_pool.protocol,
                    'lb_algorithm': updated_pool.lb_algorithm,
                    'admin_state_up': updated_pool.admin_state_up,
                    'provisioning_status': updated_pool.provisioning_status,
                    'operating_status': updated_pool.operating_status
                }
            }
        
        else:
            return {
                'success': False,
                'message': f'Invalid action: {action}. Supported actions: create, delete, show, set'
            }
            
    except Exception as e:
        logger.error(f"Failed to manage pool: {e}")
        return {
            'success': False,
            'message': f'Failed to manage pool: {str(e)}',
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
                'admin_state_up': member.admin_state_up,
                'provisioning_status': member.provisioning_status,
                'operating_status': member.operating_status,
                'backup': getattr(member, 'backup', False),
                'monitor_address': getattr(member, 'monitor_address', None),
                'monitor_port': getattr(member, 'monitor_port', None),
                'created_at': str(member.created_at) if hasattr(member, 'created_at') else 'N/A',
                'updated_at': str(member.updated_at) if hasattr(member, 'updated_at') else 'N/A'
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
                                 weight: int = 1, admin_state_up: bool = True, 
                                 backup: bool = False, monitor_address: str = "",
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
        weight: Member weight (1-256)
        admin_state_up: Administrative state
        backup: Backup member flag
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
                'weight': weight,
                'admin_state_up': admin_state_up,
                'backup': backup
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
                'message': f'Pool member created successfully',
                'member': {
                    'id': member.id,
                    'name': getattr(member, 'name', ''),
                    'address': member.address,
                    'protocol_port': member.protocol_port,
                    'weight': member.weight,
                    'admin_state_up': member.admin_state_up,
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
                'message': f'Pool member deleted successfully: {member.address}:{member.protocol_port}'
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
                    'admin_state_up': member.admin_state_up,
                    'provisioning_status': member.provisioning_status,
                    'operating_status': member.operating_status,
                    'backup': getattr(member, 'backup', False),
                    'monitor_address': getattr(member, 'monitor_address', None),
                    'monitor_port': getattr(member, 'monitor_port', None),
                    'pool_id': pool.id,
                    'created_at': str(member.created_at) if hasattr(member, 'created_at') else 'N/A',
                    'updated_at': str(member.updated_at) if hasattr(member, 'updated_at') else 'N/A'
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
            if weight > 0:
                update_attrs['weight'] = weight
            update_attrs['admin_state_up'] = admin_state_up
            update_attrs['backup'] = backup
            if monitor_address:
                update_attrs['monitor_address'] = monitor_address
            if monitor_port > 0:
                update_attrs['monitor_port'] = monitor_port
            
            updated_member = conn.load_balancer.update_member(member, pool, **update_attrs)
            
            return {
                'success': True,
                'message': f'Pool member updated successfully',
                'member': {
                    'id': updated_member.id,
                    'name': getattr(updated_member, 'name', ''),
                    'address': updated_member.address,
                    'protocol_port': updated_member.protocol_port,
                    'weight': updated_member.weight,
                    'admin_state_up': updated_member.admin_state_up,
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