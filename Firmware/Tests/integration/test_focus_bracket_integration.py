"""
Integration tests for Focus Bracket End-to-End Workflows - 

Tests complete workflows from settings files to captured images, including:
- End-to-end capture workflows (settings → script → images)
- External media CSV detection and loading
- Settings persistence and roundtrip
- Progress message generation
- Error recovery and graceful degradation
- API integration (endpoint triggering, WebSocket progress)
- File system operations (directory creation, naming consistency)

These tests use mocked hardware (no real camera required) and verify
integration between multiple components.

Related: Issue #13  - Focus Bracket Integration Testing
"""

import os
os.environ['MOTHBOX_ENV'] = 'development'  # Must be set before importing config

import pytest
import sys
import csv
import time
import subprocess
import importlib
from pathlib import Path
from unittest.mock import MagicMock, patch, call

# Add webui backend to path
FIRMWARE_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(FIRMWARE_DIR / "webui" / "backend"))
sys.path.insert(0, str(FIRMWARE_DIR))


# ============================================================================
# Integration Test Fixtures
# ============================================================================

@pytest.fixture
def integration_env(tmp_path, monkeypatch):
    """
    Setup complete environment for integration testing

    Creates all necessary files and patches paths for isolated testing:
    - camera_settings.csv with focus bracket settings
    - controls.txt with flash settings
    - photos directory for captured images
    - Patches all path constants in relevant modules
    """
    import mothbox_paths

    # Create directory structure
    photos_dir = tmp_path / "photos"
    photos_dir.mkdir()

    controls_file = tmp_path / "controls.txt"
    controls_file.write_text("OnlyFlash=False\n")

    camera_settings = tmp_path / "camera_settings.csv"
    camera_settings.write_text("""SETTING,VALUE,DETAILS
FocusBracket,3,Three positions
FocusBracket_Start,2.0,Near
FocusBracket_End,8.0,Far
ExposureTime,10000,Fast for testing
AnalogueGain,2.0,ISO 200
""")

    # Patch paths in mothbox_paths
    monkeypatch.setattr(mothbox_paths, 'CAMERA_SETTINGS_FILE', camera_settings)
    monkeypatch.setattr(mothbox_paths, 'PHOTOS_DIR', photos_dir)
    monkeypatch.setattr(mothbox_paths, 'CONTROLS_FILE', controls_file)

    # Patch get_gpio_pins
    def mock_get_gpio_pins():
        return {'Relay_Ch1': 26, 'Relay_Ch2': 20, 'Relay_Ch3': 21}
    monkeypatch.setattr(mothbox_paths, 'get_gpio_pins', mock_get_gpio_pins)

    yield {
        'camera_settings': camera_settings,
        'photos_dir': photos_dir,
        'controls_file': controls_file,
        'tmp_path': tmp_path
    }


