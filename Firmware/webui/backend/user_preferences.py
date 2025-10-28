"""
User Preferences Manager

Stores user-specific preferences like default presets for photo/video workflows.
Uses a simple JSON file for persistence.
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional
import sys

# Setup path to import mothbox_paths
sys.path.insert(0, str(Path(__file__).parent.parent))
import mothbox_import  # Sets up sys.path for mothbox

from mothbox_paths import USER_PREFERENCES_FILE


# Default preferences structure
DEFAULT_PREFERENCES = {
    "default_capture_preset": None,  # Photo workflow default
    "default_preview_preset": None,  # Video workflow default
    "default_liveview_preset": None,  # Live view workflow default
}


class UserPreferencesManager:
    """Manages user preferences stored in JSON file"""

    def __init__(self, preferences_file: Path = USER_PREFERENCES_FILE):
        """
        Initialize preferences manager

        Args:
            preferences_file: Path to preferences JSON file
        """
        self.preferences_file = Path(preferences_file)
        self._ensure_file_exists()

    def _ensure_file_exists(self):
        """Create preferences file with defaults if it doesn't exist"""
        if not self.preferences_file.exists():
            # Create parent directory if needed
            self.preferences_file.parent.mkdir(parents=True, exist_ok=True)

            # Write default preferences
            try:
                with open(self.preferences_file, 'w') as f:
                    json.dump(DEFAULT_PREFERENCES, f, indent=2)
            except IOError as e:
                print(f"Warning: Could not create preferences file: {e}")

    def get_preferences(self) -> Dict[str, Any]:
        """
        Get all user preferences

        Returns:
            Dict with all preference key-value pairs
        """
        try:
            with open(self.preferences_file, 'r') as f:
                prefs = json.load(f)
                # Merge with defaults to handle new preference keys
                return {**DEFAULT_PREFERENCES, **prefs}
        except (IOError, json.JSONDecodeError) as e:
            print(f"Warning: Could not load preferences, using defaults: {e}")
            return DEFAULT_PREFERENCES.copy()

    def validate_preset_references(self, preset_manager) -> Dict[str, Any]:
        """
        Validate preset references in preferences and remove references to deleted presets

        Args:
            preset_manager: PresetManager instance to check if presets exist

        Returns:
            Dict with validation results:
            {
                'cleaned': bool,
                'removed_references': list of (key, invalid_value) tuples,
                'preferences': updated preferences dict
            }
        """
        prefs = self.get_preferences()
        removed = []
        cleaned = False

        # Get list of available presets
        available_presets = preset_manager.list_presets()
        preset_names = {p['name'] for p in available_presets}

        # Check each preset reference
        for key in ['default_capture_preset', 'default_preview_preset', 'default_liveview_preset']:
            if key in prefs and prefs[key] is not None:
                preset_name = prefs[key]
                if preset_name not in preset_names:
                    # Invalid/deleted preset reference
                    removed.append((key, preset_name))
                    prefs[key] = None
                    cleaned = True
                    print(f"Warning: Removed invalid preset reference: {key}={preset_name} (preset not found)")

        # Save cleaned preferences if any changes were made
        if cleaned:
            try:
                with open(self.preferences_file, 'w') as f:
                    json.dump(prefs, f, indent=2)
            except IOError as e:
                print(f"Error: Could not save cleaned preferences: {e}")

        return {
            'cleaned': cleaned,
            'removed_references': removed,
            'preferences': prefs
        }

    def get_preference(self, key: str) -> Optional[Any]:
        """
        Get specific preference value

        Args:
            key: Preference key

        Returns:
            Preference value, or None if not found
        """
        prefs = self.get_preferences()
        return prefs.get(key)

    def set_preference(self, key: str, value: Any) -> bool:
        """
        Set specific preference value

        Args:
            key: Preference key
            value: Preference value

        Returns:
            True if successful, False otherwise
        """
        # Validate key exists in defaults
        if key not in DEFAULT_PREFERENCES:
            print(f"Warning: Unknown preference key '{key}'")
            return False

        try:
            # Load current preferences
            prefs = self.get_preferences()

            # Update value
            prefs[key] = value

            # Write back to file
            with open(self.preferences_file, 'w') as f:
                json.dump(prefs, f, indent=2)

            return True
        except IOError as e:
            print(f"Error: Could not save preference: {e}")
            return False

    def reset_preferences(self) -> bool:
        """
        Reset all preferences to defaults

        Returns:
            True if successful, False otherwise
        """
        try:
            with open(self.preferences_file, 'w') as f:
                json.dump(DEFAULT_PREFERENCES, f, indent=2)
            return True
        except IOError as e:
            print(f"Error: Could not reset preferences: {e}")
            return False


# Global instance
preferences_manager = UserPreferencesManager()
