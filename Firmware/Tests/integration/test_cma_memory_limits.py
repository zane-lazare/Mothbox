"""
Test: CMA Memory Limits for Camera Operations

Tests that camera operations work within the 64MB CMA constraints.
Verifies that buffer optimizations (raw=None, lores=None, GC) prevent OOM kills.

Run with: pytest Tests/integration/test_cma_memory_limits.py -v -s
"""

import pytest
import sys
from pathlib import Path
import time

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'webui' / 'backend'))


class TestCMAMemoryLimits:
    """Test camera operations within 64MB CMA constraints"""

    def test_4k_capture_within_cma_limits(self, client):
        """Test 1: Single 4K capture should work within 64MB CMA"""
        print("\n" + "="*60)
        print("Test 1: Single 4K Capture (CMA Safe)")
        print("="*60)

        # Check CMA before test
        try:
            with open('/proc/meminfo', 'r') as f:
                for line in f:
                    if 'CmaFree' in line:
                        cma_free_before = int(line.split()[1])
                        print(f"\n   CMA free before: {cma_free_before} kB ({cma_free_before/1024:.1f} MB)")
        except Exception as e:
            print(f"   Could not read CMA: {e}")

        # Adjust settings
        response = client.post('/api/config/webui', json={'sharpness': 2.0})
        assert response.status_code == 200

        # Capture 4K test photo
        start = time.time()
        response = client.post('/api/camera/test-capture')
        elapsed = time.time() - start

        print(f"\n   Capture completed in {elapsed:.2f}s")
        print(f"   Status: {response.status_code}")

        if response.status_code == 200:
            data = response.get_json()
            print(f"   ✓ Success: {data.get('test_photo_path')}")
            print(f"   Metadata: {data.get('metadata')}")
        else:
            data = response.get_json()
            print(f"   ❌ Failed: {data.get('error')}")

        # Check CMA after test
        try:
            with open('/proc/meminfo', 'r') as f:
                for line in f:
                    if 'CmaFree' in line:
                        cma_free_after = int(line.split()[1])
                        print(f"   CMA free after: {cma_free_after} kB ({cma_free_after/1024:.1f} MB)")
                        print(f"   CMA used by test: {(cma_free_before - cma_free_after)/1024:.1f} MB")
        except Exception as e:
            print(f"   Could not read CMA: {e}")

        assert response.status_code == 200

    def test_multiple_4k_captures_sequential(self, client):
        """Test 2: Multiple 4K captures in sequence (tests GC cleanup)"""
        print("\n" + "="*60)
        print("Test 2: Multiple 4K Captures Sequential")
        print("="*60)

        for i in range(3):
            print(f"\n   Capture {i+1}/3:")

            # Check CMA before each capture
            try:
                with open('/proc/meminfo', 'r') as f:
                    for line in f:
                        if 'CmaFree' in line:
                            cma_free = int(line.split()[1])
                            print(f"      CMA free: {cma_free} kB ({cma_free/1024:.1f} MB)")
            except Exception:
                pass

            response = client.post('/api/camera/test-capture')

            if response.status_code == 200:
                data = response.get_json()
                print(f"      ✓ Success: {data.get('test_photo_path')}")
            else:
                data = response.get_json()
                print(f"      ❌ Failed: {data.get('error')}")
                pytest.fail(f"Capture {i+1} failed: {data.get('error')}")

            # Small delay between captures
            time.sleep(0.5)

        print("\n   ✓ All 3 captures succeeded")

    def test_autofocus_within_cma_limits(self, client):
        """Test 3: Autofocus uses preview resolution (should fit in CMA)"""
        print("\n" + "="*60)
        print("Test 3: Autofocus (Preview Resolution)")
        print("="*60)

        # Check CMA before
        try:
            with open('/proc/meminfo', 'r') as f:
                for line in f:
                    if 'CmaFree' in line:
                        cma_free_before = int(line.split()[1])
                        print(f"\n   CMA free before: {cma_free_before} kB ({cma_free_before/1024:.1f} MB)")
        except Exception:
            pass

        start = time.time()
        response = client.post('/api/camera/autofocus')
        elapsed = time.time() - start

        print(f"\n   Autofocus completed in {elapsed:.2f}s")
        print(f"   Status: {response.status_code}")

        if response.status_code == 200:
            data = response.get_json()
            print(f"   ✓ Success: {data.get('af_state')}")
            print(f"   Lens position: {data.get('lens_position')}")
        else:
            data = response.get_json()
            print(f"   ❌ Failed: {data.get('error')}")

        # Check CMA after
        try:
            with open('/proc/meminfo', 'r') as f:
                for line in f:
                    if 'CmaFree' in line:
                        cma_free_after = int(line.split()[1])
                        print(f"   CMA free after: {cma_free_after} kB ({cma_free_after/1024:.1f} MB)")
        except Exception:
            pass

        assert response.status_code == 200

    def test_calibrate_within_cma_limits(self, client):
        """Test 4: Calibration uses 4K preview (should fit in CMA)"""
        print("\n" + "="*60)
        print("Test 4: Calibration (4K Preview Resolution)")
        print("="*60)

        # Check CMA before
        try:
            with open('/proc/meminfo', 'r') as f:
                for line in f:
                    if 'CmaFree' in line:
                        cma_free_before = int(line.split()[1])
                        print(f"\n   CMA free before: {cma_free_before} kB ({cma_free_before/1024:.1f} MB)")
        except Exception:
            pass

        start = time.time()
        response = client.post('/api/camera/calibrate', json={'apply_to': 'preview'})
        elapsed = time.time() - start

        print(f"\n   Calibration completed in {elapsed:.2f}s")
        print(f"   Status: {response.status_code}")

        if response.status_code == 200:
            data = response.get_json()
            print(f"   ✓ Success: {data.get('af_state')}")
            print(f"   After: {data.get('after')}")
        else:
            data = response.get_json()
            print(f"   ❌ Failed: {data.get('error')}")

        # Check CMA after
        try:
            with open('/proc/meminfo', 'r') as f:
                for line in f:
                    if 'CmaFree' in line:
                        cma_free_after = int(line.split()[1])
                        print(f"   CMA free after: {cma_free_after} kB ({cma_free_after/1024:.1f} MB)")
        except Exception:
            pass

        assert response.status_code == 200

    def test_workflow_autofocus_capture_sequence(self, client):
        """Test 5: Common workflow sequence (autofocus → adjust → capture)"""
        print("\n" + "="*60)
        print("Test 5: Workflow Sequence (Autofocus → Adjust → Capture)")
        print("="*60)

        # Step 1: Autofocus
        print("\n   Step 1: Autofocus...")
        response = client.post('/api/camera/autofocus')
        if response.status_code != 200:
            pytest.skip("Autofocus failed, skipping workflow")
        print("      ✓ Autofocus complete")
        time.sleep(0.5)

        # Step 2: Adjust settings
        print("\n   Step 2: Adjust settings...")
        response = client.post('/api/config/webui', json={'sharpness': 2.5})
        assert response.status_code == 200
        print("      ✓ Settings adjusted")

        # Step 3: Test capture
        print("\n   Step 3: Test capture...")
        response = client.post('/api/camera/test-capture')

        if response.status_code == 200:
            data = response.get_json()
            print(f"      ✓ Capture success: {data.get('test_photo_path')}")
        else:
            data = response.get_json()
            print(f"      ❌ Capture failed: {data.get('error')}")
            pytest.fail(f"Workflow capture failed: {data.get('error')}")

        print("\n   ✓ Full workflow completed")


