"""Tool implementation for get_flavors."""

import json
from datetime import datetime
from ..functions import get_flavor_list as _get_flavor_list
from ..mcp_main import (
    logger,
    mcp,
)


@mcp.tool()
async def get_flavors(name_contains: str = "", accelerators_only: bool = False) -> str:
    """
    List the compute flavors visible to the project (like 'openstack flavor list --long').

    Each flavor reports vCPUs, RAM (MB), root disk, ephemeral disk and swap,
    visibility, its extra specs, and an `accelerators` summary parsed from the
    `pci_passthrough:alias` and `resources:VGPU`/`resources:PGPU` extra specs.
    Use it to choose a flavor for a new instance or to find GPU flavors.
    `extra_specs` is null with `extra_specs_error` when the specs could not be
    read; an empty object means the flavor has none.

    Flavor sizes are not free capacity: whether a host can fit a flavor right
    now needs admin-only hypervisor or placement data.

    Args:
        name_contains: Only flavors whose name contains this text
            (case-insensitive); empty for all.
        accelerators_only: Only flavors that request GPUs or other
            accelerators (PCI passthrough aliases or VGPU/PGPU resources).
    """
    try:
        logger.info("Fetching flavor list")
        flavors = _get_flavor_list()
        needle = name_contains.strip().lower()
        if needle:
            flavors = [f for f in flavors if needle in str(f.get('name') or '').lower()]
        if accelerators_only:
            flavors = [f for f in flavors if f.get('accelerators')]
        flavors.sort(key=lambda f: (f.get('vcpus') or 0, f.get('ram') or 0, str(f.get('name'))))
        unreadable = [f['name'] for f in flavors if f.get('extra_specs') is None]
        result = {
            "timestamp": datetime.now().isoformat(),
            "total_flavors": len(flavors),
            "flavors": flavors,
        }
        if unreadable:
            result["warning"] = (
                f"Extra specs could not be read for {len(unreadable)} flavor(s); "
                "their accelerators are unknown")
        return json.dumps(result, indent=2, ensure_ascii=False)
    except Exception as e:
        error_msg = f"Error: Failed to fetch flavors - {str(e)}"
        logger.error(error_msg)
        return error_msg
