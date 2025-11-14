#!/usr/bin/env python3
"""
Test to debug why sample_photos fixture creates empty directory
"""
import pytest
from pathlib import Path
import time


@pytest.fixture
def sample_photos_debug(temp_photos_dir, capsys):
    """Debug version of sample_photos fixture"""
    from PIL import Image

    print(f"\n=== sample_photos_debug STARTING ===", flush=True)
    print(f"temp_photos_dir = {temp_photos_dir}", flush=True)
    print(f"temp_photos_dir exists: {temp_photos_dir.exists()}", flush=True)
    print(f"temp_photos_dir is_dir: {temp_photos_dir.is_dir()}", flush=True)

    photos = []
    for i in range(10):
        photo_path = temp_photos_dir / f"photo_{i:03d}.jpg"
        print(f"Creating {photo_path}", flush=True)
        try:
            img = Image.new('RGB', (800, 600), color=(i * 25, 100, 150))
            img.save(photo_path, format='JPEG', quality=85)
            print(f"  Saved successfully, exists: {photo_path.exists()}", flush=True)
            photos.append(photo_path)
        except Exception as e:
            print(f"  ERROR: {e}", flush=True)
            raise

        time.sleep(0.1)

    print(f"=== sample_photos_debug COMPLETE: Created {len(photos)} files ===", flush=True)
    print(f"Directory contents: {list(temp_photos_dir.iterdir())}", flush=True)
    return photos


def test_sample_photos_creation(sample_photos_debug):
    """Test that sample_photos actually creates files"""
    assert len(sample_photos_debug) == 10
    for photo in sample_photos_debug:
        assert photo.exists(), f"Photo {photo} should exist"
