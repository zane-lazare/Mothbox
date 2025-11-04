#!/usr/bin/env python3
"""Debug test for focus peaking"""
import numpy as np
from unittest.mock import patch
import sys

# Add webui/backend to path
sys.path.insert(0, 'webui/backend')

# Import the module
import liveview_stream

# Create a simple test
frame = np.zeros((768, 1024, 3), dtype=np.uint8)
frame[300:400, 400:600] = [100, 150, 200]

print(f"Initial frame non-zero pixels: {np.sum(frame > 0)}")
print(f"Initial CV2_AVAILABLE: {liveview_stream.CV2_AVAILABLE}")

# Create a minimal streamer (without camera)
class MockCamera:
    def __init__(self):
        pass

streamer = liveview_stream.LiveViewStreamer()

# First try without patching (should return frame unchanged)
print("\n=== Without patching ===")
result1 = streamer._apply_focus_peaking_laplacian(frame, threshold=100, color='green')
print(f"Result non-zero pixels: {np.sum(result1 > 0)}")
print(f"Result is frame: {result1 is frame}")

# Now try WITH patching (like the test does)
print("\n=== With patching ===")
# Import mock opencv
sys.path.insert(0, 'Tests')
from conftest import mock_opencv
import pytest

# Get the mock
mock_cv = pytest.fixture(mock_opencv)(lambda x: None)(None)

with patch('liveview_stream.CV2_AVAILABLE', True):
    with patch('liveview_stream.cv2', mock_cv, create=True):
        with patch('liveview_stream.np', np, create=True):
            print(f"CV2_AVAILABLE inside patch: {liveview_stream.CV2_AVAILABLE}")
            result2 = streamer._apply_focus_peaking_laplacian(frame, threshold=100, color='green')

print(f"Result non-zero pixels: {np.sum(result2 > 0)}")
print(f"Result is frame: {result2 is frame}")
print(f"Result equals frame: {np.array_equal(result2, frame)}")
