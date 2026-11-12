"""Tool implementation for get_instance_details."""

from functools import partial

from anyio import to_thread

import json
from datetime import datetime
from ..functions import get_instance_details as _get_instance_details
from ..mcp_main import (
    logger,
    mcp,
)

@mcp.tool()
async def get_instance_details(
    instance_names: str = "", 
    instance_ids: str = "", 
    all_instances: bool = False,
    limit: int = 50,
    offset: int = 0,
    include_all: bool = False,
    all_projects: bool = False
) -> str:
    """
    Provides detailed information and status for OpenStack instances with pagination support.
    
    Functions:
    - Query basic instance information (name, ID, status, image, flavor) with efficient pagination
    - Collect network connection status and IP address information
    - Check CPU, memory, storage resource usage and allocation
    - Provide instance metadata, keypair, and security group settings
    - Support large-scale environments with configurable limits
    
    Use when user requests specific instance information, VM details, server analysis, or instance troubleshooting.
    
    Args:
        instance_names: Comma-separated list of instance names to query (optional)
        instance_ids: Comma-separated list of instance IDs to query (optional)
        all_instances: If True, returns all instances of the current project (default: False)
        limit: Maximum number of instances to return (default: 50, max: 200)
        offset: Number of instances to skip for pagination (default: 0)
        include_all: If True, ignore pagination limits (use with caution in large environments)
        all_projects: If True, include every project the credential's OpenStack
            policy allows (like 'openstack server list --all-projects'). Requires
            ALLOW_CROSS_PROJECT_READ=true on the server; a disabled or denied
            request is reported as an error, never as current-project results.
        
    Returns:
        Instance detailed information in JSON format with instance, network, resource data, and pagination info.
    """
    try:
        logger.info(f"Fetching instance details - names: {instance_names}, ids: {instance_ids}, all: {all_instances}, limit: {limit}, offset: {offset}")
        
        names_list = None
        ids_list = None
        
        if instance_names.strip():
            names_list = [name.strip() for name in instance_names.split(',') if name.strip()]
            
        if instance_ids.strip():
            ids_list = [id.strip() for id in instance_ids.split(',') if id.strip()]
        
        # Call the updated function with pagination parameters
        combined_names_ids = []
        if names_list:
            combined_names_ids.extend(names_list)
        if ids_list:
            combined_names_ids.extend(ids_list)
        
        if all_instances or (not names_list and not ids_list):
            details_result = await to_thread.run_sync(partial(_get_instance_details,
                instance_names=None,
                limit=limit, 
                offset=offset, 
                include_all=include_all,
                all_projects=all_projects
            ))
        else:
            details_result = await to_thread.run_sync(partial(_get_instance_details,
                instance_names=combined_names_ids,
                limit=limit, 
                offset=offset, 
                include_all=include_all,
                all_projects=all_projects
            ))
        
        # A failed lookup must not be reported as "0 instances found".
        if isinstance(details_result, dict) and details_result.get('success') is False:
            error_msg = ("Error: Failed to fetch instance details - "
                         f"{details_result.get('error') or details_result.get('message', 'unknown error')}")
            logger.error(error_msg)
            return error_msg

        # Handle both old return format (list) and new return format (dict)
        if isinstance(details_result, dict):
            instances = details_result.get('instances', [])
            pagination_info = details_result.get('pagination', {})
            performance_info = details_result.get('performance', {})
        else:
            # Backward compatibility with old list return format
            instances = details_result
            pagination_info = {}
            performance_info = {}
        
        result = {
            "timestamp": datetime.now().isoformat(),
            "filter_applied": {
                "instance_names": names_list,
                "instance_ids": ids_list,
                "all_instances": all_instances,
                "all_projects": all_projects
            },
            "pagination": {
                "limit": limit,
                "offset": offset,
                "include_all": include_all,
                **pagination_info
            },
            "instances_found": len(instances),
            "instance_details": instances,
            "performance": performance_info
        }
        if all_projects and isinstance(details_result, dict):
            result["scope"] = details_result.get("scope")
        
        return json.dumps(result, indent=2, ensure_ascii=False)
        
    except Exception as e:
        error_msg = f"Error: Failed to fetch instance details - {str(e)}"
        logger.error(error_msg)
        return error_msg
