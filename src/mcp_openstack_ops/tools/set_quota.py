"""Tool implementation for set_quota."""

from ..functions import set_quota as _set_quota
from ..mcp_main import (
    conditional_tool,
    handle_operation_result,
    logger,
)

@conditional_tool
async def set_quota(
    project_name: str, 
    action: str, 
    cores: int = None,
    instances: int = None,
    ram: int = None,
    volumes: int = None,
    snapshots: int = None,
    gigabytes: int = None,
    networks: int = None,
    ports: int = None,
    routers: int = None,
    floating_ips: int = None,
    security_groups: int = None,
    security_group_rules: int = None
) -> str:
    """
    Manage project quotas (set, delete, list).
    
    Args:
        project_name: Name of the project (required for set/delete, optional for list)
        action: Action to perform (set, delete, list)
        cores: Compute cores quota (optional, for set action)
        instances: Instance count quota (optional, for set action)
        ram: RAM in MB quota (optional, for set action)
        volumes: Volume count quota (optional, for set action)
        snapshots: Snapshot count quota (optional, for set action)
        gigabytes: Storage in GB quota (optional, for set action)
        networks: Network count quota (optional, for set action)
        ports: Port count quota (optional, for set action)
        routers: Router count quota (optional, for set action)
        floating_ips: Floating IP count quota (optional, for set action)
        security_groups: Security group count quota (optional, for set action)
        security_group_rules: Security group rules count quota (optional, for set action)
    
    Returns:
        JSON string containing the result of the quota management operation
    """
    try:
        logger.info(f"Managing quota - Action: {action}, Project: {project_name}")
        
        # Build quota parameters for set action
        quota_params = {}
        if cores is not None:
            quota_params['cores'] = cores
        if instances is not None:
            quota_params['instances'] = instances
        if ram is not None:
            quota_params['ram'] = ram
        if volumes is not None:
            quota_params['volumes'] = volumes
        if snapshots is not None:
            quota_params['snapshots'] = snapshots
        if gigabytes is not None:
            quota_params['gigabytes'] = gigabytes
        if networks is not None:
            quota_params['networks'] = networks
        if ports is not None:
            quota_params['ports'] = ports
        if routers is not None:
            quota_params['routers'] = routers
        if floating_ips is not None:
            quota_params['floating_ips'] = floating_ips
        if security_groups is not None:
            quota_params['security_groups'] = security_groups
        if security_group_rules is not None:
            quota_params['security_group_rules'] = security_group_rules
        
        quota_result = _set_quota(project_name=project_name, action=action, **quota_params)
        
        # Use centralized result handling
        return handle_operation_result(
            quota_result,
            "Quota Management",
            {
                "Action": action,
                "Project": project_name or "Current project",
                "Parameters": f"{len(quota_params)} quota limits" if quota_params else "No limits specified"
            }
        )
        
    except Exception as e:
        error_msg = f"Error: Failed to manage quota - {str(e)}"
        logger.error(error_msg)
        return error_msg
