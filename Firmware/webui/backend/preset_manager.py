"""
Preset Manager - Handle camera/preview settings presets

This module provides functionality to:
- Load built-in and user presets
- Create new user presets
- Apply presets to camera/preview settings
- Validate preset data
- Manage preset files
"""

import json
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple


class PresetManager:
    """Manages camera and preview settings presets"""

    def __init__(self, builtin_dir: Path, user_dir: Path):
        """
        Initialize preset manager

        Args:
            builtin_dir: Path to built-in presets directory
            user_dir: Path to user presets directory
        """
        self.builtin_dir = Path(builtin_dir)
        self.user_dir = Path(user_dir)

        # Create user directory if it doesn't exist
        self.user_dir.mkdir(parents=True, exist_ok=True)

    def list_presets(self) -> List[Dict]:
        """
        List all available presets (built-in + user)

        Returns:
            List of preset metadata dicts with keys:
            - name: preset identifier
            - display_name: human-readable name
            - description: preset description
            - category: 'built-in' or 'user'
            - version: preset version
        """
        presets = []

        # Load built-in presets
        if self.builtin_dir.exists():
            for preset_file in sorted(self.builtin_dir.glob('*.json')):
                try:
                    with open(preset_file, 'r') as f:
                        data = json.load(f)

                        # Normalize and validate preset
                        data = self.normalize_preset(data)
                        valid, error_msg = self.validate_preset(data)
                        if not valid:
                            print(f"Warning: Skipping invalid built-in preset {preset_file.name}: {error_msg}")
                            continue

                        presets.append({
                            'name': data.get('name', preset_file.stem),
                            'display_name': data.get('display_name', preset_file.stem),
                            'description': data.get('description', ''),
                            'category': 'built-in',
                            'version': data.get('version', '1.0'),
                            'author': data.get('author', 'system'),
                            'workflow': data.get('workflow', 'both')  # photo, liveview, or both
                        })
                except (json.JSONDecodeError, IOError) as e:
                    print(f"Warning: Could not load built-in preset {preset_file}: {e}")

        # Load user presets
        if self.user_dir.exists():
            for preset_file in sorted(self.user_dir.glob('*.json')):
                try:
                    with open(preset_file, 'r') as f:
                        data = json.load(f)

                        # Normalize and validate preset
                        data = self.normalize_preset(data)
                        valid, error_msg = self.validate_preset(data)
                        if not valid:
                            print(f"Warning: Skipping invalid user preset {preset_file.name}: {error_msg}")
                            continue

                        presets.append({
                            'name': data.get('name', preset_file.stem),
                            'display_name': data.get('display_name', preset_file.stem),
                            'description': data.get('description', ''),
                            'category': 'user',
                            'version': data.get('version', '1.0'),
                            'author': data.get('author', 'user'),
                            'created_at': data.get('created_at', ''),
                            'workflow': data.get('workflow', 'both')  # photo, liveview, or both
                        })
                except (json.JSONDecodeError, IOError) as e:
                    print(f"Warning: Could not load user preset {preset_file}: {e}")

        return presets

    def get_preset(self, name: str) -> Optional[Dict]:
        """
        Get specific preset by name

        Args:
            name: Preset name (without .json extension)

        Returns:
            Preset data dict, or None if not found or invalid
        """
        preset_data = None

        # Try built-in first
        builtin_path = self.builtin_dir / f"{name}.json"
        if builtin_path.exists():
            try:
                with open(builtin_path, 'r') as f:
                    preset_data = json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                print(f"Error loading built-in preset {name}: {e}")
                return None

        # Try user presets if not found in built-in
        if not preset_data:
            user_path = self.user_dir / f"{name}.json"
            if user_path.exists():
                try:
                    with open(user_path, 'r') as f:
                        preset_data = json.load(f)
                except (json.JSONDecodeError, IOError) as e:
                    print(f"Error loading user preset {name}: {e}")
                    return None

        # Normalize and validate the preset before returning
        if preset_data:
            preset_data = self.normalize_preset(preset_data)
            valid, error_msg = self.validate_preset(preset_data)
            if not valid:
                print(f"Error: Invalid preset '{name}': {error_msg}")
                return None
            return preset_data

        return None

    def save_preset(self, name: str, settings: Dict, description: str = '', category: str = 'user', workflow: str = 'both') -> Tuple[bool, str]:
        """
        Save preset to user directory

        Args:
            name: Preset name (alphanumeric + underscores only)
            settings: Dict with 'camera' and/or 'preview' settings
            description: Human-readable description
            category: Should always be 'user' (built-in are read-only)
            workflow: 'photo', 'liveview', or 'both' - which workflow this preset is for

        Returns:
            Tuple of (success: bool, message: str)
        """
        # Validate name (alphanumeric + underscores only)
        if not name or not all(c.isalnum() or c == '_' for c in name):
            return False, "Preset name must contain only letters, numbers, and underscores"

        # Built-in presets cannot be overwritten
        if category == 'built-in':
            return False, "Cannot modify built-in presets"

        # Validate workflow (support 'video' for backward compatibility, normalize to 'liveview')
        if workflow == 'video':
            workflow = 'liveview'  # Normalize deprecated 'video' to 'liveview'

        if workflow not in ['photo', 'liveview', 'both']:
            return False, "Workflow must be 'photo', 'liveview', or 'both'"

        # Build preset data FIRST
        preset_data = {
            'name': name,
            'display_name': name.replace('_', ' ').title(),
            'description': description,
            'version': '1.0',
            'created_at': datetime.utcnow().isoformat() + 'Z',
            'author': 'user',
            'category': 'user',
            'workflow': workflow,
            'settings': settings
        }

        # Normalize and validate the complete preset structure
        preset_data = self.normalize_preset(preset_data)
        valid, error_msg = self.validate_preset(preset_data)
        if not valid:
            return False, error_msg

        # Save to user directory
        try:
            preset_path = self.user_dir / f"{name}.json"
            with open(preset_path, 'w') as f:
                json.dump(preset_data, f, indent=2)
            return True, f"Preset '{name}' saved successfully"
        except IOError as e:
            return False, f"Failed to save preset: {str(e)}"

    def delete_preset(self, name: str) -> Tuple[bool, str]:
        """
        Delete user preset (built-in presets are protected)

        Args:
            name: Preset name to delete

        Returns:
            Tuple of (success: bool, message: str)
        """
        # Check if it's a built-in preset
        builtin_path = self.builtin_dir / f"{name}.json"
        if builtin_path.exists():
            return False, "Cannot delete built-in presets"

        # Try to delete user preset
        user_path = self.user_dir / f"{name}.json"
        if not user_path.exists():
            return False, f"Preset '{name}' not found"

        try:
            user_path.unlink()
            return True, f"Preset '{name}' deleted successfully"
        except IOError as e:
            return False, f"Failed to delete preset: {str(e)}"

    def normalize_preset(self, preset_data: Dict) -> Dict:
        """
        Normalize preset by adding missing fields with defaults

        Args:
            preset_data: Raw preset data

        Returns:
            Normalized preset with all required fields
        """
        normalized = preset_data.copy()

        # Ensure top-level metadata exists
        if 'workflow' not in normalized:
            normalized['workflow'] = 'both'  # Safe default

        if 'version' not in normalized:
            normalized['version'] = '1.0'

        # Ensure settings structure exists
        if 'settings' not in normalized:
            normalized['settings'] = {}

        settings = normalized['settings']

        # Migrate legacy 'preview' key to 'liveview' (backward compatibility)
        if 'preview' in settings and (not settings.get('liveview') or not settings['liveview']):
            print(f"Migrating legacy 'preview' key to 'liveview' for preset '{normalized.get('name', 'unknown')}'")
            settings['liveview'] = settings.pop('preview')

        # Add empty camera settings if missing (for liveview-only presets)
        if 'camera' not in settings and normalized['workflow'] in ['photo', 'both']:
            print(f"Warning: Preset missing camera settings for workflow '{normalized['workflow']}'")
            settings['camera'] = {}

        # Add empty liveview settings if missing (for capture-only presets)
        if 'liveview' not in settings and normalized['workflow'] in ['liveview', 'both']:
            print(f"Warning: Preset missing liveview settings for workflow '{normalized['workflow']}'")
            settings['liveview'] = {}

        return normalized

    def validate_preset(self, preset_data: Dict) -> Tuple[bool, str]:
        """
        Validate preset structure and data types

        Args:
            preset_data: Preset data to validate (should have 'settings' key)

        Returns:
            Tuple of (valid: bool, error_message: str)
        """
        # Check for settings key
        if 'settings' in preset_data:
            settings = preset_data['settings']
        elif 'camera' in preset_data or 'liveview' in preset_data:
            settings = preset_data
        else:
            return False, "Preset must contain 'settings' or 'camera'/'liveview' keys"

        # Settings must have at least camera or liveview
        if 'camera' not in settings and 'liveview' not in settings:
            return False, "Preset must contain 'camera' and/or 'liveview' settings"

        # Camera settings validation (basic type checking)
        if 'camera' in settings:
            if not isinstance(settings['camera'], dict):
                return False, "Camera settings must be a dictionary"

            # Check for common required fields
            camera = settings['camera']
            if camera:  # Only validate if not empty
                # Type checks for common fields
                numeric_fields = ['ExposureTime', 'AnalogueGain', 'Sharpness', 'Brightness', 'Contrast', 'Saturation']
                for field in numeric_fields:
                    if field in camera:
                        try:
                            float(camera[field])
                        except (ValueError, TypeError):
                            return False, f"Camera setting '{field}' must be numeric"

        # Liveview settings validation
        if 'liveview' in settings:
            if not isinstance(settings['liveview'], dict):
                return False, "Liveview settings must be a dictionary"

            # Type checks for liveview settings
            liveview = settings['liveview']
            if liveview:  # Only validate if not empty
                numeric_fields = ['sharpness', 'brightness', 'contrast', 'saturation', 'focus_peaking_intensity']
                for field in numeric_fields:
                    if field in liveview:
                        try:
                            float(liveview[field])
                        except (ValueError, TypeError):
                            return False, f"Liveview setting '{field}' must be numeric"

                # Validate focus peaking boolean
                if 'focus_peaking_enabled' in liveview:
                    if not isinstance(liveview['focus_peaking_enabled'], bool):
                        if isinstance(liveview['focus_peaking_enabled'], str):
                            if liveview['focus_peaking_enabled'].lower() not in ['true', 'false']:
                                return False, "Liveview setting 'focus_peaking_enabled' must be boolean or 'true'/'false' string"
                        else:
                            return False, "Liveview setting 'focus_peaking_enabled' must be boolean"

                # Validate focus peaking color
                if 'focus_peaking_color' in liveview:
                    valid_colors = ['green', 'red', 'yellow', 'cyan', 'magenta']
                    if liveview['focus_peaking_color'] not in valid_colors:
                        return False, f"Liveview setting 'focus_peaking_color' must be one of {valid_colors}"

                # Validate focus peaking algorithm
                if 'focus_peaking_algorithm' in liveview:
                    valid_algorithms = ['laplacian', 'sobel', 'canny']
                    if liveview['focus_peaking_algorithm'] not in valid_algorithms:
                        return False, f"Liveview setting 'focus_peaking_algorithm' must be one of {valid_algorithms}"

        return True, "Preset validation successful"

    def get_preset_count(self) -> Dict[str, int]:
        """
        Get count of presets by category

        Returns:
            Dict with 'built_in', 'user', and 'total' counts
        """
        builtin_count = len(list(self.builtin_dir.glob('*.json'))) if self.builtin_dir.exists() else 0
        user_count = len(list(self.user_dir.glob('*.json'))) if self.user_dir.exists() else 0

        return {
            'built_in': builtin_count,
            'user': user_count,
            'total': builtin_count + user_count
        }
