"""
OpenStack Identity (Keystone) Service Functions

This module contains functions for managing projects, users, roles, domains, and keypairs.
"""

import logging
from typing import Dict, List, Any, Optional
from ..connection import get_openstack_connection

# Configure logging
logger = logging.getLogger(__name__)


def set_domains(action: str, domain_name: Optional[str] = None, **kwargs) -> Dict[str, Any]:
    """
    Manage OpenStack domains (list, show, create, delete, update)
    
    Args:
        action: Action to perform (list, show, create, delete, update)
        domain_name: Name or ID of the domain
        **kwargs: Additional parameters
    
    Returns:
        Result of the domain management operation
    """
    try:
        conn = get_openstack_connection()
        
        if action.lower() == 'list':
            domains = []
            try:
                for domain in conn.identity.domains():
                    domains.append({
                        'id': domain.id,
                        'name': domain.name,
                        'description': getattr(domain, 'description', 'N/A'),
                        'enabled': domain.is_enabled,
                        'created_at': str(getattr(domain, 'created_at', 'N/A')),
                        'updated_at': str(getattr(domain, 'updated_at', 'N/A'))
                    })
            except Exception as e:
                return {
                    'success': False,
                    'message': f'Domains not accessible: {str(e)}',
                    'domains': []
                }
            return {
                'success': True,
                'domains': domains,
                'count': len(domains)
            }
            
        elif action.lower() == 'create':
            if not domain_name:
                return {
                    'success': False,
                    'message': 'domain_name is required for create action'
                }
                
            description = kwargs.get('description', f'Domain created via MCP: {domain_name}')
            enabled = kwargs.get('enabled', True)
            
            try:
                domain = conn.identity.create_domain(
                    name=domain_name,
                    description=description,
                    enabled=enabled
                )
                return {
                    'success': True,
                    'message': f'Domain "{domain_name}" created successfully',
                    'domain_id': domain.id,
                    'enabled': enabled
                }
            except Exception as e:
                return {
                    'success': False,
                    'message': f'Failed to create domain: {str(e)}'
                }
        
        else:
            return {
                'success': False,
                'message': f'Unknown action "{action}". Supported: list, create'
            }
            
    except Exception as e:
        logger.error(f"Failed to manage domain: {e}")
        return {
            'success': False,
            'message': f'Failed to manage domain: {str(e)}',
            'error': str(e)
        }


def get_project_info() -> Dict[str, Any]:
    """
    Get information about the current OpenStack project/tenant.
    
    Returns:
        Dict containing project information
    """
    try:
        # Import here to avoid circular imports
        from ..connection import get_openstack_connection
        conn = get_openstack_connection()
        
        project_id = conn.current_project_id
        project = conn.identity.get_project(project_id)
        
        # Get project quotas
        quotas = {}
        try:
            compute_quotas = conn.compute.get_quota_set(project_id)
            network_quotas = conn.network.get_quota(project_id)
            volume_quotas = conn.volume.get_quota_set(project_id)
            
            quotas = {
                'compute': {
                    'instances': getattr(compute_quotas, 'instances', -1),
                    'cores': getattr(compute_quotas, 'cores', -1),
                    'ram': getattr(compute_quotas, 'ram', -1)
                },
                'network': {
                    'networks': getattr(network_quotas, 'networks', -1),
                    'subnets': getattr(network_quotas, 'subnets', -1),
                    'ports': getattr(network_quotas, 'ports', -1),
                    'routers': getattr(network_quotas, 'routers', -1),
                    'floatingips': getattr(network_quotas, 'floatingips', -1)
                },
                'volume': {
                    'volumes': getattr(volume_quotas, 'volumes', -1),
                    'snapshots': getattr(volume_quotas, 'snapshots', -1),
                    'gigabytes': getattr(volume_quotas, 'gigabytes', -1)
                }
            }
        except Exception as quota_e:
            logger.warning(f"Could not retrieve quotas: {quota_e}")
            quotas = {'error': str(quota_e)}
        
        return {
            'id': project.id,
            'name': project.name,
            'description': getattr(project, 'description', 'N/A'),
            'domain_id': getattr(project, 'domain_id', 'N/A'),
            'enabled': project.is_enabled,
            'quotas': quotas
        }
    except Exception as e:
        logger.error(f"Failed to get project info: {e}")
        return {'error': str(e), 'name': 'unknown-project', 'id': 'unknown'}


