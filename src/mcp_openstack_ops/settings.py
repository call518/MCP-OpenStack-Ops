"""Numeric server settings read from the environment on every call."""

import os

DEFAULT_LIST_MAX_LIMIT = 100
DEFAULT_INSTANCE_FILTER_MAX_MATCHES = 100


def positive_int_setting(name: str, default: int) -> int:
    """Return a positive integer environment setting.

    An unset or empty variable gives ``default``. Any other value that is not
    a positive integer raises ValueError naming the variable, so a typo is
    reported instead of silently replaced.
    """
    raw = os.environ.get(name, '').strip()
    if not raw:
        return default
    if not raw.isdigit() or int(raw) < 1:
        raise ValueError(f'{name} must be a positive integer, got {raw!r}')
    return int(raw)


def list_max_limit() -> int:
    """Most items one call of a list tool with a limit parameter returns."""
    return positive_int_setting('LIST_MAX_LIMIT', DEFAULT_LIST_MAX_LIMIT)


def instance_filter_max_matches() -> int:
    """Most instances a filter-based set_instance call may act on."""
    return positive_int_setting('INSTANCE_FILTER_MAX_MATCHES',
                                DEFAULT_INSTANCE_FILTER_MAX_MATCHES)


ENDPOINT_SOURCES = ('configured', 'catalog')
ENDPOINT_INTERFACES = ('public', 'internal', 'admin')


def endpoint_source() -> str:
    """Where service endpoints come from: OS_ENDPOINT_SOURCE.

    ``configured`` (the default) builds the compute, network, volume, image,
    placement and Heat URLs from OS_AUTH_HOST and the OS_*_PORT settings.
    ``catalog`` uses the Keystone service catalog for every service, for clouds
    that publish each service on its own host or URL path.
    """
    raw = os.environ.get('OS_ENDPOINT_SOURCE', '').strip().lower()
    if not raw:
        return 'configured'
    if raw not in ENDPOINT_SOURCES:
        raise ValueError(
            f"OS_ENDPOINT_SOURCE must be one of {', '.join(ENDPOINT_SOURCES)}, "
            f"got {raw!r}")
    return raw


def endpoint_interface() -> str:
    """Catalog interface used for endpoints not built from settings: OS_INTERFACE."""
    raw = os.environ.get('OS_INTERFACE', '').strip().lower()
    if not raw:
        return 'internal'
    if raw not in ENDPOINT_INTERFACES:
        raise ValueError(
            f"OS_INTERFACE must be one of {', '.join(ENDPOINT_INTERFACES)}, "
            f"got {raw!r}")
    return raw
