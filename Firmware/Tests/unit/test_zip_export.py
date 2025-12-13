"""
Unit tests for ZIP export library (webui.backend.lib.zip_export).

Tests cover:
- ZipExportOptions dataclass defaults and customization
- ZipExportResult dataclass structure
- ZIP file creation with photos
- XMP sidecar inclusion
- Manifest.json generation
- Summary.csv generation
- Streaming ZIP generation
- ZIP integrity validation
- Error handling (missing files, permission errors)
- Performance: 50 photos should complete in <5 seconds
- Edge cases: empty photo list, single photo, special characters in filenames
"""

import csv
import json
import time
from collections.abc import Generator
from datetime import datetime
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile, is_zipfile

from webui.backend.lib.zip_export import (
    MANIFEST_FILENAME,
    SUMMARY_FILENAME,
    ZIP_BUFFER_SIZE,
    ZIP_COMPRESSION_LEVEL,
    PhotoFileError,
    XMPGenerationError,
    ZipExportError,
    ZipExportOptions,
    ZipExportResult,
    ZipWriteError,
    add_photo_to_zip,
    create_zip_export,
    estimate_zip_size,
    generate_csv_summary,
    generate_manifest,
    stream_zip_export,
    validate_zip_integrity,
)
from webui.backend.services.export_metadata_service import ExportMetadata

# ============================================================================
# Test Helpers
# ============================================================================


def create_test_jpeg(path: Path, size: int = 1024) -> None:
    """Create minimal valid JPEG for testing."""
    # JPEG header + padding
    header = b'\xFF\xD8\xFF\xE0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00'
    footer = b'\xFF\xD9'
    padding = b'\x00' * (size - len(header) - len(footer))
    path.write_bytes(header + padding + footer)


def create_test_metadata(
    filename: str = "moth_2024_01_15__10_00_00.jpg",
    latitude: float = 37.7749,
    longitude: float = -122.4194,
    timestamp: str = "2024-01-15T10:00:00",
    species: str = "Actias luna",
    species_common_name: str = "Luna Moth",
    tags: list[str] | None = None,
) -> ExportMetadata:
    """Create test ExportMetadata instance."""
    return ExportMetadata(
        photo_path=f"/photos/{filename}",
        filename=filename,
        latitude=latitude,
        longitude=longitude,
        timestamp=timestamp,
        species=species,
        species_common_name=species_common_name,
        tags=tags or ["moth", "lepidoptera"],
        altitude=350.5,
        gps_accuracy=5.0,
        notes="Test observation",
    )


# ============================================================================
# Test Constants
# ============================================================================


class TestConstants:
    """Test that constants are defined correctly."""

    def test_zip_compression_level(self):
        """ZIP_COMPRESSION_LEVEL should be 0 for no compression."""
        assert ZIP_COMPRESSION_LEVEL == 0

    def test_zip_buffer_size(self):
        """ZIP_BUFFER_SIZE should be 8KB."""
        assert ZIP_BUFFER_SIZE == 8192

    def test_manifest_filename(self):
        """MANIFEST_FILENAME should be 'manifest.json'."""
        assert MANIFEST_FILENAME == "manifest.json"

    def test_summary_filename(self):
        """SUMMARY_FILENAME should be 'summary.csv'."""
        assert SUMMARY_FILENAME == "summary.csv"


# ============================================================================
# Test ZipExportOptions Dataclass
# ============================================================================


class TestZipExportOptions:
    """Test ZipExportOptions dataclass."""

    def test_default_values(self):
        """Test default option values."""
        options = ZipExportOptions()
        assert options.include_xmp_sidecars is True
        assert options.include_manifest is True
        assert options.include_csv_summary is True
        assert options.compression_level == 0
        assert options.flatten_structure is False

    def test_custom_values(self):
        """Test custom option values."""
        options = ZipExportOptions(
            include_xmp_sidecars=False,
            include_manifest=False,
            include_csv_summary=False,
            compression_level=6,
            flatten_structure=True,
        )
        assert options.include_xmp_sidecars is False
        assert options.include_manifest is False
        assert options.include_csv_summary is False
        assert options.compression_level == 6
        assert options.flatten_structure is True

    def test_partial_customization(self):
        """Test partial option customization."""
        options = ZipExportOptions(include_xmp_sidecars=False)
        assert options.include_xmp_sidecars is False
        assert options.include_manifest is True  # default
        assert options.include_csv_summary is True  # default


# ============================================================================
# Test ZipExportResult Dataclass
# ============================================================================


