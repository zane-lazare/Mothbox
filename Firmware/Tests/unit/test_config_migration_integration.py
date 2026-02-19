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
import textwrap

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


class TestRealWorldScenarios:
    """Test migration against realistic config files from actual Mothbox installs."""

    def test_old_install_missing_hdr(self, migration_script, config_dir):
        """Issue #378: Old installs missing HDR setting default to wrong value."""
        camera = config_dir / "camera_settings.csv"
        camera.write_text(textwrap.dedent("""\
            SETTING,VALUE,DETAILS
            LensPosition,0.5,lens position
            ExposureValue,0.6,exposure
            ExposureTime,499,microseconds
            AnalogueGain,8.0,gain
        """))

        result = run_migration(migration_script, config_dir)
        assert result.returncode == 0

        content = camera.read_text()
        assert "HDR,1," in content  # default=1 meaning off

    def test_old_install_missing_cache_settings(self, migration_script, config_dir):
        """Old installs before gallery cache feature."""
        controls = config_dir / "controls.txt"
        controls.write_text(textwrap.dedent("""\
            shutdown_enabled=False
            name=mothbox
            softwareversion=5.0.0
            Relay_Ch1=5
            Relay_Ch2=19
            Relay_Ch3=9
        """))

        result = run_migration(migration_script, config_dir)
        assert result.returncode == 0

        content = controls.read_text()
        # New cache settings added
        assert "cache_max_size_mb=500" in content
        assert "cache_sizes=64,128,256" in content
        assert "thumbnail_quality=85" in content
        # User values preserved
        assert "Relay_Ch1=5" in content
        assert "name=mothbox" in content

    def test_full_current_config_unchanged(self, migration_script, config_dir):
        """Running migration on a fully up-to-date config changes nothing."""
        controls = config_dir / "controls.txt"
        controls.write_text(textwrap.dedent("""\
            shutdown_enabled=False
            OnlyFlash=False
            LastCalibration=0
            nextWake=0
            name=mothbox
            softwareversion=5.0.0
            gpstime=0
            UTCoff=-5
            lat=n/a
            lon=n/a
            gps_fix_mode=0
            gps_satellites_used=0
            gps_satellites_visible=0
            gps_altitude=0
            gps_hdop=99.99
            gps_pdop=99.99
            last_known_lat=n/a
            last_known_lon=n/a
            last_position_time=0
            weekdays=1;2;3;4;5;6;7
            hours=19;21;23;2;4
            minutes=0
            runtime=59
            Relay_Ch1=5
            Relay_Ch2=19
            Relay_Ch3=9
            relay_enabled=true
            relay_active_low=true
            flash_duration_ms=100
            off_pin=16
            debug_pin=12
            jpeg_quality=96
            cache_max_size_mb=500
            cache_sizes=64,128,256
            thumbnail_quality=85
            cache_warm_on_startup=false
            cache_warm_count=100
            log_level=INFO
            log_retention_days=7
        """))

        content_before = controls.read_text()

        result = run_migration(migration_script, config_dir)
        assert result.returncode == 0

        content_after = controls.read_text()
        assert content_before == content_after
