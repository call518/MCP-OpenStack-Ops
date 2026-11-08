"""
OpenStack Orchestration (Heat) Service Functions

This module contains functions for managing Heat stacks and orchestration operations.
"""

import logging
from typing import Dict, List, Any
from urllib.parse import urlsplit

# Configure logging
logger = logging.getLogger(__name__)


def _heat_stack_is_owned(stack: Any, project_id: str) -> bool:
    """Use Heat's self link when its list response omits the project field."""
    if not project_id:
        return False
    explicit = getattr(stack, 'project_id', None)
    if explicit and explicit != project_id:
        return False
    link_projects = set()
    for link in getattr(stack, 'links', None) or []:
        if not isinstance(link, dict) or link.get('rel') != 'self':
            continue
        parts = urlsplit(link.get('href', '')).path.strip('/').split('/')
        for index, part in enumerate(parts):
            if part == 'stacks' and index >= 2 and parts[index - 2] == 'v1':
                link_projects.add(parts[index - 1])
    if link_projects:
        return link_projects == {project_id}
    return explicit == project_id


def _find_owned_heat_stack(conn: Any, name_or_id: str) -> Any:
    for stack in conn.orchestration.stacks():
        if (name_or_id in (getattr(stack, 'name', None), getattr(stack, 'id', None))
                and _heat_stack_is_owned(stack, conn.current_project_id)):
            return stack
    return None


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
            if not current_project_id:
                raise ValueError('A project-scoped connection is required')
            stacks = []
            
            for stack in stacks_iterator:
                if _heat_stack_is_owned(stack, current_project_id):
                    stacks.append({
                        'id': stack.id,
                        'name': stack.name,
                        'status': stack.status,
                        'stack_status': stack.status,
                        'stack_status_reason': getattr(stack, 'status_reason', ''),
                        'creation_time': str(getattr(stack, 'created_at', 'unknown')),
                        'updated_time': str(getattr(stack, 'updated_at', 'unknown')),
                        'description': getattr(stack, 'description', ''),
                        'tags': getattr(stack, 'tags', []),
                        'timeout_mins': getattr(stack, 'timeout_mins', None),
                        'owner': getattr(stack, 'owner_id', None) or 'unknown',
                        'project_id': current_project_id
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
        # Do not return a placeholder stack that is counted as a real one.
        raise


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
                tags=kwargs.get('tags', '')
            )
            return {
                'success': True,
                'message': f'Stack "{stack_name}" creation started',
                'stack': {
                    'id': stack.id,
                    'name': stack.name,
                    'status': stack.status
                }
            }
            
        elif action.lower() == 'delete':
            conn = get_openstack_connection()
            stack = _find_owned_heat_stack(conn, stack_name)
                    
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
            conn = get_openstack_connection()
            stack = _find_owned_heat_stack(conn, stack_name)
                    
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
                    'status': updated_stack.status
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

def get_heat_stack_details(stack_name: str, section: str = 'resources') -> Dict[str,
    Any]:
    """Read resources, events, the template or resolved outputs for a Heat stack."""
    from ..connection import get_openstack_connection

    try:
        if section not in {'resources', 'events', 'template', 'outputs'}:
            raise ValueError('Supported sections: resources, events, template, outputs')
        if not stack_name.strip():
            raise ValueError('stack_name is required')
        conn = get_openstack_connection()
        api = conn.orchestration
        stack = api.find_stack(stack_name, ignore_missing=False)
        if not _heat_stack_is_owned(stack, conn.current_project_id):
            raise ValueError('Heat stack is not accessible in the current project')
        if section == 'resources':
            data = [r.to_dict() for r in api.resources(stack)]
        elif section == 'events':
            data = [e.to_dict() for e in api.stack_events(stack)]
        elif section == 'template':
            # Return the original template document, including vendor/CFN keys.
            from urllib.parse import quote
            path = '/stacks/' + quote(stack.name, safe='') + '/' + quote(stack.id,
                safe='') + '/template'
            response = api.get(path)
            response.raise_for_status()
            data = response.json()
        else:
            data = api.get_stack(stack, resolve_outputs=True).outputs
        return {'success': True, 'stack_id': stack.id, section: data}
    except Exception as exc:
        return {'success': False, 'message': 'Heat stack query failed',
            'error': str(exc)}
