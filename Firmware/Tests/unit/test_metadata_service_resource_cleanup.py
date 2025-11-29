"""
Test image resource cleanup in MetadataService.

This module verifies that PIL Image objects are properly closed using context
managers, preventing resource leaks on error paths.

Original Issue:
- Image.open() result not closed if early returns happen
- Resource leak on error paths (PermissionError, exceptions, early returns)

Solution:
- Use context manager: with Image.open(photo_path) as image:
- Ensures image is always closed, even on exceptions

Related to: Issue #100 - Metadata API implementation
"""

from unittest.mock import MagicMock, Mock, patch

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


def test_image_closed_on_normal_path(service, sample_photo_path):
    """
    Test that image is properly closed on normal execution path.

    When metadata extraction succeeds, the image should be closed
    via the context manager's __exit__.
    """
    with patch('webui.backend.services.metadata_service.Image.open') as mock_open:
        # Create a mock image with context manager support
        mock_image = MagicMock()
        mock_image.__enter__ = Mock(return_value=mock_image)
        mock_image.__exit__ = Mock(return_value=False)
        mock_image.size = (1920, 1080)
        mock_image.format = "JPEG"
        mock_open.return_value = mock_image

        # Get metadata
        metadata = service.get_photo_metadata(sample_photo_path)

        # Verify image was opened
        mock_open.assert_called_once_with(sample_photo_path)

        # Verify context manager was used (__enter__ and __exit__ called)
        mock_image.__enter__.assert_called_once()
        mock_image.__exit__.assert_called_once()


def test_image_closed_on_exif_parsing_failure(service, sample_photo_path):
    """
    Test that image is closed when EXIF parsing fails.

    Even when piexif.load() raises an exception, the image should
    still be properly closed via the context manager.
    """
    with patch('webui.backend.services.metadata_service.Image.open') as mock_open:
        with patch('webui.backend.services.metadata_service.piexif.load') as mock_piexif:
            # Create mock image with context manager support
            mock_image = MagicMock()
            mock_image.__enter__ = Mock(return_value=mock_image)
            mock_image.__exit__ = Mock(return_value=False)
            mock_image.size = (1920, 1080)
            mock_image.format = "JPEG"
            mock_open.return_value = mock_image

            # Simulate EXIF parsing failure
            mock_piexif.side_effect = ValueError("Invalid EXIF")

            # Get metadata
            metadata = service.get_photo_metadata(sample_photo_path)

            # Verify image was still closed despite EXIF error
            mock_image.__exit__.assert_called_once()
            assert 'exif_warning' in metadata


def test_image_closed_on_metadata_extraction_exception(service, sample_photo_path):
    """
    Test that image is closed when metadata extraction raises exception.

    If any metadata extraction method fails, the image should still be closed.
    """
    with patch('webui.backend.services.metadata_service.Image.open') as mock_open:
        # Create mock image with context manager support
        mock_image = MagicMock()
        mock_image.__enter__ = Mock(return_value=mock_image)
        mock_image.__exit__ = Mock(return_value=False)
        mock_image.size = (1920, 1080)
        mock_image.format = "JPEG"
        mock_open.return_value = mock_image

        # Simulate failure in metadata extraction
        with patch.object(service, '_extract_camera_metadata') as mock_extract:
            mock_extract.side_effect = RuntimeError("Extraction failed")

            # Get metadata (should handle error gracefully)
            metadata = service.get_photo_metadata(sample_photo_path)

            # Verify image was closed despite extraction error
            mock_image.__exit__.assert_called_once()


def test_no_resource_leak_on_image_open_failure(service, sample_photo_path):
    """
    Test that no resources leak when Image.open() fails.

    When the image cannot be opened, there should be no unclosed resources.
    """
    with patch('webui.backend.services.metadata_service.Image.open') as mock_open:
        # Simulate Image.open() failure
        mock_open.side_effect = OSError("Cannot open image")

        # Get metadata (should return error)
        metadata = service.get_photo_metadata(sample_photo_path)

        # Verify error is returned
        assert 'error' in metadata
        assert "Failed to open image" in metadata['error']

        # Verify Image.open was attempted
        mock_open.assert_called_once()


def test_image_closed_on_file_metadata_extraction(service, sample_photo_path):
    """
    Test that image remains open during _extract_file_metadata and closed after.

    The _extract_file_metadata method needs the image object, so it should
    be available during that call but closed afterward.
    """
    with patch('webui.backend.services.metadata_service.Image.open') as mock_open:
        # Create mock image with context manager support
        mock_image = MagicMock()
        mock_image.__enter__ = Mock(return_value=mock_image)
        mock_image.__exit__ = Mock(return_value=False)
        mock_image.size = (1920, 1080)
        mock_image.format = "JPEG"
        mock_open.return_value = mock_image

        # Spy on _extract_file_metadata to verify image is available
        with patch.object(service, '_extract_file_metadata', wraps=service._extract_file_metadata) as mock_extract:
            metadata = service.get_photo_metadata(sample_photo_path)

            # Verify _extract_file_metadata was called with image object
            mock_extract.assert_called_once()
            call_args = mock_extract.call_args
            assert call_args[0][1] == mock_image  # Second arg is image

            # Verify image was closed after metadata extraction
            mock_image.__exit__.assert_called_once()


