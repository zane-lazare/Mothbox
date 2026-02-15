#!/usr/bin/env python3
"""GPS EXIF Tagger - Post-processing service for Mothbox photos.

This script monitors the photos directory and embeds GPS EXIF data
from controls.txt into newly captured photos.

Deployment Modes:
    1. Immediate (systemd service): Tags photos as they're captured
    2. Batch (manual): Tag all photos in directory

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
    --force                   Re-tag photos even if already have GPS EXIF
    --pattern GLOB            File pattern (default: *.jpg)
    --interval SECONDS        Polling interval for immediate mode (default: 10)
    --verbose, -v             Enable verbose logging
"""

import argparse
import logging
import sys
import time
from pathlib import Path
from typing import Any

# Path setup for accessing mothbox_paths at firmware root
_cli_dir = Path(__file__).resolve().parent
_webui_dir = _cli_dir.parent
_firmware_root = _webui_dir.parent
if str(_firmware_root) not in sys.path:
    sys.path.insert(0, str(_firmware_root))

from mothbox_paths import PHOTOS_DIR, get_hardware_config
from webui.backend.lib.gps_coordinate_resolver import resolve_coordinates
from webui.backend.lib.gps_exif_lib import (
    embed_gps_exif,
    get_gps_data_from_controls,
    is_already_tagged,
)
from webui.backend.services.deployment_service import DeploymentService

# Module exports
__all__ = [
    "setup_logging",
    "wait_for_file_stability",
    "process_single_photo",
    "batch_process_directory",
    "watch_directory",
    "main",
]


# Lazy-initialized deployment service for coordinate resolver
_deployment_service = None


def _get_deployment_service():
    """Get or create the shared DeploymentService instance."""
    global _deployment_service
    if _deployment_service is None:
        _deployment_service = DeploymentService()
    return _deployment_service


# Default configuration constants
POLL_INTERVAL_DEFAULT = 10  # Default polling interval in seconds for watch mode
POLL_INTERVAL_MIN = 1  # Minimum polling interval (prevents CPU spinning)
PATTERN_DEFAULT = "**/*.jpg"  # Default file pattern for photo matching
JPEG_QUALITY_DEFAULT = 95  # JPEG quality for re-encoding (in lib, referenced here for docs)
LOG_FORMAT = "[%(asctime)s] [%(levelname)s] %(message)s"  # Log message format
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"  # Log timestamp format
FILE_STABILITY_CHECKS = 2  # Number of mtime checks to verify file write completion
FILE_STABILITY_INTERVAL = 0.5  # Seconds between stability checks


def setup_logging(verbose: bool = False) -> logging.Logger:
    """Configure logging for GPS EXIF tagger.

    Args:
        verbose: If True, enable DEBUG level logging

    Returns:
        logging.Logger: Configured logger instance
    """
    # Create logger
    logger = logging.getLogger("gps_exif_tagger")
    logger.setLevel(logging.DEBUG if verbose else logging.INFO)

    # Create console handler (for systemd journal)
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.DEBUG if verbose else logging.INFO)

    # Create formatter
    formatter = logging.Formatter(LOG_FORMAT, datefmt=LOG_DATE_FORMAT)
    handler.setFormatter(formatter)

    # Add handler to logger
    logger.addHandler(handler)

    return logger


def wait_for_file_stability(photo_path: Path, logger: logging.Logger) -> bool:
    """Wait for a file to finish writing by checking mtime stability.

    Polls the file's modification time multiple times to ensure it's
    no longer being written. This is more robust than a fixed sleep()
    for handling slow writes (large files, slow SD cards, network mounts).

    Args:
        photo_path: Path to file to check
        logger: Logger instance for debug output

    Returns:
        bool: True if file is stable, False if file disappeared during check

    Implementation:
        - Checks mtime FILE_STABILITY_CHECKS times (default: 2)
        - Waits FILE_STABILITY_INTERVAL seconds between checks (default: 0.5s)
        - Returns False if file disappears (caught by TOCTOU handler)
        - Total wait: FILE_STABILITY_CHECKS * FILE_STABILITY_INTERVAL

    Example:
        >>> if wait_for_file_stability(photo_path, logger):
        ...     process_photo(photo_path)  # Safe to process
    """
    try:
        # Get initial mtime
        last_mtime = photo_path.stat().st_mtime

        # Check stability FILE_STABILITY_CHECKS times
        for _check_num in range(FILE_STABILITY_CHECKS):
            time.sleep(FILE_STABILITY_INTERVAL)

            # Re-check mtime
            try:
                current_mtime = photo_path.stat().st_mtime
            except FileNotFoundError:
                # File was deleted during stability check
                logger.debug(f"File disappeared during stability check: {photo_path.name}")
                return False

            # If mtime changed, file is still being written
            if current_mtime != last_mtime:
                logger.debug(f"File still being written (mtime changed): {photo_path.name}")
                last_mtime = current_mtime
                # Continue checking (don't reset counter - prevent infinite loop)

        # File mtime stable for all checks
        return True

    except (OSError, FileNotFoundError) as e:
        # File disappeared or is inaccessible
        logger.debug(f"File not accessible during stability check: {e}")
        return False


