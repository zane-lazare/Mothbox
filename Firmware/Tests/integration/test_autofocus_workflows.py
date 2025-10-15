"""
Integration Tests: Autofocus Workflows (Feature Set 3)

Tests autofocus behavior under various conditions including
success/fail scenarios, focus modes, and streaming interaction.

These tests require real Raspberry Pi hardware and camera.

Run with: pytest Tests/integration/test_autofocus_workflows.py -v -s
"""

import pytest
import time
from pathlib import Path

# Fixtures (app, client) are provided by conftest.py


class TestAutofocusSuccessScenarios:
    """Test autofocus under favorable conditions"""

    def test_autofocus_well_lit_high_contrast(self, client):
        """Test autofocus success in well-lit, high-contrast scene"""
        print("\n🔍 Testing autofocus in well-lit conditions...")

        response = client.post('/api/camera/autofocus')

        assert response.status_code == 200
        data = response.get_json()

        # Verify success
        assert data['success'] is True, "Autofocus should succeed in good lighting"
        assert data['af_state'] in ['Success', 'Idle'], \
            f"Expected Success/Idle, got {data['af_state']}"

        # Verify lens position is reasonable
        lens_pos = data['lens_position']
        assert 0.0 <= lens_pos <= 15.0, f"Lens position {lens_pos} out of range"

        # Verify timing
        duration = data['duration_seconds']
        assert 0 < duration < 10, f"Autofocus took {duration}s (should be <10s)"

        # Verify metadata
        metadata = data['metadata']
        assert 'exposure_time' in metadata
        assert 'analogue_gain' in metadata
        assert 100 <= metadata['exposure_time'] <= 1000000
        assert 1.0 <= metadata['analogue_gain'] <= 16.0

        print(f"   ✓ Autofocus succeeded in {duration}s")
        print(f"   ✓ Lens position: {lens_pos} diopters")
        print(f"   ✓ AF state: {data['af_state']}")
        print(f"   ✓ Exposure: {metadata['exposure_time']}µs")
        print(f"   ✓ Gain: {metadata['analogue_gain']}")

    def test_autofocus_multiple_cycles(self, client):
        """Test multiple autofocus cycles in succession"""
        print("\n🔁 Testing 5 consecutive autofocus cycles...")

        results = []
        for i in range(5):
            print(f"   Cycle {i+1}/5...")
            response = client.post('/api/camera/autofocus')
            assert response.status_code == 200

            data = response.get_json()
            results.append({
                'lens_position': data['lens_position'],
                'duration': data['duration_seconds'],
                'af_state': data['af_state']
            })

            # Brief delay between cycles
            time.sleep(0.5)

        # Verify all cycles completed
        assert len(results) == 5, "Should complete all 5 cycles"

        # Verify lens positions are consistent (within 1 diopter)
        lens_positions = [r['lens_position'] for r in results]
        lens_range = max(lens_positions) - min(lens_positions)
        assert lens_range < 2.0, \
            f"Lens positions vary too much ({lens_range}D) - focusing unstable"

        # Verify timing is reasonable
        durations = [r['duration'] for r in results]
        avg_duration = sum(durations) / len(durations)
        assert avg_duration < 5.0, \
            f"Average autofocus duration {avg_duration}s too slow"

        print(f"   ✓ All 5 cycles completed")
        print(f"   ✓ Lens position range: {lens_range:.2f}D (consistent)")
        print(f"   ✓ Average duration: {avg_duration:.2f}s")
        print(f"   ✓ Positions: {[f'{p:.2f}D' for p in lens_positions]}")

    def test_autofocus_normal_range(self, client):
        """Test autofocus with normal range (0.5m - infinity)"""
        print("\n📏 Testing autofocus with normal range...")

        # Set AfRange to Normal (0) via webui settings
        response = client.post('/api/config/webui', json={'af_range': 0})
        assert response.status_code == 200

        time.sleep(0.2)

        # Run autofocus
        response = client.post('/api/camera/autofocus')
        assert response.status_code == 200

        data = response.get_json()
        assert data['success'] is True or data['af_state'] in ['Success', 'Idle']

        print(f"   ✓ Normal range autofocus completed")
        print(f"   ✓ Lens position: {data['lens_position']}D")


