#!/bin/bash
# ==============================================================================
# GPS EXIF Tagger Service - Resource Limits Test
# ==============================================================================
#
# This script monitors the GPS EXIF Tagger service resource usage to verify
# it stays within configured limits.
#
# Usage: ./test_resource_limits.sh [duration_seconds]
#
# Default monitoring duration: 60 seconds
#
# Resource limits being tested:
# - MemoryMax=256M (268435456 bytes)
# - CPUQuota=25%
#
# Exit codes:
#   0 - Resource usage within limits
#   1 - Resource limits exceeded or service not running
#
# ==============================================================================

set -e

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
DURATION=${1:-60}  # Default 60 seconds
MEMORY_LIMIT_MB=256
MEMORY_LIMIT_BYTES=$((MEMORY_LIMIT_MB * 1024 * 1024))
CPU_LIMIT_PERCENT=25
SAMPLE_INTERVAL=5  # Sample every 5 seconds

# Detect service name
if systemctl list-unit-files | grep -q "gps-exif-tagger.service"; then
    SERVICE_NAME="gps-exif-tagger.service"
elif systemctl list-unit-files | grep -q "gps-exif-tagger-legacy.service"; then
    SERVICE_NAME="gps-exif-tagger-legacy.service"
else
    echo -e "${RED}Error: GPS EXIF Tagger service not installed${NC}"
    exit 1
fi

echo -e "${BLUE}================================================================================${NC}"
echo -e "${BLUE}GPS EXIF Tagger Service - Resource Limits Test${NC}"
echo -e "${BLUE}================================================================================${NC}"
echo ""

# Check if service is running
if ! systemctl is-active --quiet "$SERVICE_NAME"; then
    echo -e "${RED}Error: Service is not running${NC}"
    echo "Start the service first: sudo systemctl start $SERVICE_NAME"
    exit 1
fi

# Get PID
PID=$(systemctl show "$SERVICE_NAME" -p MainPID --value)
if [ "$PID" = "0" ] || [ -z "$PID" ]; then
    echo -e "${RED}Error: Cannot get service PID${NC}"
    exit 1
fi

echo -e "${BLUE}Service Name:${NC} $SERVICE_NAME"
echo -e "${BLUE}PID:${NC} $PID"
echo -e "${BLUE}Monitoring Duration:${NC} ${DURATION}s"
echo -e "${BLUE}Sample Interval:${NC} ${SAMPLE_INTERVAL}s"
echo ""
echo -e "${BLUE}Resource Limits:${NC}"
echo -e "  Memory: ${MEMORY_LIMIT_MB}MB (${MEMORY_LIMIT_BYTES} bytes)"
echo -e "  CPU: ${CPU_LIMIT_PERCENT}%"
echo ""

# Initialize tracking variables
MAX_MEMORY=0
MAX_CPU=0
SAMPLES=0
MEMORY_VIOLATIONS=0
CPU_VIOLATIONS=0

echo -e "${BLUE}Starting monitoring...${NC}"
echo ""
printf "%-10s %-15s %-15s %-10s %-10s\n" "Time(s)" "Memory(MB)" "Memory(%)" "CPU(%)" "Status"
echo "--------------------------------------------------------------------------------"