class TestZipExportResult:
    """Test ZipExportResult dataclass."""

    def test_success_result(self):
        """Test successful result structure."""
        result = ZipExportResult(
            success=True,
            zip_path=Path("/tmp/export.zip"),
            zip_size_bytes=1024000,
            photo_count=10,
            xmp_count=10,
            errors=[],
            took_ms=1234.5,
        )
        assert result.success is True
        assert result.zip_path == Path("/tmp/export.zip")
        assert result.zip_size_bytes == 1024000
        assert result.photo_count == 10
        assert result.xmp_count == 10
        assert result.errors == []
        assert result.took_ms == 1234.5

    def test_failure_result(self):
        """Test failure result structure."""
        result = ZipExportResult(
            success=False,
            zip_path=None,
            zip_size_bytes=0,
            photo_count=0,
            xmp_count=0,
            errors=[{"error": "File not found"}],
            took_ms=50.0,
        )
        assert result.success is False
        assert result.zip_path is None
        assert result.zip_size_bytes == 0
        assert result.errors == [{"error": "File not found"}]


# ============================================================================
# Test generate_csv_summary
# ============================================================================


class TestGenerateCSVSummary:
    """Test CSV summary generation."""

    def test_generate_csv_summary_single_photo(self):
        """Test CSV generation with single photo."""
        metadata_list = [create_test_metadata()]
        csv_content = generate_csv_summary(metadata_list)

        # Parse CSV
        lines = csv_content.strip().split('\n')
        assert len(lines) == 2  # header + 1 data row

        # Check header
        reader = csv.DictReader(lines)
        rows = list(reader)
        assert len(rows) == 1
        row = rows[0]
        assert row['filename'] == "moth_2024_01_15__10_00_00.jpg"
        assert row['timestamp'] == "2024-01-15T10:00:00"
        assert row['latitude'] == "37.7749"
        assert row['longitude'] == "-122.4194"
        assert row['species'] == "Actias luna"
        assert row['species_common_name'] == "Luna Moth"
        assert row['tags'] == "moth; lepidoptera"

    def test_generate_csv_summary_multiple_photos(self):
        """Test CSV generation with multiple photos."""
        metadata_list = [
            create_test_metadata(filename="photo1.jpg", species="Species A"),
            create_test_metadata(filename="photo2.jpg", species="Species B"),
            create_test_metadata(filename="photo3.jpg", species="Species C"),
        ]
        csv_content = generate_csv_summary(metadata_list)

        lines = csv_content.strip().split('\n')
        assert len(lines) == 4  # header + 3 data rows

    def test_generate_csv_summary_empty_list(self):
        """Test CSV generation with empty metadata list."""
        csv_content = generate_csv_summary([])
        lines = csv_content.strip().split('\n')
        assert len(lines) == 1  # header only

    def test_generate_csv_summary_missing_optional_fields(self):
        """Test CSV generation with missing optional fields."""
        metadata = create_test_metadata()
        metadata.species = None
        metadata.species_common_name = None
        metadata.tags = None

        csv_content = generate_csv_summary([metadata])
        reader = csv.DictReader(csv_content.strip().split('\n'))
        rows = list(reader)
        assert rows[0]['species'] == ""
        assert rows[0]['species_common_name'] == ""
        assert rows[0]['tags'] == ""

    def test_generate_csv_summary_special_characters(self):
        """Test CSV generation with special characters in fields."""
        metadata = create_test_metadata(
            filename="moth,with,commas.jpg",
            species="Species \"with quotes\"",
            tags=["tag,with,comma", "tag;with;semicolon"],
        )
        csv_content = generate_csv_summary([metadata])
        reader = csv.DictReader(csv_content.strip().split('\n'))
        rows = list(reader)
        assert rows[0]['filename'] == "moth,with,commas.jpg"
        assert rows[0]['species'] == 'Species "with quotes"'


# ============================================================================
# Test generate_manifest
# ============================================================================


