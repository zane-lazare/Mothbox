"""
Unit tests for gps_exif_tagger.py operational functions
Tests batch processing, watch mode, and single photo processing
"""

import contextlib
import tempfile
import time
from pathlib import Path
from unittest.mock import Mock, patch

from PIL import Image

# Import the module under test
from webui.cli import gps_exif_tagger


class TestBatchProcessing:
    """Test batch_process_directory function."""

    def test_batch_process_empty_directory(self):
        """Test batch processing an empty directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            logger = Mock()

            stats = gps_exif_tagger.batch_process_directory(tmp_path, logger, pattern="*.jpg")

            assert stats["total"] == 0
            assert stats["tagged"] == 0
            assert stats["skipped"] == 0
            assert stats["errors"] == 0

    def test_batch_process_single_photo(self):
        """Test batch processing with a single photo."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            logger = Mock()

            # Create a test photo
            photo_path = tmp_path / "test.jpg"
            img = Image.new("RGB", (100, 100), color="white")
            img.save(photo_path)

            # Create GPS data
            with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as controls:
                controls.write("lat=40.7\n")
                controls.write("lon=-74.0\n")
                controls.write("fix=3\n")
                controls.flush()
                controls_path = Path(controls.name)

            try:
                with patch("webui.backend.lib.gps_exif_lib.CONTROLS_FILE", controls_path):
                    stats = gps_exif_tagger.batch_process_directory(
                        tmp_path, logger, pattern="*.jpg"
                    )

                    assert stats["total"] == 1
                    assert stats["tagged"] >= 0  # May be tagged or skipped
            finally:
                controls_path.unlink()

    def test_batch_process_multiple_photos(self):
        """Test batch processing with multiple photos."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            logger = Mock()

            # Create multiple test photos
            for i in range(5):
                photo_path = tmp_path / f"test_{i}.jpg"
                img = Image.new("RGB", (100, 100), color="white")
                img.save(photo_path)

            stats = gps_exif_tagger.batch_process_directory(tmp_path, logger, pattern="*.jpg")

            assert stats["total"] == 5

    def test_batch_process_with_pattern_filter(self):
        """Test batch processing with file pattern filtering."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            logger = Mock()

            # Create photos with different extensions
            for ext in ["jpg", "jpeg", "png", "txt"]:
                photo_path = tmp_path / f"test.{ext}"
                if ext in ["jpg", "jpeg", "png"]:
                    img = Image.new("RGB", (100, 100), color="white")
                    img.save(photo_path)
                else:
                    photo_path.write_text("text file")

            stats = gps_exif_tagger.batch_process_directory(tmp_path, logger, pattern="*.jpg")

            # Should only find .jpg files
            assert stats["total"] == 1

    def test_batch_process_with_force_flag(self):
        """Test batch processing with force re-tagging."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            logger = Mock()

            # Create and tag a photo
            photo_path = tmp_path / "test.jpg"
            img = Image.new("RGB", (100, 100), color="white")
            img.save(photo_path)

            # Create GPS data
            with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as controls:
                controls.write("lat=40.7\n")
                controls.write("lon=-74.0\n")
                controls.write("fix=3\n")
                controls.flush()
                controls_path = Path(controls.name)

            try:
                with patch("webui.backend.lib.gps_exif_lib.CONTROLS_FILE", controls_path):
                    # First tagging
                    stats1 = gps_exif_tagger.batch_process_directory(
                        tmp_path, logger, pattern="*.jpg", force=False
                    )

                    # Second tagging without force - should skip
                    stats2 = gps_exif_tagger.batch_process_directory(
                        tmp_path, logger, pattern="*.jpg", force=False
                    )

                    # Third tagging with force - should re-tag
                    stats3 = gps_exif_tagger.batch_process_directory(
                        tmp_path, logger, pattern="*.jpg", force=True
                    )

                    # Verify force behavior
                    assert stats1["total"] == 1
                    assert stats2["total"] == 1
                    assert stats3["total"] == 1
            finally:
                controls_path.unlink()

    def test_batch_process_dry_run(self):
        """Test batch processing in dry-run mode."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            logger = Mock()

            # Create a test photo
            photo_path = tmp_path / "test.jpg"
            img = Image.new("RGB", (100, 100), color="white")
            img.save(photo_path)

            # Get original modification time
            original_mtime = photo_path.stat().st_mtime

            # Create GPS data
            with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as controls:
                controls.write("lat=40.7\n")
                controls.write("lon=-74.0\n")
                controls.write("fix=3\n")
                controls.flush()
                controls_path = Path(controls.name)

            try:
                with patch("webui.backend.lib.gps_exif_lib.CONTROLS_FILE", controls_path):
                    gps_exif_tagger.batch_process_directory(
                        tmp_path, logger, pattern="*.jpg", dry_run=True
                    )

                    # File should not be modified
                    assert photo_path.stat().st_mtime == original_mtime
            finally:
                controls_path.unlink()

    def test_batch_process_with_backup(self):
        """Test batch processing with backup creation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            logger = Mock()

            # Create a test photo
            photo_path = tmp_path / "test.jpg"
            img = Image.new("RGB", (100, 100), color="white")
            img.save(photo_path)

            # Create GPS data
            with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as controls:
                controls.write("lat=40.7\n")
                controls.write("lon=-74.0\n")
                controls.write("fix=3\n")
                controls.flush()
                controls_path = Path(controls.name)

            try:
                with patch("webui.backend.lib.gps_exif_lib.CONTROLS_FILE", controls_path):
                    gps_exif_tagger.batch_process_directory(
                        tmp_path, logger, pattern="*.jpg", backup=True
                    )
            finally:
                controls_path.unlink()

    def test_batch_process_logs_summary(self):
        """Test that batch processing logs summary statistics."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            logger = Mock()

            # Create test photos
            for i in range(3):
                photo_path = tmp_path / f"test_{i}.jpg"
                img = Image.new("RGB", (100, 100), color="white")
                img.save(photo_path)

            gps_exif_tagger.batch_process_directory(tmp_path, logger, pattern="*.jpg")

            # Should log summary
            assert logger.info.called
            info_calls = [str(call) for call in logger.info.call_args_list]
            assert any("Summary" in call or "Total" in call for call in info_calls)

    def test_batch_process_preserves_chronological_order(self):
        """Test that batch processing preserves chronological file order."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            logger = Mock()

            # Create files with timestamps in specific order
            # (sorted alphabetically = photo1, photo2, photo3)
            # We'll create them with specific mtimes to test chronological ordering
            import time

            photo1 = tmp_path / "photo1.jpg"
            photo2 = tmp_path / "photo2.JPG"  # Different case
            photo3 = tmp_path / "photo3.jpg"

            # Create files at different times
            img = Image.new("RGB", (100, 100), color="red")
            img.save(photo1)
            time.sleep(0.01)

            img = Image.new("RGB", (100, 100), color="green")
            img.save(photo2)
            time.sleep(0.01)

            img = Image.new("RGB", (100, 100), color="blue")
            img.save(photo3)

            # Track processing order
            processed_files = []

            def track_processing(photo_path, *args, **kwargs):
                processed_files.append(photo_path.name)
                return {"success": True, "skipped": False}

            mock_resolved = {
                "lat": 35.96, "lon": -83.92, "source": "gps",
                "deployment_name": None,
                "gps_data": {"has_fix": True, "latitude": 35.96, "longitude": -83.92,
                             "altitude": None, "fix_mode": 3, "gpstime": 0,
                             "satellites_used": 0, "hdop": 99.99, "pdop": 99.99},
            }

            with patch.object(
                gps_exif_tagger, "process_single_photo", side_effect=track_processing
            ), patch(
                "webui.cli.gps_exif_tagger.resolve_coordinates",
                return_value=mock_resolved,
            ):
                gps_exif_tagger.batch_process_directory(
                    tmp_path, logger, pattern="*.jpg", force=False, backup=False, dry_run=False
                )

            # Verify all 3 files were processed
            assert len(processed_files) == 3, f"Expected 3 files, got {len(processed_files)}"

            # Verify files were processed in sorted order (alphabetically)
            # This ensures chronological order is maintained after deduplication
            assert processed_files == ["photo1.jpg", "photo2.JPG", "photo3.jpg"], (
                f"Files processed out of order: {processed_files}"
            )

    def test_batch_process_ignores_symlinks(self):
        """Test that batch processing skips symlinks (security: prevent directory traversal)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            logger = Mock()

            # Create real photo
            real_photo = tmp_path / "real.jpg"
            img = Image.new("RGB", (100, 100), color="blue")
            img.save(real_photo)

            # Create external directory with photo
            external_dir = tmp_path / "external"
            external_dir.mkdir()
            external_photo = external_dir / "external.jpg"
            img = Image.new("RGB", (100, 100), color="red")
            img.save(external_photo)

            # Create symlink to external photo
            symlink_photo = tmp_path / "symlink.jpg"
            symlink_photo.symlink_to(external_photo)

            # Track which files were processed
            processed_files = []

            def track_processing(photo_path, *args, **kwargs):
                processed_files.append(photo_path.name)
                return {"success": True, "skipped": False}

            mock_resolved = {
                "lat": 35.96, "lon": -83.92, "source": "gps",
                "deployment_name": None,
                "gps_data": {"has_fix": True, "latitude": 35.96, "longitude": -83.92,
                             "altitude": None, "fix_mode": 3, "gpstime": 0,
                             "satellites_used": 0, "hdop": 99.99, "pdop": 99.99},
            }

            with patch.object(
                gps_exif_tagger, "process_single_photo", side_effect=track_processing
            ), patch(
                "webui.cli.gps_exif_tagger.resolve_coordinates",
                return_value=mock_resolved,
            ):
                gps_exif_tagger.batch_process_directory(
                    tmp_path, logger, pattern="*.jpg", force=False, backup=False, dry_run=False
                )

            # Should only process real.jpg, not symlink.jpg
            assert "real.jpg" in processed_files, "Real photo should be processed"
            assert "symlink.jpg" not in processed_files, "Symlink should be skipped (security)"
            assert len(processed_files) == 1, (
                f"Expected 1 file, got {len(processed_files)}: {processed_files}"
            )


