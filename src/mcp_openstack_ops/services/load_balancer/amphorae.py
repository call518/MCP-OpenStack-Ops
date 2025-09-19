"""
Load Balancer Amphora Management Module

This module provides amphora (load balancer instances) management operations
including getting amphora information, failover, configuration, and status.
"""

import logging
from typing import Dict, Any
from ...connection import get_openstack_connection

logger = logging.getLogger(__name__)


def get_load_balancer_amphorae(lb_name_or_id: str = "", **kwargs) -> Dict[str, Any]:
    """
    Get amphora instances for load balancer or all amphorae.
    Supports both legacy parameter style and **kwargs style for compatibility.
    
    Args:
        lb_name_or_id: Optional load balancer name or ID (legacy parameter)
        **kwargs: Optional arguments including:
            - loadbalancer_id: Load balancer ID to filter amphorae
    
    Returns:
        Dictionary containing amphora information
    """
    try:
        conn = get_openstack_connection()
        
        # Handle both parameter styles for compatibility
        loadbalancer_id = kwargs.get('loadbalancer_id') or lb_name_or_id
        
        amphorae = []
        
        if loadbalancer_id:
            # Find specific load balancer
            lb = conn.load_balancer.find_load_balancer(lb_name_or_id)
            if not lb:
                return {
                    'success': False,
                    'message': f'Load balancer not found: {lb_name_or_id}'
                }
            amphorae = list(conn.load_balancer.amphorae(loadbalancer_id=lb.id))
        else:
            # Get all amphorae
            amphorae = list(conn.load_balancer.amphorae())
        
        amphora_details = []
        for amphora in amphorae:
            amphora_info = {
                'id': amphora.id,
                'loadbalancer_id': getattr(amphora, 'loadbalancer_id', None),
                'compute_id': getattr(amphora, 'compute_id', None),
                'lb_network_ip': getattr(amphora, 'lb_network_ip', None),
                'vrrp_ip': getattr(amphora, 'vrrp_ip', None),
                'ha_ip': getattr(amphora, 'ha_ip', None),
                'vrrp_port_id': getattr(amphora, 'vrrp_port_id', None),
                'ha_port_id': getattr(amphora, 'ha_port_id', None),
                'cert_expiration': getattr(amphora, 'cert_expiration', None),
                'cert_busy': getattr(amphora, 'cert_busy', False),
                'role': getattr(amphora, 'role', None),
                'status': getattr(amphora, 'status', None),
                'cached_zone': getattr(amphora, 'cached_zone', None),
                'image_id': getattr(amphora, 'image_id', None),
                'compute_flavor': getattr(amphora, 'compute_flavor', None),
                'created_at': str(amphora.created_at) if hasattr(amphora, 'created_at') else 'N/A',
                'updated_at': str(amphora.updated_at) if hasattr(amphora, 'updated_at') else 'N/A'
            }
            amphora_details.append(amphora_info)
        
        return {
            'success': True,
            'amphorae': amphora_details,
            'amphora_count': len(amphora_details)
        }
        
    except Exception as e:
        logger.error(f"Failed to get amphorae: {e}")
        return {
            'success': False,
            'message': f'Failed to get amphorae: {str(e)}',
            'error': str(e)
        }


