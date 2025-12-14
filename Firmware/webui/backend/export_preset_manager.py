"""
Export Preset Manager - Handle export settings presets.

This module provides functionality to:
- Load built-in and user export presets
- Create new user presets
- Apply presets to export job creation
- Validate preset data
- Manage preset files with file locking

Author: Mothbox Team
Date: 2024
"""

import fcntl
import json
import logging
from datetime import UTC, datetime
from pathlib import Path

from webui.backend.lib.export_job_types import ExportJobFormat
from webui.backend.lib.export_preset_types import ExportPreset, ExportPresetCategory

# Setup logging
logger = logging.getLogger(__name__)

# Maximum preset file size (1MB) - prevents loading maliciously large files
MAX_PRESET_FILE_SIZE = 1024 * 1024


class ExportPresetManager:
    """Manages export settings presets (built-in and user-created)."""

    def __init__(self, builtin_dir: Path, user_dir: Path):
        """
        Initialize export preset manager.

        Args:
            builtin_dir: Path to built-in presets directory
            user_dir: Path to user presets directory
        """
        self.builtin_dir = Path(builtin_dir)
        self.user_dir = Path(user_dir)

        # Create user directory if it doesn't exist
        self.user_dir.mkdir(parents=True, exist_ok=True)

    def list_presets(self, format_filter: str | None = None) -> list[dict]:
        """
        List all available presets (built-in + user).

        Args:
            format_filter: Optional filter by export format (e.g., "darwin_core")

        Returns:
            List of preset metadata dicts with keys:
            - name: preset identifier
            - display_name: human-readable name
            - description: preset description
            - category: 'built-in' or 'user'
            - export_format: export format string
            - version: preset version
        """
        presets = []

        # Load built-in presets
        if self.builtin_dir.exists():
            for preset_file in sorted(self.builtin_dir.glob("*.json")):
                try:
                    # Check file size before loading
                    if preset_file.stat().st_size > MAX_PRESET_FILE_SIZE:
                        logger.warning(
                            f"Skipping oversized built-in preset {preset_file.name}: "
                            f"exceeds {MAX_PRESET_FILE_SIZE} bytes"
                        )
                        continue

                    with open(preset_file) as f:
                        data = json.load(f)

                    # Validate and normalize
                    data = self.normalize_preset(data)
                    valid, error_msg = self.validate_preset(data)
                    if not valid:
                        logger.warning(
                            f"Skipping invalid built-in preset {preset_file.name}: {error_msg}"
                        )
                        continue

                    # Warn if JSON name doesn't match filename
                    json_name = data.get("name")
                    if json_name and json_name != preset_file.stem:
                        logger.warning(
                            f"Preset name mismatch: file={preset_file.stem}, json={json_name}"
                        )

                    # Apply format filter
                    if format_filter and data.get("export_format") != format_filter:
                        continue

                    presets.append(
                        {
                            "name": json_name or preset_file.stem,
                            "display_name": data.get("display_name", preset_file.stem),
                            "description": data.get("description", ""),
                            "category": "built-in",
                            "export_format": data.get("export_format"),
                            "version": data.get("version", "1.0"),
                            "author": data.get("author", "system"),
                        }
                    )
                except (OSError, json.JSONDecodeError) as e:
                    logger.warning(
                        f"Could not load built-in preset {preset_file} "
                        f"({type(e).__name__}): {e}"
                    )

        # Load user presets
        if self.user_dir.exists():
            for preset_file in sorted(self.user_dir.glob("*.json")):
                try:
                    # Check file size before loading
                    if preset_file.stat().st_size > MAX_PRESET_FILE_SIZE:
                        logger.warning(
                            f"Skipping oversized user preset {preset_file.name}: "
                            f"exceeds {MAX_PRESET_FILE_SIZE} bytes"
                        )
                        continue

                    with open(preset_file) as f:
                        data = json.load(f)

                    # Validate and normalize
                    data = self.normalize_preset(data)
                    valid, error_msg = self.validate_preset(data)
                    if not valid:
                        logger.warning(f"Skipping invalid user preset {preset_file.name}: {error_msg}")
                        continue

                    # Warn if JSON name doesn't match filename
                    json_name = data.get("name")
                    if json_name and json_name != preset_file.stem:
                        logger.warning(
                            f"Preset name mismatch: file={preset_file.stem}, json={json_name}"
                        )

                    # Apply format filter
                    if format_filter and data.get("export_format") != format_filter:
                        continue

                    presets.append(
                        {
                            "name": json_name or preset_file.stem,
                            "display_name": data.get("display_name", preset_file.stem),
                            "description": data.get("description", ""),
                            "category": "user",
                            "export_format": data.get("export_format"),
                            "version": data.get("version", "1.0"),
                            "author": data.get("author", "user"),
                            "created_at": data.get("created_at", ""),
                        }
                    )
                except (OSError, json.JSONDecodeError) as e:
                    logger.warning(
                        f"Could not load user preset {preset_file} "
                        f"({type(e).__name__}): {e}"
                    )

        return presets

    def get_preset(self, name: str) -> ExportPreset | None:
        """
        Get specific preset by name.

        Built-in presets take precedence over user presets with the same name.

        Args:
            name: Preset name (without .json extension)

        Returns:
            ExportPreset instance, or None if not found or invalid
        """
        preset_data = None

        # Try built-in first (takes precedence)
        builtin_path = self.builtin_dir / f"{name}.json"
        if builtin_path.exists():
            try:
                # Check file size before loading
                if builtin_path.stat().st_size > MAX_PRESET_FILE_SIZE:
                    logger.error(
                        f"Built-in preset {name} exceeds max file size "
                        f"({MAX_PRESET_FILE_SIZE} bytes)"
                    )
                    return None

                with open(builtin_path) as f:
                    preset_data = json.load(f)
            except (OSError, json.JSONDecodeError) as e:
                logger.error(f"Error loading built-in preset {name}: {e}")
                return None

        # Try user presets if not found in built-in
        if not preset_data:
            user_path = self.user_dir / f"{name}.json"
            if user_path.exists():
                try:
                    # Check file size before loading
                    if user_path.stat().st_size > MAX_PRESET_FILE_SIZE:
                        logger.error(
                            f"User preset {name} exceeds max file size "
                            f"({MAX_PRESET_FILE_SIZE} bytes)"
                        )
                        return None

                    with open(user_path) as f:
                        preset_data = json.load(f)
                except (OSError, json.JSONDecodeError) as e:
                    logger.error(f"Error loading user preset {name}: {e}")
                    return None

        if preset_data:
            # Normalize and validate
            preset_data = self.normalize_preset(preset_data)
            valid, error_msg = self.validate_preset(preset_data)
            if not valid:
                logger.error(f"Invalid preset '{name}': {error_msg}")
                return None

            # Convert to ExportPreset object
            try:
                return ExportPreset.from_dict(preset_data)
            except (ValueError, KeyError) as e:
                logger.error(f"Failed to create ExportPreset from '{name}': {e}")
                return None

        return None

    def save_preset(self, preset: ExportPreset) -> tuple[bool, str]:
        """
        Save preset to user directory.

        Args:
            preset: ExportPreset instance to save

        Returns:
            Tuple of (success: bool, message: str)
        """
        # Validate name (alphanumeric + underscores only)
        if not preset.name or not all(c.isalnum() or c == "_" for c in preset.name):
            return False, "Preset name must contain only letters, numbers, and underscores"

        # Built-in presets cannot be saved as built-in
        if preset.category == ExportPresetCategory.BUILT_IN:
            return False, "Cannot save preset with built-in category"

        # Build preset data
        preset_data = preset.to_dict()

        # Ensure created_at is set
        if not preset_data.get("created_at"):
            preset_data["created_at"] = datetime.now(UTC).isoformat()

        # Ensure category is user (enforce on save)
        preset_data["category"] = "user"
        preset_data["author"] = "user"

        # Validate the complete preset
        valid, error_msg = self.validate_preset(preset_data)
        if not valid:
            return False, error_msg

        # Save to user directory with file locking
        try:
            preset_path = self.user_dir / f"{preset.name}.json"
            with open(preset_path, "w") as f:
                try:
                    # Acquire exclusive lock
                    fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                    json.dump(preset_data, f, indent=2)
                    f.flush()
                finally:
                    # Release lock
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)
            return True, f"Preset '{preset.name}' saved successfully"
        except OSError as e:
            return False, f"Failed to save preset: {e}"

    def delete_preset(self, name: str) -> tuple[bool, str]:
        """
        Delete user preset (built-in presets are protected).

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
            return False, f"Failed to delete preset: {e}"

    def validate_preset(self, preset_data: dict) -> tuple[bool, str]:
        """
        Validate preset structure and required fields.

        Args:
            preset_data: Preset data dict to validate

        Returns:
            Tuple of (valid: bool, error_message: str)
        """
        # Check required fields
        if not preset_data.get("name"):
            return False, "Preset must have a 'name' field"

        if not preset_data.get("display_name"):
            return False, "Preset must have a 'display_name' field"

        if not preset_data.get("export_format"):
            return False, "Preset must have an 'export_format' field"

        # Validate export_format is a known format
        export_format = preset_data.get("export_format")
        valid_formats = [f.value for f in ExportJobFormat]
        if export_format not in valid_formats:
            return False, f"Invalid export_format '{export_format}'. Must be one of: {valid_formats}"

        # Validate category if present
        category = preset_data.get("category", "user")
        valid_categories = [c.value for c in ExportPresetCategory]
        if category not in valid_categories:
            return False, f"Invalid category '{category}'. Must be one of: {valid_categories}"

        return True, "Preset validation successful"

    def normalize_preset(self, preset_data: dict) -> dict:
        """
        Normalize preset by adding missing fields with defaults.

        Args:
            preset_data: Raw preset data

        Returns:
            Normalized preset with all required fields
        """
        normalized = preset_data.copy()

        # Add default values for optional fields
        if "description" not in normalized:
            normalized["description"] = ""

        if "version" not in normalized:
            normalized["version"] = "1.0"

        if "author" not in normalized:
            normalized["author"] = "user"

        if "category" not in normalized:
            normalized["category"] = "user"

        if "filter" not in normalized:
            normalized["filter"] = {}

        if "options" not in normalized:
            normalized["options"] = {}

        return normalized

    def get_preset_count(self) -> dict[str, int]:
        """
        Get count of presets by category.

        Returns:
            Dict with 'built_in', 'user', and 'total' counts
        """
        builtin_count = (
            len(list(self.builtin_dir.glob("*.json"))) if self.builtin_dir.exists() else 0
        )
        user_count = len(list(self.user_dir.glob("*.json"))) if self.user_dir.exists() else 0

        return {"built_in": builtin_count, "user": user_count, "total": builtin_count + user_count}
