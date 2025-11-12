"""
Unit tests for gps_exif_tagger.py CLI functionality
Tests argument parsing, validation, and main entry point
"""

import pytest
import sys
import argparse
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, call
from io import StringIO

# Import the module under test
import gps_exif_tagger


class TestCLIArgumentParsing:
    """Test CLI argument parsing and validation."""

    def test_default_arguments(self):
        """Test that default arguments are correctly set."""
        with patch('sys.argv', ['gps_exif_tagger.py']):
            with patch.object(gps_exif_tagger, 'batch_process_directory', return_value={'errors': 0}) as mock_batch:
                with patch.object(gps_exif_tagger, 'setup_logging', return_value=Mock()):
                    with patch.object(gps_exif_tagger, 'get_hardware_config', return_value={'gps_enabled': True}):
                        with patch.object(gps_exif_tagger, 'get_gps_data_from_controls', return_value={'has_fix': True}):
                            with patch('pathlib.Path.exists', return_value=True):
                                # Should run without raising (no sys.exit when errors=0)
                                gps_exif_tagger.main()

                                # Verify batch mode was called (default)
                                assert mock_batch.called

    def test_watch_mode_argument(self):
        """Test --watch flag enables immediate mode."""
        test_args = ['gps_exif_tagger.py', '--watch', '--directory', '/tmp/test']

        with patch('sys.argv', test_args):
            with patch.object(gps_exif_tagger, 'watch_directory') as mock_watch:
                with patch.object(gps_exif_tagger, 'setup_logging', return_value=Mock()):
                    with patch.object(gps_exif_tagger, 'get_hardware_config', return_value={'gps_enabled': True}):
                        with patch.object(gps_exif_tagger, 'get_gps_data_from_controls', return_value={'has_fix': True}):
                            with patch('pathlib.Path.exists', return_value=True):
                                # Mock KeyboardInterrupt to exit watch loop
                                mock_watch.side_effect = KeyboardInterrupt

                                with pytest.raises(KeyboardInterrupt):
                                    gps_exif_tagger.main()

    def test_batch_mode_argument(self):
        """Test --mode batch runs batch processing."""
        test_args = ['gps_exif_tagger.py', '--mode', 'batch', '--directory', '/tmp/test']

        with patch('sys.argv', test_args):
            with patch.object(gps_exif_tagger, 'batch_process_directory', return_value={'errors': 0}) as mock_batch:
                with patch.object(gps_exif_tagger, 'setup_logging', return_value=Mock()):
                    with patch.object(gps_exif_tagger, 'get_hardware_config', return_value={'gps_enabled': True}):
                        with patch.object(gps_exif_tagger, 'get_gps_data_from_controls', return_value={'has_fix': True}):
                            with patch('pathlib.Path.exists', return_value=True):
                                gps_exif_tagger.main()

                                # Verify batch was called
                                assert mock_batch.called

    def test_immediate_mode_argument(self):
        """Test --mode immediate runs watch mode."""
        test_args = ['gps_exif_tagger.py', '--mode', 'immediate', '--directory', '/tmp/test']

        with patch('sys.argv', test_args):
            with patch.object(gps_exif_tagger, 'watch_directory') as mock_watch:
                with patch.object(gps_exif_tagger, 'setup_logging', return_value=Mock()):
                    with patch.object(gps_exif_tagger, 'get_hardware_config', return_value={'gps_enabled': True}):
                        with patch.object(gps_exif_tagger, 'get_gps_data_from_controls', return_value={'has_fix': True}):
                            with patch('pathlib.Path.exists', return_value=True):
                                mock_watch.side_effect = KeyboardInterrupt

                                with pytest.raises(KeyboardInterrupt):
                                    gps_exif_tagger.main()

                                assert mock_watch.called

    def test_directory_argument(self):
        """Test --directory sets custom photo directory."""
        custom_dir = '/custom/photo/dir'
        test_args = ['gps_exif_tagger.py', '--directory', custom_dir]

        with patch('sys.argv', test_args):
            with patch.object(gps_exif_tagger, 'batch_process_directory', return_value={'errors': 0}) as mock_batch:
                with patch.object(gps_exif_tagger, 'setup_logging', return_value=Mock()):
                    with patch.object(gps_exif_tagger, 'get_hardware_config', return_value={'gps_enabled': True}):
                        with patch.object(gps_exif_tagger, 'get_gps_data_from_controls', return_value={'has_fix': True}):
                            with patch('pathlib.Path.exists', return_value=True):
                                gps_exif_tagger.main()

                                # Check first argument (directory) passed to batch_process_directory
                                call_args = mock_batch.call_args[0]
                                assert str(call_args[0]) == custom_dir

    def test_pattern_argument(self):
        """Test --pattern sets file matching pattern."""
        test_args = ['gps_exif_tagger.py', '--pattern', '*.jpeg']

        with patch('sys.argv', test_args):
            with patch.object(gps_exif_tagger, 'batch_process_directory', return_value={'errors': 0}) as mock_batch:
                with patch.object(gps_exif_tagger, 'setup_logging', return_value=Mock()):
                    with patch.object(gps_exif_tagger, 'get_hardware_config', return_value={'gps_enabled': True}):
                        with patch.object(gps_exif_tagger, 'get_gps_data_from_controls', return_value={'has_fix': True}):
                            with patch('pathlib.Path.exists', return_value=True):
                                gps_exif_tagger.main()

                                # Check pattern kwarg
                                assert mock_batch.call_args[1]['pattern'] == '*.jpeg'

    def test_interval_argument(self):
        """Test --interval sets watch mode polling interval."""
        test_args = ['gps_exif_tagger.py', '--watch', '--interval', '30']

        with patch('sys.argv', test_args):
            with patch.object(gps_exif_tagger, 'watch_directory') as mock_watch:
                with patch.object(gps_exif_tagger, 'setup_logging', return_value=Mock()):
                    with patch.object(gps_exif_tagger, 'get_hardware_config', return_value={'gps_enabled': True}):
                        with patch.object(gps_exif_tagger, 'get_gps_data_from_controls', return_value={'has_fix': True}):
                            with patch('pathlib.Path.exists', return_value=True):
                                mock_watch.side_effect = KeyboardInterrupt

                                with pytest.raises(KeyboardInterrupt):
                                    gps_exif_tagger.main()

                                # Check interval kwarg
                                assert mock_watch.call_args[1]['interval'] == 30

    def test_dry_run_argument(self):
        """Test --dry-run flag enables test mode."""
        test_args = ['gps_exif_tagger.py', '--dry-run']

        with patch('sys.argv', test_args):
            with patch.object(gps_exif_tagger, 'batch_process_directory', return_value={'errors': 0}) as mock_batch:
                with patch.object(gps_exif_tagger, 'setup_logging', return_value=Mock()):
                    with patch.object(gps_exif_tagger, 'get_hardware_config', return_value={'gps_enabled': True}):
                        with patch.object(gps_exif_tagger, 'get_gps_data_from_controls', return_value={'has_fix': True}):
                            with patch('pathlib.Path.exists', return_value=True):
                                gps_exif_tagger.main()

                                assert mock_batch.call_args[1]['dry_run'] is True

    def test_backup_argument(self):
        """Test --backup flag enables backup creation."""
        test_args = ['gps_exif_tagger.py', '--backup']

        with patch('sys.argv', test_args):
            with patch.object(gps_exif_tagger, 'batch_process_directory', return_value={'errors': 0}) as mock_batch:
                with patch.object(gps_exif_tagger, 'setup_logging', return_value=Mock()):
                    with patch.object(gps_exif_tagger, 'get_hardware_config', return_value={'gps_enabled': True}):
                        with patch.object(gps_exif_tagger, 'get_gps_data_from_controls', return_value={'has_fix': True}):
                            with patch('pathlib.Path.exists', return_value=True):
                                gps_exif_tagger.main()

                                assert mock_batch.call_args[1]['backup'] is True

    def test_force_argument(self):
        """Test --force flag enables re-tagging."""
        test_args = ['gps_exif_tagger.py', '--force']

        with patch('sys.argv', test_args):
            with patch.object(gps_exif_tagger, 'batch_process_directory', return_value={'errors': 0}) as mock_batch:
                with patch.object(gps_exif_tagger, 'setup_logging', return_value=Mock()):
                    with patch.object(gps_exif_tagger, 'get_hardware_config', return_value={'gps_enabled': True}):
                        with patch.object(gps_exif_tagger, 'get_gps_data_from_controls', return_value={'has_fix': True}):
                            with patch('pathlib.Path.exists', return_value=True):
                                gps_exif_tagger.main()

                                assert mock_batch.call_args[1]['force'] is True

    def test_verbose_argument(self):
        """Test --verbose flag enables debug logging."""
        test_args = ['gps_exif_tagger.py', '--verbose']

        with patch('sys.argv', test_args):
            with patch.object(gps_exif_tagger, 'batch_process_directory', return_value={'errors': 0}):
                with patch.object(gps_exif_tagger, 'setup_logging', return_value=Mock()) as mock_logging:
                    with patch.object(gps_exif_tagger, 'get_hardware_config', return_value={'gps_enabled': True}):
                        with patch.object(gps_exif_tagger, 'get_gps_data_from_controls', return_value={'has_fix': True}):
                            with patch('pathlib.Path.exists', return_value=True):
                                gps_exif_tagger.main()

                                # Verify setup_logging was called with verbose=True
                                mock_logging.assert_called_once_with(True)