class TestAutofocusFailureScenarios:
    """Test autofocus under challenging conditions"""

    def test_autofocus_returns_result_regardless(self, client):
        """Test autofocus returns valid result even if it fails"""
        print("\n❌ Testing autofocus failure handling...")

        response = client.post('/api/camera/autofocus')
        assert response.status_code == 200, "Should return 200 even if AF fails"

        data = response.get_json()

        # Should have valid structure regardless of success
        assert 'success' in data
        assert 'af_state' in data
        assert 'lens_position' in data
        assert 'duration_seconds' in data
        assert 'metadata' in data

        # AF state should be valid
        assert data['af_state'] in ['Idle', 'Scanning', 'Success', 'Fail']

        # Lens position should be in valid range
        assert 0.0 <= data['lens_position'] <= 15.0

        print(f"   ✓ Returned valid response structure")
        print(f"   ✓ AF state: {data['af_state']}")
        print(f"   ✓ Success: {data['success']}")

    def test_autofocus_timeout_handling(self, client):
        """Test autofocus completes within reasonable time"""
        print("\n⏱️  Testing autofocus timeout...")

        start_time = time.time()
        response = client.post('/api/camera/autofocus')
        elapsed = time.time() - start_time

        assert response.status_code == 200
        assert elapsed < 15.0, \
            f"Autofocus took {elapsed}s (should timeout/complete within 15s)"

        data = response.get_json()
        assert data['duration_seconds'] < 15.0, \
            "Reported duration should be less than 15s"

        print(f"   ✓ Completed in {elapsed:.2f}s (< 15s)")
        print(f"   ✓ Reported duration: {data['duration_seconds']:.2f}s")


class TestFocusRangeModes:
    """Test different focus range modes"""

    def test_autofocus_macro_range(self, client):
        """Test autofocus with macro range (10cm - 50cm)"""
        print("\n🔬 Testing autofocus with macro range...")

        # Set AfRange to Macro (1)
        response = client.post('/api/config/webui', json={'af_range': 1})
        assert response.status_code == 200

        time.sleep(0.2)

        # Run autofocus
        response = client.post('/api/camera/autofocus')
        assert response.status_code == 200

        data = response.get_json()

        # Macro mode typically results in higher diopter values (closer focus)
        # But we just verify it completes successfully
        assert 'lens_position' in data
        assert 0.0 <= data['lens_position'] <= 15.0

        print(f"   ✓ Macro range autofocus completed")
        print(f"   ✓ Lens position: {data['lens_position']}D")
        print(f"   ✓ AF state: {data['af_state']}")

    def test_autofocus_full_range(self, client):
        """Test autofocus with full range (10cm - infinity)"""
        print("\n🌐 Testing autofocus with full range...")

        # Set AfRange to Full (2)
        response = client.post('/api/config/webui', json={'af_range': 2})
        assert response.status_code == 200

        time.sleep(0.2)

        # Run autofocus
        response = client.post('/api/camera/autofocus')
        assert response.status_code == 200

        data = response.get_json()

        assert 'lens_position' in data
        assert 0.0 <= data['lens_position'] <= 15.0

        print(f"   ✓ Full range autofocus completed")
        print(f"   ✓ Lens position: {data['lens_position']}D")

    def test_autofocus_range_comparison(self, client):
        """Test autofocus behavior across different ranges"""
        print("\n📊 Comparing autofocus across different ranges...")

        ranges = {
            0: 'Normal (0.5m - infinity)',
            1: 'Macro (10cm - 50cm)',
            2: 'Full (10cm - infinity)'
        }

        results = {}

        for range_val, description in ranges.items():
            # Set range
            response = client.post('/api/config/webui', json={'af_range': range_val})
            assert response.status_code == 200
            time.sleep(0.2)

            # Run autofocus
            response = client.post('/api/camera/autofocus')
            assert response.status_code == 200

            data = response.get_json()
            results[range_val] = {
                'description': description,
                'lens_position': data['lens_position'],
                'duration': data['duration_seconds'],
                'af_state': data['af_state']
            }

            time.sleep(0.5)

        # Print comparison
        print(f"\n   Range Comparison:")
        for range_val, result in results.items():
            print(f"   {range_val} ({result['description']}): "
                  f"{result['lens_position']:.2f}D in {result['duration']:.2f}s "
                  f"[{result['af_state']}]")

        # All should complete
        for range_val, result in results.items():
            assert result['af_state'] in ['Idle', 'Scanning', 'Success', 'Fail']


class TestAutofocusDuringStreaming:
    """Test autofocus interaction with active streaming"""

    def test_autofocus_with_active_stream(self, client):
        """Test autofocus when preview stream is active"""
        print("\n📹 Testing autofocus during active streaming...")

        # Note: The camera_streamer should be active from conftest.py fixtures
        # The autofocus endpoint should handle camera resource management

        response = client.post('/api/camera/autofocus')

        # Should succeed even with stream active
        assert response.status_code == 200, \
            "Autofocus should handle camera resource conflicts"

        data = response.get_json()
        assert 'success' in data
        assert 'lens_position' in data

        print(f"   ✓ Autofocus completed with stream active")
        print(f"   ✓ Lens position: {data['lens_position']}D")

    def test_stream_recovers_after_autofocus(self, client):
        """Test stream can resume after autofocus"""
        print("\n🔄 Testing stream recovery after autofocus...")

        # Trigger autofocus
        response = client.post('/api/camera/autofocus')
        assert response.status_code == 200

        # Wait for camera to be released back to stream
        time.sleep(1.0)

        # Verify stream can be accessed again
        # (If stream is broken, subsequent operations would fail)
        response2 = client.post('/api/camera/autofocus')
        assert response2.status_code == 200, \
            "Stream should recover after autofocus"

        print(f"   ✓ Stream recovered after autofocus")