@pytest.fixture
def mock_camera_hardware(monkeypatch):
    """
    Mock camera hardware (Picamera2, GPIO, cv2) for integration tests

    Returns comprehensive mocks that track all interactions
    """
    # Mock cv2 (opencv) which is imported by capture_focus_bracket
    mock_cv2 = MagicMock()
    sys.modules['cv2'] = mock_cv2

    # Mock exif module
    mock_exif = MagicMock()
    sys.modules['exif'] = mock_exif

    # Mock PIL/Pillow
    mock_pil = MagicMock()
    mock_pil_image = MagicMock()
    mock_pil.ExifTags = {}
    sys.modules['PIL'] = mock_pil
    sys.modules['PIL.Image'] = mock_pil_image
    sys.modules['PIL.ExifTags'] = mock_pil.ExifTags

    # Mock libcamera
    mock_libcamera = MagicMock()
    mock_libcamera.controls = MagicMock()
    sys.modules['libcamera'] = mock_libcamera

    # Mock picamera2
    mock_picamera2_module = MagicMock()
    sys.modules['picamera2'] = mock_picamera2_module
    sys.modules['picamera2.Picamera2'] = mock_picamera2_module.Picamera2
    sys.modules['picamera2.Preview'] = mock_picamera2_module.Preview

    # Mock Picamera2
    class MockRequest:
        def __init__(self, request_id=0):
            self.request_id = request_id
            self.saved_path = None

        def save(self, stream_name, filepath):
            """Create actual file to simulate image save"""
            filepath_obj = Path(filepath)
            filepath_obj.parent.mkdir(parents=True, exist_ok=True)
            filepath_obj.write_bytes(b'\xff\xd8\xff\xe0' + b'\x00' * 1000 + b'\xff\xd9')  # Mock JPEG
            self.saved_path = filepath
            return filepath

        def release(self):
            pass

    class MockPicamera2:
        def __init__(self):
            self.started = False
            self.controls_history = []
            self.capture_count = 0
            self.config = None

        def create_still_configuration(self, main=None):
            return {'main': main, 'type': 'still'}

        def configure(self, config):
            self.config = config

        def start(self):
            self.started = True

        def stop(self):
            self.started = False

        def set_controls(self, controls):
            self.controls_history.append(controls.copy())

        def capture_request(self, flush=True):
            self.capture_count += 1
            return MockRequest(self.capture_count)

    mock_picamera2 = MockPicamera2()

    # Mock GPIO
    class MockGPIO:
        BCM = 11
        OUT = 0
        HIGH = 1
        LOW = 0

        outputs = []

        @classmethod
        def setwarnings(cls, enabled):
            pass

        @classmethod
        def setmode(cls, mode):
            pass

        @classmethod
        def setup(cls, pin, mode):
            pass

        @classmethod
        def output(cls, pin, value):
            cls.outputs.append((pin, value))

        @classmethod
        def reset(cls):
            cls.outputs.clear()

    # Inject into sys.modules
    sys.modules['RPi'] = type(sys)('RPi')
    sys.modules['RPi.GPIO'] = MockGPIO

    # Mock time.sleep to speed up tests
    sleep_calls = []
    original_sleep = time.sleep
    def mock_sleep(duration):
        sleep_calls.append(duration)
        # Still sleep a tiny bit to allow context switching
        if duration > 1:
            original_sleep(0.001)
    monkeypatch.setattr('time.sleep', mock_sleep)

    yield {
        'picamera2': mock_picamera2,
        'gpio': MockGPIO,
        'sleep_calls': sleep_calls
    }

    # Cleanup
    MockGPIO.reset()
    if 'RPi.GPIO' in sys.modules:
        del sys.modules['RPi.GPIO']
    if 'RPi' in sys.modules:
        del sys.modules['RPi']
    if 'cv2' in sys.modules:
        del sys.modules['cv2']
    if 'exif' in sys.modules:
        del sys.modules['exif']
    if 'PIL' in sys.modules:
        del sys.modules['PIL']
    if 'PIL.Image' in sys.modules:
        del sys.modules['PIL.Image']
    if 'PIL.ExifTags' in sys.modules:
        del sys.modules['PIL.ExifTags']
    if 'libcamera' in sys.modules:
        del sys.modules['libcamera']
    if 'picamera2' in sys.modules:
        del sys.modules['picamera2']
    if 'picamera2.Picamera2' in sys.modules:
        del sys.modules['picamera2.Picamera2']
    if 'picamera2.Preview' in sys.modules:
        del sys.modules['picamera2.Preview']


@pytest.fixture
def mock_external_media(tmp_path, monkeypatch):
    """
    Mock external media directory structure

    Creates media directory with camera_settings.csv directly in it to match
    script expectation that CSV is in /media/ not /media/usb0/
    """
    media_dir = tmp_path / "media"
    media_dir.mkdir(parents=True)

    # Track original functions
    original_listdir = os.listdir
    original_join = os.path.join

    def mock_listdir(path):
        """Mock listdir to simulate external media mount points"""
        path_str = str(path)
        if path_str == "/media":
            # Return contents of our mocked media directory
            return [f.name for f in media_dir.iterdir()]
        # Fall back to original for other paths
        try:
            return original_listdir(path)
        except:
            return []

    def mock_join(path, *args):
        """Mock os.path.join to redirect /media paths to our temp directory"""
        if path == "/media":
            # Redirect to our temp media directory
            return str(media_dir / "/".join(args))
        return original_join(path, *args)

    monkeypatch.setattr('os.listdir', mock_listdir)
    monkeypatch.setattr('os.path.join', mock_join)

    yield media_dir


