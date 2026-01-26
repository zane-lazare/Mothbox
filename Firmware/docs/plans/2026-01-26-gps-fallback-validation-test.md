# GPS Fallback Validation Route Test Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add route-level test verifying that invalid GPS coordinates from controls.txt fallback are rejected with 400 error.

**Architecture:** Mock `get_control_values()` to return invalid GPS coordinates, verify the route returns 400 with "Invalid coordinates" error message.

**Tech Stack:** pytest, unittest.mock, Flask test client

---

## Task 1: Add Route-Level Test for Invalid GPS Latitude from controls.txt

**Files:**
- Modify: `Tests/unit/test_scheduler_ui_routes.py` (add test to `TestActivateScheduleEndpoint` class, after line 1226)

**Step 1: Write the failing test**

Add this test method to the `TestActivateScheduleEndpoint` class:

```python
    def test_activate_rejects_invalid_gps_latitude_from_controls(
        self, client, mock_scheduler_service, sample_schedule
    ):
        """Test activation rejects invalid GPS latitude from controls.txt (Issue #385)."""
        module = _get_scheduler_ui_module()

        mock_scheduler_service.get_schedule.return_value = sample_schedule

        # Mock get_control_values to return invalid latitude (out of range)
        with patch.object(
            module,
            "get_control_values",
            return_value={"lat": "91.0", "lon": "0.0"},  # Invalid: lat > 90
        ):
            response = client.post(
                "/api/scheduler/ui/schedules/test-schedule/activate",
                json={},  # No explicit coordinates - will use GPS fallback
                content_type="application/json",
            )

        assert response.status_code == 400
        data = response.get_json()
        assert "Invalid coordinates" in data["error"]
```

**Step 2: Run test to verify it passes**

Run: `MOTHBOX_ENV=test SECRET_KEY="test-key" pytest Tests/unit/test_scheduler_ui_routes.py::TestActivateScheduleEndpoint::test_activate_rejects_invalid_gps_latitude_from_controls -v`

Expected: PASS (the fix was already implemented, test just confirms it works)

---

## Task 2: Add Route-Level Test for Invalid GPS Longitude from controls.txt

**Files:**
- Modify: `Tests/unit/test_scheduler_ui_routes.py` (add test after the previous one)

**Step 1: Write the test**

Add this test method to the `TestActivateScheduleEndpoint` class:

```python
    def test_activate_rejects_invalid_gps_longitude_from_controls(
        self, client, mock_scheduler_service, sample_schedule
    ):
        """Test activation rejects invalid GPS longitude from controls.txt (Issue #385)."""
        module = _get_scheduler_ui_module()

        mock_scheduler_service.get_schedule.return_value = sample_schedule

        # Mock get_control_values to return invalid longitude (out of range)
        with patch.object(
            module,
            "get_control_values",
            return_value={"lat": "45.0", "lon": "181.0"},  # Invalid: lon > 180
        ):
            response = client.post(
                "/api/scheduler/ui/schedules/test-schedule/activate",
                json={},  # No explicit coordinates - will use GPS fallback
                content_type="application/json",
            )

        assert response.status_code == 400
        data = response.get_json()
        assert "Invalid coordinates" in data["error"]
```

**Step 2: Run test to verify it passes**

Run: `MOTHBOX_ENV=test SECRET_KEY="test-key" pytest Tests/unit/test_scheduler_ui_routes.py::TestActivateScheduleEndpoint::test_activate_rejects_invalid_gps_longitude_from_controls -v`

Expected: PASS

---

## Task 3: Run All Scheduler UI Route Tests

**Step 1: Run full test suite to verify no regressions**

Run: `MOTHBOX_ENV=test SECRET_KEY="test-key" pytest Tests/unit/test_scheduler_ui_routes.py -v --tb=short`

Expected: All tests pass (including the 2 new tests)

---

## Task 4: Run Lint Check

**Step 1: Verify code style**

Run: `ruff check Tests/unit/test_scheduler_ui_routes.py`

Expected: No new errors (may have pre-existing issues unrelated to new code)

---

## Summary

This plan adds 2 new route-level tests to verify the GPS fallback validation fix from Issue #385:

| Test | What it validates |
|------|-------------------|
| `test_activate_rejects_invalid_gps_latitude_from_controls` | Latitude > 90 from controls.txt is rejected |
| `test_activate_rejects_invalid_gps_longitude_from_controls` | Longitude > 180 from controls.txt is rejected |

These tests complement the existing service-layer tests and provide end-to-end coverage of the validation fix.
