# OldScripts - Deprecated Code

This directory contains deprecated/archived scripts that are no longer actively used in production.

## Important Note

**These files have NOT been migrated** to use dynamic GPIO configuration from `controls.txt`. They retain hardcoded GPIO pin values.

If you need to use any of these scripts, either:

1. **Update them to use dynamic configuration** following the pattern used in the parent directory scripts:
   ```python
   from pathlib import Path
   import sys
   sys.path.insert(0, str(Path(__file__).parent.parent.parent))
   from mothbox_paths import get_gpio_pins

   pins = get_gpio_pins()
   Relay_Ch1 = pins['Relay_Ch1']
   Relay_Ch2 = pins['Relay_Ch2']
   Relay_Ch3 = pins['Relay_Ch3']
   ```

2. **Ensure the hardcoded pins match your hardware configuration** in `controls.txt`

## Migration Status

- ✅ Active scripts in parent directory: **Migrated** (use dynamic GPIO configuration)
- ❌ Scripts in this OldScripts directory: **Not migrated** (use hardcoded pins)

## Reference

See parent directory scripts for examples of the current GPIO configuration pattern, or refer to:
- `mothbox_paths.py` - Configuration loading functions
- `install_mothbox.sh` - Interactive hardware configuration setup
- PR #12 - Comprehensive hardware module configuration implementation
