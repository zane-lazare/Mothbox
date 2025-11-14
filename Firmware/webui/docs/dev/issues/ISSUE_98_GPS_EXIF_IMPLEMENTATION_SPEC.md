# Issue #98: GPS EXIF Embedding - Post-Processing Architecture Implementation Specification

## Executive Summary

This document specifies a **post-processing approach** for embedding GPS EXIF data into Mothbox photos. Instead of modifying the photo capture workflow (`TakePhoto.py`), we implement a standalone service that adds GPS metadata after photos are captured. This provides better separation of concerns, works without firmware changes, and enables retroactive tagging of existing photos.

**Architecture Decision**: Post-processing GPS EXIF tagger with multiple deployment modes (immediate, lazy, batch).

---

## 1. Architecture Overview

### 1.1 Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              PHOTO CAPTURE WORKFLOW                          │
│  ┌──────────┐    ┌──────────────┐    ┌────────────┐    ┌──────────────┐   │
│  │ GPS.py   │───▶│ controls.txt │◀───│ TakePhoto  │───▶│ /photos/     │   │
│  │ Updates  │    │ (GPS data)   │    │ (no GPS)   │    │ RAW JPEG     │   │
│  │ Position │    └──────────────┘    └────────────┘    └──────┬───────┘   │
│  └──────────┘                                                  │           │
└────────────────────────────────────────────────────────────────┼───────────┘
                                                                  │
                                  ┌───────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        GPS EXIF POST-PROCESSOR                               │
│                                                                              │
│  ┌────────────────┐   ┌──────────────────┐   ┌───────────────────────┐    │
│  │ File Monitor   │──▶│ GPS Data Fetcher │──▶│ EXIF Embedder         │    │
│  │ (inotify/poll) │   │ (controls.txt)   │   │ (piexif in-place edit)│    │
│  └────────────────┘   └──────────────────┘   └───────────┬───────────┘    │
│                                                            │                │
│  ┌────────────────────────────────────────────────────────┘                │
│  │                                                                          │
│  ▼                                                                          │
│  ┌────────────────────────────────────────────────────────────┐            │
│  │ Tagged Photo:                                              │            │
│  │  - Original camera EXIF (exposure, ISO, focus)             │            │
│  │  - GPS coordinates (lat/lon)                               │            │
│  │  - GPS timestamp                                            │            │
│  │  - GPS precision (HDOP/PDOP)                               │            │
│  │  - GPS satellites used                                     │            │
│  └────────────────────────────────────────────────────────────┘            │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 1.2 Component Interaction

```
┌──────────────┐
│ Scheduler.py │ (cron job)
└──────┬───────┘
       │ Triggers GPS.py every N minutes
       ▼
┌──────────────────┐
│ GPS.py           │
│ - Reads gpsd     │
│ - Updates        │
│   controls.txt:  │
│   • lat/lon      │──────┐
│   • gpstime      │      │
│   • hdop/pdop    │      │
│   • satellites   │      │
│   • fix_mode     │      │
└──────────────────┘      │
                          │ Atomic file write (fcntl)
                          ▼
                   ┌──────────────────┐
                   │ controls.txt     │
                   │ (GPS state)      │
                   └──────┬───────────┘
                          │
       ┌──────────────────┴──────────────────┐
       │                                     │
       ▼                                     ▼
┌──────────────────┐              ┌───────────────────────┐
│ TakePhoto.py     │              │ gps_exif_tagger.py    │
│ - Reads camera   │              │ - Reads GPS data      │
│   settings       │              │ - Embeds EXIF GPS     │
│ - Captures photo │              │ - Writes in-place     │
│ - Saves to disk  │              │ - Validates integrity │
│ - NO GPS EXIF    │              └───────────────────────┘
└──────────────────┘
```

### 1.3 Key Design Principles

1. **Non-invasive**: `TakePhoto.py` remains unchanged
2. **Idempotent**: Safe to run multiple times on same photo
3. **Atomic operations**: File locking prevents corruption
4. **Graceful degradation**: Works without GPS (no-op)
5. **Retroactive capable**: Can tag old photos
6. **Multiple deployment modes**: Immediate, lazy, batch

---

## 2. File Structure

### 2.1 New Files to Create

```
/home/pi/projects/Mothbox/Firmware/
│
├── gps_exif_tagger.py              # Main post-processor (standalone script)
├── lib/
│   ├── __init__.py
│   └── gps_exif_lib.py             # Reusable GPS EXIF library
│
├── services/
│   └── gps-exif-tagger.service     # Systemd service (immediate mode)
│
├── scripts/
│   ├── batch_tag_photos.py         # Batch retroactive tagging utility
│   └── verify_gps_exif.py          # Validation/inspection tool
│
├── Tests/
│   ├── unit/
│   │   ├── test_gps_exif_lib.py           # Library unit tests
│   │   └── test_gps_data_extraction.py    # GPS data parsing tests
│   └── integration/
│       ├── test_gps_exif_workflow.py      # End-to-end workflow tests
│       └── test_batch_tagging.py          # Batch processing tests
│
└── webui/backend/routes/
    └── gps_exif.py                 # Optional: Web UI routes for status/control
```

### 2.2 Files to Modify

```
controls.txt                        # Already has GPS fields (no changes needed)
installation-utils/requirements.txt # Already has piexif (no changes needed)
pyproject.toml                      # Add pytest markers for GPS EXIF tests
Tests/conftest.py                   # Add fixtures for GPS EXIF testing
```

---

## 3. Function Specifications

### 3.1 Core Library: `lib/gps_exif_lib.py`

```python
"""GPS EXIF embedding library for Mothbox photos.

This module provides functions to read GPS data from controls.txt
and embed it into JPEG EXIF metadata without modifying the original
photo capture workflow.
"""

from pathlib import Path
from typing import Optional, Dict, Tuple, Any
import piexif
from mothbox_paths import CONTROLS_FILE, get_control_values


def get_gps_data_from_controls() -> Dict[str, Any]:
    """
    Read current GPS data from controls.txt.

    Returns:
        dict: GPS data dictionary with keys:
            - latitude (float or None): Decimal latitude
            - longitude (float or None): Decimal longitude
            - gpstime (int): Unix timestamp from GPS
            - altitude (float or None): Altitude in meters (if available)
            - fix_mode (int): 0=no fix, 2=2D, 3=3D
            - satellites_used (int): Number of satellites in fix
            - hdop (float): Horizontal dilution of precision
            - pdop (float): Position dilution of precision
            - has_fix (bool): Whether GPS has valid position

    Example:
        >>> gps_data = get_gps_data_from_controls()
        >>> if gps_data['has_fix']:
        ...     print(f"Position: {gps_data['latitude']}, {gps_data['longitude']}")
    """
    pass


def decimal_to_dms(decimal: float, is_latitude: bool) -> Tuple[Tuple, str]:
    """
    Convert decimal degrees to EXIF GPS format (degrees, minutes, seconds).

    Args:
        decimal: Decimal degrees (e.g., 37.7749 or -122.4194)
        is_latitude: True if this is latitude, False if longitude

    Returns:
        tuple: (dms_tuple, ref_string) where:
            - dms_tuple: ((degrees, 1), (minutes, 1), (seconds, 100))
            - ref_string: 'N'/'S' for latitude, 'E'/'W' for longitude

    Example:
        >>> dms, ref = decimal_to_dms(37.7749, is_latitude=True)
        >>> print(dms, ref)
        ((37, 1), (46, 1), (2964, 100)) 'N'

    Note:
        Seconds are multiplied by 100 and stored as rational (seconds*100, 100)
        to preserve precision (EXIF standard).
    """
    pass


def build_gps_ifd(gps_data: Dict[str, Any]) -> Dict:
    """
    Build piexif GPS IFD dictionary from GPS data.

    Args:
        gps_data: GPS data dictionary from get_gps_data_from_controls()

    Returns:
        dict: piexif GPS IFD dictionary ready for embedding

    EXIF GPS tags included:
        - GPSVersionID: (2, 3, 0, 0) - EXIF 2.3 standard
        - GPSLatitude: DMS tuple
        - GPSLatitudeRef: 'N' or 'S'
        - GPSLongitude: DMS tuple
        - GPSLongitudeRef: 'E' or 'W'
        - GPSAltitude: (altitude_meters * 100, 100) if available
        - GPSAltitudeRef: 0 (above sea level) or 1 (below)
        - GPSTimeStamp: (hour, minute, second) - UTC time
        - GPSDateStamp: 'YYYY:MM:DD' - UTC date
        - GPSDOP: (hdop * 100, 100) - Dilution of precision
        - GPSSatellites: f"{satellites_used}" - Number of satellites

    Example:
        >>> gps_data = get_gps_data_from_controls()
        >>> gps_ifd = build_gps_ifd(gps_data)
        >>> print(gps_ifd[piexif.GPSIFD.GPSLatitudeRef])
        'N'
    """
    pass


def embed_gps_exif(
    photo_path: Path,
    gps_data: Optional[Dict[str, Any]] = None,
    backup: bool = False,
    dry_run: bool = False
) -> Dict[str, Any]:
    """
    Embed GPS EXIF data into a JPEG photo in-place.

    This function:
    1. Reads existing EXIF from photo
    2. Builds GPS IFD from current GPS data (or provided data)
    3. Merges GPS IFD with existing EXIF
    4. Writes EXIF back to photo atomically
    5. Verifies integrity after write

    Args:
        photo_path: Path to JPEG photo file
        gps_data: GPS data dict (or None to read from controls.txt)
        backup: If True, create .bak file before modifying
        dry_run: If True, validate but don't write changes

    Returns:
        dict: Operation result with keys:
            - success (bool): True if GPS EXIF was embedded
            - skipped (bool): True if no GPS fix available
            - error (str or None): Error message if failed
            - gps_embedded (bool): True if GPS tags were written
            - original_had_gps (bool): True if photo already had GPS EXIF
            - backup_path (Path or None): Path to backup file if created

    Raises:
        FileNotFoundError: If photo_path doesn't exist
        ValueError: If photo_path is not a JPEG file
        PermissionError: If unable to write to photo

    Example:
        >>> result = embed_gps_exif(Path('/photos/mothbox_2025_01_15__12_30_00.jpg'))
        >>> if result['success']:
        ...     print("GPS EXIF embedded successfully")
        >>> elif result['skipped']:
        ...     print("No GPS fix available, skipped")

    Security:
        - Uses atomic write (write to temp, then rename)
        - Validates JPEG integrity after write
        - Original file preserved if backup=True
    """
    pass


def verify_gps_exif(photo_path: Path) -> Dict[str, Any]:
    """
    Read and verify GPS EXIF data from a photo.

    Args:
        photo_path: Path to JPEG photo file

    Returns:
        dict: GPS EXIF data with keys:
            - has_gps (bool): True if GPS EXIF tags present
            - latitude (float or None): Extracted latitude
            - longitude (float or None): Extracted longitude
            - timestamp (str or None): GPS timestamp
            - altitude (float or None): Altitude in meters
            - satellites (str or None): Number of satellites
            - hdop (float or None): Horizontal DOP
            - raw_gps_ifd (dict): Raw piexif GPS IFD

    Example:
        >>> info = verify_gps_exif(Path('/photos/mothbox_2025_01_15__12_30_00.jpg'))
        >>> if info['has_gps']:
        ...     print(f"Photo location: {info['latitude']}, {info['longitude']}")
    """
    pass


def is_already_tagged(photo_path: Path) -> bool:
    """
    Check if photo already has GPS EXIF data.

    Args:
        photo_path: Path to JPEG photo file

    Returns:
        bool: True if photo has GPSLatitude and GPSLongitude tags

    Note:
        Used for idempotency - avoids re-processing tagged photos.
    """
    pass
```

