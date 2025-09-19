"""
Load Balancer Listener Management Module

This module provides comprehensive load balancer listener management operations
including creating, updating, deleting, and querying listeners.
"""

import logging
from typing import Dict, Any
from ...connection import get_openstack_connection

logger = logging.getLogger(__name__)


def get_load_balancer_listeners(lb_name_or_id: str) -> Dict[str, Any]:
    """
    Get listeners for a specific load balancer.
    
    Args:
        lb_name_or_id: Load balancer name or ID
    
    Returns:
        Dictionary containing listeners information
    """
    try:
        conn = get_openstack_connection()
        
        # Find load balancer
        lb = conn.load_balancer.find_load_balancer(lb_name_or_id)
        if not lb:
            return {
                'success': False,
                'message': f'Load balancer not found: {lb_name_or_id}'
            }
        
        # Get listeners
        listeners = list(conn.load_balancer.listeners(loadbalancer_id=lb.id))
        listener_details = []
        
        for listener in listeners:
            listener_info = {
                'id': listener.id,
                'name': listener.name,
                'description': listener.description,
                'protocol': listener.protocol,
                'protocol_port': listener.protocol_port,
                'admin_state_up': listener.admin_state_up,
                'loadbalancer_id': listener.loadbalancer_id,
                'default_pool_id': getattr(listener, 'default_pool_id', None),
                'created_at': str(listener.created_at) if hasattr(listener, 'created_at') else 'N/A',
                'updated_at': str(listener.updated_at) if hasattr(listener, 'updated_at') else 'N/A'
            }
            listener_details.append(listener_info)
        
        return {
            'success': True,
            'load_balancer': {
                'id': lb.id,
                'name': lb.name
            },
            'listeners': listener_details,
            'listener_count': len(listener_details)
        }
        
    except Exception as e:
        logger.error(f"Failed to get load balancer listeners: {e}")
        return {
            'success': False,
            'message': f'Failed to get load balancer listeners: {str(e)}',
            'error': str(e)
        }


