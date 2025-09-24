"""Tool implementation for search_instances."""

import json
from datetime import datetime
from ..mcp_main import (
    logger,
    mcp,
)
from ..services.compute import search_instances as _search_instances

@mcp.tool()
async def search_instances(
    search_term: str, 
    search_in: str = "name",
    limit: int = 50,
    offset: int = 0,
    case_sensitive: bool = False
) -> str:
    """
    Search for OpenStack instances based on various criteria with efficient pagination.
    
    Functions:
    - Search instances by name, status, host, flavor, image, or availability zone
    - Support partial matching with configurable case sensitivity
    - Return detailed information for matching instances with pagination
    - Optimized for large-scale environments with intelligent filtering
    
    Args:
        search_term: Term to search for (supports partial matching)
        search_in: Field to search in ('name', 'status', 'host', 'flavor', 'image', 'availability_zone', 'all')
        limit: Maximum number of matching instances to return (default: 50, max: 200)
        offset: Number of matching instances to skip for pagination (default: 0)
        case_sensitive: If True, performs case-sensitive search (default: False)
        
    Returns:
        List of matching instances with detailed information and pagination metadata
    """
    try:
        logger.info(f"Searching instances for '{search_term}' in '{search_in}' with limit {limit}, offset {offset}")
        
        search_result = _search_instances(
            search_term=search_term, 
            search_fields=search_in.split(',') if search_in else ['name', 'id'],
            limit=limit,
            include_inactive=True  # 모든 인스턴스를 검색하기 위해
        )
        
        # Handle both old return format (list) and new return format (dict)
        if isinstance(search_result, list):
            instances = search_result
            search_info = {
                'search_term': search_term,
                'search_in': search_in,
                'case_sensitive': case_sensitive,
                'matches_found': len(instances)
            }
            pagination_info = {'limit': limit, 'offset': offset, 'has_more': False}
            performance_info = {}
        elif isinstance(search_result, dict):
            instances = search_result.get('instances', [])
            search_info = search_result.get('search_info', {})
            pagination_info = search_result.get('pagination', {})
            performance_info = search_result.get('performance', {})
        else:
            # Fallback for unexpected format
            instances = []
            search_info = {'search_term': search_term, 'matches_found': 0}
            pagination_info = {'limit': limit, 'offset': offset, 'has_more': False}
            performance_info = {}
        
        result = {
            "timestamp": datetime.now().isoformat(),
            "search_info": search_info,
            "pagination": pagination_info,
            "instances_found": len(instances),
            "matching_instances": instances,
            "performance": performance_info
        }
        
        return json.dumps(result, indent=2, ensure_ascii=False)
        
    except Exception as e:
        error_msg = f"Error: Failed to search instances - {str(e)}"
        logger.error(error_msg)
        return error_msg
        
    except Exception as e:
        error_msg = f"Error: Failed to search instances - {str(e)}"
        logger.error(error_msg)
        return error_msg
