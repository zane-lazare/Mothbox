"""
Unit Tests: Noise Reduction Mode Validation

Tests validation logic for noise reduction control including
boundary values, type conversion, and error handling.

These tests validate the routes/camera.py validation logic for:
- NoiseReductionMode (0=Off, 1=Fast, 2=High Quality)

RUN ON RASPBERRY PI ONLY - tests Flask routes

Usage:
    pytest Tests/unit/test_noise_reduction_validation.py -v -s
"""
import os
os.environ['MOTHBOX_ENV'] = 'development'  # Must be set before importing config

import pytest
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'webui' / 'backend'))


@pytest.mark.stream
class TestNoiseReductionModeBoundaryValues:
    """Test noise reduction mode validation (0, 1, 2)"""

    def test_noise_reduction_off(self, client):
        """Test NoiseReductionMode = 0 (Off)"""
        response = client.post('/api/camera/settings', json={'NoiseReductionMode': 0})
        assert response.status_code == 200, "Should accept NoiseReductionMode=0 (Off)"
        print("\n✓ Accepted NoiseReductionMode=0 (Off)")

    def test_noise_reduction_fast(self, client):
        """Test NoiseReductionMode = 1 (Fast)"""
        response = client.post('/api/camera/settings', json={'NoiseReductionMode': 1})
        assert response.status_code == 200, "Should accept NoiseReductionMode=1 (Fast)"
        print("✓ Accepted NoiseReductionMode=1 (Fast)")

    def test_noise_reduction_high_quality(self, client):
        """Test NoiseReductionMode = 2 (High Quality)"""
        response = client.post('/api/camera/settings', json={'NoiseReductionMode': 2})
        assert response.status_code == 200, "Should accept NoiseReductionMode=2 (High Quality)"
        print("✓ Accepted NoiseReductionMode=2 (High Quality)")

    def test_noise_reduction_invalid_negative(self, client):
        """Test NoiseReductionMode = -1 (invalid) - should fail"""
        response = client.post('/api/camera/settings', json={'NoiseReductionMode': -1})
        assert response.status_code == 400, "Should reject NoiseReductionMode=-1"
        data = response.get_json()
        assert 'error' in data
        print("✓ Rejected NoiseReductionMode=-1 (negative)")

    def test_noise_reduction_invalid_above_range(self, client):
        """Test NoiseReductionMode = 3 (invalid) - should fail"""
        response = client.post('/api/camera/settings', json={'NoiseReductionMode': 3})
        assert response.status_code == 400, "Should reject NoiseReductionMode=3"
        data = response.get_json()
        assert 'error' in data
        print("✓ Rejected NoiseReductionMode=3 (above valid range)")

    def test_noise_reduction_invalid_way_out_of_range(self, client):
        """Test NoiseReductionMode = 100 (invalid) - should fail"""
        response = client.post('/api/camera/settings', json={'NoiseReductionMode': 100})
        assert response.status_code == 400, "Should reject NoiseReductionMode=100"
        data = response.get_json()
        assert 'error' in data
        print("✓ Rejected NoiseReductionMode=100 (way out of range)")

    def test_noise_reduction_invalid_string(self, client):
        """Test NoiseReductionMode with string value - should fail"""
        response = client.post('/api/camera/settings', json={'NoiseReductionMode': 'high'})
        assert response.status_code == 400, "Should reject NoiseReductionMode='high'"
        data = response.get_json()
        assert 'error' in data
        print("✓ Rejected NoiseReductionMode='high' (invalid type)")

    def test_noise_reduction_invalid_float(self, client):
        """Test NoiseReductionMode with float value - should fail"""
        response = client.post('/api/camera/settings', json={'NoiseReductionMode': 1.5})
        assert response.status_code == 400, "Should reject NoiseReductionMode=1.5"
        data = response.get_json()
        assert 'error' in data
        print("✓ Rejected NoiseReductionMode=1.5 (float not allowed)")

    def test_noise_reduction_invalid_none(self, client):
        """Test NoiseReductionMode with None value - should fail"""
        response = client.post('/api/camera/settings', json={'NoiseReductionMode': None})
        assert response.status_code == 400, "Should reject NoiseReductionMode=None"
        data = response.get_json()
        assert 'error' in data
        print("✓ Rejected NoiseReductionMode=None (null value)")


