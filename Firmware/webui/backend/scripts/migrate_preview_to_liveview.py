#!/usr/bin/env python3
"""
Migration Script: Preview → Live View Terminology

Migrates configuration files and user presets from old "preview/video"
terminology to new "live view/liveview" terminology.

This script is idempotent - safe to run multiple times.

Changes:
1. Renames webui_settings.txt → liveview_settings.txt
2. Updates user presets: workflow "video" → "liveview"
3. Creates backups before any modifications

Usage:
    python3 migrate_preview_to_liveview.py [--dry-run]

Options:
    --dry-run    Show what would be changed without making changes
"""

import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

# Add paths for imports
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))
sys.path.insert(0, str(backend_dir.parent.parent))  # Mothbox root

try:
    import mothbox_import  # noqa: F401 - Sets up sys.path

    from mothbox_paths import CONFIG_DIR, USER_PRESET_DIR
except ImportError:
    # Fallback for development environments
    CONFIG_DIR = backend_dir.parent.parent / "mothbox" / "config"
    USER_PRESET_DIR = CONFIG_DIR / "presets" / "user"
    print("Using fallback paths (mothbox_paths not found)")
    print(f"   CONFIG_DIR: {CONFIG_DIR}")
    print(f"   USER_PRESET_DIR: {USER_PRESET_DIR}")


def migrate_config_file(dry_run=False):
    """Migrate webui_settings.txt → liveview_settings.txt"""
    old_path = CONFIG_DIR / "webui_settings.txt"
    new_path = CONFIG_DIR / "liveview_settings.txt"

    print("\nConfig File Migration:")
    print(f"   Old: {old_path}")
    print(f"   New: {new_path}")

    if new_path.exists():
        print("Already migrated (liveview_settings.txt exists)")
        return True

    if not old_path.exists():
        print("No migration needed (webui_settings.txt doesn't exist)")
        return True

    if dry_run:
        print(f"   [DRY RUN] Would rename: {old_path.name} → {new_path.name}")
        return True

    # Create backup
    backup_path = (
        old_path.parent / f"{old_path.name}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    )
    shutil.copy2(old_path, backup_path)
    print(f"   Backup created: {backup_path.name}")

    # Rename file
    old_path.rename(new_path)
    print(f"Renamed: {old_path.name} → {new_path.name}")

    return True


def migrate_preset_workflows(dry_run=False):
    """Update user preset files: workflow 'video' → 'liveview' and settings.preview → settings.liveview"""
    print("\nUser Preset Migration:")
    print(f"   Directory: {USER_PRESET_DIR}")

    if not USER_PRESET_DIR.exists():
        print("No user presets directory found")
        return True

    preset_files = list(USER_PRESET_DIR.glob("*.json"))

    if not preset_files:
        print("No user preset files found")
        return True

    print(f"   Found {len(preset_files)} preset file(s)")

    migrated_count = 0
    skipped_count = 0

    for preset_file in preset_files:
        try:
            # Read preset
            with open(preset_file) as f:
                preset_data = json.load(f)

            needs_migration = False
            changes = []

            # Check workflow field migration
            workflow = preset_data.get("workflow", "")
            if workflow == "video":
                needs_migration = True
                changes.append("workflow 'video' → 'liveview'")
                if not dry_run:
                    preset_data["workflow"] = "liveview"

            # Check settings.preview → settings.liveview migration
            settings = preset_data.get("settings", {})
            if "preview" in settings:
                needs_migration = True
                changes.append("settings.preview → settings.liveview")
                if not dry_run:
                    preset_data["settings"]["liveview"] = preset_data["settings"].pop("preview")

            if needs_migration:
                if dry_run:
                    print(f"   [DRY RUN] Would update {preset_file.name}: {', '.join(changes)}")
                    migrated_count += 1
                else:
                    # Create backup
                    backup_path = (
                        preset_file.parent
                        / f"{preset_file.stem}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                    )
                    shutil.copy2(preset_file, backup_path)

                    # Write updated preset
                    with open(preset_file, "w") as f:
                        json.dump(preset_data, f, indent=2)

                    print(f"Updated {preset_file.name}: {', '.join(changes)}")
                    print(f"      Backup: {backup_path.name}")
                    migrated_count += 1
            else:
                # Already migrated or no migration needed
                skipped_count += 1

        except Exception as e:
            print(f"   Error processing {preset_file.name}: {e}")
            continue

    print(f"\n   Summary: {migrated_count} migrated, {skipped_count} skipped")
    return True


def main():
    """Run all migrations"""
    dry_run = "--dry-run" in sys.argv

    print("=" * 60)
    print("Migration: Preview → Live View Terminology")
    print("=" * 60)

    if dry_run:
        print("\nDRY RUN MODE - No changes will be made\n")

    # Run migrations
    success = True
    success &= migrate_config_file(dry_run)
    success &= migrate_preset_workflows(dry_run)

    # Summary
    print("\n" + "=" * 60)
    if success:
        if dry_run:
            print("Dry run completed - review changes above")
            print("\nTo apply changes, run without --dry-run:")
            print(f"  python3 {Path(__file__).name}")
        else:
            print("Migration completed successfully!")
            print("\nBackup files created for safety.")
            print("You can delete .backup_* files once you verify everything works.")
    else:
        print("Migration completed with warnings")
        return 1

    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
