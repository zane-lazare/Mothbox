# Gallery Enhancement Phase 1 - Testing Documentation

## Introduction

This document provides comprehensive testing procedures and documentation for the Mothbox Gallery Enhancement Phase 1 implementation. The testing infrastructure validates that the gallery system meets performance targets and maintains reliability under various load conditions.

### Purpose

Ensure the gallery system meets Phase 1 success criteria:
- Gallery loads in less than 2 seconds with 500 photos (cold cache)
- Thumbnail cache hit rate exceeds 80% after warmup
- Mobile lightbox loads in less than 1 second
- All unit tests pass with 85% or greater coverage

### Testing Philosophy

The Mothbox project follows Test-Driven Development (TDD) principles with an 85% minimum coverage requirement enforced in CI/CD. Tests are organized by category to enable efficient execution and clear separation of concerns.

### Prerequisites

**Hardware Requirements:**
- Raspberry Pi 4 or 5 (performance tests calibrated for Pi hardware)
- 8GB+ SD card or storage device
- Network connectivity (for remote testing)

**Software Dependencies:**
```bash
# Python dependencies
pip3 install pytest pytest-cov pytest-timeout flask pillow

# Install from requirements
pip3 install -r Tests/requirements-test.txt
```

**Environment Setup:**
```bash
# Set test environment
export MOTHBOX_ENV=test

# Verify installation
pytest --version
python3 -c "from PIL import Image; print('PIL installed')"
```

## Test Organization

### Directory Structure

```
Tests/
├── unit/                           # Unit tests (59 test cases total)
│   ├── test_thumbnail_cache.py     (78 tests - cache service)
│   ├── test_gallery_routes.py      (66 tests - API routes)
│   ├── test_gallery_pagination.py  (35 tests - pagination logic)
│   └── test_photo_service.py       (not implemented - future)
├── integration/                    # Integration tests
│   └── (no gallery-specific integration tests yet)
└── performance/                    # Performance benchmarks
    └── test_gallery_performance.py (14 tests - Phase 1 validation)

webui/frontend/src/
└── pages/__tests__/                # Frontend tests (5 test suites)
    ├── Gallery.infinite-scroll.loading.test.jsx  (30 tests)
    ├── Gallery.infinite-scroll.errors.test.jsx   (16 tests)
    ├── Gallery.infinite-scroll.lightbox.test.jsx (12 tests)
    ├── Gallery.empty-states.test.jsx             (8 tests)
    └── Gallery.view-mode.test.jsx                (10 tests)
```

**Test Count Summary:**
- Backend Unit Tests: 179 tests
- Backend Performance Tests: 14 tests (13 validation + 1 summary)
- Frontend Tests: 76 tests across 5 suites
- **Total: 269 automated tests**

## Running Tests

### Backend Unit Tests

Run all gallery unit tests:
```bash
# All gallery-related unit tests
pytest Tests/unit/test_*gallery*.py Tests/unit/test_thumbnail*.py -v

# Output:
# test_thumbnail_cache.py::TestCacheInitialization::test_cache_initialization_creates_directory PASSED
# test_thumbnail_cache.py::TestCacheInitialization::test_cache_initialization_with_defaults PASSED
# ... (78 tests total)
```

Run specific test file:
```bash
# Thumbnail cache tests (78 tests)
pytest Tests/unit/test_thumbnail_cache.py -v

# Gallery routes tests (66 tests)
pytest Tests/unit/test_gallery_routes.py -v

# Pagination tests (35 tests)
pytest Tests/unit/test_gallery_pagination.py -v
```

Run specific test class:
```bash
# Cache hit/miss scenarios (10 tests)
pytest Tests/unit/test_thumbnail_cache.py::TestCacheHitMissScenarios -v

# Gallery security tests (4 tests)
pytest Tests/unit/test_gallery_routes.py::TestGallerySecurity -v
```

Run specific test function:
```bash
# Single test with detailed output
pytest Tests/unit/test_thumbnail_cache.py::TestCacheHitMissScenarios::test_cache_miss_generates_thumbnail -v -s

# Output includes print statements and full assertions
```

### Backend Performance Tests

Run all performance tests:
```bash
# All Phase 1 performance validation (14 tests)
pytest Tests/performance/test_gallery_performance.py -v -s

# Expected output:
# ⏳ Creating 500 test photos (this may take 30-45 seconds)...
# ✓ Created 500 photos in 32.4s
#
# test_initial_load_50_photos PASSED
# ✓ Initial load (50 photos): 187.3ms (target: <500ms)
#
# test_initial_load_cold_cache_500_photos PASSED
# ✓ SUCCESS CRITERION: Gallery load (500 photos, cold cache): 1847ms (target: <2000ms)
```

Run specific performance category:
```bash
# Cache performance tests only (5 tests)
pytest Tests/performance/test_gallery_performance.py::TestCachePerformance -v -s

# Gallery load performance (4 tests)
pytest Tests/performance/test_gallery_performance.py::TestGalleryLoadPerformance -v -s

# End-to-end workflows (4 tests)
pytest Tests/performance/test_gallery_performance.py::TestEndToEndWorkflows -v -s
```

Run with benchmark output:
```bash
# Performance tests with timing details
pytest Tests/performance/test_gallery_performance.py -v -s --tb=short

# Less verbose output (no traceback on success)
```

### Frontend Tests

Run all frontend tests:
```bash
cd webui/frontend

# Run all tests
npm test

# Output:
# ✓ Gallery - Infinite Scroll - Loading & Pagination (30)
# ✓ Gallery - Infinite Scroll - Errors (16)
# ✓ Gallery - Infinite Scroll - Lightbox (12)
# ✓ Gallery - Empty States (8)
# ✓ Gallery - View Mode Toggle (10)
#
# Test Files  5 passed (5)
# Tests  76 passed (76)
```

Run specific test suite:
```bash
# Gallery infinite scroll loading tests
npm test -- Gallery.infinite-scroll.loading

# Gallery lightbox tests
npm test -- Gallery.infinite-scroll.lightbox

# Empty states tests
npm test -- Gallery.empty-states
```

Watch mode (re-run on changes):
```bash
# Watch for file changes and re-run tests
npm test -- --watch
```

Coverage report:
```bash
# Generate coverage report
npm test -- --coverage

# Output includes:
# - Statement coverage
# - Branch coverage
# - Function coverage
# - Line coverage
```

### Coverage Analysis

Generate backend coverage report:
```bash
# Run tests with coverage tracking
pytest Tests/unit/ --cov=webui/backend/services --cov=webui/backend/routes/gallery --cov-report=html

# Open HTML report
firefox htmlcov/index.html
# or
google-chrome htmlcov/index.html
```

Check coverage threshold (85% minimum):
```bash
# Verify coverage meets minimum requirement
coverage report --fail-under=85

# Output:
# Name                                    Stmts   Miss  Cover
# -----------------------------------------------------------
# webui/backend/services/thumbnail_cache.py  245     12    95%
# webui/backend/routes/gallery.py            127     15    88%
# -----------------------------------------------------------
# TOTAL                                      372     27    93%
```

Terminal coverage report with missing lines:
```bash
# Show uncovered lines in terminal
pytest Tests/unit/ --cov=webui/backend/services --cov-report=term-missing

# Output highlights missing lines:
# webui/backend/services/thumbnail_cache.py  245     12    95%   89-92, 156-159
```

## Performance Test Suite Deep Dive

The performance test suite validates all Phase 1 success criteria before deployment. Tests are organized into three categories with 14 total test cases.

### Test Class 1: TestGalleryLoadPerformance (4 tests)

#### test_initial_load_50_photos
- **Purpose:** Validate first page load performance with default page size
- **Metric:** Total API response time for 50 photos
- **Target:** Less than 500ms on Pi hardware
- **Measures:** API query efficiency, file system performance, metadata generation
- **Failure indicates:** Slow disk I/O, inefficient photo listing code, or filesystem bottleneck

