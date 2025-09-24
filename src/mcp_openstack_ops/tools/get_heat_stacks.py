"""Tool implementation for get_heat_stacks."""

import json
from datetime import datetime
from ..functions import get_heat_stacks as _get_heat_stacks
from ..mcp_main import (
    logger,
    mcp,
)

@mcp.tool()
async def get_heat_stacks() -> str:
    """
    Get list of Heat orchestration stacks.
    
    Functions:
    - Query Heat stacks and their current status
    - Display stack creation and update timestamps
    - Show stack templates and resource information
    - Provide orchestration deployment information
    
    Use when user requests stack information, orchestration queries, or infrastructure-as-code status.
    
    Returns:
        List of Heat stacks with detailed information in JSON format.
    """
    try:
        logger.info("Fetching Heat stacks")
        stacks = _get_heat_stacks()
        
        result = {
            "timestamp": datetime.now().isoformat(),
            "total_stacks": len(stacks),
            "stacks": stacks
        }
        
        return json.dumps(result, indent=2, ensure_ascii=False)
        
    except Exception as e:
        error_msg = f"Error: Failed to fetch Heat stacks - {str(e)}"
        logger.error(error_msg)
        return error_msg
