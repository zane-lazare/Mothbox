# Prompt for Continuing Phase 2 Backend Route Test Coverage

Use this prompt to start a new session and continue work on Issue #78.

---

## Session Continuation Prompt

```
I'm continuing work on Issue #78: "Add Unit Tests for Web UI Backend Routes" - a systematic effort to increase backend route test coverage to >85% overall.

**Current Branch**: `feature/issue-13-phase1-hardware-config-tests`
**Base branch for PRs**: `main`

**Completed Work (Phases 1, 2A, 2B):**

Phase 1 was completed previously with 75 tests across 4 modules (scheduler, preferences, gallery, system) achieving 87.62% average coverage.

**I just completed Phases 2A and 2B:**

1. ✅ **test_config_routes.py**: 68.59% → 85.36% (+16.77%, 12 new tests, 41 total)
   - Type conversion error handling, boolean/string/numeric validations
   - Endpoint error handling (500 errors)
   - Schedule backup restoration, copy settings edge cases

2. ✅ **test_gpio_routes.py**: 77.89% → 83.16% (+5.27%, 5 new tests, 34 total)
   - GPIO availability/permission checks
   - Missing relay state handling
   - Note: 90% target unreachable (17% module init code untestable)

3. ✅ **test_gps_routes.py**: 0% → 85.81% (46 new tests, 39 passing)
   - Adaptive timeout calculation (hot/warm/cold/almanac states)
   - GPS status/config/sync endpoints
   - Caching (2s TTL), file locking, security validations
   - **Latest commits**: `8a3c8a7` (Phases 2A & 2B), `eb96819` (Phase 2C structure)

4. 🚧 **test_presets_routes.py**: Started but needs work (25 tests created, 1 passing)
   - Tests structured but preset_manager module-level mocking needs fixing
   - Current coverage: 12.50%, target: 60-70%
   - File location: `Tests/unit/test_presets_routes.py`

**Total Completed**: 121 tests, 85%+ average coverage on 3 modules

---

**Next Steps (Priority Order):**

**Phase 2C - Fix Presets Tests** (~5-10 hours):
- File: `Tests/unit/test_presets_routes.py` (25 tests already created)
- Issue: `preset_manager` is instantiated at module level in `routes/presets.py` line 21
- Need to fix mocking strategy (patch before import or monkeypatch instance)
- Target: 60-70% coverage on presets.py (332 lines)
- Currently only 1/25 tests passing due to mocking issue

**Phase 2D - Camera Testing Infrastructure** (~8-10 hours, CRITICAL):
- Build fixtures in `Tests/conftest.py`:
  1. `mock_picamera2()` - Comprehensive Picamera2 mock
  2. `mock_subprocess_run()` - Factory for TakePhoto.py subprocess mocks
  3. `mock_socketio_emit()` - Track WebSocket emissions
  4. `temp_photos_dir()` - Isolated photo directory with samples
  5. `mock_camera_streamer()` - Full LiveViewStreamer mock
- This is critical foundation for Phase 2E-2I

**Phase 2E-2I - Camera Routes** (~55-69 hours):
- File: `webui/backend/routes/camera.py` (1,238 lines, 638 statements)
- Current coverage: 3.93% (only 25/638 statements)
- Target: 50-60% coverage (realistic, not 75%)
- 9 endpoints to test across 5 sub-phases:
  - Phase 2E: Settings endpoints (GET/POST /settings, freeze-settings)
  - Phase 2F: Basic capture (single-exposure only)
  - Phase 2G: HDR & focus bracket modes
  - Phase 2H: Autofocus & calibration
  - Phase 2I: Test capture workflows

---

**Established Testing Patterns (from Phases 1 & 2):**

1. **Mock external dependencies** at module level using `sys.modules` before importing
2. **Use `patch_path_constant_everywhere()`** for mothbox_paths constants
3. **Mock hardware**: RPi.GPIO (done), Picamera2 (partial - need more work)
4. **Mock subprocess** calls for external scripts (GPS.py, TakePhoto.py, systemd)
5. **Test security**: path traversal, command injection, CSV injection, input validation
6. **Use Flask test client** with `app.config['TESTING'] = True`
7. **Organize by endpoint** with class-based grouping
8. **Include error recovery** and edge case tests

**Key Code References:**
- Existing patterns: `Tests/unit/test_gpio_routes.py`, `Tests/unit/test_gps_routes.py`
- Fixtures: `Tests/conftest.py` (mock_rpi_gpio, temp file fixtures, patch_path_constant_everywhere)
- Routes: `webui/backend/routes/*.py`
- Coverage cmd: `python3 -m pytest Tests/unit/test_<module>_routes.py -v --cov=routes.<module> --cov-report=term-missing`

**Important Notes:**
- All tests must pass in CI without hardware dependencies
- GPS blueprint already registered in conftest.py (line 195, 208)
- Camera routes are VERY HIGH complexity - split into sub-phases
- Realistic timeline: ~90-100 hours remaining for full Phase 2 completion

---

**Where to Start:**

Option 1 (Quick Win): Fix preset tests in `Tests/unit/test_presets_routes.py`
- Problem: Module-level `preset_manager` instance (routes/presets.py:21)
- Solution: Patch before import or use monkeypatch to replace instance
- Expected: 60-70% coverage with 25 existing tests

Option 2 (Foundation): Build camera testing infrastructure (Phase 2D)
- Create 5 fixtures in Tests/conftest.py
- Highest ROI - unblocks all camera route testing
- Start with mock_picamera2 (most complex)

Option 3 (Continue Linear): Complete presets → infrastructure → camera routes

**Recommended**: Start with Option 1 (preset tests) for quick momentum, then Option 2 (infrastructure).

Let me know which approach you'd like to take, and I'll continue from there!
```

---

## Additional Context Files to Reference

When starting the new session, have the assistant read these files for full context:

1. **Test examples**:
   - `Tests/unit/test_gps_routes.py` - Most recent complete test suite (46 tests, 85.81% coverage)
   - `Tests/unit/test_config_routes.py` - Complex validation patterns (41 tests, 85.36% coverage)
   - `Tests/unit/test_gpio_routes.py` - Hardware mocking patterns (34 tests, 83.16% coverage)

2. **Code to test**:
   - `webui/backend/routes/presets.py` - Next target (332 lines, 12.50% coverage)
   - `webui/backend/routes/camera.py` - Major remaining work (1,238 lines, 3.93% coverage)

3. **Infrastructure**:
   - `Tests/conftest.py` - Existing fixtures and patterns (lines 190-210 for blueprint registration)

4. **Current branch state**:
   - Run: `git log --oneline -5` to see recent commits
   - Latest: `eb96819` (Phase 2C structure), `8a3c8a7` (Phase 2A & 2B complete)

---

## Quick Reference Commands

```bash
# Check current branch and status
git status
git log --oneline -5

# Run specific test file
python3 -m pytest Tests/unit/test_presets_routes.py -v --cov=routes.presets --cov-report=term-missing

# Run all existing tests
python3 -m pytest Tests/unit/ -v

# Count test totals
find Tests/unit -name "test_*.py" -exec grep -c "def test_" {} + | awk '{s+=$1} END {print s}'

# Check coverage for specific module
python3 -m pytest Tests/unit/test_<module>_routes.py --cov=routes.<module> --cov-report=term-missing
```

---

## Success Criteria for Next Session

**Minimum (Phase 2C)**:
- [ ] Fix preset_manager mocking in test_presets_routes.py
- [ ] Achieve 60-70% coverage on presets.py
- [ ] All 25 preset tests passing
- [ ] Commit with detailed metrics

**Stretch (Phase 2D Start)**:
- [ ] Create mock_picamera2 fixture in conftest.py
- [ ] Create mock_subprocess_run fixture
- [ ] Document usage patterns
- [ ] Write 1-2 simple camera route tests to validate fixtures

**Timeline**: 5-15 hours depending on scope
