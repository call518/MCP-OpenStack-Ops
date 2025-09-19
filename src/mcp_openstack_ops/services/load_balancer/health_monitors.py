"""
Load Balancer Health Monitor Management Module

This module provides comprehensive load balancer health monitor management operations
including creating, updating, deleting, and querying health monitors.
"""

import logging
from typing import Dict, Any
from ...connection import get_openstack_connection

logger = logging.getLogger(__name__)


def get_load_balancer_health_monitors(pool_name_or_id: str = "") -> Dict[str, Any]:
    """
    Get health monitors, optionally filtered by pool.
    
    Args:
        pool_name_or_id: Optional pool name or ID to filter monitors
        
    Returns:
        Dictionary with health monitor information
    """
    try:
        conn = get_openstack_connection()
        
        monitor_details = []
        
        # If pool is specified, find it first
        target_pool = None
        if pool_name_or_id:
            for lb_pool in conn.load_balancer.pools():
                if lb_pool.name == pool_name_or_id or lb_pool.id == pool_name_or_id:
                    target_pool = lb_pool
                    break
            
            if not target_pool:
                return {
                    'success': False,
                    'message': f'Pool not found: {pool_name_or_id}'
                }
        
        # Get health monitors
        for monitor in conn.load_balancer.health_monitors():
            # If pool filter is specified, only include monitors for that pool
            if target_pool and getattr(monitor, 'pool_id', None) != target_pool.id:
                continue
                
            monitor_info = {
                'id': monitor.id,
                'name': getattr(monitor, 'name', ''),
                'type': monitor.type,
                'delay': monitor.delay,
                'timeout': monitor.timeout,
                'max_retries': monitor.max_retries,
                'max_retries_down': getattr(monitor, 'max_retries_down', None),
                'admin_state_up': monitor.admin_state_up,
                'provisioning_status': monitor.provisioning_status,
                'operating_status': monitor.operating_status,
                'pool_id': getattr(monitor, 'pool_id', None),
                'http_method': getattr(monitor, 'http_method', None),
                'url_path': getattr(monitor, 'url_path', None),
                'expected_codes': getattr(monitor, 'expected_codes', None),
                'created_at': str(monitor.created_at) if hasattr(monitor, 'created_at') else 'N/A',
                'updated_at': str(monitor.updated_at) if hasattr(monitor, 'updated_at') else 'N/A'
            }
            monitor_details.append(monitor_info)
        
        return {
            'success': True,
            'health_monitors': monitor_details,
            'monitor_count': len(monitor_details),
            'filter': f'pool: {pool_name_or_id}' if pool_name_or_id else 'all monitors'
        }
        
    except Exception as e:
        logger.error(f"Failed to get health monitors: {e}")
        return {
            'success': False,
            'message': f'Failed to get health monitors: {str(e)}',
            'error': str(e)
        }


