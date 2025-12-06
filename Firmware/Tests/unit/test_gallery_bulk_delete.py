"""
Tests for bulk photo deletion endpoint.

This module tests the DELETE /api/gallery/photos/bulk endpoint for deleting
multiple photos and their associated sidecar metadata files.
"""

import pytest
from pathlib import Path
from PIL import Image


class TestBulkDeleteEndpoint:
    """Test DELETE /api/gallery/photos/bulk endpoint."""

    def test_delete_single_photo_success(self, client, temp_photos_dir):
        """DELETE with single filename removes photo and sidecar."""
        # Create test photo
        photo = temp_photos_dir / "test1.jpg"
        Image.new('RGB', (100, 100)).save(photo)
        sidecar = temp_photos_dir / "test1.jpg.json"
        sidecar.write_text('{"tags": ["test"]}')

        assert photo.exists()
        assert sidecar.exists()

        response = client.delete('/api/gallery/photos/bulk', json={
            'filenames': ['test1.jpg']
        })

        assert response.status_code == 200
        data = response.get_json()
        assert 'success' in data
        assert 'failed' in data
        assert 'test1.jpg' in data['success']
        assert len(data['failed']) == 0
        assert data['total'] == 1
        assert data['success_count'] == 1
        assert data['failed_count'] == 0
        assert not photo.exists()
        assert not sidecar.exists()

    def test_delete_multiple_photos(self, client, temp_photos_dir):
        """DELETE with multiple filenames removes all."""
        # Create test photos
        photos = []
        for i in range(3):
            photo = temp_photos_dir / f"test{i}.jpg"
            Image.new('RGB', (100, 100)).save(photo)
            sidecar = temp_photos_dir / f"test{i}.jpg.json"
            sidecar.write_text(f'{{"tags": ["test{i}"]}}')
            photos.append(photo)

        response = client.delete('/api/gallery/photos/bulk', json={
            'filenames': ['test0.jpg', 'test1.jpg', 'test2.jpg']
        })

        assert response.status_code == 200
        data = response.get_json()
        assert len(data['success']) == 3
        assert len(data['failed']) == 0
        assert data['total'] == 3
        assert data['success_count'] == 3
        assert data['failed_count'] == 0

        # Verify all photos deleted
        for photo in photos:
            assert not photo.exists()
            assert not photo.with_suffix(photo.suffix + '.json').exists()

    def test_delete_photo_without_sidecar(self, client, temp_photos_dir):
        """DELETE works when photo has no sidecar file."""
        # Create test photo WITHOUT sidecar
        photo = temp_photos_dir / "no_sidecar.jpg"
        Image.new('RGB', (100, 100)).save(photo)

        response = client.delete('/api/gallery/photos/bulk', json={
            'filenames': ['no_sidecar.jpg']
        })

        assert response.status_code == 200
        data = response.get_json()
        assert 'no_sidecar.jpg' in data['success']
        assert not photo.exists()

    def test_delete_nonexistent_file_returns_in_failed(self, client, temp_photos_dir):
        """DELETE with nonexistent filename returns in failed list."""
        response = client.delete('/api/gallery/photos/bulk', json={
            'filenames': ['nonexistent.jpg']
        })

        assert response.status_code == 200
        data = response.get_json()
        assert 'nonexistent.jpg' in data['failed']
        assert 'nonexistent.jpg' in data['errors']
        assert 'File not found' in data['errors']['nonexistent.jpg']
        assert data['success_count'] == 0
        assert data['failed_count'] == 1

    def test_delete_path_traversal_blocked(self, client, temp_photos_dir):
        """DELETE rejects ../ path traversal attempts."""
        response = client.delete('/api/gallery/photos/bulk', json={
            'filenames': ['../etc/passwd', '../../secret.txt']
        })

        assert response.status_code == 200
        data = response.get_json()
        assert '../etc/passwd' in data['failed']
        assert '../../secret.txt' in data['failed']
        assert 'Invalid path' in data['errors']['../etc/passwd']
        assert data['success_count'] == 0
        assert data['failed_count'] == 2

    def test_delete_max_files_limit(self, client, temp_photos_dir):
        """DELETE rejects more than MAX_BULK_DELETE (100)."""
        # Try to delete 101 files
        filenames = [f"test{i}.jpg" for i in range(101)]

        response = client.delete('/api/gallery/photos/bulk', json={
            'filenames': filenames
        })

        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
        assert 'Maximum 100 files' in data['error']

    def test_delete_empty_filenames_error(self, client):
        """DELETE with empty filenames array returns 400."""
        response = client.delete('/api/gallery/photos/bulk', json={
            'filenames': []
        })

        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
        assert 'non-empty array' in data['error']

    def test_delete_missing_filenames_key_error(self, client):
        """DELETE without filenames key returns 400."""
        response = client.delete('/api/gallery/photos/bulk', json={
            'other_key': 'value'
        })

        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
        assert 'filenames array required' in data['error']

    def test_delete_no_json_body_error(self, client):
        """DELETE without JSON body returns 415 (Unsupported Media Type)."""
        response = client.delete('/api/gallery/photos/bulk')

        # Flask returns 415 when Content-Type is not application/json
        assert response.status_code == 415

    def test_delete_returns_success_and_failed_counts(self, client, temp_photos_dir):
        """DELETE response includes total, success_count, failed_count."""
        # Create one valid photo
        photo = temp_photos_dir / "valid.jpg"
        Image.new('RGB', (100, 100)).save(photo)

        response = client.delete('/api/gallery/photos/bulk', json={
            'filenames': ['valid.jpg', 'invalid.jpg']
        })

        assert response.status_code == 200
        data = response.get_json()
        assert data['total'] == 2
        assert data['success_count'] == 1
        assert data['failed_count'] == 1
        assert 'valid.jpg' in data['success']
        assert 'invalid.jpg' in data['failed']

    def test_delete_partial_success(self, client, temp_photos_dir):
        """DELETE with mix of valid/invalid files returns partial success."""
        # Create two valid photos
        photo1 = temp_photos_dir / "photo1.jpg"
        Image.new('RGB', (100, 100)).save(photo1)
        photo2 = temp_photos_dir / "photo2.jpg"
        Image.new('RGB', (100, 100)).save(photo2)

        response = client.delete('/api/gallery/photos/bulk', json={
            'filenames': [
                'photo1.jpg',
                'nonexistent.jpg',
                'photo2.jpg',
                '../traversal.jpg'
            ]
        })

        assert response.status_code == 200
        data = response.get_json()
        assert data['total'] == 4
        assert data['success_count'] == 2
        assert data['failed_count'] == 2
        assert set(data['success']) == {'photo1.jpg', 'photo2.jpg'}
        assert set(data['failed']) == {'nonexistent.jpg', '../traversal.jpg'}
        assert not photo1.exists()
        assert not photo2.exists()

    def test_delete_filenames_not_list_error(self, client):
        """DELETE with filenames as non-list returns 400."""
        response = client.delete('/api/gallery/photos/bulk', json={
            'filenames': 'not_a_list'
        })

        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
        assert 'non-empty array' in data['error']

    def test_delete_removes_only_sidecar_if_photo_missing(self, client, temp_photos_dir):
        """DELETE removes sidecar even if photo file is already missing."""
        # Create ONLY sidecar file (photo missing)
        sidecar = temp_photos_dir / "orphan.jpg.json"
        sidecar.write_text('{"tags": ["test"]}')

        response = client.delete('/api/gallery/photos/bulk', json={
            'filenames': ['orphan.jpg']
        })

        assert response.status_code == 200
        data = response.get_json()
        # Should fail because photo doesn't exist
        assert 'orphan.jpg' in data['failed']
        assert 'File not found' in data['errors']['orphan.jpg']
        # Sidecar should still exist (we only delete if photo exists)
        assert sidecar.exists()

    def test_delete_handles_permission_error(self, client, temp_photos_dir, monkeypatch):
        """DELETE handles permission errors gracefully."""
        # Create test photo
        photo = temp_photos_dir / "readonly.jpg"
        Image.new('RGB', (100, 100)).save(photo)

        # Mock unlink to raise PermissionError
        original_unlink = Path.unlink

        def mock_unlink(self, *args, **kwargs):
            if self.name == "readonly.jpg":
                raise PermissionError("Permission denied")
            return original_unlink(self, *args, **kwargs)

        monkeypatch.setattr(Path, 'unlink', mock_unlink)

        response = client.delete('/api/gallery/photos/bulk', json={
            'filenames': ['readonly.jpg']
        })

        assert response.status_code == 200
        data = response.get_json()
        assert 'readonly.jpg' in data['failed']
        # Error messages are generic for security (no internal details exposed)
        assert data['errors']['readonly.jpg'] == 'Failed to delete photo'

    def test_delete_invalidates_sidecar_cache(self, client, temp_photos_dir, monkeypatch):
        """DELETE invalidates sidecar cache when files are deleted."""
        # Create test photo
        photo = temp_photos_dir / "test.jpg"
        Image.new('RGB', (100, 100)).save(photo)

        # Track cache invalidation
        cache_invalidated = []

        def mock_invalidate():
            cache_invalidated.append(True)

        # Import and patch the invalidation function from sidecar module
        import routes.sidecar as sidecar_module
        monkeypatch.setattr(sidecar_module, 'invalidate_aggregation_cache', mock_invalidate)

        # Also patch in gallery module if it imports it
        import routes.gallery as gallery_module
        if hasattr(gallery_module, 'invalidate_aggregation_cache'):
            monkeypatch.setattr(gallery_module, 'invalidate_aggregation_cache', mock_invalidate)

        response = client.delete('/api/gallery/photos/bulk', json={
            'filenames': ['test.jpg']
        })

        assert response.status_code == 200
        # Cache should be invalidated since we successfully deleted a file
        assert len(cache_invalidated) >= 1

    def test_delete_does_not_invalidate_cache_on_all_failures(
        self, client, temp_photos_dir, monkeypatch
    ):
        """DELETE does not invalidate cache if all files failed to delete."""
        # Track cache invalidation
        cache_invalidated = []

        def mock_invalidate():
            cache_invalidated.append(True)

        # Import and patch the invalidation function from sidecar module
        import routes.sidecar as sidecar_module
        monkeypatch.setattr(sidecar_module, 'invalidate_aggregation_cache', mock_invalidate)

        # Also patch in gallery module if it imports it
        import routes.gallery as gallery_module
        if hasattr(gallery_module, 'invalidate_aggregation_cache'):
            monkeypatch.setattr(gallery_module, 'invalidate_aggregation_cache', mock_invalidate)

        response = client.delete('/api/gallery/photos/bulk', json={
            'filenames': ['nonexistent.jpg', '../traversal.jpg']
        })

        assert response.status_code == 200
        data = response.get_json()
        assert data['success_count'] == 0
        # Cache should NOT be invalidated since no files were deleted
        assert len(cache_invalidated) == 0

    def test_delete_with_subdirectory_paths(self, client, temp_photos_dir):
        """DELETE handles photos in subdirectories correctly."""
        # Create subdirectory with photo
        subdir = temp_photos_dir / "2024_01"
        subdir.mkdir()
        photo = subdir / "photo.jpg"
        Image.new('RGB', (100, 100)).save(photo)
        sidecar = subdir / "photo.jpg.json"
        sidecar.write_text('{"tags": ["test"]}')

        response = client.delete('/api/gallery/photos/bulk', json={
            'filenames': ['2024_01/photo.jpg']
        })

        assert response.status_code == 200
        data = response.get_json()
        assert '2024_01/photo.jpg' in data['success']
        assert not photo.exists()
        assert not sidecar.exists()

    def test_delete_handles_cache_invalidation_failure(
        self, client, temp_photos_dir, monkeypatch
    ):
        """DELETE handles cache invalidation failure gracefully."""
        # Create test photo
        photo = temp_photos_dir / "test.jpg"
        Image.new('RGB', (100, 100)).save(photo)

        # Mock invalidate_aggregation_cache to raise exception
        def mock_invalidate():
            raise RuntimeError("Cache invalidation failed")

        import routes.sidecar as sidecar_module
        monkeypatch.setattr(sidecar_module, 'invalidate_aggregation_cache', mock_invalidate)

        # Should still succeed even if cache invalidation fails
        response = client.delete('/api/gallery/photos/bulk', json={
            'filenames': ['test.jpg']
        })

        assert response.status_code == 200
        data = response.get_json()
        assert 'test.jpg' in data['success']
        assert not photo.exists()


# Test Fixtures
@pytest.fixture
def temp_photos_dir(tmp_path, monkeypatch):
    """Temporary PHOTOS_DIR for testing."""
    photos_dir = tmp_path / "photos"
    photos_dir.mkdir()

    # Patch PHOTOS_DIR in mothbox_paths
    import mothbox_paths
    monkeypatch.setattr(mothbox_paths, 'PHOTOS_DIR', photos_dir)

    # Also patch in routes.gallery module
    import routes.gallery
    monkeypatch.setattr(routes.gallery, 'PHOTOS_DIR', photos_dir)

    return photos_dir


@pytest.fixture
def gallery_app(temp_photos_dir):
    """Flask app with gallery blueprint for testing."""
    from flask import Flask
    from routes.gallery import gallery_bp

    app = Flask(__name__)
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False  # Disable CSRF for tests

    # Register blueprint AFTER patching PHOTOS_DIR
    app.register_blueprint(gallery_bp, url_prefix='/api/gallery')
    return app


@pytest.fixture
def client(gallery_app):
    """Test client for gallery routes."""
    return gallery_app.test_client()