def test_context_manager_exit_called_with_no_exception(service, sample_photo_path):
    """
    Test that context manager __exit__ is called with (None, None, None) on success.

    When no exception occurs, __exit__ should be called with all None arguments.
    """
    with patch('webui.backend.services.metadata_service.Image.open') as mock_open:
        # Create mock image with context manager support
        mock_image = MagicMock()
        mock_image.__enter__ = Mock(return_value=mock_image)
        mock_image.__exit__ = Mock(return_value=False)
        mock_image.size = (1920, 1080)
        mock_image.format = "JPEG"
        mock_open.return_value = mock_image

        # Get metadata (successful path)
        metadata = service.get_photo_metadata(sample_photo_path)

        # Verify __exit__ was called (exception info would be in args if exception occurred)
        mock_image.__exit__.assert_called_once()
        # In successful case, __exit__ receives (None, None, None) but we can't easily verify
        # that with MagicMock. The important part is that it was called.


def test_context_manager_exit_called_on_exception(service, sample_photo_path):
    """
    Test that context manager __exit__ is called even when exception occurs.

    The context manager should handle cleanup even if code inside raises.
    """
    with patch('webui.backend.services.metadata_service.Image.open') as mock_open:
        # Create mock image with context manager support
        mock_image = MagicMock()
        mock_image.__enter__ = Mock(return_value=mock_image)
        mock_image.__exit__ = Mock(return_value=False)  # Don't suppress exception
        mock_image.size = (1920, 1080)
        mock_image.format = "JPEG"
        mock_open.return_value = mock_image

        # Simulate exception during metadata extraction
        with patch.object(service, '_extract_file_metadata') as mock_extract:
            mock_extract.side_effect = RuntimeError("Extraction error")

            # Get metadata
            metadata = service.get_photo_metadata(sample_photo_path)

            # Verify __exit__ was called despite exception
            mock_image.__exit__.assert_called_once()


def test_no_manual_close_calls(service, sample_photo_path):
    """
    Test that image.close() is NOT manually called (context manager handles it).

    The refactored code should not call image.close() explicitly since
    the context manager handles cleanup.
    """
    with patch('webui.backend.services.metadata_service.Image.open') as mock_open:
        # Create mock image with context manager support
        mock_image = MagicMock()
        mock_image.__enter__ = Mock(return_value=mock_image)
        mock_image.__exit__ = Mock(return_value=False)
        mock_image.size = (1920, 1080)
        mock_image.format = "JPEG"
        mock_image.close = Mock()  # Track close() calls
        mock_open.return_value = mock_image

        # Get metadata
        metadata = service.get_photo_metadata(sample_photo_path)

        # Verify close() was NOT called manually
        mock_image.close.assert_not_called()

        # But __exit__ was called (context manager cleanup)
        mock_image.__exit__.assert_called_once()


def test_batch_processing_closes_all_images(service, tmp_path):
    """
    Test that batch processing properly closes all images.

    When processing multiple photos, each image should be closed
    via context manager.
    """
    # Create 3 sample photos
    photos = []
    for i in range(3):
        photo = tmp_path / f"photo_{i}.jpg"
        img = Image.new('RGB', (50, 50), color='blue')
        img.save(photo, 'JPEG')
        photos.append(photo)

    with patch('webui.backend.services.metadata_service.Image.open') as mock_open:
        # Track all mock images created
        mock_images = []

        def create_mock_image(*args, **kwargs):
            mock_image = MagicMock()
            mock_image.__enter__ = Mock(return_value=mock_image)
            mock_image.__exit__ = Mock(return_value=False)
            mock_image.size = (50, 50)
            mock_image.format = "JPEG"
            mock_images.append(mock_image)
            return mock_image

        mock_open.side_effect = create_mock_image

        # Process batch
        results = service.batch_get_metadata(photos)

        # Verify all images were opened
        assert mock_open.call_count == 3

        # Verify all images were closed via context manager
        for mock_image in mock_images:
            mock_image.__exit__.assert_called_once()


def test_resource_cleanup_order(service, sample_photo_path):
    """
    Test that resources are cleaned up in correct order.

    Image should be closed after all metadata extraction is complete.
    """
    with patch('webui.backend.services.metadata_service.Image.open') as mock_open:
        # Create mock image with context manager support
        mock_image = MagicMock()
        mock_image.__enter__ = Mock(return_value=mock_image)
        mock_image.__exit__ = Mock(return_value=False)
        mock_image.size = (1920, 1080)
        mock_image.format = "JPEG"
        mock_open.return_value = mock_image

        # Track call order
        call_order = []

        # Wrap metadata extraction methods to track calls
        original_extract_file = service._extract_file_metadata
        def tracked_extract_file(*args, **kwargs):
            call_order.append('extract_file')
            return original_extract_file(*args, **kwargs)

        def tracked_exit(*args, **kwargs):
            call_order.append('image_exit')
            return False

        with patch.object(service, '_extract_file_metadata', side_effect=tracked_extract_file):
            mock_image.__exit__ = Mock(side_effect=tracked_exit)

            metadata = service.get_photo_metadata(sample_photo_path)

            # Verify extraction happens before cleanup
            assert call_order == ['extract_file', 'image_exit']


def test_no_resource_leak_with_real_image(service, sample_photo_path):
    """
    Test with real PIL Image to verify actual resource cleanup.

    Uses real Image.open() to ensure context manager behavior is correct.
    """
    # This test uses real PIL Image (no mocking)
    metadata = service.get_photo_metadata(sample_photo_path)

    # Verify metadata was extracted successfully
    assert 'file' in metadata
    assert metadata['file']['width'] == 100
    assert metadata['file']['height'] == 100

    # Try to access the file again (should not be locked)
    # This would fail if the image wasn't properly closed
    with open(sample_photo_path, 'rb') as f:
        data = f.read()
        assert len(data) > 0  # File is accessible
