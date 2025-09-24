"""Tool registration utilities for OpenStack MCP."""

import importlib
import pkgutil
from typing import Iterable

def _iter_tool_modules() -> Iterable[str]:
    """Yield importable tool module names within this package."""
    for module_info in pkgutil.iter_modules(__path__):  # type: ignore[name-defined]
        name = module_info.name
        if name.startswith('_'):
            continue
        yield name

def register_all_tools() -> None:
    """Import every tool module so decorators register with FastMCP."""
    for module_name in sorted(_iter_tool_modules()):
        importlib.import_module(f"{__name__}.{module_name}")
