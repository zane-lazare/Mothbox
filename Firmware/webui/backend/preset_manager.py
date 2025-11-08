"""
Preset Manager - Handle camera/preview settings presets

This module provides functionality to:
- Load built-in and user presets
- Create new user presets
- Apply presets to camera/preview settings
- Validate preset data
- Manage preset files
"""

import fcntl
import json
import logging
import re
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any

# Import validation schemas for type normalization
from utils import ALLOWED_CAMERA_SETTINGS, ALLOWED_LIVEVIEW_SETTINGS

# Setup logging
logger = logging.getLogger(__name__)


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

        # Cache for type derivation results to avoid re-analyzing validators
        self._type_cache: dict[tuple[str, str], type] = {}

    def _derive_type_from_validator(
        self, key: str, validator: Callable, setting_type: str
    ) -> type | None:
        """
        Derive the expected type from a validation lambda function.

        Analyzes validation function source code patterns to determine expected type:
        - float(v) with decimal range → float
        - int(v) in [...] → int
        - .lower() in ['true', 'false'] → bool
        - .lower() in [string list] → str

        Args:
            key: Setting name
            validator: Validation lambda function
            setting_type: 'camera' or 'liveview' (for cache key)

        Returns:
            Python type (int, float, bool, str) or None if unable to determine
        """
        # Check cache first
        cache_key = (setting_type, key)
        if cache_key in self._type_cache:
            return self._type_cache[cache_key]

        try:
            # Get the source code of the validator (works for lambdas and functions)
            import inspect

            # Check if it's a lambda or a function
            validator_name = getattr(validator, "__name__", None)

            # Handle special function names that indicate type
            if validator_name:
                if "int_enum" in validator_name:
                    derived_type = int
                    self._type_cache[cache_key] = derived_type
                    return derived_type
                elif "exposure_time" in validator_name:
                    # ExposureTime validation function returns int
                    derived_type = int
                    self._type_cache[cache_key] = derived_type
                    return derived_type

            source = inspect.getsource(validator).strip()

            # Pattern matching to infer type
            derived_type = None

            # Check for calls to validation helper functions
            if "_validate_int_enum" in source or "_validate_exposure_time" in source:
                derived_type = int

            # Boolean: str(v).lower() in ['true', 'false']
            elif re.search(r"\.lower\(\)\s+in\s+\[.*['\"]true['\"].*['\"]false['\"]", source):
                derived_type = bool

            # String enum: str(v).lower() in ['option1', 'option2', ...]
            # (but NOT the boolean pattern above)
            elif re.search(r"str\(v\)\.lower\(\)", source) and not re.search(
                r"['\"]true['\"]", source
            ):
                derived_type = str

            # Float: float(v) with decimal literals in range checks
            elif re.search(r"float\(v\)", source) and re.search(r"\d+\.\d+", source):
                derived_type = float

            # Integer: int(v) in [...] or range checks with integers only
            elif re.search(r"int\(v\)", source) or re.search(r"isinstance\(v,\s*int\)", source):
                derived_type = int
            elif re.search(r"isinstance\(v,\s*float\)", source):
                derived_type = float
            elif re.search(r"isinstance\(v,\s*bool\)", source):
                derived_type = bool

            # Cache the result
            if derived_type:
                self._type_cache[cache_key] = derived_type

            return derived_type

        except (OSError, TypeError) as e:
            # inspect.getsource() can fail for built-in functions or C code
            logger.debug(f"Could not derive type for {setting_type} setting '{key}': {e}")
            return None

    def _normalize_setting_types(self, settings: dict[str, Any]) -> dict[str, Any]:
        """
        Normalize setting value types from strings to their proper types.

        This ensures consistent JSON serialization regardless of data source:
        - Numbers stored as strings (from CSV/TXT files) → int/float
        - Booleans stored as strings ("true", "True", "false") → bool
        - Actual string values remain strings

        Args:
            settings: Dict with 'camera' and/or 'liveview' settings

        Returns:
            Settings dict with normalized types
        """
        normalized = {}

        # Normalize camera settings
        if "camera" in settings:
            normalized["camera"] = {}
            for key, value in settings["camera"].items():
                normalized["camera"][key] = self._convert_value_type(key, value, "camera")

        # Normalize liveview settings
        if "liveview" in settings:
            normalized["liveview"] = {}
            for key, value in settings["liveview"].items():
                normalized["liveview"][key] = self._convert_value_type(key, value, "liveview")

        return normalized

    def _convert_value_type(
        self, key: str, value: Any, setting_type: str
    ) -> int | float | bool | str:
        """
        Convert a single setting value from string to its proper type using validation schemas.

        This method derives the expected type from the validation schema (ALLOWED_CAMERA_SETTINGS
        or ALLOWED_LIVEVIEW_SETTINGS) rather than using hardcoded type lists. This ensures
        consistency between validation and type normalization.

        Args:
            key: Setting name (e.g., 'ExposureTime', 'sharpness')
            value: Raw value (possibly string)
            setting_type: 'camera' or 'liveview'

        Returns:
            Value with proper type, or original value if conversion fails
        """
        # If already non-string type, return as-is (already correct type)
        if not isinstance(value, str):
            return value

        # Get the appropriate validation schema
        schema = ALLOWED_CAMERA_SETTINGS if setting_type == "camera" else ALLOWED_LIVEVIEW_SETTINGS

        # Check if key exists in schema
        if key in schema:
            validator = schema[key]

            # Derive type from validator function
            expected_type = self._derive_type_from_validator(key, validator, setting_type)

            if expected_type is bool:
                # Boolean conversion: 'true', '1', 'yes' → True
                return value.lower() in ["true", "1", "yes"]

            elif expected_type is int:
                # Integer conversion
                try:
                    return int(value)
                except (ValueError, TypeError) as e:
                    logger.warning(
                        f"Failed to convert {setting_type} setting '{key}' value '{value}' to int: {e}. "
                        f"Keeping as string."
                    )
                    return value

            elif expected_type is float:
                # Float conversion
                try:
                    return float(value)
                except (ValueError, TypeError) as e:
                    logger.warning(
                        f"Failed to convert {setting_type} setting '{key}' value '{value}' to float: {e}. "
                        f"Keeping as string."
                    )
                    return value

            elif expected_type is str:
                # String enum - lowercase for consistency
                return value.lower() if value else value

            else:
                # Could not derive type from validator - fall back to inference
                logger.debug(
                    f"Could not derive type for {setting_type} setting '{key}' from validator. "
                    f"Using type inference."
                )
                return self._infer_type(value)
        else:
            # Unknown setting not in schema - use type inference
            logger.debug(
                f"{setting_type.capitalize()} setting '{key}' not found in validation schema. "
                f"Using type inference."
            )
            return self._infer_type(value)

        return value

    def _infer_type(self, value: str) -> int | float | bool | str:
        """
        Infer the proper type for a string value when schema lookup fails.

        This method is ONLY used as a fallback when:
        1. A setting is not found in ALLOWED_CAMERA_SETTINGS or ALLOWED_LIVEVIEW_SETTINGS
        2. Type derivation from the validator function fails

        For known settings, type conversion is always schema-based via _convert_value_type().

        Type inference hierarchy:
        1. Boolean: 'true', 'false', 'yes', 'no', '0', '1' → bool
           - '0' → False, '1' → True (common in camera control systems)
           - Schema-based conversion distinguishes boolean vs integer fields
        2. Integer: No decimal point → int (e.g., '2', '42', '100')
        3. Float: Contains decimal point → float (e.g., '3.14', '1.0')
        4. String: Everything else → str (e.g., 'green', 'custom')

        Args:
            value: String value to convert

        Returns:
            Value with inferred type

        Examples:
            >>> _infer_type("true")
            True
            >>> _infer_type("1")
            True  # '1' is treated as boolean True
            >>> _infer_type("0")
            False  # '0' is treated as boolean False
            >>> _infer_type("42")
            42
            >>> _infer_type("3.14")
            3.14
            >>> _infer_type("hello")
            'hello'
        """
        if not isinstance(value, str):
            return value

        # Try boolean - explicit boolean strings AND numeric '0'/'1'
        # '0' → False, '1' → True (common in camera control systems)
        # '2' and higher are treated as integers
        if value.lower() in ["true", "false", "yes", "no"]:
            return value.lower() in ["true", "yes"]

        # Special case: '0' and '1' are treated as booleans
        if value == "0":
            return False
        if value == "1":
            return True

        # Try integer (no decimal point)
        # Note: '2' and higher will be parsed here as integers
        try:
            if "." not in value:
                return int(value)
        except (ValueError, TypeError):
            pass

        # Try float (has decimal point or scientific notation)
        try:
            return float(value)
        except (ValueError, TypeError):
            pass

        # Keep as string (for text values, enums, etc.)
        return value

    def list_presets(self) -> list[dict]:
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
            for preset_file in sorted(self.builtin_dir.glob("*.json")):
                try:
                    with open(preset_file) as f:
                        data = json.load(f)

                        # Normalize and validate preset
                        data = self.normalize_preset(data)

                        # Normalize setting types (convert strings to proper int/float/bool)
                        if "settings" in data:
                            data["settings"] = self._normalize_setting_types(data["settings"])

                        valid, error_msg = self.validate_preset(data)
                        if not valid:
                            print(
                                f"Warning: Skipping invalid built-in preset {preset_file.name}: {error_msg}"
                            )
                            continue

                        presets.append(
                            {
                                "name": data.get("name", preset_file.stem),
                                "display_name": data.get("display_name", preset_file.stem),
                                "description": data.get("description", ""),
                                "category": "built-in",
                                "version": data.get("version", "1.0"),
                                "author": data.get("author", "system"),
                                "workflow": data.get(
                                    "workflow", "both"
                                ),  # photo, liveview, or both
                            }
                        )
                except (OSError, json.JSONDecodeError) as e:
                    print(f"Warning: Could not load built-in preset {preset_file}: {e}")

        # Load user presets
        if self.user_dir.exists():
            for preset_file in sorted(self.user_dir.glob("*.json")):
                try:
                    with open(preset_file) as f:
                        data = json.load(f)

                        # Normalize and validate preset
                        data = self.normalize_preset(data)

                        # Normalize setting types (convert strings to proper int/float/bool)
                        if "settings" in data:
                            data["settings"] = self._normalize_setting_types(data["settings"])

                        valid, error_msg = self.validate_preset(data)
                        if not valid:
                            print(
                                f"Warning: Skipping invalid user preset {preset_file.name}: {error_msg}"
                            )
                            continue

                        presets.append(
                            {
                                "name": data.get("name", preset_file.stem),
                                "display_name": data.get("display_name", preset_file.stem),
                                "description": data.get("description", ""),
                                "category": "user",
                                "version": data.get("version", "1.0"),
                                "author": data.get("author", "user"),
                                "created_at": data.get("created_at", ""),
                                "workflow": data.get(
                                    "workflow", "both"
                                ),  # photo, liveview, or both
                            }
                        )
                except (OSError, json.JSONDecodeError) as e:
                    print(f"Warning: Could not load user preset {preset_file}: {e}")

        return presets

    def get_preset(self, name: str) -> dict | None:
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
                with open(builtin_path) as f:
                    preset_data = json.load(f)
            except (OSError, json.JSONDecodeError) as e:
                print(f"Error loading built-in preset {name}: {e}")
                return None

        # Try user presets if not found in built-in
        if not preset_data:
            user_path = self.user_dir / f"{name}.json"
            if user_path.exists():
                try:
                    with open(user_path) as f:
                        preset_data = json.load(f)
                except (OSError, json.JSONDecodeError) as e:
                    print(f"Error loading user preset {name}: {e}")
                    return None

        # Normalize and validate the preset before returning
        if preset_data:
            preset_data = self.normalize_preset(preset_data)

            # Normalize setting types (convert strings to proper int/float/bool)
            # This handles legacy presets and manually edited files
            if "settings" in preset_data:
                preset_data["settings"] = self._normalize_setting_types(preset_data["settings"])

            valid, error_msg = self.validate_preset(preset_data)
            if not valid:
                print(f"Error: Invalid preset '{name}': {error_msg}")
                return None
            return preset_data

        return None

    def save_preset(
        self,
        name: str,
        settings: dict,
        description: str = "",
        category: str = "user",
        workflow: str = "both",
    ) -> tuple[bool, str]:
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
        if not name or not all(c.isalnum() or c == "_" for c in name):
            return False, "Preset name must contain only letters, numbers, and underscores"

        # Built-in presets cannot be overwritten
        if category == "built-in":
            return False, "Cannot modify built-in presets"

        # Validate workflow (support 'video' for backward compatibility, normalize to 'liveview')
        if workflow == "video":
            workflow = "liveview"  # Normalize deprecated 'video' to 'liveview'

        if workflow not in ["photo", "liveview", "both"]:
            return False, "Workflow must be 'photo', 'liveview', or 'both'"

        # Normalize setting types FIRST (convert strings to proper types)
        normalized_settings = self._normalize_setting_types(settings)

        # Build preset data
        preset_data = {
            "name": name,
            "display_name": name.replace("_", " ").title(),
            "description": description,
            "version": "1.0",
            "created_at": datetime.utcnow().isoformat() + "Z",
            "author": "user",
            "category": "user",
            "workflow": workflow,
            "settings": normalized_settings,
        }

        # Normalize and validate the complete preset structure
        preset_data = self.normalize_preset(preset_data)
        valid, error_msg = self.validate_preset(preset_data)
        if not valid:
            return False, error_msg

        # Save to user directory
        try:
            preset_path = self.user_dir / f"{name}.json"
            # Use file locking to prevent race conditions during concurrent writes
            # (e.g., if multiple API requests try to save presets simultaneously)
            with open(preset_path, "w") as f:
                try:
                    # Acquire exclusive lock (blocks until lock is available)
                    fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                    json.dump(preset_data, f, indent=2)
                    f.flush()
                finally:
                    # Release lock (automatically released when file closes, but explicit is better)
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)
            return True, f"Preset '{name}' saved successfully"
        except OSError as e:
            return False, f"Failed to save preset: {str(e)}"

    def delete_preset(self, name: str) -> tuple[bool, str]:
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
        except OSError as e:
            return False, f"Failed to delete preset: {str(e)}"

    def normalize_preset(self, preset_data: dict) -> dict:
        """
        Normalize preset by adding missing fields with defaults

        Args:
            preset_data: Raw preset data

        Returns:
            Normalized preset with all required fields
        """
        normalized = preset_data.copy()

        # Ensure top-level metadata exists
        if "workflow" not in normalized:
            normalized["workflow"] = "both"  # Safe default

        if "version" not in normalized:
            normalized["version"] = "1.0"

        # Ensure settings structure exists
        if "settings" not in normalized:
            normalized["settings"] = {}

        settings = normalized["settings"]

        # Migrate legacy 'preview' key to 'liveview' (backward compatibility)
        if "preview" in settings and (not settings.get("liveview") or not settings["liveview"]):
            print(
                f"Migrating legacy 'preview' key to 'liveview' for preset '{normalized.get('name', 'unknown')}'"
            )
            settings["liveview"] = settings.pop("preview")

        # Add empty camera settings if missing (for liveview-only presets)
        if "camera" not in settings and normalized["workflow"] in ["photo", "both"]:
            print(
                f"Warning: Preset missing camera settings for workflow '{normalized['workflow']}'"
            )
            settings["camera"] = {}

        # Add empty liveview settings if missing (for capture-only presets)
        if "liveview" not in settings and normalized["workflow"] in ["liveview", "both"]:
            print(
                f"Warning: Preset missing liveview settings for workflow '{normalized['workflow']}'"
            )
            settings["liveview"] = {}

        return normalized

    def validate_preset(self, preset_data: dict) -> tuple[bool, str]:
        """
        Validate preset structure and data types

        Args:
            preset_data: Preset data to validate (should have 'settings' key)

        Returns:
            Tuple of (valid: bool, error_message: str)
        """
        # Check for settings key
        if "settings" in preset_data:
            settings = preset_data["settings"]
        elif "camera" in preset_data or "liveview" in preset_data:
            settings = preset_data
        else:
            return (
                False,
                "Preset must contain 'settings' or 'camera'/'liveview' keys. If this is a legacy preset, try re-saving it from the Settings page.",
            )

        # Settings must have at least camera or liveview
        if "camera" not in settings and "liveview" not in settings:
            return (
                False,
                "Preset must contain 'camera' and/or 'liveview' settings. This preset may be corrupted or from an incompatible version.",
            )

        # Camera settings validation (basic type checking)
        if "camera" in settings:
            if not isinstance(settings["camera"], dict):
                return (
                    False,
                    f"Camera settings must be a dictionary (found {type(settings['camera']).__name__}). This preset may be corrupted.",
                )

            # Check for common required fields
            camera = settings["camera"]
            if camera:  # Only validate if not empty
                # Type checks for common fields
                numeric_fields = [
                    "ExposureTime",
                    "AnalogueGain",
                    "Sharpness",
                    "Brightness",
                    "Contrast",
                    "Saturation",
                ]
                for field in numeric_fields:
                    if field in camera:
                        try:
                            float(camera[field])
                        except (ValueError, TypeError):
                            return (
                                False,
                                f"Camera setting '{field}' has invalid value '{camera[field]}' (must be numeric). If this is a legacy preset, try re-saving it.",
                            )

        # Liveview settings validation
        if "liveview" in settings:
            if not isinstance(settings["liveview"], dict):
                return (
                    False,
                    f"Liveview settings must be a dictionary (found {type(settings['liveview']).__name__}). This preset may be corrupted.",
                )

            # Type checks for liveview settings
            liveview = settings["liveview"]
            if liveview:  # Only validate if not empty
                numeric_fields = [
                    "sharpness",
                    "brightness",
                    "contrast",
                    "saturation",
                    "focus_peaking_intensity",
                ]
                for field in numeric_fields:
                    if field in liveview:
                        try:
                            float(liveview[field])
                        except (ValueError, TypeError):
                            return (
                                False,
                                f"Liveview setting '{field}' has invalid value '{liveview[field]}' (must be numeric). If this is a legacy preset, try re-saving it.",
                            )

                # Validate focus peaking boolean
                if "focus_peaking_enabled" in liveview:
                    value = liveview["focus_peaking_enabled"]

                    # Accept boolean values
                    if isinstance(value, bool):
                        pass  # Valid
                    # Accept "true"/"false" strings for legacy presets
                    elif isinstance(value, str) and value.lower() in ["true", "false"]:
                        pass  # Valid legacy format
                    # Reject invalid strings
                    elif isinstance(value, str):
                        return (
                            False,
                            "Liveview setting 'focus_peaking_enabled' must be boolean or 'true'/'false' string",
                        )
                    # Reject non-boolean, non-string types
                    else:
                        return False, "Liveview setting 'focus_peaking_enabled' must be boolean"

                # Validate focus peaking colour
                if "focus_peaking_colour" in liveview:
                    valid_colors = ["green", "red", "yellow", "cyan", "magenta"]
                    if liveview["focus_peaking_colour"] not in valid_colors:
                        return (
                            False,
                            f"Liveview setting 'focus_peaking_colour' must be one of {valid_colors}",
                        )

                # Validate focus peaking algorithm
                if "focus_peaking_algorithm" in liveview:
                    valid_algorithms = ["laplacian", "sobel", "canny"]
                    if liveview["focus_peaking_algorithm"] not in valid_algorithms:
                        return (
                            False,
                            f"Liveview setting 'focus_peaking_algorithm' must be one of {valid_algorithms}",
                        )

        return True, "Preset validation successful"

    def get_preset_count(self) -> dict[str, int]:
        """
        Get count of presets by category

        Returns:
            Dict with 'built_in', 'user', and 'total' counts
        """
        builtin_count = (
            len(list(self.builtin_dir.glob("*.json"))) if self.builtin_dir.exists() else 0
        )
        user_count = len(list(self.user_dir.glob("*.json"))) if self.user_dir.exists() else 0

        return {"built_in": builtin_count, "user": user_count, "total": builtin_count + user_count}
