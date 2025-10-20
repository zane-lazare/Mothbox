#!/bin/bash
# Mothbox Test Runner for Raspberry Pi
# Handles externally-managed environment issue on newer Pi OS versions

set -e  # Exit on error

echo "🧪 Mothbox Test Runner - Issue #43 Complete Test Suite"
echo "======================================================="
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

# Stop mothbox-webui service if running (camera must be released for tests)
echo "🔍 Checking mothbox-webui service..."
if systemctl is-active --quiet mothbox-webui 2>/dev/null; then
    echo "   ⚠️  mothbox-webui is running - stopping for tests..."
    sudo systemctl stop mothbox-webui
    WEBUI_WAS_RUNNING=true
    echo "   ✓ Service stopped"
else
    echo "   ✓ Service not running"
    WEBUI_WAS_RUNNING=false
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

    "performance"|"streaming")
        # Performance & Streaming tests
        echo "🚀 Running Performance & Streaming tests..."
        echo ""
        echo "Testing stream modes, stability, and concurrent performance..."
        pytest Tests/unit/test_stream_modes.py \
               Tests/integration/test_stream_stability.py \
               Tests/integration/test_stream_performance.py -v -s
        ;;

    "quality"|"image-quality")
        # Image Quality Controls tests
        echo "🚀 Running Image Quality Controls tests..."
        echo ""
        echo "Testing quality validation, persistence, and visual metrics..."
        pytest Tests/unit/test_image_quality_validation.py \
               Tests/integration/test_quality_settings_persistence.py \
               Tests/integration/test_image_quality.py -v -s
        ;;

    "focus"|"exposure")
        # Focus & Exposure Controls tests
        echo "🚀 Running Focus & Exposure Controls tests..."
        echo ""
        echo "Testing autofocus, calibration, exposure, and metering workflows..."
        pytest Tests/unit/test_focus_control_validation.py \
               Tests/unit/test_metering_validation.py \
               Tests/integration/test_autofocus_workflows.py \
               Tests/integration/test_calibration_workflows.py \
               Tests/integration/test_camera_controls.py \
               Tests/integration/test_metering_exposure.py -v -s
        ;;

    "workflows"|"interactive")
        # Interactive Features & Workflows tests
        echo "🚀 Running Interactive Features & Workflows tests..."
        echo ""
        echo "Testing WebSocket events, test capture, and end-to-end workflows..."
        pytest Tests/unit/test_websocket_handlers.py \
               Tests/integration/test_websocket_integration.py \
               Tests/integration/test_test_capture_workflows.py \
               Tests/integration/test_end_to_end_workflows.py \
               Tests/integration/test_frontend_integration.py -v -s
        ;;

    "noise-reduction"|"noise")
        # Noise Reduction Mode tests
        echo "🚀 Running Noise Reduction Mode tests..."
        echo ""
        echo "=== Hardware Tests (exclusive camera access) ==="
        pytest Tests/integration/test_noise_reduction_hardware.py -v -s
        echo ""
        echo "=== Validation, API, and Quality Tests ==="
        pytest Tests/unit/test_noise_reduction_validation.py \
               Tests/integration/test_noise_reduction_api.py \
               Tests/integration/test_noise_reduction_quality.py -v -s
        ;;

    "metering"|"exposure-metering")
        # Exposure Metering Mode tests (feature/exposure-metering branch)
        echo "🚀 Running Exposure Metering Mode tests..."
        echo ""
        echo "Testing AeMeteringMode control (Centre-Weighted, Spot, Matrix)..."
        pytest Tests/unit/test_metering_validation.py \
               Tests/integration/test_metering_exposure.py -v -s
        ;;

    "isp"|"tuning")
        # ISP Tuning Feature tests
        echo "🚀 Running ISP Tuning Feature tests..."
        echo ""
        echo "Testing tuning loader, ISP controls, and integration..."
        pytest Tests/unit/test_tuning_loader.py \
               Tests/integration/test_isp_features.py -v -s
        ;;

    "focusbracket"|"focus-bracket")
        # Focus Bracketing tests
        echo "🚀 Running Focus Bracketing tests..."
        echo ""
        echo "Testing focus bracket validation and capture workflows..."
        pytest Tests/unit/test_focus_bracket_validation.py \
               Tests/integration/test_focus_bracket_capture.py -v -s
        ;;

    "metadata"|"extended-metadata")
        # Extended Metadata tests
        echo "🚀 Running Extended Metadata tests..."
        echo ""
        echo "Testing accuracy of 15+ new metadata fields with real hardware..."
        pytest Tests/integration/test_metadata_accuracy.py -v -s
        ;;

    "issue43"|"complete")
        # All tests for GitHub issue #43
        echo "🚀 Running COMPLETE test suite for GitHub issue #43..."
        echo ""
        echo "=== Performance & Streaming ==="
        pytest Tests/unit/test_stream_modes.py Tests/integration/test_stream_stability.py -v -s
        echo ""
        echo "=== Image Quality Controls ==="
        pytest Tests/unit/test_image_quality_validation.py Tests/integration/test_quality_settings_persistence.py -v -s
        echo ""
        echo "=== Focus & Exposure Controls ==="
        pytest Tests/unit/test_focus_control_validation.py Tests/integration/test_autofocus_workflows.py Tests/integration/test_calibration_workflows.py -v -s
        echo ""
        echo "=== Interactive Features & Workflows ==="
        pytest Tests/unit/test_websocket_handlers.py Tests/integration/test_websocket_integration.py Tests/integration/test_test_capture_workflows.py Tests/integration/test_end_to_end_workflows.py -v -s
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
        echo "=== GitHub Issue #43 Test Categories ==="
        echo "  issue43       - Run ALL tests for issue #43 (comprehensive)"
        echo "  complete      - Same as issue43"
        echo "  performance   - Performance & Streaming tests"
        echo "  streaming     - Same as performance"
        echo "  quality       - Image Quality Controls tests"
        echo "  image-quality - Same as quality"
        echo "  focus         - Focus & Exposure Controls tests"
        echo "  exposure      - Same as focus"
        echo "  workflows     - Interactive Features & Workflows tests"
        echo "  interactive   - Same as workflows"
        echo "  noise         - Noise Reduction Mode tests"
        echo "  noise-reduction - Same as noise"
        echo "  metering      - Exposure Metering Mode tests (feature branch)"
        echo "  exposure-metering - Same as metering"
        echo "  isp           - ISP Tuning Feature tests"
        echo "  tuning        - Same as isp"
        echo "  focusbracket  - Focus Bracketing tests"
        echo "  focus-bracket - Same as focusbracket"
        echo "  metadata      - Extended Metadata extraction tests (15+ fields)"
        echo "  extended-metadata - Same as metadata"
        echo ""
        echo "=== Legacy Phase Commands (backward compatibility) ==="
        echo "  phase2        - Run Phase 2 complete test suite"
        echo "  phase3        - Run Phase 3 frontend integration tests"
        echo "  frontend      - Same as phase3"
        echo "  phase4        - Test Phase 4.5 test capture endpoint"
        echo "  testcapture   - Same as phase4"
        echo "  controls      - Test Phase 2 camera controls validation"
        echo ""
        echo "=== General Test Commands ==="
        echo "  quick         - Run single most important test (encoding speed)"
        echo "  unit          - Run all unit tests"
        echo "  integration   - Run integration/performance tests"
        echo "  all           - Run full automated test suite (default)"
        echo "  manual        - Show manual verification checklist"
        echo "  help          - Show this help message"
        echo ""
        echo "Examples:"
        echo "  ./run_tests.sh                  # Run all automated tests"
        echo "  ./run_tests.sh issue43          # Run all issue #43 tests (recommended)"
        echo "  ./run_tests.sh performance      # Test performance & streaming"
        echo "  ./run_tests.sh quality          # Test image quality controls"
        echo "  ./run_tests.sh focus            # Test focus & exposure"
        echo "  ./run_tests.sh focusbracket     # Test focus bracketing"
        echo "  ./run_tests.sh workflows        # Test interactive features"
        echo "  ./run_tests.sh noise            # Test noise reduction modes"
        echo "  ./run_tests.sh metering         # Test exposure metering mode (feature)"
        echo "  ./run_tests.sh isp              # Test ISP tuning features"
        echo "  ./run_tests.sh metadata         # Test extended metadata (15+ fields)"
        echo "  ./run_tests.sh quick            # Quick performance check"
        echo "  ./run_tests.sh manual           # Show manual test steps"
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

# Restart web service if it was running before tests
if [ "$WEBUI_WAS_RUNNING" = "true" ]; then
    echo "🔄 Restarting mothbox-webui service..."
    sudo systemctl start mothbox-webui
    echo "   ✓ Service restarted"
    echo ""
fi

# Show next steps
if [ "$TEST_TYPE" != "manual" ] && [ "$TEST_TYPE" != "help" ]; then
    echo "📋 Next steps:"
    echo "   1. Check test results above"
    echo "   2. Run manual verification: ./Tests/run_tests.sh manual"
    echo "   3. Test WebUI: python3 webui/backend/app.py"
    echo "   4. Browser: http://$(hostname -I | awk '{print $1}'):5000"
fi
