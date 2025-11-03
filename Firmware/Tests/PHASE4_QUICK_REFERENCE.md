# Phase 4 Testing Quick Reference

## Running Tests

### Run All Tests
```bash
python3 -m pytest Tests/unit/test_capture_focus_bracket_unit.py Tests/regression/test_focus_bracket_regression.py -v
```

### Run Edge Case Tests Only
```bash
python3 -m pytest Tests/unit/test_capture_focus_bracket_unit.py::TestEdgeCases -v
```

### Run Error Handling Tests Only
```bash
python3 -m pytest Tests/unit/test_capture_focus_bracket_unit.py::TestErrorHandling -v
```

### Run Regression Tests Only
```bash
python3 -m pytest Tests/regression/test_focus_bracket_regression.py -v
```

### Run Specific Test
```bash
python3 -m pytest Tests/unit/test_capture_focus_bracket_unit.py::TestEdgeCases::test_focus_bracket_boundary_focus_minimum -v
```

---

## Test Count Summary

| Category | Tests | Location |
|----------|-------|----------|
| Edge Cases | 9 | `test_capture_focus_bracket_unit.py::TestEdgeCases` |
| Error Handling | 6 | `test_capture_focus_bracket_unit.py::TestErrorHandling` |
| Regression | 3 | `test_focus_bracket_regression.py::TestHistoricalBugs` |
| **Phase 4 Total** | **18** | |
| **All Phases Total** | **64 passing, 10 skipped** | |

---

## Edge Case Tests (9)

1. **test_focus_bracket_boundary_focus_minimum** - Focus at 0.0 diopters (infinity)
2. **test_focus_bracket_boundary_focus_maximum** - Focus at 10.0 diopters (macro)
3. **test_focus_bracket_zero_delays** - All timing delays at 0ms
4. **test_focus_bracket_maximum_delays** - Max delays (settle=2000ms, flash=500ms)
5. **test_focus_bracket_extreme_color_gains_minimum** - Gains at 1.0
6. **test_focus_bracket_extreme_color_gains_maximum** - Gains at 4.0
7. **test_focus_bracket_very_long_computer_name** - 200+ character name
8. **test_focus_bracket_maximum_steps** - 10 step bracket (maximum)
9. **test_focus_bracket_full_range_single_step** - Single step with full range

---

## Error Handling Tests (6)

1. **test_focus_bracket_file_save_error_handling** - Disk full simulation
2. **test_focus_bracket_request_release_always_called** - Resource cleanup verification
3. **test_focus_bracket_camera_start_error** - Camera initialization failure
4. **test_calculate_focus_positions_invalid_steps** - Steps validation (0, -1, 11, "5")
5. **test_calculate_focus_positions_invalid_focus_range** - Focus range validation
6. **test_focus_bracket_empty_camera_settings_dict** - Empty settings handling

---

## Regression Tests (3)

1. **test_regression_line_109_undefined_root_variable**
   - **Bug**: Line 109 used undefined 'root' variable
   - **Fixed**: 2025-11-02
   - **Impact**: Script crashed on external media detection

2. **test_regression_color_gains_tuple_format**
   - **Type**: Preventive
   - **Ensures**: Color gains remain as tuple (red, blue)
   - **Impact if broken**: TypeError during capture

3. **test_regression_request_release_leak**
   - **Type**: Preventive
   - **Ensures**: All requests are released
   - **Impact if broken**: Memory leak in long sessions

---

## Performance Benchmarks

- **Total Runtime**: ~2.9 seconds (64 tests)
- **Edge Cases**: ~0.4 seconds (9 tests)
- **Error Handling**: ~0.2 seconds (6 tests)
- **Regression**: ~0.1 seconds (3 tests)
- **Target**: <30 seconds ✅ (10x better)

---

## Key Findings

### ✅ Working Correctly
- Boundary focus values (0.0 and 10.0 diopters)
- Zero and maximum delays
- Extreme color gains (1.0 and 4.0)
- Very long computer names
- Maximum step count (10)
- Input validation (proper ValueError messages)

### ⚠️ Known Limitations
- **Request cleanup on error**: No try/finally block means request not released if save() fails
- **Main() tests skipped**: 10 tests need refactoring to run
- **CSV BOM handling**: Not yet tested (add if needed)

---

## Adding New Regression Tests

When you discover a bug:

1. **Fix the bug** in the source code
2. **Add regression test** to `Tests/regression/test_focus_bracket_regression.py`
3. **Document the bug** with:
   - Bug description (what broke)
   - Impact statement (severity)
   - Root cause explanation
   - Fix description and date
   - Test verification strategy

### Template:
```python
def test_regression_YOUR_BUG_NAME(self, ...):
    """
    Regression test for [bug description]
    
    BUG DESCRIPTION:
    [What broke and how]
    
    CODE: [broken code]
    FIX:  [fixed code]
    
    IMPACT:
    [What happened to users]
    
    ROOT CAUSE:
    [Why it happened]
    
    TEST VERIFIES:
    [What this test checks]
    
    Related: Issue #XX
    Fixed: YYYY-MM-DD
    """
    # Test implementation
```

---

## Test Maintenance

### Monthly Checklist
- [ ] Review new bugs for regression test candidates
- [ ] Check test runtime stays under 5 seconds
- [ ] Update documentation for new test patterns
- [ ] Verify all regression tests still pass

### When Refactoring
- [ ] Keep all regression tests (NEVER delete)
- [ ] Update test implementation if needed
- [ ] Maintain test documentation accuracy
- [ ] Verify no performance regression

---

## Contact & Support

For questions about Phase 4 testing:
- See: `Tests/PHASE4_SUMMARY.md` for complete details
- See: `Tests/unit/test_capture_focus_bracket_unit.py` docstring for test organization
- See: `Tests/regression/test_focus_bracket_regression.py` for regression test examples

**Related**: Issue #13 Phase 4 - Focus bracket testing
**Date**: 2025-11-03