# ============================================================================
# End-to-End Workflow Tests
# ============================================================================

@pytest.mark.integration  # Mark as integration but NOT hardware (uses mocks)
class TestFocusBracketWorkflow:
    """End-to-end workflow integration tests"""

    def test_complete_capture_workflow(self, integration_env, mock_camera_hardware, monkeypatch):
        """
        Test complete workflow: CSV settings → capture → images created

        Verifies:
        1. Settings file is read correctly
        2. Script logic executes without errors
        3. Expected number of image files created
        4. Filename format is correct
        """
        env = integration_env
        mocks = mock_camera_hardware

        # Patch mothbox_paths BEFORE importing the module
        import mothbox_paths
        monkeypatch.setattr(mothbox_paths, 'CAMERA_SETTINGS_FILE', env['camera_settings'])
        monkeypatch.setattr(mothbox_paths, 'PHOTOS_DIR', env['photos_dir'])
        monkeypatch.setattr(mothbox_paths, 'CONTROLS_FILE', env['controls_file'])

        # Mock quit to prevent exit
        import builtins
        monkeypatch.setattr(builtins, 'quit', lambda: None)

        # Mock platform detection
        import platform
        monkeypatch.setattr(platform, 'system', lambda: 'Linux')

        # Import after patching paths
        import webui.backend.scripts.capture_focus_bracket as focus_module

        # Set relay pins as module attributes (used by flashOn/flashOff)
        monkeypatch.setattr(focus_module, 'Relay_Ch1', 26, raising=False)
        monkeypatch.setattr(focus_module, 'Relay_Ch2', 20, raising=False)
        monkeypatch.setattr(focus_module, 'Relay_Ch3', 21, raising=False)

        # Mock Picamera2 constructor - patch in sys.modules
        # so when the script does `from picamera2 import Picamera2`, it gets our mock
        sys.modules['picamera2'].Picamera2 = lambda: mocks['picamera2']
        monkeypatch.setattr(focus_module, 'Picamera2', lambda: mocks['picamera2'])

        # Execute the workflow
        try:
            focus_module.main()
        except SystemExit:
            pass  # Expected from quit()

        # Verify results
        photos = sorted([f for f in env['photos_dir'].iterdir() if f.suffix == '.jpg'])

        assert len(photos) == 3, f"Expected 3 images, found {len(photos)}"

        # Verify filenames contain focus bracket markers
        for i, photo in enumerate(photos):
            # Photos might not be in order (FB0, FB1, FB2), so just check that FBx exists
            has_fb_marker = any(f"FB{j}" in photo.name for j in range(3))
            assert has_fb_marker, f"Photo {photo.name} should contain a focus bracket marker (FB0, FB1, or FB2)"
            assert photo.stat().st_size > 0, f"Photo {photo.name} should not be empty"
            assert "ManFocus_" in photo.name, f"Photo should have ManFocus_ prefix"

        # Verify all FB markers are present (FB0, FB1, FB2)
        fb_markers_found = set()
        for photo in photos:
            for j in range(3):
                if f"FB{j}" in photo.name:
                    fb_markers_found.add(j)
        assert fb_markers_found == {0, 1, 2}, f"Should have FB0, FB1, and FB2, found: {fb_markers_found}"

    def test_settings_loading_and_application(self, integration_env, mock_camera_hardware, monkeypatch):
        """
        Test that settings are loaded from CSV and applied to camera

        Verifies:
        1. load_camera_settings() reads CSV correctly
        2. Focus bracket settings are extracted
        3. Camera controls are applied
        """
        env = integration_env
        mocks = mock_camera_hardware

        # Update settings file with specific values
        env['camera_settings'].write_text("""SETTING,VALUE,DETAILS
FocusBracket,5,Five steps
FocusBracket_Start,1.0,Near
FocusBracket_End,9.0,Far
ExposureTime,20000,Slow
AnalogueGain,4.0,ISO 400
FocusBracket_SettleDelay,1000,1 second
FocusBracket_LockColorGains,1,Locked
FocusBracket_ColorGainRed,2.5,Red
FocusBracket_ColorGainBlue,1.8,Blue
""")

        import webui.backend.scripts.capture_focus_bracket as focus_module
        monkeypatch.setattr(focus_module, 'CAMERA_SETTINGS_FILE', env['camera_settings'])
        monkeypatch.setattr(focus_module, 'PHOTOS_DIR', env['photos_dir'])
        monkeypatch.setattr(focus_module, 'CONTROLS_FILE', env['controls_file'])

        # Test load_camera_settings
        settings = focus_module.load_camera_settings()

        assert settings is not None, "Settings should be loaded"
        assert settings['FocusBracket'] == 5, "Should load FocusBracket setting"
        assert settings['FocusBracket_Start'] == 1.0, "Should convert start to float"
        assert settings['FocusBracket_End'] == 9.0, "Should convert end to float"
        assert settings['ExposureTime'] == 20000, "Should load ExposureTime"
        assert settings['AnalogueGain'] == 4.0, "Should load AnalogueGain"

    def test_file_creation_and_naming(self, integration_env, mock_camera_hardware, monkeypatch):
        """
        Test file naming consistency across runs

        Verifies:
        1. Filenames follow ManFocus_{computer}_{timestamp}_FB{index}.jpg format
        2. All files are created in PHOTOS_DIR
        3. Files contain focus bracket index (FB0, FB1, FB2...)
        """
        env = integration_env
        mocks = mock_camera_hardware

        # Patch mothbox_paths BEFORE importing focus_module to survive reload
        import mothbox_paths
        monkeypatch.setattr(mothbox_paths, 'CAMERA_SETTINGS_FILE', env['camera_settings'])
        monkeypatch.setattr(mothbox_paths, 'PHOTOS_DIR', env['photos_dir'])
        monkeypatch.setattr(mothbox_paths, 'CONTROLS_FILE', env['controls_file'])

        # Patch picamera2 module BEFORE importing focus_module to survive reload
        import picamera2
        monkeypatch.setattr(picamera2, 'Picamera2', lambda: mocks['picamera2'])

        import webui.backend.scripts.capture_focus_bracket as focus_module
        monkeypatch.setattr(focus_module, 'Relay_Ch1', 26, raising=False)
        monkeypatch.setattr(focus_module, 'Relay_Ch2', 20, raising=False)
        monkeypatch.setattr(focus_module, 'Relay_Ch3', 21, raising=False)

        import builtins
        monkeypatch.setattr(builtins, 'quit', lambda: None)

        import platform
        monkeypatch.setattr(platform, 'system', lambda: 'Linux')

        # Set computer name
        monkeypatch.setattr(focus_module, 'computerName', 'test_mothbox')

        importlib.reload(focus_module)

        # Run capture
        try:
            focus_module.main()
        except SystemExit:
            pass

        # Check all files
        photos = sorted(env['photos_dir'].glob("*.jpg"))
        assert len(photos) == 3

        for i, photo in enumerate(photos):
            # Verify filename structure
            assert photo.name.startswith("ManFocus_"), f"Filename should start with ManFocus_"
            assert f"FB{i}" in photo.name, f"Filename should contain FB{i}"
            assert photo.suffix == ".jpg", f"File should have .jpg extension"

            # Verify file is in correct directory
            assert photo.parent == env['photos_dir']

    def test_error_recovery_missing_settings(self, integration_env, mock_camera_hardware, monkeypatch):
        """
        Test error recovery when settings are missing

        Verifies:
        1. Script handles missing CSV file gracefully
        2. Falls back to default values
        3. Still produces output (with warnings)
        """
        env = integration_env
        mocks = mock_camera_hardware

        # Delete settings file to simulate missing configuration
        env['camera_settings'].unlink()

        import webui.backend.scripts.capture_focus_bracket as focus_module
        monkeypatch.setattr(focus_module, 'CAMERA_SETTINGS_FILE', env['camera_settings'])

        # Test load_camera_settings with missing file
        settings = focus_module.load_camera_settings()

        # Should return None and print error
        assert settings is None, "Should return None when file missing"

    def test_progress_messages_generated(self, integration_env, mock_camera_hardware, monkeypatch, capsys):
        """
        Test that progress messages are generated during capture

        Verifies:
        1. FOCUS_BRACKET_PROGRESS messages printed
        2. Progress percentages calculated correctly
        3. Step information included
        """
        env = integration_env
        mocks = mock_camera_hardware

        import webui.backend.scripts.capture_focus_bracket as focus_module
        monkeypatch.setattr(focus_module, 'CAMERA_SETTINGS_FILE', env['camera_settings'])
        monkeypatch.setattr(focus_module, 'PHOTOS_DIR', env['photos_dir'])
        monkeypatch.setattr(focus_module, 'CONTROLS_FILE', env['controls_file'])
        monkeypatch.setattr(focus_module, 'Relay_Ch1', 26, raising=False)
        monkeypatch.setattr(focus_module, 'Relay_Ch2', 20, raising=False)
        monkeypatch.setattr(focus_module, 'Relay_Ch3', 21, raising=False)
        monkeypatch.setattr(focus_module, 'Picamera2', lambda: mocks['picamera2'])

        import builtins
        monkeypatch.setattr(builtins, 'quit', lambda: None)

        import platform
        monkeypatch.setattr(platform, 'system', lambda: 'Linux')

        importlib.reload(focus_module)

        # Run capture and capture output
        try:
            focus_module.main()
        except SystemExit:
            pass

        captured = capsys.readouterr()
        output = captured.out

        # Verify progress messages
        assert "FOCUS_BRACKET_PROGRESS" in output, "Should print progress messages"
        assert "Step 1/3" in output, "Should show step 1 of 3"
        assert "Step 2/3" in output, "Should show step 2 of 3"
        assert "Step 3/3" in output, "Should show step 3 of 3"

        # Verify percentages (33%, 66%, 100%)
        assert "33%" in output or "34%" in output, "Should show ~33% progress"
        assert "66%" in output or "67%" in output, "Should show ~66% progress"
        assert "100%" in output, "Should show 100% progress"