class TestGenerateManifest:
    """Test manifest generation."""

    def test_generate_manifest_structure(self):
        """Test manifest JSON structure."""
        photo_paths = [Path("/photos/moth1.jpg")]
        metadata_list = [create_test_metadata(filename="moth1.jpg")]
        options = ZipExportOptions()

        manifest = generate_manifest(photo_paths, metadata_list, options)

        assert manifest['version'] == "1.0"
        assert manifest['generator'] == "Mothbox"
        assert 'generator_version' in manifest
        assert 'created_at' in manifest
        assert manifest['photo_count'] == 1
        assert 'total_size_bytes' in manifest
        assert len(manifest['photos']) == 1

    def test_generate_manifest_photo_details(self):
        """Test manifest photo details."""
        photo_paths = [Path("/photos/moth1.jpg")]
        metadata_list = [create_test_metadata(filename="moth1.jpg")]
        options = ZipExportOptions()

        manifest = generate_manifest(photo_paths, metadata_list, options)
        photo = manifest['photos'][0]

        assert photo['filename'] == "moth1.jpg"
        assert photo['xmp_sidecar'] == "moth1.xmp"
        assert photo['latitude'] == 37.7749
        assert photo['longitude'] == -122.4194
        assert photo['timestamp'] == "2024-01-15T10:00:00"
        assert photo['species'] == "Actias luna"

    def test_generate_manifest_multiple_photos(self):
        """Test manifest with multiple photos."""
        photo_paths = [
            Path("/photos/moth1.jpg"),
            Path("/photos/moth2.jpg"),
            Path("/photos/moth3.jpg"),
        ]
        metadata_list = [
            create_test_metadata(filename="moth1.jpg"),
            create_test_metadata(filename="moth2.jpg"),
            create_test_metadata(filename="moth3.jpg"),
        ]
        options = ZipExportOptions()

        manifest = generate_manifest(photo_paths, metadata_list, options)
        assert manifest['photo_count'] == 3
        assert len(manifest['photos']) == 3

    def test_generate_manifest_without_xmp(self):
        """Test manifest when XMP sidecars are disabled."""
        photo_paths = [Path("/photos/moth1.jpg")]
        metadata_list = [create_test_metadata(filename="moth1.jpg")]
        options = ZipExportOptions(include_xmp_sidecars=False)

        manifest = generate_manifest(photo_paths, metadata_list, options)
        photo = manifest['photos'][0]

        assert 'xmp_sidecar' not in photo or photo['xmp_sidecar'] is None

    def test_generate_manifest_created_at_iso_format(self):
        """Test manifest created_at is in ISO format."""
        photo_paths = [Path("/photos/moth1.jpg")]
        metadata_list = [create_test_metadata()]
        options = ZipExportOptions()

        manifest = generate_manifest(photo_paths, metadata_list, options)

        # Verify ISO 8601 format
        created_at = manifest['created_at']
        datetime.fromisoformat(created_at.replace('Z', '+00:00'))  # Should not raise


# ============================================================================
# Test add_photo_to_zip
# ============================================================================


class TestAddPhotoToZip:
    """Test adding photos to ZIP."""

    def test_add_photo_to_zip_with_xmp(self, tmp_path):
        """Test adding photo with XMP sidecar."""
        photo_path = tmp_path / "moth.jpg"
        create_test_jpeg(photo_path)
        metadata = create_test_metadata(filename="moth.jpg")

        zip_path = tmp_path / "test.zip"
        with ZipFile(zip_path, 'w') as zf:
            result = add_photo_to_zip(zf, photo_path, metadata, include_xmp=True)

        assert result['success'] is True
        assert result['filename'] == "moth.jpg"
        assert result['xmp_filename'] == "moth.xmp"
        assert result['size'] > 0
        assert 'error' not in result

        # Verify ZIP contents
        with ZipFile(zip_path, 'r') as zf:
            assert "moth.jpg" in zf.namelist()
            assert "moth.xmp" in zf.namelist()

    def test_add_photo_to_zip_without_xmp(self, tmp_path):
        """Test adding photo without XMP sidecar."""
        photo_path = tmp_path / "moth.jpg"
        create_test_jpeg(photo_path)
        metadata = create_test_metadata(filename="moth.jpg")

        zip_path = tmp_path / "test.zip"
        with ZipFile(zip_path, 'w') as zf:
            result = add_photo_to_zip(zf, photo_path, metadata, include_xmp=False)

        assert result['success'] is True
        assert result['filename'] == "moth.jpg"
        assert result['xmp_filename'] is None

        # Verify ZIP contents
        with ZipFile(zip_path, 'r') as zf:
            assert "moth.jpg" in zf.namelist()
            assert "moth.xmp" not in zf.namelist()

    def test_add_photo_to_zip_missing_file(self, tmp_path):
        """Test adding missing photo file."""
        photo_path = tmp_path / "missing.jpg"
        metadata = create_test_metadata(filename="missing.jpg")

        zip_path = tmp_path / "test.zip"
        with ZipFile(zip_path, 'w') as zf:
            result = add_photo_to_zip(zf, photo_path, metadata, include_xmp=True)

        assert result['success'] is False
        assert 'error' in result

    def test_add_photo_to_zip_special_characters(self, tmp_path):
        """Test adding photo with special characters in filename."""
        photo_path = tmp_path / "moth with spaces & special.jpg"
        create_test_jpeg(photo_path)
        metadata = create_test_metadata(filename="moth with spaces & special.jpg")

        zip_path = tmp_path / "test.zip"
        with ZipFile(zip_path, 'w') as zf:
            result = add_photo_to_zip(zf, photo_path, metadata, include_xmp=True)

        assert result['success'] is True
        assert result['filename'] == "moth with spaces & special.jpg"


# ============================================================================
# Test validate_zip_integrity
# ============================================================================