def process_single_photo(
    photo_path: Path,
    logger: logging.Logger,
    force: bool = False,
    backup: bool = False,
    dry_run: bool = False,
    gps_data: dict | None = None,
) -> dict[str, Any]:
    """Process a single photo for GPS EXIF tagging.

    Args:
        photo_path: Path to photo file
        logger: Logger instance for output
        force: If True, re-tag even if already tagged
        backup: If True, create backup before modifying
        dry_run: If True, don't modify files
        gps_data: Pre-resolved GPS data dict (or None to read from controls.txt)

    Returns:
        dict: Processing result from embed_gps_exif()
    """
    # Check if already tagged (skip if not forcing)
    if not force and is_already_tagged(photo_path):
        logger.debug(f"Skipping {photo_path.name} (already tagged)")
        return {
            "success": False,
            "skipped": True,
            "error": None,
            "gps_embedded": False,
            "original_had_gps": True,
            "backup_path": None,
        }

    # Embed GPS EXIF
    logger.debug(f"Processing {photo_path.name}...")
    result = embed_gps_exif(photo_path, gps_data=gps_data, backup=backup, dry_run=dry_run)

    # Log result
    if result["success"]:
        action = "Would tag" if dry_run else "Tagged"
        logger.info(f"{action} {photo_path.name}")
    elif result["skipped"]:
        logger.warning(f"Skipped {photo_path.name} (no GPS fix)")
    elif result["error"]:
        logger.error(f"Failed to process {photo_path.name}: {result['error']}")

    return result


def batch_process_directory(
    directory: Path,
    logger: logging.Logger,
    pattern: str = "*.jpg",
    force: bool = False,
    backup: bool = False,
    dry_run: bool = False,
    coordinate_sources: tuple[str, ...] = ("deployment", "gps"),
    manual_coords: dict[str, float] | None = None,
) -> dict[str, Any]:
    """Process all photos in directory (batch mode).

    Args:
        directory: Directory to scan for photos
        logger: Logger instance for output
        pattern: Glob pattern for photo files
        force: If True, re-tag already tagged photos
        backup: If True, create backups
        dry_run: If True, don't modify files
        coordinate_sources: Ordered tuple of coordinate source names to try
        manual_coords: Dict with "lat" and "lon" for manual source

    Returns:
        dict: Batch processing statistics:
            - total (int): Total photos found
            - tagged (int): Photos successfully tagged
            - skipped (int): Photos skipped (no GPS or already tagged)
            - errors (int): Photos that failed to process
            - error_list (list): List of (path, error_message) tuples
            - source_counts (dict): Count of photos tagged per source
    """
    # Initialize statistics
    stats = {
        "total": 0,
        "tagged": 0,
        "skipped": 0,
        "errors": 0,
        "error_list": [],
        "source_counts": {},
    }

    # Find all photos matching pattern
    logger.info(f"Scanning {directory} for {pattern} files...")

    # Handle case-insensitive extensions
    photo_files = []
    # Extract extension from pattern (e.g., '*.jpg' -> '.jpg')
    if "." in pattern:
        base_pattern, ext = pattern.rsplit(".", 1)
        # Add uppercase variant of the SAME extension only
        for variant in [pattern, f"{base_pattern}.{ext.upper()}"]:
            photo_files.extend(directory.glob(variant))
    else:
        # No extension in pattern, use as-is
        photo_files.extend(directory.glob(pattern))

    # Remove duplicates while preserving order
    # (dict.fromkeys() maintains insertion order as of Python 3.7+)
    photo_files = list(dict.fromkeys(photo_files))

    # Filter out symlinks (security: prevent directory traversal attacks)
    # Only process regular files within the intended directory
    photo_files = [f for f in photo_files if not f.is_symlink()]

    # Sort after deduplication to maintain consistent chronological order
    photo_files = sorted(photo_files)

    stats["total"] = len(photo_files)
    logger.info(f"Found {stats['total']} photo(s)")

    # Process each photo
    for photo_path in photo_files:
        # Resolve coordinates from the configured source chain
        resolved = resolve_coordinates(
            photo_path,
            sources=coordinate_sources,
            manual_coords=manual_coords,
            deployment_service=_get_deployment_service(),
        )

        if resolved is None:
            logger.warning(
                f"Skipping {photo_path.name} (no coordinates from sources: "
                f"{', '.join(coordinate_sources)})"
            )
            stats["skipped"] += 1
            continue

        source = resolved["source"]
        logger.debug(f"Resolved coordinates for {photo_path.name} from '{source}'")

        result = process_single_photo(
            photo_path, logger, force, backup, dry_run, gps_data=resolved["gps_data"]
        )

        if result["success"]:
            stats["tagged"] += 1
            stats["source_counts"][source] = stats["source_counts"].get(source, 0) + 1
        elif result["skipped"]:
            stats["skipped"] += 1
        elif result["error"]:
            stats["errors"] += 1
            stats["error_list"].append((photo_path, result["error"]))

    # Log summary
    logger.info("Batch processing complete:")
    logger.info(f"  Total: {stats['total']}")
    logger.info(f"  Tagged: {stats['tagged']}")
    logger.info(f"  Skipped: {stats['skipped']}")
    logger.info(f"  Errors: {stats['errors']}")
    if stats["source_counts"]:
        logger.info(f"  Sources: {stats['source_counts']}")

    return stats


