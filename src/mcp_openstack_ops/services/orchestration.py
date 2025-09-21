"""
OpenStack Orchestration (Heat) Service Functions

This module contains functions for managing Heat stacks and orchestration operations.
"""

import logging
from typing import Dict, List, Any

# Configure logging
logger = logging.getLogger(__name__)


def get_heat_stacks() -> List[Dict[str, Any]]:
    """
    Get list of Heat stacks for current project.
    
    Returns:
        List of stack dictionaries for current project
    """
    try:
        # Import here to avoid circular imports
        from ..connection import get_openstack_connection
        conn = get_openstack_connection()
        
        # Check if Heat service is available
        try:
            # Test Heat service availability
            stacks_iterator = conn.orchestration.stacks()
            current_project_id = conn.current_project_id
            stacks = []
            
            for stack in stacks_iterator:
                # Filter stacks by current project
                stack_project_id = getattr(stack, 'project_id', None)
                if stack_project_id == current_project_id:
                    stacks.append({
                        'id': stack.id,
                        'name': stack.name,
                        'status': stack.status,
                        'stack_status': getattr(stack, 'stack_status', 'unknown'),
                        'stack_status_reason': getattr(stack, 'stack_status_reason', ''),
                        'creation_time': str(getattr(stack, 'creation_time', 'unknown')),
                        'updated_time': str(getattr(stack, 'updated_time', 'unknown')),
                        'description': getattr(stack, 'description', ''),
                        'tags': getattr(stack, 'tags', []),
                        'timeout_mins': getattr(stack, 'timeout_mins', None),
                        'owner': getattr(stack, 'stack_owner', 'unknown'),
                        'project_id': stack_project_id
                    })
            
            logger.info(f"Retrieved {len(stacks)} stacks for project {current_project_id}")
            return stacks
            
        except AttributeError as attr_error:
            if "catalog_url" in str(attr_error):
                logger.error(f"Heat service not available in service catalog: {attr_error}")
                return [{
                    'id': 'heat-service-unavailable',
                    'name': 'Heat Service Not Available',
                    'status': 'SERVICE_UNAVAILABLE',
                    'stack_status': 'SERVICE_UNAVAILABLE',
                    'description': 'Heat orchestration service is not available or not configured in service catalog',
                    'error': 'Heat service endpoint not found in service catalog',
                    'recommendation': 'Please ensure Heat service is installed and properly configured in OpenStack'
                }]
            else:
                raise
        
    except Exception as e:
        logger.error(f"Failed to get stacks: {e}")
        return [
            {
                'id': 'error-stack', 
                'name': 'Error retrieving stacks', 
                'status': 'ERROR',
                'stack_status': 'ERROR', 
                'description': 'Failed to retrieve Heat stacks', 
                'error': str(e)
            }
        ]


def set_heat_stack(stack_name: str, action: str, **kwargs) -> Dict[str, Any]:
    """
    Manage Heat stacks (create, delete, update).
    
    Args:
        stack_name: Name of the stack
        action: Action to perform (create, delete, update, abandon)
        **kwargs: Additional parameters (template, parameters)
    
    Returns:
        Result of the stack operation
    """
    try:
        # Import here to avoid circular imports
        from ..connection import get_openstack_connection
        conn = get_openstack_connection()
        
        if action.lower() == 'create':
            template = kwargs.get('template')
            if not template:
                return {
                    'success': False,
                    'message': 'template parameter is required for create action'
                }
                
            stack = conn.orchestration.create_stack(
                name=stack_name,
                template=template,
                parameters=kwargs.get('parameters', {}),
                timeout=kwargs.get('timeout', 60),
                tags=kwargs.get('tags', [])
            )
            return {
                'success': True,
                'message': f'Stack "{stack_name}" creation started',
                'stack': {
                    'id': stack.id,
                    'name': stack.name,
                    'status': stack.stack_status
                }
            }
            
        elif action.lower() == 'delete':
            # Find the stack using secure project-scoped lookup
            from ..connection import find_resource_by_name_or_id
            conn = get_openstack_connection()
            
            stack = find_resource_by_name_or_id(
                conn.orchestration.stacks(), 
                stack_name, 
                "Heat stack"
            )
                    
            if not stack:
                return {
                    'success': False,
                    'message': f'Heat stack "{stack_name}" not found or not accessible in current project'
                }
                
            conn.orchestration.delete_stack(stack)
            return {
                'success': True,
                'message': f'Heat stack "{stack_name}" deletion started',
                'stack_id': stack.id
            }
            
        elif action.lower() == 'update':
            # Find the stack using secure project-scoped lookup
            from ..connection import find_resource_by_name_or_id
            conn = get_openstack_connection()
            
            stack = find_resource_by_name_or_id(
                conn.orchestration.stacks(), 
                stack_name, 
                "Heat stack"
            )
                    
            if not stack:
                return {
                    'success': False,
                    'message': f'Heat stack "{stack_name}" not found or not accessible in current project'
                }
                
            template = kwargs.get('template')
            if not template:
                return {
                    'success': False,
                    'message': 'template parameter is required for update action'
                }
                
            updated_stack = conn.orchestration.update_stack(
                stack,
                template=template,
                parameters=kwargs.get('parameters', {})
            )
            return {
                'success': True,
                'message': f'Heat stack "{stack_name}" update started',
                'stack': {
                    'id': updated_stack.id,
                    'name': updated_stack.name,
                    'status': updated_stack.stack_status
                }
            }
        else:
            return {
                'success': False,
                'message': f'Unknown action "{action}". Supported: create, delete, update'
            }
            
    except Exception as e:
        logger.error(f"Failed to manage stack: {e}")
        return {
            'success': False,
            'message': f'Failed to manage stack: {str(e)}',
            'error': str(e)
        }