class TestValidateZipIntegrity:
    """Test ZIP integrity validation."""

    def test_validate_zip_integrity_valid(self, tmp_path):
        """Test validation of valid ZIP file."""
        zip_path = tmp_path / "valid.zip"
        with ZipFile(zip_path, 'w') as zf:
            zf.writestr("test.txt", "test content")

        assert validate_zip_integrity(zip_path) is True

    def test_validate_zip_integrity_invalid(self, tmp_path):
        """Test validation of invalid ZIP file."""
        zip_path = tmp_path / "invalid.zip"
        zip_path.write_text("not a zip file")

        assert validate_zip_integrity(zip_path) is False

    def test_validate_zip_integrity_missing(self, tmp_path):
        """Test validation of missing ZIP file."""
        zip_path = tmp_path / "missing.zip"
        assert validate_zip_integrity(zip_path) is False

    def test_validate_zip_integrity_empty(self, tmp_path):
        """Test validation of empty ZIP file."""
        zip_path = tmp_path / "empty.zip"
        with ZipFile(zip_path, 'w'):
            pass  # Empty ZIP

        assert validate_zip_integrity(zip_path) is True


# ============================================================================
# Test estimate_zip_size
# ============================================================================


class TestEstimateZipSize:
    """Test ZIP size estimation."""

    def test_estimate_zip_size_single_photo(self, tmp_path):
        """Test size estimation for single photo."""
        photo_path = tmp_path / "moth.jpg"
        create_test_jpeg(photo_path, size=10000)

        estimated = estimate_zip_size([photo_path], include_xmp=True)
        assert estimated > 10000  # Should be at least photo size
        assert estimated < 20000  # XMP overhead should be reasonable

    def test_estimate_zip_size_multiple_photos(self, tmp_path):
        """Test size estimation for multiple photos."""
        photo_paths = []
        for i in range(5):
            path = tmp_path / f"moth{i}.jpg"
            create_test_jpeg(path, size=10000)
            photo_paths.append(path)

        estimated = estimate_zip_size(photo_paths, include_xmp=True)
        assert estimated > 50000  # At least 5 * 10000

    def test_estimate_zip_size_without_xmp(self, tmp_path):
        """Test size estimation without XMP sidecars."""
        photo_path = tmp_path / "moth.jpg"
        create_test_jpeg(photo_path, size=10000)

        with_xmp = estimate_zip_size([photo_path], include_xmp=True)
        without_xmp = estimate_zip_size([photo_path], include_xmp=False)

        assert without_xmp < with_xmp  # Should be smaller without XMP

    def test_estimate_zip_size_missing_file(self, tmp_path):
        """Test size estimation with missing file."""
        photo_path = tmp_path / "missing.jpg"
        estimated = estimate_zip_size([photo_path], include_xmp=True)
        assert estimated == 0  # Should handle gracefully


# ============================================================================
# Test create_zip_export
# ============================================================================