@pytest.mark.stream
class TestNoiseReductionPersistence:
    """Test noise reduction mode persistence"""

    def test_noise_reduction_persistence_off(self, client):
        """Test that NoiseReductionMode=0 persists correctly"""
        # Set to Off
        response = client.post('/api/camera/settings', json={'NoiseReductionMode': 0})
        assert response.status_code == 200

        # Verify it persisted
        response = client.get('/api/camera/settings')
        assert response.status_code == 200
        data = response.get_json()
        assert 'NoiseReductionMode' in data
        assert int(data['NoiseReductionMode']) == 0
        print("\n✓ NoiseReductionMode=0 (Off) persisted correctly")

    def test_noise_reduction_persistence_fast(self, client):
        """Test that NoiseReductionMode=1 persists correctly"""
        # Set to Fast
        response = client.post('/api/camera/settings', json={'NoiseReductionMode': 1})
        assert response.status_code == 200

        # Verify it persisted
        response = client.get('/api/camera/settings')
        assert response.status_code == 200
        data = response.get_json()
        assert int(data['NoiseReductionMode']) == 1
        print("✓ NoiseReductionMode=1 (Fast) persisted correctly")

    def test_noise_reduction_persistence_high_quality(self, client):
        """Test that NoiseReductionMode=2 persists correctly"""
        # Set to High Quality
        response = client.post('/api/camera/settings', json={'NoiseReductionMode': 2})
        assert response.status_code == 200

        # Verify it persisted
        response = client.get('/api/camera/settings')
        assert response.status_code == 200
        data = response.get_json()
        assert int(data['NoiseReductionMode']) == 2
        print("✓ NoiseReductionMode=2 (High Quality) persisted correctly")


@pytest.mark.stream
class TestNoiseReductionWebUISettings:
    """Test noise reduction in webui_settings.txt (preview settings)"""

    def test_webui_noise_reduction_default(self, client):
        """Test that webui noise reduction has sensible default"""
        response = client.get('/api/config/webui')
        assert response.status_code == 200
        data = response.get_json()

        # Should have noise_reduction_mode key with default value 0
        assert 'noise_reduction_mode' in data
        assert data['noise_reduction_mode'] in [0, 1, 2]
        print(f"\n✓ WebUI noise_reduction_mode default: {data['noise_reduction_mode']}")

    def test_webui_noise_reduction_update_valid(self, client):
        """Test updating webui noise reduction to valid values"""
        # Test all valid modes
        for mode in [0, 1, 2]:
            response = client.post('/api/config/webui', json={'noise_reduction_mode': mode})
            assert response.status_code == 200, f"Should accept noise_reduction_mode={mode}"

            # Verify persistence
            response = client.get('/api/config/webui')
            data = response.get_json()
            assert data['noise_reduction_mode'] == mode
            print(f"✓ WebUI noise_reduction_mode={mode} updated and persisted")

    def test_webui_noise_reduction_invalid(self, client):
        """Test that invalid noise reduction values are rejected"""
        # Test invalid values
        invalid_values = [-1, 3, 10, 'high', None]

        for invalid_val in invalid_values:
            response = client.post('/api/config/webui', json={'noise_reduction_mode': invalid_val})
            assert response.status_code == 400, f"Should reject noise_reduction_mode={invalid_val}"
            data = response.get_json()
            assert 'error' in data

        print("✓ WebUI rejected all invalid noise reduction values")


@pytest.mark.stream
class TestNoiseReductionCombinedSettings:
    """Test noise reduction with other image quality settings"""

    def test_combined_quality_settings_with_noise_reduction(self, client):
        """Test updating all quality settings including noise reduction"""
        settings = {
            'sharpness': 2.0,
            'brightness': 0.1,
            'contrast': 1.5,
            'saturation': 1.2,
            'noise_reduction_mode': 2  # High Quality
        }

        response = client.post('/api/config/webui', json=settings)
        assert response.status_code == 200, "Should accept all quality settings with noise reduction"
        print("\n✓ Accepted combined quality settings with noise reduction")

        # Verify all were stored
        response = client.get('/api/config/webui')
        data = response.get_json()

        assert abs(data['sharpness'] - 2.0) < 0.01
        assert abs(data['brightness'] - 0.1) < 0.01
        assert abs(data['contrast'] - 1.5) < 0.01
        assert abs(data['saturation'] - 1.2) < 0.01
        assert data['noise_reduction_mode'] == 2
        print("   All settings stored correctly ✓")

    def test_invalid_noise_reduction_rejects_entire_update(self, client):
        """Test that invalid noise reduction rejects the entire update"""
        settings = {
            'sharpness': 2.0,
            'brightness': 0.1,
            'noise_reduction_mode': 5  # INVALID
        }

        response = client.post('/api/config/webui', json=settings)
        assert response.status_code == 400, "Should reject update with invalid noise reduction"
        data = response.get_json()
        assert 'error' in data
        print("\n✓ Invalid noise reduction mode rejected entire update")


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
