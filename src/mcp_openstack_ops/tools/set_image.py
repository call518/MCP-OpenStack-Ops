"""Tool implementation for set_image."""

import json
from datetime import datetime
from ..functions import set_image as _set_image
from ..mcp_main import (
    _get_resource_status_by_name,
    conditional_tool,
    handle_operation_result,
    logger,
)

@conditional_tool
async def set_image(image_names: str, action: str, container_format: str = "bare", disk_format: str = "qcow2", 
                   visibility: str = "private", min_disk: int = 0, min_ram: int = 0, properties: str = "{}") -> str:
    """
    Manage images (create, delete, update, list).
    Supports both single image and bulk operations.
    
    Functions:
    - Create new images with specified formats and properties
    - Delete existing images
    - Update image metadata and visibility settings
    - List all available images in the project
    - Handle image lifecycle management
    - Bulk operations: Apply action to multiple images at once
    
    Use when user requests image management, custom image creation, image listing, or image metadata updates.
    
    Args:
        image_names: Name(s) of images to manage. Support formats:
                    - Single: "image1" 
                    - Multiple: "image1,image2,image3" or "image1, image2, image3"
                    - List format: '["image1", "image2", "image3"]'
        action: Action to perform (create, delete, update, list)
        container_format: Container format (bare, ovf, etc.)
        disk_format: Disk format (qcow2, raw, vmdk, etc.)
        visibility: Image visibility (private, public, shared, community)
        min_disk: Minimum disk space required in GB (for create action)
        min_ram: Minimum RAM required in MB (for create action)
        properties: Additional image properties as JSON string (for create action)
        
    Returns:
        Result of image management operation in JSON format.
        For bulk operations, returns summary of successes and failures.
    """
    
    try:
        # For list action, allow empty image_names
        if action.lower() == 'list':
            logger.info(f"Managing image with action '{action}'")
            
            kwargs = {
                'container_format': container_format,
                'disk_format': disk_format,
                'visibility': visibility,
                'min_disk': min_disk,
                'min_ram': min_ram
            }
            
            # Parse properties JSON if provided
            if properties.strip():
                try:
                    kwargs['properties'] = json.loads(properties)
                except json.JSONDecodeError:
                    return json.dumps({
                        "timestamp": datetime.now().isoformat(),
                        "error": "Invalid JSON format for properties",
                        "message": "Properties must be valid JSON format"
                    })
            
            result_data = _set_image("", action, **kwargs)
            return handle_operation_result(
                result_data,
                "Image Management",
                {
                    "Action": action,
                    "Image Name": "all",
                    "Container Format": container_format,
                    "Disk Format": disk_format,
                    "Visibility": visibility
                }
            )
        
        # Parse image names for non-list actions
        if not image_names or not image_names.strip():
            return "Error: Image name(s) are required for this action"
            
        names_str = image_names.strip()
        
        # Handle JSON list format: ["name1", "name2"]
        if names_str.startswith('[') and names_str.endswith(']'):
            try:
                import json
                name_list = json.loads(names_str)
                if not isinstance(name_list, list):
                    return "Error: Invalid JSON list format for image names"
            except json.JSONDecodeError:
                return "Error: Invalid JSON format for image names"
        else:
            # Handle comma-separated format: "name1,name2" or "name1, name2"
            name_list = [name.strip() for name in names_str.split(',')]
        
        # Remove empty strings
        name_list = [name for name in name_list if name]
        
        if not name_list:
            return "Error: No valid image names provided"
        
        kwargs = {
            'container_format': container_format,
            'disk_format': disk_format,
            'visibility': visibility,
            'min_disk': min_disk,
            'min_ram': min_ram
        }
        
        # Parse properties JSON if provided
        if properties.strip():
            try:
                kwargs['properties'] = json.loads(properties)
            except json.JSONDecodeError:
                return json.dumps({
                    "timestamp": datetime.now().isoformat(),
                    "error": "Invalid JSON format for properties",
                    "message": "Properties must be valid JSON format"
                })
        
        # Handle single image (backward compatibility)
        if len(name_list) == 1:
            logger.info(f"Managing image '{name_list[0]}' with action '{action}'")
            result_data = _set_image(name_list[0].strip(), action, **kwargs)
            
            return handle_operation_result(
                result_data,
                "Image Management",
                {
                    "Action": action,
                    "Image Name": name_list[0],
                    "Container Format": container_format,
                    "Disk Format": disk_format,
                    "Visibility": visibility
                }
            )
        
        # Handle bulk operations (multiple images)
        else:
            logger.info(f"Managing {len(name_list)} images with action '{action}': {name_list}")
            results = []
            successes = []
            failures = []
            
            for image_name in name_list:
                try:
                    result = _set_image(image_name.strip(), action, **kwargs)
                    
                    # Check if result indicates success or failure
                    if isinstance(result, dict):
                        if result.get('success', False):
                            successes.append(image_name)
                            results.append(f"✓ {image_name}: {result.get('message', 'Success')}")
                        else:
                            failures.append(image_name)
                            results.append(f"✗ {image_name}: {result.get('error', 'Unknown error')}")
                    elif isinstance(result, str):
                        # For string results, check if it contains error indicators
                        if 'error' in result.lower() or 'failed' in result.lower():
                            failures.append(image_name)
                            results.append(f"✗ {image_name}: {result}")
                        else:
                            successes.append(image_name)
                            results.append(f"✓ {image_name}: {result}")
                    else:
                        successes.append(image_name)
                        results.append(f"✓ {image_name}: Operation completed")
                        
                except Exception as e:
                    failures.append(image_name)
                    results.append(f"✗ {image_name}: {str(e)}")
            
            # Post-action status verification for all processed images
            logger.info("Verifying post-action status for images")
            post_action_status = {}
            
            # Allow some time for OpenStack operations to complete
            import time
            time.sleep(2)
            
            for image_name in name_list:
                post_action_status[image_name] = _get_resource_status_by_name("image", image_name.strip())
            
            # Prepare summary with post-action status
            summary_parts = [
                f"Bulk Image Management - Action: {action}",
                f"Total images: {len(name_list)}",
                f"Successes: {len(successes)}",
                f"Failures: {len(failures)}"
            ]
            
            if successes:
                summary_parts.append(f"Successful images: {', '.join(successes)}")
            if failures:
                summary_parts.append(f"Failed images: {', '.join(failures)}")
                
            summary_parts.append("\nDetailed Results:")
            summary_parts.extend(results)
            
            # Add post-action status information
            summary_parts.append("\nPost-Action Status:")
            for image_name in name_list:
                current_status = post_action_status.get(image_name, 'Unknown')
                status_indicator = "🟢" if current_status.lower() in ["active", "available"] else "🔴" if current_status.lower() in ["deleted", "error", "killed"] else "🟡"
                summary_parts.append(f"{status_indicator} {image_name}: {current_status}")
            
            return "\n".join(summary_parts)
        
    except Exception as e:
        error_msg = f"Error: Failed to manage image(s) '{image_names}' - {str(e)}"
        logger.error(error_msg)
        return error_msg