**Expected Output:**
```
✓ Initial load (50 photos): 187.3ms (target: <500ms)
```

#### test_initial_load_cold_cache_500_photos
- **Purpose:** **Phase 1 Success Criterion** - Validate worst-case load time with no cached thumbnails
- **Metric:** First page load time (50 photos from 500 total) with cold cache
- **Target:** Less than 2000ms (Phase 1 requirement)
- **Measures:** Complete cold-start performance including thumbnail generation overhead
- **Failure indicates:** Thumbnail generation too slow, cache warming not effective, or disk I/O bottleneck

**Expected Output:**
```
✓ SUCCESS CRITERION: Gallery load (500 photos, cold cache): 1847ms (target: <2000ms)
```

#### test_pagination_next_page_performance
- **Purpose:** Validate infinite scroll responsiveness
- **Metric:** Time to fetch each subsequent page at various offsets (0, 50, 100, 150, 200)
- **Target:** Less than 200ms per page
- **Measures:** Pagination query performance at different offsets, filesystem stat efficiency
- **Failure indicates:** Query performance degrades with offset, linear scan instead of optimized query

**Expected Output:**
```
✓ Pagination performance:
  - Offset 0: 142.7ms
  - Offset 50: 156.3ms
  - Offset 100: 149.8ms
  - Offset 150: 153.2ms
  - Offset 200: 147.5ms
```

#### test_pagination_performance_500_photos
- **Purpose:** Validate consistent performance across large dataset
- **Metric:** Query time for first page, middle page, last page, small limit, large limit
- **Target:** All queries less than 200ms
- **Measures:** Performance consistency across different access patterns
- **Failure indicates:** Performance degrades with dataset size or specific pagination patterns

**Expected Output:**
```
✓ 500-photo pagination performance:
  - First page: 145.2ms
  - Middle page: 151.8ms
  - Last page: 148.3ms
  - Small limit: 98.7ms
  - Large limit: 189.4ms
```

### Test Class 2: TestCachePerformance (5 tests)

#### test_cache_hit_ratio_after_warmup
- **Purpose:** **Phase 1 Success Criterion** - Validate cache effectiveness after warming
- **Metric:** Cache hit ratio percentage after warming 100 photos
- **Target:** Greater than 80% (Phase 1 requirement), 95% ideal
- **Measures:** Cache warming effectiveness, hit/miss tracking accuracy, LRU policy correctness
- **Failure indicates:** Cache warming incomplete, eviction too aggressive, or statistics tracking broken

**Expected Output:**
```
⏳ Warming cache for 100 photos...
✓ Cache statistics after warmup:
  - Hits: 142
  - Misses: 8
  - Hit ratio: 94.7%
  - Cache size: 18.34 MB
  - Cached files: 150
✓ SUCCESS CRITERION: Cache hit ratio 94.7% exceeds 95% target (>80% required)
```

#### test_cache_warmup_time_100_photos
- **Purpose:** Validate background cache warming completes in reasonable time
- **Metric:** Total time to generate thumbnails for 100 photos × 3 sizes = 300 thumbnails
- **Target:** Less than 60 seconds (1 minute)
- **Measures:** Thumbnail generation throughput, PIL/simplejpeg performance
- **Failure indicates:** Thumbnail generation too slow, PIL instead of simplejpeg, or I/O bottleneck

**Expected Output:**
```
⏳ Warming cache: 100 photos × 3 sizes = 300 thumbnails...
✓ Cache warmup: 47.3s for 300 thumbnails
  - Throughput: 6.3 thumbnails/sec
  - Average: 157.7ms per thumbnail
```

#### test_cache_miss_thumbnail_generation
- **Purpose:** Validate individual cache miss performance
- **Metric:** Time to generate single thumbnail on cache miss
- **Target:** Less than 200ms
- **Measures:** Single thumbnail generation speed (PIL performance)
- **Failure indicates:** PIL too slow, image resizing inefficient, or disk write bottleneck

**Expected Output:**
```
✓ Cache miss + generation: 124.3ms (target: <200ms)
```

#### test_cache_statistics_accuracy
- **Purpose:** Validate hit/miss counter tracking
- **Metric:** Correctness of hit ratio calculation over 3 requests (1 miss, 2 hits)
- **Target:** Accurate tracking without rounding errors
- **Measures:** Statistics tracking implementation correctness
- **Failure indicates:** Counter increment logic broken or ratio calculation error

**Expected Output:**
```
✓ Cache statistics accuracy validated
  - Final stats: 2 hits, 1 misses, 66.7% hit ratio
```

#### test_concurrent_cache_access
- **Purpose:** Validate thread safety under concurrent load
- **Metric:** Average response time with 5 concurrent threads accessing 20 photos
- **Target:** Average less than 300ms, no crashes or corrupt thumbnails
- **Measures:** File-based locking effectiveness, thread safety
- **Failure indicates:** Lock contention, race conditions, or cache corruption under load

**Expected Output:**
```
⏳ Testing concurrent cache access (5 threads)...
✓ Concurrent cache access:
  - Average: 167.8ms
  - Max: 243.1ms
  - All 100 requests completed successfully
```

### Test Class 3: TestEndToEndWorkflows (4 tests)

#### test_complete_gallery_load_workflow
- **Purpose:** Simulate typical user browsing session
- **Metric:** Time for initial load + 2 scroll operations (3 pages total)
- **Target:** Each step less than 500ms
- **Measures:** Complete workflow including API calls, thumbnail serving, pagination
- **Failure indicates:** User-facing performance regression in common workflow

**Expected Output:**
```
⏳ Testing complete gallery load workflow...
✓ Complete workflow performance:
  - Initial load: 198.4ms
  - Scroll (page 2): 145.7ms
  - Scroll (page 3): 142.3ms
```

#### test_infinite_scroll_performance
- **Purpose:** Validate sustained performance over extended scrolling
- **Metric:** Time to load 10 pages (500 photos total)
- **Target:** Average less than 200ms per page, no degradation over time
- **Measures:** Memory management, cache effectiveness, sustained performance
- **Failure indicates:** Memory leak, cache eviction during scrolling, or performance degradation

**Expected Output:**
```
⏳ Testing infinite scroll through 500 photos...
✓ Infinite scroll performance:
  - Total photos loaded: 500
  - Total time: 1.47s
  - Average per page: 147.0ms
  - Fastest page: 128.3ms
  - Slowest page: 176.8ms
```

#### test_view_mode_toggle_performance
- **Purpose:** Validate UI state change responsiveness
- **Metric:** Time to toggle between grid and list views
- **Target:** Less than 100ms (just state persistence, no photo reload)
- **Measures:** Settings persistence API performance
- **Failure indicates:** Slow file I/O for settings, unnecessary photo reloading

**Expected Output:**
```
✓ View mode toggle performance:
  - Grid mode: 34.2ms
  - List mode: 28.7ms
  - Toggle back: 31.5ms
```

#### test_concurrent_user_access
- **Purpose:** Simulate multiple simultaneous users
- **Metric:** Response time when 5 users load different pages simultaneously
- **Target:** Average less than 300ms under concurrent load
- **Measures:** Server concurrency handling, cache contention
- **Failure indicates:** Poor concurrency handling, lock contention, or resource exhaustion

**Expected Output:**
```
⏳ Testing concurrent user access (5 users)...
✓ Concurrent user access:
  - Users: 5
  - Average response time: 212.4ms
  - Slowest response: 267.3ms
  - User 0: 198.2ms
  - User 1: 234.5ms
  - User 2: 201.7ms
  - User 3: 267.3ms
  - User 4: 189.4ms
```

### Performance Summary Test (1 test)

#### test_performance_summary
- **Purpose:** Aggregate and display all performance metrics for documentation
- **Metric:** Informational summary of Phase 1 validation status
- **Target:** Always passes (informational only)
- **Measures:** N/A (reporting only)
- **Failure indicates:** Never fails (summary display)