class TestCreateZipExport:
    """Test ZIP export creation."""

    def test_create_zip_export_single_photo(self, tmp_path):
        """Test creating ZIP export with single photo."""
        photo_path = tmp_path / "moth.jpg"
        create_test_jpeg(photo_path)
        metadata = create_test_metadata(filename="moth.jpg")
        output_path = tmp_path / "export.zip"

        result = create_zip_export([photo_path], [metadata], output_path)

        assert result.success is True
        assert result.zip_path == output_path
        assert result.photo_count == 1
        assert result.xmp_count == 1
        assert len(result.errors) == 0
        assert result.took_ms > 0
        assert output_path.exists()

    def test_create_zip_export_multiple_photos(self, tmp_path):
        """Test creating ZIP export with multiple photos."""
        photo_paths = []
        metadata_list = []
        for i in range(5):
            path = tmp_path / f"moth{i}.jpg"
            create_test_jpeg(path)
            photo_paths.append(path)
            metadata_list.append(create_test_metadata(filename=f"moth{i}.jpg"))

        output_path = tmp_path / "export.zip"
        result = create_zip_export(photo_paths, metadata_list, output_path)

        assert result.success is True
        assert result.photo_count == 5
        assert result.xmp_count == 5

    def test_create_zip_export_with_manifest(self, tmp_path):
        """Test ZIP export includes manifest.json."""
        photo_path = tmp_path / "moth.jpg"
        create_test_jpeg(photo_path)
        metadata = create_test_metadata(filename="moth.jpg")
        output_path = tmp_path / "export.zip"

        options = ZipExportOptions(include_manifest=True)
        result = create_zip_export([photo_path], [metadata], output_path, options)

        assert result.success is True
        with ZipFile(output_path, 'r') as zf:
            assert MANIFEST_FILENAME in zf.namelist()
            manifest_content = zf.read(MANIFEST_FILENAME).decode('utf-8')
            manifest = json.loads(manifest_content)
            assert manifest['photo_count'] == 1

    def test_create_zip_export_with_csv_summary(self, tmp_path):
        """Test ZIP export includes summary.csv."""
        photo_path = tmp_path / "moth.jpg"
        create_test_jpeg(photo_path)
        metadata = create_test_metadata(filename="moth.jpg")
        output_path = tmp_path / "export.zip"

        options = ZipExportOptions(include_csv_summary=True)
        result = create_zip_export([photo_path], [metadata], output_path, options)

        assert result.success is True
        with ZipFile(output_path, 'r') as zf:
            assert SUMMARY_FILENAME in zf.namelist()
            csv_content = zf.read(SUMMARY_FILENAME).decode('utf-8')
            assert 'filename' in csv_content
            assert 'moth.jpg' in csv_content

    def test_create_zip_export_without_xmp(self, tmp_path):
        """Test ZIP export without XMP sidecars."""
        photo_path = tmp_path / "moth.jpg"
        create_test_jpeg(photo_path)
        metadata = create_test_metadata(filename="moth.jpg")
        output_path = tmp_path / "export.zip"

        options = ZipExportOptions(include_xmp_sidecars=False)
        result = create_zip_export([photo_path], [metadata], output_path, options)

        assert result.success is True
        assert result.xmp_count == 0
        with ZipFile(output_path, 'r') as zf:
            assert "moth.jpg" in zf.namelist()
            assert "moth.xmp" not in zf.namelist()

    def test_create_zip_export_empty_list(self, tmp_path):
        """Test creating ZIP export with empty photo list."""
        output_path = tmp_path / "export.zip"
        result = create_zip_export([], [], output_path)

        assert result.success is True
        assert result.photo_count == 0
        assert result.xmp_count == 0
        assert output_path.exists()

    def test_create_zip_export_missing_photo(self, tmp_path):
        """Test creating ZIP export with missing photo."""
        photo_path = tmp_path / "missing.jpg"
        metadata = create_test_metadata(filename="missing.jpg")
        output_path = tmp_path / "export.zip"

        result = create_zip_export([photo_path], [metadata], output_path)

        # Should still succeed but with errors
        assert len(result.errors) == 1
        assert result.photo_count == 0

    def test_create_zip_export_flatten_structure(self, tmp_path):
        """Test ZIP export with flattened structure."""
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        photo_path = subdir / "moth.jpg"
        create_test_jpeg(photo_path)
        metadata = create_test_metadata(filename="moth.jpg")
        output_path = tmp_path / "export.zip"

        options = ZipExportOptions(flatten_structure=True)
        result = create_zip_export([photo_path], [metadata], output_path, options)

        assert result.success is True
        with ZipFile(output_path, 'r') as zf:
            # All files should be at root level
            assert "moth.jpg" in zf.namelist()
            assert not any("/" in name for name in zf.namelist()
                          if name not in [MANIFEST_FILENAME, SUMMARY_FILENAME])

    def test_create_zip_export_special_characters(self, tmp_path):
        """Test ZIP export with special characters in filenames."""
        photo_path = tmp_path / "moth with spaces & special.jpg"
        create_test_jpeg(photo_path)
        metadata = create_test_metadata(filename="moth with spaces & special.jpg")
        output_path = tmp_path / "export.zip"

        result = create_zip_export([photo_path], [metadata], output_path)

        assert result.success is True
        with ZipFile(output_path, 'r') as zf:
            assert "moth with spaces & special.jpg" in zf.namelist()

    def test_create_zip_export_validates_integrity(self, tmp_path):
        """Test created ZIP file is valid."""
        photo_path = tmp_path / "moth.jpg"
        create_test_jpeg(photo_path)
        metadata = create_test_metadata(filename="moth.jpg")
        output_path = tmp_path / "export.zip"

        result = create_zip_export([photo_path], [metadata], output_path)

        assert result.success is True
        assert is_zipfile(output_path)
        assert validate_zip_integrity(output_path)


# ============================================================================
# Test stream_zip_export
# ============================================================================