### 3.2 Main Script: `gps_exif_tagger.py`

```python
#!/usr/bin/env python3
"""
GPS EXIF Tagger - Post-processing service for Mothbox photos.

This script monitors the photos directory and embeds GPS EXIF data
from controls.txt into newly captured photos.

Deployment Modes:
    1. Immediate (systemd service): Tags photos as they're captured
    2. Lazy (on-demand): Tags photos when accessed (via API/gallery)
    3. Batch (manual): Tag all photos in directory

Usage:
    # Immediate mode (background service)
    python3 gps_exif_tagger.py --mode immediate --watch

    # Batch mode (one-time processing)
    python3 gps_exif_tagger.py --mode batch --directory /var/lib/mothbox/photos

    # Dry run (test without modifying files)
    python3 gps_exif_tagger.py --mode batch --directory ./photos --dry-run

    # With backups
    python3 gps_exif_tagger.py --mode batch --backup

Arguments:
    --mode {immediate,batch}  Deployment mode
    --watch                   Monitor directory for new files (immediate mode)
    --directory PATH          Photo directory to process
    --dry-run                 Validate without modifying files
    --backup                  Create .bak files before modifying
    --force                   Re-tag photos even if already tagged
    --pattern GLOB            File pattern (default: *.jpg)
    --interval SECONDS        Polling interval for immediate mode (default: 10)
"""

import argparse
import logging
import time
from pathlib import Path
from typing import List, Dict, Any

from mothbox_paths import PHOTOS_DIR, get_hardware_config
from lib.gps_exif_lib import embed_gps_exif, is_already_tagged, get_gps_data_from_controls


def setup_logging(verbose: bool = False) -> logging.Logger:
    """Configure logging for GPS EXIF tagger."""
    pass


def process_single_photo(
    photo_path: Path,
    force: bool = False,
    backup: bool = False,
    dry_run: bool = False
) -> Dict[str, Any]:
    """
    Process a single photo for GPS EXIF tagging.

    Args:
        photo_path: Path to photo file
        force: If True, re-tag even if already tagged
        backup: If True, create backup before modifying
        dry_run: If True, don't modify files

    Returns:
        dict: Processing result from embed_gps_exif()
    """
    pass


def batch_process_directory(
    directory: Path,
    pattern: str = "*.jpg",
    force: bool = False,
    backup: bool = False,
    dry_run: bool = False
) -> Dict[str, Any]:
    """
    Process all photos in directory (batch mode).

    Args:
        directory: Directory to scan for photos
        pattern: Glob pattern for photo files
        force: If True, re-tag already tagged photos
        backup: If True, create backups
        dry_run: If True, don't modify files

    Returns:
        dict: Batch processing statistics:
            - total (int): Total photos found
            - tagged (int): Photos successfully tagged
            - skipped (int): Photos skipped (no GPS or already tagged)
            - errors (int): Photos that failed to process
            - error_list (list): List of (path, error_message) tuples
    """
    pass


def watch_directory(
    directory: Path,
    pattern: str = "*.jpg",
    interval: int = 10,
    backup: bool = False
) -> None:
    """
    Monitor directory and tag new photos (immediate mode).

    Uses polling with mtime tracking (more portable than inotify).

    Args:
        directory: Directory to monitor
        pattern: Glob pattern for photo files
        interval: Polling interval in seconds
        backup: If True, create backups

    Implementation:
        - Track last modification times of all photos
        - Poll directory every `interval` seconds
        - Process new/modified photos
        - Skip photos already tagged
        - Handle filesystem events gracefully
    """
    pass


def main():
    """Main entry point for GPS EXIF tagger."""
    parser = argparse.ArgumentParser(
        description="GPS EXIF post-processor for Mothbox photos",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument(
        '--mode',
        choices=['immediate', 'batch'],
        default='batch',
        help='Deployment mode: immediate (watch) or batch (one-time)'
    )
    parser.add_argument(
        '--watch',
        action='store_true',
        help='Monitor directory for new files (immediate mode)'
    )
    parser.add_argument(
        '--directory',
        type=Path,
        default=PHOTOS_DIR,
        help=f'Photo directory to process (default: {PHOTOS_DIR})'
    )
    parser.add_argument(
        '--pattern',
        default='*.jpg',
        help='File pattern to match (default: *.jpg)'
    )
    parser.add_argument(
        '--interval',
        type=int,
        default=10,
        help='Polling interval in seconds for watch mode (default: 10)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Test mode: validate without modifying files'
    )
    parser.add_argument(
        '--backup',
        action='store_true',
        help='Create .bak files before modifying photos'
    )
    parser.add_argument(
        '--force',
        action='store_true',
        help='Re-tag photos even if already have GPS EXIF'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )

    args = parser.parse_args()

    # Implementation continues...
    pass


if __name__ == '__main__':
    main()
```

### 3.3 Batch Utility: `scripts/batch_tag_photos.py`

