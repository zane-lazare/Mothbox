/**
 * Tests for WeekHourlyTimeline utility functions (#387)
 *
 * TIMEZONE HANDLING: Uses local time (no Z suffix) for timezone-agnostic tests.
 */

import { describe, it, expect } from 'vitest'
import {
  groupExecutionsByDayAndHour,
  getConflictsForDay,
  buildExecutionConflictsMap,
} from '../weekTimelineUtils'

// Helper to create week dates starting from a given Monday
function makeWeekDates(startDateStr) {
  const dates = []
  const start = new Date(startDateStr + 'T00:00:00')
  for (let i = 0; i < 7; i++) {
    const d = new Date(start)
    d.setDate(d.getDate() + i)
    dates.push(d)
  }
  return dates
}

describe('weekTimelineUtils', () => {
  describe('groupExecutionsByDayAndHour', () => {
    const weekDates = makeWeekDates('2025-01-13') // Mon-Sun

    it('returns empty object for null/undefined executions', () => {
      expect(groupExecutionsByDayAndHour(null, weekDates)).toEqual({})
      expect(groupExecutionsByDayAndHour(undefined, weekDates)).toEqual({})
    })

    it('returns empty day buckets for empty array', () => {
      const result = groupExecutionsByDayAndHour([], weekDates)
      expect(Object.keys(result)).toHaveLength(7)
      Object.values(result).forEach(hours => {
        expect(Object.keys(hours)).toHaveLength(0)
      })
    })

    it('groups single execution by date and hour', () => {
      const execs = [
        { pattern_id: 'p1', start_time: '2025-01-15T18:30:00' },
      ]
      const result = groupExecutionsByDayAndHour(execs, weekDates)
      expect(result['2025-01-15'][18]).toHaveLength(1)
      expect(result['2025-01-15'][18][0].pattern_id).toBe('p1')
    })

    it('groups multiple executions in same hour', () => {
      const execs = [
        { pattern_id: 'p1', start_time: '2025-01-15T18:00:00' },
        { pattern_id: 'p2', start_time: '2025-01-15T18:30:00' },
      ]
      const result = groupExecutionsByDayAndHour(execs, weekDates)
      expect(result['2025-01-15'][18]).toHaveLength(2)
    })

    it('groups executions across different days', () => {
      const execs = [
        { pattern_id: 'p1', start_time: '2025-01-13T10:00:00' },
        { pattern_id: 'p2', start_time: '2025-01-14T10:00:00' },
      ]
      const result = groupExecutionsByDayAndHour(execs, weekDates)
      expect(result['2025-01-13'][10]).toHaveLength(1)
      expect(result['2025-01-14'][10]).toHaveLength(1)
    })

    it('skips executions outside the week', () => {
      const execs = [
        { pattern_id: 'p1', start_time: '2025-01-12T10:00:00' },
        { pattern_id: 'p2', start_time: '2025-01-20T10:00:00' },
      ]
      const result = groupExecutionsByDayAndHour(execs, weekDates)
      Object.values(result).forEach(hours => {
        expect(Object.keys(hours)).toHaveLength(0)
      })
    })

    it('deduplicates same pattern_id at same time', () => {
      const execs = [
        { pattern_id: 'p1', start_time: '2025-01-15T18:00:00' },
        { pattern_id: 'p1', start_time: '2025-01-15T18:00:00' },
      ]
      const result = groupExecutionsByDayAndHour(execs, weekDates)
      expect(result['2025-01-15'][18]).toHaveLength(1)
    })

    it('skips executions with missing start_time', () => {
      const execs = [
        { pattern_id: 'p1' },
        { pattern_id: 'p2', start_time: null },
      ]
      const result = groupExecutionsByDayAndHour(execs, weekDates)
      Object.values(result).forEach(hours => {
        expect(Object.keys(hours)).toHaveLength(0)
      })
    })

    describe('overnight schedules', () => {
      it('shifts post-midnight executions to previous day', () => {
        const cycleInfo = { start_hour: 21, end_hour: 5 }
        const execs = [
          { pattern_id: 'p1', start_time: '2025-01-14T02:00:00' },
        ]
        const result = groupExecutionsByDayAndHour(execs, weekDates, cycleInfo)
        expect(result['2025-01-13'][2]).toHaveLength(1)
        expect(result['2025-01-14'][2] || []).toHaveLength(0)
      })

      it('skips post-midnight on first day of week (belongs to previous week)', () => {
        const cycleInfo = { start_hour: 21, end_hour: 5 }
        const execs = [
          { pattern_id: 'p1', start_time: '2025-01-13T03:00:00' },
        ]
        const result = groupExecutionsByDayAndHour(execs, weekDates, cycleInfo)
        expect(result['2025-01-13'][3] || []).toHaveLength(0)
      })

      it('does not shift executions outside overnight window', () => {
        const cycleInfo = { start_hour: 21, end_hour: 5 }
        const execs = [
          { pattern_id: 'p1', start_time: '2025-01-14T22:00:00' },
        ]
        const result = groupExecutionsByDayAndHour(execs, weekDates, cycleInfo)
        expect(result['2025-01-14'][22]).toHaveLength(1)
      })
    })
  })

  describe('getConflictsForDay', () => {
    it('returns empty array for null/undefined conflicts', () => {
      expect(getConflictsForDay(null, '2025-01-15')).toEqual([])
      expect(getConflictsForDay(undefined, '2025-01-15')).toEqual([])
    })

    it('returns empty array for null dateKey', () => {
      expect(getConflictsForDay([{ start_time: '2025-01-15T10:00:00' }], null)).toEqual([])
    })

    it('returns empty array for non-array conflicts', () => {
      expect(getConflictsForDay('not-array', '2025-01-15')).toEqual([])
    })

    it('filters conflicts matching the date', () => {
      const conflicts = [
        { start_time: '2025-01-15T10:00:00', id: 'c1' },
        { start_time: '2025-01-16T10:00:00', id: 'c2' },
        { start_time: '2025-01-15T22:00:00', id: 'c3' },
      ]
      const result = getConflictsForDay(conflicts, '2025-01-15')
      expect(result).toHaveLength(2)
      expect(result.map(c => c.id)).toEqual(['c1', 'c3'])
    })

    it('skips conflicts with missing start_time', () => {
      const conflicts = [
        { id: 'c1' },
        { start_time: null, id: 'c2' },
        { start_time: '2025-01-15T10:00:00', id: 'c3' },
      ]
      const result = getConflictsForDay(conflicts, '2025-01-15')
      expect(result).toHaveLength(1)
    })
  })

  describe('buildExecutionConflictsMap', () => {
    it('returns empty object for null inputs', () => {
      expect(buildExecutionConflictsMap(null, [])).toEqual({})
      expect(buildExecutionConflictsMap([], null)).toEqual({})
    })

    it('maps execution to conflict by event1_id', () => {
      const execs = [{ pattern_id: 'r1', start_time: '2025-01-15T10:00:00' }]
      const conflicts = [{ event1_id: 'r1', event2_id: 'r2', start_time: '2025-01-15T10:00:00' }]
      const result = buildExecutionConflictsMap(execs, conflicts)
      expect(result['r1']).toBeDefined()
      expect(result['r1'].event1_id).toBe('r1')
    })

    it('maps execution to conflict by event2_id', () => {
      const execs = [{ pattern_id: 'r2', start_time: '2025-01-15T10:00:00' }]
      const conflicts = [{ event1_id: 'r1', event2_id: 'r2', start_time: '2025-01-15T10:00:00' }]
      const result = buildExecutionConflictsMap(execs, conflicts)
      expect(result['r2']).toBeDefined()
    })

    it('maps execution to conflict by start_time', () => {
      const execs = [{ pattern_id: 'r3', start_time: '2025-01-15T10:00:00' }]
      const conflicts = [{ event1_id: 'r1', event2_id: 'r2', start_time: '2025-01-15T10:00:00' }]
      const result = buildExecutionConflictsMap(execs, conflicts)
      expect(result['r3']).toBeDefined()
    })

    it('does not map executions with no matching conflict', () => {
      const execs = [{ pattern_id: 'r5', start_time: '2025-01-15T12:00:00' }]
      const conflicts = [{ event1_id: 'r1', event2_id: 'r2', start_time: '2025-01-15T10:00:00' }]
      const result = buildExecutionConflictsMap(execs, conflicts)
      expect(result['r5']).toBeUndefined()
    })

    it('handles multiple executions with same conflict', () => {
      const execs = [
        { pattern_id: 'r1', start_time: '2025-01-15T10:00:00' },
        { pattern_id: 'r2', start_time: '2025-01-15T10:00:00' },
      ]
      const conflicts = [{ event1_id: 'r1', event2_id: 'r2', start_time: '2025-01-15T10:00:00' }]
      const result = buildExecutionConflictsMap(execs, conflicts)
      expect(result['r1']).toBeDefined()
      expect(result['r2']).toBeDefined()
    })
  })
})