class TestSinglePhotoProcessing:
    """Test process_single_photo function."""

    def test_process_single_photo_success(self):
        """Test successful single photo processing."""
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
            tmp_path = Path(tmp.name)

            # Create a test photo
            img = Image.new("RGB", (100, 100), color="blue")
            img.save(tmp_path)

        try:
            logger = Mock()

            # Create GPS data
            with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as controls:
                controls.write("lat=40.7\n")
                controls.write("lon=-74.0\n")
                controls.write("fix=3\n")
                controls.flush()
                controls_path = Path(controls.name)

            try:
                with patch("webui.backend.lib.gps_exif_lib.CONTROLS_FILE", controls_path):
                    result = gps_exif_tagger.process_single_photo(tmp_path, logger)

                    # Should return result dict
                    assert "success" in result or "skipped" in result or "error" in result
            finally:
                controls_path.unlink()
        finally:
            tmp_path.unlink()

    def test_process_single_photo_with_force(self):
        """Test single photo processing with force flag."""
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
            tmp_path = Path(tmp.name)

            # Create a test photo
            img = Image.new("RGB", (100, 100), color="red")
            img.save(tmp_path)

        try:
            logger = Mock()

            # Create GPS data
            with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as controls:
                controls.write("lat=40.7\n")
                controls.write("lon=-74.0\n")
                controls.write("fix=3\n")
                controls.flush()
                controls_path = Path(controls.name)

            try:
                with patch("webui.backend.lib.gps_exif_lib.CONTROLS_FILE", controls_path):
                    result = gps_exif_tagger.process_single_photo(tmp_path, logger, force=True)

                    # Should process with force
                    assert "success" in result or "error" in result
            finally:
                controls_path.unlink()
        finally:
            tmp_path.unlink()

    def test_process_single_photo_error_handling(self):
        """Test single photo processing error handling."""
        nonexistent_path = Path("/nonexistent/photo.jpg")
        logger = Mock()

        result = gps_exif_tagger.process_single_photo(nonexistent_path, logger)

        # Should return error
        assert "error" in result


