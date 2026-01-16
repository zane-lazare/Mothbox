/**
 * Tests for DayTimeline utility functions (Issue #326)
 *
 * TIMEZONE HANDLING: These tests use local time expectations.
 * Times without 'Z' suffix are parsed as local time, making tests timezone-agnostic.
 * Times with 'Z' suffix are UTC and will be converted to local time.
 */

import { describe, it, expect } from 'vitest'
import {
  getHourFromIsoTime,
  getMinuteFromIsoTime,
  formatHourLabel,
  formatTimeShort,
  groupExecutionsByHour,
  getConflictForHour,
  getActionTypeDisplay,
  countConflictsBySeverity,
  getConflictForExecution,
  getExecutionKey,
  getExecutionTestId,
} from '../dayTimelineUtils'

describe('dayTimelineUtils', () => {
  describe('getHourFromIsoTime', () => {
    it('extracts hour from local time string (no Z suffix)', () => {
      // Times without Z are parsed as local time
      expect(getHourFromIsoTime('2025-12-17T18:30:00')).toBe(18)
      expect(getHourFromIsoTime('2025-12-17T00:00:00')).toBe(0)
      expect(getHourFromIsoTime('2025-12-17T23:59:59')).toBe(23)
    })

    it('converts UTC time to local hour', () => {
      // Times with Z are UTC and converted to local
      // Just verify it returns a valid hour (0-23)
      const hour = getHourFromIsoTime('2025-12-17T18:30:00Z')
      expect(hour).toBeGreaterThanOrEqual(0)
      expect(hour).toBeLessThanOrEqual(23)
    })

    it('returns null for invalid input', () => {
      expect(getHourFromIsoTime(null)).toBeNull()
      expect(getHourFromIsoTime(undefined)).toBeNull()
      expect(getHourFromIsoTime('')).toBeNull()
      expect(getHourFromIsoTime('invalid')).toBeNull()
      expect(getHourFromIsoTime(123)).toBeNull()
    })

    describe('ISO format handling', () => {
      it('handles various ISO formats', () => {
        // Date parsing handles these formats
        expect(getHourFromIsoTime('2025-12-17T18:30:00')).toBe(18)
        expect(getHourFromIsoTime('2025-12-17T18:30:00.123')).toBe(18)
      })

      it('returns null for completely invalid formats', () => {
        expect(getHourFromIsoTime('not-a-date')).toBeNull()
      })
    })
  })

  describe('getMinuteFromIsoTime', () => {
    it('extracts minute from local time string', () => {
      expect(getMinuteFromIsoTime('2025-12-17T18:30:00')).toBe(30)
      expect(getMinuteFromIsoTime('2025-12-17T18:00:00')).toBe(0)
      expect(getMinuteFromIsoTime('2025-12-17T18:59:00')).toBe(59)
    })

    it('returns null for invalid input', () => {
      expect(getMinuteFromIsoTime(null)).toBeNull()
      expect(getMinuteFromIsoTime('')).toBeNull()
      expect(getMinuteFromIsoTime('invalid')).toBeNull()
    })

    describe('ISO format handling', () => {
      it('handles ISO format with milliseconds', () => {
        expect(getMinuteFromIsoTime('2025-12-17T18:30:00.123')).toBe(30)
      })

      it('handles various time formats', () => {
        expect(getMinuteFromIsoTime('2025-12-17T14:45:00')).toBe(45)
        expect(getMinuteFromIsoTime('2025-12-17T08:05:00')).toBe(5)
      })
    })
  })

  describe('formatHourLabel', () => {
    it('formats hour to HH:00 string', () => {
      expect(formatHourLabel(0)).toBe('0:00')
      expect(formatHourLabel(9)).toBe('9:00')
      expect(formatHourLabel(18)).toBe('18:00')
      expect(formatHourLabel(23)).toBe('23:00')
    })

    it('returns empty string for invalid input', () => {
      expect(formatHourLabel(-1)).toBe('')
      expect(formatHourLabel(24)).toBe('')
      expect(formatHourLabel(null)).toBe('')
      expect(formatHourLabel('18')).toBe('')
    })
  })

  describe('formatTimeShort', () => {
    it('formats local time ISO string to HH:MM', () => {
      expect(formatTimeShort('2025-12-17T18:30:00')).toBe('18:30')
      expect(formatTimeShort('2025-12-17T09:05:00')).toBe('9:05')
      expect(formatTimeShort('2025-12-17T00:00:00')).toBe('0:00')
    })

    it('returns empty string for invalid input', () => {
      expect(formatTimeShort(null)).toBe('')
      expect(formatTimeShort('')).toBe('')
      expect(formatTimeShort('invalid')).toBe('')
    })

    describe('format handling', () => {
      it('handles ISO format with milliseconds', () => {
        expect(formatTimeShort('2025-12-17T18:30:00.123')).toBe('18:30')
      })
    })
  })

  describe('groupExecutionsByHour', () => {
    // Use local time strings (no Z suffix) for predictable behavior
    const mockExecutions = [
      { pattern_id: 'p1', pattern_name: 'Test 1', start_time: '2025-12-17T18:00:00' },
      { pattern_id: 'p2', pattern_name: 'Test 2', start_time: '2025-12-17T18:15:00' },
      { pattern_id: 'p3', pattern_name: 'Test 3', start_time: '2025-12-17T19:00:00' },
      { pattern_id: 'p4', pattern_name: 'Test 4', start_time: '2025-12-18T18:00:00' }, // Different date
    ]

    it('groups executions by hour', () => {
      const grouped = groupExecutionsByHour(mockExecutions, '2025-12-17')
      expect(grouped[18]).toHaveLength(2)
      expect(grouped[19]).toHaveLength(1)
      expect(grouped[20]).toBeUndefined()
    })

    it('filters by date when provided', () => {
      const grouped = groupExecutionsByHour(mockExecutions, '2025-12-17')
      // Should not include the execution from 2025-12-18
      expect(grouped[18]).toHaveLength(2)
    })

    it('includes all dates when date is not provided', () => {
      const grouped = groupExecutionsByHour(mockExecutions, null)
      expect(grouped[18]).toHaveLength(3) // 2 from 12-17 + 1 from 12-18
    })

    it('returns empty object for invalid input', () => {
      expect(groupExecutionsByHour(null, '2025-12-17')).toEqual({})
      expect(groupExecutionsByHour([], '2025-12-17')).toEqual({})
      expect(groupExecutionsByHour('invalid', '2025-12-17')).toEqual({})
    })

    it('skips executions without start_time', () => {
      const executions = [
        { pattern_id: 'p1', pattern_name: 'Test 1' }, // No start_time
        { pattern_id: 'p2', pattern_name: 'Test 2', start_time: '2025-12-17T18:00:00' },
      ]
      const grouped = groupExecutionsByHour(executions, '2025-12-17')
      expect(grouped[18]).toHaveLength(1)
    })
  })

  describe('getConflictForHour', () => {
    // Use local time strings for predictable behavior
    const mockConflicts = [
      {
        id: 'c1',
        severity: 'error',
        start_time: '2025-12-17T19:00:00',
        message: 'Camera busy',
      },
      {
        id: 'c2',
        severity: 'warning',
        start_time: '2025-12-17T21:00:00',
        message: 'Unexpected GPIO state',
      },
      {
        id: 'c3',
        severity: 'warning',
        start_time: '2025-12-17T19:00:00',
        message: 'Another warning',
      },
    ]

    it('finds conflict for matching hour', () => {
      const conflict = getConflictForHour(mockConflicts, 19, '2025-12-17')
      expect(conflict).not.toBeNull()
      expect(conflict.id).toBe('c1') // Error is more severe
    })

    it('returns most severe conflict when multiple exist', () => {
      const conflict = getConflictForHour(mockConflicts, 19, '2025-12-17')
      expect(conflict.severity).toBe('error')
    })

    it('returns null when no conflict for hour', () => {
      const conflict = getConflictForHour(mockConflicts, 18, '2025-12-17')
      expect(conflict).toBeNull()
    })

    it('filters by date', () => {
      const conflict = getConflictForHour(mockConflicts, 19, '2025-12-18')
      expect(conflict).toBeNull()
    })

    it('returns null for invalid input', () => {
      expect(getConflictForHour(null, 19, '2025-12-17')).toBeNull()
      expect(getConflictForHour([], 19, '2025-12-17')).toBeNull()
      expect(getConflictForHour(mockConflicts, -1, '2025-12-17')).toBeNull()
      expect(getConflictForHour(mockConflicts, 25, '2025-12-17')).toBeNull()
    })
  })

  describe('getActionTypeDisplay', () => {
    it('returns camera colors for camera type', () => {
      const display = getActionTypeDisplay('camera', 'takephoto')
      expect(display.bg).toBe('bg-blue-500/20')
      expect(display.text).toBe('text-blue-400')
    })

    it('returns gpio colors for gpio type', () => {
      const display = getActionTypeDisplay('gpio', 'attract_on')
      expect(display.bg).toBe('bg-orange-500/20')
      expect(display.text).toBe('text-orange-400')
    })

    it('returns hdr colors for HDR action names', () => {
      const display1 = getActionTypeDisplay('camera', 'HDR Bracket')
      const display2 = getActionTypeDisplay('camera', 'hdr_capture')
      expect(display1.bg).toBe('bg-purple-500/20')
      expect(display2.bg).toBe('bg-purple-500/20')
    })

    it('returns default colors for unknown types', () => {
      const display = getActionTypeDisplay('unknown', 'test')
      expect(display.bg).toBe('bg-blue-500/20')
    })

    it('returns gps_sync colors', () => {
      const display = getActionTypeDisplay('gps_sync', 'sync')
      expect(display.bg).toBe('bg-green-500/20')
    })

    it('returns service colors', () => {
      const display = getActionTypeDisplay('service', 'restart')
      expect(display.bg).toBe('bg-gray-500/20')
    })
  })

  describe('countConflictsBySeverity', () => {
    it('counts conflicts correctly', () => {
      const conflicts = [
        { severity: 'error' },
        { severity: 'error' },
        { severity: 'warning' },
      ]
      const result = countConflictsBySeverity(conflicts)
      expect(result.total).toBe(3)
      expect(result.errors).toBe(2)
      expect(result.warnings).toBe(1)
    })

    it('returns zeros for empty array', () => {
      const result = countConflictsBySeverity([])
      expect(result.total).toBe(0)
      expect(result.errors).toBe(0)
      expect(result.warnings).toBe(0)
    })

    it('returns zeros for invalid input', () => {
      const result = countConflictsBySeverity(null)
      expect(result.total).toBe(0)
    })
  })

  describe('getConflictForExecution', () => {
    const execution = {
      pattern_id: 'routine-1',
      start_time: '2025-12-17T19:00:00',
    }

    const conflicts = [
      {
        id: 'c1',
        event1_id: 'routine-1',
        event2_id: 'routine-2',
        severity: 'error',
        start_time: '2025-12-17T19:00:00',
      },
    ]

    it('finds conflict by pattern_id match', () => {
      const conflict = getConflictForExecution(execution, conflicts)
      expect(conflict).not.toBeNull()
      expect(conflict.id).toBe('c1')
    })

    it('finds conflict by time match', () => {
      const exec = { pattern_id: 'other', start_time: '2025-12-17T19:00:00' }
      const conflict = getConflictForExecution(exec, conflicts)
      expect(conflict).not.toBeNull()
    })

    it('returns null when no match', () => {
      const exec = { pattern_id: 'other', start_time: '2025-12-17T20:00:00' }
      const conflict = getConflictForExecution(exec, conflicts)
      expect(conflict).toBeNull()
    })

    it('returns null for invalid input', () => {
      expect(getConflictForExecution(null, conflicts)).toBeNull()
      expect(getConflictForExecution(execution, null)).toBeNull()
    })
  })

  describe('getExecutionKey', () => {
    it('generates unique key from pattern_id, time, and id', () => {
      const execution = {
        id: 'exec-123',
        pattern_id: 'routine-1',
        start_time: '2025-12-17T18:30:00',
      }
      expect(getExecutionKey(execution)).toBe(
        'routine-1-2025-12-17T18:30:00-exec-123'
      )
    })

    it('uses index as fallback when id is missing', () => {
      const execution = {
        pattern_id: 'routine-1',
        start_time: '2025-12-17T18:30:00',
      }
      expect(getExecutionKey(execution, 5)).toBe(
        'routine-1-2025-12-17T18:30:00-5'
      )
    })

    it('uses 0 as default index', () => {
      const execution = {
        pattern_id: 'routine-1',
        start_time: '2025-12-17T18:30:00',
      }
      expect(getExecutionKey(execution)).toBe(
        'routine-1-2025-12-17T18:30:00-0'
      )
    })

    it('handles missing fields', () => {
      expect(getExecutionKey({})).toBe('unknown--0')
    })

    it('prevents key collision for same pattern_id and time', () => {
      const exec1 = { pattern_id: 'r1', start_time: '2025-12-17T18:00:00' }
      const exec2 = { pattern_id: 'r1', start_time: '2025-12-17T18:00:00' }
      expect(getExecutionKey(exec1, 0)).not.toBe(getExecutionKey(exec2, 1))
    })
  })

  describe('getExecutionTestId', () => {
    it('generates data-testid format with local time', () => {
      const execution = {
        pattern_id: 'routine-1',
        start_time: '2025-12-17T18:30:00',
      }
      expect(getExecutionTestId(execution)).toBe('execution-routine-1-1830')
    })

    it('handles missing fields', () => {
      expect(getExecutionTestId({})).toBe('execution-unknown-')
    })
  })
})
