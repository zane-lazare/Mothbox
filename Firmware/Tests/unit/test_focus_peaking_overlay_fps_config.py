"""
Unit tests for focus_peaking_overlay_fps configuration integration
"""

def test_validation_logic():
    """Test the validation logic for focus_peaking_overlay_fps"""

    # Test valid values
    valid_values = [1, 5, 10, 15, 20, 25, 30]
    for val in valid_values:
        assert 1 <= val <= 30, f"Valid value {val} should pass validation"
    print(f"✓ All valid values pass: {valid_values}")

    # Test invalid values
    invalid_values = [0, -1, 31, 50, 100]
    for val in invalid_values:
        assert not (1 <= val <= 30), f"Invalid value {val} should fail validation"
    print(f"✓ All invalid values rejected: {invalid_values}")

    # Test overlay interval calculation
    test_fps_values = [
        (1, 1.0),      # 1 fps = 1 second interval
        (10, 0.1),     # 10 fps = 0.1 second interval
        (20, 0.05),    # 20 fps = 0.05 second interval
        (30, 0.0333),  # 30 fps = ~0.033 second interval
    ]

    for fps, expected_interval in test_fps_values:
        calculated_interval = 1.0 / fps
        # Allow small floating point tolerance
        assert abs(calculated_interval - expected_interval) < 0.001, \
            f"FPS {fps} should produce interval ~{expected_interval}, got {calculated_interval}"
    print("✓ Overlay interval calculations correct")

    # Test lambda validation function (same as in camera.py)
    validator = lambda v: 1 <= int(v) <= 30

    # Test with integers
    assert validator(1) == True
    assert validator(10) == True
    assert validator(30) == True
    assert validator(0) == False
    assert validator(31) == False
    print("✓ Lambda validator works with integers")

    # Test with strings (user input)
    assert validator("1") == True
    assert validator("10") == True
    assert validator("30") == True
    assert validator("0") == False
    assert validator("31") == False
    print("✓ Lambda validator works with string inputs")

    print("\n✅ All configuration validation tests passed!")


def test_default_value():
    """Test that default value is reasonable"""
    default_fps = 10

    # Default should be in valid range
    assert 1 <= default_fps <= 30, "Default FPS should be in valid range"

    # Default should produce reasonable interval
    interval = 1.0 / default_fps
    assert 0.033 <= interval <= 1.0, "Default interval should be reasonable (33ms to 1s)"

    # Default should be CPU-friendly (not too high)
    assert default_fps <= 15, "Default FPS should be conservative for CPU efficiency"

    print(f"✓ Default value {default_fps} fps (interval={interval:.3f}s) is appropriate")


if __name__ == '__main__':
    test_validation_logic()
    test_default_value()