class TestStreamZipExport:
    """Test ZIP export streaming."""

    def test_stream_zip_export_returns_generator(self, tmp_path):
        """Test stream_zip_export returns a generator."""
        photo_path = tmp_path / "moth.jpg"
        create_test_jpeg(photo_path)
        metadata = create_test_metadata(filename="moth.jpg")

        generator = stream_zip_export([photo_path], [metadata])
        assert isinstance(generator, Generator)

    def test_stream_zip_export_yields_bytes(self, tmp_path):
        """Test stream_zip_export yields bytes."""
        photo_path = tmp_path / "moth.jpg"
        create_test_jpeg(photo_path)
        metadata = create_test_metadata(filename="moth.jpg")

        chunks = []
        result = None
        for chunk in stream_zip_export([photo_path], [metadata]):
            if isinstance(chunk, bytes):
                chunks.append(chunk)
            else:
                result = chunk

        assert len(chunks) > 0
        assert all(isinstance(chunk, bytes) for chunk in chunks)
        assert isinstance(result, ZipExportResult)

    def test_stream_zip_export_final_result(self, tmp_path):
        """Test stream_zip_export returns ZipExportResult at end."""
        photo_path = tmp_path / "moth.jpg"
        create_test_jpeg(photo_path)
        metadata = create_test_metadata(filename="moth.jpg")

        result = None
        for chunk in stream_zip_export([photo_path], [metadata]):
            if isinstance(chunk, ZipExportResult):
                result = chunk

        assert result is not None
        assert result.success is True
        assert result.photo_count == 1

    def test_stream_zip_export_creates_valid_zip(self, tmp_path):
        """Test streamed ZIP is valid."""
        photo_path = tmp_path / "moth.jpg"
        create_test_jpeg(photo_path)
        metadata = create_test_metadata(filename="moth.jpg")

        chunks = []
        for chunk in stream_zip_export([photo_path], [metadata]):
            if isinstance(chunk, bytes):
                chunks.append(chunk)

        # Reconstruct ZIP from chunks
        zip_data = b''.join(chunks)
        zip_buffer = BytesIO(zip_data)
        assert is_zipfile(zip_buffer)

    def test_stream_zip_export_multiple_photos(self, tmp_path):
        """Test streaming with multiple photos."""
        photo_paths = []
        metadata_list = []
        for i in range(5):
            path = tmp_path / f"moth{i}.jpg"
            create_test_jpeg(path)
            photo_paths.append(path)
            metadata_list.append(create_test_metadata(filename=f"moth{i}.jpg"))

        result = None
        for chunk in stream_zip_export(photo_paths, metadata_list):
            if isinstance(chunk, ZipExportResult):
                result = chunk

        assert result.photo_count == 5


# ============================================================================
# Test Performance
# ============================================================================


class TestPerformance:
    """Test ZIP export performance."""

    def test_create_zip_export_50_photos_under_5_seconds(self, tmp_path):
        """Test creating ZIP with 50 photos completes in <5 seconds."""
        photo_paths = []
        metadata_list = []
        for i in range(50):
            path = tmp_path / f"moth{i}.jpg"
            create_test_jpeg(path, size=50000)  # 50KB each
            photo_paths.append(path)
            metadata_list.append(create_test_metadata(filename=f"moth{i}.jpg"))

        output_path = tmp_path / "export.zip"

        start_time = time.time()
        result = create_zip_export(photo_paths, metadata_list, output_path)
        elapsed_time = time.time() - start_time

        assert result.success is True
        assert result.photo_count == 50
        assert elapsed_time < 5.0, f"Export took {elapsed_time:.2f}s, expected <5s"

    def test_stream_zip_export_50_photos_under_5_seconds(self, tmp_path):
        """Test streaming ZIP with 50 photos completes in <5 seconds."""
        photo_paths = []
        metadata_list = []
        for i in range(50):
            path = tmp_path / f"moth{i}.jpg"
            create_test_jpeg(path, size=50000)  # 50KB each
            photo_paths.append(path)
            metadata_list.append(create_test_metadata(filename=f"moth{i}.jpg"))

        start_time = time.time()
        result = None
        for chunk in stream_zip_export(photo_paths, metadata_list):
            if isinstance(chunk, ZipExportResult):
                result = chunk
        elapsed_time = time.time() - start_time

        assert result.success is True
        assert result.photo_count == 50
        assert elapsed_time < 5.0, f"Streaming took {elapsed_time:.2f}s, expected <5s"


# ============================================================================
# Test Custom Exception Classes
# ============================================================================


class TestZipExportExceptions:
    """Test custom exception classes for ZIP export."""

    def test_exception_hierarchy(self):
        """Test exception inheritance hierarchy."""
        assert issubclass(PhotoFileError, ZipExportError)
        assert issubclass(XMPGenerationError, ZipExportError)
        assert issubclass(ZipWriteError, ZipExportError)
        assert issubclass(ZipExportError, Exception)

    def test_can_catch_base_exception(self):
        """Test catching all ZIP export errors with base class."""
        try:
            raise PhotoFileError("test error")
        except ZipExportError as e:
            assert str(e) == "test error"

    def test_photo_file_error_message(self):
        """Test PhotoFileError preserves error message."""
        error = PhotoFileError("Permission denied")
        assert str(error) == "Permission denied"

    def test_xmp_generation_error_message(self):
        """Test XMPGenerationError preserves error message."""
        error = XMPGenerationError("Invalid metadata")
        assert str(error) == "Invalid metadata"

    def test_zip_write_error_message(self):
        """Test ZipWriteError preserves error message."""
        error = ZipWriteError("Disk full")
        assert str(error) == "Disk full"


# ============================================================================
# Test Error Handling
# ============================================================================


