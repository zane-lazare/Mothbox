"""
Unit tests for series detection library (Issue #110 - Phase 3)

Tests HDR and Focus Bracket photo series detection from filenames.
TDD approach: tests written first, then implementation.

Coverage Target: 90%+
"""

import pytest
from pathlib import Path
from dataclasses import dataclass


# ============================================================================
# Expected Interface (TDD - define before implementation)
# ============================================================================

# Import will fail until implementation exists - that's expected in TDD
try:
    from webui.backend.lib.series_detection import (
        SeriesInfo,
        SeriesType,
        detect_series_type,
        get_series_id,
        group_photos_into_series,
        HDR_PATTERN,
        FB_PATTERN,
    )
    IMPLEMENTATION_EXISTS = True
except ImportError:
    IMPLEMENTATION_EXISTS = False
    # Define stubs for test discovery
    SeriesInfo = None
    SeriesType = None
    detect_series_type = None
    get_series_id = None
    group_photos_into_series = None
    HDR_PATTERN = None
    FB_PATTERN = None


# Skip all tests if implementation doesn't exist yet (TDD red phase)
pytestmark = pytest.mark.skipif(
    not IMPLEMENTATION_EXISTS,
    reason="Implementation not yet created (TDD red phase)"
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def sample_hdr_series(tmp_path):
    """Create sample HDR photo series for testing."""
    base = "moth_2024_01_15__10_00_00"
    photos = []
    for i in range(3):
        p = tmp_path / f"{base}_HDR{i}.jpg"
        p.write_bytes(b'\xFF\xD8\xFF\xE0' + b'\x00' * 100)
        photos.append(p)
    return photos


@pytest.fixture
def sample_fb_series(tmp_path):
    """Create sample Focus Bracket photo series for testing."""
    base = "ManFocus_moth_2024_01_15__11_00_00_000000"
    photos = []
    for i in range(5):
        p = tmp_path / f"{base}_FB{i}.jpg"
        p.write_bytes(b'\xFF\xD8\xFF\xE0' + b'\x00' * 100)
        photos.append(p)
    return photos


@pytest.fixture
def mixed_photos(tmp_path):
    """Create a mix of HDR, FB, and regular photos."""
    photos = []

    # HDR series (3 photos)
    for i in range(3):
        p = tmp_path / f"moth_2024_01_15__10_00_00_HDR{i}.jpg"
        p.write_bytes(b'\xFF\xD8\xFF\xE0' + b'\x00' * 100)
        photos.append(p)

    # Focus bracket series (5 photos)
    for i in range(5):
        p = tmp_path / f"ManFocus_moth_2024_01_15__11_00_00_000000_FB{i}.jpg"
        p.write_bytes(b'\xFF\xD8\xFF\xE0' + b'\x00' * 100)
        photos.append(p)

    # Regular photos (not part of any series)
    regular_names = [
        "moth_2024_01_15__12_00_00.jpg",
        "moth_2024_01_15__13_00_00.jpg",
    ]
    for name in regular_names:
        p = tmp_path / name
        p.write_bytes(b'\xFF\xD8\xFF\xE0' + b'\x00' * 100)
        photos.append(p)

    return photos


# ============================================================================
# Test SeriesInfo Data Class
# ============================================================================

class TestSeriesInfoDataClass:
    """Tests for SeriesInfo data class structure."""

    def test_series_info_has_required_fields(self):
        """SeriesInfo should have series_type, base_name, and index fields."""
        info = SeriesInfo(series_type="hdr", base_name="moth_2024_01_15__10_00_00", index=0)
        assert info.series_type == "hdr"
        assert info.base_name == "moth_2024_01_15__10_00_00"
        assert info.index == 0

    def test_series_info_equality(self):
        """SeriesInfo instances with same values should be equal."""
        info1 = SeriesInfo(series_type="hdr", base_name="test", index=1)
        info2 = SeriesInfo(series_type="hdr", base_name="test", index=1)
        assert info1 == info2

    def test_series_info_different_types_not_equal(self):
        """SeriesInfo with different types should not be equal."""
        info1 = SeriesInfo(series_type="hdr", base_name="test", index=1)
        info2 = SeriesInfo(series_type="focus_bracket", base_name="test", index=1)
        assert info1 != info2


# ============================================================================
# Test HDR Pattern Detection
# ============================================================================

class TestHDRDetection:
    """Tests for HDR series detection."""

    def test_detect_hdr_basic_pattern(self):
        """Detect basic HDR filename pattern."""
        result = detect_series_type("moth_2024_01_15__10_00_00_HDR0.jpg")
        assert result is not None
        assert result.series_type == "hdr"
        assert result.index == 0
        assert "moth_2024_01_15__10_00_00" in result.base_name

    def test_detect_hdr_index_1(self):
        """Detect HDR with index 1."""
        result = detect_series_type("moth_2024_01_15__10_00_00_HDR1.jpg")
        assert result is not None
        assert result.series_type == "hdr"
        assert result.index == 1

    def test_detect_hdr_index_2(self):
        """Detect HDR with index 2."""
        result = detect_series_type("moth_2024_01_15__10_00_00_HDR2.jpg")
        assert result is not None
        assert result.series_type == "hdr"
        assert result.index == 2

    def test_detect_hdr_double_digit_index(self):
        """Detect HDR with double-digit index (if supported)."""
        result = detect_series_type("moth_2024_01_15__10_00_00_HDR10.jpg")
        assert result is not None
        assert result.series_type == "hdr"
        assert result.index == 10

    def test_detect_hdr_case_insensitive_jpg(self):
        """Detect HDR with uppercase JPG extension."""
        result = detect_series_type("moth_2024_01_15__10_00_00_HDR0.JPG")
        assert result is not None
        assert result.series_type == "hdr"

    def test_detect_hdr_case_insensitive_hdr(self):
        """Detect HDR with lowercase hdr suffix."""
        result = detect_series_type("moth_2024_01_15__10_00_00_hdr0.jpg")
        assert result is not None
        assert result.series_type == "hdr"

    def test_detect_hdr_with_mb_prefix(self):
        """Detect HDR with 'mb' prefix (from TakePhoto_noAuto.py)."""
        result = detect_series_type("mb12345_2024_01_15__10_00_00_HDR0.jpg")
        assert result is not None
        assert result.series_type == "hdr"
        assert result.index == 0

    def test_detect_hdr_png_extension(self):
        """Detect HDR with PNG extension (supported by TakePhoto.py)."""
        result = detect_series_type("moth_2024_01_15__10_00_00_HDR0.png")
        assert result is not None
        assert result.series_type == "hdr"

    def test_hdr_base_name_extraction(self):
        """HDR base_name should exclude the _HDR{N} suffix."""
        result = detect_series_type("moth_2024_01_15__10_00_00_HDR1.jpg")
        assert result is not None
        # Base name should be the part before _HDR
        assert result.base_name == "moth_2024_01_15__10_00_00"


# ============================================================================
# Test Focus Bracket Pattern Detection
# ============================================================================

class TestFocusBracketDetection:
    """Tests for Focus Bracket series detection."""

    def test_detect_fb_basic_pattern(self):
        """Detect basic focus bracket filename pattern."""
        result = detect_series_type("ManFocus_moth_2024_01_15__11_00_00_000000_FB0.jpg")
        assert result is not None
        assert result.series_type == "focus_bracket"
        assert result.index == 0

    def test_detect_fb_index_4(self):
        """Detect focus bracket with index 4."""
        result = detect_series_type("ManFocus_moth_2024_01_15__11_00_00_000000_FB4.jpg")
        assert result is not None
        assert result.series_type == "focus_bracket"
        assert result.index == 4

    def test_detect_fb_case_insensitive_jpg(self):
        """Detect FB with uppercase JPG extension."""
        result = detect_series_type("ManFocus_moth_2024_01_15__11_00_00_000000_FB0.JPG")
        assert result is not None
        assert result.series_type == "focus_bracket"

    def test_detect_fb_case_insensitive_fb(self):
        """Detect FB with lowercase fb suffix."""
        result = detect_series_type("ManFocus_moth_2024_01_15__11_00_00_000000_fb0.jpg")
        assert result is not None
        assert result.series_type == "focus_bracket"

    def test_detect_fb_without_microseconds(self):
        """Detect FB without microseconds in timestamp."""
        result = detect_series_type("ManFocus_moth_2024_01_15__11_00_00_FB0.jpg")
        assert result is not None
        assert result.series_type == "focus_bracket"
        assert result.index == 0

    def test_detect_16mp_manfocus(self):
        """Detect 16MP ManFocus pattern (from TakePhoto16mp.py)."""
        result = detect_series_type("16MPManFocus_moth_2024_01_15__11_00_00_HDR0.jpg")
        # This is actually HDR, not FB - from TakePhoto16mp.py naming
        assert result is not None
        assert result.series_type == "hdr"

    def test_fb_base_name_extraction(self):
        """FB base_name should exclude the _FB{N} suffix."""
        result = detect_series_type("ManFocus_moth_2024_01_15__11_00_00_000000_FB2.jpg")
        assert result is not None
        assert result.base_name == "ManFocus_moth_2024_01_15__11_00_00_000000"


# ============================================================================
# Test Non-Series Photos
# ============================================================================

class TestNonSeriesPhotos:
    """Tests for photos that are NOT part of any series."""

    def test_regular_photo_not_series(self):
        """Regular photo without HDR/FB suffix returns None."""
        result = detect_series_type("moth_2024_01_15__12_00_00.jpg")
        assert result is None

    def test_photo_with_number_not_series(self):
        """Photo with trailing number but not HDR/FB pattern returns None."""
        result = detect_series_type("moth_2024_01_15__12_00_00_1.jpg")
        assert result is None

    def test_photo_hdr_in_name_but_not_pattern(self):
        """Photo with 'HDR' in name but not proper pattern returns None."""
        result = detect_series_type("HDR_moth_2024_01_15__12_00_00.jpg")
        assert result is None

    def test_non_image_file(self):
        """Non-image file returns None."""
        result = detect_series_type("moth_2024_01_15__12_00_00.txt")
        assert result is None

    def test_empty_filename(self):
        """Empty filename returns None."""
        result = detect_series_type("")
        assert result is None

    def test_none_filename(self):
        """None filename returns None without error."""
        result = detect_series_type(None)
        assert result is None


# ============================================================================
# Test get_series_id Function
# ============================================================================

class TestGetSeriesId:
    """Tests for get_series_id function (used for grouping)."""

    def test_hdr_series_id(self):
        """HDR photos in same series return same ID."""
        id0 = get_series_id("moth_2024_01_15__10_00_00_HDR0.jpg")
        id1 = get_series_id("moth_2024_01_15__10_00_00_HDR1.jpg")
        id2 = get_series_id("moth_2024_01_15__10_00_00_HDR2.jpg")

        assert id0 is not None
        assert id0 == id1 == id2

    def test_fb_series_id(self):
        """FB photos in same series return same ID."""
        id0 = get_series_id("ManFocus_moth_2024_01_15__11_00_00_000000_FB0.jpg")
        id1 = get_series_id("ManFocus_moth_2024_01_15__11_00_00_000000_FB1.jpg")

        assert id0 is not None
        assert id0 == id1

    def test_different_series_different_ids(self):
        """Different series return different IDs."""
        hdr_id = get_series_id("moth_2024_01_15__10_00_00_HDR0.jpg")
        fb_id = get_series_id("ManFocus_moth_2024_01_15__11_00_00_000000_FB0.jpg")

        assert hdr_id != fb_id

    def test_regular_photo_no_series_id(self):
        """Regular photo returns None series ID."""
        result = get_series_id("moth_2024_01_15__12_00_00.jpg")
        assert result is None

    def test_series_id_includes_type(self):
        """Series ID should include type prefix for clarity."""
        hdr_id = get_series_id("moth_2024_01_15__10_00_00_HDR0.jpg")
        fb_id = get_series_id("ManFocus_moth_2024_01_15__11_00_00_000000_FB0.jpg")

        assert hdr_id.startswith("hdr_") or "hdr" in hdr_id.lower()
        assert fb_id.startswith("fb_") or "focus" in fb_id.lower()


# ============================================================================
# Test group_photos_into_series Function
# ============================================================================

class TestGroupPhotosIntoSeries:
    """Tests for grouping photos by series."""

    def test_group_hdr_series(self, sample_hdr_series):
        """Group HDR photos into single series."""
        groups = group_photos_into_series(sample_hdr_series)

        # Should have exactly 1 series
        assert len(groups) == 1

        # Series should contain all 3 photos
        series_id = list(groups.keys())[0]
        assert len(groups[series_id]) == 3

    def test_group_fb_series(self, sample_fb_series):
        """Group focus bracket photos into single series."""
        groups = group_photos_into_series(sample_fb_series)

        # Should have exactly 1 series
        assert len(groups) == 1

        # Series should contain all 5 photos
        series_id = list(groups.keys())[0]
        assert len(groups[series_id]) == 5

    def test_group_mixed_photos(self, mixed_photos, tmp_path):
        """Group mixed photos correctly separates series and singles."""
        groups = group_photos_into_series(mixed_photos)

        # Should have 2 series (HDR + FB) and 2 singles grouped under None/individual keys
        # Regular photos should either be excluded or grouped under None key
        hdr_count = 0
        fb_count = 0

        for series_id, photos in groups.items():
            if series_id and "hdr" in series_id.lower():
                hdr_count = len(photos)
            elif series_id and ("fb" in series_id.lower() or "focus" in series_id.lower()):
                fb_count = len(photos)

        assert hdr_count == 3, "HDR series should have 3 photos"
        assert fb_count == 5, "FB series should have 5 photos"

    def test_group_empty_list(self):
        """Empty list returns empty dict."""
        groups = group_photos_into_series([])
        assert groups == {}

    def test_group_no_series_photos(self, tmp_path):
        """Photos with no series patterns returns empty dict or grouped under None."""
        photos = []
        for name in ["photo1.jpg", "photo2.jpg"]:
            p = tmp_path / name
            p.write_bytes(b'\xFF\xD8\xFF\xE0')
            photos.append(p)

        groups = group_photos_into_series(photos)

        # Should have no series (empty dict) or photos under None key
        for series_id, photos in groups.items():
            if series_id is not None:
                assert False, f"Unexpected series: {series_id}"

    def test_group_preserves_order(self, sample_hdr_series):
        """Grouped photos should be sorted by index."""
        # Shuffle the input
        shuffled = [sample_hdr_series[2], sample_hdr_series[0], sample_hdr_series[1]]
        groups = group_photos_into_series(shuffled)

        series_id = list(groups.keys())[0]
        photos = groups[series_id]

        # Photos should be sorted by index (HDR0, HDR1, HDR2)
        for i, photo in enumerate(photos):
            assert f"HDR{i}" in photo.name

    def test_group_accepts_path_strings(self, tmp_path):
        """Function accepts both Path objects and strings."""
        p = tmp_path / "moth_2024_01_15__10_00_00_HDR0.jpg"
        p.write_bytes(b'\xFF\xD8\xFF\xE0')

        # Test with string
        groups = group_photos_into_series([str(p)])
        assert len(groups) == 1

    def test_group_cross_directory(self, tmp_path):
        """Series spanning directories should be grouped together."""
        # Create HDR series in two different directories
        dir1 = tmp_path / "2024-01-15"
        dir2 = tmp_path / "2024-01-16"
        dir1.mkdir()
        dir2.mkdir()

        # Same series base name, different directories
        base = "moth_2024_01_15__23_59_59"
        p1 = dir1 / f"{base}_HDR0.jpg"
        p2 = dir2 / f"{base}_HDR1.jpg"  # Could happen if capture spans midnight
        p1.write_bytes(b'\xFF\xD8\xFF\xE0')
        p2.write_bytes(b'\xFF\xD8\xFF\xE0')

        groups = group_photos_into_series([p1, p2])

        # Should group by base_name, not directory
        assert len(groups) == 1
        series_id = list(groups.keys())[0]
        assert len(groups[series_id]) == 2


# ============================================================================
# Test Regex Pattern Constants
# ============================================================================

class TestRegexPatterns:
    """Tests for regex pattern constants."""

    def test_hdr_pattern_compiles(self):
        """HDR_PATTERN should be a compiled regex."""
        import re
        assert isinstance(HDR_PATTERN, re.Pattern)

    def test_fb_pattern_compiles(self):
        """FB_PATTERN should be a compiled regex."""
        import re
        assert isinstance(FB_PATTERN, re.Pattern)

    def test_hdr_pattern_case_insensitive(self):
        """HDR_PATTERN should be case-insensitive."""
        assert HDR_PATTERN.flags & 2  # re.IGNORECASE = 2


# ============================================================================
# Test Edge Cases
# ============================================================================

class TestEdgeCases:
    """Edge case tests for series detection."""

    def test_very_long_filename(self):
        """Handle very long filenames gracefully."""
        long_name = "a" * 200 + "_2024_01_15__10_00_00_HDR0.jpg"
        result = detect_series_type(long_name)
        assert result is not None
        assert result.series_type == "hdr"

    def test_special_characters_in_name(self):
        """Handle special characters in computer name."""
        result = detect_series_type("moth-box_v2_2024_01_15__10_00_00_HDR0.jpg")
        assert result is not None
        assert result.series_type == "hdr"

    def test_unicode_in_filename(self):
        """Handle unicode characters in filename."""
        result = detect_series_type("móth_2024_01_15__10_00_00_HDR0.jpg")
        assert result is not None
        assert result.series_type == "hdr"

    def test_path_object_input(self):
        """detect_series_type should handle Path objects."""
        result = detect_series_type(Path("moth_2024_01_15__10_00_00_HDR0.jpg"))
        assert result is not None
        assert result.series_type == "hdr"

    def test_full_path_input(self):
        """detect_series_type should extract filename from full path."""
        result = detect_series_type("/var/lib/mothbox/photos/2024-01-15/moth_2024_01_15__10_00_00_HDR0.jpg")
        assert result is not None
        assert result.series_type == "hdr"


# ============================================================================
# Performance Tests (lightweight)
# ============================================================================

class TestPerformance:
    """Lightweight performance tests (detailed tests in performance/)."""

    def test_single_detection_fast(self):
        """Single detection should complete in <10ms."""
        import time

        start = time.perf_counter()
        for _ in range(100):
            detect_series_type("moth_2024_01_15__10_00_00_HDR0.jpg")
        elapsed = time.perf_counter() - start

        avg_ms = (elapsed / 100) * 1000
        assert avg_ms < 10, f"Average detection time {avg_ms:.2f}ms exceeds 10ms target"

    def test_grouping_1000_photos_fast(self, tmp_path):
        """Grouping 1000 photos should complete in <100ms."""
        import time

        # Generate 1000 filenames (don't need actual files for string-based test)
        filenames = []
        for series in range(100):  # 100 series
            for i in range(10):  # 10 photos each
                filenames.append(f"moth_2024_01_15__{series:02d}_00_00_HDR{i}.jpg")

        # Create paths (but not actual files - just test grouping logic)
        paths = [tmp_path / f for f in filenames]

        start = time.perf_counter()
        groups = group_photos_into_series(paths)
        elapsed = time.perf_counter() - start

        elapsed_ms = elapsed * 1000
        assert elapsed_ms < 100, f"Grouping time {elapsed_ms:.2f}ms exceeds 100ms target"
        assert len(groups) == 100, "Should have 100 series"