```python
#!/usr/bin/env python3
"""
Batch GPS EXIF tagger for retroactive photo processing.

This utility processes existing photos and embeds GPS EXIF data from
the last known GPS position (stored in controls.txt).

Use Cases:
    1. Tag photos from before GPS EXIF feature was implemented
    2. Re-tag photos after GPS position was corrected
    3. Tag photos from a specific time range using historical GPS data

Usage:
    # Tag all photos in photos directory
    python3 scripts/batch_tag_photos.py

    # Tag photos from specific date range
    python3 scripts/batch_tag_photos.py --start 2025-01-01 --end 2025-01-31

    # Use specific GPS coordinates (override controls.txt)
    python3 scripts/batch_tag_photos.py --lat 37.7749 --lon -122.4194

    # Dry run (test without modifying)
    python3 scripts/batch_tag_photos.py --dry-run --verbose

Arguments:
    --directory PATH          Photo directory (default: from mothbox_paths)
    --start YYYY-MM-DD       Only process photos from this date onward
    --end YYYY-MM-DD         Only process photos up to this date
    --lat DECIMAL            Override latitude (decimal degrees)
    --lon DECIMAL            Override longitude (decimal degrees)
    --backup                 Create .bak files before modifying
    --dry-run                Test without modifying files
    --verbose                Enable detailed logging
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any

from mothbox_paths import PHOTOS_DIR
from lib.gps_exif_lib import embed_gps_exif, get_gps_data_from_controls


def extract_timestamp_from_filename(filename: str) -> Optional[datetime]:
    """
    Extract timestamp from Mothbox photo filename.

    Args:
        filename: Filename like 'mothbox_2025_01_15__12_30_00.jpg'

    Returns:
        datetime: Extracted timestamp or None if parsing fails

    Example:
        >>> ts = extract_timestamp_from_filename('mothbox_2025_01_15__12_30_00.jpg')
        >>> print(ts)
        2025-01-15 12:30:00
    """
    pass


def filter_photos_by_date(
    photos: List[Path],
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
) -> List[Path]:
    """
    Filter photos by capture date (extracted from filename).

    Args:
        photos: List of photo paths
        start_date: Include photos from this date onward (or None)
        end_date: Include photos up to this date (or None)

    Returns:
        list: Filtered list of photo paths
    """
    pass


def main():
    """Main entry point for batch tagging utility."""
    parser = argparse.ArgumentParser(
        description='Batch GPS EXIF tagger for existing photos',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument(
        '--directory',
        type=Path,
        default=PHOTOS_DIR,
        help=f'Photo directory (default: {PHOTOS_DIR})'
    )
    parser.add_argument(
        '--start',
        type=lambda s: datetime.strptime(s, '%Y-%m-%d'),
        help='Start date (YYYY-MM-DD)'
    )
    parser.add_argument(
        '--end',
        type=lambda s: datetime.strptime(s, '%Y-%m-%d'),
        help='End date (YYYY-MM-DD)'
    )
    parser.add_argument(
        '--lat',
        type=float,
        help='Override latitude (decimal degrees)'
    )
    parser.add_argument(
        '--lon',
        type=float,
        help='Override longitude (decimal degrees)'
    )
    parser.add_argument(
        '--backup',
        action='store_true',
        help='Create .bak files before modifying'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Test mode: validate without modifying files'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )

    args = parser.parse_args()

    # Validation
    if (args.lat is not None and args.lon is None) or (args.lat is None and args.lon is not None):
        print("Error: Both --lat and --lon must be specified together", file=sys.stderr)
        sys.exit(1)

    # Implementation continues...
    pass


if __name__ == '__main__':
    main()
```

### 3.4 Verification Tool: `scripts/verify_gps_exif.py`

```python
#!/usr/bin/env python3
"""
GPS EXIF verification and inspection tool.

This utility reads and displays GPS EXIF data from Mothbox photos.
Useful for debugging, validation, and quality assurance.

Usage:
    # Verify single photo
    python3 scripts/verify_gps_exif.py /photos/mothbox_2025_01_15__12_30_00.jpg

    # Verify all photos in directory
    python3 scripts/verify_gps_exif.py /photos/ --all

    # Generate CSV report
    python3 scripts/verify_gps_exif.py /photos/ --all --csv report.csv

    # Check for missing GPS data
    python3 scripts/verify_gps_exif.py /photos/ --all --missing-only

Output Format:
    Photo: mothbox_2025_01_15__12_30_00.jpg
    Has GPS: Yes
    Latitude: 37.7749° N
    Longitude: 122.4194° W
    Timestamp: 2025-01-15 12:30:00 UTC
    Altitude: 15.2 m
    Satellites: 8
    HDOP: 1.2
    Fix Quality: Good
"""

import argparse
import csv
import sys
from pathlib import Path
from typing import List, Dict, Any

from lib.gps_exif_lib import verify_gps_exif


def print_gps_info(photo_path: Path, info: Dict[str, Any]) -> None:
    """Print human-readable GPS EXIF information."""
    pass


def generate_csv_report(
    results: List[Dict[str, Any]],
    output_path: Path
) -> None:
    """Generate CSV report of GPS EXIF data."""
    pass


def main():
    """Main entry point for verification tool."""
    # Implementation...
    pass


if __name__ == '__main__':
    main()
```

---

## 4. Implementation Steps

### Phase 1: Core Library (Week 1)

- [ ] **Step 1.1**: Create `lib/gps_exif_lib.py` skeleton
  - [ ] Implement `get_gps_data_from_controls()`
  - [ ] Implement `decimal_to_dms()` conversion
  - [ ] Write unit tests for coordinate conversion

- [ ] **Step 1.2**: Implement EXIF embedding
  - [ ] Implement `build_gps_ifd()` with all GPS tags
  - [ ] Implement `embed_gps_exif()` with atomic write
  - [ ] Add integrity verification after write
  - [ ] Write unit tests with mock photos

- [ ] **Step 1.3**: Add verification functions
  - [ ] Implement `verify_gps_exif()`
  - [ ] Implement `is_already_tagged()`
  - [ ] Write unit tests for reading EXIF

### Phase 2: Main Tagger Script (Week 2)

- [ ] **Step 2.1**: Create `gps_exif_tagger.py` skeleton
  - [ ] Implement argument parsing
  - [ ] Implement logging setup
  - [ ] Add hardware config checks (GPS enabled)

- [ ] **Step 2.2**: Implement batch mode
  - [ ] Implement `process_single_photo()`
  - [ ] Implement `batch_process_directory()`
  - [ ] Add progress reporting
  - [ ] Write integration tests

- [ ] **Step 2.3**: Implement immediate mode
  - [ ] Implement `watch_directory()` with polling
  - [ ] Add graceful shutdown handling (SIGTERM)
  - [ ] Add error recovery (retry logic)
  - [ ] Write integration tests

### Phase 3: Utilities (Week 3)

- [ ] **Step 3.1**: Create batch tagging utility
  - [ ] Implement `scripts/batch_tag_photos.py`
  - [ ] Add date range filtering
  - [ ] Add GPS coordinate override
  - [ ] Write integration tests

- [ ] **Step 3.2**: Create verification tool
  - [ ] Implement `scripts/verify_gps_exif.py`
  - [ ] Add CSV report generation
  - [ ] Add missing GPS detection
  - [ ] Write integration tests

### Phase 4: Systemd Service (Week 4)

- [ ] **Step 4.1**: Create systemd service file
  - [ ] Write `services/gps-exif-tagger.service`
  - [ ] Configure service dependencies (after gpsd)
  - [ ] Add restart policy (on-failure)

- [ ] **Step 4.2**: Add installation script
  - [ ] Update `install_mothbox.sh` to install service
  - [ ] Add service enable/start commands
  - [ ] Add service status check

### Phase 5: Web UI Integration (Optional, Week 5)

- [ ] **Step 5.1**: Create API routes
  - [ ] Implement `webui/backend/routes/gps_exif.py`
  - [ ] Add `/api/gps-exif/status` endpoint
  - [ ] Add `/api/gps-exif/tag-photo` endpoint
  - [ ] Add `/api/gps-exif/batch-tag` endpoint

- [ ] **Step 5.2**: Add frontend components
  - [ ] Add GPS EXIF status panel to Dashboard
  - [ ] Add "Tag Photo" button to Gallery
  - [ ] Add batch tagging modal
  - [ ] Write frontend tests

### Phase 6: Testing & Documentation (Week 6)

- [ ] **Step 6.1**: Write comprehensive tests
  - [ ] Unit tests (85% coverage minimum)
  - [ ] Integration tests (end-to-end workflows)
  - [ ] Performance tests (batch processing speed)
  - [ ] Edge case tests (see Section 9)

- [ ] **Step 6.2**: Write documentation
  - [ ] Update CLAUDE.md with GPS EXIF architecture
  - [ ] Create GPS_EXIF_GUIDE.md user guide
  - [ ] Update TESTING_PROCEDURE.md
  - [ ] Add docstrings to all functions

---

## 5. Testing Strategy

### 5.1 Unit Tests

**File**: `Tests/unit/test_gps_exif_lib.py`

