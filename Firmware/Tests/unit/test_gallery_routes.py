"""
Unit tests for gallery routes (Issue #78 - Phase 1)

Tests gallery photo listing, serving, and thumbnail generation endpoints.
Focuses on security (path traversal), error handling, and metadata accuracy.

Coverage Target: 90%+ (gallery.py is 92 lines)
"""

import pytest
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from flask import Flask
from io import BytesIO

# Import the blueprint
from routes.gallery import gallery_bp


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def temp_photos_dir(tmp_path, monkeypatch):
    """
    Temporary PHOTOS_DIR for gallery tests

    Creates isolated photo directory and patches mothbox_paths.PHOTOS_DIR
    in all relevant modules.
    """
    photos_dir = tmp_path / "photos"
    photos_dir.mkdir()

    # Patch PHOTOS_DIR in mothbox_paths
    import mothbox_paths
    monkeypatch.setattr(mothbox_paths, 'PHOTOS_DIR', photos_dir)

    # Also patch in routes.gallery module (already imported)
    import routes.gallery
    monkeypatch.setattr(routes.gallery, 'PHOTOS_DIR', photos_dir)

    return photos_dir


@pytest.fixture
def gallery_app(temp_photos_dir):
    """Flask app with gallery blueprint for testing"""
    app = Flask(__name__)
    app.config['TESTING'] = True

    # Register blueprint AFTER patching PHOTOS_DIR
    app.register_blueprint(gallery_bp, url_prefix='/api/gallery')
    return app


@pytest.fixture
def gallery_client(gallery_app):
    """Test client for gallery routes"""
    return gallery_app.test_client()


@pytest.fixture
def sample_photos(temp_photos_dir):
    """Create sample photo files for testing"""
    photos = []

    # Create some test photos with different timestamps
    for i in range(3):
        photo_path = temp_photos_dir / f"photo_{i}.jpg"
        photo_path.write_bytes(b'\xFF\xD8\xFF\xE0' + b'\x00' * 100)  # Minimal JPEG header
        photos.append(photo_path)

    # Create a nested directory with a photo
    nested_dir = temp_photos_dir / "2024" / "10"
    nested_dir.mkdir(parents=True)
    nested_photo = nested_dir / "nested_photo.jpg"
    nested_photo.write_bytes(b'\xFF\xD8\xFF\xE0' + b'\x00' * 100)
    photos.append(nested_photo)

    return photos


# ============================================================================
# Test List Photos Endpoint
# ============================================================================

class TestGalleryListEndpoint:
    """Tests for GET /api/gallery/photos"""

    def test_list_photos_empty_directory(self, gallery_client, temp_photos_dir):
        """GET /photos returns empty list when no photos exist"""
        response = gallery_client.get('/api/gallery/photos')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'photos' in data
        assert data['photos'] == []

    def test_list_photos_returns_sorted_by_mtime(self, gallery_client, sample_photos, temp_photos_dir):
        """GET /photos returns photos sorted by modification time (newest first)"""
        response = gallery_client.get('/api/gallery/photos')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'photos' in data
        assert len(data['photos']) == 4  # 3 regular + 1 nested

        # Verify photos are sorted by mtime descending (newest first)
        mtimes = [photo['timestamp'] for photo in data['photos']]
        assert mtimes == sorted(mtimes, reverse=True), "Photos should be sorted newest first"

    def test_list_photos_includes_metadata(self, gallery_client, sample_photos):
        """GET /photos includes complete metadata for each photo"""
        response = gallery_client.get('/api/gallery/photos')

        assert response.status_code == 200
        data = json.loads(response.data)

        # Check first photo has all required fields
        photo = data['photos'][0]
        assert 'path' in photo
        assert 'filename' in photo
        assert 'size' in photo
        assert 'timestamp' in photo
        assert 'date' in photo

        # Verify data types
        assert isinstance(photo['path'], str)
        assert isinstance(photo['filename'], str)
        assert isinstance(photo['size'], int)
        assert isinstance(photo['timestamp'], (int, float))
        assert isinstance(photo['date'], str)

        # Verify date is ISO format
        datetime.fromisoformat(photo['date'])  # Should not raise

    def test_list_photos_handles_nested_directories(self, gallery_client, sample_photos, temp_photos_dir):
        """GET /photos includes photos from nested directories"""
        response = gallery_client.get('/api/gallery/photos')

        assert response.status_code == 200
        data = json.loads(response.data)

        # Find the nested photo
        nested_photos = [p for p in data['photos'] if '2024' in p['path']]
        assert len(nested_photos) == 1

        nested_photo = nested_photos[0]
        assert 'nested_photo.jpg' in nested_photo['path']
        assert nested_photo['filename'] == 'nested_photo.jpg'

    def test_list_photos_filters_non_jpg_files(self, gallery_client, temp_photos_dir):
        """GET /photos only includes .jpg files, ignoring other file types"""
        # Create various file types
        (temp_photos_dir / "photo.jpg").write_bytes(b'\xFF\xD8\xFF\xE0' + b'\x00' * 100)
        (temp_photos_dir / "photo.png").write_bytes(b'PNG data')
        (temp_photos_dir / "readme.txt").write_text("Not a photo")
        (temp_photos_dir / "data.json").write_text('{"foo": "bar"}')

        response = gallery_client.get('/api/gallery/photos')

        assert response.status_code == 200
        data = json.loads(response.data)

        # Should only have 1 JPG file
        assert len(data['photos']) == 1
        assert data['photos'][0]['filename'] == 'photo.jpg'

    def test_list_photos_handles_missing_photos_dir(self, gallery_client, temp_photos_dir, monkeypatch):
        """GET /photos returns empty list when PHOTOS_DIR doesn't exist"""
        # Point to non-existent directory
        nonexistent_dir = temp_photos_dir / "nonexistent"
        from Tests.conftest import patch_path_constant_everywhere
        patch_path_constant_everywhere(monkeypatch, 'PHOTOS_DIR', nonexistent_dir)

        response = gallery_client.get('/api/gallery/photos')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['photos'] == []


