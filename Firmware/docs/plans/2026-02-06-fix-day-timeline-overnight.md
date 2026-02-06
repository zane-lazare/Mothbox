# Fix Day Timeline Overnight Schedule Display

## Problem

The DayTimeline component filters executions by strict calendar date. For overnight
schedules (dusk-to-dawn), the post-midnight entries (00:00-06:00) belong to the next
calendar day. Viewing Feb 6 shows 21:00-23:59 with entries, then 0:00-6:00 as empty
("no executions"), even though the schedule runs continuously through the night.

The week view already handles this correctly by shifting post-midnight entries to the
previous day's column (`weekTimelineUtils.js:133-144`).

## Fix

In `DayTimeline.jsx`, update the `filteredExecutions` filter: when
`cycleInfo.spans_midnight` is true, also include next-day entries where
`hour <= end_hour`. Add a `getNextDateKey()` utility to `dayTimelineUtils.js`.

## Scope

- DayTimeline day view only (2 files, ~15 lines)
- Month view counts unchanged (strict calendar date)
- Week view already correct (no change)
- Backend/API unchanged (data is correct)