```python
"""Unit tests for GPS EXIF library."""

import pytest
from pathlib import Path
from lib.gps_exif_lib import (
    get_gps_data_from_controls,
    decimal_to_dms,
    build_gps_ifd,
    embed_gps_exif,
    verify_gps_exif,
    is_already_tagged
)


class TestCoordinateConversion:
    """Test decimal to DMS conversion."""

    def test_positive_latitude(self):
        """Test north latitude conversion."""
        dms, ref = decimal_to_dms(37.7749, is_latitude=True)
        assert ref == 'N'
        assert dms[0] == (37, 1)  # degrees
        assert dms[1] == (46, 1)  # minutes
        # seconds = (0.7749 - 46/60) * 60 * 60 = 29.64
        assert dms[2] == (2964, 100)

    def test_negative_longitude(self):
        """Test west longitude conversion."""
        dms, ref = decimal_to_dms(-122.4194, is_latitude=False)
        assert ref == 'W'
        assert dms[0] == (122, 1)
        assert dms[1] == (25, 1)
        # seconds = (0.4194 - 25/60) * 60 * 60 = 9.84
        assert dms[2] == (984, 100)

    def test_zero_coordinates(self):
        """Test coordinates at origin (0, 0)."""
        dms_lat, ref_lat = decimal_to_dms(0.0, is_latitude=True)
        dms_lon, ref_lon = decimal_to_dms(0.0, is_latitude=False)
        assert ref_lat == 'N'  # Default to north
        assert ref_lon == 'E'  # Default to east
        assert dms_lat[0] == (0, 1)
        assert dms_lon[0] == (0, 1)

    def test_extreme_latitudes(self):
        """Test near-pole latitudes."""
        # North pole
        dms, ref = decimal_to_dms(89.9999, is_latitude=True)
        assert ref == 'N'
        assert dms[0] == (89, 1)

        # South pole
        dms, ref = decimal_to_dms(-89.9999, is_latitude=True)
        assert ref == 'S'
        assert dms[0] == (89, 1)


class TestGPSDataExtraction:
    """Test reading GPS data from controls.txt."""

    @pytest.fixture
    def mock_controls_file(self, tmp_path, monkeypatch):
        """Create temporary controls.txt with GPS data."""
        controls = tmp_path / "controls.txt"
        controls.write_text("""
gpstime=1705329000
lat=37.7749
lon=-122.4194
gps_fix_mode=3
gps_satellites_used=8
gps_hdop=1.2
gps_pdop=2.1
""")
        from mothbox_paths import CONTROLS_FILE
        monkeypatch.setattr('mothbox_paths.CONTROLS_FILE', controls)
        return controls

    def test_read_valid_gps_data(self, mock_controls_file):
        """Test reading valid GPS data from controls.txt."""
        gps_data = get_gps_data_from_controls()
        assert gps_data['latitude'] == 37.7749
        assert gps_data['longitude'] == -122.4194
        assert gps_data['gpstime'] == 1705329000
        assert gps_data['fix_mode'] == 3
        assert gps_data['satellites_used'] == 8
        assert gps_data['hdop'] == 1.2
        assert gps_data['pdop'] == 2.1
        assert gps_data['has_fix'] is True

    def test_read_no_gps_fix(self, tmp_path, monkeypatch):
        """Test reading controls.txt with no GPS fix."""
        controls = tmp_path / "controls.txt"
        controls.write_text("""
gpstime=0
lat=n/a
lon=n/a
gps_fix_mode=0
""")
        monkeypatch.setattr('mothbox_paths.CONTROLS_FILE', controls)

        gps_data = get_gps_data_from_controls()
        assert gps_data['latitude'] is None
        assert gps_data['longitude'] is None
        assert gps_data['has_fix'] is False


class TestEXIFEmbedding:
    """Test EXIF embedding functions."""

    @pytest.fixture
    def sample_photo(self, tmp_path):
        """Create a minimal JPEG for testing."""
        # Create minimal valid JPEG (will use PIL to create)
        from PIL import Image
        photo = tmp_path / "test_photo.jpg"
        img = Image.new('RGB', (100, 100), color='red')
        img.save(photo, 'JPEG')
        return photo

    def test_embed_gps_exif_success(self, sample_photo):
        """Test successful GPS EXIF embedding."""
        gps_data = {
            'latitude': 37.7749,
            'longitude': -122.4194,
            'gpstime': 1705329000,
            'fix_mode': 3,
            'satellites_used': 8,
            'hdop': 1.2,
            'pdop': 2.1,
            'has_fix': True
        }

        result = embed_gps_exif(sample_photo, gps_data=gps_data)
        assert result['success'] is True
        assert result['gps_embedded'] is True
        assert result['error'] is None

        # Verify GPS data was written
        info = verify_gps_exif(sample_photo)
        assert info['has_gps'] is True
        assert abs(info['latitude'] - 37.7749) < 0.0001
        assert abs(info['longitude'] - (-122.4194)) < 0.0001

    def test_embed_gps_exif_no_fix(self, sample_photo):
        """Test GPS embedding skipped when no GPS fix."""
        gps_data = {
            'latitude': None,
            'longitude': None,
            'has_fix': False
        }

        result = embed_gps_exif(sample_photo, gps_data=gps_data)
        assert result['success'] is True
        assert result['skipped'] is True
        assert result['gps_embedded'] is False

    def test_embed_gps_exif_idempotent(self, sample_photo):
        """Test GPS embedding is idempotent."""
        gps_data = {
            'latitude': 37.7749,
            'longitude': -122.4194,
            'gpstime': 1705329000,
            'has_fix': True
        }

        # First embedding
        result1 = embed_gps_exif(sample_photo, gps_data=gps_data)
        assert result1['success'] is True
        assert result1['original_had_gps'] is False

        # Second embedding (should detect existing GPS)
        result2 = embed_gps_exif(sample_photo, gps_data=gps_data)
        assert result2['success'] is True
        assert result2['original_had_gps'] is True

    def test_embed_gps_exif_with_backup(self, sample_photo):
        """Test backup file creation."""
        gps_data = {
            'latitude': 37.7749,
            'longitude': -122.4194,
            'has_fix': True
        }

        result = embed_gps_exif(sample_photo, gps_data=gps_data, backup=True)
        assert result['success'] is True
        assert result['backup_path'] is not None
        assert result['backup_path'].exists()
        assert result['backup_path'].suffix == '.bak'

    def test_embed_gps_exif_dry_run(self, sample_photo):
        """Test dry run mode doesn't modify file."""
        original_mtime = sample_photo.stat().st_mtime

        gps_data = {
            'latitude': 37.7749,
            'longitude': -122.4194,
            'has_fix': True
        }

        result = embed_gps_exif(sample_photo, gps_data=gps_data, dry_run=True)
        assert result['success'] is True

        # File should not be modified
        assert sample_photo.stat().st_mtime == original_mtime
        info = verify_gps_exif(sample_photo)
        assert info['has_gps'] is False


@pytest.mark.parametrize("invalid_path", [
    "nonexistent.jpg",
    "test.txt",  # Not a JPEG
    "test.png",  # Not a JPEG
])
def test_embed_gps_exif_invalid_input(invalid_path):
    """Test error handling for invalid inputs."""
    with pytest.raises((FileNotFoundError, ValueError)):
        embed_gps_exif(Path(invalid_path))
```

### 5.2 Integration Tests

**File**: `Tests/integration/test_gps_exif_workflow.py`