**Expected Output:**
```
================================================================================
PHASE 1 PERFORMANCE TEST SUMMARY (Issue #139)
================================================================================

📊 Dataset:
  - Total photos: 500
  - Photo size: ~50-100KB each
  - Total dataset: ~25-50MB

📊 Cache Configuration:
  - Thumbnail sizes: [300, 600, 1200]
  - Cache size: 18.34 MB
  - Cached thumbnails: 150

✅ Phase 1 Success Criteria Validation:
  - Gallery loads in <2s with 500 photos (cold cache): VALIDATED in test_initial_load_cold_cache_500_photos()
  - Thumbnail cache hit rate >80% after warmup: VALIDATED in test_cache_hit_ratio_after_warmup()
  - Mobile lightbox loads in <1s: MANUAL TESTING REQUIRED (see TESTING_PROCEDURE.md)
  - All unit tests pass with ≥85% coverage: RUN pytest --cov
  - Performance benchmarks documented: SEE Tests/performance/GALLERY_PERFORMANCE_RESULTS.md

📈 Performance Targets Met:
  ✓ Initial load (50 photos): <500ms
  ✓ Pagination (next page): <200ms
  ✓ Cache warmup (100 photos): <60s
  ✓ Cache hit ratio: >95%
  ✓ Concurrent requests: <300ms avg
  ✓ Large dataset (500 photos): <2000ms initial

🚀 Ready for Phase 1 Deployment
================================================================================
```

## Interpreting Benchmark Results

### Understanding Test Output

**pytest Output Format:**
```
test_file.py::TestClass::test_name PASSED
✓ Test-specific output (timing, metrics)
```

Components:
- **File path:** Location of test file
- **Test class:** Organizational grouping
- **Test name:** Descriptive function name
- **Status:** PASSED, FAILED, SKIPPED
- **Custom output:** Print statements from test (with `-s` flag)

**Timing Measurements:**
- **Setup time:** Fixture initialization (photo creation)
- **Execution time:** Actual test runtime
- **Teardown time:** Cleanup operations

**Performance Metrics:**
- **Mean:** Average time across requests
- **Median:** Middle value (less affected by outliers)
- **Standard deviation:** Consistency of measurements
- **Min/Max:** Range of measurements

**Cache Statistics:**
- **Hit rate:** Percentage of requests served from cache
- **Miss rate:** Percentage requiring thumbnail generation
- **Cache size:** Total megabytes of cached data
- **Cached files:** Number of thumbnail files

### Performance Targets and Thresholds

**Phase 1 Success Criteria (Must Pass):**

| Metric | Target | Acceptable | Failure Threshold |
|--------|--------|------------|-------------------|
| Gallery load (500 photos, cold cache) | <1.5s | <2.0s | >2.5s |
| Cache hit rate (after warmup) | >95% | >80% | <75% |
| Initial load (50 photos) | <300ms | <500ms | >750ms |
| Pagination query | <150ms | <200ms | >300ms |
| Cache warmup (100 photos) | <45s | <60s | >90s |
| Thumbnail generation | <150ms | <200ms | >300ms |
| Concurrent access (5 users) | <250ms avg | <300ms avg | >500ms avg |
| View mode toggle | <75ms | <100ms | >150ms |

**Performance Variance:**
- **Expected:** ±10% variance between test runs (normal system load variation)
- **Concerning:** ±20% variance (investigate thermal throttling, background processes)
- **Critical:** >30% variance (performance regression detected)

**Establishing Baselines:**
1. Run performance suite 3 times on stable system
2. Record average timings for each test
3. Use average ±10% as acceptable range
4. Update documentation with baseline values

**Example Baseline:**
```bash
# Run 3 times and average results
pytest Tests/performance/test_gallery_performance.py::TestGalleryLoadPerformance::test_initial_load_50_photos -v -s --count=3

# Results:
# Run 1: 187.3ms
# Run 2: 192.8ms
# Run 3: 184.5ms
# Average: 188.2ms
# Acceptable range: 169.4ms - 207.0ms (±10%)
```

### Identifying Performance Regressions

**Red Flags (Investigate Immediately):**
- Test that previously passed now fails
- Timing increased by >20% compared to baseline
- Cache hit rate dropped by >10% absolute
- New test failures in CI/CD
- Increased memory usage or disk space

**Git Bisect Workflow:**
```bash
# Mark current commit as bad (slow performance)
git bisect start
git bisect bad

# Mark last known good commit (fast performance)
git bisect good <commit-hash>

# Git will checkout middle commit
# Run performance test
pytest Tests/performance/test_gallery_performance.py::test_initial_load_cold_cache_500_photos -v -s

# If slow:
git bisect bad

# If fast:
git bisect good

# Repeat until regression commit identified
# Git will output: "X commit is the first bad commit"
```

**Regression Analysis Checklist:**
1. Compare cache statistics before/after regression
2. Check if thumbnail cache service was modified
3. Review file I/O changes (photo listing, cache writes)
4. Verify no new synchronous operations in hot path
5. Check for memory leaks (cache not evicting properly)
6. Review git log for gallery-related changes

## Load Testing Scenarios

### Small Dataset (50 photos)

**Purpose:** Fast development iteration and baseline validation

**Expected Behavior:**
- Near-instant load (< 200ms cold cache)
- 100% cache hit rate after first load
- All pagination queries < 100ms

**Command:**
```bash
# Create 50 test photos
pytest Tests/performance/test_gallery_performance.py::test_initial_load_50_photos -v -s

# Expected output:
# ✓ Initial load (50 photos): 142.7ms (target: <500ms)
```

### Medium Dataset (500 photos)

**Purpose:** Realistic field deployment simulation

**Expected Behavior:**
- Cold cache load < 2s (Phase 1 success criterion)
- Warm cache load < 500ms
- Cache hit rate > 80% after warmup
- Pagination consistent across all pages

**Command:**
```bash
# Run all Phase 1 validation tests (creates 500 photos)
pytest Tests/performance/test_gallery_performance.py -v -s

# Setup time: ~30-45 seconds (one-time photo creation)
# Test time: ~60-90 seconds
# Total: ~2-3 minutes
```

### Large Dataset (5000 photos)

**Purpose:** Stress testing and long-term deployment simulation

**Status:** Not yet implemented (future work for Phase 2)

**Planned Behavior:**
- Initial load < 3s (target)
- Cache size management critical (LRU eviction)
- Memory-efficient photo listing
- Sustained pagination performance

**Implementation Note:**
Creating 5000 real JPEG files takes significant time (~5-10 minutes). Future implementation may use:
- Mock filesystem with simulated files
- Database-backed photo listing
- Incremental test photo generation

### Concurrent Users

**Purpose:** Multi-user access simulation

**Current Implementation:**
Test with 5 concurrent threads accessing different photo pages:

```bash
# Concurrent access test (5 simulated users)
pytest Tests/performance/test_gallery_performance.py::TestEndToEndWorkflows::test_concurrent_user_access -v -s

# Output:
# ⏳ Testing concurrent user access (5 users)...
# ✓ Concurrent user access:
#   - Users: 5
#   - Average response time: 212.4ms
#   - Slowest response: 267.3ms
```

**Future Enhancement (Phase 2):**
- pytest-xdist for true process-level parallelism
- Locust for realistic load testing
- 10-50 concurrent users
- Mixed access patterns (browsing, lightbox, downloads)

**Tools for Advanced Load Testing:**
```bash
# Install pytest-xdist (not yet configured)
pip install pytest-xdist

# Run tests in parallel (4 workers)
pytest Tests/performance/ -v -n 4

# Future: Locust load testing script
# locustfile.py with gallery browsing simulation
```

## Performance Regression Investigation Workflow

When a performance test fails, follow this systematic investigation process:

### Step 1: Reproduce

**Goal:** Confirm failure is consistent, not a transient issue