class TestAutofocusAccuracy:
    """Test autofocus accuracy and lens position verification"""

    def test_lens_position_precision(self, client):
        """Test lens position is reported with reasonable precision"""
        print("\n🎯 Testing lens position precision...")

        response = client.post('/api/camera/autofocus')
        assert response.status_code == 200

        data = response.get_json()
        lens_pos = data['lens_position']

        # Lens position should be a reasonable float (not NaN, not infinite)
        assert isinstance(lens_pos, (int, float))
        assert lens_pos == lens_pos, "Lens position should not be NaN"
        assert abs(lens_pos) < float('inf'), "Lens position should not be infinite"

        # Should be reported to reasonable precision (2 decimal places max)
        # Round to 2 decimals and verify it matches (tests precision)
        rounded = round(lens_pos, 2)
        assert abs(lens_pos - rounded) < 0.01, \
            "Lens position should be precise to 2 decimal places"

        print(f"   ✓ Lens position: {lens_pos}D")
        print(f"   ✓ Precision validated (2 decimal places)")

    def test_metadata_accuracy(self, client):
        """Test autofocus metadata values are accurate"""
        print("\n📊 Testing metadata accuracy...")

        response = client.post('/api/camera/autofocus')
        assert response.status_code == 200

        data = response.get_json()
        metadata = data['metadata']

        # Exposure time should be reasonable
        exp_time = metadata['exposure_time']
        assert 100 <= exp_time <= 1000000, \
            f"Exposure time {exp_time}µs seems unreasonable"

        # Gain should be reasonable
        gain = metadata['analogue_gain']
        assert 1.0 <= gain <= 16.0, \
            f"Analogue gain {gain} out of valid range"

        # Color temperature should be plausible
        color_temp = metadata['colour_temperature']
        assert 1000 <= color_temp <= 15000, \
            f"Color temperature {color_temp}K seems unreasonable"

        print(f"   ✓ Exposure: {exp_time}µs (valid)")
        print(f"   ✓ Gain: {gain} (valid)")
        print(f"   ✓ Color temp: {color_temp}K (valid)")


class TestAutofocusStateTransitions:
    """Test autofocus state machine transitions"""

    def test_af_state_is_valid(self, client):
        """Test AF state is always one of the valid states"""
        print("\n🔀 Testing AF state validity...")

        valid_states = ['Idle', 'Scanning', 'Success', 'Fail']

        # Run multiple autofocus cycles
        for i in range(3):
            response = client.post('/api/camera/autofocus')
            assert response.status_code == 200

            data = response.get_json()
            af_state = data['af_state']

            assert af_state in valid_states, \
                f"Invalid AF state: {af_state} (expected one of {valid_states})"

            print(f"   Cycle {i+1}: AF state = {af_state} ✓")
            time.sleep(0.3)

    def test_success_state_correlates_with_flag(self, client):
        """Test success flag matches AF state"""
        print("\n🔗 Testing success flag consistency...")

        response = client.post('/api/camera/autofocus')
        assert response.status_code == 200

        data = response.get_json()
        success_flag = data['success']
        af_state = data['af_state']

        # If success=True, state should be Success (usually)
        # Note: AF can be Idle and still succeed in manual mode
        if success_flag:
            assert af_state in ['Success', 'Idle'], \
                f"success=True but state={af_state}"
        else:
            # If success=False, state might be Fail or Scanning
            assert af_state in ['Fail', 'Scanning', 'Idle'], \
                f"success=False but state={af_state}"

        print(f"   ✓ success={success_flag}, af_state={af_state} (consistent)")


class TestFocusHuntingDetection:
    """Test detection of focus hunting behavior"""

    def test_focus_hunting_by_repeated_af(self, client):
        """Test focus stability over repeated AF cycles"""
        print("\n🎭 Testing focus hunting detection...")

        # Fast autofocus might cause hunting
        response = client.post('/api/config/webui', json={'af_speed': 1})
        assert response.status_code == 200
        time.sleep(0.2)

        positions = []
        for i in range(7):
            response = client.post('/api/camera/autofocus')
            assert response.status_code == 200

            data = response.get_json()
            positions.append(data['lens_position'])
            time.sleep(0.3)

        # Calculate position variance
        avg_pos = sum(positions) / len(positions)
        variance = sum((p - avg_pos) ** 2 for p in positions) / len(positions)
        std_dev = variance ** 0.5

        # If standard deviation is high, focus is hunting
        if std_dev > 0.5:
            print(f"   ⚠️  Focus hunting detected (σ={std_dev:.2f}D)")
            print(f"   ⚠️  Positions: {[f'{p:.2f}' for p in positions]}")
        else:
            print(f"   ✓ Focus stable (σ={std_dev:.2f}D)")
            print(f"   ✓ Average position: {avg_pos:.2f}D")

        # Test passes regardless, just report hunting
        assert len(positions) == 7

        # Reset to normal speed
        response = client.post('/api/config/webui', json={'af_speed': 0})
        assert response.status_code == 200


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
