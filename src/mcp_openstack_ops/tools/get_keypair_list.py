"""Tool implementation for get_keypair_list."""

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
        
    except Exception as e:
        error_msg = f"Error: Failed to fetch keypair list - {str(e)}"
        logger.error(error_msg)
        return error_msg
