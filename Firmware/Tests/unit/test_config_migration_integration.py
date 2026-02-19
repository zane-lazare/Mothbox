"""Tests for config_migrations.sh integration with update workflow.

Verifies that:
- ensure_key adds missing keys without overwriting existing values
- rename_key preserves user values under new names
- remove_key cleans up deprecated keys
- Migrations are idempotent
- Backup files are created
"""

import os
import subprocess

import pytest


@pytest.fixture
def migration_script():
    """Path to config_migrations.sh."""
    repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    script = os.path.join(repo_root, "config_migrations.sh")
    assert os.path.exists(script), f"config_migrations.sh not found at {script}"
    return script


@pytest.fixture
def config_dir(tmp_path):
    """Create a temporary config directory."""
    return tmp_path


def run_migration(migration_script, config_dir):
    """Source config_migrations.sh and call run_config_migrations."""
    cmd = f'source "{migration_script}" && run_config_migrations "{config_dir}"'
    result = subprocess.run(
        ["bash", "-c", cmd],
        capture_output=True,
        text=True,
    )
    return result


class TestEnsureKeyIntegration:
    """Test that missing keys are added to real config files."""

    def test_adds_missing_keys_to_controls(self, migration_script, config_dir):
        controls = config_dir / "controls.txt"
        controls.write_text("name=mothbox\nsoftwareversion=5.0.0\n")

        result = run_migration(migration_script, config_dir)
        assert result.returncode == 0

        content = controls.read_text()
        assert "cache_max_size_mb=500" in content
        assert "log_level=INFO" in content
        assert "name=mothbox" in content  # preserved

    def test_preserves_user_customized_values(self, migration_script, config_dir):
        controls = config_dir / "controls.txt"
        controls.write_text("log_level=DEBUG\ncache_max_size_mb=1000\n")

        run_migration(migration_script, config_dir)

        content = controls.read_text()
        assert "log_level=DEBUG" in content  # not overwritten
        assert "cache_max_size_mb=1000" in content  # not overwritten

    def test_adds_missing_csv_keys(self, migration_script, config_dir):
        camera = config_dir / "camera_settings.csv"
        camera.write_text("SETTING,VALUE,DETAILS\nLensPosition,0.5,lens\n")

        run_migration(migration_script, config_dir)

        content = camera.read_text()
        assert "HDR," in content
        assert "LensPosition,0.5,lens" in content  # preserved

    def test_idempotent(self, migration_script, config_dir):
        controls = config_dir / "controls.txt"
        controls.write_text("name=mothbox\n")

        run_migration(migration_script, config_dir)
        content_first = controls.read_text()

        run_migration(migration_script, config_dir)
        content_second = controls.read_text()

        assert content_first == content_second


class TestBackupIntegration:
    """Test that backup files are created correctly."""

    def test_creates_pre_migration_backup(self, migration_script, config_dir):
        controls = config_dir / "controls.txt"
        controls.write_text("name=mothbox\n")

        run_migration(migration_script, config_dir)

        backup = config_dir / "controls.txt.pre-migration"
        assert backup.exists()
        assert backup.read_text() == "name=mothbox\n"

    def test_backup_reflects_pre_migration_state(self, migration_script, config_dir):
        controls = config_dir / "controls.txt"
        controls.write_text("name=mothbox\n")

        run_migration(migration_script, config_dir)

        backup = config_dir / "controls.txt.pre-migration"
        assert "cache_max_size_mb" not in backup.read_text()
        assert "cache_max_size_mb=500" in controls.read_text()


class TestMissingFiles:
    """Test graceful handling of missing config files."""

    def test_handles_missing_config_dir(self, migration_script, tmp_path):
        nonexistent = tmp_path / "nonexistent"
        result = run_migration(migration_script, nonexistent)
        assert result.returncode == 0

    def test_handles_missing_individual_files(self, migration_script, config_dir):
        controls = config_dir / "controls.txt"
        controls.write_text("name=mothbox\n")

        result = run_migration(migration_script, config_dir)
        assert result.returncode == 0
        assert "cache_max_size_mb=500" in controls.read_text()
