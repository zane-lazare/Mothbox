"""Tests for thumbnail cache memory management."""

import pytest
import re
from pathlib import Path


class TestThumbnailMemoryManagement:
    """Test that thumbnail generation properly releases image resources."""

    def test_thumbnail_cache_uses_context_manager(self):
        """Verify thumbnail_cache.py uses 'with Image.open()' for proper cleanup."""
        # Read the actual source file
        thumbnail_cache_path = (
            Path(__file__).parent.parent.parent
            / 'webui' / 'backend' / 'services' / 'thumbnail_cache.py'
        )
        content = thumbnail_cache_path.read_text()

        # Check for context manager pattern with Image.open
        # This ensures proper resource cleanup via __exit__
        pattern = r'with\s+Image\.open\s*\([^)]+\)\s+as\s+\w+'
        match = re.search(pattern, content)

        assert match is not None, (
            "thumbnail_cache.py must use context manager pattern: "
            "'with Image.open(...) as img:' for proper resource cleanup"
        )

    def test_no_bare_image_open_calls(self):
        """Verify there are no unguarded Image.open() calls."""
        thumbnail_cache_path = (
            Path(__file__).parent.parent.parent
            / 'webui' / 'backend' / 'services' / 'thumbnail_cache.py'
        )
        content = thumbnail_cache_path.read_text()

        # Look for bare Image.open() calls (not in a 'with' statement)
        # This pattern matches "img = Image.open(...)" which is the bad pattern
        bare_pattern = r'^\s*\w+\s*=\s*Image\.open\s*\('
        bare_matches = re.findall(bare_pattern, content, re.MULTILINE)

        assert len(bare_matches) == 0, (
            f"Found {len(bare_matches)} bare Image.open() calls that should use "
            "context manager for proper resource cleanup"
        )
