"""Tool implementation for get_service_status."""

import json
from datetime import datetime
from ..functions import get_service_status as _get_service_status
from ..mcp_main import (
    logger,
    mcp,
)

@mcp.tool()
async def get_service_status() -> str:
    """
    Report the state of Nova and Cinder services and Neutron agents, and whether
    the Glance and Heat APIs answer.

    Functions:
    - List Nova and Cinder services and Neutron agents with status and state
    - Probe the Glance and Heat APIs with a one-item list; these rows have
      host "unknown" and no service record behind them
    - Report a section that failed as a row with an error

    Other services (for example Keystone, Octavia, Barbican, Aodh, Gnocchi)
    and the Keystone endpoint catalog are not covered.

    Use when user requests service status, API status, health checks, or service troubleshooting.
    
    Returns:
        Service status information in JSON format with service details and health summary.
    """
    try:
        logger.info("Fetching OpenStack service status")
        services = _get_service_status()
        
        # services is a list, not a dict
        enabled_services = [s for s in services if s.get('status') == 'enabled']
        running_services = [s for s in services if s.get('state') == 'up']
        
        result = {
            "timestamp": datetime.now().isoformat(),
            "service_status": services,
            "summary": {
                "total_services": len(services),
                "enabled_services": len(enabled_services),
                "running_services": len(running_services),
                "service_types": list(set(s.get('service_type', 'unknown') for s in services))
            }
        }
        
        return json.dumps(result, indent=2, ensure_ascii=False)
        
    except Exception as e:
        error_msg = f"Error: Failed to fetch OpenStack service status - {str(e)}"
        logger.error(error_msg)
        return error_msg