```python
"""Integration tests for GPS EXIF end-to-end workflows."""

import pytest
import time
from pathlib import Path
from PIL import Image
import piexif

from mothbox_paths import PHOTOS_DIR, CONTROLS_FILE
from lib.gps_exif_lib import embed_gps_exif, verify_gps_exif
from gps_exif_tagger import batch_process_directory, process_single_photo


@pytest.mark.hardware
@pytest.mark.integration
class TestGPSEXIFWorkflow:
    """Test complete GPS EXIF workflow with real hardware."""

    def test_end_to_end_workflow(self, tmp_path):
        """
        Test complete workflow: GPS.py -> controls.txt -> photo -> EXIF embed.

        Steps:
            1. Simulate GPS.py updating controls.txt
            2. Simulate TakePhoto.py creating photo
            3. Run gps_exif_tagger.py on photo
            4. Verify GPS EXIF is correct
        """
        # Setup: Create temporary photos directory
        photos_dir = tmp_path / "photos"
        photos_dir.mkdir()

        # Step 1: Simulate GPS.py writing to controls.txt
        controls_file = tmp_path / "controls.txt"
        controls_file.write_text("""
gpstime=1705329000
lat=37.7749
lon=-122.4194
gps_fix_mode=3
gps_satellites_used=8
gps_hdop=1.2
gps_pdop=2.1
""")

        # Step 2: Simulate TakePhoto.py creating photo (no GPS EXIF)
        photo_path = photos_dir / "mothbox_2025_01_15__12_30_00.jpg"
        img = Image.new('RGB', (640, 480), color='blue')

        # Add camera EXIF (like TakePhoto.py does)
        exif_dict = {
            "0th": {piexif.ImageIFD.Make: b"MothboxV4"},
            "Exif": {
                piexif.ExifIFD.ExposureTime: (1, 100),
                piexif.ExifIFD.ISOSpeed: 100,
            },
            "GPS": {}  # Empty GPS IFD
        }
        exif_bytes = piexif.dump(exif_dict)
        img.save(photo_path, 'JPEG', exif=exif_bytes)

        # Verify photo exists and has no GPS
        assert photo_path.exists()
        info_before = verify_gps_exif(photo_path)
        assert info_before['has_gps'] is False

        # Step 3: Run GPS EXIF tagger
        result = process_single_photo(photo_path)
        assert result['success'] is True
        assert result['gps_embedded'] is True

        # Step 4: Verify GPS EXIF was embedded correctly
        info_after = verify_gps_exif(photo_path)
        assert info_after['has_gps'] is True
        assert abs(info_after['latitude'] - 37.7749) < 0.0001
        assert abs(info_after['longitude'] - (-122.4194)) < 0.0001
        assert info_after['satellites'] == "8"

        # Verify original camera EXIF is preserved
        exif_dict_after = piexif.load(str(photo_path))
        assert exif_dict_after["0th"][piexif.ImageIFD.Make] == b"MothboxV4"
        assert exif_dict_after["Exif"][piexif.ExifIFD.ExposureTime] == (1, 100)

    def test_batch_processing_mixed_photos(self, tmp_path):
        """
        Test batch processing directory with mixed photos:
        - Photos without GPS EXIF (should be tagged)
        - Photos with GPS EXIF (should be skipped)
        - Non-JPEG files (should be skipped)
        """
        photos_dir = tmp_path / "photos"
        photos_dir.mkdir()

        # Create 5 photos without GPS
        for i in range(5):
            photo = photos_dir / f"photo_{i}.jpg"
            img = Image.new('RGB', (100, 100), color='red')
            img.save(photo, 'JPEG')

        # Create 2 photos with GPS (pre-tagged)
        for i in range(5, 7):
            photo = photos_dir / f"photo_{i}.jpg"
            img = Image.new('RGB', (100, 100), color='blue')
            gps_ifd = {
                piexif.GPSIFD.GPSLatitude: ((37, 1), (46, 1), (2964, 100)),
                piexif.GPSIFD.GPSLatitudeRef: b'N',
            }
            exif_dict = {"GPS": gps_ifd}
            exif_bytes = piexif.dump(exif_dict)
            img.save(photo, 'JPEG', exif=exif_bytes)

        # Create 1 non-JPEG file
        (photos_dir / "readme.txt").write_text("Test file")

        # Run batch processing
        stats = batch_process_directory(photos_dir, pattern="*.jpg", force=False)

        # Verify statistics
        assert stats['total'] == 7  # 5 untagged + 2 tagged
        assert stats['tagged'] == 5  # Only untagged photos processed
        assert stats['skipped'] == 2  # Already tagged photos skipped
        assert stats['errors'] == 0

    def test_watch_mode_realtime_tagging(self, tmp_path):
        """
        Test watch mode: Monitor directory and tag new photos.

        Simulates:
            1. Start watch_directory() in background thread
            2. Create new photo (simulate TakePhoto.py)
            3. Wait for tagger to process it
            4. Verify GPS EXIF was added
        """
        # This test requires threading/multiprocessing
        # Implementation deferred to actual testing phase
        pytest.skip("Watch mode test requires background thread setup")


@pytest.mark.integration
class TestBatchTaggingUtility:
    """Test batch_tag_photos.py utility."""

    def test_batch_tag_with_date_filter(self, tmp_path):
        """Test batch tagging with date range filter."""
        photos_dir = tmp_path / "photos"
        photos_dir.mkdir()

        # Create photos with different dates
        photos = [
            "mothbox_2025_01_10__12_00_00.jpg",  # Jan 10 (before range)
            "mothbox_2025_01_15__12_00_00.jpg",  # Jan 15 (in range)
            "mothbox_2025_01_20__12_00_00.jpg",  # Jan 20 (in range)
            "mothbox_2025_01_25__12_00_00.jpg",  # Jan 25 (after range)
        ]

        for photo_name in photos:
            photo = photos_dir / photo_name
            img = Image.new('RGB', (100, 100), color='red')
            img.save(photo, 'JPEG')

        # Run batch tagger with date filter: Jan 15-20
        from scripts.batch_tag_photos import filter_photos_by_date
        from datetime import datetime

        photo_paths = [photos_dir / p for p in photos]
        filtered = filter_photos_by_date(
            photo_paths,
            start_date=datetime(2025, 1, 15),
            end_date=datetime(2025, 1, 20)
        )

        # Verify only Jan 15 and Jan 20 are included
        assert len(filtered) == 2
        assert "2025_01_15" in str(filtered[0])
        assert "2025_01_20" in str(filtered[1])

    def test_batch_tag_with_coordinate_override(self, tmp_path):
        """Test batch tagging with GPS coordinate override."""
        photos_dir = tmp_path / "photos"
        photos_dir.mkdir()

        photo = photos_dir / "test_photo.jpg"
        img = Image.new('RGB', (100, 100), color='red')
        img.save(photo, 'JPEG')

        # Override GPS coordinates (different from controls.txt)
        override_gps = {
            'latitude': 40.7128,  # NYC
            'longitude': -74.0060,
            'gpstime': 1705329000,
            'has_fix': True
        }

        result = embed_gps_exif(photo, gps_data=override_gps)
        assert result['success'] is True

        # Verify override coordinates were used
        info = verify_gps_exif(photo)
        assert abs(info['latitude'] - 40.7128) < 0.0001
        assert abs(info['longitude'] - (-74.0060)) < 0.0001
```

### 5.3 Test Data Needed

```python
# Tests/fixtures/gps_test_data.py
"""Test fixtures for GPS EXIF testing."""

GPS_TEST_COORDINATES = {
    'san_francisco': {
        'latitude': 37.7749,
        'longitude': -122.4194,
        'name': 'San Francisco, CA'
    },
    'new_york': {
        'latitude': 40.7128,
        'longitude': -74.0060,
        'name': 'New York, NY'
    },
    'london': {
        'latitude': 51.5074,
        'longitude': -0.1278,
        'name': 'London, UK'
    },
    'sydney': {
        'latitude': -33.8688,
        'longitude': 151.2093,
        'name': 'Sydney, Australia'
    },
    'north_pole': {
        'latitude': 89.9999,
        'longitude': 0.0,
        'name': 'North Pole'
    },
    'south_pole': {
        'latitude': -89.9999,
        'longitude': 0.0,
        'name': 'South Pole'
    },
    'prime_meridian': {
        'latitude': 0.0,
        'longitude': 0.0,
        'name': 'Null Island (0°, 0°)'
    },
    'date_line': {
        'latitude': 0.0,
        'longitude': 180.0,
        'name': 'International Date Line'
    }
}

MOCK_CONTROLS_TXT_WITH_GPS = """
gpstime=1705329000
lat=37.7749
lon=-122.4194
gps_fix_mode=3
gps_satellites_visible=12
gps_satellites_used=8
gps_hdop=1.2
gps_pdop=2.1
last_known_lat=37.7749
last_known_lon=-122.4194
last_position_time=1705329000
"""

MOCK_CONTROLS_TXT_NO_GPS = """
gpstime=0
lat=n/a
lon=n/a
gps_fix_mode=0
gps_satellites_visible=0
gps_satellites_used=0
gps_hdop=99.99
gps_pdop=99.99
last_known_lat=n/a
last_known_lon=n/a
last_position_time=0
"""
```

---

## 6. Deployment Options

### 6.1 Immediate Mode (Systemd Service)

**Use Case**: Tag photos immediately after capture (production deployments)

**File**: `services/gps-exif-tagger.service`

```ini
[Unit]
Description=Mothbox GPS EXIF Tagger
Documentation=https://github.com/Digital-Naturalism-Laboratories/Mothbox
After=network.target gpsd.service
Wants=gpsd.service

[Service]
Type=simple
User=pi
Group=pi
WorkingDirectory=/opt/mothbox
Environment="MOTHBOX_HOME=/opt/mothbox"
Environment="PYTHONUNBUFFERED=1"

# Main service command (watch mode with 10 second polling)
ExecStart=/usr/bin/python3 /opt/mothbox/gps_exif_tagger.py \
    --mode immediate \
    --watch \
    --interval 10 \
    --directory /var/lib/mothbox/photos

# Restart policy
Restart=on-failure
RestartSec=30s

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=gps-exif-tagger

# Resource limits
MemoryMax=256M
CPUQuota=25%

# Security hardening
PrivateTmp=true
ProtectSystem=strict
ReadWritePaths=/var/lib/mothbox/photos
ReadOnlyPaths=/etc/mothbox

[Install]
WantedBy=multi-user.target
```

