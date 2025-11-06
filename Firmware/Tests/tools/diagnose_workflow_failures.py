#!/usr/bin/env python3
"""
Diagnostic Script: Analyze Workflow Test Failures

This script analyzes the test code to identify patterns that might cause failures.
Can be run without hardware.

Usage:
    python3 Tests/diagnose_workflow_failures.py
"""

import re
from pathlib import Path
from collections import defaultdict


def analyze_test_file(file_path):
    """Analyze a test file for camera operation patterns"""
    print(f"\n{'='*70}")
    print(f"Analyzing: {file_path.name}")
    print(f"{'='*70}")

    with open(file_path, 'r') as f:
        content = f.read()

    # Find all test functions
    test_functions = re.findall(r'def (test_\w+)\(.*?\):', content)
    print(f"\nFound {len(test_functions)} test functions")

    # Track API calls per test
    api_patterns = {
        'test-capture': r"client\.post\('/api/camera/test-capture'\)",
        'autofocus': r"client\.post\('/api/camera/autofocus'\)",
        'calibrate': r"client\.post\('/api/camera/calibrate'",
        'config/webui': r"client\.post\('/api/config/webui'",
        'copy-settings': r"client\.post\('/api/config/copy-settings'",
    }

    # Analyze each test function
    lines = content.split('\n')
    test_starts = []
    for i, line in enumerate(lines):
        if line.strip().startswith('def test_'):
            test_starts.append(i)

    for idx, start in enumerate(test_starts):
        # Get test content (until next test or end of class)
        end = test_starts[idx + 1] if idx + 1 < len(test_starts) else len(lines)
        test_content = '\n'.join(lines[start:end])

        # Extract test name
        match = re.search(r'def (test_\w+)', test_content)
        if not match:
            continue
        test_name = match.group(1)

        # Count API calls
        api_calls = []
        for api_name, pattern in api_patterns.items():
            matches = re.findall(pattern, test_content)
            for _ in matches:
                api_calls.append(api_name)

        # Count time.sleep() calls
        sleep_calls = re.findall(r'time\.sleep\(([\d.]+)\)', test_content)
        sleep_total = sum(float(s) for s in sleep_calls)

        # Check for early returns (camera busy handling)
        has_early_return = 'status_code != 200' in test_content and 'return' in test_content

        if api_calls:
            print(f"\n  📝 {test_name}")
            print(f"     Camera operations: {len([c for c in api_calls if c in ['test-capture', 'autofocus', 'calibrate']])}")
            print(f"     Sequence: {' → '.join(api_calls[:5])}")
            if sleep_total > 0:
                print(f"     Total sleep time: {sleep_total}s")
            if has_early_return:
                print(f"     ⚠️  Has early return for busy camera")


def analyze_camera_routes():
    """Analyze camera.py routes for sleep delays"""
    print(f"\n{'='*70}")
    print(f"Analyzing: routes/camera.py - Camera Operation Delays")
    print(f"{'='*70}")

    routes_file = Path(__file__).parent.parent.parent / 'webui' / 'backend' / 'routes' / 'camera.py'

    if not routes_file.exists():
        print("❌ routes/camera.py not found")
        return

    with open(routes_file, 'r') as f:
        lines = f.readlines()

    # Find release_camera() calls and subsequent sleeps
    routes = ['test-capture', 'autofocus', 'calibrate']

    for route in routes:
        print(f"\n  🔍 Analyzing /{route} endpoint:")

        # Find the route definition
        route_start = None
        for i, line in enumerate(lines):
            if f"'{route}'" in line and '@camera_bp.route' in line:
                route_start = i
                break

        if route_start is None:
            print(f"     ❌ Route not found")
            continue

        # Look for release_camera and sleep patterns in next 100 lines
        found_release = False
        sleep_after_release = None

        for i in range(route_start, min(route_start + 100, len(lines))):
            line = lines[i]

            if 'release_camera()' in line and not found_release:
                found_release = True
                print(f"     ✓ Found release_camera() at line {i+1}")

            if found_release and not sleep_after_release:
                sleep_match = re.search(r'time\.sleep\(([\d.]+)\)', line)
                if sleep_match:
                    sleep_after_release = float(sleep_match.group(1))
                    print(f"     ⏱️  Sleep delay: {sleep_after_release}s at line {i+1}")
                    break

        if found_release and sleep_after_release:
            if sleep_after_release < 1.0:
                print(f"     ⚠️  WARNING: Delay of {sleep_after_release}s may be too short!")
        elif found_release:
            print(f"     ⚠️  WARNING: No sleep found after release_camera()!")