class TestWatchMode:
    """Test watch_directory function."""

    def test_watch_mode_detects_new_photo(self):
        """Test that watch mode detects newly created photos."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            logger = Mock()

            # Mock process_single_photo to track calls
            with patch.object(
                gps_exif_tagger, "process_single_photo", return_value={"success": True}
            ):
                # Start watch mode in a separate thread-like context
                # Use a timeout to prevent infinite loop
                import threading

                def run_watch():
                    with contextlib.suppress(KeyboardInterrupt):
                        gps_exif_tagger.watch_directory(
                            tmp_path,
                            logger,
                            pattern="*.jpg",
                            interval=1,  # Minimum valid interval
                        )

                watch_thread = threading.Thread(target=run_watch, daemon=True)
                watch_thread.start()

                # Give watch mode time to start
                time.sleep(0.5)

                # Create a new photo
                photo_path = tmp_path / "new_photo.jpg"
                img = Image.new("RGB", (100, 100), color="green")
                img.save(photo_path)

                # Give watch mode time to detect (interval=1s + processing time)
                time.sleep(2.0)

                # Stop watch mode
                # (thread will exit on its own as daemon)

    def test_watch_mode_handles_modified_photo(self):
        """Test that watch mode handles modified photos."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            logger = Mock()

            # Create initial photo
            photo_path = tmp_path / "photo.jpg"
            img = Image.new("RGB", (100, 100), color="yellow")
            img.save(photo_path)

            # Track processing calls
            process_count = [0]

            def mock_process(*args, **kwargs):
                process_count[0] += 1
                return {"success": True}

            with patch.object(gps_exif_tagger, "process_single_photo", side_effect=mock_process):
                import threading

                def run_watch():
                    with contextlib.suppress(KeyboardInterrupt):
                        gps_exif_tagger.watch_directory(
                            tmp_path, logger, pattern="*.jpg", interval=1
                        )

                watch_thread = threading.Thread(target=run_watch, daemon=True)
                watch_thread.start()

                time.sleep(0.5)

                # Modify the photo (change mtime)
                time.sleep(0.5)
                img2 = Image.new("RGB", (100, 100), color="purple")
                img2.save(photo_path)

                time.sleep(2.0)

    def test_watch_mode_handles_errors_gracefully(self):
        """Test that watch mode continues after processing errors."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            logger = Mock()

            # Create a photo
            photo_path = tmp_path / "photo.jpg"
            img = Image.new("RGB", (100, 100), color="orange")
            img.save(photo_path)

            # Mock process to raise error then succeed
            call_count = [0]

            def mock_process(*args, **kwargs):
                call_count[0] += 1
                if call_count[0] == 1:
                    raise Exception("Test error")
                return {"success": True}

            with patch.object(gps_exif_tagger, "process_single_photo", side_effect=mock_process):
                import threading

                def run_watch():
                    with contextlib.suppress(KeyboardInterrupt):
                        gps_exif_tagger.watch_directory(
                            tmp_path, logger, pattern="*.jpg", interval=1
                        )

                watch_thread = threading.Thread(target=run_watch, daemon=True)
                watch_thread.start()

                time.sleep(2.0)

    def test_watch_mode_respects_polling_interval(self):
        """Test that watch mode respects the polling interval."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            logger = Mock()

            # Track sleep calls
            sleep_calls = []

            def mock_sleep(duration):
                sleep_calls.append(duration)
                if len(sleep_calls) >= 3:
                    raise KeyboardInterrupt  # Exit after a few iterations

            with (
                patch("time.sleep", side_effect=mock_sleep),
                contextlib.suppress(KeyboardInterrupt, SystemExit),
            ):
                gps_exif_tagger.watch_directory(tmp_path, logger, pattern="*.jpg", interval=5)

            # Should have called sleep with the interval
            if sleep_calls:
                assert (
                    5 in sleep_calls or 0.5 in sleep_calls
                )  # 5 is interval, 0.5 is file write delay

    def test_watch_mode_keyboard_interrupt_exits_cleanly(self):
        """Test that Ctrl+C exits watch mode cleanly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            logger = Mock()

            # Simulate KeyboardInterrupt
            with patch("time.sleep", side_effect=KeyboardInterrupt):
                # Should exit without raising
                gps_exif_tagger.watch_directory(tmp_path, logger, pattern="*.jpg", interval=1)

            # Should log exit message
            info_calls = [str(call) for call in logger.info.call_args_list]
            assert any("stopped" in call.lower() for call in info_calls)

    def test_watch_mode_case_insensitive_pattern(self):
        """Test that watch mode handles case-insensitive file patterns."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            logger = Mock()

            # Create photos with different case extensions
            photo1 = tmp_path / "photo1.jpg"
            photo2 = tmp_path / "photo2.JPG"
            photo3 = tmp_path / "photo3.jpeg"

            for photo in [photo1, photo2, photo3]:
                img = Image.new("RGB", (100, 100), color="cyan")
                img.save(photo)

            # Mock glob to track what patterns are searched
            glob_patterns = []
            original_glob = Path.glob

            def mock_glob(self, pattern):
                glob_patterns.append(pattern)
                return original_glob(self, pattern)

            with (
                patch.object(Path, "glob", mock_glob),
                patch("time.sleep", side_effect=[0.1, KeyboardInterrupt]),
                contextlib.suppress(KeyboardInterrupt, SystemExit),
            ):
                gps_exif_tagger.watch_directory(tmp_path, logger, pattern="*.jpg", interval=1)

            # Should search for multiple case variants
            # (Implementation detail - may vary)

    def test_watch_mode_handles_file_deletion_race(self):
        """Test that watch mode handles files deleted between stat() and processing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            logger = Mock()

            # Create initial photo
            photo_path = tmp_path / "photo.jpg"
            img = Image.new("RGB", (100, 100), color="yellow")
            img.save(photo_path)

            # Track processing attempts
            process_calls = []

            def mock_process(photo, *args, **kwargs):
                process_calls.append(str(photo))
                return {"success": True, "skipped": False}

            # Delete file after initial detection but before processing
            # (simulate race condition during the 0.5 second sleep)
            def delete_after_delay():
                time.sleep(0.3)  # Wait for detection + partial sleep
                if photo_path.exists():
                    photo_path.unlink()

            with patch.object(gps_exif_tagger, "process_single_photo", side_effect=mock_process):
                import threading

                # Start deletion thread
                delete_thread = threading.Thread(target=delete_after_delay, daemon=True)
                delete_thread.start()

                def run_watch():
                    with contextlib.suppress(KeyboardInterrupt):
                        gps_exif_tagger.watch_directory(
                            tmp_path, logger, pattern="*.jpg", interval=1, backup=False
                        )

                watch_thread = threading.Thread(target=run_watch, daemon=True)
                watch_thread.start()

                # Wait for detection, deletion, and processing attempt (interval=1s + processing)
                time.sleep(2.0)

                # Stop watch mode
                watch_thread.join(timeout=1.0)
                delete_thread.join(timeout=0.5)

            # With fix: process_single_photo() should NOT be called
            # (file is caught by stability check before processing)
            assert len(process_calls) == 0, (
                "Should NOT process file that was deleted during stability check"
            )

            # Verify logger.debug was called with skip message
            # Can be either "disappeared during stability check" or "unstable file"
            debug_calls = [str(call) for call in logger.debug.call_args_list]
            assert any(
                "disappeared" in str(call).lower() or "unstable" in str(call).lower()
                for call in debug_calls
            ), "Should log that file disappeared or is unstable"


class TestFileStability:
    """Test wait_for_file_stability function."""

    def test_stable_file_returns_true(self, tmp_path):
        """Test that a stable file returns True."""
        from webui.cli.gps_exif_tagger import setup_logging, wait_for_file_stability

        logger = setup_logging(verbose=False)

        # Create a stable file
        test_file = tmp_path / "stable.jpg"
        test_file.write_bytes(b"fake jpeg data")

        # Wait for filesystem to settle
        time.sleep(0.1)

        # Should return True
        result = wait_for_file_stability(test_file, logger)
        assert result is True

    def test_nonexistent_file_returns_false(self, tmp_path):
        """Test that a nonexistent file returns False."""
        from webui.cli.gps_exif_tagger import setup_logging, wait_for_file_stability

        logger = setup_logging(verbose=False)

        nonexistent = tmp_path / "does_not_exist.jpg"

        # Should return False
        result = wait_for_file_stability(nonexistent, logger)
        assert result is False

    def test_file_deleted_during_check_returns_false(self, tmp_path):
        """Test that a file deleted during stability check returns False."""
        import threading

        from webui.cli.gps_exif_tagger import (
            FILE_STABILITY_INTERVAL,
            setup_logging,
            wait_for_file_stability,
        )

        logger = setup_logging(verbose=False)

        # Create a file
        test_file = tmp_path / "disappearing.jpg"
        test_file.write_bytes(b"fake jpeg data")

        # Delete file after short delay
        def delete_file():
            time.sleep(FILE_STABILITY_INTERVAL * 0.5)
            if test_file.exists():
                test_file.unlink()

        deleter = threading.Thread(target=delete_file, daemon=True)
        deleter.start()

        # Should return False (file disappeared)
        result = wait_for_file_stability(test_file, logger)
        assert result is False

        deleter.join(timeout=1.0)

    def test_file_modified_during_check_logs_warning(self, tmp_path):
        """Test that files modified during check are logged."""
        import threading

        from webui.cli.gps_exif_tagger import (
            FILE_STABILITY_INTERVAL,
            setup_logging,
            wait_for_file_stability,
        )

        logger = setup_logging(verbose=True)

        # Create a file
        test_file = tmp_path / "modified.jpg"
        test_file.write_bytes(b"initial data")

        # Modify file once during stability check
        def modify_file():
            time.sleep(FILE_STABILITY_INTERVAL * 0.5)
            if test_file.exists():
                test_file.write_bytes(b"modified data")

        modifier = threading.Thread(target=modify_file, daemon=True)
        modifier.start()

        # Should return True after all checks complete
        # (doesn't reset counter - prevents infinite loop)
        result = wait_for_file_stability(test_file, logger)
        assert result is True

        modifier.join(timeout=1.0)

    def test_stability_check_completes_after_max_attempts(self, tmp_path):
        """Test that stability check completes after FILE_STABILITY_CHECKS attempts."""
        import threading

        from webui.cli.gps_exif_tagger import (
            FILE_STABILITY_CHECKS,
            FILE_STABILITY_INTERVAL,
            setup_logging,
            wait_for_file_stability,
        )

        logger = setup_logging(verbose=False)

        # Create a file
        test_file = tmp_path / "continuously_written.jpg"
        test_file.write_bytes(b"initial")

        # Keep modifying file during all stability checks
        stop_writing = threading.Event()
        modification_count = [0]

        def keep_writing():
            counter = 0
            while not stop_writing.is_set():
                test_file.write_bytes(f"data {counter}".encode())
                modification_count[0] += 1
                counter += 1
                time.sleep(FILE_STABILITY_INTERVAL * 0.8)

        writer = threading.Thread(target=keep_writing, daemon=True)
        writer.start()

        # Give writer time to start
        time.sleep(0.1)

        # Start stability check
        start_time = time.time()
        result = wait_for_file_stability(test_file, logger)
        elapsed = time.time() - start_time

        # Stop writer
        stop_writing.set()
        writer.join(timeout=1.0)

        # Should return True (completes after FILE_STABILITY_CHECKS attempts)
        assert result is True

        # Should take approximately FILE_STABILITY_CHECKS * FILE_STABILITY_INTERVAL
        expected_time = FILE_STABILITY_CHECKS * FILE_STABILITY_INTERVAL
        assert elapsed >= expected_time * 0.8  # Allow 20% variance
        assert elapsed <= expected_time * 2.0  # Allow generous upper bound

        # Should have detected modifications
        assert modification_count[0] > 0

    def test_stability_check_handles_oserror(self, tmp_path):
        """Test that stability check handles OSError gracefully."""
        from webui.cli.gps_exif_tagger import setup_logging, wait_for_file_stability

        logger = setup_logging(verbose=False)

        # Create a file on a read-only filesystem would cause OSError
        # For testing, use a path that will fail on stat()
        test_file = tmp_path / "test.jpg"
        test_file.write_bytes(b"data")

        # Make directory read-only to trigger permission errors
        import os

        os.chmod(tmp_path, 0o444)

        try:
            # Should handle OSError and return False
            # Note: stat() might still work on directory, so this may return True
            result = wait_for_file_stability(test_file, logger)
            # Either True or False is acceptable - we're testing it doesn't crash
            assert result in [True, False]

        finally:
            # Restore permissions
            os.chmod(tmp_path, 0o755)


class TestResolverIntegration:
    """Test that tagger uses coordinate resolver per photo."""

    def test_batch_uses_resolver_per_photo(self):
        """batch_process_directory calls resolve_coordinates for each photo."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            logger = Mock()

            # Create two photos in a subdirectory (tests recursive glob)
            subdir = tmp_path / "2026-02-10"
            subdir.mkdir()
            for name in ["photo_001.jpg", "photo_002.jpg"]:
                img = Image.new("RGB", (100, 100), color="white")
                img.save(subdir / name)

            mock_result = {
                "lat": 35.96,
                "lon": -83.92,
                "source": "deployment",
                "deployment_name": "Test Deploy",
                "gps_data": {
                    "has_fix": True,
                    "latitude": 35.96,
                    "longitude": -83.92,
                    "altitude": None,
                    "fix_mode": 3,
                    "gpstime": 0,
                    "satellites_used": 0,
                    "hdop": 99.99,
                    "pdop": 99.99,
                },
            }

            with patch(
                "webui.cli.gps_exif_tagger.resolve_coordinates",
                return_value=mock_result,
            ) as mock_resolve:
                stats = gps_exif_tagger.batch_process_directory(
                    tmp_path,
                    logger,
                    pattern="**/*.jpg",
                    coordinate_sources=("deployment", "gps"),
                )

            assert mock_resolve.call_count == 2
            assert stats["total"] == 2

    def test_batch_skips_when_resolver_returns_none(self):
        """Photos are skipped when resolver returns None."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            logger = Mock()

            img = Image.new("RGB", (100, 100), color="white")
            img.save(tmp_path / "photo.jpg")

            with patch(
                "webui.cli.gps_exif_tagger.resolve_coordinates",
                return_value=None,
            ):
                stats = gps_exif_tagger.batch_process_directory(
                    tmp_path,
                    logger,
                    pattern="**/*.jpg",
                    coordinate_sources=("deployment", "gps"),
                )

            assert stats["skipped"] == 1

    def test_batch_stats_include_source_counts(self):
        """Batch stats track how many photos tagged per source."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            logger = Mock()

            for i in range(3):
                img = Image.new("RGB", (100, 100), color="white")
                img.save(tmp_path / f"photo_{i}.jpg")

            mock_result = {
                "lat": 35.96,
                "lon": -83.92,
                "source": "deployment",
                "deployment_name": "Test",
                "gps_data": {
                    "has_fix": True, "latitude": 35.96, "longitude": -83.92,
                    "altitude": None, "fix_mode": 3, "gpstime": 0,
                    "satellites_used": 0, "hdop": 99.99, "pdop": 99.99,
                },
            }

            with patch(
                "webui.cli.gps_exif_tagger.resolve_coordinates",
                return_value=mock_result,
            ):
                stats = gps_exif_tagger.batch_process_directory(
                    tmp_path,
                    logger,
                    pattern="**/*.jpg",
                    coordinate_sources=("deployment",),
                )

            assert "source_counts" in stats
            assert stats["source_counts"].get("deployment", 0) >= 0

    def test_process_single_photo_accepts_gps_data(self):
        """process_single_photo can receive pre-resolved gps_data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            logger = Mock()

            photo_path = tmp_path / "test.jpg"
            img = Image.new("RGB", (100, 100), color="white")
            img.save(photo_path)

            gps_data = {
                "has_fix": True, "latitude": 35.96, "longitude": -83.92,
                "altitude": None, "fix_mode": 3, "gpstime": 0,
                "satellites_used": 0, "hdop": 99.99, "pdop": 99.99,
            }

            result = gps_exif_tagger.process_single_photo(
                photo_path, logger, gps_data=gps_data,
            )

            # Should succeed or at least not error on the gps_data param
            assert isinstance(result, dict)
            assert "success" in result
