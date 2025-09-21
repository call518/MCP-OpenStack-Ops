"""
OpenStack Connection Management Module

This module handles OpenStack SDK connection establishment and caching.
Separated to avoid circular imports with service modules.

Added Project Isolation Security Features:
- Current project ID verification
- Resource project ownership validation 
- Cross-project access prevention
"""

import logging
import os
from typing import Optional, Any, Dict
from dotenv import load_dotenv
from openstack import connection

# Configure logging
logger = logging.getLogger(__name__)

# Global connection cache
_connection_cache: Optional[connection.Connection] = None


def get_openstack_connection():
    """
    Creates and caches OpenStack connection using proxy URLs for all services.
    Returns cached connection if available to improve performance.
    """
    global _connection_cache
    
    if _connection_cache is not None:
        try:
            # Test connection validity
            _connection_cache.identity.get_token()
            return _connection_cache
        except Exception as e:
            logger.warning(f"Cached connection invalid, creating new one: {e}")
            _connection_cache = None
    
    load_dotenv()
    
    # Check required environment variables
    required_vars = ["OS_PROJECT_NAME", "OS_USERNAME", "OS_PASSWORD", "OS_AUTH_HOST", "OS_AUTH_PORT"]
    missing_vars = [var for var in required_vars if not os.environ.get(var)]
    
    if missing_vars:
        error_msg = f"Missing required OpenStack environment variables: {missing_vars}"
        logger.error(error_msg)
        logger.error("Please ensure your .env file contains OpenStack authentication credentials")
        raise ValueError(error_msg)
    
    # Get OpenStack connection parameters
    os_auth_host = os.environ.get("OS_AUTH_HOST")
    os_auth_port = os.environ.get("OS_AUTH_PORT")
    
    # Get configurable service ports (with defaults)
    # Note: OS_AUTH_PORT is used for Identity service endpoint
    compute_port = os.environ.get("OS_COMPUTE_PORT", "8774") 
    network_port = os.environ.get("OS_NETWORK_PORT", "9696")
    volume_port = os.environ.get("OS_VOLUME_PORT", "8776")
    image_port = os.environ.get("OS_IMAGE_PORT", "9292")
    placement_port = os.environ.get("OS_PLACEMENT_PORT", "8780")
    heat_stack_port = os.environ.get("OS_HEAT_STACK_PORT", "8004")
    heat_stack_cfn_port = os.environ.get("OS_HEAT_STACK_CFN_PORT", "18888")
    
    try:
        logger.info(f"Creating OpenStack connection with proxy host: {os_auth_host}")
        _connection_cache = connection.Connection(
            auth_url=f"http://{os_auth_host}:{os_auth_port}",
            project_name=os.environ.get("OS_PROJECT_NAME"),
            username=os.environ.get("OS_USERNAME"),
            password=os.environ.get("OS_PASSWORD"),
            user_domain_name=os.environ.get("OS_USER_DOMAIN_NAME", "Default"),
            project_domain_name=os.environ.get("OS_PROJECT_DOMAIN_NAME", "Default"),
            region_name=os.environ.get("OS_REGION_NAME", "RegionOne"),
            identity_api_version=os.environ.get("OS_IDENTITY_API_VERSION", "3"),
            interface="internal",
            # Override all service endpoints to use proxy
            identity_endpoint=f"http://{os_auth_host}:{os_auth_port}",
            compute_endpoint=f"http://{os_auth_host}:{compute_port}/v2.1",
            network_endpoint=f"http://{os_auth_host}:{network_port}",
            volume_endpoint=f"http://{os_auth_host}:{volume_port}/v3",
            image_endpoint=f"http://{os_auth_host}:{image_port}",
            placement_endpoint=f"http://{os_auth_host}:{placement_port}",
            orchestration_endpoint=f"http://{os_auth_host}:{heat_stack_port}/v1",
            timeout=10
        )
        
        # Test the connection
        try:
            token = _connection_cache.identity.get_token()
            logger.info(f"OpenStack connection successful. Token acquired: {token[:20]}...")
        except Exception as test_e:
            logger.error(f"Connection test failed: {test_e}")
            raise
            
        return _connection_cache
    except Exception as e:
        logger.error(f"Failed to create OpenStack connection: {e}")
        logger.error("Please check your OpenStack credentials and network connectivity")
        raise


def reset_connection_cache():
    """
    Reset the connection cache. Useful for testing or when connection parameters change.
    """
    global _connection_cache
    _connection_cache = None
    logger.info("OpenStack connection cache reset")


# =============================================================================
# PROJECT ISOLATION SECURITY FUNCTIONS
# =============================================================================

def get_current_project_id() -> str:
    """
    Get the current project ID from the authenticated connection.
    
    Returns:
        str: Current project ID
        
    Raises:
        Exception: If unable to get project ID
    """
    try:
        conn = get_openstack_connection()
        # Get project ID from the token
        token = conn.identity.get_token()
        project_id = conn.auth.get('project_id') or conn.auth.get('tenant_id')
        
        if not project_id:
            # Fallback: get from project name
            project_name = os.environ.get("OS_PROJECT_NAME")
            if project_name:
                for project in conn.identity.projects():
                    if project.name == project_name:
                        project_id = project.id
                        break
        
        if not project_id:
            raise Exception("Unable to determine current project ID")
        
        logger.debug(f"Current project ID: {project_id}")
        return project_id
    except Exception as e:
        logger.error(f"Failed to get current project ID: {e}")
        raise


