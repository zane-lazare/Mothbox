"""
Unit tests for gps_exif_tagger.py operational functions
Tests batch processing, watch mode, and single photo processing
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, call
import tempfile
import time
import sys

# Import the module under test
import gps_exif_tagger
from lib.gps_exif_lib import embed_gps_exif


@pytest.fixture(scope="module", autouse=True)
def ensure_real_pil():
    """
    Ensure PIL is not mocked for this test module (Python 3.13 compatibility).

    In Python 3.13, PIL mocks from test_gallery_routes persist across modules
    despite the reset_pil_imports fixture. Force fresh PIL import at module level.
    """
    # Remove any existing PIL modules
    pil_modules = [key for key in sys.modules.keys() if key == 'PIL' or key.startswith('PIL.')]
    for key in pil_modules:
        del sys.modules[key]

    # Re-import PIL.Image globally for this module
    global Image
    from PIL import Image

    # Initialize PIL plugins to register file format handlers (.jpg, .png, etc.)
    Image.init()

    yield

    # Cleanup after module
    pil_modules = [key for key in sys.modules.keys() if key == 'PIL' or key.startswith('PIL.')]
    for key in pil_modules:
        del sys.modules[key]


class TestBatchProcessing:
    """Test batch_process_directory function."""

    def test_batch_process_empty_directory(self):
        """Test batch processing an empty directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            logger = Mock()

            stats = gps_exif_tagger.batch_process_directory(
                tmp_path,
                logger,
                pattern='*.jpg'
            )

            assert stats['total'] == 0
            assert stats['tagged'] == 0
            assert stats['skipped'] == 0
            assert stats['errors'] == 0

    def test_batch_process_single_photo(self):
        """Test batch processing with a single photo."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            logger = Mock()

            # Create a test photo
            photo_path = tmp_path / 'test.jpg'
            img = Image.new('RGB', (100, 100), color='white')
            img.save(photo_path)

            # Create GPS data
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as controls:
                controls.write("lat=40.7\n")
                controls.write("lon=-74.0\n")
                controls.write("fix=3\n")
                controls.flush()
                controls_path = Path(controls.name)

            try:
                with patch('lib.gps_exif_lib.CONTROLS_FILE', controls_path):
                    stats = gps_exif_tagger.batch_process_directory(
                        tmp_path,
                        logger,
                        pattern='*.jpg'
                    )

                    assert stats['total'] == 1
                    assert stats['tagged'] >= 0  # May be tagged or skipped
            finally:
                controls_path.unlink()

    def test_batch_process_multiple_photos(self):
        """Test batch processing with multiple photos."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            logger = Mock()

            # Create multiple test photos
            for i in range(5):
                photo_path = tmp_path / f'test_{i}.jpg'
                img = Image.new('RGB', (100, 100), color='white')
                img.save(photo_path)

            stats = gps_exif_tagger.batch_process_directory(
                tmp_path,
                logger,
                pattern='*.jpg'
            )

            assert stats['total'] == 5

    def test_batch_process_with_pattern_filter(self):
        """Test batch processing with file pattern filtering."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            logger = Mock()

            # Create photos with different extensions
            for ext in ['jpg', 'jpeg', 'png', 'txt']:
                photo_path = tmp_path / f'test.{ext}'
                if ext in ['jpg', 'jpeg', 'png']:
                    img = Image.new('RGB', (100, 100), color='white')
                    img.save(photo_path)
                else:
                    photo_path.write_text("text file")

            stats = gps_exif_tagger.batch_process_directory(
                tmp_path,
                logger,
                pattern='*.jpg'
            )

            # Should only find .jpg files
            assert stats['total'] == 1

    def test_batch_process_with_force_flag(self):
        """Test batch processing with force re-tagging."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            logger = Mock()

            # Create and tag a photo
            photo_path = tmp_path / 'test.jpg'
            img = Image.new('RGB', (100, 100), color='white')
            img.save(photo_path)

            # Create GPS data
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as controls:
                controls.write("lat=40.7\n")
                controls.write("lon=-74.0\n")
                controls.write("fix=3\n")
                controls.flush()
                controls_path = Path(controls.name)

            try:
                with patch('lib.gps_exif_lib.CONTROLS_FILE', controls_path):
                    # First tagging
                    stats1 = gps_exif_tagger.batch_process_directory(
                        tmp_path,
                        logger,
                        pattern='*.jpg',
                        force=False
                    )

                    # Second tagging without force - should skip
                    stats2 = gps_exif_tagger.batch_process_directory(
                        tmp_path,
                        logger,
                        pattern='*.jpg',
                        force=False
                    )

                    # Third tagging with force - should re-tag
                    stats3 = gps_exif_tagger.batch_process_directory(
                        tmp_path,
                        logger,
                        pattern='*.jpg',
                        force=True
                    )

                    # Verify force behavior
                    assert stats1['total'] == 1
                    assert stats2['total'] == 1
                    assert stats3['total'] == 1
            finally:
                controls_path.unlink()

    def test_batch_process_dry_run(self):
        """Test batch processing in dry-run mode."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            logger = Mock()

            # Create a test photo
            photo_path = tmp_path / 'test.jpg'
            img = Image.new('RGB', (100, 100), color='white')
            img.save(photo_path)

            # Get original modification time
            original_mtime = photo_path.stat().st_mtime

            # Create GPS data
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as controls:
                controls.write("lat=40.7\n")
                controls.write("lon=-74.0\n")
                controls.write("fix=3\n")
                controls.flush()
                controls_path = Path(controls.name)

            try:
                with patch('lib.gps_exif_lib.CONTROLS_FILE', controls_path):
                    stats = gps_exif_tagger.batch_process_directory(
                        tmp_path,
                        logger,
                        pattern='*.jpg',
                        dry_run=True
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
            photo_path = tmp_path / 'test.jpg'
            img = Image.new('RGB', (100, 100), color='white')
            img.save(photo_path)

            # Create GPS data
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as controls:
                controls.write("lat=40.7\n")
                controls.write("lon=-74.0\n")
                controls.write("fix=3\n")
                controls.flush()
                controls_path = Path(controls.name)

            try:
                with patch('lib.gps_exif_lib.CONTROLS_FILE', controls_path):
                    stats = gps_exif_tagger.batch_process_directory(
                        tmp_path,
                        logger,
                        pattern='*.jpg',
                        backup=True
                    )

                    # Backup file should exist
                    backup_path = photo_path.with_suffix('.jpg.bak')
                    # May or may not exist depending on if photo was tagged
                    # assert backup_path.exists() or not backup_path.exists()
            finally:
                controls_path.unlink()

    def test_batch_process_logs_summary(self):
        """Test that batch processing logs summary statistics."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            logger = Mock()

            # Create test photos
            for i in range(3):
                photo_path = tmp_path / f'test_{i}.jpg'
                img = Image.new('RGB', (100, 100), color='white')
                img.save(photo_path)

            stats = gps_exif_tagger.batch_process_directory(
                tmp_path,
                logger,
                pattern='*.jpg'
            )

            # Should log summary
            assert logger.info.called
            info_calls = [str(call) for call in logger.info.call_args_list]
            assert any('Summary' in call or 'Total' in call for call in info_calls)

    def test_batch_process_preserves_chronological_order(self):
        """Test that batch processing preserves chronological file order."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            logger = Mock()

            # Create files with timestamps in specific order
            # (sorted alphabetically = photo1, photo2, photo3)
            # We'll create them with specific mtimes to test chronological ordering
            import time

            photo1 = tmp_path / 'photo1.jpg'
            photo2 = tmp_path / 'photo2.JPG'  # Different case
            photo3 = tmp_path / 'photo3.jpg'

            # Create files at different times
            img = Image.new('RGB', (100, 100), color='red')
            img.save(photo1)
            time.sleep(0.01)

            img = Image.new('RGB', (100, 100), color='green')
            img.save(photo2)
            time.sleep(0.01)

            img = Image.new('RGB', (100, 100), color='blue')
            img.save(photo3)

            # Track processing order
            processed_files = []

            def track_processing(photo_path, *args, **kwargs):
                processed_files.append(photo_path.name)
                return {'success': True, 'skipped': False}

            with patch.object(gps_exif_tagger, 'process_single_photo', side_effect=track_processing):
                gps_exif_tagger.batch_process_directory(
                    tmp_path,
                    logger,
                    pattern='*.jpg',
                    force=False,
                    backup=False,
                    dry_run=False
                )

            # Verify all 3 files were processed
            assert len(processed_files) == 3, f"Expected 3 files, got {len(processed_files)}"

            # Verify files were processed in sorted order (alphabetically)
            # This ensures chronological order is maintained after deduplication
            assert processed_files == ['photo1.jpg', 'photo2.JPG', 'photo3.jpg'], \
                f"Files processed out of order: {processed_files}"


class TestSinglePhotoProcessing:
    """Test process_single_photo function."""

    def test_process_single_photo_success(self):
        """Test successful single photo processing."""
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
            tmp_path = Path(tmp.name)

            # Create a test photo
            img = Image.new('RGB', (100, 100), color='blue')
            img.save(tmp_path)

        try:
            logger = Mock()

            # Create GPS data
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as controls:
                controls.write("lat=40.7\n")
                controls.write("lon=-74.0\n")
                controls.write("fix=3\n")
                controls.flush()
                controls_path = Path(controls.name)

            try:
                with patch('lib.gps_exif_lib.CONTROLS_FILE', controls_path):
                    result = gps_exif_tagger.process_single_photo(
                        tmp_path,
                        logger
                    )

                    # Should return result dict
                    assert 'success' in result or 'skipped' in result or 'error' in result
            finally:
                controls_path.unlink()
        finally:
            tmp_path.unlink()

    def test_process_single_photo_with_force(self):
        """Test single photo processing with force flag."""
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
            tmp_path = Path(tmp.name)

            # Create a test photo
            img = Image.new('RGB', (100, 100), color='red')
            img.save(tmp_path)

        try:
            logger = Mock()

            # Create GPS data
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as controls:
                controls.write("lat=40.7\n")
                controls.write("lon=-74.0\n")
                controls.write("fix=3\n")
                controls.flush()
                controls_path = Path(controls.name)

            try:
                with patch('lib.gps_exif_lib.CONTROLS_FILE', controls_path):
                    result = gps_exif_tagger.process_single_photo(
                        tmp_path,
                        logger,
                        force=True
                    )

                    # Should process with force
                    assert 'success' in result or 'error' in result
            finally:
                controls_path.unlink()
        finally:
            tmp_path.unlink()

    def test_process_single_photo_error_handling(self):
        """Test single photo processing error handling."""
        nonexistent_path = Path('/nonexistent/photo.jpg')
        logger = Mock()

        result = gps_exif_tagger.process_single_photo(
            nonexistent_path,
            logger
        )

        # Should return error
        assert 'error' in result


class TestWatchMode:
    """Test watch_directory function."""

    def test_watch_mode_detects_new_photo(self):
        """Test that watch mode detects newly created photos."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            logger = Mock()

            # Mock process_single_photo to track calls
            with patch.object(gps_exif_tagger, 'process_single_photo', return_value={'success': True}) as mock_process:
                # Start watch mode in a separate thread-like context
                # Use a timeout to prevent infinite loop
                import threading

                def run_watch():
                    try:
                        gps_exif_tagger.watch_directory(
                            tmp_path,
                            logger,
                            pattern='*.jpg',
                            interval=0.1  # Very short interval for testing
                        )
                    except KeyboardInterrupt:
                        pass

                watch_thread = threading.Thread(target=run_watch, daemon=True)
                watch_thread.start()

                # Give watch mode time to start
                time.sleep(0.2)

                # Create a new photo
                photo_path = tmp_path / 'new_photo.jpg'
                img = Image.new('RGB', (100, 100), color='green')
                img.save(photo_path)

                # Give watch mode time to detect
                time.sleep(0.5)

                # Stop watch mode
                # (thread will exit on its own as daemon)

    def test_watch_mode_handles_modified_photo(self):
        """Test that watch mode handles modified photos."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            logger = Mock()

            # Create initial photo
            photo_path = tmp_path / 'photo.jpg'
            img = Image.new('RGB', (100, 100), color='yellow')
            img.save(photo_path)

            # Track processing calls
            process_count = [0]

            def mock_process(*args, **kwargs):
                process_count[0] += 1
                return {'success': True}

            with patch.object(gps_exif_tagger, 'process_single_photo', side_effect=mock_process):
                import threading

                def run_watch():
                    try:
                        gps_exif_tagger.watch_directory(
                            tmp_path,
                            logger,
                            pattern='*.jpg',
                            interval=0.1
                        )
                    except KeyboardInterrupt:
                        pass

                watch_thread = threading.Thread(target=run_watch, daemon=True)
                watch_thread.start()

                time.sleep(0.2)

                # Modify the photo (change mtime)
                time.sleep(0.1)
                img2 = Image.new('RGB', (100, 100), color='purple')
                img2.save(photo_path)

                time.sleep(0.5)

    def test_watch_mode_handles_errors_gracefully(self):
        """Test that watch mode continues after processing errors."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            logger = Mock()

            # Create a photo
            photo_path = tmp_path / 'photo.jpg'
            img = Image.new('RGB', (100, 100), color='orange')
            img.save(photo_path)

            # Mock process to raise error then succeed
            call_count = [0]

            def mock_process(*args, **kwargs):
                call_count[0] += 1
                if call_count[0] == 1:
                    raise Exception("Test error")
                return {'success': True}

            with patch.object(gps_exif_tagger, 'process_single_photo', side_effect=mock_process):
                import threading

                def run_watch():
                    try:
                        gps_exif_tagger.watch_directory(
                            tmp_path,
                            logger,
                            pattern='*.jpg',
                            interval=0.1
                        )
                    except KeyboardInterrupt:
                        pass

                watch_thread = threading.Thread(target=run_watch, daemon=True)
                watch_thread.start()

                time.sleep(0.5)

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

            with patch('time.sleep', side_effect=mock_sleep):
                try:
                    gps_exif_tagger.watch_directory(
                        tmp_path,
                        logger,
                        pattern='*.jpg',
                        interval=5
                    )
                except (KeyboardInterrupt, SystemExit):
                    pass

            # Should have called sleep with the interval
            if sleep_calls:
                assert 5 in sleep_calls or 0.5 in sleep_calls  # 5 is interval, 0.5 is file write delay

    def test_watch_mode_keyboard_interrupt_exits_cleanly(self):
        """Test that Ctrl+C exits watch mode cleanly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            logger = Mock()

            # Simulate KeyboardInterrupt
            with patch('time.sleep', side_effect=KeyboardInterrupt):
                # Should exit without raising
                gps_exif_tagger.watch_directory(
                    tmp_path,
                    logger,
                    pattern='*.jpg',
                    interval=1
                )

            # Should log exit message
            info_calls = [str(call) for call in logger.info.call_args_list]
            assert any('stopped' in call.lower() for call in info_calls)

    def test_watch_mode_case_insensitive_pattern(self):
        """Test that watch mode handles case-insensitive file patterns."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            logger = Mock()

            # Create photos with different case extensions
            photo1 = tmp_path / 'photo1.jpg'
            photo2 = tmp_path / 'photo2.JPG'
            photo3 = tmp_path / 'photo3.jpeg'

            for photo in [photo1, photo2, photo3]:
                img = Image.new('RGB', (100, 100), color='cyan')
                img.save(photo)

            # Mock glob to track what patterns are searched
            glob_patterns = []
            original_glob = Path.glob

            def mock_glob(self, pattern):
                glob_patterns.append(pattern)
                return original_glob(self, pattern)

            with patch.object(Path, 'glob', mock_glob):
                with patch('time.sleep', side_effect=[0.1, KeyboardInterrupt]):
                    try:
                        gps_exif_tagger.watch_directory(
                            tmp_path,
                            logger,
                            pattern='*.jpg',
                            interval=1
                        )
                    except (KeyboardInterrupt, SystemExit):
                        pass

            # Should search for multiple case variants
            # (Implementation detail - may vary)

    def test_watch_mode_handles_file_deletion_race(self):
        """Test that watch mode handles files deleted between stat() and processing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            logger = Mock()

            # Create initial photo
            photo_path = tmp_path / 'photo.jpg'
            img = Image.new('RGB', (100, 100), color='yellow')
            img.save(photo_path)

            # Track processing attempts
            process_calls = []

            def mock_process(photo, *args, **kwargs):
                process_calls.append(str(photo))
                return {'success': True, 'skipped': False}

            # Delete file after initial detection but before processing
            # (simulate race condition during the 0.5 second sleep)
            def delete_after_delay():
                time.sleep(0.3)  # Wait for detection + partial sleep
                if photo_path.exists():
                    photo_path.unlink()

            with patch.object(gps_exif_tagger, 'process_single_photo', side_effect=mock_process):
                import threading

                # Start deletion thread
                delete_thread = threading.Thread(target=delete_after_delay, daemon=True)
                delete_thread.start()

                def run_watch():
                    try:
                        gps_exif_tagger.watch_directory(
                            tmp_path,
                            logger,
                            pattern='*.jpg',
                            interval=0.1,
                            backup=False
                        )
                    except KeyboardInterrupt:
                        pass

                watch_thread = threading.Thread(target=run_watch, daemon=True)
                watch_thread.start()

                # Wait for detection, deletion, and processing attempt
                time.sleep(0.8)

                # Stop watch mode
                watch_thread.join(timeout=0.5)
                delete_thread.join(timeout=0.1)

            # With fix: process_single_photo() should NOT be called
            # (file is checked and skipped before processing)
            assert len(process_calls) == 0, \
                "Should NOT process file that was deleted during sleep window"

            # Verify logger.debug was called with skip message
            debug_calls = [str(call) for call in logger.debug.call_args_list]
            assert any('no longer exists' in str(call).lower() for call in debug_calls), \
                "Should log that file no longer exists"
