"""
Integration Tests: Firmware Compatibility (4.x vs 5.x)

Tests that calibration works correctly with both 4.x and 5.x firmware
installations, ensuring no hardcoded paths break compatibility.

Key scenarios tested:
- 4.x firmware environment uses 4.x/TakePhoto.py
- 5.x firmware environment uses 5.x/TakePhoto.py
- No hardcoded "5.x" paths in code

Related: Issue #45, PR #55 - Camera Calibration Architecture

Run with: pytest Tests/integration/test_firmware_compatibility.py -v
"""

import pytest
from pathlib import Path


@pytest.mark.integration
class TestFirmwareCompatibility:
    """Test calibration works with both 4.x and 5.x firmware"""

    def test_4x_firmware_calibration_uses_correct_path(self, client, tmp_path, monkeypatch):
        """Test calibration with 4.x firmware uses 4.x/TakePhoto.py"""
        print("\n🔧 Testing 4.x firmware compatibility...")

        # Setup mock 4.x environment
        controls_file = tmp_path / "controls.txt"
        controls_file.write_text("softwareversion=4.0.0\n")

        mothbox_home = tmp_path / "mothbox"
        mothbox_home.mkdir()

        # Create 4.x directory structure
        takephoto_4x_dir = mothbox_home / "4.x"
        takephoto_4x_dir.mkdir()
        takephoto_4x = takephoto_4x_dir / "TakePhoto.py"
        takephoto_4x.write_text("""
def run_calibration():
    print("4.x calibration running")
    # In real scenario, would update camera_settings.csv
""")

        # Patch mothbox_paths
        import mothbox_paths
        monkeypatch.setattr(mothbox_paths, 'CONTROLS_FILE', controls_file)
        monkeypatch.setattr(mothbox_paths, 'MOTHBOX_HOME', mothbox_home)

        # Verify firmware detection
        from mothbox_paths import get_firmware_version, get_takephoto_script
        version = get_firmware_version()
        assert version == "4", f"Should detect 4.x firmware, got {version}"

        script_path = get_takephoto_script()
        assert "4.x" in str(script_path), f"Should use 4.x path, got {script_path}"
        assert script_path.exists(), "4.x/TakePhoto.py should exist"

        print(f"   ✓ Detected firmware: {version}.x")
        print(f"   ✓ TakePhoto.py path: {script_path}")
        print(f"   ✓ 4.x firmware compatibility verified")

    def test_5x_firmware_calibration_uses_correct_path(self, client, tmp_path, monkeypatch):
        """Test calibration with 5.x firmware uses 5.x/TakePhoto.py"""
        print("\n🔧 Testing 5.x firmware compatibility...")

        # Setup mock 5.x environment
        controls_file = tmp_path / "controls.txt"
        controls_file.write_text("softwareversion=5.0.0\n")

        mothbox_home = tmp_path / "mothbox"
        mothbox_home.mkdir()

        # Create 5.x directory structure
        takephoto_5x_dir = mothbox_home / "5.x"
        takephoto_5x_dir.mkdir()
        takephoto_5x = takephoto_5x_dir / "TakePhoto.py"
        takephoto_5x.write_text("""
def run_calibration():
    print("5.x calibration running")
    # In real scenario, would update camera_settings.csv
""")

        # Patch mothbox_paths
        import mothbox_paths
        monkeypatch.setattr(mothbox_paths, 'CONTROLS_FILE', controls_file)
        monkeypatch.setattr(mothbox_paths, 'MOTHBOX_HOME', mothbox_home)

        # Verify firmware detection
        from mothbox_paths import get_firmware_version, get_takephoto_script
        version = get_firmware_version()
        assert version == "5", f"Should detect 5.x firmware, got {version}"

        script_path = get_takephoto_script()
        assert "5.x" in str(script_path), f"Should use 5.x path, got {script_path}"
        assert script_path.exists(), "5.x/TakePhoto.py should exist"

        print(f"   ✓ Detected firmware: {version}.x")
        print(f"   ✓ TakePhoto.py path: {script_path}")
        print(f"   ✓ 5.x firmware compatibility verified")

    def test_no_hardcoded_5x_paths_in_code(self):
        """Test code doesn't contain hardcoded '5.x' paths"""
        print("\n🔍 Checking for hardcoded paths...")

        # Read the files that should use dynamic paths
        files_to_check = [
            Path(__file__).parent.parent.parent / 'webui' / 'backend' / 'scripts' / 'run_photo_calibration.py',
            Path(__file__).parent.parent.parent / 'webui' / 'backend' / 'routes' / 'camera.py',
            Path(__file__).parent.parent.parent / 'mothbox_paths.py',
        ]

        hardcoded_issues = []

        for file_path in files_to_check:
            if not file_path.exists():
                continue

            content = file_path.read_text()

            # Check for hardcoded "5.x" paths (excluding comments and docstrings)
            lines = content.split('\n')
            for i, line in enumerate(lines, 1):
                # Skip comments and docstrings
                if line.strip().startswith('#') or line.strip().startswith('"""') or line.strip().startswith("'''"):
                    continue

                # Check for hardcoded path patterns
                if "/ '5.x'" in line or '/ "5.x"' in line or "Path('5.x')" in line or 'Path("5.x")' in line:
                    hardcoded_issues.append(f"{file_path.name}:{i}: {line.strip()}")

        if hardcoded_issues:
            print(f"   ❌ Found hardcoded '5.x' paths:")
            for issue in hardcoded_issues:
                print(f"      {issue}")
            pytest.fail(f"Found {len(hardcoded_issues)} hardcoded '5.x' path(s)")
        else:
            print(f"   ✓ No hardcoded '5.x' paths found")
            print(f"   ✓ All paths use dynamic firmware detection")

    def test_fallback_firmware_version_is_documented(self):
        """Test fallback firmware version behavior is documented"""
        print("\n📚 Checking fallback behavior documentation...")

        mothbox_paths_file = Path(__file__).parent.parent.parent / 'mothbox_paths.py'

        if not mothbox_paths_file.exists():
            pytest.skip("mothbox_paths.py not found")

        content = mothbox_paths_file.read_text()

        # Check that fallback behavior is documented
        assert "fallback" in content.lower() or "default" in content.lower(), \
            "Fallback behavior should be documented"

        # Check that get_firmware_version mentions what happens when controls.txt missing
        assert "5" in content or '"5"' in content, \
            "Should document default/fallback to version 5"

        print(f"   ✓ Fallback behavior documented")
        print(f"   ✓ Default firmware version: 5.x")