class TestCLIValidation:
    """Test CLI input validation and error handling."""

    def test_nonexistent_directory_exits_with_error(self):
        """Test that nonexistent directory causes exit with error code 1."""
        test_args = ['gps_exif_tagger.py', '--directory', '/nonexistent/path']

        with patch('sys.argv', test_args):
            with patch.object(gps_exif_tagger, 'setup_logging', return_value=Mock()):
                with patch('pathlib.Path.exists', return_value=False):
                    with pytest.raises(SystemExit) as exc_info:
                        gps_exif_tagger.main()

                    assert exc_info.value.code == 1

    def test_gps_disabled_warning(self):
        """Test warning when GPS is disabled in hardware config."""
        test_args = ['gps_exif_tagger.py']

        with patch('sys.argv', test_args):
            mock_logger = Mock()
            with patch.object(gps_exif_tagger, 'setup_logging', return_value=mock_logger):
                with patch.object(gps_exif_tagger, 'get_hardware_config', return_value={'gps_enabled': False}):
                    with patch.object(gps_exif_tagger, 'get_gps_data_from_controls', return_value={'has_fix': False}):
                        with patch.object(gps_exif_tagger, 'batch_process_directory', return_value={'errors': 0}):
                            with patch('pathlib.Path.exists', return_value=True):
                                gps_exif_tagger.main()

                                # Check warning was logged
                                warning_calls = [call for call in mock_logger.warning.call_args_list
                                               if 'GPS is disabled' in str(call)]
                                assert len(warning_calls) > 0

    def test_no_gps_fix_warning(self):
        """Test warning when GPS has no fix."""
        test_args = ['gps_exif_tagger.py']

        with patch('sys.argv', test_args):
            mock_logger = Mock()
            with patch.object(gps_exif_tagger, 'setup_logging', return_value=mock_logger):
                with patch.object(gps_exif_tagger, 'get_hardware_config', return_value={'gps_enabled': True}):
                    with patch.object(gps_exif_tagger, 'get_gps_data_from_controls', return_value={'has_fix': False}):
                        with patch.object(gps_exif_tagger, 'batch_process_directory', return_value={'errors': 0}):
                            with patch('pathlib.Path.exists', return_value=True):
                                gps_exif_tagger.main()

                                # Check warning was logged
                                warning_calls = [call for call in mock_logger.warning.call_args_list
                                               if 'No GPS fix' in str(call)]
                                assert len(warning_calls) > 0

    def test_batch_errors_exit_with_error_code(self):
        """Test that batch processing errors cause exit with code 1."""
        test_args = ['gps_exif_tagger.py']

        with patch('sys.argv', test_args):
            with patch.object(gps_exif_tagger, 'setup_logging', return_value=Mock()):
                with patch.object(gps_exif_tagger, 'get_hardware_config', return_value={'gps_enabled': True}):
                    with patch.object(gps_exif_tagger, 'get_gps_data_from_controls', return_value={'has_fix': True}):
                        with patch.object(gps_exif_tagger, 'batch_process_directory', return_value={'errors': 5}):
                            with patch('pathlib.Path.exists', return_value=True):
                                with pytest.raises(SystemExit) as exc_info:
                                    gps_exif_tagger.main()

                                assert exc_info.value.code == 1

    def test_fatal_exception_exits_with_error_code(self):
        """Test that hardware config errors are logged as warnings."""
        test_args = ['gps_exif_tagger.py']

        with patch('sys.argv', test_args):
            mock_logger = Mock()
            with patch.object(gps_exif_tagger, 'setup_logging', return_value=mock_logger):
                with patch.object(gps_exif_tagger, 'get_hardware_config', side_effect=Exception("Fatal error")):
                    with patch.object(gps_exif_tagger, 'get_gps_data_from_controls', return_value={'has_fix': False}):
                        with patch('pathlib.Path.exists', return_value=True):
                            with patch.object(gps_exif_tagger, 'batch_process_directory', return_value={'errors': 0}):
                                # Should log warning but not exit
                                gps_exif_tagger.main()

                                # Verify warning was logged
                                assert any('hardware config' in str(call).lower() for call in mock_logger.warning.call_args_list)

    def test_fatal_exception_with_verbose_shows_traceback(self):
        """Test that --verbose shows full traceback on fatal errors."""
        test_args = ['gps_exif_tagger.py', '--verbose']

        with patch('sys.argv', test_args):
            mock_logger = Mock()
            with patch.object(gps_exif_tagger, 'setup_logging', return_value=mock_logger):
                with patch('pathlib.Path.exists', return_value=True):
                    with patch.object(gps_exif_tagger, 'batch_process_directory', side_effect=RuntimeError("Test error")):
                        with patch.object(gps_exif_tagger, 'get_hardware_config', return_value={'gps_enabled': True}):
                            with patch.object(gps_exif_tagger, 'get_gps_data_from_controls', return_value={'has_fix': True}):
                                with pytest.raises(SystemExit):
                                    gps_exif_tagger.main()

                                # Verify error was logged
                                assert mock_logger.error.called

    def test_hardware_config_read_error_continues(self):
        """Test that hardware config read errors don't stop execution."""
        test_args = ['gps_exif_tagger.py']

        with patch('sys.argv', test_args):
            mock_logger = Mock()
            with patch.object(gps_exif_tagger, 'setup_logging', return_value=mock_logger):
                with patch.object(gps_exif_tagger, 'get_hardware_config', side_effect=Exception("Config error")):
                    with patch.object(gps_exif_tagger, 'get_gps_data_from_controls', return_value={'has_fix': True}):
                        with patch.object(gps_exif_tagger, 'batch_process_directory', return_value={'errors': 0}):
                            with patch('pathlib.Path.exists', return_value=True):
                                gps_exif_tagger.main()

                                # Should log warning but continue
                                warning_calls = [call for call in mock_logger.warning.call_args_list
                                               if 'Could not read hardware config' in str(call)]
                                assert len(warning_calls) > 0

    def test_gps_data_read_error_continues(self):
        """Test that GPS data read errors don't stop execution."""
        test_args = ['gps_exif_tagger.py']

        with patch('sys.argv', test_args):
            mock_logger = Mock()
            with patch.object(gps_exif_tagger, 'setup_logging', return_value=mock_logger):
                with patch.object(gps_exif_tagger, 'get_hardware_config', return_value={'gps_enabled': True}):
                    with patch.object(gps_exif_tagger, 'get_gps_data_from_controls', side_effect=Exception("GPS error")):
                        with patch.object(gps_exif_tagger, 'batch_process_directory', return_value={'errors': 0}):
                            with patch('pathlib.Path.exists', return_value=True):
                                gps_exif_tagger.main()

                                # Should log warning but continue
                                warning_calls = [call for call in mock_logger.warning.call_args_list
                                               if 'Could not read GPS data' in str(call)]
                                assert len(warning_calls) > 0