def watch_directory(
    directory: Path,
    logger: logging.Logger,
    pattern: str = "*.jpg",
    interval: int = 10,
    backup: bool = False,
    coordinate_sources: tuple[str, ...] = ("deployment", "gps"),
) -> None:
    """Monitor directory and tag new photos (immediate mode).

    Uses polling with mtime tracking (more portable than inotify).

    Args:
        directory: Directory to monitor
        logger: Logger instance for output
        pattern: Glob pattern for photo files
        interval: Polling interval in seconds (must be >= 1)
        backup: If True, create backups
        coordinate_sources: Ordered tuple of coordinate source names to try

    Implementation:
        - Track last modification times of all photos
        - Poll directory every `interval` seconds
        - Process new/modified photos
        - Skip photos already tagged
        - Handle filesystem events gracefully

    Raises:
        ValueError: If interval < 1 (would cause CPU spinning)
    """
    # Validate interval to prevent CPU spinning
    if interval < POLL_INTERVAL_MIN:
        raise ValueError(
            f"Interval must be >= {POLL_INTERVAL_MIN} second (got {interval}). "
            "Use a positive integer to avoid CPU spinning."
        )

    logger.info(f"Starting watch mode on {directory}")
    logger.info(f"Polling interval: {interval}s")
    logger.info(f"Pattern: {pattern}")

    # Track last modification times
    seen_files = {}  # {path: mtime}

    try:
        while True:
            # Find all photos matching pattern (case-insensitive)
            photo_files = []
            if "." in pattern:
                base_pattern, ext = pattern.rsplit(".", 1)
                for variant in [pattern, f"{base_pattern}.{ext.upper()}"]:
                    photo_files.extend(directory.glob(variant))
            else:
                photo_files.extend(directory.glob(pattern))
            photo_files = list(dict.fromkeys(photo_files))

            # Filter out symlinks (security: prevent directory traversal attacks)
            # Only process regular files within the intended directory
            photo_files = [f for f in photo_files if not f.is_symlink()]

            # Check each photo
            for photo_path in photo_files:
                try:
                    # Get modification time
                    mtime = photo_path.stat().st_mtime

                    # Check if this is a new or modified file
                    if photo_path not in seen_files or seen_files[photo_path] != mtime:
                        # Update tracking
                        seen_files[photo_path] = mtime

                        # Wait for file to finish writing (check mtime stability)
                        # More robust than fixed sleep for slow SD cards, network mounts
                        logger.debug(f"Detected new/modified photo: {photo_path.name}")

                        if not wait_for_file_stability(photo_path, logger):
                            # File disappeared or is unstable - skip for now
                            # Will be picked up in next polling cycle if it reappears
                            logger.debug(f"Skipping unstable file: {photo_path.name}")
                            continue

                        # Resolve coordinates from the configured source chain
                        resolved = resolve_coordinates(
                            photo_path,
                            sources=coordinate_sources,
                            deployment_service=_get_deployment_service(),
                        )

                        if resolved is None:
                            logger.warning(
                                f"Skipping {photo_path.name} (no coordinates from sources: "
                                f"{', '.join(coordinate_sources)})"
                            )
                            continue

                        source = resolved["source"]
                        logger.debug(f"Resolved coordinates for {photo_path.name} from '{source}'")

                        # Process the photo (use try-except to handle TOCTOU race condition)
                        # File could still be deleted/moved between stability check and processing
                        try:
                            result = process_single_photo(
                                photo_path,
                                logger,
                                force=False,  # Never force in watch mode
                                backup=backup,
                                dry_run=False,
                                gps_data=resolved["gps_data"],
                            )

                            # Log result
                            if result["success"]:
                                logger.info(f"Tagged {photo_path.name} (source: {source})")
                            elif result["skipped"]:
                                logger.debug(f"Skipped {photo_path.name}")

                        except (FileNotFoundError, OSError) as e:
                            # File was deleted/moved between detection and processing (TOCTOU race)
                            # This is expected behavior in watch mode - file system is concurrent
                            logger.debug(
                                f"Skipping {photo_path.name} (file no longer accessible: {e})"
                            )
                            # Remove from tracking since file is gone
                            if photo_path in seen_files:
                                del seen_files[photo_path]

                except OSError as e:
                    logger.warning(f"Error checking {photo_path}: {e}")

            # Sleep until next poll
            time.sleep(interval)

    except KeyboardInterrupt:
        logger.info("Watch mode stopped by user")
    except Exception as e:
        logger.error(f"Watch mode error: {e}")
        raise


