"""
Validation script to test 3 approaches for mocking module-level preset_manager instance.

Problem: routes/presets.py line 21 instantiates preset_manager at module level:
    preset_manager = PresetManager(BUILTIN_PRESET_DIR, USER_PRESET_DIR)

This happens at import time, before test patches can be applied.
"""
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

# Setup paths
sys.path.insert(0, str(Path(__file__).parent.parent / 'webui' / 'backend'))

print("=" * 70)
print("APPROACH 1: Patch preset_manager attribute after import")
print("=" * 70)

# Clean up any previous imports
if 'routes.presets' in sys.modules:
    del sys.modules['routes.presets']
if 'preset_manager' in sys.modules:
    del sys.modules['preset_manager']

try:
    # Import the module (preset_manager gets instantiated)
    from routes import presets

    # Now patch the instance
    mock_pm = MagicMock()
    mock_pm.list_presets.return_value = [{'name': 'test', 'workflow': 'both'}]

    # Replace the module-level instance
    presets.preset_manager = mock_pm

    # Test if it works
    result = presets.preset_manager.list_presets()
    print(f"✅ APPROACH 1 WORKS: {result}")
    print(f"   preset_manager type: {type(presets.preset_manager)}")
    print(f"   Is mock?: {isinstance(presets.preset_manager, MagicMock)}")
except Exception as e:
    print(f"❌ APPROACH 1 FAILED: {e}")

print("\n" + "=" * 70)
print("APPROACH 2: Patch PresetManager class before import")
print("=" * 70)

# Clean up imports
if 'routes.presets' in sys.modules:
    del sys.modules['routes.presets']
if 'preset_manager' in sys.modules:
    del sys.modules['preset_manager']

try:
    # Patch PresetManager class BEFORE importing routes.presets
    with patch('preset_manager.PresetManager') as MockPresetManagerClass:
        # Configure the mock class to return a mock instance
        mock_instance = MagicMock()
        mock_instance.list_presets.return_value = [{'name': 'test2', 'workflow': 'both'}]
        MockPresetManagerClass.return_value = mock_instance

        # NOW import the module (will use our mocked class)
        from routes import presets

        # Test if it works
        result = presets.preset_manager.list_presets()
        print(f"✅ APPROACH 2 WORKS: {result}")
        print(f"   preset_manager type: {type(presets.preset_manager)}")
        print(f"   PresetManager was called?: {MockPresetManagerClass.called}")
        print(f"   Call args: {MockPresetManagerClass.call_args}")
except Exception as e:
    print(f"❌ APPROACH 2 FAILED: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 70)
print("APPROACH 3: Use sys.modules to mock preset_manager module")
print("=" * 70)

# Clean up imports
if 'routes.presets' in sys.modules:
    del sys.modules['routes.presets']
if 'preset_manager' in sys.modules:
    del sys.modules['preset_manager']

try:
    # Create a mock module
    mock_preset_manager_module = MagicMock()
    mock_instance = MagicMock()
    mock_instance.list_presets.return_value = [{'name': 'test3', 'workflow': 'both'}]
    mock_preset_manager_module.PresetManager.return_value = mock_instance

    # Inject the mock module BEFORE import
    sys.modules['preset_manager'] = mock_preset_manager_module

    # NOW import routes.presets (will use our mocked module)
    from routes import presets

    # Test if it works
    result = presets.preset_manager.list_presets()
    print(f"✅ APPROACH 3 WORKS: {result}")
    print(f"   preset_manager type: {type(presets.preset_manager)}")
    print(f"   PresetManager was called?: {mock_preset_manager_module.PresetManager.called}")
    print(f"   Call args: {mock_preset_manager_module.PresetManager.call_args}")
except Exception as e:
    print(f"❌ APPROACH 3 FAILED: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 70)
print("SUMMARY")
print("=" * 70)
print("""
Approach 1 (Monkeypatch after import):
  - Simplest, requires just: presets.preset_manager = mock_pm
  - Works in test context with direct attribute assignment
  - Easy to use with pytest fixtures

Approach 2 (Patch class before import):
  - Requires patching before module import
  - Complex to use in test fixtures (import timing issues)
  - Would need to import routes.presets inside each test

Approach 3 (sys.modules injection):
  - Similar to Approach 2 but at module level
  - Already used successfully for RPi.GPIO, Picamera2 mocks
  - Can be done in conftest.py before any imports

RECOMMENDATION: Use Approach 1 (monkeypatch) for tests.
  - Create a pytest fixture that patches presets.preset_manager
  - Use it like: def test_foo(mock_preset_manager): ...
""")