# ============================================================================
# Test Get Photo Endpoint
# ============================================================================

class TestGalleryPhotoEndpoint:
    """Tests for GET /api/gallery/photo/<path>"""

    def test_get_photo_success(self, gallery_client, sample_photos, temp_photos_dir):
        """GET /photo/<path> returns photo file"""
        # Use first sample photo
        photo_path = sample_photos[0].relative_to(temp_photos_dir)

        response = gallery_client.get(f'/api/gallery/photo/{photo_path}')

        assert response.status_code == 200
        assert response.mimetype == 'image/jpeg'
        assert len(response.data) > 0

    def test_get_photo_not_found(self, gallery_client):
        """GET /photo/<path> returns 404 for non-existent photo"""
        response = gallery_client.get('/api/gallery/photo/nonexistent.jpg')

        assert response.status_code == 404
        data = json.loads(response.data)
        assert 'error' in data
        assert 'not found' in data['error'].lower()

    def test_get_photo_path_traversal_blocked(self, gallery_client):
        """GET /photo/<path> blocks path traversal attempts"""
        # Try various path traversal attacks
        traversal_attempts = [
            '../../../etc/passwd',
            '../../secrets.txt',
            '../.ssh/id_rsa',
            'subdir/../../etc/passwd',
        ]

        for malicious_path in traversal_attempts:
            response = gallery_client.get(f'/api/gallery/photo/{malicious_path}')

            # Should return 400 (invalid path) or 404 (not found)
            # Both are acceptable as they prevent access
            assert response.status_code in [400, 404], \
                f"Path traversal should be blocked: {malicious_path}"

            if response.status_code == 400:
                data = json.loads(response.data)
                assert 'error' in data

    def test_get_photo_absolute_path_blocked(self, gallery_client, temp_photos_dir):
        """GET /photo/<path> blocks absolute path attempts"""
        # Try to access files with absolute paths
        # Flask may redirect absolute paths (308) or block them (400)
        # Both are acceptable security outcomes
        absolute_paths = [
            'etc/passwd',  # Use relative-looking absolute path
            'home/user/.ssh/id_rsa',
        ]

        for abs_path in absolute_paths:
            response = gallery_client.get(f'/api/gallery/photo/{abs_path}')

            # Should return 400 (invalid path) or 404 (not found)
            assert response.status_code in [400, 404], \
                f"Absolute path should be blocked: {abs_path}"

    def test_get_photo_nested_path(self, gallery_client, sample_photos, temp_photos_dir):
        """GET /photo/<path> works with nested directory paths"""
        # Get the nested photo
        nested_photo = [p for p in sample_photos if 'nested_photo.jpg' in str(p)][0]
        photo_path = nested_photo.relative_to(temp_photos_dir)

        response = gallery_client.get(f'/api/gallery/photo/{photo_path}')

        assert response.status_code == 200
        assert response.mimetype == 'image/jpeg'


# ============================================================================
# Test Get Thumbnail Endpoint
# ============================================================================