class TestLogging:
    """Test logging setup and output."""

    def test_setup_logging_default_level(self):
        """Test that default logging level is INFO."""
        logger = gps_exif_tagger.setup_logging(verbose=False)
        assert logger.level == gps_exif_tagger.logging.INFO

    def test_setup_logging_verbose_level(self):
        """Test that verbose enables DEBUG level."""
        logger = gps_exif_tagger.setup_logging(verbose=True)
        assert logger.level == gps_exif_tagger.logging.DEBUG

    def test_startup_messages_logged(self):
        """Test that startup messages are logged."""
        test_args = ['gps_exif_tagger.py']

        with patch('sys.argv', test_args):
            mock_logger = Mock()
            with patch.object(gps_exif_tagger, 'setup_logging', return_value=mock_logger):
                with patch.object(gps_exif_tagger, 'get_hardware_config', return_value={'gps_enabled': True}):
                    with patch.object(gps_exif_tagger, 'get_gps_data_from_controls', return_value={'has_fix': True}):
                        with patch.object(gps_exif_tagger, 'batch_process_directory', return_value={'errors': 0}):
                            with patch('pathlib.Path.exists', return_value=True):
                                gps_exif_tagger.main()

                                # Check that info messages were logged
                                info_calls = mock_logger.info.call_args_list
                                assert any('GPS EXIF Tagger starting' in str(call) for call in info_calls)
                                assert any('Mode:' in str(call) for call in info_calls)
                                assert any('Directory:' in str(call) for call in info_calls)