def validate_resource_ownership(resource: Any, resource_type: str = "resource") -> bool:
    """
    Validate that a resource belongs to the current project or is publicly available.
    
    Args:
        resource: OpenStack resource object
        resource_type: Type of resource for logging
        
    Returns:
        bool: True if resource belongs to current project or is public, False otherwise
    """
    try:
        current_project_id = get_current_project_id()
        
        # Special handling for public resources (like flavors, public images)
        # These resources should be accessible regardless of project ownership
        if hasattr(resource, 'is_public') and resource.is_public:
            logger.debug(f"Public {resource_type} {getattr(resource, 'id', 'unknown')} is accessible")
            return True
            
        # Special handling for flavors - they are typically public and don't have project_id
        if resource_type.lower() == "flavor":
            # Most flavors are public and accessible to all projects
            if not hasattr(resource, 'project_id') or not resource.project_id:
                logger.debug(f"Public {resource_type} {getattr(resource, 'id', 'unknown')} is accessible")
                return True
        
        # Special handling for images - include public, community, and shared images
        if resource_type.lower() == "image":
            visibility = getattr(resource, 'visibility', 'private')
            if visibility in ['public', 'community', 'shared']:
                logger.debug(f"{visibility.capitalize()} {resource_type} {getattr(resource, 'id', 'unknown')} is accessible")
                return True
        
        # Try different attribute names for project ID
        resource_project_id = getattr(resource, 'project_id', None) or \
                             getattr(resource, 'tenant_id', None) or \
                             getattr(resource, 'owner', None)
        
        if not resource_project_id:
            # If no project ID and not handled above, it's likely a system resource
            logger.debug(f"System {resource_type} {getattr(resource, 'id', 'unknown')} with no project_id - allowing access")
            return True
        
        is_owned = resource_project_id == current_project_id
        
        if not is_owned:
            logger.warning(f"Access denied: {resource_type} {getattr(resource, 'id', 'unknown')} "
                          f"belongs to project {resource_project_id}, not current project {current_project_id}")
        
        return is_owned
    
    except Exception as e:
        logger.error(f"Failed to validate resource ownership: {e}")
        return False


def find_resource_by_name_or_id(resources, name_or_id: str, resource_type: str = "resource") -> Optional[Any]:
    """
    Find a resource by name or ID, ensuring it belongs to the current project.
    
    Args:
        resources: Iterable of OpenStack resources
        name_or_id: Name or ID to search for
        resource_type: Type of resource for logging
        
    Returns:
        Resource object if found and owned by current project, None otherwise
    """
    try:
        current_project_id = get_current_project_id()
        found_resources = []
        
        # First pass: collect all matching resources
        for resource in resources:
            resource_name = getattr(resource, 'name', '')
            resource_id = getattr(resource, 'id', '')
            
            if resource_name == name_or_id or resource_id == name_or_id:
                found_resources.append(resource)
        
        if not found_resources:
            logger.debug(f"No {resource_type} found with name or ID: {name_or_id}")
            return None
        
        # Second pass: filter by project ownership
        owned_resources = []
        for resource in found_resources:
            if validate_resource_ownership(resource, resource_type):
                owned_resources.append(resource)
        
        if not owned_resources:
            logger.warning(f"Found {len(found_resources)} {resource_type}(s) with name/ID '{name_or_id}' "
                          f"but none belong to current project {current_project_id}")
            return None
        
        if len(owned_resources) > 1:
            logger.warning(f"Multiple {resource_type}s with name '{name_or_id}' found in current project. "
                          f"Using first one: {getattr(owned_resources[0], 'id', 'unknown')}")
        
        resource = owned_resources[0]
        logger.debug(f"Found {resource_type} {getattr(resource, 'id', 'unknown')} "
                    f"with name/ID '{name_or_id}' in current project")
        return resource
        
    except Exception as e:
        logger.error(f"Error finding {resource_type} by name/ID '{name_or_id}': {e}")
        return None


def get_project_scoped_resources(conn, service_attr: str, resource_type: str = "resource") -> list:
    """
    Get resources from a service, ensuring they belong to the current project.
    
    Args:
        conn: OpenStack connection
        service_attr: Service attribute name (e.g., 'compute', 'network')
        resource_type: Type of resource for logging
        
    Returns:
        List of resources belonging to current project
    """
    try:
        service = getattr(conn, service_attr)
        all_resources = list(service)
        
        project_resources = []
        for resource in all_resources:
            if validate_resource_ownership(resource, resource_type):
                project_resources.append(resource)
        
        logger.debug(f"Found {len(project_resources)}/{len(all_resources)} {resource_type}s "
                    f"belonging to current project")
        
        return project_resources
        
    except Exception as e:
        logger.error(f"Error getting project-scoped {resource_type}s: {e}")
        return []