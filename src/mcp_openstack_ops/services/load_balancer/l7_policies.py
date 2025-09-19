"""
Load Balancer L7 Policy and Rule Management Module

This module provides comprehensive L7 (Layer 7) policy and rule management operations
for load balancers, including creating, updating, deleting, and querying L7 policies and rules.
"""

import logging
from typing import Dict, Any
from ...connection import get_openstack_connection

logger = logging.getLogger(__name__)


def get_load_balancer_l7_policies(listener_name_or_id: str = "") -> Dict[str, Any]:
    """
    Get L7 policies for a listener or all policies.
    
    Args:
        listener_name_or_id: Optional listener name or ID to filter policies
    
    Returns:
        Dictionary containing L7 policies information
    """
    try:
        conn = get_openstack_connection()
        
        policies = []
        
        if listener_name_or_id:
            # Find specific listener
            listener = conn.load_balancer.find_listener(listener_name_or_id)
            if not listener:
                return {
                    'success': False,
                    'message': f'Listener not found: {listener_name_or_id}'
                }
            policies = list(conn.load_balancer.l7_policies(listener_id=listener.id))
        else:
            # Get all L7 policies
            policies = list(conn.load_balancer.l7_policies())
        
        policy_details = []
        for policy in policies:
            policy_info = {
                'id': policy.id,
                'name': policy.name or 'N/A',
                'description': policy.description or '',
                'listener_id': policy.listener_id,
                'action': policy.action,
                'position': policy.position,
                'redirect_pool_id': getattr(policy, 'redirect_pool_id', None),
                'redirect_url': getattr(policy, 'redirect_url', None),
                'admin_state_up': policy.admin_state_up,
                'provisioning_status': policy.provisioning_status,
                'operating_status': policy.operating_status
            }
            policy_details.append(policy_info)
        
        return {
            'success': True,
            'l7_policies': policy_details,
            'policy_count': len(policy_details)
        }
        
    except Exception as e:
        logger.error(f"Failed to get L7 policies: {e}")
        return {
            'success': False,
            'message': f'Failed to get L7 policies: {str(e)}',
            'error': str(e)
        }


def set_load_balancer_l7_policy(action: str, **kwargs) -> Dict[str, Any]:
    """
    Manage L7 policy operations.
    
    Args:
        action: Action (create, delete, set, unset, show)
        **kwargs: Parameters based on action
    
    Returns:
        Dictionary with operation results
    """
    try:
        conn = get_openstack_connection()
        
        if action == "create":
            listener_name_or_id = kwargs.get('listener_name_or_id')
            action_type = kwargs.get('action_type', 'REJECT')
            
            if not listener_name_or_id:
                return {
                    'success': False,
                    'message': 'listener_name_or_id is required for create'
                }
            
            listener = conn.load_balancer.find_listener(listener_name_or_id)
            if not listener:
                return {
                    'success': False,
                    'message': f'Listener not found: {listener_name_or_id}'
                }
            
            policy_params = {
                'listener_id': listener.id,
                'action': action_type,
                'name': kwargs.get('name'),
                'description': kwargs.get('description', ''),
                'position': kwargs.get('position', 1),
                'admin_state_up': kwargs.get('admin_state_up', True),
                'redirect_pool_id': kwargs.get('redirect_pool_id'),
                'redirect_url': kwargs.get('redirect_url')
            }
            
            # Remove None values
            policy_params = {k: v for k, v in policy_params.items() if v is not None}
            
            policy = conn.load_balancer.create_l7_policy(**policy_params)
            
            return {
                'success': True,
                'message': f'L7 policy created successfully',
                'l7_policy': {
                    'id': policy.id,
                    'name': policy.name,
                    'action': policy.action,
                    'position': policy.position
                }
            }
        
        elif action == "delete":
            policy_name_or_id = kwargs.get('policy_name_or_id')
            if not policy_name_or_id:
                return {
                    'success': False,
                    'message': 'policy_name_or_id is required for delete'
                }
            
            policy = conn.load_balancer.find_l7_policy(policy_name_or_id)
            if not policy:
                return {
                    'success': False,
                    'message': f'L7 policy not found: {policy_name_or_id}'
                }
            
            conn.load_balancer.delete_l7_policy(policy.id)
            return {
                'success': True,
                'message': 'L7 policy deleted successfully'
            }
        
        else:
            return {
                'success': False,
                'message': f'Unknown action "{action}". Supported: create, delete, set, unset, show'
            }
            
    except Exception as e:
        logger.error(f"Failed to manage L7 policy: {e}")
        return {
            'success': False,
            'message': f'Failed to manage L7 policy: {str(e)}',
            'error': str(e)
        }