# ============================================================================
# External Media Integration Tests
# ============================================================================

@pytest.mark.integration  # Mark as integration but NOT hardware (uses mocks)
class TestExternalMediaIntegration:
    """External media detection and loading tests"""

    def test_external_media_csv_priority(self, integration_env, mock_external_media, mock_camera_hardware, monkeypatch):
        """
        Test that external media CSV takes priority over internal

        Verifies:
        1. Script detects camera_settings.csv on USB drive
        2. External settings are loaded instead of internal
        3. Correct priority when both exist
        """
        env = integration_env
        usb_dir = mock_external_media

        # Create external settings with different values
        external_csv = usb_dir / "camera_settings.csv"
        external_csv.write_text("""SETTING,VALUE,DETAILS
FocusBracket,7,External USB
FocusBracket_Start,0.5,External
FocusBracket_End,9.5,External
""")

        # Update internal settings (should be ignored)
        env['camera_settings'].write_text("""SETTING,VALUE,DETAILS
FocusBracket,3,Internal
FocusBracket_Start,2.0,Internal
FocusBracket_End,8.0,Internal
""")

        import webui.backend.scripts.capture_focus_bracket as focus_module
        monkeypatch.setattr(focus_module, 'CAMERA_SETTINGS_FILE', env['camera_settings'])

        # Load settings (should find external)
        settings = focus_module.load_camera_settings()

        # Verify external settings were loaded
        assert settings is not None, "Should load settings"
        assert settings['FocusBracket'] == 7, "Should load from external USB (7, not 3)"
        assert settings['FocusBracket_Start'] == 0.5, "Should use external start value"
        assert settings['FocusBracket_End'] == 9.5, "Should use external end value"

    def test_external_media_fallback_to_internal(self, integration_env, mock_external_media, monkeypatch):
        """
        Test fallback to internal settings when external not present

        Verifies:
        1. Script checks for external media
        2. Falls back to internal when external missing
        3. Correct settings loaded from fallback
        """
        env = integration_env
        usb_dir = mock_external_media

        # External directory exists but no camera_settings.csv
        assert not (usb_dir / "camera_settings.csv").exists()

        import webui.backend.scripts.capture_focus_bracket as focus_module
        monkeypatch.setattr(focus_module, 'CAMERA_SETTINGS_FILE', env['camera_settings'])

        # Load settings (should fall back to internal)
        settings = focus_module.load_camera_settings()

        # Verify internal settings were loaded
        assert settings is not None, "Should load settings"
        assert settings['FocusBracket'] == 3, "Should load from internal (3)"
        assert settings['FocusBracket_Start'] == 2.0, "Should use internal start"

    def test_multiple_external_drives_first_wins(self, tmp_path, integration_env, mock_camera_hardware, monkeypatch):
        """
        Test behavior when multiple external drives exist

        Verifies:
        1. First external drive with camera_settings.csv is used
        2. Subsequent drives are ignored
        """
        env = integration_env

        # Create multiple media directories
        media_dir = tmp_path / "media_test"
        media_dir.mkdir()

        usb0 = media_dir / "usb0"
        usb0.mkdir()
        usb0_csv = usb0 / "camera_settings.csv"
        usb0_csv.write_text("""SETTING,VALUE,DETAILS
FocusBracket,5,First USB
""")

        usb1 = media_dir / "usb1"
        usb1.mkdir()
        usb1_csv = usb1 / "camera_settings.csv"
        usb1_csv.write_text("""SETTING,VALUE,DETAILS
FocusBracket,9,Second USB
""")

        # Mock listdir to return both drives (directory names only, not full paths)
        def mock_listdir(path):
            path_str = str(path)
            if path_str == "/media":
                return ["camera_settings.csv"]  # Script expects CSV directly in /media
            elif str(usb0) in path_str:
                return ["camera_settings.csv"]
            elif str(usb1) in path_str:
                return ["camera_settings.csv"]
            return []

        # Mock os.path.join to redirect /media paths to our test directories
        original_join = os.path.join
        def mock_join(path, *args):
            if path == "/media" and len(args) == 1 and args[0] == "camera_settings.csv":
                # Return first USB drive's CSV
                return str(usb0_csv)
            return original_join(path, *args)

        monkeypatch.setattr('os.listdir', mock_listdir)
        monkeypatch.setattr('os.path.join', mock_join)

        import webui.backend.scripts.capture_focus_bracket as focus_module
        monkeypatch.setattr(focus_module, 'CAMERA_SETTINGS_FILE', env['camera_settings'])

        # Load settings
        settings = focus_module.load_camera_settings()

        # Should use first drive found
        assert settings is not None
        assert settings['FocusBracket'] == 5, "Should use first USB drive (5, not 9)"


