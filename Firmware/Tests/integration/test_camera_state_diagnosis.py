"""
Diagnostic Test: Camera State Investigation

This test investigates camera initialization failures in workflow tests.
Tests the theory that rapid camera reinit causes failures.

Run with: pytest Tests/integration/test_camera_state_diagnosis.py -v -s
"""

import pytest
import sys
from pathlib import Path
import time

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'webui' / 'backend'))


@pytest.mark.photo
class TestCameraStateTheory:
    """Test camera initialization patterns to diagnose workflow failures"""

    def test_camera_global_info(self):
        """Test 1: Check camera availability before initialization"""
        print("\n" + "="*60)
        print("Test 1: Camera Global Info Check")
        print("="*60)

        try:
            from picamera2 import Picamera2

            # Check what cameras are available
            print("\n📹 Checking global camera info...")
            camera_info = Picamera2.global_camera_info()
            print(f"   Available cameras: {camera_info}")

            if not camera_info:
                print("   ⚠ No cameras detected!")
                return

            print(f"   ✓ Found {len(camera_info)} camera(s)")

        except Exception as e:
            print(f"   ❌ Error: {e}")
            import traceback
            print(traceback.format_exc())

    def test_rapid_init_release_cycle(self):
        """Test 2: Rapid camera init/release cycle (mimics test suite)"""
        print("\n" + "="*60)
        print("Test 2: Rapid Init/Release Cycle")
        print("="*60)

        try:
            from picamera2 import Picamera2

            for i in range(5):
                print(f"\n🔄 Cycle {i+1}/5:")
                start_time = time.time()

                try:
                    # Try to init camera 0
                    print(f"   Initializing camera 0...")
                    picam2 = Picamera2(0)
                    init_time = time.time() - start_time
                    print(f"   ✓ Init succeeded in {init_time:.3f}s")

                    # Configure
                    config = picam2.create_preview_configuration(
                        main={'format': 'RGB888', 'size': (1920, 1080)}
                    )
                    picam2.configure(config)

                    # Start/stop
                    picam2.start()
                    time.sleep(0.1)
                    picam2.stop()
                    picam2.close()

                    close_time = time.time() - start_time
                    print(f"   ✓ Full cycle in {close_time:.3f}s")

                    # Wait 0.5s like the current code does
                    print(f"   Waiting 0.5s before next cycle...")
                    time.sleep(0.5)

                except Exception as e:
                    print(f"   ❌ FAILED on cycle {i+1}: {e}")
                    print(f"   Time before failure: {time.time() - start_time:.3f}s")
                    break

        except Exception as e:
            print(f"❌ Test error: {e}")
            import traceback
            print(traceback.format_exc())

    def test_init_with_increasing_delays(self):
        """Test 3: Camera init with increasing delays between cycles"""
        print("\n" + "="*60)
        print("Test 3: Init with Increasing Delays")
        print("="*60)

        try:
            from picamera2 import Picamera2

            delays = [0.5, 1.0, 1.5, 2.0]

            for delay in delays:
                print(f"\n⏱️  Testing with {delay}s delay:")

                for attempt in range(3):
                    try:
                        picam2 = Picamera2(0)
                        config = picam2.create_preview_configuration(
                            main={'format': 'RGB888', 'size': (1920, 1080)}
                        )
                        picam2.configure(config)
                        picam2.start()
                        time.sleep(0.1)
                        picam2.stop()
                        picam2.close()

                        print(f"   ✓ Attempt {attempt+1}/3 succeeded")
                        time.sleep(delay)

                    except Exception as e:
                        print(f"   ❌ Attempt {attempt+1}/3 FAILED: {e}")
                        break

        except Exception as e:
            print(f"❌ Test error: {e}")
            import traceback
            print(traceback.format_exc())

    def test_check_device_file_availability(self):
        """Test 4: Check /dev/video0 availability"""
        print("\n" + "="*60)
        print("Test 4: Device File Availability")
        print("="*60)

        import os
        import subprocess

        print("\n📂 Checking /dev/video* devices...")

        # List video devices
        try:
            result = subprocess.run(
                ['ls', '-la', '/dev/video*'],
                capture_output=True,
                text=True,
                timeout=5
            )
            print(f"   Video devices:\n{result.stdout}")
        except Exception as e:
            print(f"   ⚠ Could not list devices: {e}")

        # Check lsof on video devices
        print("\n🔍 Checking if any process has video devices open...")
        try:
            result = subprocess.run(
                ['lsof', '/dev/video0'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.stdout:
                print(f"   Processes using /dev/video0:\n{result.stdout}")
            else:
                print(f"   ✓ No processes have /dev/video0 open")
        except Exception as e:
            print(f"   (lsof check skipped: {e})")

    def test_workflow_1_simulation(self, client):
        """Test 5: Simulate exact Workflow 1 sequence"""
        print("\n" + "="*60)
        print("Test 5: Workflow 1 Simulation")
        print("="*60)

        # This simulates the exact sequence from test_end_to_end_workflows.py

        # Step 1: Set preview settings
        print("\n📝 Step 1: Set preview settings...")
        response = client.post('/api/config/webui', json={
            'sharpness': 2.5,
            'brightness': 0.2,
        })
        print(f"   Status: {response.status_code}")

        # Step 2: Test capture (where it likely fails)
        print("\n📸 Step 2: Test capture...")
        start_time = time.time()

        try:
            response = client.post('/api/camera/test-capture')
            elapsed = time.time() - start_time

            print(f"   Status: {response.status_code}")
            print(f"   Response time: {elapsed:.3f}s")

            if response.status_code == 200:
                data = response.get_json()
                print(f"   ✓ Success: {data.get('test_photo_path')}")
            else:
                data = response.get_json()
                print(f"   ❌ Failed: {data.get('error')}")

        except Exception as e:
            elapsed = time.time() - start_time
            print(f"   ❌ Exception after {elapsed:.3f}s: {e}")

    def test_workflow_2_simulation(self, client):
        """Test 6: Simulate exact Workflow 2 sequence"""
        print("\n" + "="*60)
        print("Test 6: Workflow 2 Simulation (Autofocus → Calibrate → Capture)")
        print("="*60)

        # Step 1: Autofocus
        print("\n🔍 Step 1: Autofocus...")
        start_time = time.time()

        response = client.post('/api/camera/autofocus')
        elapsed = time.time() - start_time

        print(f"   Status: {response.status_code} (took {elapsed:.3f}s)")

        if response.status_code != 200:
            print(f"   ⚠ Autofocus failed, stopping here")
            return

        # Check camera availability after autofocus
        print("\n🔍 Checking camera availability after autofocus...")
        try:
            from picamera2 import Picamera2
            info = Picamera2.global_camera_info()
            print(f"   Camera info: {info}")
        except Exception as e:
            print(f"   ⚠ Error checking camera: {e}")

        # Wait like workflow does
        print("\n⏱️  Waiting 1s (like workflow)...")
        time.sleep(1)

        # Step 2: Calibrate
        print("\n⚙️ Step 2: Calibrate...")
        start_time = time.time()

        response = client.post('/api/camera/calibrate', json={
            'apply_to': 'capture'
        })
        elapsed = time.time() - start_time

        print(f"   Status: {response.status_code} (took {elapsed:.3f}s)")

        if response.status_code != 200:
            print(f"   ⚠ Calibration failed")
            data = response.get_json()
            print(f"   Error: {data.get('error')}")
            return

        # Check camera availability after calibration
        print("\n🔍 Checking camera availability after calibration...")
        try:
            from picamera2 import Picamera2
            info = Picamera2.global_camera_info()
            print(f"   Camera info: {info}")
        except Exception as e:
            print(f"   ⚠ Error checking camera: {e}")

        # Step 3: Test capture (where it likely crashes)
        print("\n📸 Step 3: Test capture...")
        start_time = time.time()

        try:
            response = client.post('/api/camera/test-capture')
            elapsed = time.time() - start_time

            print(f"   Status: {response.status_code} (took {elapsed:.3f}s)")

            if response.status_code == 200:
                data = response.get_json()
                print(f"   ✓ Success: {data.get('test_photo_path')}")
            else:
                data = response.get_json()
                print(f"   ❌ Failed: {data.get('error')}")

        except Exception as e:
            elapsed = time.time() - start_time
            print(f"   ❌ Exception after {elapsed:.3f}s: {e}")
            import traceback
            print(traceback.format_exc())

    def test_camera_init_retry_pattern(self):
        """Test 7: Test if retry pattern helps with initialization"""
        print("\n" + "="*60)
        print("Test 7: Camera Init with Retry Pattern")
        print("="*60)

        try:
            from picamera2 import Picamera2

            # First, stress the camera with rapid cycles
            print("\n📹 Stressing camera with rapid cycles...")
            for i in range(3):
                try:
                    picam2 = Picamera2(0)
                    config = picam2.create_preview_configuration(
                        main={'format': 'RGB888', 'size': (1920, 1080)}
                    )
                    picam2.configure(config)
                    picam2.start()
                    time.sleep(0.1)
                    picam2.stop()
                    picam2.close()
                    time.sleep(0.3)  # Very short delay
                except Exception as e:
                    print(f"   ⚠ Cycle {i+1} failed: {e}")

            # Now try to init with retry pattern
            print("\n🔄 Testing retry pattern after stress...")

            def init_with_retry(max_attempts=3):
                """Try to initialize camera with exponential backoff"""
                for attempt in range(max_attempts):
                    try:
                        print(f"   Attempt {attempt+1}/{max_attempts}...")
                        picam2 = Picamera2(0)
                        print(f"   ✓ Success on attempt {attempt+1}")
                        return picam2
                    except Exception as e:
                        if attempt < max_attempts - 1:
                            delay = 0.5 * (attempt + 1)  # 0.5s, 1.0s, 1.5s
                            print(f"   ❌ Failed: {e}")
                            print(f"   Waiting {delay}s before retry...")
                            time.sleep(delay)
                        else:
                            print(f"   ❌ All attempts failed!")
                            raise

            picam2 = init_with_retry()
            picam2.close()

            print("\n✅ Retry pattern succeeded!")

        except Exception as e:
            print(f"\n❌ Retry pattern failed: {e}")
            import traceback
            print(traceback.format_exc())


@pytest.mark.photo
class TestCameraReleaseDelay:
    """Test different release delays to find optimal value"""

    def test_optimal_release_delay(self, app):
        """Test 8: Find optimal delay after camera release"""
        print("\n" + "="*60)
        print("Test 8: Finding Optimal Release Delay")
        print("="*60)

        try:
            from picamera2 import Picamera2
            camera_streamer = app.config.get('CAMERA_STREAMER')

            if not camera_streamer:
                print("   ⚠ No camera streamer available")
                return

            delays = [0.3, 0.5, 0.7, 1.0, 1.5]

            for delay in delays:
                print(f"\n⏱️  Testing {delay}s delay:")

                success_count = 0
                attempts = 3

                for attempt in range(attempts):
                    try:
                        # Simulate the release pattern from routes/camera.py
                        if camera_streamer.camera:
                            camera_streamer.release_camera()
                            time.sleep(delay)

                        # Try to init
                        picam2 = Picamera2(0)
                        config = picam2.create_preview_configuration(
                            main={'format': 'RGB888', 'size': (1920, 1080)}
                        )
                        picam2.configure(config)
                        picam2.start()
                        time.sleep(0.1)
                        picam2.stop()
                        picam2.close()

                        success_count += 1
                        print(f"   ✓ Attempt {attempt+1}/{attempts} succeeded")

                        time.sleep(0.5)

                    except Exception as e:
                        print(f"   ❌ Attempt {attempt+1}/{attempts} failed: {e}")

                print(f"   Result: {success_count}/{attempts} succeeded with {delay}s delay")

                if success_count == attempts:
                    print(f"   🎯 {delay}s delay appears optimal!")
                    break

        except Exception as e:
            print(f"❌ Test error: {e}")
            import traceback
            print(traceback.format_exc())
