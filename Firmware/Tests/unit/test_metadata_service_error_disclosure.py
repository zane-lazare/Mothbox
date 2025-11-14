"""
Test information disclosure prevention in MetadataService error messages.

This module verifies that error messages don't expose sensitive information
like full file paths or exception details to API consumers.

Original Issue:
- Error messages exposed full file paths and exception details
- Contradicts security approach used in gallery.py routes

Solution:
- Log full error details server-side only
- Return generic error messages to API consumers
- Follows CodeQL security requirements

Related to: Issue #100 - Metadata API implementation
"""

import logging
from pathlib import Path
from unittest.mock import patch

import pytest
from PIL import Image

from webui.backend.services.metadata_service import MetadataService


@pytest.fixture
def service():
    """Create MetadataService instance"""
    return MetadataService()


@pytest.fixture
def sample_photo_path(tmp_path):
    """Create a sample photo file"""
    photo_path = tmp_path / "test_photo.jpg"
    img = Image.new('RGB', (100, 100), color='red')
    img.save(photo_path, 'JPEG')
    return photo_path


def test_image_open_failure_does_not_expose_path(service, sample_photo_path, caplog):
    """
    Test that image open failure doesn't expose file path to user.

    Full path should be logged server-side but not returned in error message.
    """
    with caplog.at_level(logging.ERROR):
        with patch('webui.backend.services.metadata_service.Image.open') as mock_open:
            # Simulate image open failure with detailed exception
            mock_open.side_effect = OSError("/sensitive/path/to/image.jpg: No such file")

            metadata = service.get_photo_metadata(sample_photo_path)

            # Verify error field doesn't contain path or exception details
            assert 'error' in metadata
            assert metadata['error'] == "Failed to open image"
            assert str(sample_photo_path) not in metadata['error']
            assert "/sensitive/path" not in metadata['error']
            assert "No such file" not in metadata['error']

            # Verify full details are logged server-side
            assert len(caplog.records) == 1
            assert caplog.records[0].levelname == "ERROR"
            assert str(sample_photo_path) in caplog.records[0].message


def test_permission_error_does_not_expose_path(service, sample_photo_path, caplog):
    """
    Test that PermissionError doesn't expose file path to user.

    Full path should be logged but generic message returned.
    """
    with caplog.at_level(logging.ERROR):
        # Simulate permission denied by making file stat() fail
        with patch.object(Path, 'stat') as mock_stat:
            mock_stat.side_effect = PermissionError("Permission denied accessing /secret/photo.jpg")

            metadata = service.get_photo_metadata(sample_photo_path)

            # Verify error field doesn't contain path
            assert 'error' in metadata
            assert metadata['error'] == "Permission denied"
            assert str(sample_photo_path) not in metadata['error']
            assert "/secret/photo.jpg" not in metadata['error']

            # Verify full details are logged server-side
            assert len(caplog.records) == 1
            assert caplog.records[0].levelname == "ERROR"
            assert str(sample_photo_path) in caplog.records[0].message


def test_unexpected_error_does_not_expose_details(service, sample_photo_path, caplog):
    """
    Test that unexpected exceptions don't expose internal details to user.

    Exception details should be logged but generic message returned.
    """
    with caplog.at_level(logging.ERROR):
        # Simulate unexpected error by making exists() raise
        with patch.object(Path, 'exists') as mock_exists:
            mock_exists.side_effect = RuntimeError("Internal database connection failed at 192.168.1.100:5432")

            metadata = service.get_photo_metadata(sample_photo_path)

            # Verify error field doesn't contain exception details
            assert 'error' in metadata
            assert metadata['error'] == "Failed to read metadata"
            assert "RuntimeError" not in metadata['error']
            assert "database connection" not in metadata['error']
            assert "192.168.1.100" not in metadata['error']

            # Verify full details are logged server-side
            assert len(caplog.records) == 1
            assert caplog.records[0].levelname == "ERROR"
            assert str(sample_photo_path) in caplog.records[0].message


def test_error_messages_are_consistent_and_generic(service, tmp_path):
    """
    Test that all error messages are generic and don't leak information.

    Verifies consistency with gallery.py error handling approach.
    """
    photo = tmp_path / "test.jpg"
    img = Image.new('RGB', (50, 50), color='blue')
    img.save(photo, 'JPEG')

    error_scenarios = []

    # Scenario 1: Image open failure
    with patch('webui.backend.services.metadata_service.Image.open') as mock_open:
        mock_open.side_effect = OSError("Detailed system error")
        metadata = service.get_photo_metadata(photo)
        error_scenarios.append(metadata['error'])

    # Scenario 2: Permission denied
    with patch.object(Path, 'stat') as mock_stat:
        mock_stat.side_effect = PermissionError("Access denied to /admin/files")
        metadata = service.get_photo_metadata(photo)
        error_scenarios.append(metadata['error'])

    # Scenario 3: Unexpected exception (use exists() which triggers outer exception handler)
    with patch.object(Path, 'exists') as mock_exists:
        mock_exists.side_effect = ValueError("Invalid configuration in /etc/mothbox.conf")
        metadata = service.get_photo_metadata(photo)
        error_scenarios.append(metadata['error'])

    # Verify all error messages are generic
    assert error_scenarios == [
        "Failed to open image",
        "Permission denied",
        "Failed to read metadata"
    ]

    # Verify none contain sensitive details
    for error_msg in error_scenarios:
        assert "Detailed" not in error_msg
        assert "/admin" not in error_msg
        assert "/etc" not in error_msg
        assert "conf" not in error_msg
        assert str(photo) not in error_msg