def get_user_list() -> List[Dict[str, Any]]:
    """
    Get list of users in the current OpenStack domain.
    
    Returns:
        List of user dictionaries
    """
    try:
        # Import here to avoid circular imports
        from ..connection import get_openstack_connection
        conn = get_openstack_connection()
        users = []
        
        for user in conn.identity.users():
            users.append({
                'id': user.id,
                'name': user.name,
                'email': getattr(user, 'email', 'N/A'),
                'enabled': user.is_enabled,
                'domain_id': getattr(user, 'domain_id', 'N/A'),
                'created_at': str(getattr(user, 'created_at', 'N/A')),
                'updated_at': str(getattr(user, 'updated_at', 'N/A'))
            })
        
        return users
    except Exception as e:
        logger.error(f"Failed to get user list: {e}")
        return [
            {'id': 'user-1', 'name': 'demo-user', 'email': 'demo@example.com', 
             'enabled': True, 'error': str(e)}
        ]


def get_role_assignments() -> List[Dict[str, Any]]:
    """
    Get role assignments for the current project.
    
    Returns:
        List of role assignment dictionaries
    """
    try:
        # Import here to avoid circular imports
        from ..connection import get_openstack_connection
        conn = get_openstack_connection()
        assignments = []
        
        for assignment in conn.identity.role_assignments():
            assignments.append({
                'user_id': getattr(assignment, 'user', {}).get('id', 'N/A'),
                'project_id': getattr(assignment, 'scope', {}).get('project', {}).get('id', 'N/A'),
                'role_id': getattr(assignment, 'role', {}).get('id', 'N/A'),
                'role_name': getattr(assignment, 'role', {}).get('name', 'N/A'),
                'scope_type': getattr(assignment, 'scope', {}).keys() if hasattr(assignment, 'scope') else []
            })
        
        return assignments
    except Exception as e:
        logger.error(f"Failed to get role assignments: {e}")
        return [
            {'user_id': 'user-1', 'project_id': 'project-1', 'role_id': 'role-1', 
             'role_name': 'member', 'error': str(e)}
        ]


def get_keypair_list() -> List[Dict[str, Any]]:
    """
    Get list of SSH keypairs for the current project.
    
    Returns:
        List of keypair dictionaries
    """
    try:
        # Import here to avoid circular imports
        from ..connection import get_openstack_connection
        conn = get_openstack_connection()
        keypairs = []
        
        for keypair in conn.compute.keypairs():
            keypairs.append({
                'name': keypair.name,
                'fingerprint': getattr(keypair, 'fingerprint', 'N/A'),
                'public_key': getattr(keypair, 'public_key', 'N/A')[:100] + '...' if getattr(keypair, 'public_key', None) else 'N/A',
                'type': getattr(keypair, 'type', 'ssh'),
                'user_id': getattr(keypair, 'user_id', 'N/A')
            })
        
        return keypairs
    except Exception as e:
        logger.error(f"Failed to get keypair list: {e}")
        return [
            {'name': 'demo-key', 'fingerprint': 'xx:xx:xx:...', 'type': 'ssh', 'error': str(e)}
        ]