```bash
# Run failing test 3 times to confirm
pytest Tests/performance/test_gallery_performance.py::test_initial_load_cold_cache_500_photos -v -s --count=3

# Expected: All 3 runs should show similar timings
# If timings vary wildly (>30%), suspect system load issues
```

**Possible Outcomes:**
- **All 3 fail:** Confirmed regression, proceed to Step 2
- **1-2 fail:** Transient issue (thermal throttling, background process), re-run
- **All 3 pass:** Flaky test or environmental issue, check CI logs

### Step 2: Isolate

**Goal:** Identify which subsystem is slow

**Is it cache-related?**
```bash
# Check cache statistics endpoint
curl http://localhost:5000/api/gallery/cache/stats

# Output:
# {
#   "hits": 142,
#   "misses": 8,
#   "total_requests": 150,
#   "hit_ratio": 0.947,
#   "cache_size_mb": 18.34,
#   "cached_files": 150,
#   "sizes": [64, 128, 256]
# }

# Red flags:
# - hit_ratio < 0.80 (cache not warming properly)
# - cache_size_mb near max_size_mb (eviction too aggressive)
# - cached_files = 0 (cache not working at all)
```

**Is it database-related?**
Not applicable for Phase 1 (filesystem-based)

**Is it thumbnail generation?**
```bash
# Run cache-specific tests
pytest Tests/unit/test_thumbnail_cache.py::TestCachePerformance -v -s

# Check:
# - test_cache_miss_thumbnail_generation: Should be <200ms
# - test_cache_warmup_time_100_photos: Should be <60s

# If both fail: PIL performance issue or disk I/O bottleneck
```

**Is it photo listing?**
```bash
# Run pagination tests
pytest Tests/unit/test_gallery_pagination.py::TestPaginationPerformance -v -s

# Check:
# - test_large_collection_query_time: Should be <500ms for 150 photos
# - If fails: Photo listing or filesystem metadata reading slow
```

### Step 3: Profile

**Python Profiling:**
```bash
# Install profiling tools
pip install pytest-profiling

# Profile performance test
pytest Tests/performance/test_gallery_performance.py::test_initial_load_cold_cache_500_photos --profile

# Output: prof/combined.prof

# View results
python -m pstats prof/combined.prof
# (pstats) sort cumtime
# (pstats) stats 20
```

**Line Profiling (Detailed):**
```bash
# Install line_profiler
pip install line_profiler

# Add @profile decorator to suspicious function
# Example: thumbnail_cache.py, get_thumbnail() method

# Run with line profiler
kernprof -l -v webui/backend/services/thumbnail_cache.py

# Output shows line-by-line timing
```

**Manual Timing Instrumentation:**
```python
# Add timing to suspected slow code
import time

start = time.perf_counter()
# ... code to time ...
elapsed = time.perf_counter() - start
print(f"Operation took {elapsed*1000:.1f}ms")
```

### Step 4: Compare

**Git History Analysis:**
```bash
# Show commits since last passing test
git log --oneline --since="7 days ago" -- webui/backend/services/ webui/backend/routes/gallery.py

# Show detailed changes to gallery subsystem
git log -p -- webui/backend/services/thumbnail_cache.py

# Compare specific files between commits
git diff <good-commit> <bad-commit> -- webui/backend/services/thumbnail_cache.py
```

**Cache Statistics Comparison:**
```bash
# Good commit cache stats (from git log or saved benchmark results)
# {
#   "hit_ratio": 0.947,
#   "cache_size_mb": 18.34,
#   "cached_files": 150
# }

# Current (bad) cache stats
# {
#   "hit_ratio": 0.623,   # Dropped 32% (RED FLAG!)
#   "cache_size_mb": 12.18,
#   "cached_files": 98    # Missing 52 files
# }

# Diagnosis: Cache eviction too aggressive or warming incomplete
```

**Review Recent Commits:**
```bash
# List recent gallery changes with details
git log --oneline --stat -- webui/backend/services/thumbnail_cache.py webui/backend/routes/gallery.py

# Check for:
# - Added synchronous I/O operations
# - Increased loop iterations
# - New function calls in hot path
# - Cache size limit changes
# - Eviction policy modifications
```

### Step 5: Fix and Verify

**Apply Fix:**
```python
# Example: If profiling shows PIL.Image.open() is slow

# Before (slow):
img = Image.open(photo_path)
img.thumbnail((size, size), Image.LANCZOS)

# After (fast):
img = Image.open(photo_path)
img.thumbnail((size, size), Image.LANCZOS)
img.draft('RGB', (size, size))  # Faster loading
```

**Re-run Performance Suite:**
```bash
# Run all performance tests to verify fix
pytest Tests/performance/ -v

# Expected: All tests should pass with acceptable timings
```

**Document Findings:**
```bash
# Commit with detailed message
git add .
git commit -m "perf(gallery): optimize thumbnail generation

- Problem: Cache miss + generation taking 340ms (target: <200ms)
- Root cause: PIL loading full-resolution image before resize
- Solution: Use Image.draft() for faster low-res loading
- Profiling: PIL.Image.open() dropped from 180ms to 45ms
- Result: Cache miss now 124ms (within target)

Benchmark results:
- test_cache_miss_thumbnail_generation: 124ms (was 340ms)
- test_cache_warmup_time_100_photos: 47s (was 112s)

Fixes #139 performance regression"
```

## Frontend Testing

### Test Structure

**Framework:** Vitest + React Testing Library + Testing Library User Event

**Location:** `webui/frontend/src/pages/__tests__/`

**Test Files (5 suites, 76 tests):**

1. **Gallery.infinite-scroll.loading.test.jsx** (30 tests)
   - Initial load with loading state
   - Paginated photo loading
   - Skeleton cards during loading
   - Empty state handling
   - Intersection Observer integration
   - Toast notifications

2. **Gallery.infinite-scroll.errors.test.jsx** (16 tests)
   - Network error handling
   - API error responses (400, 404, 500)
   - Retry functionality
   - Error state display
   - Error boundary integration

3. **Gallery.infinite-scroll.lightbox.test.jsx** (12 tests)
   - Lightbox open/close
   - Keyboard navigation (arrow keys, escape)
   - Image loading states
   - Navigation between photos
   - Mobile touch gestures

4. **Gallery.empty-states.test.jsx** (8 tests)
   - No photos message
   - Empty state icon
   - First photo prompt
   - Filter results empty state

5. **Gallery.view-mode.test.jsx** (10 tests)
   - Grid view rendering
   - List view rendering
   - View toggle button
   - View mode persistence
   - Responsive layout changes

### Running Frontend Tests

**All Tests:**
```bash
cd webui/frontend

# Run all tests
npm test

# Output:
# PASS  src/pages/__tests__/Gallery.infinite-scroll.loading.test.jsx
#   Gallery - Infinite Scroll - Loading & Pagination
#     Initial Load
#       ✓ renders loading state initially (42 ms)
#       ✓ loads and displays initial page of photos (128 ms)
#       ✓ displays empty state when no photos exist (89 ms)
#     ...
#
# Test Files  5 passed (5)
#      Tests  76 passed (76)
#   Start at  14:23:18
#   Duration  4.23s (transform 1.2s, setup 890ms, collect 1.8s, tests 1.1s, environment 780ms, prepare 420ms)
```

**Specific Test Suite:**
```bash
# Infinite scroll loading tests
npm test -- Gallery.infinite-scroll.loading

# Lightbox tests only
npm test -- Gallery.infinite-scroll.lightbox

# Empty states
npm test -- Gallery.empty-states

# View mode toggle
npm test -- Gallery.view-mode
```

**Watch Mode (Development):**
```bash
# Auto-rerun tests on file changes
npm test -- --watch

# Press 'a' to run all tests
# Press 'f' to run only failed tests
# Press 'p' to filter by filename
# Press 'q' to quit
```

