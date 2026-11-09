"""Tool implementation for get_gnocchi_service_info."""

import json
from ..functions import get_gnocchi_service_info as _get_gnocchi_service_info
from ..mcp_main import mcp


@mcp.tool()
async def get_gnocchi_service_info(sections: str = "") -> str:
    """
    Read Gnocchi service configuration and health information.

    Use to check which granularities and aggregation methods a metric supports
    (for get_gnocchi_measures or set_alarms), which resource types exist, and
    whether measure processing is backlogged.

    Args:
        sections: Comma-separated subset of archive_policies,
            archive_policy_rules, resource_types, capabilities, status
            (default: all). status usually requires an admin role.

    Requires a metric endpoint in the Keystone catalog. A denied section is
    reported in errors while other sections are still returned.

    Returns:
        JSON string with the requested sections and per-section errors.
    """
    result = _get_gnocchi_service_info(sections=sections or None)
    return json.dumps(result, indent=2, ensure_ascii=False, default=str)
