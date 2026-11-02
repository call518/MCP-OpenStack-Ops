"""Tool implementation for get_user_list."""

from fastmcp.exceptions import ToolError

import json
from datetime import datetime
from ..functions import get_user_list as _get_user_list
from ..mcp_main import (
    logger,
    mcp,
)

@mcp.tool()
async def get_user_list() -> str:
    """
    Get list of OpenStack users in the current domain.
    
    Functions:
    - Query user accounts and their basic information
    - Display user status (enabled/disabled)
    - Show user email and domain information
    - Provide user creation and modification timestamps
    
    Use when user requests user management information, identity queries, or user administration tasks.
    
    Returns:
        List of users with detailed information in JSON format.
    """
    try:
        logger.info("Fetching user list")
        users = _get_user_list()
        
        result = {
            "timestamp": datetime.now().isoformat(),
            "total_users": len(users),
            "users": users
        }
        
        return json.dumps(result, indent=2, ensure_ascii=False)
        
    except Exception as error:
        logger.error("get_user_list failed error_type=%s", type(error).__name__)
        raise ToolError("OpenStack query failed: get_user_list") from None