def main():
    """Main entry point for GPS EXIF tagger."""
    parser = argparse.ArgumentParser(
        description="GPS EXIF post-processor for Mothbox photos",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    parser.add_argument(
        "--mode",
        choices=["immediate", "batch"],
        default="batch",
        help="Deployment mode: immediate (watch) or batch (one-time)",
    )
    parser.add_argument(
        "--watch", action="store_true", help="Monitor directory for new files (immediate mode)"
    )
    parser.add_argument(
        "--directory",
        type=Path,
        default=PHOTOS_DIR,
        help=f"Photo directory to process (default: {PHOTOS_DIR})",
    )
    parser.add_argument(
        "--pattern",
        default=PATTERN_DEFAULT,
        help=f"File pattern to match (default: {PATTERN_DEFAULT})",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=POLL_INTERVAL_DEFAULT,
        help=f"Polling interval in seconds for watch mode (default: {POLL_INTERVAL_DEFAULT})",
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Test mode: validate without modifying files"
    )
    parser.add_argument(
        "--backup", action="store_true", help="Create .bak files before modifying photos"
    )
    parser.add_argument(
        "--force", action="store_true", help="Re-tag photos even if already have GPS EXIF"
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")
    parser.add_argument(
        "--coordinate-source",
        default="deployment,gps",
        help="Comma-separated coordinate sources in priority order (default: deployment,gps). "
        "Valid sources: deployment, gps, manual",
    )

    args = parser.parse_args()

    # Parse coordinate sources
    coordinate_sources = tuple(s.strip() for s in args.coordinate_source.split(","))

    # Setup logging
    logger = setup_logging(args.verbose)

    # Log startup
    logger.info("GPS EXIF Tagger starting...")
    logger.info(f"Mode: {args.mode}")
    logger.info(f"Directory: {args.directory}")

    # Check if directory exists
    if not args.directory.exists():
        logger.error(f"Directory does not exist: {args.directory}")
        sys.exit(1)

    # Check if GPS is enabled in hardware config
    try:
        hw_config = get_hardware_config()
        if not hw_config.get("gps_enabled", False):
            logger.warning("GPS is disabled in hardware config (controls.txt)")
            logger.warning("GPS EXIF tagging will skip photos without GPS data")
    except Exception as e:
        logger.warning(f"Could not read hardware config: {e}")

    # Check GPS data availability
    try:
        gps_data = get_gps_data_from_controls()
        if gps_data["has_fix"]:
            logger.info(
                f"GPS fix available: {gps_data['latitude']:.6f}, {gps_data['longitude']:.6f}"
            )
        else:
            logger.warning("No GPS fix available - photos will be skipped")
            if args.mode == "batch" and not args.force:
                logger.info("Run with --force to process anyway, or wait for GPS fix")
    except Exception as e:
        logger.warning(f"Could not read GPS data: {e}")

    # Run appropriate mode
    try:
        if args.mode == "immediate" or args.watch:
            # Watch mode
            watch_directory(
                args.directory,
                logger,
                pattern=args.pattern,
                interval=args.interval,
                backup=args.backup,
                coordinate_sources=coordinate_sources,
            )
        else:
            # Batch mode
            stats = batch_process_directory(
                args.directory,
                logger,
                pattern=args.pattern,
                force=args.force,
                backup=args.backup,
                dry_run=args.dry_run,
                coordinate_sources=coordinate_sources,
            )

            # Exit with error code if errors occurred
            if stats["errors"] > 0:
                sys.exit(1)

    except Exception as e:
        logger.error(f"Fatal error: {e}")
        if args.verbose:
            import traceback

            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
