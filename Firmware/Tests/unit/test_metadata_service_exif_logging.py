"""
Test EXIF parsing failure logging in MetadataService.

This module verifies that EXIF parsing failures are properly logged and
that metadata includes an error flag when EXIF data cannot be parsed.

Original Issue:
- If piexif.load() fails but Image.open() succeeds, code continues silently
  with empty exif_dict without logging the failure

Solution:
- Log EXIF parsing failures at WARNING level
- Add 'exif_warning' field to metadata to indicate parsing failure
- Continue processing with empty exif_dict (graceful degradation)

Related to: Issue #100 - Metadata API implementation
"""

import logging
from unittest.mock import Mock, patch

import pytest
from PIL import Image

from webui.backend.services.metadata_service import MetadataService


@pytest.fixture
def service():
    """Create MetadataService instance"""
    return MetadataService()


@pytest.fixture
def mock_image():
    """Create a mock PIL Image"""
    img = Mock(spec=Image.Image)
    img.size = (1920, 1080)
    img.format = "JPEG"
    return img


@pytest.fixture
def sample_photo_path(tmp_path):
    """Create a sample photo file"""
    photo_path = tmp_path / "test_photo.jpg"

    # Create a minimal valid JPEG file
    img = Image.new('RGB', (100, 100), color='red')
    img.save(photo_path, 'JPEG')

    return photo_path


def test_exif_parsing_failure_is_logged(service, sample_photo_path, caplog):
    """
    Test that EXIF parsing failures are logged at WARNING level.

    When piexif.load() fails but Image.open() succeeds, a warning should
    be logged with the photo name and error details.
    """
    with caplog.at_level(logging.WARNING):
        with patch('webui.backend.services.metadata_service.piexif.load') as mock_piexif:
            # Simulate EXIF parsing failure
            mock_piexif.side_effect = ValueError("Invalid EXIF data")

            # Get metadata (should handle failure gracefully)
            metadata = service.get_photo_metadata(sample_photo_path)

            # Verify warning was logged
            assert len(caplog.records) == 1
            assert caplog.records[0].levelname == "WARNING"
            assert sample_photo_path.name in caplog.records[0].message
            assert "Invalid EXIF data" in caplog.records[0].message


def test_exif_parsing_failure_adds_warning_field(service, sample_photo_path):
    """
    Test that EXIF parsing failures add 'exif_warning' field to metadata.

    The warning field should contain generic message (not exception details).
    Full details are logged server-side only (CodeQL security requirement).
    """
    with patch('webui.backend.services.metadata_service.piexif.load') as mock_piexif:
        # Simulate EXIF parsing failure
        mock_piexif.side_effect = RuntimeError("Corrupted EXIF header")

        # Get metadata
        metadata = service.get_photo_metadata(sample_photo_path)

        # Verify warning field is present with generic message
        assert 'exif_warning' in metadata
        assert metadata['exif_warning'] == "EXIF parsing failed"
        # Verify exception details are NOT exposed to user
        assert "Corrupted EXIF header" not in metadata['exif_warning']


def test_exif_parsing_failure_does_not_prevent_metadata_extraction(service, sample_photo_path):
    """
    Test that EXIF parsing failure doesn't prevent extraction of other metadata.

    Even without EXIF data, should still extract file metadata (size, dimensions, etc.)
    """
    with patch('webui.backend.services.metadata_service.piexif.load') as mock_piexif:
        # Simulate EXIF parsing failure
        mock_piexif.side_effect = OSError("Cannot read EXIF")

        # Get metadata
        metadata = service.get_photo_metadata(sample_photo_path)

        # Verify no fatal error
        assert 'error' not in metadata

        # Verify file metadata is still extracted
        assert metadata['file']['filename'] == sample_photo_path.name
        assert metadata['file']['size'] > 0
        assert metadata['file']['width'] == 100
        assert metadata['file']['height'] == 100
        assert metadata['file']['format'] == 'JPEG'

        # Verify categories exist (with None/empty values)
        assert 'camera' in metadata
        assert 'capture' in metadata
        assert 'location' in metadata
        assert 'deployment' in metadata


def test_exif_parsing_success_has_no_warning_field(service, sample_photo_path):
    """
    Test that successful EXIF parsing does not add 'exif_warning' field.

    The warning field should only be present when parsing fails.
    """
    with patch('webui.backend.services.metadata_service.piexif.load') as mock_piexif:
        # Simulate successful EXIF parsing
        mock_piexif.return_value = {
            "0th": {},
            "Exif": {},
            "GPS": {},
            "Interop": {},
            "1st": {},
            "thumbnail": None
        }

        # Get metadata
        metadata = service.get_photo_metadata(sample_photo_path)

        # Verify no warning field
        assert 'exif_warning' not in metadata
        assert 'error' not in metadata