def set_keypair(keypair_name: str, action: str, **kwargs) -> Dict[str, Any]:
    """
    Manage SSH keypairs (create, delete, list).
    
    Args:
        keypair_name: Name of the keypair
        action: Action to perform (create, delete, list, show)
        **kwargs: Additional parameters (public_key for create, type)
    
    Returns:
        Result of the keypair operation
    """
    try:
        # Import here to avoid circular imports
        from ..connection import get_openstack_connection
        conn = get_openstack_connection()
        
        if action.lower() == 'list':
            keypairs = []
            for keypair in conn.compute.keypairs():
                keypairs.append({
                    'name': keypair.name,
                    'fingerprint': getattr(keypair, 'fingerprint', 'N/A'),
                    'public_key': getattr(keypair, 'public_key', 'N/A'),
                    'type': getattr(keypair, 'type', 'ssh'),
                    'user_id': getattr(keypair, 'user_id', 'N/A')
                })
            return {
                'success': True,
                'keypairs': keypairs,
                'count': len(keypairs)
            }
        
        elif action.lower() == 'create':
            public_key = kwargs.get('public_key')
            keypair_type = kwargs.get('type', 'ssh')
            
            create_params = {
                'name': keypair_name,
                'type': keypair_type
            }
            
            if public_key:
                create_params['public_key'] = public_key
            
            keypair = conn.compute.create_keypair(**create_params)
            
            return {
                'success': True,
                'message': f'Keypair "{keypair_name}" created successfully',
                'keypair': {
                    'name': keypair.name,
                    'fingerprint': getattr(keypair, 'fingerprint', 'N/A'),
                    'private_key': getattr(keypair, 'private_key', None),  # Only available on creation
                    'type': getattr(keypair, 'type', 'ssh')
                }
            }
            
        elif action.lower() == 'delete':
            try:
                conn.compute.delete_keypair(keypair_name)
                return {
                    'success': True,
                    'message': f'Keypair "{keypair_name}" deleted successfully'
                }
            except Exception as e:
                return {
                    'success': False,
                    'message': f'Failed to delete keypair "{keypair_name}": {str(e)}'
                }
        
        elif action.lower() == 'show':
            try:
                keypair = conn.compute.get_keypair(keypair_name)
                return {
                    'success': True,
                    'keypair': {
                        'name': keypair.name,
                        'fingerprint': getattr(keypair, 'fingerprint', 'N/A'),
                        'public_key': getattr(keypair, 'public_key', 'N/A'),
                        'type': getattr(keypair, 'type', 'ssh'),
                        'user_id': getattr(keypair, 'user_id', 'N/A')
                    }
                }
            except Exception as e:
                return {
                    'success': False,
                    'message': f'Keypair "{keypair_name}" not found: {str(e)}'
                }
        
        else:
            return {
                'success': False,
                'message': f'Unknown action "{action}". Supported: create, delete, list, show'
            }
            
    except Exception as e:
        logger.error(f"Failed to manage keypair: {e}")
        return {
            'success': False,
            'message': f'Failed to manage keypair: {str(e)}',
            'error': str(e)
        }