def compare_test_patterns():
    """Compare patterns between passing and failing tests"""
    print(f"\n{'='*70}")
    print(f"Pattern Comparison: Passing vs Failing Tests")
    print(f"{'='*70}")

    tests_dir = Path(__file__).parent / 'integration'

    # Analyze test_test_capture_workflows.py (passing)
    passing_file = tests_dir / 'test_test_capture_workflows.py'
    # Analyze test_end_to_end_workflows.py (failing)
    failing_file = tests_dir / 'test_end_to_end_workflows.py'

    print("\n📊 Comparison:")
    print(f"\n  ✅ PASSING: {passing_file.name}")

    if passing_file.exists():
        with open(passing_file, 'r') as f:
            passing_content = f.read()

        # Count operations
        passing_test_captures = len(re.findall(r"client\.post\('/api/camera/test-capture'\)", passing_content))
        passing_autofocus = len(re.findall(r"client\.post\('/api/camera/autofocus'\)", passing_content))
        passing_calibrate = len(re.findall(r"client\.post\('/api/camera/calibrate'", passing_content))

        print(f"     test-capture calls: {passing_test_captures}")
        print(f"     autofocus calls: {passing_autofocus}")
        print(f"     calibrate calls: {passing_calibrate}")
        print(f"     Total camera ops: {passing_test_captures + passing_autofocus + passing_calibrate}")

    print(f"\n  ❌ FAILING: {failing_file.name}")

    if failing_file.exists():
        with open(failing_file, 'r') as f:
            failing_content = f.read()

        # Count operations
        failing_test_captures = len(re.findall(r"client\.post\('/api/camera/test-capture'\)", failing_content))
        failing_autofocus = len(re.findall(r"client\.post\('/api/camera/autofocus'\)", failing_content))
        failing_calibrate = len(re.findall(r"client\.post\('/api/camera/calibrate'", failing_content))

        print(f"     test-capture calls: {failing_test_captures}")
        print(f"     autofocus calls: {failing_autofocus}")
        print(f"     calibrate calls: {failing_calibrate}")
        print(f"     Total camera ops: {failing_test_captures + failing_autofocus + failing_calibrate}")

        # Look for complex sequences (multiple camera ops in one test)
        lines = failing_content.split('\n')
        test_starts = []
        for i, line in enumerate(lines):
            if line.strip().startswith('def test_'):
                test_starts.append(i)

        complex_tests = []
        for idx, start in enumerate(test_starts):
            end = test_starts[idx + 1] if idx + 1 < len(test_starts) else len(lines)
            test_content = '\n'.join(lines[start:end])

            # Count camera operations in this test
            ops = 0
            ops += len(re.findall(r"client\.post\('/api/camera/test-capture'\)", test_content))
            ops += len(re.findall(r"client\.post\('/api/camera/autofocus'\)", test_content))
            ops += len(re.findall(r"client\.post\('/api/camera/calibrate'", test_content))

            if ops >= 2:
                match = re.search(r'def (test_\w+)', test_content)
                if match:
                    complex_tests.append((match.group(1), ops))

        if complex_tests:
            print(f"\n     ⚠️  Complex tests (multiple camera ops):")
            for test_name, op_count in complex_tests:
                print(f"        - {test_name}: {op_count} operations")


def print_recommendations():
    """Print diagnostic recommendations"""
    print(f"\n{'='*70}")
    print(f"Diagnostic Recommendations")
    print(f"{'='*70}")

    print("""
To test the theories, run these commands on your Raspberry Pi:

1. Test camera availability check:
   pytest Tests/integration/test_camera_state_diagnosis.py::TestCameraStateTheory::test_camera_global_info -v -s

2. Test rapid initialization pattern:
   pytest Tests/integration/test_camera_state_diagnosis.py::TestCameraStateTheory::test_rapid_init_release_cycle -v -s

3. Simulate Workflow 1 exactly:
   pytest Tests/integration/test_camera_state_diagnosis.py::TestCameraStateTheory::test_workflow_1_simulation -v -s

4. Simulate Workflow 2 exactly (autofocus → calibrate → capture):
   pytest Tests/integration/test_camera_state_diagnosis.py::TestCameraStateTheory::test_workflow_2_simulation -v -s

5. Test retry pattern effectiveness:
   pytest Tests/integration/test_camera_state_diagnosis.py::TestCameraStateTheory::test_camera_init_retry_pattern -v -s

6. Find optimal release delay:
   pytest Tests/integration/test_camera_state_diagnosis.py::TestCameraReleaseDelay::test_optimal_release_delay -v -s

The output will show:
- Exact timing when failures occur
- Whether camera is available between operations
- If longer delays or retry patterns help
- The optimal delay duration

Look for patterns like:
  ❌ FAILED on cycle X          → Camera exhaustion confirmed
  ✓ Success on attempt 2/3      → Retry pattern works
  🎯 1.0s delay appears optimal → Increase sleep delays
""")


def main():
    print("""
╔════════════════════════════════════════════════════════════════════╗
║  Mothbox Workflow Test Failure Diagnostic                          ║
║  Analyzing test patterns without requiring hardware                ║
╚════════════════════════════════════════════════════════════════════╝
    """)

    tests_dir = Path(__file__).parent / 'integration'

    # Analyze passing tests
    passing_test = tests_dir / 'test_test_capture_workflows.py'
    if passing_test.exists():
        analyze_test_file(passing_test)

    # Analyze failing workflow tests
    failing_test = tests_dir / 'test_end_to_end_workflows.py'
    if failing_test.exists():
        analyze_test_file(failing_test)

    # Analyze camera routes
    analyze_camera_routes()

    # Compare patterns
    compare_test_patterns()

    # Print recommendations
    print_recommendations()


if __name__ == '__main__':
    main()