**Installation**:
```bash
# Copy service file
sudo cp services/gps-exif-tagger.service /etc/systemd/system/

# Reload systemd
sudo systemctl daemon-reload

# Enable service (start on boot)
sudo systemctl enable gps-exif-tagger

# Start service now
sudo systemctl start gps-exif-tagger

# Check status
sudo systemctl status gps-exif-tagger

# View logs
sudo journalctl -u gps-exif-tagger -f
```

### 6.2 Lazy Mode (On-Demand via Web UI)

**Use Case**: Tag photos only when accessed (reduces CPU usage)

**Implementation**: Add API endpoint to Web UI

```python
# webui/backend/routes/gps_exif.py

@gps_exif_bp.route('/api/gps-exif/tag-photo', methods=['POST'])
@csrf.exempt  # CSRF handled by Flask-WTF
def tag_photo():
    """Tag a single photo with GPS EXIF on-demand."""
    data = request.json
    photo_path = Path(data.get('photo_path'))

    # Security: Validate photo path is within PHOTOS_DIR
    if not photo_path.is_relative_to(PHOTOS_DIR):
        return jsonify({'error': 'Invalid photo path'}), 400

    # Tag photo
    from lib.gps_exif_lib import embed_gps_exif
    result = embed_gps_exif(photo_path)

    return jsonify(result), 200 if result['success'] else 500
```

**Frontend**: Add "Tag Photo" button to Gallery

```jsx
// webui/frontend/src/components/PhotoGallery.jsx

function PhotoGallery({ photos }) {
  const tagPhotoMutation = useMutation({
    mutationFn: (photoPath) =>
      fetch('/api/gps-exif/tag-photo', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ photo_path: photoPath })
      }),
    onSuccess: () => {
      toast.success('GPS EXIF added successfully');
    }
  });

  return (
    <div className="grid grid-cols-3 gap-4">
      {photos.map(photo => (
        <div key={photo.path} className="relative">
          <img src={photo.url} alt={photo.name} />
          {!photo.hasGPS && (
            <button
              onClick={() => tagPhotoMutation.mutate(photo.path)}
              className="absolute top-2 right-2 bg-blue-500 text-white px-2 py-1 rounded"
            >
              Add GPS
            </button>
          )}
        </div>
      ))}
    </div>
  );
}
```

### 6.3 Batch Mode (Manual Execution)

**Use Case**: One-time processing, retroactive tagging, troubleshooting

**Command Line**:
```bash
# Tag all photos in photos directory
python3 gps_exif_tagger.py --mode batch --directory /var/lib/mothbox/photos

# Tag photos from January 2025 only
python3 scripts/batch_tag_photos.py --start 2025-01-01 --end 2025-01-31

# Tag photos with custom GPS coordinates (e.g., after manual correction)
python3 scripts/batch_tag_photos.py --lat 37.7749 --lon -122.4194

# Dry run (test without modifying files)
python3 gps_exif_tagger.py --mode batch --dry-run --verbose

# Create backups before modifying
python3 gps_exif_tagger.py --mode batch --backup
```

**Cron Job** (alternative to systemd service):
```cron
# Tag new photos every 5 minutes
*/5 * * * * /usr/bin/python3 /opt/mothbox/gps_exif_tagger.py --mode batch --directory /var/lib/mothbox/photos >> /var/log/mothbox/gps-exif-tagger.log 2>&1
```

### 6.4 Deployment Mode Comparison

| Mode | When to Use | CPU Impact | Latency | Retroactive | Complexity |
|------|-------------|------------|---------|-------------|------------|
| **Immediate (systemd)** | Production deployments | Low (10s polling) | ~10 seconds | No | Medium |
| **Lazy (on-demand)** | Low-power setups | Minimal | On-access | No | Low |
| **Batch (manual)** | Troubleshooting, retroactive | High (one-time) | Manual | Yes | Low |
| **Cron (scheduled)** | Compromise | Very low | 1-5 minutes | No | Low |

**Recommendation**: Use **immediate mode (systemd)** for production, **lazy mode** for low-power deployments, **batch mode** for retroactive tagging.

---

## 7. Code Examples

### 7.1 Minimal Working Example

```python
#!/usr/bin/env python3
"""Minimal example: Tag a single photo with GPS EXIF."""

from pathlib import Path
from lib.gps_exif_lib import embed_gps_exif

# Tag photo using GPS data from controls.txt
photo = Path('/var/lib/mothbox/photos/mothbox_2025_01_15__12_30_00.jpg')
result = embed_gps_exif(photo)

if result['success']:
    if result['gps_embedded']:
        print(f"✓ GPS EXIF added to {photo.name}")
    elif result['skipped']:
        print(f"⊘ No GPS fix available, skipped")
else:
    print(f"✗ Error: {result['error']}")
```

### 7.2 Batch Processing Example

```python
#!/usr/bin/env python3
"""Example: Batch process all photos in directory."""

from pathlib import Path
from lib.gps_exif_lib import embed_gps_exif

photos_dir = Path('/var/lib/mothbox/photos')
photos = list(photos_dir.glob('*.jpg'))

print(f"Found {len(photos)} photos")

stats = {'tagged': 0, 'skipped': 0, 'errors': 0}

for photo in photos:
    result = embed_gps_exif(photo)

    if result['success']:
        if result['gps_embedded']:
            stats['tagged'] += 1
        else:
            stats['skipped'] += 1
    else:
        stats['errors'] += 1
        print(f"Error processing {photo.name}: {result['error']}")

print(f"\nResults:")
print(f"  Tagged: {stats['tagged']}")
print(f"  Skipped: {stats['skipped']}")
print(f"  Errors: {stats['errors']}")
```

### 7.3 Verification Example

```python
#!/usr/bin/env python3
"""Example: Verify GPS EXIF in a photo."""

from pathlib import Path
from lib.gps_exif_lib import verify_gps_exif

photo = Path('/var/lib/mothbox/photos/mothbox_2025_01_15__12_30_00.jpg')
info = verify_gps_exif(photo)

if info['has_gps']:
    print(f"Photo: {photo.name}")
    print(f"Latitude: {info['latitude']:.6f}°")
    print(f"Longitude: {info['longitude']:.6f}°")
    print(f"Timestamp: {info['timestamp']}")
    print(f"Satellites: {info['satellites']}")
    print(f"HDOP: {info['hdop']}")
else:
    print(f"Photo {photo.name} has no GPS EXIF data")
```

### 7.4 Custom GPS Coordinates Example

```python
#!/usr/bin/env python3
"""Example: Tag photo with custom GPS coordinates."""

from pathlib import Path
from lib.gps_exif_lib import embed_gps_exif

# Custom GPS data (e.g., manually corrected coordinates)
custom_gps = {
    'latitude': 37.7749,
    'longitude': -122.4194,
    'gpstime': 1705329000,
    'altitude': 15.0,
    'satellites_used': 8,
    'hdop': 1.2,
    'has_fix': True
}

photo = Path('/var/lib/mothbox/photos/mothbox_2025_01_15__12_30_00.jpg')
result = embed_gps_exif(photo, gps_data=custom_gps, backup=True)

if result['success']:
    print(f"✓ Custom GPS coordinates embedded")
    print(f"  Backup saved to: {result['backup_path']}")
else:
    print(f"✗ Error: {result['error']}")
```

---

## 8. Migration Path

### 8.1 Handling Existing Photos

**Scenario**: Mothbox has been deployed for months without GPS EXIF. Now GPS EXIF feature is added.

**Solution**: Batch retroactive tagging

```bash
# Step 1: Verify GPS data is available in controls.txt
cat /etc/mothbox/controls.txt | grep -E "lat|lon|gpstime"

# Step 2: Run batch tagger in dry-run mode
python3 gps_exif_tagger.py --mode batch --dry-run --verbose

# Step 3: Review dry-run output, then run for real
python3 gps_exif_tagger.py --mode batch --backup

# Step 4: Verify random sample of photos
python3 scripts/verify_gps_exif.py /var/lib/mothbox/photos/ --all | head -20
```

### 8.2 Handling Photos Without GPS

**Scenario**: Photos captured before GPS module was installed.

**Options**:

1. **Skip**: Leave photos untagged (default behavior)
   ```bash
   # No action needed - tagger will skip photos without GPS fix
   ```

2. **Use last known position**: Tag with `last_known_lat`/`last_known_lon`
   ```python
   # In gps_exif_lib.py, modify get_gps_data_from_controls():
   if gps_data['latitude'] is None and last_known_lat != 'n/a':
       gps_data['latitude'] = float(last_known_lat)
       gps_data['longitude'] = float(last_known_lon)
       gps_data['has_fix'] = True  # Mark as "approximate"
   ```