def test_image_open_failure_after_exif_failure_returns_error(service, sample_photo_path):
    """
    Test that if both piexif.load() and Image.open() fail, an error is returned.

    This is the fallback case where the image file is truly corrupted.
    """
    with patch('webui.backend.services.metadata_service.piexif.load') as mock_piexif:
        with patch('webui.backend.services.metadata_service.Image.open') as mock_open:
            # First call fails (EXIF parsing)
            # Second call fails (image opening in fallback)
            mock_piexif.side_effect = ValueError("Invalid EXIF")
            mock_open.side_effect = [
                ValueError("Invalid EXIF"),  # First call in try block
                OSError("Cannot identify image file")  # Second call in except block
            ]

            # Get metadata
            metadata = service.get_photo_metadata(sample_photo_path)

            # Verify error is returned (not warning)
            assert 'error' in metadata
            assert "Failed to open image" in metadata['error']
            assert 'exif_warning' not in metadata  # No warning if image can't open


def test_multiple_exif_parsing_failures_are_logged_separately(service, tmp_path, caplog):
    """
    Test that multiple EXIF parsing failures are logged as separate entries.

    When processing multiple photos with EXIF failures, each should be logged.
    """
    # Create two sample photos
    photo1 = tmp_path / "photo1.jpg"
    photo2 = tmp_path / "photo2.jpg"

    img = Image.new('RGB', (100, 100), color='blue')
    img.save(photo1, 'JPEG')
    img.save(photo2, 'JPEG')

    with caplog.at_level(logging.WARNING):
        with patch('webui.backend.services.metadata_service.piexif.load') as mock_piexif:
            # Simulate EXIF parsing failures (always raises same error)
            mock_piexif.side_effect = ValueError("EXIF parsing error")

            # Process both photos
            service.get_photo_metadata(photo1)
            service.get_photo_metadata(photo2)

            # Verify both failures were logged
            assert len(caplog.records) == 2
            assert "photo1.jpg" in caplog.records[0].message
            assert "EXIF parsing error" in caplog.records[0].message
            assert "photo2.jpg" in caplog.records[1].message
            assert "EXIF parsing error" in caplog.records[1].message


def test_exif_warning_field_format_consistency(service, sample_photo_path):
    """
    Test that 'exif_warning' field has consistent format.

    Format should be: "EXIF parsing failed" (generic message only).
    Exception details should NOT be exposed (CodeQL security requirement).
    """
    with patch('webui.backend.services.metadata_service.piexif.load') as mock_piexif:
        # Test with various error types
        error_messages = [
            "Invalid EXIF header",
            "Unsupported EXIF format",
            "Missing required EXIF tags"
        ]

        for error_msg in error_messages:
            mock_piexif.side_effect = Exception(error_msg)

            metadata = service.get_photo_metadata(sample_photo_path)

            # Verify format consistency: always generic message
            assert metadata['exif_warning'] == "EXIF parsing failed"
            # Verify exception details are NOT exposed
            assert error_msg not in metadata['exif_warning']


def test_batch_processing_logs_all_exif_failures(service, tmp_path, caplog):
    """
    Test that batch processing logs EXIF failures for all affected photos.

    When using batch_get_metadata(), each EXIF failure should be logged.
    """
    # Create 3 sample photos
    photos = []
    for i in range(3):
        photo = tmp_path / f"batch_photo_{i}.jpg"
        img = Image.new('RGB', (50, 50), color='green')
        img.save(photo, 'JPEG')
        photos.append(photo)

    with caplog.at_level(logging.WARNING):
        with patch('webui.backend.services.metadata_service.piexif.load') as mock_piexif:
            # All EXIF parsing attempts fail
            mock_piexif.side_effect = ValueError("Batch EXIF error")

            # Process batch
            results = service.batch_get_metadata(photos)

            # Verify all failures were logged
            assert len(caplog.records) == 3
            for i, record in enumerate(caplog.records):
                assert f"batch_photo_{i}.jpg" in record.message
                assert "Batch EXIF error" in record.message

            # Verify all results have warning field
            for result in results:
                assert 'exif_warning' in result


def test_logging_includes_exception_details(service, sample_photo_path, caplog):
    """
    Test that logged warning includes exception type and details.

    Helps with debugging to know what kind of error occurred.
    """
    with caplog.at_level(logging.WARNING):
        with patch('webui.backend.services.metadata_service.piexif.load') as mock_piexif:
            # Simulate specific exception with details
            mock_piexif.side_effect = KeyError("EXIF tag 'DateTimeOriginal' not found")

            metadata = service.get_photo_metadata(sample_photo_path)

            # Verify exception details in log
            log_message = caplog.records[0].message
            assert "KeyError" in log_message or "DateTimeOriginal" in log_message
            assert sample_photo_path.name in log_message


def test_exif_warning_does_not_affect_cache_key(service, sample_photo_path):
    """
    Test that 'exif_warning' field doesn't interfere with caching.

    Metadata with warnings should still be cacheable and retrievable.
    """
    with patch('webui.backend.services.metadata_service.piexif.load') as mock_piexif:
        # Simulate EXIF failure
        mock_piexif.side_effect = ValueError("Cache test error")

        # Get metadata twice
        metadata1 = service.get_photo_metadata(sample_photo_path)
        metadata2 = service.get_photo_metadata(sample_photo_path)

        # Both should have warning field
        assert 'exif_warning' in metadata1
        assert 'exif_warning' in metadata2

        # Warning messages should be identical
        assert metadata1['exif_warning'] == metadata2['exif_warning']
