"""
OpenStack Connection Management Module

This module handles OpenStack SDK connection establishment and caching.
Separated to avoid circular imports with service modules.
"""

import logging
import os
from typing import Optional
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