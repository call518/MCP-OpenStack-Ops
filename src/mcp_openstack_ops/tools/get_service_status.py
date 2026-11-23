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
    Report OpenStack service state from service APIs, plus API probes.

    Functions:
    - List Nova and Cinder services, Neutron agents and Heat engines with
      status, state and heartbeat (Heat's service API is usually admin-only)
    - Probe the Glance and Heat APIs, and the Octavia, Barbican, Aodh and
      Gnocchi APIs when the catalog has them, with a one-item request. Probe
      rows have check "api_probe", null host and updated_at, and checked_at
      in UTC; state "up" only means the API answered
    - Report a section that failed as a row with an error

    summary.running_services counts service records only; summary.api_probes
    counts probes. Keystone and the Keystone endpoint catalog are not covered.

    Use when user requests service status, API status, health checks, or service troubleshooting.
    
    Returns:
        Service status information in JSON format with service details and health summary.
    """
    try:
        logger.info("Fetching OpenStack service status")
        services = _get_service_status()
        
        # services is a list, not a dict; probes are not service records.
        records = [s for s in services if s.get('check') != 'api_probe']
        probes = [s for s in services if s.get('check') == 'api_probe']
        enabled_services = [s for s in records if s.get('status') == 'enabled']
        running_services = [s for s in records if s.get('state') == 'up']

        result = {
            "timestamp": datetime.now().isoformat(),
            "service_status": services,
            "summary": {
                "total_services": len(records),
                "enabled_services": len(enabled_services),
                "running_services": len(running_services),
                "api_probes": {
                    "total": len(probes),
                    "answered": sum(s.get('state') == 'up' for s in probes),
                },
                "service_types": sorted(set(s.get('service_type', 'unknown') for s in services))
            }
        }
        
        return json.dumps(result, indent=2, ensure_ascii=False)
        
    except Exception as e:
        error_msg = f"Error: Failed to fetch OpenStack service status - {str(e)}"
        logger.error(error_msg)
        return error_msg