3. **Manual coordinates**: Use batch tagger with `--lat`/`--lon`
   ```bash
   # Tag old photos with deployment site coordinates
   python3 scripts/batch_tag_photos.py \
       --start 2024-01-01 --end 2024-12-31 \
       --lat 37.7749 --lon -122.4194
   ```

### 8.3 Data Integrity During Migration

**Concern**: Ensure photo files aren't corrupted during batch tagging.

**Safeguards**:

1. **Create backups**: Use `--backup` flag
   ```bash
   python3 gps_exif_tagger.py --mode batch --backup
   ```

2. **Atomic writes**: Library uses temp file + rename pattern
   ```python
   # In embed_gps_exif():
   temp_path = photo_path.with_suffix('.jpg.tmp')
   img.save(temp_path, exif=exif_bytes)
   temp_path.replace(photo_path)  # Atomic rename
   ```

3. **Integrity verification**: Verify JPEG after write
   ```python
   # In embed_gps_exif():
   from PIL import Image
   try:
       Image.open(photo_path).verify()
   except Exception as e:
       # Restore from backup or log error
       raise ValueError(f"JPEG integrity check failed: {e}")
   ```

4. **Checksum validation**: Compare file size before/after
   ```python
   original_size = photo_path.stat().st_size
   # ... modify photo ...
   new_size = photo_path.stat().st_size
   if abs(new_size - original_size) > 10000:  # Allow 10KB EXIF overhead
       raise ValueError("File size changed unexpectedly")
   ```

---

## 9. Edge Cases

### 9.1 GPS Unavailable

**Scenario**: GPS module is disabled or not working.

**Behavior**: Skip tagging gracefully.

```python
def get_gps_data_from_controls():
    hw_config = get_hardware_config()

    if not hw_config['gps_enabled']:
        return {
            'has_fix': False,
            'latitude': None,
            'longitude': None,
            'error': 'GPS disabled in configuration'
        }

    # Continue reading GPS data...
```

### 9.2 Timestamp Mismatch

**Scenario**: Photo timestamp doesn't match GPS timestamp.

**Causes**:
- GPS.py runs every 15 minutes, photo captured between runs
- System clock drift
- GPS time sync hasn't run yet

**Solution**: Use `gpstime` from `controls.txt` (most recent GPS fix)

```python
# GPS timestamp may be up to 15 minutes old (GPS.py polling interval)
# This is acceptable - location doesn't change significantly in 15 minutes
# for stationary Mothbox deployments

def build_gps_ifd(gps_data):
    # Use GPS timestamp from controls.txt, NOT photo capture time
    gps_timestamp = datetime.fromtimestamp(gps_data['gpstime'], tz=timezone.utc)

    gps_ifd = {
        piexif.GPSIFD.GPSTimeStamp: (
            (gps_timestamp.hour, 1),
            (gps_timestamp.minute, 1),
            (gps_timestamp.second, 1)
        ),
        piexif.GPSIFD.GPSDateStamp: gps_timestamp.strftime('%Y:%m:%d'),
    }

    return gps_ifd
```

**Future Enhancement**: Store GPS timestamp in photo filename for exact correlation.

### 9.3 Corrupted EXIF

**Scenario**: Photo has corrupted existing EXIF data.

**Behavior**: Skip photo and log error.

```python
def embed_gps_exif(photo_path, ...):
    try:
        exif_dict = piexif.load(str(photo_path))
    except piexif.InvalidImageDataError as e:
        return {
            'success': False,
            'error': f'Corrupted EXIF data: {e}',
            'skipped': True
        }

    # Continue processing...
```

### 9.4 Read-Only Filesystem

**Scenario**: Photos directory is mounted read-only (e.g., during backup).

**Behavior**: Fail gracefully and retry later.

```python
def embed_gps_exif(photo_path, ...):
    try:
        # ... write to photo ...
    except PermissionError as e:
        return {
            'success': False,
            'error': f'Permission denied (filesystem may be read-only): {e}',
            'skipped': False,
            'retry': True  # Signal caller to retry later
        }
```

### 9.5 Concurrent Access

**Scenario**: TakePhoto.py writing photo while GPS tagger tries to read it.

**Solution**: Retry with exponential backoff.

```python
def embed_gps_exif(photo_path, max_retries=3, ...):
    for attempt in range(max_retries):
        try:
            # Open and read photo
            img = Image.open(photo_path)
            exif_dict = piexif.load(str(photo_path))
            break
        except (OSError, IOError) as e:
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)  # Exponential backoff: 1s, 2s, 4s
                continue
            else:
                return {'success': False, 'error': f'File locked after {max_retries} attempts'}

    # Continue processing...
```

### 9.6 Large Photo Directory

**Scenario**: 10,000+ photos in directory (months of deployment).

**Performance Optimization**:

1. **Index recently modified files**: Only scan photos modified in last 24 hours
   ```python
   def get_recent_photos(directory, hours=24):
       cutoff = time.time() - (hours * 3600)
       return [
           p for p in directory.glob('*.jpg')
           if p.stat().st_mtime > cutoff
       ]
   ```

2. **Parallel processing**: Use multiprocessing for batch mode
   ```python
   from multiprocessing import Pool

   def batch_process_directory(directory, num_workers=4, ...):
       photos = list(directory.glob('*.jpg'))

       with Pool(num_workers) as pool:
           results = pool.map(process_single_photo, photos)

       # Aggregate results...
   ```

3. **Progress tracking**: Show progress for large batches
   ```python
   from tqdm import tqdm

   for photo in tqdm(photos, desc="Tagging photos"):
       result = embed_gps_exif(photo)
   ```

### 9.7 GPS Precision Degradation

**Scenario**: GPS fix has poor precision (HDOP > 5, few satellites).

**Solution**: Tag photo but include precision metadata.

```python
def build_gps_ifd(gps_data):
    gps_ifd = {
        # ... standard GPS tags ...
        piexif.GPSIFD.GPSDOP: (int(gps_data['hdop'] * 100), 100),
        piexif.GPSIFD.GPSSatellites: f"{gps_data['satellites_used']}",
    }

    # Add warning comment if precision is poor
    if gps_data['hdop'] > 5:
        logging.warning(
            f"Poor GPS precision (HDOP={gps_data['hdop']:.2f}). "
            f"Location may be inaccurate by 10+ meters."
        )

    return gps_ifd
```

**Quality Thresholds**:
- HDOP < 2: Excellent (±1-5m accuracy)
- HDOP 2-5: Good (±5-10m accuracy)
- HDOP 5-10: Moderate (±10-50m accuracy)
- HDOP > 10: Poor (±50-100m+ accuracy)

### 9.8 No Altitude Data

**Scenario**: 2D GPS fix (no altitude).

**Behavior**: Omit altitude tags from EXIF.

```python
def build_gps_ifd(gps_data):
    gps_ifd = {
        piexif.GPSIFD.GPSLatitude: ...,
        piexif.GPSIFD.GPSLongitude: ...,
    }

    # Only add altitude if available (3D fix)
    if gps_data.get('altitude') is not None:
        gps_ifd[piexif.GPSIFD.GPSAltitude] = (
            int(gps_data['altitude'] * 100), 100
        )
        gps_ifd[piexif.GPSIFD.GPSAltitudeRef] = 0  # Above sea level

    return gps_ifd
```

---

## 10. Success Criteria

### 10.1 Functional Requirements

- [ ] **FR1**: GPS EXIF data is embedded in JPEG photos captured by Mothbox
- [ ] **FR2**: GPS data includes: latitude, longitude, timestamp, altitude (if available), HDOP, satellite count
- [ ] **FR3**: Original camera EXIF (exposure, ISO, focus) is preserved
- [ ] **FR4**: System works without modifying `TakePhoto.py`
- [ ] **FR5**: Idempotent: Safe to run multiple times on same photo
- [ ] **FR6**: Graceful degradation: Works without GPS (skips tagging)
- [ ] **FR7**: Retroactive tagging: Can process existing photos

### 10.2 Performance Requirements

- [ ] **PR1**: Single photo processing: <500ms per photo
- [ ] **PR2**: Batch processing: >10 photos/second on Pi 4
- [ ] **PR3**: Immediate mode: <10 seconds latency after photo capture
- [ ] **PR4**: Memory footprint: <256MB RAM for immediate mode service
- [ ] **PR5**: CPU impact: <5% CPU utilization in immediate mode

### 10.3 Quality Requirements

