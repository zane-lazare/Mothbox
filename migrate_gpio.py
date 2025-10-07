#!/usr/bin/env python3
"""
GPIO Pin Migration Script

Migrates firmware scripts from hardcoded GPIO pins to dynamic configuration.
"""

import re
from pathlib import Path

# Files to migrate
FILES_4X = [
    "Firmware/4.x/scripts/TakePhoto_HDR.py",
    "Firmware/4.x/scripts/TakePhoto_AutoExposure.py",
    "Firmware/4.x/scripts/TakePhoto_noAuto.py",
    "Firmware/4.x/scripts/TakePhoto_Stereo_HDR.py",
    "Firmware/4.x/scripts/TakePhoto_uniqueAutoID.py",
    "Firmware/4.x/scripts/TakePhoto16mp.py",
    "Firmware/4.x/scripts/TakePhotoHDR_Fast_WithEXIF.py",
    "Firmware/4.x/scripts/TakeSinglePhoto with flash.py",
    "Firmware/4.x/scripts/Flash_On.py",
    "Firmware/4.x/scripts/Flash_Off.py",
    "Firmware/4.x/scripts/FlashOn_ManPhoto_FlashOff.py",
    "Firmware/4.x/scripts/PlowmanAutofocus.py",
    "Firmware/4.x/scripts/CheckFocus.py",
    "Firmware/4.x/scripts/Full_Test_Relay_Photo_Logging_Shutdown.py",
]

FILES_5X = [
    "Firmware/5.x/scripts/TakePhoto_HDR.py",
    "Firmware/5.x/scripts/TakePhoto_AutoExposure.py",
    "Firmware/5.x/scripts/TakePhoto_noAuto.py",
    "Firmware/5.x/scripts/TakePhoto_Stereo_HDR.py",
    "Firmware/5.x/scripts/TakePhoto_uniqueAutoID.py",
    "Firmware/5.x/scripts/TakePhoto16mp.py",
    "Firmware/5.x/scripts/TakePhotoHDR_Fast_WithEXIF.py",
    "Firmware/5.x/scripts/TakeSinglePhoto with flash.py",
    "Firmware/5.x/scripts/Flash_On.py",
    "Firmware/5.x/scripts/Flash_Off.py",
    "Firmware/5.x/scripts/FlashOn_ManPhoto_FlashOff.py",
    "Firmware/5.x/scripts/PlowmanAutofocus.py",
    "Firmware/5.x/scripts/CheckFocus.py",
    "Firmware/5.x/scripts/Full_Test_Relay_Photo_Logging_Shutdown.py",
]

# Pattern to match GPIO pin assignments
GPIO_PATTERN = re.compile(
    r'^(Relay_Ch1\s*=\s*\d+\s*\n'
    r'Relay_Ch2\s*=\s*\d+\s*\n'
    r'Relay_Ch3\s*=\s*\d+)',
    re.MULTILINE
)

# Replacement text for scripts in scripts/ subdirectory
REPLACEMENT_SCRIPTS = """# Load GPIO pins from configuration
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from mothbox_paths import get_gpio_pins

pins = get_gpio_pins()
Relay_Ch1 = pins['Relay_Ch1']
Relay_Ch2 = pins['Relay_Ch2']
Relay_Ch3 = pins['Relay_Ch3']"""


def migrate_file(filepath):
    """Migrate a single file to use dynamic GPIO configuration."""
    path = Path(filepath)

    if not path.exists():
        print(f"❌ File not found: {filepath}")
        return False

    # Read file content
    content = path.read_text()

    # Check if already migrated
    if 'get_gpio_pins()' in content:
        print(f"⏭️  Already migrated: {filepath}")
        return True

    # Find GPIO pin assignments
    match = GPIO_PATTERN.search(content)
    if not match:
        print(f"⚠️  No GPIO pattern found: {filepath}")
        return False

    # Replace with dynamic loading
    new_content = GPIO_PATTERN.sub(REPLACEMENT_SCRIPTS, content)

    # Write back
    path.write_text(new_content)
    print(f"✅ Migrated: {filepath}")
    return True


def main():
    """Main migration function."""
    print("=" * 70)
    print("GPIO Pin Configuration Migration")
    print("=" * 70)
    print()

    all_files = FILES_4X + FILES_5X
    total = len(all_files)
    success = 0
    skipped = 0
    failed = 0

    print(f"Migrating {total} files...")
    print()

    for filepath in all_files:
        result = migrate_file(filepath)
        if result:
            if 'Already migrated' in str(result):
                skipped += 1
            else:
                success += 1
        else:
            failed += 1

    print()
    print("=" * 70)
    print("Migration Summary")
    print("=" * 70)
    print(f"Total files: {total}")
    print(f"✅ Successfully migrated: {success}")
    print(f"⏭️  Already migrated: {skipped}")
    print(f"❌ Failed: {failed}")
    print()

    if failed > 0:
        print("⚠️  Some files failed to migrate. Please review manually.")
        return 1

    print("🎉 Migration complete!")
    return 0


if __name__ == "__main__":
    exit(main())