def test_logging_includes_full_context_for_debugging(service, sample_photo_path, caplog):
    """
    Test that logs contain full context for debugging purposes.

    While user-facing errors are generic, logs should have all details.
    """
    with caplog.at_level(logging.ERROR):
        with patch('webui.backend.services.metadata_service.Image.open') as mock_open:
            detailed_error = "IOError: [Errno 28] No space left on device: '/var/mothbox/photos/large_photo.jpg'"
            mock_open.side_effect = OSError(detailed_error)

            metadata = service.get_photo_metadata(sample_photo_path)

            # User sees generic error
            assert metadata['error'] == "Failed to open image"

            # Log contains full details
            log_message = caplog.records[0].message
            assert str(sample_photo_path) in log_message
            assert "Failed to open image" in log_message

            # Verify exc_info=True was used (exception traceback logged)
            assert caplog.records[0].exc_info is not None


def test_batch_processing_doesnt_expose_paths(service, tmp_path, caplog):
    """
    Test that batch processing doesn't expose file paths in error messages.

    When processing multiple photos, errors should still be generic.
    Batch processing just calls get_photo_metadata for each photo, so
    error handling is the same.
    """
    # Create 2 photos
    photo1 = tmp_path / "photo1.jpg"
    photo2 = tmp_path / "photo2.jpg"

    img = Image.new('RGB', (50, 50), color='green')
    img.save(photo1, 'JPEG')
    img.save(photo2, 'JPEG')

    with caplog.at_level(logging.ERROR):
        # Make second photo fail by making Image.open fail for it
        original_open = Image.open

        def selective_open(path, *args, **kwargs):
            if 'photo2' in str(path):
                raise OSError(f"Cannot open {path}: File corrupted")
            return original_open(path, *args, **kwargs)

        with patch('webui.backend.services.metadata_service.Image.open', side_effect=selective_open):
            results = service.batch_get_metadata([photo1, photo2])

            # Verify second photo has generic error
            assert 'error' in results[1]
            assert results[1]['error'] == "Failed to open image"
            assert str(photo2) not in results[1]['error']
            assert "corrupted" not in results[1]['error']

            # Verify logging includes full details (at least one log for photo2)
            assert len(caplog.records) >= 1
            # Check that at least one log mentions photo2
            assert any(str(photo2) in record.message for record in caplog.records)


def test_error_messages_match_gallery_pattern(service, sample_photo_path):
    """
    Test that error messages follow the same pattern as gallery.py.

    Ensures consistency across the codebase.
    """
    # Expected pattern from gallery.py:
    # - Log full details server-side with logger.error()
    # - Return generic message without sensitive info
    # - Use exc_info=True for full traceback

    with patch('webui.backend.services.metadata_service.Image.open') as mock_open:
        mock_open.side_effect = OSError("System-specific error details")

        metadata = service.get_photo_metadata(sample_photo_path)

        # Generic error message (matches gallery.py pattern)
        assert metadata['error'] in [
            "Failed to open image",
            "Permission denied",
            "Failed to read metadata"
        ]

        # No exception type exposed
        assert "OSError" not in metadata['error']
        assert "Exception" not in metadata['error']

        # No system details exposed
        assert "System-specific" not in metadata['error']


def test_no_stack_traces_in_error_responses(service, sample_photo_path):
    """
    Test that stack traces are never included in error responses.

    Stack traces should only be in logs, not API responses.
    """
    with patch('webui.backend.services.metadata_service.Image.open') as mock_open:
        mock_open.side_effect = RuntimeError("Critical failure with traceback")

        metadata = service.get_photo_metadata(sample_photo_path)

        # Verify error message doesn't contain stack trace indicators
        assert 'error' in metadata
        assert "Traceback" not in metadata['error']
        assert "File \"" not in metadata['error']
        assert "line " not in metadata['error']
        assert ".py" not in str(metadata['error'])


