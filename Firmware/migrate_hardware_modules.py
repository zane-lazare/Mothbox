#!/usr/bin/env python3
"""
Script to migrate hardware module usage in Mothbox firmware files.
This script adds hardware configuration support to INA260, GPS, and other modules.
"""

import re
from pathlib import Path

def migrate_update_display_ina260(filepath):
    """Migrate UpdateDisplay.py files to use configurable INA260"""
    print(f"Migrating {filepath}...")

    with open(filepath, 'r') as f:
        content = f.read()

    # Add hardware config import after existing mothbox_paths import
    if 'from mothbox_paths import' in content and 'get_hardware_config' not in content:
        content = content.replace(
            'from mothbox_paths import CONTROLS_FILE, MOTHBOX_HOME, get_script_path',
            'from mothbox_paths import CONTROLS_FILE, MOTHBOX_HOME, get_script_path, get_hardware_config'
        )

    # Add hardware config loading after control values are loaded
    if 'control_values = get_control_values(str(CONTROLS_FILE))' in content and 'hw_config = get_hardware_config()' not in content:
        content = content.replace(
            'control_values = get_control_values(str(CONTROLS_FILE))',
            'control_values = get_control_values(str(CONTROLS_FILE))\nhw_config = get_hardware_config()'
        )

    # Wrap INA260 initialization in enable check
    ina260_init_pattern = r'(\s+)(i2c = board\.I2C\(\).*?\n\s+.*?ina260 = adafruit_ina260\.INA260\(i2c\))'

    def replace_ina260_init(match):
        indent = match.group(1)
        init_code = match.group(2)
        return f"""{indent}# Initialize INA260 if enabled
{indent}if hw_config['ina260_enabled']:
{indent}    try:
{indent}        {init_code.strip()}
{indent}        voltage = ina260.voltage
{indent}    except (OSError, ValueError):
{indent}        voltage = 0.0
{indent}        print("INA260 sensor not connected")
{indent}else:
{indent}    voltage = 0.0"""

    content = re.sub(ina260_init_pattern, replace_ina260_init, content, flags=re.DOTALL)

    # Update INA260 constructor to use configurable address
    content = content.replace(
        'adafruit_ina260.INA260(i2c)',
        'adafruit_ina260.INA260(i2c, address=hw_config["ina260_address"])'
    )

    with open(filepath, 'w') as f:
        f.write(content)

    print(f"✓ Migrated {filepath}")

def validate_python_syntax(filepath):
    """Validate Python file syntax"""
    import ast
    try:
        with open(filepath, 'r') as f:
            ast.parse(f.read())
        return True
    except SyntaxError as e:
        print(f"✗ Syntax error in {filepath}: {e}")
        return False

if __name__ == "__main__":
    # Get base directory
    base_dir = Path(__file__).parent

    # Files to migrate
    files_to_migrate = [
        base_dir / "4.x/UpdateDisplay.py",
        base_dir / "5.x/UpdateDisplay.py",
    ]

    print("Starting hardware module migration...")
    print("=" * 60)

    for filepath in files_to_migrate:
        if filepath.exists():
            migrate_update_display_ina260(filepath)
            if validate_python_syntax(filepath):
                print(f"✓ Validated {filepath}")
            else:
                print(f"✗ Validation failed for {filepath}")
        else:
            print(f"⊗ File not found: {filepath}")

    print("=" * 60)
    print("Migration complete!")
