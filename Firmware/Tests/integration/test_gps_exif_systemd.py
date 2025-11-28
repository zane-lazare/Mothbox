"""
Integration tests for GPS EXIF systemd service integration
Tests service startup, operation, and monitoring scenarios
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import tempfile
import subprocess
from PIL import Image


class TestSystemdServiceIntegration:
    """Test systemd service integration scenarios."""

    def test_service_file_exists(self):
        """Test that systemd service files exist."""
        service_dir = Path('/home/zane/projects/Mothbox/Firmware/webui/services')

        production_service = service_dir / 'gps-exif-tagger.service'
        legacy_service = service_dir / 'gps-exif-tagger-legacy.service'

        assert production_service.exists(), "Production service file should exist"
        assert legacy_service.exists(), "Legacy service file should exist"

    def test_service_file_contains_correct_exec_start(self):
        """Test that service files have correct ExecStart paths."""
        service_file = Path('/home/zane/projects/Mothbox/Firmware/webui/services/gps-exif-tagger.service')

        content = service_file.read_text()

        # Should reference gps_exif_tagger.py
        assert 'gps_exif_tagger.py' in content
        # Should use watch mode
        assert '--watch' in content or '--mode' in content

    def test_service_file_has_restart_policy(self):
        """Test that service files have restart policy configured."""
        service_file = Path('/home/zane/projects/Mothbox/Firmware/webui/services/gps-exif-tagger.service')

        content = service_file.read_text()

        # Should have restart configuration
        assert 'Restart=' in content
        # Should restart on failure
        assert 'on-failure' in content or 'always' in content

    def test_service_file_has_proper_dependencies(self):
        """Test that service files declare proper dependencies."""
        service_file = Path('/home/zane/projects/Mothbox/Firmware/webui/services/gps-exif-tagger.service')

        content = service_file.read_text()

        # Should wait for filesystem
        assert 'After=' in content
        # Should be part of multi-user target
        assert 'WantedBy=' in content

    def test_service_runs_in_batch_mode_simulation(self):
        """Simulate systemd running service in batch mode."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)

            # Create test photos
            for i in range(3):
                photo_path = tmp_path / f'test_{i}.jpg'
                img = Image.new('RGB', (100, 100), color='white')
                img.save(photo_path)

            # Simulate service execution
            from webui.cli import gps_exif_tagger

            logger = gps_exif_tagger.setup_logging(verbose=False)

            # Create GPS data
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as controls:
                controls.write("lat=40.7\n")
                controls.write("lon=-74.0\n")
                controls.write("fix=3\n")
                controls.flush()
                controls_path = Path(controls.name)

            try:
                with patch('webui.backend.lib.gps_exif_lib.CONTROLS_FILE', controls_path):
                    stats = gps_exif_tagger.batch_process_directory(
                        tmp_path,
                        logger,
                        pattern='*.jpg'
                    )

                    # Service should process all photos
                    assert stats['total'] == 3
                    assert stats['errors'] == 0
            finally:
                controls_path.unlink()

    def test_service_handles_missing_gps_gracefully(self):
        """Test that service handles missing GPS data without crashing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)

            # Create test photo
            photo_path = tmp_path / 'test.jpg'
            img = Image.new('RGB', (100, 100), color='blue')
            img.save(photo_path)

            # Simulate service execution
            from webui.cli import gps_exif_tagger

            logger = gps_exif_tagger.setup_logging(verbose=False)

            # Create GPS data with no fix
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as controls:
                controls.write("lat=n/a\n")
                controls.write("lon=n/a\n")
                controls.write("fix=0\n")
                controls.flush()
                controls_path = Path(controls.name)

            try:
                with patch('webui.backend.lib.gps_exif_lib.CONTROLS_FILE', controls_path):
                    # Should not crash
                    stats = gps_exif_tagger.batch_process_directory(
                        tmp_path,
                        logger,
                        pattern='*.jpg'
                    )

                    # Should skip photos gracefully
                    assert stats['total'] >= 0
            finally:
                controls_path.unlink()


class TestServiceMonitoring:
    """Test service monitoring and logging."""

    def test_logging_setup_produces_output(self):
        """Test that logging is properly configured for service."""
        from webui.cli import gps_exif_tagger
        import logging

        logger = gps_exif_tagger.setup_logging(verbose=False)

        # Should be a logger instance
        assert isinstance(logger, logging.Logger)
        # Should have handlers
        assert len(logger.handlers) > 0
        # Should log to stdout/stderr for systemd journal
        assert logger.level in [logging.INFO, logging.DEBUG]

    def test_batch_processing_reports_statistics(self):
        """Test that batch processing reports statistics for monitoring."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)

            # Create test photos
            for i in range(5):
                photo_path = tmp_path / f'test_{i}.jpg'
                img = Image.new('RGB', (100, 100), color='red')
                img.save(photo_path)

            from webui.cli import gps_exif_tagger

            logger = Mock()

            stats = gps_exif_tagger.batch_process_directory(
                tmp_path,
                logger,
                pattern='*.jpg'
            )

            # Should return complete statistics
            assert 'total' in stats
            assert 'tagged' in stats
            assert 'skipped' in stats
            assert 'errors' in stats

            # Should log summary
            assert logger.info.called

    def test_watch_mode_logs_startup_information(self):
        """Test that watch mode logs startup information for monitoring."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)

            from webui.cli import gps_exif_tagger

            logger = Mock()

            # Mock sleep to exit quickly
            with patch('time.sleep', side_effect=[0.1, KeyboardInterrupt]):
                try:
                    gps_exif_tagger.watch_directory(
                        tmp_path,
                        logger,
                        pattern='*.jpg',
                        interval=10
                    )
                except (KeyboardInterrupt, SystemExit):
                    pass

            # Should log startup information
            info_calls = [str(call) for call in logger.info.call_args_list]
            assert any('Starting watch mode' in call for call in info_calls)
            assert any('interval' in call.lower() for call in info_calls)


class TestCrossServiceIntegration:
    """Test integration with other Mothbox services."""

    def test_gps_exif_tagger_works_after_takephoto(self):
        """Test that GPS EXIF tagger can process photos created by TakePhoto.py."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)

            # Simulate TakePhoto.py creating a photo
            # Standard Mothbox filename format: YYYYMMDD_HHMMSS.jpg
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            photo_path = tmp_path / f'{timestamp}.jpg'

            # Create photo
            img = Image.new('RGB', (100, 100), color='green')
            img.save(photo_path, quality=95)

            # Now run GPS EXIF tagger
            from webui.cli import gps_exif_tagger

            logger = Mock()

            # Create GPS data
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as controls:
                controls.write("lat=40.7128\n")
                controls.write("lon=-74.0060\n")
                controls.write("fix=3\n")
                controls.write("alt=10.5\n")
                controls.flush()
                controls_path = Path(controls.name)

            try:
                result = gps_exif_tagger.process_single_photo(
                    photo_path,
                    logger,
                    controls_file=controls_path
                )

                # Should process successfully
                assert 'success' in result or 'skipped' in result
                assert photo_path.exists()
            finally:
                controls_path.unlink()

    def test_gps_exif_tagger_preserves_camera_exif(self):
        """Test that GPS EXIF tagger preserves existing camera EXIF metadata."""
        with tempfile.TemporaryFile(suffix='.jpg', delete=False) as tmp:
            tmp_path = Path(tmp.name)

        try:
            # Create photo with camera EXIF
            import piexif

            img = Image.new('RGB', (100, 100), color='yellow')

            # Add camera EXIF metadata
            exif_dict = {
                '0th': {
                    piexif.ImageIFD.Make: b'Raspberry Pi',
                    piexif.ImageIFD.Model: b'Arducam OwlSight 64MP',
                    piexif.ImageIFD.Software: b'Mothbox v5.0',
                },
                'Exif': {
                    piexif.ExifIFD.ExposureTime: (1, 100),
                    piexif.ExifIFD.FNumber: (28, 10),
                    piexif.ExifIFD.ISOSpeedRatings: 100,
                }
            }

            exif_bytes = piexif.dump(exif_dict)
            img.save(tmp_path, exif=exif_bytes)

            # Run GPS EXIF tagger
            from webui.backend.lib.gps_exif_lib import embed_gps_exif

            # Create GPS data
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as controls:
                controls.write("lat=40.7\n")
                controls.write("lon=-74.0\n")
                controls.write("fix=3\n")
                controls.flush()
                controls_path = Path(controls.name)

            try:
                result = embed_gps_exif(tmp_path, controls_file=controls_path)

                # Verify camera EXIF is preserved
                exif_dict = piexif.load(str(tmp_path))

                assert exif_dict['0th'][piexif.ImageIFD.Make] == b'Raspberry Pi'
                assert exif_dict['0th'][piexif.ImageIFD.Model] == b'Arducam OwlSight 64MP'
                assert piexif.ExifIFD.ExposureTime in exif_dict['Exif']
            finally:
                controls_path.unlink()
        finally:
            tmp_path.unlink()

    def test_verify_tool_can_check_tagger_output(self):
        """Test that verify_gps_exif.py can verify tagger output."""
        with tempfile.TemporaryFile(suffix='.jpg', delete=False) as tmp:
            tmp_path = Path(tmp.name)

        try:
            # Create and tag a photo
            img = Image.new('RGB', (100, 100), color='purple')
            img.save(tmp_path)

            # Tag with GPS
            from webui.backend.lib.gps_exif_lib import embed_gps_exif

            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as controls:
                controls.write("lat=40.7128\n")
                controls.write("lon=-74.0060\n")
                controls.write("fix=3\n")
                controls.write("alt=15.0\n")
                controls.flush()
                controls_path = Path(controls.name)

            try:
                result = embed_gps_exif(tmp_path, controls_file=controls_path)

                # Now verify with verify tool
                from webui.backend.lib.gps_exif_lib import verify_gps_exif

                verification = verify_gps_exif(tmp_path)

                # Should have GPS data
                assert verification.get('has_gps', False) is True
                assert 'latitude' in verification
                assert 'longitude' in verification
            finally:
                controls_path.unlink()
        finally:
            tmp_path.unlink()
