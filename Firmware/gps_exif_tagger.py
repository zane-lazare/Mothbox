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
from typing import Dict, Any

from mothbox_paths import PHOTOS_DIR, get_hardware_config
from lib.gps_exif_lib import embed_gps_exif, is_already_tagged, get_gps_data_from_controls


def setup_logging(verbose: bool = False) -> logging.Logger:
    """Configure logging for GPS EXIF tagger.

    Args:
        verbose: If True, enable DEBUG level logging

    Returns:
        logging.Logger: Configured logger instance
    """
    # Create logger
    logger = logging.getLogger('gps_exif_tagger')
    logger.setLevel(logging.DEBUG if verbose else logging.INFO)

    # Create console handler (for systemd journal)
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.DEBUG if verbose else logging.INFO)

    # Create formatter
    formatter = logging.Formatter(
        '[%(asctime)s] [%(levelname)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    handler.setFormatter(formatter)

    # Add handler to logger
    logger.addHandler(handler)

    return logger


def process_single_photo(
    photo_path: Path,
    logger: logging.Logger,
    force: bool = False,
    backup: bool = False,
    dry_run: bool = False
) -> Dict[str, Any]:
    """Process a single photo for GPS EXIF tagging.

    Args:
        photo_path: Path to photo file
        logger: Logger instance for output
        force: If True, re-tag even if already tagged
        backup: If True, create backup before modifying
        dry_run: If True, don't modify files

    Returns:
        dict: Processing result from embed_gps_exif()
    """
    # Check if already tagged (skip if not forcing)
    if not force and is_already_tagged(photo_path):
        logger.debug(f"Skipping {photo_path.name} (already tagged)")
        return {
            'success': False,
            'skipped': True,
            'error': None,
            'gps_embedded': False,
            'original_had_gps': True,
            'backup_path': None
        }

    # Embed GPS EXIF
    logger.debug(f"Processing {photo_path.name}...")
    result = embed_gps_exif(photo_path, backup=backup, dry_run=dry_run)

    # Log result
    if result['success']:
        action = "Would tag" if dry_run else "Tagged"
        logger.info(f"{action} {photo_path.name}")
    elif result['skipped']:
        logger.warning(f"Skipped {photo_path.name} (no GPS fix)")
    elif result['error']:
        logger.error(f"Failed to process {photo_path.name}: {result['error']}")

    return result


def batch_process_directory(
    directory: Path,
    logger: logging.Logger,
    pattern: str = "*.jpg",
    force: bool = False,
    backup: bool = False,
    dry_run: bool = False
) -> Dict[str, Any]:
    """Process all photos in directory (batch mode).

    Args:
        directory: Directory to scan for photos
        logger: Logger instance for output
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
    # Initialize statistics
    stats = {
        'total': 0,
        'tagged': 0,
        'skipped': 0,
        'errors': 0,
        'error_list': []
    }

    # Find all photos matching pattern
    logger.info(f"Scanning {directory} for {pattern} files...")

    # Handle case-insensitive extensions
    photo_files = []
    # Extract extension from pattern (e.g., '*.jpg' -> '.jpg')
    if '.' in pattern:
        base_pattern, ext = pattern.rsplit('.', 1)
        # Add uppercase variant of the SAME extension only
        for variant in [pattern, f"{base_pattern}.{ext.upper()}"]:
            photo_files.extend(directory.glob(variant))
    else:
        # No extension in pattern, use as-is
        photo_files.extend(directory.glob(pattern))

    # Remove duplicates while preserving order
    # (dict.fromkeys() maintains insertion order as of Python 3.7+)
    photo_files = list(dict.fromkeys(photo_files))

    # Sort after deduplication to maintain consistent chronological order
    photo_files = sorted(photo_files)

    stats['total'] = len(photo_files)
    logger.info(f"Found {stats['total']} photo(s)")

    # Process each photo
    for photo_path in photo_files:
        result = process_single_photo(photo_path, logger, force, backup, dry_run)

        if result['success']:
            stats['tagged'] += 1
        elif result['skipped']:
            stats['skipped'] += 1
        elif result['error']:
            stats['errors'] += 1
            stats['error_list'].append((photo_path, result['error']))

    # Log summary
    logger.info(f"Batch processing complete:")
    logger.info(f"  Total: {stats['total']}")
    logger.info(f"  Tagged: {stats['tagged']}")
    logger.info(f"  Skipped: {stats['skipped']}")
    logger.info(f"  Errors: {stats['errors']}")

    return stats


def watch_directory(
    directory: Path,
    logger: logging.Logger,
    pattern: str = "*.jpg",
    interval: int = 10,
    backup: bool = False
) -> None:
    """Monitor directory and tag new photos (immediate mode).

    Uses polling with mtime tracking (more portable than inotify).

    Args:
        directory: Directory to monitor
        logger: Logger instance for output
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
    logger.info(f"Starting watch mode on {directory}")
    logger.info(f"Polling interval: {interval}s")
    logger.info(f"Pattern: {pattern}")

    # Track last modification times
    seen_files = {}  # {path: mtime}

    try:
        while True:
            # Find all photos matching pattern (case-insensitive)
            photo_files = []
            for ext in [pattern, pattern.replace('.jpg', '.JPG'), pattern.replace('.jpg', '.jpeg'), pattern.replace('.jpg', '.JPEG')]:
                photo_files.extend(directory.glob(ext))

            # Check each photo
            for photo_path in photo_files:
                try:
                    # Get modification time
                    mtime = photo_path.stat().st_mtime

                    # Check if this is a new or modified file
                    if photo_path not in seen_files or seen_files[photo_path] != mtime:
                        # Update tracking
                        seen_files[photo_path] = mtime

                        # Give the file a moment to finish writing
                        # (in case we caught it mid-write)
                        time.sleep(0.5)

                        # Check file still exists after sleep
                        # (could be deleted/renamed during wait)
                        if not photo_path.exists():
                            logger.debug(f"Skipping {photo_path.name} (file no longer exists)")
                            continue

                        # Process the photo
                        logger.debug(f"Detected new/modified photo: {photo_path.name}")
                        result = process_single_photo(
                            photo_path,
                            logger,
                            force=False,  # Never force in watch mode
                            backup=backup,
                            dry_run=False
                        )

                        # Log result
                        if result['success']:
                            logger.info(f"✓ Tagged {photo_path.name}")
                        elif result['skipped']:
                            logger.debug(f"Skipped {photo_path.name}")

                except (OSError, IOError) as e:
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
        if not hw_config.get('gps_enabled', False):
            logger.warning("GPS is disabled in hardware config (controls.txt)")
            logger.warning("GPS EXIF tagging will skip photos without GPS data")
    except Exception as e:
        logger.warning(f"Could not read hardware config: {e}")

    # Check GPS data availability
    try:
        gps_data = get_gps_data_from_controls()
        if gps_data['has_fix']:
            logger.info(f"GPS fix available: {gps_data['latitude']:.6f}, {gps_data['longitude']:.6f}")
        else:
            logger.warning("No GPS fix available - photos will be skipped")
            if args.mode == 'batch' and not args.force:
                logger.info("Run with --force to process anyway, or wait for GPS fix")
    except Exception as e:
        logger.warning(f"Could not read GPS data: {e}")

    # Run appropriate mode
    try:
        if args.mode == 'immediate' or args.watch:
            # Watch mode
            watch_directory(
                args.directory,
                logger,
                pattern=args.pattern,
                interval=args.interval,
                backup=args.backup
            )
        else:
            # Batch mode
            stats = batch_process_directory(
                args.directory,
                logger,
                pattern=args.pattern,
                force=args.force,
                backup=args.backup,
                dry_run=args.dry_run
            )

            # Exit with error code if errors occurred
            if stats['errors'] > 0:
                sys.exit(1)

    except Exception as e:
        logger.error(f"Fatal error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
