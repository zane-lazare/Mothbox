#!/bin/bash
# Mothbox Test Runner for Raspberry Pi
# Handles externally-managed environment issue on newer Pi OS versions

set -e  # Exit on error

echo "🧪 Mothbox Phase 1.1-1.3 Test Runner"
echo "====================================="
echo ""

# Get the script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
FIRMWARE_DIR="$( cd "$SCRIPT_DIR/.." && pwd )"

cd "$FIRMWARE_DIR"

# Check if we're on Raspberry Pi
if [ ! -f /proc/cpuinfo ] || ! grep -q "Raspberry Pi" /proc/cpuinfo 2>/dev/null; then
    echo "⚠️  Warning: Not running on Raspberry Pi"
    echo "   Tests require Pi hardware (camera, simplejpeg)"
    echo ""
fi

# Install test dependencies
echo "📦 Installing test dependencies..."
pip3 install --break-system-packages -q -r Tests/requirements-test.txt 2>&1 | grep -v "already satisfied" || true

echo "✅ Dependencies installed!"
echo ""

# Verify simplejpeg is available
echo "🔍 Checking simplejpeg..."
if python3 -c "import simplejpeg; print(f'   ✓ simplejpeg v{simplejpeg.__version__} available')" 2>/dev/null; then
    :
else
    echo "   ✗ simplejpeg not available!"
    echo "   Install with: pip3 install --break-system-packages simplejpeg"
    exit 1
fi

echo ""

# Parse command line arguments
TEST_TYPE="${1:-all}"

case "$TEST_TYPE" in
    "quick")
        echo "🚀 Running quick performance test..."
        echo ""
        pytest Tests/unit/test_camera_stream.py::TestSimpleJPEGEncoding::test_encoding_speed_comparison -v -s
        ;;

    "unit")
        echo "🚀 Running unit tests..."
        echo ""
        pytest Tests/unit/ -v -s
        ;;

    "integration")
        echo "🚀 Running integration tests..."
        echo ""
        pytest Tests/integration/test_stream_performance.py -v -s
        ;;

    "controls")
        # Phase 2: Test camera controls validation
        echo "🚀 Testing Phase 2 camera controls validation..."
        echo ""
        pytest Tests/unit/test_preview_controls.py Tests/unit/test_capture_settings.py -v -s
        ;;

    "phase2")
        # Phase 2: Full test suite
        echo "🚀 Running Phase 2 complete test suite..."
        echo ""
        echo "Phase 2.1: Testing controls validation..."
        pytest Tests/unit/test_preview_controls.py Tests/unit/test_capture_settings.py -v -s
        echo ""
        echo "Phase 2.2: Testing interactive features..."
        pytest Tests/integration/test_camera_controls.py Tests/integration/test_image_quality.py -v -s
        ;;

    "phase3"|"frontend")
        # Phase 3: Frontend integration tests
        echo "🚀 Running Phase 3 frontend integration tests..."
        echo ""
        pytest Tests/integration/test_frontend_integration.py Tests/unit/test_settings_copy.py -v -s
        ;;

    "phase4"|"testcapture")
        # Phase 4.5: Test capture endpoint
        echo "🚀 Testing Phase 4.5 test capture endpoint..."
        echo ""
        pytest Tests/unit/test_test_capture.py -v -s
        ;;

    "all")
        echo "🚀 Running full test suite..."
        echo ""
        pytest Tests/ -v -s --ignore=Tests/integration/test_manual_verification.py
        ;;

    "manual")
        echo "📋 Manual verification checklist"
        echo ""
        pytest Tests/integration/test_manual_verification.py -v -s
        ;;

    "help"|"-h"|"--help")
        echo "Usage: ./run_tests.sh [TEST_TYPE]"
        echo ""
        echo "TEST_TYPE options:"
        echo "  quick         - Run single most important test (encoding speed)"
        echo "  unit          - Run all unit tests"
        echo "  integration   - Run integration/performance tests"
        echo "  controls      - Test Phase 2 camera controls validation"
        echo "  phase2        - Run Phase 2 complete test suite"
        echo "  phase3        - Run Phase 3 frontend integration tests"
        echo "  frontend      - Same as phase3"
        echo "  phase4        - Test Phase 4.5 test capture endpoint"
        echo "  testcapture   - Same as phase4"
        echo "  all           - Run full automated test suite (default)"
        echo "  manual        - Show manual verification checklist"
        echo "  help          - Show this help message"
        echo ""
        echo "Examples:"
        echo "  ./run_tests.sh              # Run all automated tests"
        echo "  ./run_tests.sh quick        # Quick performance check"
        echo "  ./run_tests.sh unit         # Unit tests only"
        echo "  ./run_tests.sh controls     # Phase 2 controls validation"
        echo "  ./run_tests.sh phase2       # Full Phase 2 test suite"
        echo "  ./run_tests.sh phase3       # Frontend integration tests"
        echo "  ./run_tests.sh phase4       # Test capture endpoint"
        echo "  ./run_tests.sh manual       # Show manual test steps"
        exit 0
        ;;

    *)
        echo "❌ Unknown test type: $TEST_TYPE"
        echo "   Run './run_tests.sh help' for usage"
        exit 1
        ;;
esac

echo ""
echo "✅ Tests complete!"
echo ""

# Show next steps
if [ "$TEST_TYPE" != "manual" ] && [ "$TEST_TYPE" != "help" ]; then
    echo "📋 Next steps:"
    echo "   1. Check test results above"
    echo "   2. Run manual verification: ./Tests/run_tests.sh manual"
    echo "   3. Test WebUI: python3 webui/backend/app.py"
    echo "   4. Browser: http://$(hostname -I | awk '{print $1}'):5000"
fi