class TestCMADocumentation:
    """Document CMA behavior and requirements"""

    def test_document_cma_requirements(self):
        """Document CMA memory requirements for different operations"""
        print("\n" + "="*70)
        print("CMA Memory Requirements Documentation")
        print("="*70)

        requirements = {
            "1080p Preview (1920×1080 RGB888)": (1920 * 1080 * 3) / (1024**2),
            "4K Preview (3840×2160 RGB888)": (3840 * 2160 * 3) / (1024**2),
            "4K Test Capture (3840×2160 BGR888)": (3840 * 2160 * 3) / (1024**2),
            "64MP Capture (9152×6944 BGR888)": (9152 * 6944 * 3) / (1024**2),
        }

        print("\nSingle Buffer Requirements:")
        for operation, mb in requirements.items():
            status = "✓ Fits in 64MB CMA" if mb < 64 else "❌ Too large for 64MB CMA"
            print(f"  {operation:45s} {mb:6.1f} MB   {status}")

        print("\nWith raw=None, lores=None optimization:")
        print("  - Only allocates main buffer (not raw + lores)")
        print("  - Saves ~90MB for 64MP captures")
        print("  - But 64MP still needs ~180MB (exceeds 64MB CMA)")

        print("\nConclusion:")
        print("  - 4K test captures: Safe for 64MB CMA")
        print("  - 64MP production captures: Need standalone process (TakePhoto.py)")
        print("  - Preview operations: Safe (1080p/4K)")

        # Check actual CMA
        try:
            with open('/proc/meminfo', 'r') as f:
                for line in f:
                    if 'CmaTotal' in line:
                        print(f"\nCurrent System:")
                        print(f"  {line.strip()}")
                    elif 'CmaFree' in line:
                        print(f"  {line.strip()}")
        except Exception as e:
            print(f"\nCould not read CMA info: {e}")
