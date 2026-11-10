"""Regression tests for optional-service classification in the live harness."""

from types import SimpleNamespace
from unittest.mock import Mock

from scripts.live_tool_check import Runner


def test_optional_tool_dependencies_are_classified():
    runner = Runner(None, None, None)

    assert runner.required_service('get_gnocchi_measures') == 'metric'
    assert runner.required_service('set_alarms') == 'alarming'
    assert runner.required_service('get_heat_stacks') == 'orchestration'
    assert runner.required_service('set_volume_backups') == 'backup'
    assert runner.required_service('get_volume_list') == 'block-storage'


def test_cinder_backup_detection():
    conn = SimpleNamespace(block_storage=Mock())
    runner = Runner(None, conn, None)
    conn.block_storage.services.return_value = [
        SimpleNamespace(binary='cinder-volume'),
    ]
    assert runner.has_cinder_backup() is False

    conn.block_storage.services.return_value = [
        SimpleNamespace(binary='cinder-backup'),
    ]
    assert runner.has_cinder_backup() is True

    conn.block_storage.services.side_effect = PermissionError
    assert runner.has_cinder_backup() is True
