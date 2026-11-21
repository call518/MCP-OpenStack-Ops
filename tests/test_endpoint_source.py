"""OS_ENDPOINT_SOURCE and OS_INTERFACE select where service endpoints come from."""

from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from mcp_openstack_ops import connection, settings, user_connection as users
from mcp_openstack_ops.services import storage

CONFIGURED_SERVICES = (
    "compute", "network", "block_storage", "image", "placement", "orchestration",
)


@pytest.fixture(autouse=True)
def clean_endpoint_env(monkeypatch):
    for name in ("OS_ENDPOINT_SOURCE", "OS_INTERFACE", "OS_VOLUME_PORT"):
        monkeypatch.delenv(name, raising=False)


def test_defaults_keep_configured_endpoints_and_internal_interface():
    assert settings.endpoint_source() == "configured"
    assert settings.endpoint_interface() == "internal"


@pytest.mark.parametrize("value, expected", [
    ("catalog", "catalog"), (" Catalog ", "catalog"), ("configured", "configured"),
])
def test_endpoint_source_values(monkeypatch, value, expected):
    monkeypatch.setenv("OS_ENDPOINT_SOURCE", value)
    assert settings.endpoint_source() == expected


@pytest.mark.parametrize("value", ["public", "internal", "admin", "PUBLIC"])
def test_interface_values(monkeypatch, value):
    monkeypatch.setenv("OS_INTERFACE", value)
    assert settings.endpoint_interface() == value.lower()


@pytest.mark.parametrize("name, value", [
    ("OS_ENDPOINT_SOURCE", "keystone"), ("OS_INTERFACE", "private"),
])
def test_invalid_values_are_reported(monkeypatch, name, value):
    monkeypatch.setenv(name, value)
    with pytest.raises(ValueError, match=name):
        settings.endpoint_source() if name == "OS_ENDPOINT_SOURCE" \
            else settings.endpoint_interface()


@pytest.mark.parametrize("name, value", [
    ("OS_ENDPOINT_SOURCE", "keystone"), ("OS_INTERFACE", "private"),
])
def test_startup_rejects_invalid_values(monkeypatch, name, value):
    from mcp_openstack_ops.mcp_main import main
    monkeypatch.setenv(name, value)
    with pytest.raises(SystemExit) as error:
        main(["--type", "stdio"])
    assert error.value.code == 2


def _single_account(monkeypatch):
    for name, value in {
        "OS_PROJECT_NAME": "test-project", "OS_USERNAME": "test-user",
        "OS_PASSWORD": "test-only-password", "OS_AUTH_HOST": "keystone.example.test",
        "OS_AUTH_PORT": "443", "OS_AUTH_PROTOCOL": "https",
    }.items():
        monkeypatch.setenv(name, value)
    fake = Mock(current_project_id="project-a")
    fake.config = SimpleNamespace(config={})
    constructor = Mock(return_value=fake)
    monkeypatch.setattr(connection.connection, "Connection", constructor)
    monkeypatch.setattr(connection, "load_dotenv", lambda: None)
    monkeypatch.setattr(connection, "_connection_cache", None)
    monkeypatch.setattr(users, "enabled", False)
    assert connection.get_openstack_connection() is fake
    return constructor.call_args.kwargs, fake


def test_single_account_catalog_mode_uses_catalog_endpoints(monkeypatch):
    monkeypatch.setenv("OS_ENDPOINT_SOURCE", "catalog")
    monkeypatch.setenv("OS_INTERFACE", "public")
    kwargs, fake = _single_account(monkeypatch)
    assert kwargs["interface"] == "public"
    assert kwargs["identity_endpoint"] == "https://keystone.example.test:443"
    for service in ("compute", "network", "volume", "image", "placement",
                    "orchestration"):
        assert f"{service}_endpoint" not in kwargs
    assert "orchestration_endpoint_override" not in fake.config.config


def test_single_account_configured_mode_is_unchanged(monkeypatch):
    kwargs, fake = _single_account(monkeypatch)
    assert kwargs["interface"] == "internal"
    assert kwargs["compute_endpoint"] == "https://keystone.example.test:8774/v2.1"
    assert fake.config.config["orchestration_endpoint_override"] == (
        "https://keystone.example.test:8004/v1/project-a"
    )


def _multi_user(monkeypatch):
    monkeypatch.setattr(users, "enabled", True)
    monkeypatch.setenv("OS_AUTH_HOST", "keystone.example.test")
    monkeypatch.setenv("OS_AUTH_PORT", "443")
    monkeypatch.setenv("OS_AUTH_PROTOCOL", "https")
    access = SimpleNamespace(user_id="alice", project_id="project-a",
                             auth_token="token")
    monkeypatch.setattr(users.ApplicationCredential, "get_access",
                        lambda *args: access)
    return users.authenticate("credential-id", "secret")


def test_multi_user_catalog_mode_has_only_identity_override(monkeypatch):
    monkeypatch.setenv("OS_ENDPOINT_SOURCE", "catalog")
    monkeypatch.setenv("OS_INTERFACE", "public")
    item = _multi_user(monkeypatch)
    try:
        config = item.connection.config.config
        assert config["interface"] == "public"
        assert config["identity_endpoint_override"] == (
            "https://keystone.example.test:443/v3"
        )
        for service in CONFIGURED_SERVICES:
            assert f"{service}_endpoint_override" not in config
        # Catalog URLs still pass through the HTTPS-only session.
        assert isinstance(item.connection.session.session, users.RestrictedSession)
        assert item.connection.session.session.protocol == "https"
    finally:
        item.connection.close()
        item.connection.session.session.close()


def test_multi_user_configured_mode_is_unchanged(monkeypatch):
    item = _multi_user(monkeypatch)
    try:
        config = item.connection.config.config
        assert config["interface"] == "internal"
        for service in CONFIGURED_SERVICES:
            assert config[f"{service}_endpoint_override"].startswith(
                "https://keystone.example.test:")
    finally:
        item.connection.close()
        item.connection.session.session.close()


def test_cinder_port_match_applies_only_to_configured_endpoints(monkeypatch):
    text = "Unable to establish connection to https://cinder.example.test:8776/v3"
    assert storage._mentions_volume_endpoint(text)
    monkeypatch.setenv("OS_ENDPOINT_SOURCE", "catalog")
    assert not storage._mentions_volume_endpoint(text)