def set_load_balancer_health_monitor(action: str, monitor_name_or_id: str = "", name: str = "",
                                   pool_name_or_id: str = "", monitor_type: str = "HTTP",
                                   delay: int = 10, timeout: int = 5, max_retries: int = 3,
                                   max_retries_down: int = 3, admin_state_up: bool = True,
                                   http_method: str = "GET", url_path: str = "/",
                                   expected_codes: str = "200") -> Dict[str, Any]:
    """
    Manage load balancer health monitor operations.
    
    Args:
        action: Operation to perform (create, delete, show, set)
        monitor_name_or_id: Monitor name or ID (required for delete/show/set)
        name: Name for the monitor
        pool_name_or_id: Pool name or ID (required for create)
        monitor_type: Monitor type (HTTP, HTTPS, TCP, PING, UDP-CONNECT, SCTP)
        delay: Delay between health checks in seconds
        timeout: Timeout for health check in seconds
        max_retries: Maximum retries before marking unhealthy
        max_retries_down: Maximum retries before marking down
        admin_state_up: Administrative state
        http_method: HTTP method for HTTP/HTTPS monitors
        url_path: URL path for HTTP/HTTPS monitors
        expected_codes: Expected HTTP status codes
        
    Returns:
        Dictionary with operation results
    """
    try:
        conn = get_openstack_connection()
        
        if action == "create":
            if not pool_name_or_id:
                return {
                    'success': False,
                    'message': 'Pool name or ID is required for create action'
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
            
            # Create health monitor
            monitor_attrs = {
                'type': monitor_type.upper(),
                'delay': delay,
                'timeout': timeout,
                'max_retries': max_retries,
                'max_retries_down': max_retries_down,
                'admin_state_up': admin_state_up,
                'pool_id': pool.id
            }
            
            if name:
                monitor_attrs['name'] = name
            
            # HTTP/HTTPS specific attributes
            if monitor_type.upper() in ['HTTP', 'HTTPS']:
                monitor_attrs['http_method'] = http_method.upper()
                monitor_attrs['url_path'] = url_path
                monitor_attrs['expected_codes'] = expected_codes
                
            monitor = conn.load_balancer.create_health_monitor(**monitor_attrs)
            
            return {
                'success': True,
                'message': f'Health monitor created successfully',
                'health_monitor': {
                    'id': monitor.id,
                    'name': getattr(monitor, 'name', ''),
                    'type': monitor.type,
                    'delay': monitor.delay,
                    'timeout': monitor.timeout,
                    'max_retries': monitor.max_retries,
                    'pool_id': getattr(monitor, 'pool_id', None),
                    'provisioning_status': monitor.provisioning_status,
                    'operating_status': monitor.operating_status
                }
            }
            
        elif action == "delete":
            if not monitor_name_or_id:
                return {
                    'success': False,
                    'message': 'Monitor name or ID is required for delete action'
                }
            
            # Find monitor
            monitor = None
            for hm in conn.load_balancer.health_monitors():
                if (getattr(hm, 'name', '') == monitor_name_or_id or hm.id == monitor_name_or_id):
                    monitor = hm
                    break
            
            if not monitor:
                return {
                    'success': False,
                    'message': f'Health monitor not found: {monitor_name_or_id}'
                }
            
            conn.load_balancer.delete_health_monitor(monitor)
            
            return {
                'success': True,
                'message': f'Health monitor deleted successfully'
            }
            
        elif action == "show":
            if not monitor_name_or_id:
                return {
                    'success': False,
                    'message': 'Monitor name or ID is required for show action'
                }
            
            # Find monitor
            monitor = None
            for hm in conn.load_balancer.health_monitors():
                if (getattr(hm, 'name', '') == monitor_name_or_id or hm.id == monitor_name_or_id):
                    monitor = hm
                    break
            
            if not monitor:
                return {
                    'success': False,
                    'message': f'Health monitor not found: {monitor_name_or_id}'
                }
            
            return {
                'success': True,
                'health_monitor': {
                    'id': monitor.id,
                    'name': getattr(monitor, 'name', ''),
                    'type': monitor.type,
                    'delay': monitor.delay,
                    'timeout': monitor.timeout,
                    'max_retries': monitor.max_retries,
                    'max_retries_down': getattr(monitor, 'max_retries_down', None),
                    'admin_state_up': monitor.admin_state_up,
                    'provisioning_status': monitor.provisioning_status,
                    'operating_status': monitor.operating_status,
                    'pool_id': getattr(monitor, 'pool_id', None),
                    'http_method': getattr(monitor, 'http_method', None),
                    'url_path': getattr(monitor, 'url_path', None),
                    'expected_codes': getattr(monitor, 'expected_codes', None),
                    'created_at': str(monitor.created_at) if hasattr(monitor, 'created_at') else 'N/A',
                    'updated_at': str(monitor.updated_at) if hasattr(monitor, 'updated_at') else 'N/A'
                }
            }
            
        elif action == "set":
            if not monitor_name_or_id:
                return {
                    'success': False,
                    'message': 'Monitor name or ID is required for set action'
                }
            
            # Find monitor
            monitor = None
            for hm in conn.load_balancer.health_monitors():
                if (getattr(hm, 'name', '') == monitor_name_or_id or hm.id == monitor_name_or_id):
                    monitor = hm
                    break
            
            if not monitor:
                return {
                    'success': False,
                    'message': f'Health monitor not found: {monitor_name_or_id}'
                }
            
            # Update monitor attributes
            update_attrs = {}
            if name:
                update_attrs['name'] = name
            if delay > 0:
                update_attrs['delay'] = delay
            if timeout > 0:
                update_attrs['timeout'] = timeout
            if max_retries > 0:
                update_attrs['max_retries'] = max_retries
            if max_retries_down > 0:
                update_attrs['max_retries_down'] = max_retries_down
            update_attrs['admin_state_up'] = admin_state_up
            
            # HTTP/HTTPS specific attributes
            if monitor.type in ['HTTP', 'HTTPS']:
                if http_method:
                    update_attrs['http_method'] = http_method.upper()
                if url_path:
                    update_attrs['url_path'] = url_path
                if expected_codes:
                    update_attrs['expected_codes'] = expected_codes
            
            updated_monitor = conn.load_balancer.update_health_monitor(monitor, **update_attrs)
            
            return {
                'success': True,
                'message': f'Health monitor updated successfully',
                'health_monitor': {
                    'id': updated_monitor.id,
                    'name': getattr(updated_monitor, 'name', ''),
                    'type': updated_monitor.type,
                    'delay': updated_monitor.delay,
                    'timeout': updated_monitor.timeout,
                    'max_retries': updated_monitor.max_retries,
                    'admin_state_up': updated_monitor.admin_state_up,
                    'provisioning_status': updated_monitor.provisioning_status,
                    'operating_status': updated_monitor.operating_status
                }
            }
        
        else:
            return {
                'success': False,
                'message': f'Invalid action: {action}. Supported actions: create, delete, show, set'
            }
            
    except Exception as e:
        logger.error(f"Failed to manage health monitor: {e}")
        return {
            'success': False,
            'message': f'Failed to manage health monitor: {str(e)}',
            'error': str(e)
        }