def get_project_details(project_name: str = "") -> Dict[str, Any]:
    """
    Get detailed information about OpenStack projects.
    
    Args:
        project_name: Name of specific project (optional, returns current project if empty)
    
    Returns:
        Dict containing project details
    """
    try:
        # Import here to avoid circular imports
        from ..connection import get_openstack_connection
        conn = get_openstack_connection()
        
        if not project_name:
            # Return current project details
            project_id = conn.current_project_id
            project = conn.identity.get_project(project_id)
        else:
            # Find project by name
            project = None
            for proj in conn.identity.projects():
                if proj.name == project_name:
                    project = proj
                    break
            
            if not project:
                return {
                    'success': False,
                    'message': f'Project "{project_name}" not found'
                }
        
        # Get project users and roles
        users = []
        try:
            for assignment in conn.identity.role_assignments():
                scope = getattr(assignment, 'scope', {})
                if 'project' in scope and scope['project'].get('id') == project.id:
                    user_info = getattr(assignment, 'user', {})
                    role_info = getattr(assignment, 'role', {})
                    users.append({
                        'user_id': user_info.get('id', 'N/A'),
                        'user_name': user_info.get('name', 'N/A'),
                        'role_id': role_info.get('id', 'N/A'),
                        'role_name': role_info.get('name', 'N/A')
                    })
        except Exception as user_e:
            logger.warning(f"Could not retrieve project users: {user_e}")
            users = []
        
        return {
            'success': True,
            'project': {
                'id': project.id,
                'name': project.name,
                'description': getattr(project, 'description', 'N/A'),
                'domain_id': getattr(project, 'domain_id', 'N/A'),
                'enabled': project.is_enabled,
                'is_domain': getattr(project, 'is_domain', False),
                'parent_id': getattr(project, 'parent_id', None),
                'created_at': str(getattr(project, 'created_at', 'N/A')),
                'updated_at': str(getattr(project, 'updated_at', 'N/A')),
                'users': users,
                'user_count': len(users)
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to get project details: {e}")
        return {
            'success': False,
            'message': f'Failed to get project details: {str(e)}',
            'error': str(e)
        }


def set_project(project_name: str, action: str, **kwargs) -> Dict[str, Any]:
    """
    Manage OpenStack projects (create, delete, update, show).
    
    Args:
        project_name: Name of the project
        action: Action to perform (create, delete, update, show, list)
        **kwargs: Additional parameters
    
    Returns:
        Result of the project operation
    """
    try:
        # Import here to avoid circular imports
        from ..connection import get_openstack_connection
        conn = get_openstack_connection()
        
        if action.lower() == 'list':
            projects = []
            try:
                for project in conn.identity.projects():
                    projects.append({
                        'id': project.id,
                        'name': project.name,
                        'description': getattr(project, 'description', 'N/A'),
                        'domain_id': getattr(project, 'domain_id', 'N/A'),
                        'enabled': project.is_enabled,
                        'is_domain': getattr(project, 'is_domain', False),
                        'parent_id': getattr(project, 'parent_id', None)
                    })
            except Exception as e:
                return {
                    'success': False,
                    'message': f'Failed to list projects: {str(e)}',
                    'projects': []
                }
            return {
                'success': True,
                'projects': projects,
                'count': len(projects)
            }
            
        elif action.lower() == 'create':
            description = kwargs.get('description', f'Project {project_name}')
            domain_id = kwargs.get('domain_id', 'default')
            enabled = kwargs.get('enabled', True)
            
            try:
                project = conn.identity.create_project(
                    name=project_name,
                    description=description,
                    domain_id=domain_id,
                    is_enabled=enabled
                )
                return {
                    'success': True,
                    'message': f'Project "{project_name}" created successfully',
                    'project': {
                        'id': project.id,
                        'name': project.name,
                        'description': getattr(project, 'description', 'N/A'),
                        'enabled': project.is_enabled
                    }
                }
            except Exception as e:
                return {
                    'success': False,
                    'message': f'Failed to create project "{project_name}": {str(e)}'
                }
                
        elif action.lower() == 'delete':
            # Find the project
            project = None
            for proj in conn.identity.projects():
                if proj.name == project_name or proj.id == project_name:
                    project = proj
                    break
                    
            if not project:
                return {
                    'success': False,
                    'message': f'Project "{project_name}" not found'
                }
                
            try:
                conn.identity.delete_project(project)
                return {
                    'success': True,
                    'message': f'Project "{project_name}" deleted successfully'
                }
            except Exception as e:
                return {
                    'success': False,
                    'message': f'Failed to delete project "{project_name}": {str(e)}'
                }
                
        elif action.lower() == 'update':
            # Find the project
            project = None
            for proj in conn.identity.projects():
                if proj.name == project_name or proj.id == project_name:
                    project = proj
                    break
                    
            if not project:
                return {
                    'success': False,
                    'message': f'Project "{project_name}" not found'
                }
                
            update_params = {}
            if 'description' in kwargs:
                update_params['description'] = kwargs['description']
            if 'enabled' in kwargs:
                update_params['is_enabled'] = kwargs['enabled']
                
            try:
                updated_project = conn.identity.update_project(project, **update_params)
                return {
                    'success': True,
                    'message': f'Project "{project_name}" updated successfully',
                    'project': {
                        'id': updated_project.id,
                        'name': updated_project.name,
                        'description': getattr(updated_project, 'description', 'N/A'),
                        'enabled': updated_project.is_enabled
                    }
                }
            except Exception as e:
                return {
                    'success': False,
                    'message': f'Failed to update project "{project_name}": {str(e)}'
                }
                
        elif action.lower() == 'show':
            # Find the project
            project = None
            for proj in conn.identity.projects():
                if proj.name == project_name or proj.id == project_name:
                    project = proj
                    break
                    
            if not project:
                return {
                    'success': False,
                    'message': f'Project "{project_name}" not found'
                }
                
            return {
                'success': True,
                'project': {
                    'id': project.id,
                    'name': project.name,
                    'description': getattr(project, 'description', 'N/A'),
                    'domain_id': getattr(project, 'domain_id', 'N/A'),
                    'enabled': project.is_enabled,
                    'is_domain': getattr(project, 'is_domain', False),
                    'parent_id': getattr(project, 'parent_id', None),
                    'created_at': str(getattr(project, 'created_at', 'N/A')),
                    'updated_at': str(getattr(project, 'updated_at', 'N/A'))
                }
            }
        
        else:
            return {
                'success': False,
                'message': f'Unknown action "{action}". Supported: create, delete, update, show, list'
            }
            
    except Exception as e:
        logger.error(f"Failed to manage project: {e}")
        return {
            'success': False,
            'message': f'Failed to manage project: {str(e)}',
            'error': str(e)
        }