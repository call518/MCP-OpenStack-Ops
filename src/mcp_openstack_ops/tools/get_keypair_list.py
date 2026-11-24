"""Tool implementation for get_keypair_list."""

from fastmcp.exceptions import ToolError

import json
from datetime import datetime
from ..functions import get_keypair_list as _get_keypair_list
from ..services.identity import set_keypair as _keypair_query
from ..mcp_main import (
    logger,
    mcp,
)

@mcp.tool()
async def get_keypair_list(keypair_name: str = "") -> str:
    """
    Get list of SSH keypairs for the current user, or show one keypair.

    Functions:
    - Query SSH keypairs and their fingerprints
    - Display keypair types and user IDs
    - Show public key information (the list truncates it to 100 characters)
    - Provide keypair management information
    
    Use when user requests SSH key management, keypair information, or security key queries.

    Args:
        keypair_name: Optional keypair name. When provided, show that keypair
            with its full public key; otherwise list keypairs.

    Returns:
        List of SSH keypairs with detailed information in JSON format.
    """
    if keypair_name:
        return json.dumps(_keypair_query(keypair_name, 'show'), indent=2)
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