class TestErrorHandling:
    """Test specific error handling scenarios."""

    def test_add_photo_permission_error(self, tmp_path, monkeypatch):
        """Test handling of permission denied error during photo read."""
        photo_path = tmp_path / "moth.jpg"
        create_test_jpeg(photo_path)
        metadata = create_test_metadata(filename="moth.jpg")

        # Mock ZipFile.write to raise PermissionError
        def mock_write(self, filename, arcname=None, compress_type=None):
            raise PermissionError("Permission denied")

        zip_path = tmp_path / "test.zip"
        with ZipFile(zip_path, 'w') as zf:
            monkeypatch.setattr(type(zf), 'write', mock_write)
            result = add_photo_to_zip(zf, photo_path, metadata, include_xmp=True)

        assert result['success'] is False
        assert result['error'] == "Permission denied reading photo file"
        assert result['error_type'] == 'permission'

    def test_add_photo_oserror_disk_full(self, tmp_path, monkeypatch):
        """Test handling of disk full error (OSError)."""
        import errno

        photo_path = tmp_path / "moth.jpg"
        create_test_jpeg(photo_path)
        metadata = create_test_metadata(filename="moth.jpg")

        # Mock ZipFile.write to raise OSError with ENOSPC
        def mock_write(self, filename, arcname=None, compress_type=None):
            err = OSError(errno.ENOSPC, "No space left on device")
            raise err

        zip_path = tmp_path / "test.zip"
        with ZipFile(zip_path, 'w') as zf:
            monkeypatch.setattr(type(zf), 'write', mock_write)
            result = add_photo_to_zip(zf, photo_path, metadata, include_xmp=True)

        assert result['success'] is False
        assert 'File system error' in result['error']
        assert result['error_type'] == 'io'

    def test_add_photo_xmp_generation_error(self, tmp_path, monkeypatch):
        """Test handling of XMP generation failure."""
        photo_path = tmp_path / "moth.jpg"
        create_test_jpeg(photo_path)
        metadata = create_test_metadata(filename="moth.jpg")

        # Mock generate_xmp_xml to raise ValueError
        from webui.backend.lib import zip_export

        def mock_generate_xmp_xml(metadata):
            raise ValueError("Invalid metadata field")

        monkeypatch.setattr(zip_export, 'generate_xmp_xml', mock_generate_xmp_xml)

        zip_path = tmp_path / "test.zip"
        with ZipFile(zip_path, 'w') as zf:
            result = add_photo_to_zip(zf, photo_path, metadata, include_xmp=True)

        assert result['success'] is False
        assert result['error'] == "Failed to generate XMP metadata"
        assert result['error_type'] == 'xmp'

    def test_error_type_field_not_found(self, tmp_path):
        """Test that error_type is 'not_found' for missing files."""
        photo_path = tmp_path / "missing.jpg"
        metadata = create_test_metadata(filename="missing.jpg")

        zip_path = tmp_path / "test.zip"
        with ZipFile(zip_path, 'w') as zf:
            result = add_photo_to_zip(zf, photo_path, metadata, include_xmp=True)

        assert result['success'] is False
        assert 'not found' in result['error']
        assert result['error_type'] == 'not_found'

    def test_create_zip_export_permission_error(self, tmp_path, monkeypatch):
        """Test create_zip_export handles permission errors."""
        photo_path = tmp_path / "moth.jpg"
        create_test_jpeg(photo_path)
        metadata = create_test_metadata(filename="moth.jpg")

        # Use a path that will fail to create (simulate permission error)
        output_path = tmp_path / "readonly" / "export.zip"

        # Mock ZipFile to raise PermissionError
        original_init = ZipFile.__init__

        def mock_init(self, file, mode='r', *args, **kwargs):
            if mode == 'w':
                raise PermissionError("Permission denied")
            return original_init(self, file, mode, *args, **kwargs)

        monkeypatch.setattr(ZipFile, '__init__', mock_init)

        result = create_zip_export([photo_path], [metadata], output_path)

        assert result.success is False
        assert len(result.errors) > 0
        assert result.errors[0].error_type == 'permission'

    def test_user_friendly_error_messages(self, tmp_path, monkeypatch):
        """Test that error messages are user-friendly (no raw exceptions)."""
        photo_path = tmp_path / "moth.jpg"
        create_test_jpeg(photo_path)
        metadata = create_test_metadata(filename="moth.jpg")

        # Mock to raise a generic exception
        def mock_write(self, filename, arcname=None, compress_type=None):
            raise RuntimeError("Internal error with sensitive path info")

        zip_path = tmp_path / "test.zip"
        with ZipFile(zip_path, 'w') as zf:
            monkeypatch.setattr(type(zf), 'write', mock_write)
            result = add_photo_to_zip(zf, photo_path, metadata, include_xmp=True)

        assert result['success'] is False
        # Should be a generic message, not the raw exception
        assert result['error'] == "Unexpected error processing photo"
        assert result['error_type'] == 'unknown'
        # The raw exception message should NOT be in the error
        assert 'sensitive path info' not in result['error']

    def test_stream_zip_oserror(self, tmp_path, monkeypatch):
        """Test stream_zip_export handles OSError."""
        import errno

        photo_path = tmp_path / "moth.jpg"
        create_test_jpeg(photo_path)
        metadata = create_test_metadata(filename="moth.jpg")

        # Mock to raise OSError during ZIP creation
        original_init = ZipFile.__init__

        def mock_init(self, file, mode='r', *args, **kwargs):
            if mode == 'w' and hasattr(file, 'write'):
                raise OSError(errno.EIO, "Input/output error")
            return original_init(self, file, mode, *args, **kwargs)

        monkeypatch.setattr(ZipFile, '__init__', mock_init)

        result = None
        for chunk in stream_zip_export([photo_path], [metadata]):
            if isinstance(chunk, ZipExportResult):
                result = chunk

        assert result is not None
        assert result.success is False
        assert len(result.errors) > 0
        assert result.errors[0].error_type == 'io'


