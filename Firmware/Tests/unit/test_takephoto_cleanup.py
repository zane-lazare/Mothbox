"""Tests for TakePhoto.py resource cleanup."""

import pytest


class TestTakePhotoCleanup:
    """Test that TakePhoto.py properly cleans up camera resources."""

    def test_finally_block_includes_picam2_close(self):
        """Verify TakePhoto.py finally block calls picam2.close()."""
        import re
        from pathlib import Path

        # Check 5.x version
        takephoto_5x = Path(__file__).parent.parent.parent / '5.x' / 'TakePhoto.py'
        content_5x = takephoto_5x.read_text()

        # Find the finally block and check for picam2.close()
        finally_match = re.search(r'finally:\s*\n(.*?)(?=\nsys\.exit|$)', content_5x, re.DOTALL)
        assert finally_match, "Could not find finally block in 5.x/TakePhoto.py"

        finally_block = finally_match.group(1)
        assert 'picam2.close()' in finally_block, \
            "5.x/TakePhoto.py finally block must call picam2.close()"

    def test_4x_finally_block_includes_picam2_close(self):
        """Verify 4.x/TakePhoto.py finally block calls picam2.close()."""
        import re
        from pathlib import Path

        # Check 4.x version
        takephoto_4x = Path(__file__).parent.parent.parent / '4.x' / 'TakePhoto.py'
        content_4x = takephoto_4x.read_text()

        # Find the finally block and check for picam2.close()
        finally_match = re.search(r'finally:\s*\n(.*?)(?=\nsys\.exit|$)', content_4x, re.DOTALL)
        assert finally_match, "Could not find finally block in 4.x/TakePhoto.py"

        finally_block = finally_match.group(1)
        assert 'picam2.close()' in finally_block, \
            "4.x/TakePhoto.py finally block must call picam2.close()"