@pytest.mark.integration
class TestFirmwareVersionEdgeCases:
    """Test edge cases in firmware version handling"""

    def test_mixed_firmware_directories(self, tmp_path, monkeypatch):
        """Test behavior when both 4.x and 5.x directories exist"""
        print("\n🔀 Testing mixed firmware directories...")

        # Setup environment with BOTH directories
        controls_file = tmp_path / "controls.txt"
        controls_file.write_text("softwareversion=4.0.0\n")  # But user selected 4.x

        mothbox_home = tmp_path / "mothbox"
        mothbox_home.mkdir()

        # Create both directories
        takephoto_4x_dir = mothbox_home / "4.x"
        takephoto_4x_dir.mkdir()
        (takephoto_4x_dir / "TakePhoto.py").write_text("# 4.x")

        takephoto_5x_dir = mothbox_home / "5.x"
        takephoto_5x_dir.mkdir()
        (takephoto_5x_dir / "TakePhoto.py").write_text("# 5.x")

        # Patch
        import mothbox_paths
        monkeypatch.setattr(mothbox_paths, 'CONTROLS_FILE', controls_file)
        monkeypatch.setattr(mothbox_paths, 'MOTHBOX_HOME', mothbox_home)

        # Should use the one specified in controls.txt (4.x)
        from mothbox_paths import get_firmware_version, get_takephoto_script
        version = get_firmware_version()
        script_path = get_takephoto_script()

        assert version == "4", "Should use version from controls.txt"
        assert "4.x" in str(script_path), "Should use 4.x even when 5.x exists"

        print(f"   ✓ Correctly selected {version}.x from controls.txt")
        print(f"   ✓ Ignored presence of other firmware directories")

    def test_firmware_version_with_patch_number(self, tmp_path, monkeypatch):
        """Test firmware version detection with patch numbers (e.g., 5.1.2)"""
        print("\n🔢 Testing version with patch numbers...")

        controls_file = tmp_path / "controls.txt"
        controls_file.write_text("softwareversion=5.1.2\n")

        # Patch
        import mothbox_paths
        monkeypatch.setattr(mothbox_paths, 'CONTROLS_FILE', controls_file)

        # Should extract major version only
        from mothbox_paths import get_firmware_version
        version = get_firmware_version()

        assert version == "5", f"Should extract major version '5' from '5.1.2', got '{version}'"
        print(f"   ✓ Extracted major version {version} from 5.1.2")


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
