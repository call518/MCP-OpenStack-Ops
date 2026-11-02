"""Tool implementation for get_keypair_list."""

from fastmcp.exceptions import ToolError

import json
from datetime import datetime
from ..functions import get_keypair_list as _get_keypair_list
from ..mcp_main import (
    logger,
    mcp,
)

@mcp.tool()
async def get_keypair_list() -> str:
    """
    Get list of SSH keypairs for the current user.
    
    Functions:
    - Query SSH keypairs and their fingerprints
    - Display keypair types and creation dates
    - Show public key information (truncated for security)
    - Provide keypair management information
    
    Use when user requests SSH key management, keypair information, or security key queries.
    
    Returns:
        List of SSH keypairs with detailed information in JSON format.
    """
    try:
        logger.info("Fetching keypair list")
        keypairs = _get_keypair_list()
        
        result = {
            "timestamp": datetime.now().isoformat(),
            "total_keypairs": len(keypairs),
            "keypairs": keypairs
        }
        
        return json.dumps(result, indent=2, ensure_ascii=False)
        
    except Exception as error:
        logger.error("get_keypair_list failed error_type=%s", type(error).__name__)
        raise ToolError("OpenStack query failed: get_keypair_list") from None