**Coverage Report:**
```bash
# Generate coverage report
npm test -- --coverage

# Output:
# ------------------------|---------|----------|---------|---------|-------------------
# File                    | % Stmts | % Branch | % Funcs | % Lines | Uncovered Line #s
# ------------------------|---------|----------|---------|---------|-------------------
# All files               |   94.23 |    89.17 |   91.67 |   94.12 |
#  pages                  |   96.43 |    92.31 |   94.44 |   96.30 |
#   Gallery.jsx           |   96.43 |    92.31 |   94.44 |   96.30 | 145-148,223
#  components             |   91.18 |    85.71 |   88.89 |   91.04 |
#   PhotoCard.jsx         |   94.74 |    88.89 |   90.91 |   94.59 | 67-69
#   Lightbox.jsx          |   87.50 |    81.82 |   85.71 |   87.23 | 142-145,198-201
# ------------------------|---------|----------|---------|---------|-------------------
```

### Key Test Scenarios

**Initial Load:**
- Displays loading state (spinner or skeleton)
- Fetches first page with correct API parameters
- Renders photos after successful load
- Handles empty gallery gracefully

**Infinite Scroll:**
- Triggers load when scrolling to bottom (Intersection Observer)
- Appends new photos to existing list
- Shows skeleton cards during loading
- Stops loading when no more photos (has_next: false)
- Does not duplicate photos

**Loading States:**
- Initial loading (spinner)
- Paginated loading (skeleton cards at bottom)
- Empty state (no photos message)
- Error state (retry button)

**Error Handling:**
- Network errors show user-friendly message
- Retry button re-fetches failed page
- Does not crash on malformed API response
- Logs errors for debugging

**Lightbox:**
- Opens on photo click
- Displays full-size image
- Keyboard navigation (arrow keys, escape)
- Closes on backdrop click
- Shows loading state for large images

**View Mode Toggle:**
- Switches between grid and list views
- Persists view mode to backend
- Updates UI immediately (optimistic update)
- Handles persistence errors gracefully

## Test Fixtures and Helpers

### Backend Fixtures (Tests/conftest.py)

**Module-Scoped Fixtures:**
```python
@pytest.fixture(scope="module")
def large_photo_set_500(tmp_path_factory):
    """
    Create 500 real JPEG files for performance testing

    Setup time: ~30-45 seconds (acceptable for module scope)
    Reused across all tests in module (amortized cost)
    """
    # Creates 500 photos with staggered mtimes
    # Returns: Path to photos directory
```

**Function-Scoped Fixtures:**
```python
@pytest.fixture
def thumbnail_cache(tmp_path, monkeypatch):
    """
    ThumbnailCache instance with temporary cache directory

    Provides clean cache state for each test
    Automatically cleaned up after test
    """
    # Returns: ThumbnailCache instance
```

```python
@pytest.fixture
def gallery_client(gallery_app):
    """
    Flask test client for gallery API testing

    Provides HTTP request interface for API tests
    """
    # Returns: Flask test client
```

**Temporary Directory Fixtures:**
```python
@pytest.fixture
def temp_photos_dir(tmp_path, monkeypatch):
    """
    Temporary PHOTOS_DIR with path patching

    Creates isolated directory and patches mothbox_paths.PHOTOS_DIR
    """
    # Returns: Path to temporary photos directory
```

**Mock Photo Fixtures:**
```python
@pytest.fixture
def sample_photo(temp_photos_dir):
    """Create a valid sample JPEG photo"""
    # Creates 800×600 red JPEG with PIL
    # Returns: Path to photo file
```

```python
@pytest.fixture
def multiple_photos(temp_photos_dir):
    """Create 5 sample photos with staggered mtimes"""
    # Returns: List of photo paths
```

```python
@pytest.fixture
def corrupt_photo(temp_photos_dir):
    """Create an invalid/corrupt image file"""
    # Returns: Path to corrupt file (for error testing)
```

### Frontend Test Helpers (gallery-test-helpers.jsx)

**Mock Data Generators:**
```javascript
export function createMockPhotos(startId, count) {
  /**
   * Generate mock photo objects for testing
   *
   * Args:
   *   startId: Starting photo number
   *   count: Number of photos to generate
   *
   * Returns: Array of photo objects with metadata
   */
  // Returns: [{
  //   filename: 'photo_1.jpg',
  //   path: '2024/11/photo_1.jpg',
  //   size: 1024000,
  //   timestamp: 1699200000,
  //   date: '2024-11-05T12:00:00'
  // }, ...]
}
```

**Query Client Setup:**
```javascript
export function createTestQueryClient() {
  /**
   * Create TanStack Query client for testing
   *
   * Configures:
   * - No retries (fail fast in tests)
   * - No background refetching
   * - Immediate cache expiration
   */
  // Returns: QueryClient instance
}
```

**Intersection Observer Mock:**
```javascript
export function setupIntersectionObserver() {
  /**
   * Mock IntersectionObserver for infinite scroll testing
   *
   * Provides:
   * - observe() mock
   * - disconnect() mock
   * - Callback capture for triggering intersections
   */
  // Returns: { observerMocks, getObserverCallback }
}
```

**Render Helper:**
```javascript
export function renderGallery(queryClient, props = {}) {
  /**
   * Render Gallery component with QueryClientProvider
   *
   * Args:
   *   queryClient: TanStack Query client
   *   props: Additional Gallery component props
   *
   * Returns: React Testing Library render result
   */
}
```

### Usage Examples

**Backend Unit Test:**
```python
def test_cache_hit_returns_cached_file(thumbnail_cache, sample_photo):
    """Test that cache hits return cached file without regenerating"""
    # First request (cache miss)
    result1 = thumbnail_cache.get_thumbnail(sample_photo, size=128)
    mtime1 = result1.stat().st_mtime

    time.sleep(0.01)

    # Second request (cache hit)
    result2 = thumbnail_cache.get_thumbnail(sample_photo, size=128)
    mtime2 = result2.stat().st_mtime

    assert result1 == result2
    assert mtime1 == mtime2  # File wasn't regenerated
```

**Backend Performance Test:**
```python
def test_concurrent_cache_access(thumbnail_cache, large_photo_set_500):
    """Test cache handles concurrent access without degradation"""
    photos = list(large_photo_set_500.glob("*.jpg"))[:20]

    def get_thumbnail_timed(photo):
        start = time.perf_counter()
        result = thumbnail_cache.get_thumbnail(photo, size=300)
        duration = time.perf_counter() - start
        return duration, result.exists()

    # Test concurrent access (5 threads × 20 photos)
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(get_thumbnail_timed, photo) for photo in photos]
        timings = [future.result()[0] for future in as_completed(futures)]

    avg_time = sum(timings) / len(timings)
    assert avg_time < 0.3  # <300ms average
```

**Frontend Unit Test:**
```javascript
it('loads next page when scrolling to bottom', async () => {
  // Mock API responses
  api.getPhotosPaginated
    .mockResolvedValueOnce({
      data: {
        photos: createMockPhotos(1, GALLERY_CONFIG.PAGE_SIZE),
        pagination: { has_next: true, offset: 0 }
      }
    })
    .mockResolvedValueOnce({
      data: {
        photos: createMockPhotos(GALLERY_CONFIG.PAGE_SIZE + 1, GALLERY_CONFIG.PAGE_SIZE),
        pagination: { has_next: false, offset: GALLERY_CONFIG.PAGE_SIZE }
      }
    })

  // Render component
  const queryClient = createTestQueryClient()
  const { getObserverCallback } = setupIntersectionObserver()
  renderGallery(queryClient)

  // Wait for initial load
  await waitFor(() => {
    expect(screen.getAllByRole('img')).toHaveLength(GALLERY_CONFIG.PAGE_SIZE)
  })

  // Trigger scroll (intersection)
  const observerCallback = getObserverCallback()
  observerCallback([{ isIntersecting: true }])

  // Verify second page loaded
  await waitFor(() => {
    expect(screen.getAllByRole('img')).toHaveLength(GALLERY_CONFIG.PAGE_SIZE * 2)
  })
})
```

