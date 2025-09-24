"""Tool implementation for get_role_assignments."""

import json
from datetime import datetime
from ..functions import get_role_assignments as _get_role_assignments
from ..mcp_main import (
    logger,
    mcp,
)

@mcp.tool()
async def get_role_assignments() -> str:
    """
    Get role assignments for the current project.
    
    Functions:
    - Query role assignments for users and groups
    - Display project-level and domain-level permissions
    - Show scope of role assignments
    - Provide comprehensive access control information
    
    Use when user requests permission information, access control queries, or security auditing.
    
    Returns:
        List of role assignments with detailed scope information in JSON format.
    """
    try:
        logger.info("Fetching role assignments")
        assignments = _get_role_assignments()
        
        result = {
            "timestamp": datetime.now().isoformat(),
            "total_assignments": len(assignments),
            "role_assignments": assignments
        }
        
        return json.dumps(result, indent=2, ensure_ascii=False)
        
    except Exception as e:
        error_msg = f"Error: Failed to fetch role assignments - {str(e)}"
        logger.error(error_msg)
        return error_msg