def get_load_balancer_l7_rules(policy_name_or_id: str) -> Dict[str, Any]:
    """
    Get L7 rules for a specific L7 policy.
    
    Args:
        policy_name_or_id: L7 policy name or ID
    
    Returns:
        Dictionary containing L7 rules information
    """
    try:
        conn = get_openstack_connection()
        
        # Find L7 policy
        policy = conn.load_balancer.find_l7_policy(policy_name_or_id)
        if not policy:
            return {
                'success': False,
                'message': f'L7 policy not found: {policy_name_or_id}'
            }
        
        rules = list(conn.load_balancer.l7_rules(l7_policy=policy.id))
        
        rule_details = []
        for rule in rules:
            rule_info = {
                'id': rule.id,
                'l7policy_id': rule.l7policy_id,
                'type': rule.type,
                'compare_type': rule.compare_type,
                'key': getattr(rule, 'key', None),
                'value': rule.value,
                'invert': getattr(rule, 'invert', False),
                'admin_state_up': rule.admin_state_up,
                'provisioning_status': rule.provisioning_status,
                'operating_status': rule.operating_status
            }
            rule_details.append(rule_info)
        
        return {
            'success': True,
            'l7_policy': {
                'id': policy.id,
                'name': policy.name or 'N/A'
            },
            'l7_rules': rule_details,
            'rule_count': len(rule_details)
        }
        
    except Exception as e:
        logger.error(f"Failed to get L7 rules: {e}")
        return {
            'success': False,
            'message': f'Failed to get L7 rules: {str(e)}',
            'error': str(e)
        }


def set_load_balancer_l7_rule(action: str, **kwargs) -> Dict[str, Any]:
    """
    Manage L7 rule operations.
    
    Args:
        action: Action (create, delete, set, unset, show)
        **kwargs: Parameters based on action
    
    Returns:
        Dictionary with operation results
    """
    try:
        conn = get_openstack_connection()
        
        if action == "create":
            policy_name_or_id = kwargs.get('policy_name_or_id')
            rule_type = kwargs.get('type', 'PATH')
            compare_type = kwargs.get('compare_type', 'STARTS_WITH')
            value = kwargs.get('value')
            
            if not policy_name_or_id or not value:
                return {
                    'success': False,
                    'message': 'policy_name_or_id and value are required for create'
                }
            
            policy = conn.load_balancer.find_l7_policy(policy_name_or_id)
            if not policy:
                return {
                    'success': False,
                    'message': f'L7 policy not found: {policy_name_or_id}'
                }
            
            rule_params = {
                'l7policy_id': policy.id,
                'type': rule_type,
                'compare_type': compare_type,
                'value': value,
                'key': kwargs.get('key'),
                'invert': kwargs.get('invert', False),
                'admin_state_up': kwargs.get('admin_state_up', True)
            }
            
            # Remove None values
            rule_params = {k: v for k, v in rule_params.items() if v is not None}
            
            rule = conn.load_balancer.create_l7_rule(**rule_params)
            
            return {
                'success': True,
                'message': f'L7 rule created successfully',
                'l7_rule': {
                    'id': rule.id,
                    'type': rule.type,
                    'compare_type': rule.compare_type,
                    'value': rule.value
                }
            }
        
        elif action == "delete":
            rule_id = kwargs.get('rule_id')
            policy_name_or_id = kwargs.get('policy_name_or_id')
            
            if not rule_id or not policy_name_or_id:
                return {
                    'success': False,
                    'message': 'rule_id and policy_name_or_id are required for delete'
                }
            
            policy = conn.load_balancer.find_l7_policy(policy_name_or_id)
            if not policy:
                return {
                    'success': False,
                    'message': f'L7 policy not found: {policy_name_or_id}'
                }
            
            conn.load_balancer.delete_l7_rule(rule_id, l7_policy=policy.id)
            return {
                'success': True,
                'message': 'L7 rule deleted successfully'
            }
        
        else:
            return {
                'success': False,
                'message': f'Unknown action "{action}". Supported: create, delete'
            }
            
    except Exception as e:
        logger.error(f"Failed to manage L7 rule: {e}")
        return {
            'success': False,
            'message': f'Failed to manage L7 rule: {str(e)}',
            'error': str(e)
        }