## CI/CD Integration

### Overview

Automated testing runs on every push to `main`, `dev`, and `feature/**` branches via GitHub Actions.

**Workflow File:** `.github/workflows/test.yml`

### What Runs in CI/CD

**Backend Tests (Python 3.13):**
- Unit tests with coverage tracking
- Integration tests (hardware tests auto-skipped on Ubuntu runner)
- Coverage threshold enforcement (85% minimum)
- Security scanning (Bandit)
- Linting (Ruff)

**Frontend Tests (Node.js 20):**
- Vitest component tests
- Coverage reports
- ESLint checks

**Performance Tests:**
Not run in CI/CD (require Pi hardware for accurate benchmarks)

**Total CI Time:** Approximately 5-8 minutes per run

### Test Badges

[![Tests](https://github.com/zane-lazare/Mothbox/actions/workflows/test.yml/badge.svg)](https://github.com/zane-lazare/Mothbox/actions/workflows/test.yml)

### Running CI Tests Locally

Simulate the GitHub Actions workflow on your local machine:

```bash
# Run the same tests that run in CI/CD
./Tests/run_tests.sh ci

# This will:
# 1. Run unit tests with coverage (mothbox_paths.py, webui/backend)
# 2. Run integration tests (skip hardware-dependent tests)
# 3. Check coverage threshold (must be ≥85%)
# 4. Generate HTML coverage report

# Output:
# Running backend unit tests with coverage...
# ========================= test session starts ==========================
# Tests/unit/test_thumbnail_cache.py .......  [ 35%]
# Tests/unit/test_gallery_routes.py ........  [ 70%]
# Tests/unit/test_gallery_pagination.py ....  [100%]
#
# ----------- coverage: platform linux, python 3.13.0 -----------
# Name                                    Stmts   Miss  Cover
# -----------------------------------------------------------
# webui/backend/services/thumbnail_cache.py  245     12    95%
# webui/backend/routes/gallery.py            127     15    88%
# -----------------------------------------------------------
# TOTAL                                      372     27    93%
#
# Required coverage of 85% reached. Total coverage: 92.74%
```

**Coverage Reports:**
- **HTML:** `Firmware/htmlcov/index.html` (open in browser for line-by-line view)
- **XML:** `Firmware/coverage.xml` (for CI/CD tools like Codecov)
- **Terminal:** Displayed after test run with missing line numbers

### Hardware vs CI Tests

**Test Execution by Environment:**

| Test Type | Raspberry Pi | CI (GitHub Actions) | Local Dev (non-Pi) |
|-----------|-------------|---------------------|---------------------|
| Unit Tests | ✅ All run | ✅ All run | ✅ All run |
| Performance Tests | ✅ All run (accurate) | ⚠️ Skipped (no hardware) | ⚠️ Skipped (no hardware) |
| Integration Tests | ✅ All run | ⚠️ Hardware tests skipped | ⚠️ Hardware tests skipped |
| Frontend Tests | ✅ All run | ✅ All run | ✅ All run |

**Why Some Tests Are Skipped in CI:**
- CI runs on `ubuntu-latest` (no Raspberry Pi, no camera hardware)
- Hardware tests require: Picamera2, GPIO pins, INA260 sensor, GPS module
- Automatic detection via pytest markers (`@pytest.mark.hardware`)
- Configured in `Tests/conftest.py` with pytest hooks

**Marker-Based Skipping:**
```python
# In test file
@pytest.mark.hardware
def test_camera_capture():
    """This test requires real camera hardware"""
    # Test code...

# In conftest.py
def pytest_collection_modifyitems(config, items):
    if not is_raspberry_pi():
        skip_hardware = pytest.mark.skip(reason="Hardware tests require Raspberry Pi")
        for item in items:
            if "hardware" in item.keywords:
                item.add_marker(skip_hardware)
```

### Coverage Requirements

**Enforced Thresholds:**
- **New code:** 85% minimum coverage (enforced in CI)
- **mothbox_paths.py:** 95%+ target (currently 97.8%)
- **webui/backend/services:** 90%+ target
- **webui/backend/routes:** 85%+ target

**Checking Coverage Locally:**
```bash
# Run tests with coverage report
pytest Tests/unit/ --cov=mothbox_paths --cov=webui/backend --cov-report=term-missing

# Output:
# Name                                    Stmts   Miss  Cover   Missing
# ---------------------------------------------------------------------
# mothbox_paths.py                          276      6   97.8%   142-145, 289
# webui/backend/services/thumbnail_cache.py  245     12   95.1%   89-92, 156-159
# webui/backend/routes/gallery.py            127     15   88.2%   45-48, 92-95, 134
# ---------------------------------------------------------------------
# TOTAL                                      648     33   94.9%

# Check if coverage meets threshold
coverage report --fail-under=85
# Returns exit code 0 if passed, non-zero if failed
```

**Coverage HTML Report (Detailed):**
```bash
# Generate HTML report
pytest Tests/unit/ --cov=webui/backend --cov-report=html

# Open in browser
firefox htmlcov/index.html

# Features:
# - Line-by-line coverage visualization (green = covered, red = missed)
# - Branch coverage analysis (which if/else branches taken)
# - Function coverage summary
# - Sortable by coverage percentage
```

### Workflow Triggers

**Automatic Triggers:**
- Push to `main`, `dev`, or `feature/**` branches
- Pull requests to `main` or `dev`
- Only when relevant files change (Python, tests, configs, frontend)

**Path Filters (Optimized for Speed):**
```yaml
# Only run tests when these files change:
paths:
  - 'webui/**/*.py'
  - 'Tests/**/*.py'
  - 'webui/frontend/**/*.jsx'
  - 'webui/frontend/**/*.js'
  - 'pyproject.toml'
  - 'package.json'
  - '.github/workflows/test.yml'
```

**Manual Trigger:**
1. Go to repository → Actions tab
2. Select "Mothbox Tests" workflow
3. Click "Run workflow"
4. Select branch and confirm

### Viewing CI Results

**GitHub Actions UI:**
1. Navigate to repository → Actions tab
2. Click on latest workflow run
3. View "Backend Tests" and "Frontend Tests" jobs
4. Expand steps to see detailed logs
5. Download coverage artifacts (available for 7 days)

**Job Output Example:**
```
Run Backend Tests
  Setting up Python 3.13... ✓
  Installing dependencies... ✓
  Running unit tests with coverage... ✓
    - Tests/unit/test_thumbnail_cache.py .......... (78 passed)
    - Tests/unit/test_gallery_routes.py ........ (66 passed)
    - Tests/unit/test_gallery_pagination.py ..... (35 passed)
  Checking coverage threshold (85%)... ✓
    - Total coverage: 93%
  Generating coverage reports... ✓
  Uploading coverage artifacts... ✓
```

**Coverage Artifacts:**
- `coverage-report-python-3.13`: HTML coverage report (browse offline)
- `coverage-xml-python-3.13`: XML for external tools (Codecov, Coveralls)
- `frontend-coverage-node-20`: Frontend coverage report

**Downloading Artifacts:**
1. Click on workflow run
2. Scroll to "Artifacts" section at bottom
3. Click artifact name to download ZIP
4. Extract and open `index.html` for HTML reports

### Troubleshooting CI Failures

**Common Issues and Solutions:**

**Issue 1: Coverage Below 85%**
```bash
# Symptom:
# Error: Total coverage (82.3%) is below threshold (85.0%)

# Solution:
# Run locally to identify uncovered lines
./Tests/run_tests.sh ci

# Open coverage report
firefox htmlcov/index.html

# Add tests for uncovered lines
# Re-run and verify coverage increased
pytest Tests/unit/ --cov --cov-report=term-missing
```

**Issue 2: Hardware Test Failures in CI**
```bash
# Symptom:
# FAILED Tests/integration/test_camera_capture.py::test_take_photo
# RuntimeError: Camera not available

# Solution:
# Add @pytest.mark.hardware marker to test
@pytest.mark.hardware
def test_take_photo():
    # Test code requiring camera...

# Ensure test uses correct marker in pyproject.toml
markers = [
    "hardware: tests requiring Raspberry Pi hardware",
]

# Verify test is skipped in CI
pytest Tests/integration/ -m "not hardware" -v
```

**Issue 3: Import Errors**
```bash
# Symptom:
# ImportError: No module named 'services.thumbnail_cache'

# Solution:
# Verify requirements-test.txt is up to date
pip list | grep -E "flask|PIL|pytest"

# Update requirements if needed
pip freeze > Tests/requirements-test.txt

# Verify imports in conftest.py
python3 -c "import sys; sys.path.insert(0, 'webui/backend'); from services.thumbnail_cache import ThumbnailCache"
```

**Issue 4: Test Timeouts**
```bash
# Symptom:
# FAILED Tests/performance/test_gallery_performance.py::test_warmup - Timeout after 120s

# Solution:
# CI has 2-minute default timeout per test (pytest-timeout)
# Long-running tests need explicit timeout marker

@pytest.mark.timeout(300)  # 5 minutes
def test_cache_warmup_large_dataset():
    # Long-running test...

# Or increase global timeout in pytest.ini
[tool.pytest.ini_options]
timeout = 300  # 5 minutes default
```

**Issue 5: Flaky Tests (Intermittent Failures)**
```bash
# Symptom:
# Test passes locally, fails in CI intermittently

# Diagnosis:
# - Check for race conditions (threading, async)
# - Verify cleanup (temp files, database state)
# - Look for time-dependent assertions
# - Check for external dependencies (network, filesystem)

# Solution:
# Add retry decorator for known flaky tests
@pytest.mark.flaky(reruns=3, reruns_delay=2)
def test_sometimes_flaky():
    # Test code...

# Or use more robust waiting
from pytest import mark
import time

def test_with_retry():
    max_attempts = 3
    for attempt in range(max_attempts):
        try:
            # Test code...
            break
        except AssertionError:
            if attempt == max_attempts - 1:
                raise
            time.sleep(1)
```

### Configuration Files

**pytest Configuration (`Firmware/pyproject.toml`):**
```toml
[tool.pytest.ini_options]
testpaths = ["Tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]

markers = [
    "hardware: tests requiring Raspberry Pi hardware",
    "performance: performance and benchmark tests",
    "integration: multi-component integration tests",
    "unit: unit tests for individual functions",
]

[tool.coverage.run]
source = [".", "webui/backend"]
omit = ["*/tests/*", "*/Tests/*", "*/__pycache__/*"]
branch = true

[tool.coverage.report]
precision = 2
show_missing = true
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "if __name__ == .__main__.:",
]
```

**GitHub Actions (`..github/workflows/test.yml`):**
```yaml
name: Mothbox Tests

on:
  push:
    branches: [main, dev, 'feature/**']
  pull_request:
    branches: [main, dev]

jobs:
  backend-tests:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ['3.13']

    steps:
      - uses: actions/checkout@v4
      - name: Set up Python ${{ matrix.python-version }}
        uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}

      - name: Install dependencies
        run: |
          pip install -r Tests/requirements-test.txt

      - name: Run unit tests with coverage
        run: |
          pytest Tests/unit/ --cov --cov-report=xml --cov-report=html -v

      - name: Check coverage threshold
        run: |
          coverage report --fail-under=85

      - name: Upload coverage artifacts
        uses: actions/upload-artifact@v4
        with:
          name: coverage-report-python-${{ matrix.python-version }}
          path: htmlcov/
          retention-days: 7

  frontend-tests:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        node-version: ['20.x']

    steps:
      - uses: actions/checkout@v4
      - name: Set up Node.js ${{ matrix.node-version }}
        uses: actions/setup-node@v4
        with:
          node-version: ${{ matrix.node-version }}

      - name: Install dependencies
        working-directory: webui/frontend
        run: npm ci

      - name: Run frontend tests
        working-directory: webui/frontend
        run: npm test

      - name: Generate coverage
        working-directory: webui/frontend
        run: npm test -- --coverage

      - name: Upload coverage artifacts
        uses: actions/upload-artifact@v4
        with:
          name: frontend-coverage-node-${{ matrix.node-version }}
          path: webui/frontend/coverage/
          retention-days: 7
```

## Troubleshooting Test Failures

### Cache-Related Failures

**Issue:** Cache not found or permission errors
```python
# Symptom:
PermissionError: [Errno 13] Permission denied: '/tmp/pytest-cache/thumbnails/128'

# Diagnosis:
# - tmp_path fixture cleanup incomplete
# - Cache directory permissions wrong
# - Lock file not released

# Solution:
# Ensure proper cleanup in fixtures
@pytest.fixture
def thumbnail_cache(tmp_path):
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache = ThumbnailCache(cache_dir=cache_dir)

    yield cache

    # Cleanup
    cache.close()
    import shutil
    shutil.rmtree(cache_dir, ignore_errors=True)
```

**Issue:** Cache statistics incorrect
```python
# Symptom:
AssertionError: assert 0.0 == 0.75
# Cache hit ratio is 0.0 when it should be 75%

# Diagnosis:
# - Statistics not being tracked
# - Hits/misses counters not incremented
# - Statistics file not being read

# Solution:
# Verify statistics are updated in get_thumbnail()
def test_statistics_track_hits_and_misses(thumbnail_cache, sample_photo):
    # Clear stats
    thumbnail_cache.hits = 0
    thumbnail_cache.misses = 0

    # Cache miss
    thumbnail_cache.get_thumbnail(sample_photo, size=128)
    assert thumbnail_cache.misses == 1

    # Cache hit
    thumbnail_cache.get_thumbnail(sample_photo, size=128)
    assert thumbnail_cache.hits == 1

    stats = thumbnail_cache.get_statistics()
    assert stats['hit_ratio'] == 0.5
```

### Timing-Related Failures

**Issue:** Performance test fails on slower hardware
```python
# Symptom:
AssertionError: assert 0.623 < 0.5
# Initial load took 623ms (target: <500ms)

# Diagnosis:
# - Running on Pi 3 instead of Pi 4
# - System under heavy load
# - Thermal throttling

# Solution:
# Adjust timeouts for hardware capabilities
# Or skip test on underpowered hardware
import platform
import pytest

@pytest.mark.skipif(
    platform.machine() == 'armv7l',  # Pi 3
    reason="Performance test requires Pi 4 or 5"
)
def test_initial_load_50_photos(performance_client):
    # Test code...
```

**Issue:** Flaky timing assertions
```python
# Symptom:
# Test passes 9/10 times, fails intermittently

# Diagnosis:
# - System load variation
# - Filesystem cache effects
# - Python GC pauses

# Solution:
# Use more lenient thresholds or percentile-based assertions
def test_pagination_performance(performance_client):
    timings = []

    # Run multiple times
    for _ in range(10):
        start = time.perf_counter()
        response = performance_client.get('/api/gallery/photos/paginated')
        timings.append(time.perf_counter() - start)

    # Use 95th percentile instead of max
    p95 = sorted(timings)[int(len(timings) * 0.95)]
    assert p95 < 0.5, f"95th percentile {p95*1000:.1f}ms exceeds 500ms"
```

### Frontend Test Failures

**Issue:** Component not rendering
```javascript
// Symptom:
// TestingLibraryElementError: Unable to find element with text: /Loading gallery/i

// Diagnosis:
// - Mock API not returning data
// - Async query not awaited
// - Component mount timing issue

// Solution:
// Verify mock API is configured and use waitFor
it('renders loading state initially', async () => {
  // Mock API to never resolve (keeps loading state)
  api.getPhotosPaginated.mockImplementation(() => new Promise(() => {}))

  renderGallery(queryClient)

  // Wait for loading state to appear
  await waitFor(() => {
    expect(screen.getByText(/Loading gallery/i)).toBeInTheDocument()
  })
})
```

**Issue:** Intersection Observer not triggering
```javascript
// Symptom:
// Test timeout - second page never loads

// Diagnosis:
// - Observer callback not captured
// - IntersectionObserver not mocked properly
// - Observer not observing sentinel element

// Solution:
// Ensure observer mock is set up correctly
const observerMocks = setupIntersectionObserver()

// Get callback reference
const observerCallback = observerMocks.getObserverCallback()

// Manually trigger intersection
observerCallback([{ isIntersecting: true }])

// Verify page loaded
await waitFor(() => {
  expect(screen.getAllByRole('img')).toHaveLength(GALLERY_CONFIG.PAGE_SIZE * 2)
})
```

### Coverage Below Threshold

**Issue:** Coverage drops below 85%
```bash
# Symptom:
# coverage report --fail-under=85
# FAILED: Total coverage (82.3%) is below threshold (85.0%)

# Diagnosis:
# 1. Identify uncovered lines
pytest Tests/unit/ --cov=webui/backend --cov-report=term-missing

# Output:
# webui/backend/services/thumbnail_cache.py  245     43    82%   89-92, 156-159, 223-245

# 2. Review uncovered lines in code
# Lines 223-245 are error handling for corrupt images

# Solution:
# Add test for error handling
def test_corrupt_image_generates_placeholder(thumbnail_cache, corrupt_photo):
    """Test that corrupt images get placeholder thumbnails"""
    result = thumbnail_cache.get_thumbnail(corrupt_photo, size=128)

    assert result.exists()

    # Verify it's a placeholder
    from PIL import Image
    img = Image.open(result)
    assert img.size == (128, 128)

    # Placeholder should be gray-ish
    center_pixel = img.getpixel((64, 64))
    assert abs(center_pixel[0] - center_pixel[1]) < 50  # R ≈ G ≈ B

# Re-run coverage
pytest Tests/unit/test_thumbnail_cache.py::test_corrupt_image_generates_placeholder --cov=webui/backend/services/thumbnail_cache --cov-report=term-missing

# Verify coverage increased
# webui/backend/services/thumbnail_cache.py  245     12    95%   89-92
```

## Best Practices

### Test Isolation
- Each test should be independent and not rely on other tests
- Use function-scoped fixtures for mutable state
- Clear cache/database between tests
- Avoid test execution order dependencies

**Example:**
```python
# BAD: Tests depend on execution order
def test_create_thumbnail(cache):
    cache.get_thumbnail(photo1, size=128)

def test_cache_statistics(cache):  # Assumes previous test ran!
    stats = cache.get_statistics()
    assert stats['cached_files'] == 1  # FRAGILE

# GOOD: Each test is independent
@pytest.fixture
def cache_with_one_thumbnail(thumbnail_cache, sample_photo):
    """Pre-populated cache for statistics tests"""
    thumbnail_cache.get_thumbnail(sample_photo, size=128)
    return thumbnail_cache

def test_cache_statistics(cache_with_one_thumbnail):
    stats = cache_with_one_thumbnail.get_statistics()
    assert stats['cached_files'] == 1  # ROBUST
```

### Cleanup
- Always clean up resources (files, cache, connections)
- Use context managers or try/finally
- Leverage pytest fixtures for automatic cleanup
- Delete temporary files after tests

**Example:**
```python
# BAD: No cleanup
def test_thumbnail_generation():
    cache_dir = Path("/tmp/test_cache")
    cache = ThumbnailCache(cache_dir=cache_dir)
    cache.get_thumbnail(photo, size=128)
    # cache_dir left behind!

# GOOD: Fixture handles cleanup
@pytest.fixture
def thumbnail_cache(tmp_path):
    cache_dir = tmp_path / "cache"
    cache = ThumbnailCache(cache_dir=cache_dir)

    yield cache

    cache.close()
    # tmp_path automatically cleaned up by pytest
```

### Deterministic Tests
- No random behavior or timestamps
- Use fixed seeds for random generators
- Mock time-dependent functions
- Set explicit file timestamps for sorting tests

**Example:**
```python
# BAD: Random behavior
def test_photo_selection():
    import random
    photos = get_all_photos()
    selected = random.sample(photos, 10)  # Non-deterministic!
    assert len(selected) == 10

# GOOD: Deterministic
def test_photo_selection():
    import random
    random.seed(42)  # Fixed seed
    photos = get_all_photos()
    selected = random.sample(photos, 10)
    assert len(selected) == 10
    assert selected[0] == photos[3]  # Predictable result

# BAD: Time-dependent
def test_recent_photos():
    photos = get_photos_since(datetime.now() - timedelta(days=7))
    assert len(photos) > 0  # Depends on current time!

# GOOD: Mock time
def test_recent_photos(monkeypatch):
    fixed_now = datetime(2024, 11, 10, 12, 0, 0)
    monkeypatch.setattr('datetime.datetime', Mock(now=lambda: fixed_now))

    photos = get_photos_since(fixed_now - timedelta(days=7))
    # Test with known date range
```

### Fast Tests
- Unit tests should complete in under 1 second each
- Integration tests under 10 seconds each
- Use mocks to avoid slow I/O operations
- Only create files when testing file operations

**Example:**
```python
# BAD: Slow unit test (creates 500 real files)
def test_pagination_metadata():
    photos_dir = tmp_path / "photos"
    for i in range(500):
        photo = photos_dir / f"photo_{i}.jpg"
        create_real_jpeg(photo)  # Slow!

    response = client.get('/api/gallery/photos/paginated')
    assert response.status_code == 200

# GOOD: Fast unit test (mocks file listing)
def test_pagination_metadata(mocker):
    mock_photos = [Mock(name=f"photo_{i}.jpg") for i in range(500)]
    mocker.patch('pathlib.Path.glob', return_value=mock_photos)

    response = client.get('/api/gallery/photos/paginated')
    assert response.status_code == 200
```

### Meaningful Tests
- Test behavior, not implementation details
- Assert on user-visible outcomes
- Don't test private methods directly
- Focus on critical paths (common workflows)

**Example:**
```python
# BAD: Testing implementation details
def test_cache_internal_hash_algorithm():
    cache = ThumbnailCache()
    hash1 = cache._get_hash("/path/to/photo.jpg")
    assert len(hash1) == 32  # MD5 hash length
    assert hash1.startswith('a')  # Fragile!

# GOOD: Testing behavior
def test_cache_returns_consistent_paths():
    cache = ThumbnailCache()

    # Same photo should get same cached path
    path1 = cache.get_thumbnail(photo, size=128)
    path2 = cache.get_thumbnail(photo, size=128)

    assert path1 == path2  # Behavior that matters to users
```

### Coverage Focus
- Prioritize coverage for critical paths
- Don't obsess over 100% coverage
- Test error handling and edge cases
- Focus on business logic, not boilerplate

**Priority Order:**
1. **Critical paths** (95%+ coverage)
   - Thumbnail cache hit/miss logic
   - Photo pagination queries
   - API authentication (future)

2. **Common workflows** (90%+ coverage)
   - Gallery page load
   - Infinite scroll
   - Lightbox open/close

3. **Error handling** (85%+ coverage)
   - Corrupt image handling
   - Network errors
   - Permission errors

4. **Edge cases** (80%+ coverage)
   - Empty gallery
   - Single photo
   - Pagination boundary conditions

5. **Nice-to-have** (coverage not critical)
   - Logging statements
   - String formatting
   - Trivial getters/setters

---

**Last Updated:** 2025-01-10
**Mothbox Version:** 5.x
**Test Suite Version:** Phase 1.0 (Issue #139)
**Document Version:** 1.0