def set_load_balancer_listener(action: str, **kwargs) -> Dict[str, Any]:
    """
    Comprehensive load balancer listener management operations.
    
    Args:
        action: Action to perform (create, delete, set, unset, show, stats)
        **kwargs: Additional parameters based on action
    
    Returns:
        Dictionary containing operation results
    """
    try:
        conn = get_openstack_connection()
        
        logger.info(f"Managing load balancer listener with action: {action}")
        
        if action == "create":
            name = kwargs.get('name')
            lb_name_or_id = kwargs.get('lb_name_or_id')
            protocol = kwargs.get('protocol')
            protocol_port = kwargs.get('protocol_port')
            
            if not all([name, lb_name_or_id, protocol, protocol_port]):
                return {
                    'success': False,
                    'message': 'name, lb_name_or_id, protocol, and protocol_port are required'
                }
            
            # Find load balancer
            lb = conn.load_balancer.find_load_balancer(lb_name_or_id)
            if not lb:
                return {
                    'success': False,
                    'message': f'Load balancer not found: {lb_name_or_id}'
                }
            
            listener_params = {
                'name': name,
                'loadbalancer_id': lb.id,
                'protocol': protocol.upper(),
                'protocol_port': int(protocol_port),
                'description': kwargs.get('description', ''),
                'admin_state_up': kwargs.get('admin_state_up', True),
                'connection_limit': kwargs.get('connection_limit'),
                'default_pool_id': kwargs.get('default_pool_id')
            }
            
            # Remove None values
            listener_params = {k: v for k, v in listener_params.items() if v is not None}
            
            listener = conn.load_balancer.create_listener(**listener_params)
            
            return {
                'success': True,
                'message': f'Listener created successfully: {listener.name}',
                'listener': {
                    'id': listener.id,
                    'name': listener.name,
                    'protocol': listener.protocol,
                    'protocol_port': listener.protocol_port,
                    'admin_state_up': listener.admin_state_up
                }
            }
        
        elif action == "delete":
            listener_name_or_id = kwargs.get('listener_name_or_id')
            if not listener_name_or_id:
                return {
                    'success': False,
                    'message': 'listener_name_or_id is required for deletion'
                }
            
            listener = conn.load_balancer.find_listener(listener_name_or_id)
            if not listener:
                return {
                    'success': False,
                    'message': f'Listener not found: {listener_name_or_id}'
                }
            
            conn.load_balancer.delete_listener(listener.id)
            return {
                'success': True,
                'message': f'Listener deleted successfully: {listener.name}'
            }
        
        elif action in ["set", "update"]:
            listener_name_or_id = kwargs.get('listener_name_or_id')
            if not listener_name_or_id:
                return {
                    'success': False,
                    'message': 'listener_name_or_id is required for update'
                }
            
            listener = conn.load_balancer.find_listener(listener_name_or_id)
            if not listener:
                return {
                    'success': False,
                    'message': f'Listener not found: {listener_name_or_id}'
                }
            
            update_params = {}
            for key in ['name', 'description', 'admin_state_up', 'connection_limit', 'default_pool_id']:
                if key in kwargs:
                    update_params[key] = kwargs[key]
            
            if not update_params:
                return {
                    'success': False,
                    'message': 'No update parameters provided'
                }
            
            updated_listener = conn.load_balancer.update_listener(listener.id, **update_params)
            return {
                'success': True,
                'message': f'Listener updated successfully: {updated_listener.name}',
                'listener': {
                    'id': updated_listener.id,
                    'name': updated_listener.name,
                    'description': updated_listener.description,
                    'admin_state_up': updated_listener.admin_state_up
                }
            }
        
        elif action == "unset":
            listener_name_or_id = kwargs.get('listener_name_or_id')
            if not listener_name_or_id:
                return {
                    'success': False,
                    'message': 'listener_name_or_id is required for unset'
                }
            
            listener = conn.load_balancer.find_listener(listener_name_or_id)
            if not listener:
                return {
                    'success': False,
                    'message': f'Listener not found: {listener_name_or_id}'
                }
            
            unset_params = {}
            # Unset operations: clear description, connection_limit, default_pool_id
            if kwargs.get('description'):
                unset_params['description'] = ''
            if kwargs.get('connection_limit'):
                unset_params['connection_limit'] = None
            if kwargs.get('default_pool_id'):
                unset_params['default_pool_id'] = None
            
            if unset_params:
                updated_listener = conn.load_balancer.update_listener(listener.id, **unset_params)
                return {
                    'success': True,
                    'message': f'Listener settings cleared: {updated_listener.name}'
                }
            else:
                return {
                    'success': False,
                    'message': 'No unset parameters specified'
                }
        
        elif action == "stats":
            listener_name_or_id = kwargs.get('listener_name_or_id')
            if not listener_name_or_id:
                return {
                    'success': False,
                    'message': 'listener_name_or_id is required for stats'
                }
            
            listener = conn.load_balancer.find_listener(listener_name_or_id)
            if not listener:
                return {
                    'success': False,
                    'message': f'Listener not found: {listener_name_or_id}'
                }
            
            # Get listener statistics
            try:
                stats = conn.load_balancer.get_listener_statistics(listener.id)
                return {
                    'success': True,
                    'listener_stats': {
                        'bytes_in': getattr(stats, 'bytes_in', 0),
                        'bytes_out': getattr(stats, 'bytes_out', 0),
                        'active_connections': getattr(stats, 'active_connections', 0),
                        'total_connections': getattr(stats, 'total_connections', 0),
                        'request_errors': getattr(stats, 'request_errors', 0)
                    }
                }
            except Exception as e:
                return {
                    'success': False,
                    'message': f'Failed to get listener statistics: {str(e)}'
                }
        
        elif action == "show":
            listener_name_or_id = kwargs.get('listener_name_or_id')
            if not listener_name_or_id:
                return {
                    'success': False,
                    'message': 'listener_name_or_id is required'
                }
            
            listener = conn.load_balancer.find_listener(listener_name_or_id)
            if not listener:
                return {
                    'success': False,
                    'message': f'Listener not found: {listener_name_or_id}'
                }
            
            return {
                'success': True,
                'listener': {
                    'id': listener.id,
                    'name': listener.name,
                    'description': listener.description,
                    'protocol': listener.protocol,
                    'protocol_port': listener.protocol_port,
                    'admin_state_up': listener.admin_state_up,
                    'loadbalancer_id': listener.loadbalancer_id,
                    'default_pool_id': getattr(listener, 'default_pool_id', None)
                }
            }
        
        else:
            return {
                'success': False,
                'message': f'Unknown action "{action}". Supported: create, delete, show'
            }
            
    except Exception as e:
        logger.error(f"Failed to manage listener: {e}")
        return {
            'success': False,
            'message': f'Failed to manage listener: {str(e)}',
            'error': str(e)
        }