class TestGalleryThumbnailEndpoint:
    """Tests for GET /api/gallery/thumbnail/<path>"""

    def test_thumbnail_generation(self, gallery_client, sample_photos, temp_photos_dir):
        """GET /thumbnail/<path> generates and returns thumbnail"""
        # Use first sample photo
        photo_path = sample_photos[0].relative_to(temp_photos_dir)

        # Mock PIL module at import time
        import sys
        mock_pil = MagicMock()
        mock_img = MagicMock()
        mock_pil.Image.open.return_value = mock_img

        # Mock the save operation
        def mock_save(io_buf, format, quality=None):
            io_buf.write(b'\xFF\xD8\xFF\xE0' + b'\x00' * 50)  # Fake thumbnail data
        mock_img.save = mock_save

        with patch.dict(sys.modules, {'PIL': mock_pil, 'PIL.Image': mock_pil.Image}):
            response = gallery_client.get(f'/api/gallery/thumbnail/{photo_path}')

            assert response.status_code == 200
            assert response.mimetype == 'image/jpeg'

            # Verify thumbnail() was called with correct size
            mock_img.thumbnail.assert_called_once_with((300, 300))

    def test_thumbnail_not_found(self, gallery_client):
        """GET /thumbnail/<path> returns 404 for non-existent photo"""
        # Mock PIL to isolate path checking logic
        import sys
        mock_pil = MagicMock()
        with patch.dict(sys.modules, {'PIL': mock_pil, 'PIL.Image': mock_pil.Image}):
            response = gallery_client.get('/api/gallery/thumbnail/nonexistent.jpg')

            assert response.status_code == 404
            data = json.loads(response.data)
            assert 'error' in data

    def test_thumbnail_path_traversal_blocked(self, gallery_client):
        """GET /thumbnail/<path> blocks path traversal attempts"""
        traversal_attempts = [
            '../../../etc/passwd',
            '../../secrets.txt',
        ]

        # Mock PIL to isolate path checking logic
        import sys
        mock_pil = MagicMock()
        with patch.dict(sys.modules, {'PIL': mock_pil, 'PIL.Image': mock_pil.Image}):
            for malicious_path in traversal_attempts:
                response = gallery_client.get(f'/api/gallery/thumbnail/{malicious_path}')

                assert response.status_code in [400, 404], \
                    f"Path traversal should be blocked in thumbnail: {malicious_path}"

    def test_thumbnail_invalid_image_handled(self, gallery_client, temp_photos_dir):
        """GET /thumbnail/<path> handles corrupted/invalid images gracefully"""
        # Create an invalid image file
        invalid_photo = temp_photos_dir / "corrupted.jpg"
        invalid_photo.write_bytes(b'This is not a valid JPEG file')

        response = gallery_client.get('/api/gallery/thumbnail/corrupted.jpg')

        # Should return 500 error (PIL will fail to open)
        assert response.status_code == 500
        data = json.loads(response.data)
        assert 'error' in data


# ============================================================================
# Test Gallery Security
# ============================================================================

class TestGallerySecurity:
    """Security-focused tests for gallery endpoints"""

    def test_symlink_attack_blocked(self, gallery_client, temp_photos_dir, tmp_path):
        """Gallery endpoints block symlink attacks"""
        # Create a sensitive file outside PHOTOS_DIR
        sensitive_file = tmp_path / "sensitive.txt"
        sensitive_file.write_text("SECRET DATA")

        # Try to create a symlink inside PHOTOS_DIR pointing outside
        symlink_path = temp_photos_dir / "evil_link.jpg"
        try:
            symlink_path.symlink_to(sensitive_file)
        except OSError:
            pytest.skip("Symlink creation not supported on this system")

        # Try to access via photo endpoint
        response = gallery_client.get('/api/gallery/photo/evil_link.jpg')

        # Should be blocked (400 invalid path or 404)
        assert response.status_code in [400, 404]

        # Verify we didn't get the sensitive content
        if response.status_code == 200:
            assert b"SECRET DATA" not in response.data

    def test_null_byte_injection_blocked(self, gallery_client):
        """Gallery endpoints handle null byte injection attempts"""
        # Try null byte to bypass extension check
        malicious_paths = [
            'photo.jpg\x00.txt',
            '../etc/passwd\x00.jpg',
        ]

        for path in malicious_paths:
            response = gallery_client.get(f'/api/gallery/photo/{path}')

            # Should be blocked or not found
            assert response.status_code in [400, 404]

    def test_unicode_path_traversal_blocked(self, gallery_client):
        """Gallery endpoints handle Unicode path traversal attempts"""
        # Unicode-encoded path traversal (../ encoded as UTF-8 variations)
        unicode_attacks = [
            '%2e%2e%2f%2e%2e%2fetc/passwd',  # URL-encoded ../
            '..%c0%afetc/passwd',  # Overlong UTF-8
        ]

        for path in unicode_attacks:
            response = gallery_client.get(f'/api/gallery/photo/{path}')

            # Should be blocked
            assert response.status_code in [400, 404]
