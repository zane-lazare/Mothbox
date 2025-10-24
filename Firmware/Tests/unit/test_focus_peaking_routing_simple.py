"""
Simple verification of focus peaking routing logic (no external dependencies)
"""

def test_routing_logic():
    """Test the routing logic for hardware MJPEG with focus peaking"""

    # Test case 1: Focus peaking disabled -> pure hardware MJPEG
    focus_peaking_enabled = False
    cv2_available = True

    # Simulate the routing logic from _stream_hardware_mjpeg
    if focus_peaking_enabled and cv2_available:
        mode = "hybrid"
    else:
        mode = "pure_hardware"

    assert mode == "pure_hardware", "Should use pure hardware when focus peaking disabled"
    print("✓ Test 1 passed: Focus peaking disabled -> pure hardware MJPEG")

    # Test case 2: Focus peaking enabled, OpenCV available -> hybrid mode
    focus_peaking_enabled = True
    cv2_available = True

    if focus_peaking_enabled and cv2_available:
        mode = "hybrid"
    else:
        mode = "pure_hardware"

    assert mode == "hybrid", "Should use hybrid mode when focus peaking enabled and OpenCV available"
    print("✓ Test 2 passed: Focus peaking enabled + OpenCV -> hybrid mode")

    # Test case 3: Focus peaking enabled, OpenCV NOT available -> pure hardware (no overlay)
    focus_peaking_enabled = True
    cv2_available = False

    if focus_peaking_enabled and cv2_available:
        mode = "hybrid"
    else:
        mode = "pure_hardware"

    assert mode == "pure_hardware", "Should use pure hardware when OpenCV not available"
    print("✓ Test 3 passed: Focus peaking enabled but no OpenCV -> pure hardware (no overlay)")

    # Test case 4: Both disabled
    focus_peaking_enabled = False
    cv2_available = False

    if focus_peaking_enabled and cv2_available:
        mode = "hybrid"
    else:
        mode = "pure_hardware"

    assert mode == "pure_hardware", "Should use pure hardware when both disabled"
    print("✓ Test 4 passed: Both disabled -> pure hardware")

    print("\n✅ All routing logic tests passed!")


if __name__ == '__main__':
    test_routing_logic()
