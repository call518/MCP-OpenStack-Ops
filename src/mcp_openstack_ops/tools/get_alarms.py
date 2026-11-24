"""Tool implementation for get_alarms."""

import json
from ..services.alarms import set_alarms as _query
from ..mcp_main import mcp


@mcp.tool()
async def get_alarms(alarm_name: str = "") -> str:
    """List the current project's Aodh alarms, or show one alarm.

    Requires an alarming endpoint in the Keystone catalog and Aodh. Missing
    services or denied API calls return failure; no simulation is used.

    Args:
        alarm_name: Optional alarm name or ID. When provided, show that alarm
            (a name shared by several alarms is an error; use the alarm ID);
            otherwise list alarms.

    Returns:
        JSON with alarms (or alarm_details) as Aodh returns them.
    """
    if alarm_name:
        return json.dumps(_query(action="show", alarm_name=alarm_name), indent=2)
    return json.dumps(_query(action="list"), indent=2)
