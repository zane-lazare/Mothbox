#!/bin/bash
# ==============================================================================
# Mothbox Input Validation Test Suite
# ==============================================================================
#
# This script tests the input validation functions used in install_mothbox.sh
# to ensure they properly reject malicious or invalid inputs.
#
# Usage:
#   ./test_validation.sh
#
# ==============================================================================

set -e  # Exit on error

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Import validation functions from install_mothbox.sh
# We'll source the functions by extracting just the validation function definitions
INSTALL_SCRIPT="$SCRIPT_DIR/../install_mothbox.sh"

if [ ! -f "$INSTALL_SCRIPT" ]; then
    echo -e "${RED}Error: install_mothbox.sh not found at $INSTALL_SCRIPT${NC}"
    exit 1
fi

# Source the validation functions (extract lines between function definitions)
eval "$(sed -n '/^validate_gpio_pin()/,/^}/p' "$INSTALL_SCRIPT")"
eval "$(sed -n '/^validate_i2c_address()/,/^}/p' "$INSTALL_SCRIPT")"
eval "$(sed -n '/^validate_positive_integer()/,/^}/p' "$INSTALL_SCRIPT")"

echo -e "${BLUE}================================================================================${NC}"
echo -e "${BLUE}Mothbox Input Validation Test Suite${NC}"
echo -e "${BLUE}================================================================================${NC}"
echo ""

TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# Helper function to run a test
run_test() {
    local test_name="$1"
    local expected_result="$2"  # "pass" or "fail"
    shift 2
    local command="$@"

    TOTAL_TESTS=$((TOTAL_TESTS + 1))

    # Suppress output but capture exit code
    if output=$($command 2>&1); then
        result="pass"
    else
        result="fail"
    fi

    if [ "$result" = "$expected_result" ]; then
        echo -e "${GREEN}✓${NC} $test_name"
        PASSED_TESTS=$((PASSED_TESTS + 1))
    else
        echo -e "${RED}✗${NC} $test_name (expected $expected_result, got $result)"
        FAILED_TESTS=$((FAILED_TESTS + 1))
    fi
}

# ==============================================================================
# GPIO Pin Validation Tests
# ==============================================================================
echo -e "${BLUE}Testing GPIO Pin Validation${NC}"
echo "Valid BCM GPIO range: 2-27"
echo ""

run_test "GPIO pin 17 (valid)" "pass" validate_gpio_pin 17
run_test "GPIO pin 2 (minimum valid)" "pass" validate_gpio_pin 2
run_test "GPIO pin 27 (maximum valid)" "pass" validate_gpio_pin 27
run_test "GPIO pin 5 (valid)" "pass" validate_gpio_pin 5
run_test "GPIO pin 1 (below minimum)" "fail" validate_gpio_pin 1
run_test "GPIO pin 0 (too low)" "fail" validate_gpio_pin 0
run_test "GPIO pin 28 (above maximum)" "fail" validate_gpio_pin 28
run_test "GPIO pin 30 (too high)" "fail" validate_gpio_pin 30
run_test "GPIO pin 100 (way too high)" "fail" validate_gpio_pin 100
run_test "GPIO pin 'abc' (non-numeric)" "fail" validate_gpio_pin "abc"
run_test "GPIO pin '17; rm -rf /' (injection attempt)" "fail" validate_gpio_pin "17; rm -rf /"
run_test "GPIO pin '\$(whoami)' (command substitution)" "fail" validate_gpio_pin "\$(whoami)"
run_test "GPIO pin '' (empty string)" "fail" validate_gpio_pin ""

echo ""

# ==============================================================================
# I2C Address Validation Tests
# ==============================================================================
echo -e "${BLUE}Testing I2C Address Validation${NC}"
echo "Valid I2C address range: 0x03-0x77 in format 0xNN"
echo ""