def set_load_balancer_amphora(action: str, **kwargs) -> Dict[str, Any]:
    """
    Manage amphora operations (configure, failover, show).
    NOTE: delete and stats operations are not supported by OpenStack SDK.
    
    Args:
        action: Action (configure, failover, show)
        **kwargs: Parameters based on action
    
    Returns:
        Dictionary with operation results
    """
    try:
        conn = get_openstack_connection()
        
        if action == "failover":
            amphora_id = kwargs.get('amphora_id')
            if not amphora_id:
                return {
                    'success': False,
                    'message': 'amphora_id is required for failover'
                }
            
            amphora = conn.load_balancer.get_amphora(amphora_id)
            if not amphora:
                return {
                    'success': False,
                    'message': f'Amphora not found: {amphora_id}'
                }
            
            conn.load_balancer.failover_amphora(amphora_id)
            return {
                'success': True,
                'message': f'Amphora failover initiated: {amphora_id}'
            }
        
        elif action == "configure":
            amphora_id = kwargs.get('amphora_id')
            if not amphora_id:
                return {
                    'success': False,
                    'message': 'amphora_id is required for configure'
                }
            
            conn.load_balancer.configure_amphora(amphora_id)
            return {
                'success': True,
                'message': f'Amphora configuration updated: {amphora_id}'
            }
        
        elif action == "show":
            amphora_id = kwargs.get('amphora_id')
            if not amphora_id:
                return {
                    'success': False,
                    'message': 'amphora_id is required for show'
                }
            
            amphora = conn.load_balancer.get_amphora(amphora_id)
            if not amphora:
                return {
                    'success': False,
                    'message': f'Amphora not found: {amphora_id}'
                }
            
            amphora_info = {
                'id': amphora.id,
                'loadbalancer_id': getattr(amphora, 'loadbalancer_id', None),
                'compute_id': getattr(amphora, 'compute_id', None),
                'lb_network_ip': getattr(amphora, 'lb_network_ip', None),
                'vrrp_ip': getattr(amphora, 'vrrp_ip', None),
                'ha_ip': getattr(amphora, 'ha_ip', None),
                'vrrp_port_id': getattr(amphora, 'vrrp_port_id', None),
                'ha_port_id': getattr(amphora, 'ha_port_id', None),
                'cert_expiration': getattr(amphora, 'cert_expiration', None),
                'cert_busy': getattr(amphora, 'cert_busy', False),
                'role': getattr(amphora, 'role', None),
                'status': getattr(amphora, 'status', None),
                'cached_zone': getattr(amphora, 'cached_zone', None),
                'image_id': getattr(amphora, 'image_id', None),
                'compute_flavor': getattr(amphora, 'compute_flavor', None),
                'created_at': str(amphora.created_at) if hasattr(amphora, 'created_at') else 'N/A',
                'updated_at': str(amphora.updated_at) if hasattr(amphora, 'updated_at') else 'N/A'
            }
            
            return {
                'success': True,
                'amphora': amphora_info
            }
        
        elif action in ["delete", "stats"]:
            return {
                'success': False,
                'message': f'Action "{action}" is not supported by OpenStack SDK. Available: configure, failover, show'
            }
        
        else:
            return {
                'success': False,
                'message': f'Unknown action "{action}". Supported: configure, failover, show (delete and stats not supported by OpenStack SDK)'
            }
            
    except Exception as e:
        logger.error(f"Failed to manage amphora: {e}")
        return {
            'success': False,
            'message': f'Failed to manage amphora: {str(e)}',
            'error': str(e)
        }


def _set_load_balancer_amphora(action: str, **kwargs):
    """
    Manage amphora operations (configure, failover, show).
    
    Args:
        action: Action to perform (configure, failover, show)
        **kwargs: Additional arguments including:
            - amphora_id: Amphora ID (required)
    """
    try:
        conn = get_openstack_connection()
        
        amphora_id = kwargs.get('amphora_id')
        if not amphora_id:
            raise ValueError("amphora_id parameter is required")
        
        if action == "configure":
            # Configure amphora
            result = conn.load_balancer.configure_amphora(amphora_id)
            return {
                "success": True,
                "action": "configure",
                "amphora_id": amphora_id,
                "result": "Amphora configuration initiated"
            }
        
        elif action == "failover":
            # Failover amphora
            result = conn.load_balancer.failover_amphora(amphora_id)
            return {
                "success": True,
                "action": "failover",
                "amphora_id": amphora_id,
                "result": "Amphora failover initiated"
            }
        
        elif action == "show":
            # Show amphora details
            amphora = conn.load_balancer.get_amphora(amphora_id)
            return {
                "success": True,
                "action": "show",
                "amphora": {
                    "id": amphora.id,
                    "compute_id": getattr(amphora, 'compute_id', None),
                    "load_balancer_id": getattr(amphora, 'load_balancer_id', None),
                    "status": getattr(amphora, 'status', None),
                    "role": getattr(amphora, 'role', None),
                    "lb_network_ip": getattr(amphora, 'lb_network_ip', None),
                    "vrrp_ip": getattr(amphora, 'vrrp_ip', None),
                    "ha_ip": getattr(amphora, 'ha_ip', None),
                    "vrrp_port_id": getattr(amphora, 'vrrp_port_id', None),
                    "ha_port_id": getattr(amphora, 'ha_port_id', None),
                    "cached_zone": getattr(amphora, 'cached_zone', None),
                    "image_id": getattr(amphora, 'image_id', None),
                    "compute_flavor": getattr(amphora, 'compute_flavor', None),
                    "created_at": getattr(amphora, 'created_at', None),
                    "updated_at": getattr(amphora, 'updated_at', None)
                }
            }
        
        else:
            return {
                "success": False,
                "error": f"Unknown action: {action}. Available actions: configure, failover, show"
            }
        
    except Exception as e:
        logger.error(f"Error managing amphora {amphora_id}: {e}")
        return {
            "success": False,
            "error": str(e),
            "amphora_id": kwargs.get('amphora_id')
        }