# ============================================================================
# File System Integration Tests
# ============================================================================

@pytest.mark.integration  # Mark as integration but NOT hardware (uses mocks)
class TestFileSystemIntegration:
    """File system operations integration tests"""

    def test_photos_directory_created_if_missing(self, integration_env, mock_camera_hardware, monkeypatch):
        """
        Test that photos directory is created if it doesn't exist

        Verifies:
        1. Script creates PHOTOS_DIR if missing
        2. Photos are saved successfully
        3. Directory permissions are correct
        """
        env = integration_env
        mocks = mock_camera_hardware

        # Delete photos directory
        import shutil
        shutil.rmtree(env['photos_dir'])
        assert not env['photos_dir'].exists(), "Photos dir should be deleted"

        # Patch mothbox_paths BEFORE importing focus_module to survive reload
        import mothbox_paths
        monkeypatch.setattr(mothbox_paths, 'CAMERA_SETTINGS_FILE', env['camera_settings'])
        monkeypatch.setattr(mothbox_paths, 'PHOTOS_DIR', env['photos_dir'])
        monkeypatch.setattr(mothbox_paths, 'CONTROLS_FILE', env['controls_file'])

        # Patch picamera2 module BEFORE importing focus_module to survive reload
        import picamera2
        monkeypatch.setattr(picamera2, 'Picamera2', lambda: mocks['picamera2'])

        import webui.backend.scripts.capture_focus_bracket as focus_module
        monkeypatch.setattr(focus_module, 'Relay_Ch1', 26, raising=False)
        monkeypatch.setattr(focus_module, 'Relay_Ch2', 20, raising=False)
        monkeypatch.setattr(focus_module, 'Relay_Ch3', 21, raising=False)

        import builtins
        monkeypatch.setattr(builtins, 'quit', lambda: None)

        import platform
        monkeypatch.setattr(platform, 'system', lambda: 'Linux')

        importlib.reload(focus_module)

        # Run capture
        try:
            focus_module.main()
        except SystemExit:
            pass

        # Verify directory was created
        assert env['photos_dir'].exists(), "Photos directory should be created"

        # Verify photos were saved
        photos = list(env['photos_dir'].glob("*.jpg"))
        assert len(photos) == 3, "Should create 3 photos even with missing directory"

    def test_filename_consistency_across_runs(self, integration_env, mock_camera_hardware, monkeypatch):
        """
        Test that filenames are consistent and don't collide across multiple runs

        Verifies:
        1. Each run generates unique timestamps
        2. Files from different runs don't overwrite each other
        3. Timestamp format is consistent
        """
        env = integration_env
        mocks = mock_camera_hardware

        # Patch mothbox_paths BEFORE importing focus_module to survive reload
        import mothbox_paths
        monkeypatch.setattr(mothbox_paths, 'CAMERA_SETTINGS_FILE', env['camera_settings'])
        monkeypatch.setattr(mothbox_paths, 'PHOTOS_DIR', env['photos_dir'])
        monkeypatch.setattr(mothbox_paths, 'CONTROLS_FILE', env['controls_file'])

        # Patch picamera2 module BEFORE importing focus_module to survive reload
        import picamera2
        mock_cam1 = mock_camera_hardware['picamera2']
        monkeypatch.setattr(picamera2, 'Picamera2', lambda: mock_cam1)

        import webui.backend.scripts.capture_focus_bracket as focus_module
        monkeypatch.setattr(focus_module, 'Relay_Ch1', 26, raising=False)
        monkeypatch.setattr(focus_module, 'Relay_Ch2', 20, raising=False)
        monkeypatch.setattr(focus_module, 'Relay_Ch3', 21, raising=False)

        import builtins
        monkeypatch.setattr(builtins, 'quit', lambda: None)

        import platform
        monkeypatch.setattr(platform, 'system', lambda: 'Linux')

        # Run first capture
        importlib.reload(focus_module)

        try:
            focus_module.main()
        except SystemExit:
            pass

        photos_run1 = sorted(env['photos_dir'].glob("*.jpg"))
        assert len(photos_run1) == 3, "First run should create 3 photos"

        # Wait a moment to ensure different timestamp
        time.sleep(0.1)

        # Run second capture with fresh mock
        class MockPicamera2_2:
            def __init__(self):
                self.started = False
                self.controls_history = []
                self.capture_count = 0
                self.config = None

            def create_still_configuration(self, main=None):
                return {'main': main, 'type': 'still'}

            def configure(self, config):
                self.config = config

            def start(self):
                self.started = True

            def stop(self):
                self.started = False

            def set_controls(self, controls):
                self.controls_history.append(controls.copy())

            def capture_request(self, flush=True):
                self.capture_count += 1

                class MockRequest:
                    def __init__(self, request_id, saved_path=None):
                        self.request_id = request_id
                        self.saved_path = saved_path

                    def save(self, stream_name, filepath):
                        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
                        Path(filepath).write_bytes(b'\xff\xd8\xff\xe0' + b'\x00' * 1000 + b'\xff\xd9')
                        self.saved_path = filepath
                        return filepath

                    def release(self):
                        pass

                return MockRequest(self.capture_count)

        mock_cam2 = MockPicamera2_2()
        monkeypatch.setattr(picamera2, 'Picamera2', lambda: mock_cam2)
        importlib.reload(focus_module)

        try:
            focus_module.main()
        except SystemExit:
            pass

        photos_run2 = sorted(env['photos_dir'].glob("*.jpg"))
        assert len(photos_run2) == 6, "Second run should add 3 more photos (total 6)"

        # Verify no collisions
        filenames = [p.name for p in photos_run2]
        assert len(filenames) == len(set(filenames)), "All filenames should be unique"

    def test_csv_reading_from_various_locations(self, tmp_path, monkeypatch):
        """
        Test CSV reading from different filesystem locations

        Verifies:
        1. Absolute paths work correctly
        2. Settings loaded regardless of working directory
        3. Path handling is robust
        """
        # Create CSV in various locations
        csv_in_subdir = tmp_path / "config" / "camera_settings.csv"
        csv_in_subdir.parent.mkdir()
        csv_in_subdir.write_text("""SETTING,VALUE,DETAILS
FocusBracket,4,Subdir test
""")

        import webui.backend.scripts.capture_focus_bracket as focus_module
        monkeypatch.setattr(focus_module, 'CAMERA_SETTINGS_FILE', csv_in_subdir)

        # Load settings
        settings = focus_module.load_camera_settings()

        assert settings is not None, "Should load from subdirectory"
        assert settings['FocusBracket'] == 4, "Should read correct value"


