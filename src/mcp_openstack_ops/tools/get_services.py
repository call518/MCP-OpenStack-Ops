"""Tool implementation for get_services."""

import json
from ..functions import get_services as _get_services
from ..mcp_main import mcp


@mcp.tool()
async def get_services() -> str:
    """List the Keystone service catalog (like 'openstack service list').

    This is the catalog of registered services, not their health; for the
    state of Nova, Neutron, Cinder and other service processes, use
    get_service_status.

    Returns:
        JSON with services, each with id, name, type, description and enabled.
    """
    return json.dumps(_get_services(), indent=2)
