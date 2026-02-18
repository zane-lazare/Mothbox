# PR #432 Review Fixes — Design

**Date**: 2026-02-18
**PR**: #432 (sensor pre-condition UI)
**Reviewer**: claude[bot]

## Context

Four recommendations from the PR #432 code review. Each analyzed against the existing codebase to determine what's actually needed vs. what's already covered.

## Recommendation 1: Time Window Same-Time Validation

**Problem**: No validation when start_time == end_time (zero-duration window).

**Decision**: Add `timeWindowError` state to PreConditionForm. Show error when both times are identical. Do NOT validate start > end — overnight windows (21:00→06:00) are valid by design, matching IntervalTriggerForm and backend behavior.

**Changes**:
- `PreConditionForm.jsx`: Add `timeWindowError` state, validate in `handleTimeWindowChange`, clear on toggle off
- Error message: "Start and end times cannot be the same" (from `TIME_ERRORS`)

## Recommendation 2: Remove eslint-disable Comment

**Problem**: `RoutineCard.test.jsx:43` destructures unused `routineIndex` with eslint-disable comment.

**Decision**: Remove the parameter from destructuring. One-line fix.

## Recommendation 3: Cooldown Edge Case Tests

**Problem**: Cooldown validation uses `validateNumericInput` (which handles all edge cases), but tests only cover below-min and above-max.

**Decision**: Add 3 tests for cooldown edge cases:
- Non-numeric input (`'abc'`) → error
- Empty input → error
- Decimal input (`'5.5'`) → accepted (valid number in range)

## Recommendation 4: Time Window Test Cases

**Problem**: No tests for the new same-time validation.

**Decision**: Add 3 tests:
- Same start/end time shows error
- Error clears when times changed to be different
- Time window with empty start/end renders gracefully
