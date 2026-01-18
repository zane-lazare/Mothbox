/**
 * Tests for cycle-based grouping utilities.
 * Written BEFORE implementation (TDD).
 */

import { describe, it, expect } from 'vitest'
import {
  getCycleDay,
  getFirstCycleStart,
  groupExecutionsByCycleDay,
} from '../cycleGroupingUtils'

describe('cycleGroupingUtils', () => {
  // ============================================================
  // getFirstCycleStart
  // ============================================================
  describe('getFirstCycleStart', () => {
    it('returns same day when reference is after start hour', () => {
      // Reference: Jan 15, 10:00 AM, startHour: 8
      const reference = new Date(2026, 0, 15, 10, 0, 0)
      const result = getFirstCycleStart(reference, 8)

      expect(result.getFullYear()).toBe(2026)
      expect(result.getMonth()).toBe(0)
      expect(result.getDate()).toBe(15)
      expect(result.getHours()).toBe(8)
      expect(result.getMinutes()).toBe(0)
    })

    it('returns previous day when reference is before start hour', () => {
      // Reference: Jan 15, 3:00 AM, startHour: 21 (overnight schedule)
      const reference = new Date(2026, 0, 15, 3, 0, 0)
      const result = getFirstCycleStart(reference, 21)

      expect(result.getDate()).toBe(14) // Previous day
      expect(result.getHours()).toBe(21)
    })

    it('handles midnight start hour', () => {
      const reference = new Date(2026, 0, 15, 12, 0, 0)
      const result = getFirstCycleStart(reference, 0)

      expect(result.getDate()).toBe(15)
      expect(result.getHours()).toBe(0)
    })
  })

  // ============================================================
  // getCycleDay
  // ============================================================
  describe('getCycleDay', () => {
    describe('daytime schedule (08:00 start)', () => {
      const startHour = 8
      const firstCycleStart = new Date(2026, 0, 15, 8, 0, 0) // Jan 15, 8 AM

      it('assigns morning execution to day 0', () => {
        const execTime = new Date(2026, 0, 15, 10, 0, 0) // 10 AM same day
        expect(getCycleDay(execTime, firstCycleStart, startHour)).toBe(0)
      })

      it('assigns afternoon execution to day 0', () => {
        const execTime = new Date(2026, 0, 15, 18, 0, 0) // 6 PM same day
        expect(getCycleDay(execTime, firstCycleStart, startHour)).toBe(0)
      })

      it('assigns next day morning to day 1', () => {
        const execTime = new Date(2026, 0, 16, 10, 0, 0) // Jan 16, 10 AM
        expect(getCycleDay(execTime, firstCycleStart, startHour)).toBe(1)
      })

      it('assigns day 7 execution correctly', () => {
        const execTime = new Date(2026, 0, 21, 10, 0, 0) // Jan 21, 10 AM
        expect(getCycleDay(execTime, firstCycleStart, startHour)).toBe(6)
      })

      it('returns -1 for execution before first cycle', () => {
        const execTime = new Date(2026, 0, 14, 10, 0, 0) // Day before
        expect(getCycleDay(execTime, firstCycleStart, startHour)).toBe(-1)
      })

      it('returns -1 for execution after day 7', () => {
        const execTime = new Date(2026, 0, 22, 10, 0, 0) // Day 8
        expect(getCycleDay(execTime, firstCycleStart, startHour)).toBe(-1)
      })
    })

    describe('overnight schedule (21:00 start)', () => {
      const startHour = 21
      const firstCycleStart = new Date(2026, 0, 15, 21, 0, 0) // Jan 15, 9 PM

      it('assigns evening execution to day 0', () => {
        const execTime = new Date(2026, 0, 15, 22, 0, 0) // 10 PM same day
        expect(getCycleDay(execTime, firstCycleStart, startHour)).toBe(0)
      })

      it('assigns post-midnight execution to SAME cycle (day 0)', () => {
        // THIS IS THE KEY TEST - post-midnight belongs to previous cycle
        const execTime = new Date(2026, 0, 16, 2, 0, 0) // 2 AM next calendar day
        expect(getCycleDay(execTime, firstCycleStart, startHour)).toBe(0)
      })

      it('assigns next evening to day 1', () => {
        const execTime = new Date(2026, 0, 16, 22, 0, 0) // Jan 16, 10 PM
        expect(getCycleDay(execTime, firstCycleStart, startHour)).toBe(1)
      })

      it('assigns day 7 evening correctly', () => {
        const execTime = new Date(2026, 0, 21, 22, 0, 0) // Jan 21, 10 PM
        expect(getCycleDay(execTime, firstCycleStart, startHour)).toBe(6)
      })

      it('assigns day 7 post-midnight (calendar day 8) to day 6', () => {
        // THIS IS THE BUG WE'RE FIXING - Day 8 morning belongs to Day 7's cycle
        const execTime = new Date(2026, 0, 22, 2, 0, 0) // Jan 22, 2 AM
        expect(getCycleDay(execTime, firstCycleStart, startHour)).toBe(6)
      })

      it('returns -1 for execution after day 7 cycle completes', () => {
        // Jan 22, 10 PM would be day 8 cycle start
        const execTime = new Date(2026, 0, 22, 22, 0, 0)
        expect(getCycleDay(execTime, firstCycleStart, startHour)).toBe(-1)
      })
    })
  })

  // ============================================================
  // groupExecutionsByCycleDay
  // ============================================================
  describe('groupExecutionsByCycleDay', () => {
    it('returns empty object for empty executions', () => {
      const result = groupExecutionsByCycleDay([], { start_hour: 8 }, new Date())
      expect(result).toEqual({})
    })

    it('returns empty object for null executions', () => {
      const result = groupExecutionsByCycleDay(null, { start_hour: 8 }, new Date())
      expect(result).toEqual({})
    })

    it('groups daytime executions by cycle day', () => {
      const reference = new Date(2026, 0, 15, 8, 0, 0)
      const executions = [
        { pattern_id: 'p1', start_time: '2026-01-15T10:00:00' },
        { pattern_id: 'p1', start_time: '2026-01-16T10:00:00' },
        { pattern_id: 'p1', start_time: '2026-01-17T10:00:00' },
      ]

      const result = groupExecutionsByCycleDay(executions, { start_hour: 8 }, reference)

      expect(result['day-0'][10]).toHaveLength(1)
      expect(result['day-1'][10]).toHaveLength(1)
      expect(result['day-2'][10]).toHaveLength(1)
    })

    it('groups overnight post-midnight executions with previous cycle', () => {
      // Overnight schedule: 21:00 start
      const reference = new Date(2026, 0, 15, 21, 0, 0)
      const executions = [
        { pattern_id: 'p1', start_time: '2026-01-15T22:00:00' }, // Day 1 evening
        { pattern_id: 'p1', start_time: '2026-01-16T02:00:00' }, // Day 1 morning (same cycle)
        { pattern_id: 'p1', start_time: '2026-01-16T22:00:00' }, // Day 2 evening
        { pattern_id: 'p1', start_time: '2026-01-17T02:00:00' }, // Day 2 morning (same cycle)
      ]

      const result = groupExecutionsByCycleDay(executions, { start_hour: 21 }, reference)

      // Day 0 should have both 22:00 and 02:00
      expect(result['day-0'][22]).toHaveLength(1)
      expect(result['day-0'][2]).toHaveLength(1)

      // Day 1 should have both 22:00 and 02:00
      expect(result['day-1'][22]).toHaveLength(1)
      expect(result['day-1'][2]).toHaveLength(1)
    })

    it('correctly assigns Day 7 morning for overnight schedules (THE BUG FIX)', () => {
      // This is the specific bug we're fixing:
      // Day 8 calendar morning (00:00-04:00) should appear in Day 7 column
      const reference = new Date(2026, 0, 15, 21, 0, 0)
      const executions = [
        // Day 7 evening (calendar Jan 21)
        { pattern_id: 'p1', start_time: '2026-01-21T22:00:00' },
        // Day 7 morning (calendar Jan 22 - Day 8)
        { pattern_id: 'p1', start_time: '2026-01-22T00:00:00' },
        { pattern_id: 'p1', start_time: '2026-01-22T01:00:00' },
        { pattern_id: 'p1', start_time: '2026-01-22T04:00:00' },
      ]

      const result = groupExecutionsByCycleDay(executions, { start_hour: 21 }, reference)

      // All should be in day-6 (7th day, 0-indexed)
      expect(result['day-6'][22]).toHaveLength(1)
      expect(result['day-6'][0]).toHaveLength(1)
      expect(result['day-6'][1]).toHaveLength(1)
      expect(result['day-6'][4]).toHaveLength(1)
    })

    it('deduplicates executions with same pattern at same time', () => {
      const reference = new Date(2026, 0, 15, 8, 0, 0)
      const executions = [
        { pattern_id: 'p1', start_time: '2026-01-15T10:00:00' },
        { pattern_id: 'p1', start_time: '2026-01-15T10:00:00' }, // Duplicate
        { pattern_id: 'p1', start_time: '2026-01-15T10:00:00' }, // Duplicate
      ]

      const result = groupExecutionsByCycleDay(executions, { start_hour: 8 }, reference)

      expect(result['day-0'][10]).toHaveLength(1) // Only 1, not 3
    })

    it('allows different patterns at same time', () => {
      const reference = new Date(2026, 0, 15, 8, 0, 0)
      const executions = [
        { pattern_id: 'p1', start_time: '2026-01-15T10:00:00' },
        { pattern_id: 'p2', start_time: '2026-01-15T10:00:00' },
      ]

      const result = groupExecutionsByCycleDay(executions, { start_hour: 8 }, reference)

      expect(result['day-0'][10]).toHaveLength(2)
    })

    it('uses start_hour 0 when cycleInfo is null', () => {
      const reference = new Date(2026, 0, 15, 0, 0, 0)
      const executions = [
        { pattern_id: 'p1', start_time: '2026-01-15T10:00:00' },
      ]

      const result = groupExecutionsByCycleDay(executions, null, reference)

      expect(result['day-0'][10]).toHaveLength(1)
    })

    it('skips executions with invalid start_time', () => {
      const reference = new Date(2026, 0, 15, 8, 0, 0)
      const executions = [
        { pattern_id: 'p1', start_time: 'invalid' },
        { pattern_id: 'p1', start_time: null },
        { pattern_id: 'p1' }, // Missing start_time
        { pattern_id: 'p1', start_time: '2026-01-15T10:00:00' }, // Valid
      ]

      const result = groupExecutionsByCycleDay(executions, { start_hour: 8 }, reference)

      expect(result['day-0'][10]).toHaveLength(1)
    })
  })
})