- [ ] **QR1**: Test coverage: ≥85% line coverage
- [ ] **QR2**: No regressions: All existing tests pass
- [ ] **QR3**: Security: Passes Bandit scan (MEDIUM+ severity)
- [ ] **QR4**: Code quality: Passes Ruff linting
- [ ] **QR5**: Documentation: All public functions have docstrings
- [ ] **QR6**: User guide: GPS_EXIF_GUIDE.md created

### 10.4 Integration Requirements

- [ ] **IR1**: Systemd service installs cleanly on production systems
- [ ] **IR2**: Web UI displays GPS status (optional enhancement)
- [ ] **IR3**: Installation script includes GPS EXIF setup
- [ ] **IR4**: Works with both 4.x and 5.x firmware

### 10.5 Validation Tests

**Test 1: Basic GPS EXIF Embedding**
```bash
# Capture photo with TakePhoto.py
python3 /opt/mothbox/5.x/TakePhoto.py

# Run GPS EXIF tagger
python3 gps_exif_tagger.py --mode batch

# Verify GPS EXIF
python3 scripts/verify_gps_exif.py /var/lib/mothbox/photos/ --all | tail -5

# Expected: Photo has GPS coordinates matching controls.txt
```

**Test 2: Retroactive Batch Tagging**
```bash
# Tag all photos from January 2025
python3 scripts/batch_tag_photos.py --start 2025-01-01 --end 2025-01-31 --backup

# Verify statistics
# Expected: X photos tagged, Y skipped, 0 errors
```

**Test 3: Immediate Mode Service**
```bash
# Start GPS EXIF service
sudo systemctl start gps-exif-tagger

# Capture photo
python3 /opt/mothbox/5.x/TakePhoto.py

# Wait 15 seconds
sleep 15

# Check latest photo
python3 scripts/verify_gps_exif.py /var/lib/mothbox/photos/ --all | tail -1

# Expected: Photo has GPS EXIF within 15 seconds
```

**Test 4: No GPS Graceful Degradation**
```bash
# Disable GPS in controls.txt
sed -i 's/gps_enabled=true/gps_enabled=false/' /etc/mothbox/controls.txt

# Run GPS EXIF tagger
python3 gps_exif_tagger.py --mode batch

# Expected: All photos skipped, no errors
```

**Test 5: EXIF Preservation**
```bash
# Capture photo with TakePhoto.py (has camera EXIF)
python3 /opt/mothbox/5.x/TakePhoto.py

# Extract camera EXIF before tagging
exiftool -ExposureTime -ISO -FocalLength photo.jpg > before.txt

# Run GPS EXIF tagger
python3 gps_exif_tagger.py --mode batch

# Extract camera EXIF after tagging
exiftool -ExposureTime -ISO -FocalLength photo.jpg > after.txt

# Compare
diff before.txt after.txt

# Expected: No differences (camera EXIF preserved)
```

### 10.6 Acceptance Criteria

✅ **Feature is complete when**:

1. All functional requirements (FR1-FR7) are met
2. All performance requirements (PR1-PR5) are met
3. All quality requirements (QR1-QR6) are met
4. All validation tests (Test 1-5) pass
5. Documentation is complete and reviewed
6. Code is merged to main branch
7. Feature is deployed to at least one production Mothbox

---

## 11. Related Issues & Future Enhancements

### 11.1 Related Issues

- **Issue #19**: User authentication for Web UI (affects lazy mode API security)
- **Issue #13**: Hardware configuration validation (GPS module detection)
- **Issue #140**: Gallery improvements (display GPS coordinates in photo viewer)

### 11.2 Future Enhancements

**Enhancement 1: GPS Track Logging**
- Store GPS track log (time-series of positions)
- Enable GPS drift detection (stationary Mothbox shouldn't move)
- Visualize GPS track on map in Web UI

**Enhancement 2: Photo Location Map**
- Web UI map view showing photo locations
- Cluster photos by location
- Export KML/GeoJSON for Google Earth

**Enhancement 3: Altitude-based Filtering**
- Filter photos by elevation (useful for multi-site deployments)
- Detect Mothbox movement (altitude change)

**Enhancement 4: GPS-based Timezone Correction**
- Auto-adjust photo timestamps to local timezone using GPS coordinates
- Display local time in gallery instead of UTC

**Enhancement 5: Precision-based Quality Filtering**
- Mark low-precision GPS fixes in gallery
- Option to exclude poor GPS fixes from EXIF
- Alert user when GPS precision degrades

---

## 12. References

### 12.1 EXIF Standards

- **EXIF 2.3 Standard**: https://www.cipa.jp/std/documents/e/DC-008-2012_E.pdf
- **GPS EXIF Tag Specification**: https://exiftool.org/TagNames/GPS.html
- **piexif Documentation**: https://piexif.readthedocs.io/

### 12.2 Mothbox Documentation

- **CLAUDE.md**: Project architecture and development guidelines
- **GPS_SETUP.md**: GPS module installation guide
- **TESTING_PROCEDURE.md**: Manual hardware testing procedures

### 12.3 Code References

- **GPS.py** (`5.x/GPS.py`): GPS data acquisition
- **TakePhoto.py** (`5.x/TakePhoto.py`): Photo capture workflow
- **mothbox_paths.py**: Path resolution and hardware config
- **gps.py** (`webui/backend/routes/gps.py`): GPS API routes

---

## Appendix A: GPS EXIF Tag Reference

| EXIF Tag | piexif Constant | Format | Example | Description |
|----------|----------------|--------|---------|-------------|
| GPSVersionID | `GPSIFD.GPSVersionID` | 4 bytes | `(2, 3, 0, 0)` | EXIF 2.3 standard |
| GPSLatitude | `GPSIFD.GPSLatitude` | 3 rationals | `((37,1), (46,1), (2964,100))` | Latitude as DMS |
| GPSLatitudeRef | `GPSIFD.GPSLatitudeRef` | 2 bytes | `b'N'` | North or South |
| GPSLongitude | `GPSIFD.GPSLongitude` | 3 rationals | `((122,1), (25,1), (984,100))` | Longitude as DMS |
| GPSLongitudeRef | `GPSIFD.GPSLongitudeRef` | 2 bytes | `b'W'` | East or West |
| GPSAltitude | `GPSIFD.GPSAltitude` | 1 rational | `(1520, 100)` | Meters above sea level |
| GPSAltitudeRef | `GPSIFD.GPSAltitudeRef` | 1 byte | `0` | 0=above, 1=below |
| GPSTimeStamp | `GPSIFD.GPSTimeStamp` | 3 rationals | `((12,1), (30,1), (0,1))` | UTC time (HMS) |
| GPSDateStamp | `GPSIFD.GPSDateStamp` | 11 bytes | `b'2025:01:15'` | UTC date (YYYY:MM:DD) |
| GPSDOP | `GPSIFD.GPSDOP` | 1 rational | `(120, 100)` | HDOP × 100 |
| GPSSatellites | `GPSIFD.GPSSatellites` | ASCII string | `b'8'` | Number of satellites used |

---

## Appendix B: Example controls.txt with GPS Data

```ini
# Mothbox Configuration File
# GPS Module Configuration
gps_enabled=true
gps_device=/dev/ttyAMA0
gps_baudrate=9600
gps_timeout=60
gps_timeout_hot=15
gps_timeout_warm=60
gps_timeout_cold=90
gps_timeout_almanac=1200

# Current GPS Data (updated by GPS.py)
gpstime=1705329000
lat=37.7749
lon=-122.4194
gps_fix_mode=3
gps_satellites_visible=12
gps_satellites_used=8
gps_hdop=1.2
gps_pdop=2.1

# Last Known Position (fallback for intermittent GPS)
last_known_lat=37.7749
last_known_lon=-122.4194
last_position_time=1705329000

# Other Configuration...
softwareversion=5.0.0
Relay_Ch1=5
Relay_Ch2=19
Relay_Ch3=9
```

---

## Conclusion

This implementation specification provides a complete blueprint for implementing GPS EXIF embedding using a post-processing architecture. The approach is:

- **Non-invasive**: No changes to `TakePhoto.py`
- **Flexible**: Multiple deployment modes (immediate, lazy, batch)
- **Robust**: Handles edge cases gracefully
- **Retroactive**: Can tag existing photos
- **Well-tested**: Comprehensive test strategy
- **Production-ready**: Systemd service with proper error handling

Developers can follow this specification step-by-step to implement Issue #98 without needing to ask clarifying questions. All design decisions are documented with rationale, and all edge cases are explicitly handled.

**Estimated Implementation Time**: 4-6 weeks for complete implementation, testing, and documentation.

**Recommended Approach**: Start with Phase 1 (Core Library) and validate with unit tests before proceeding to subsequent phases. This ensures the foundation is solid before building deployment modes and utilities.