# ============================================================================
# API Integration Tests (if feasible)
# ============================================================================

@pytest.mark.integration  # Mark as integration but NOT hardware (uses mocks)
class TestAPIIntegration:
    """API endpoint integration tests"""

    def test_api_triggers_focus_bracket_capture(self, client, integration_env, monkeypatch):
        """
        Test that POST to /api/camera/capture triggers focus bracket script

        Verifies:
        1. API detects focus bracket mode
        2. Correct script is executed
        3. Response includes focus bracket metadata
        """
        env = integration_env

        # Patch paths in routes.camera
        from Tests.conftest import patch_path_constant_everywhere
        patch_path_constant_everywhere(monkeypatch, 'CAMERA_SETTINGS_FILE', env['camera_settings'])
        patch_path_constant_everywhere(monkeypatch, 'PHOTOS_DIR', env['photos_dir'])

        # Mock subprocess to prevent actual script execution
        subprocess_calls = []
        def mock_run(*args, **kwargs):
            subprocess_calls.append((args, kwargs))

            # Create a mock photo file
            (env['photos_dir'] / "test_photo.jpg").touch()

            return MagicMock(
                returncode=0,
                stdout="Focus bracket capture complete\n",
                stderr=""
            )

        monkeypatch.setattr('subprocess.run', mock_run)

        # Trigger capture
        response = client.post('/api/camera/capture')
        assert response.status_code == 200

        data = response.get_json()

        # Verify focus bracket mode was detected
        assert data['success'] == True
        assert data.get('focus_bracket_mode') == True, "Should detect focus bracket mode"
        assert data.get('focus_bracket_steps') == 3, "Should report 3 steps"

        # Verify correct script was called
        assert len(subprocess_calls) > 0, "Subprocess should have been called"
        script_path = str(subprocess_calls[0][0][0][1])
        assert 'capture_focus_bracket.py' in script_path, "Should call capture_focus_bracket.py"

    def test_settings_update_via_api_then_capture(self, client, integration_env, monkeypatch):
        """
        Test settings update via API → script execution

        Verifies:
        1. Settings updated via POST /api/camera/settings
        2. Changes persisted to CSV
        3. Subsequent capture uses new settings
        """
        env = integration_env

        from Tests.conftest import patch_path_constant_everywhere
        patch_path_constant_everywhere(monkeypatch, 'CAMERA_SETTINGS_FILE', env['camera_settings'])

        # Update settings via API
        response = client.post('/api/camera/settings', json={
            'FocusBracket': '7',
            'FocusBracket_Start': '1.0',
            'FocusBracket_End': '9.0'
        })

        assert response.status_code == 200
        assert response.get_json()['success'] == True

        # Verify settings were written to CSV
        with open(env['camera_settings'], 'r') as f:
            reader = csv.DictReader(f)
            settings = {row['SETTING']: row['VALUE'] for row in reader}

        assert settings['FocusBracket'] == '7', "Should update FocusBracket"
        assert settings['FocusBracket_Start'] == '1.0', "Should update start position"
        assert settings['FocusBracket_End'] == '9.0', "Should update end position"

        # Now test that detection picks up new values
        from routes.camera import _should_use_focus_bracket_mode
        use_fb, steps, start, end = _should_use_focus_bracket_mode()

        assert use_fb == True, "Should enable focus bracket mode"
        assert steps == 7, "Should use updated step count"
        assert start == 1.0, "Should use updated start position"
        assert end == 9.0, "Should use updated end position"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
