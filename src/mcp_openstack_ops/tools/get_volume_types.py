"""Tool implementation for get_volume_types."""

import json
from datetime import datetime
from ..functions import get_volume_types as _get_volume_types
from ..mcp_main import (
    logger,
    mcp,
)

@mcp.tool()
async def get_volume_types() -> str:
    """
    Get list of volume types with their specifications.
    
    Functions:
    - Query volume types and their capabilities
    - Display extra specifications and backend configurations
    - Show public/private volume type settings
    - Provide storage backend information
    
    Use when user requests volume type information, storage backend queries, or volume creation planning.
    
    Returns:
        List of volume types with detailed specifications in JSON format.
    """
    try:
        logger.info("Fetching volume types")
        volume_types = _get_volume_types()
        
        result = {
            "timestamp": datetime.now().isoformat(),
            "total_volume_types": len(volume_types),
            "volume_types": volume_types
        }
        
        return json.dumps(result, indent=2, ensure_ascii=False)
        
    except Exception as e:
        error_msg = f"Error: Failed to fetch volume types - {str(e)}"
        logger.error(error_msg)
        return error_msg
