"""Tool implementation for get_instance."""

import json
from datetime import datetime
from ..functions import (
    get_instance_details as _get_instance_details,
    get_instances_by_status as _get_instances_by_status,
)
from ..mcp_main import (
    logger,
    mcp,
)
from ..services.compute import search_instances as _search_instances

@mcp.tool()
async def get_instance(
    names: str = "",
    ids: str = "",
    status: str = "",
    search_term: str = "",
    search_in: str = "name",
    all_instances: bool = False,
    detailed: bool = True,
    limit: int = 50,
    offset: int = 0,
    case_sensitive: bool = False
) -> str:
    """
    Unified instance query tool supporting all instance retrieval patterns.
    Consolidates functionality from get_instance_details, get_instance_by_name, get_instances_by_status, and search_instances.
    
    Functions:
    - Get specific instances by names or IDs
    - Filter instances by status (ACTIVE, SHUTOFF, ERROR, etc.)
    - Search instances across multiple fields (name, flavor, image, host, etc.)
    - List all instances with pagination
    - Support both summary and detailed information modes
    
    Use when user requests instance information, status checks, or instance searches.
    
    Args:
        names: Specific instance name(s) to retrieve (comma-separated: "vm1,vm2,vm3")
        ids: Specific instance ID(s) to retrieve (comma-separated)
        status: Filter by instance status (e.g., "ACTIVE", "SHUTOFF", "ERROR")
        search_term: Search term for partial matching across fields
        search_in: Fields to search in ("name", "status", "host", "flavor", "image", "availability_zone", "all")
        all_instances: If True, retrieve all instances (ignores other filters)
        detailed: If True, return detailed information; if False, return summary only
        limit: Maximum instances to return (default: 50, max: 200)
        offset: Number of instances to skip for pagination
        case_sensitive: Case-sensitive search (default: False)
        
    Returns:
        Instance information in JSON format with metadata and pagination info.
        
    Examples:
        get_instance(names="vm1,vm2")                    # Get specific instances
        get_instance(status="SHUTOFF")                   # Get all stopped instances
        get_instance(search_term="web", search_in="name") # Search by name
        get_instance(all_instances=True, detailed=False) # List all (summary)
    """
    try:
        # Determine query method
        has_direct_names = names and names.strip()
        has_direct_ids = ids and ids.strip()
        has_status_filter = status and status.strip()
        has_search = search_term and search_term.strip()
        
        result_data = None
        query_description = ""
        
        if all_instances:
            # Get all instances
            logger.info("Fetching all instances")
            result_data = _get_instance_details(
                instance_names=None,
                limit=limit,
                offset=offset,
                include_all=True
            )
            query_description = "All instances"
            
        elif has_direct_names:
            # Get specific instances by names
            logger.info(f"Fetching instances by names: {names}")
            names_list = [name.strip() for name in names.split(',') if name.strip()]
            result_data = _get_instance_details(
                instance_names=names_list,
                limit=limit,
                offset=offset,
                include_all=True
            )
            query_description = f"Instances by names: {names}"
            
        elif has_direct_ids:
            # Get specific instances by IDs
            logger.info(f"Fetching instances by IDs: {ids}")
            # For IDs, we need to use names parameter since the function doesn't support IDs directly
            ids_list = [id.strip() for id in ids.split(',') if id.strip()]
            result_data = _get_instance_details(
                instance_names=ids_list,  # Use IDs as names for now
                limit=limit,
                offset=offset,
                include_all=True
            )
            query_description = f"Instances by IDs: {ids}"
            
        elif has_status_filter:
            # Filter by status
            logger.info(f"Fetching instances with status: {status}")
            instances = _get_instances_by_status(status.upper())
            
            # Apply pagination
            total_count = len(instances)
            paginated_instances = instances[offset:offset + limit] if instances else []
            
            result_data = {
                "timestamp": datetime.now().isoformat(),
                "query_type": "status_filter",
                "status_filter": status.upper(),
                "total_instances": total_count,
                "instances_returned": len(paginated_instances),
                "limit": limit,
                "offset": offset,
                "instances": paginated_instances
            }
            query_description = f"Instances with status: {status}"
            
        elif has_search:
            # Search instances
            logger.info(f"Searching instances for '{search_term}' in '{search_in}'")
            result_data = _search_instances(
                search_term=search_term,
                search_fields=search_in.split(',') if search_in else ['name'],
                limit=limit,
                include_inactive=True
            )
            
            # Enhance result with metadata
            if isinstance(result_data, list):
                result_data = {
                    "timestamp": datetime.now().isoformat(),
                    "query_type": "search",
                    "search_term": search_term,
                    "search_in": search_in,
                    "case_sensitive": case_sensitive,
                    "total_instances": len(result_data),
                    "instances": result_data
                }
            elif isinstance(result_data, dict) and 'instances' not in result_data:
                result_data["query_type"] = "search"
                result_data["search_term"] = search_term
                result_data["search_in"] = search_in
                
            query_description = f"Search results for '{search_term}' in '{search_in}'"
            
        else:
            return "Error: Specify at least one query parameter (names, ids, status, search_term, or all_instances=True)"
        
        # Handle detailed vs summary mode
        if not detailed and isinstance(result_data, dict) and 'instances' in result_data:
            # Convert to summary mode
            summary_instances = []
            for instance in result_data['instances']:
                summary_instances.append({
                    'id': instance.get('id', ''),
                    'name': instance.get('name', ''),
                    'status': instance.get('status', ''),
                    'flavor': instance.get('flavor', ''),
                    'image': instance.get('image', '')
                })
            result_data['instances'] = summary_instances
            result_data['mode'] = 'summary'
        elif detailed and isinstance(result_data, dict):
            result_data['mode'] = 'detailed'
        
        # Add query metadata
        if isinstance(result_data, dict):
            result_data['query_description'] = query_description
            result_data['detailed'] = detailed
        
        return json.dumps(result_data, indent=2, ensure_ascii=False)
        
    except Exception as e:
        error_msg = f"Error: Failed to query instances - {str(e)}"
        logger.error(error_msg)
        return error_msg
