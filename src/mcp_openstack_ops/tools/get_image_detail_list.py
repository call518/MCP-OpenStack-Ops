"""Tool implementation for get_image_detail_list."""

import json
from datetime import datetime
from ..functions import get_image_detail_list as _get_image_detail_list
from ..mcp_main import (
    logger,
    mcp,
)

@mcp.tool()
async def get_image_detail_list() -> str:
    """
    Get detailed list of all images with comprehensive metadata.
    
    Functions:
    - List all images available in the project
    - Show image status, size, and format information
    - Display image properties and metadata
    - Provide ownership and visibility details
    
    Use when user requests image listing, image information, or image metadata details.
    
    Returns:
        Comprehensive image list in JSON format with detailed metadata, properties, and status information.
    """
    try:
        logger.info("Fetching detailed image list")
        images = _get_image_detail_list()
        
        response = {
            "timestamp": datetime.now().isoformat(),
            "images": images,
            "count": len(images),
            "operation": "list_images_detailed"
        }
        
        return json.dumps(response, indent=2, ensure_ascii=False)
        
    except Exception as e:
        error_msg = f"Error: Failed to fetch detailed image list - {str(e)}"
        logger.error(error_msg)
        return error_msg