# ============================================================================
# Progress Callback Tests
# ============================================================================


import pytest


class TestProgressCallback:
    """Tests for progress callback functionality."""

    def test_progress_callback_called(self, tmp_path):
        """Test that progress callback is called during export."""
        # Create test photos
        photo_paths = []
        metadata_list = []
        for i in range(15):
            photo_path = tmp_path / f"photo_{i}.jpg"
            photo_path.write_bytes(b'\xFF\xD8\xFF\xE0' + b'\x00' * 100)
            photo_paths.append(photo_path)
            metadata_list.append(ExportMetadata(
                photo_path=str(photo_path),
                filename=f"photo_{i}.jpg",
            ))

        output_path = tmp_path / "output.zip"
        progress_calls = []

        def progress_callback(current: int, total: int) -> None:
            progress_calls.append((current, total))

        result = create_zip_export(
            photo_paths,
            metadata_list,
            output_path,
            progress_callback=progress_callback,
        )

        assert result.success is True
        # Should have progress calls (at least one)
        assert len(progress_calls) > 0
        # Last call should have current == total
        last_current, last_total = progress_calls[-1]
        assert last_total == len(photo_paths)
        assert last_current == len(photo_paths)

    def test_progress_callback_every_10_photos(self, tmp_path):
        """Test that progress callback is called every 10 photos."""
        # Create 25 test photos
        photo_paths = []
        metadata_list = []
        for i in range(25):
            photo_path = tmp_path / f"photo_{i}.jpg"
            photo_path.write_bytes(b'\xFF\xD8\xFF\xE0' + b'\x00' * 100)
            photo_paths.append(photo_path)
            metadata_list.append(ExportMetadata(
                photo_path=str(photo_path),
                filename=f"photo_{i}.jpg",
            ))

        output_path = tmp_path / "output.zip"
        progress_calls = []

        def progress_callback(current: int, total: int) -> None:
            progress_calls.append((current, total))

        result = create_zip_export(
            photo_paths,
            metadata_list,
            output_path,
            progress_callback=progress_callback,
        )

        assert result.success is True
        # Should have calls at 10, 20, and 25 (end)
        assert len(progress_calls) == 3
        currents = [c[0] for c in progress_calls]
        assert currents == [10, 20, 25]

    def test_progress_callback_none_no_error(self, tmp_path):
        """Test that None progress_callback doesn't cause errors."""
        photo_path = tmp_path / "photo.jpg"
        photo_path.write_bytes(b'\xFF\xD8\xFF\xE0' + b'\x00' * 100)

        metadata = ExportMetadata(
            photo_path=str(photo_path),
            filename="photo.jpg",
        )

        output_path = tmp_path / "output.zip"

        # Should not raise an error
        result = create_zip_export(
            [photo_path],
            [metadata],
            output_path,
            progress_callback=None,
        )

        assert result.success is True

    def test_progress_callback_single_photo(self, tmp_path):
        """Test progress callback with single photo."""
        photo_path = tmp_path / "photo.jpg"
        photo_path.write_bytes(b'\xFF\xD8\xFF\xE0' + b'\x00' * 100)

        metadata = ExportMetadata(
            photo_path=str(photo_path),
            filename="photo.jpg",
        )

        output_path = tmp_path / "output.zip"
        progress_calls = []

        def progress_callback(current: int, total: int) -> None:
            progress_calls.append((current, total))

        result = create_zip_export(
            [photo_path],
            [metadata],
            output_path,
            progress_callback=progress_callback,
        )

        assert result.success is True
        # Should have one call for single photo
        assert len(progress_calls) == 1
        assert progress_calls[0] == (1, 1)