run_test "I2C address 0x40 (valid)" "pass" validate_i2c_address "0x40"
run_test "I2C address 0x21 (valid)" "pass" validate_i2c_address "0x21"
run_test "I2C address 0x29 (valid)" "pass" validate_i2c_address "0x29"
run_test "I2C address 0x03 (minimum valid)" "pass" validate_i2c_address "0x03"
run_test "I2C address 0x77 (maximum valid)" "pass" validate_i2c_address "0x77"
run_test "I2C address 0x4F (uppercase hex, valid)" "pass" validate_i2c_address "0x4F"
run_test "I2C address 0x3b (lowercase hex, valid)" "pass" validate_i2c_address "0x3b"
run_test "I2C address 0xFF (out of range, too high)" "fail" validate_i2c_address "0xFF"
run_test "I2C address 0xaB (out of range, too high)" "fail" validate_i2c_address "0xaB"
run_test "I2C address 0x02 (below minimum)" "fail" validate_i2c_address "0x02"
run_test "I2C address 0x00 (too low)" "fail" validate_i2c_address "0x00"
run_test "I2C address 0x78 (above maximum)" "fail" validate_i2c_address "0x78"
run_test "I2C address 0x80 (too high)" "fail" validate_i2c_address "0x80"
run_test "I2C address 0x5 (missing leading zero)" "fail" validate_i2c_address "0x5"
run_test "I2C address '40' (missing 0x prefix)" "fail" validate_i2c_address "40"
run_test "I2C address 'abc' (non-hex)" "fail" validate_i2c_address "abc"
run_test "I2C address '0x40; rm -rf /' (injection attempt)" "fail" validate_i2c_address "0x40; rm -rf /"
run_test "I2C address '' (empty string)" "fail" validate_i2c_address ""

echo ""

# ==============================================================================
# Positive Integer Validation Tests
# ==============================================================================
echo -e "${BLUE}Testing Positive Integer Validation${NC}"
echo "Testing with default max (999999) and custom max values"
echo ""

run_test "Positive integer 100 (valid, no max)" "pass" validate_positive_integer 100
run_test "Positive integer 0 (valid edge case)" "pass" validate_positive_integer 0
run_test "Positive integer 999999 (max default)" "pass" validate_positive_integer 999999
run_test "Positive integer 9600 (GPS baudrate)" "pass" validate_positive_integer 9600 115200
run_test "Positive integer 115200 (max baudrate)" "pass" validate_positive_integer 115200 115200
run_test "Positive integer 10 (GPS timeout)" "pass" validate_positive_integer 10 300
run_test "Positive integer 300 (max timeout)" "pass" validate_positive_integer 300 300
run_test "Positive integer 301 (exceeds max timeout)" "fail" validate_positive_integer 301 300
run_test "Positive integer 115201 (exceeds max baudrate)" "fail" validate_positive_integer 115201 115200
run_test "Positive integer -1 (negative)" "fail" validate_positive_integer -1
run_test "Positive integer -100 (negative)" "fail" validate_positive_integer -100
run_test "Positive integer 'abc' (non-numeric)" "fail" validate_positive_integer "abc"
run_test "Positive integer '100; rm -rf /' (injection)" "fail" validate_positive_integer "100; rm -rf /"
run_test "Positive integer '' (empty string)" "fail" validate_positive_integer ""

echo ""

# ==============================================================================
# Summary
# ==============================================================================
echo -e "${BLUE}================================================================================${NC}"
echo -e "${BLUE}Test Summary${NC}"
echo -e "${BLUE}================================================================================${NC}"
echo ""

echo "Total tests:  $TOTAL_TESTS"
echo -e "${GREEN}Passed:       $PASSED_TESTS${NC}"

if [ $FAILED_TESTS -gt 0 ]; then
    echo -e "${RED}Failed:       $FAILED_TESTS${NC}"
    echo ""
    echo -e "${RED}Some tests failed! Please review the validation functions.${NC}"
    exit 1
else
    echo -e "${GREEN}Failed:       $FAILED_TESTS${NC}"
    echo ""
    echo -e "${GREEN}================================================================================${NC}"
    echo -e "${GREEN}All validation tests passed!${NC}"
    echo -e "${GREEN}================================================================================${NC}"
    echo ""
    echo "The input validation functions are working correctly and will:"
    echo "  ✓ Accept valid GPIO pins in BCM range (2-27)"
    echo "  ✓ Accept valid I2C addresses in format 0xNN (range 0x03-0x77)"
    echo "  ✓ Accept valid positive integers within specified ranges"
    echo "  ✓ Reject injection attempts (shell metacharacters, command substitution)"
    echo "  ✓ Reject out-of-range values"
    echo "  ✓ Reject malformed inputs"
    echo ""
fi