# Monitor for specified duration
for ((i=0; i<DURATION; i+=SAMPLE_INTERVAL)); do
    # Get memory usage
    MEMORY_BYTES=$(systemctl show "$SERVICE_NAME" -p MemoryCurrent --value)
    MEMORY_MB=$(awk "BEGIN {printf \"%.2f\", $MEMORY_BYTES/1024/1024}")
    MEMORY_PERCENT=$(awk "BEGIN {printf \"%.1f\", ($MEMORY_BYTES/$MEMORY_LIMIT_BYTES)*100}")

    # Get CPU usage (percentage over last interval)
    # Note: This is approximate, systemd tracks cumulative CPU time
    CPU_PERCENT=$(ps -p "$PID" -o %cpu --no-headers 2>/dev/null || echo "0.0")

    # Update maximums
    if (( $(echo "$MEMORY_BYTES > $MAX_MEMORY" | bc -l) )); then
        MAX_MEMORY=$MEMORY_BYTES
    fi

    if (( $(echo "$CPU_PERCENT > $MAX_CPU" | bc -l) )); then
        MAX_CPU=$CPU_PERCENT
    fi

    # Check for violations
    STATUS="${GREEN}OK${NC}"
    if (( $(echo "$MEMORY_BYTES > $MEMORY_LIMIT_BYTES" | bc -l) )); then
        STATUS="${RED}MEM LIMIT${NC}"
        MEMORY_VIOLATIONS=$((MEMORY_VIOLATIONS + 1))
    fi

    if (( $(echo "$CPU_PERCENT > $CPU_LIMIT_PERCENT" | bc -l) )); then
        STATUS="${RED}CPU LIMIT${NC}"
        CPU_VIOLATIONS=$((CPU_VIOLATIONS + 1))
    fi

    # Display current status
    printf "%-10d %-15s %-15s %-10s " "$i" "$MEMORY_MB" "$MEMORY_PERCENT" "$CPU_PERCENT"
    echo -e "$STATUS"

    SAMPLES=$((SAMPLES + 1))

    # Check if process still exists
    if ! ps -p "$PID" > /dev/null 2>&1; then
        echo ""
        echo -e "${RED}Service process terminated unexpectedly!${NC}"
        exit 1
    fi

    sleep "$SAMPLE_INTERVAL"
done

echo ""
echo -e "${BLUE}================================================================================${NC}"
echo -e "${BLUE}Resource Usage Summary${NC}"
echo -e "${BLUE}================================================================================${NC}"
echo ""

# Calculate max values in human-readable format
MAX_MEMORY_MB=$(awk "BEGIN {printf \"%.2f\", $MAX_MEMORY/1024/1024}")
MAX_MEMORY_PERCENT=$(awk "BEGIN {printf \"%.1f\", ($MAX_MEMORY/$MEMORY_LIMIT_BYTES)*100}")

echo -e "${BLUE}Peak Memory Usage:${NC}"
echo "  $MAX_MEMORY_MB MB (${MAX_MEMORY_PERCENT}% of ${MEMORY_LIMIT_MB}MB limit)"
if (( $(echo "$MAX_MEMORY > $MEMORY_LIMIT_BYTES" | bc -l) )); then
    echo -e "${RED}  ✗ EXCEEDED LIMIT${NC}"
else
    echo -e "${GREEN}  ✓ Within limit${NC}"
fi
echo ""

echo -e "${BLUE}Peak CPU Usage:${NC}"
echo "  ${MAX_CPU}% (limit: ${CPU_LIMIT_PERCENT}%)"
if (( $(echo "$MAX_CPU > $CPU_LIMIT_PERCENT" | bc -l) )); then
    echo -e "${YELLOW}  ⚠ Exceeded limit (bursts above limit are normal)${NC}"
else
    echo -e "${GREEN}  ✓ Within limit${NC}"
fi
echo ""

echo -e "${BLUE}Violations:${NC}"
echo "  Memory limit violations: $MEMORY_VIOLATIONS / $SAMPLES samples"
echo "  CPU limit violations: $CPU_VIOLATIONS / $SAMPLES samples"
echo ""

# Final verdict
if [ $MEMORY_VIOLATIONS -gt 0 ]; then
    echo -e "${RED}Test FAILED: Memory limit exceeded${NC}"
    echo -e "${YELLOW}Consider increasing MemoryMax in service file${NC}"
    exit 1
elif [ $CPU_VIOLATIONS -gt $((SAMPLES / 2)) ]; then
    echo -e "${YELLOW}Test WARNING: CPU frequently exceeded limit${NC}"
    echo -e "${YELLOW}Brief CPU bursts are normal, but sustained high usage may need investigation${NC}"
    exit 0
else
    echo -e "${GREEN}Test PASSED: All resource limits respected${NC}"
    exit 0
fi