def test_consistent_error_structure(service, tmp_path):
    """
    Test that all errors return consistent structure.

    Error responses should always have 'error' key with string value.
    """
    photo = tmp_path / "test.jpg"
    img = Image.new('RGB', (50, 50), color='yellow')
    img.save(photo, 'JPEG')

    # Test different error scenarios
    error_types = []

    # Image open failure
    with patch('webui.backend.services.metadata_service.Image.open') as mock_open:
        mock_open.side_effect = OSError("Error")
        result = service.get_photo_metadata(photo)
        error_types.append(('image_open', result))

    # Permission error
    with patch.object(Path, 'stat') as mock_stat:
        mock_stat.side_effect = PermissionError("Error")
        result = service.get_photo_metadata(photo)
        error_types.append(('permission', result))

    # Unexpected error
    with patch.object(service, '_extract_camera_metadata') as mock_extract:
        mock_extract.side_effect = ValueError("Error")
        result = service.get_photo_metadata(photo)
        error_types.append(('unexpected', result))

    # Verify all have consistent structure
    for error_name, result in error_types:
        assert 'error' in result, f"{error_name} missing 'error' key"
        assert isinstance(result['error'], str), f"{error_name} error is not string"
        assert len(result['error']) > 0, f"{error_name} error is empty"
        assert result['error'] != "Error", f"{error_name} exposes raw exception message"


def test_security_comments_present_in_code(service):
    """
    Test that security comments are present in the source code.

    Ensures future maintainers understand the security requirements.
    """
    import inspect
    source = inspect.getsource(service.get_photo_metadata)

    # Verify security-related comments are present
    assert "CodeQL security requirement" in source or "security" in source.lower()
    assert "don't expose" in source.lower() or "generic" in source.lower()
    assert "server-side" in source.lower()


def test_exif_parsing_failure_doesnt_expose_exception_details(service, sample_photo_path, caplog):
    """
    Test that EXIF parsing failures don't expose exception details to user.

    Original Issue:
    - metadata['exif_warning'] = f"EXIF parsing failed: {str(e)}"
    - Exposed exception details to API consumers

    Fixed:
    - metadata['exif_warning'] = "EXIF parsing failed"
    - Generic message only, full details logged server-side
    """
    import piexif

    with caplog.at_level(logging.WARNING):
        with patch('webui.backend.services.metadata_service.piexif.load') as mock_load:
            # Simulate EXIF parsing failure with detailed exception
            mock_load.side_effect = piexif.InvalidImageDataError(
                "Invalid EXIF data at offset 0x12AB: corrupted IFD structure in /secret/path/photo.jpg"
            )

            metadata = service.get_photo_metadata(sample_photo_path)

            # Verify exif_warning field doesn't contain exception details
            assert 'exif_warning' in metadata
            assert metadata['exif_warning'] == "EXIF parsing failed"
            assert "Invalid EXIF data" not in metadata['exif_warning']
            assert "offset 0x12AB" not in metadata['exif_warning']
            assert "corrupted IFD" not in metadata['exif_warning']
            assert "/secret/path" not in metadata['exif_warning']
            assert str(sample_photo_path) not in metadata['exif_warning']

            # Verify full details are logged server-side
            assert len(caplog.records) >= 1
            assert any(record.levelname == "WARNING" for record in caplog.records)
            # At least one warning should mention the photo filename (not full path, just name)
            assert any(sample_photo_path.name in record.message for record in caplog.records)


def test_batch_processing_doesnt_expose_paths_in_top_level_exception(service, tmp_path, caplog):
    """
    Test that batch_get_metadata doesn't expose file paths or exception details.

    Original Issue:
    - error_entry = {'error': f"Failed to process {photo_path}: {e}"}
    - Exposed full path and exception details

    Fixed:
    - error_entry = {'error': "Failed to process photo"}
    - Generic message, full details logged server-side
    """
    # Create a photo
    photo = tmp_path / "sensitive_location" / "classified_photo.jpg"
    photo.parent.mkdir(parents=True)

    img = Image.new('RGB', (50, 50), color='purple')
    img.save(photo, 'JPEG')

    with caplog.at_level(logging.ERROR):
        # Make get_photo_metadata raise an exception
        with patch.object(service, 'get_photo_metadata') as mock_get:
            mock_get.side_effect = RuntimeError(
                f"Database connection failed for {photo}: invalid credentials at 192.168.1.100"
            )

            results = service.batch_get_metadata([photo])

            # Verify error field doesn't contain path or exception details
            assert len(results) == 1
            assert 'error' in results[0]
            assert results[0]['error'] == "Failed to process photo"
            assert str(photo) not in results[0]['error']
            assert "sensitive_location" not in results[0]['error']
            assert "classified_photo" not in results[0]['error']
            assert "Database connection" not in results[0]['error']
            assert "192.168.1.100" not in results[0]['error']
            assert "RuntimeError" not in results[0]['error']

            # Verify full details are logged server-side
            assert len(caplog.records) >= 1
            log_messages = [record.message for record in caplog.records if record.levelname == "ERROR"]
            assert any(str(photo) in msg for msg in log_messages)

            # Verify exc_info=True was used for at least one log
            assert any(record.exc_info is not None for record in caplog.records if record.levelname == "ERROR")
