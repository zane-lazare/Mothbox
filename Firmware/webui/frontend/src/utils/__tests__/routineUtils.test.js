import { describe, it, expect } from 'vitest'
import {
  getTriggerLabel,
  getActionColor,
  getPrimaryActionColor,
  summarizeActions,
  describeTrigger,
  generateRoutineName,
  TRIGGER_LABELS,
  ACTION_COLORS,
} from '../routineUtils'

describe('routineUtils', () => {
  describe('getTriggerLabel', () => {
    it('returns correct label for each trigger type', () => {
      expect(getTriggerLabel({ trigger_type: 'interval' })).toBe('Interval')
      expect(getTriggerLabel({ trigger_type: 'solar' })).toBe('Solar')
      expect(getTriggerLabel({ trigger_type: 'fixed_time' })).toBe('Fixed')
      expect(getTriggerLabel({ trigger_type: 'moon_phase' })).toBe('Moon')
      expect(getTriggerLabel({ trigger_type: 'recurring_days' })).toBe('Days')
      expect(getTriggerLabel({ trigger_type: 'cron' })).toBe('Cron')
    })

    it('returns empty string for null/undefined trigger', () => {
      expect(getTriggerLabel(null)).toBe('')
      expect(getTriggerLabel(undefined)).toBe('')
      expect(getTriggerLabel({})).toBe('')
    })

    it('returns trigger_type for unknown types', () => {
      expect(getTriggerLabel({ trigger_type: 'custom' })).toBe('custom')
    })
  })

  describe('getActionColor', () => {
    it('returns orange for gpio actions', () => {
      expect(getActionColor({ action_type: 'gpio' })).toBe('bg-orange-400')
    })

    it('returns blue for camera actions', () => {
      expect(getActionColor({ action_type: 'camera' })).toBe('bg-blue-400')
    })

    it('returns purple for HDR camera actions', () => {
      expect(getActionColor({ action_type: 'camera', action_name: 'HDR Bracket' })).toBe(
        'bg-purple-400'
      )
      expect(getActionColor({ action_type: 'camera', action_name: 'hdr_capture' })).toBe(
        'bg-purple-400'
      )
    })

    it('returns green for gps_sync actions', () => {
      expect(getActionColor({ action_type: 'gps_sync' })).toBe('bg-green-400')
    })

    it('returns gray for service and unknown actions', () => {
      expect(getActionColor({ action_type: 'service' })).toBe('bg-gray-400')
      expect(getActionColor({ action_type: 'unknown' })).toBe('bg-gray-400')
      expect(getActionColor(null)).toBe('bg-gray-400')
      expect(getActionColor({})).toBe('bg-gray-400')
    })
  })

  describe('getPrimaryActionColor', () => {
    it('returns color of first action', () => {
      expect(
        getPrimaryActionColor([
          { action_type: 'gpio' },
          { action_type: 'camera' },
        ])
      ).toBe('bg-orange-400')
    })

    it('returns gray for empty or null actions', () => {
      expect(getPrimaryActionColor([])).toBe('bg-gray-400')
      expect(getPrimaryActionColor(null)).toBe('bg-gray-400')
      expect(getPrimaryActionColor(undefined)).toBe('bg-gray-400')
    })
  })

  describe('summarizeActions', () => {
    it('returns readable name for GPIO actions', () => {
      expect(summarizeActions([{ action_name: 'attract_on' }])).toBe('Attract On')
      expect(summarizeActions([{ action_name: 'attract_off' }])).toBe('Attract Off')
      expect(summarizeActions([{ action_name: 'flash_on' }])).toBe('Flash On')
      expect(summarizeActions([{ action_name: 'flash_off' }])).toBe('Flash Off')
    })

    it('returns readable name for camera actions', () => {
      expect(summarizeActions([{ action_name: 'takephoto' }])).toBe('Take Photo')
      expect(summarizeActions([{ action_name: 'take_photo' }])).toBe('Take Photo')
    })

    it('capitalizes unknown action names', () => {
      expect(summarizeActions([{ action_name: 'custom_action' }])).toBe('Custom_action')
    })

    it('returns empty string for empty/null actions', () => {
      expect(summarizeActions([])).toBe('')
      expect(summarizeActions(null)).toBe('')
      expect(summarizeActions(undefined)).toBe('')
    })

    it('uses name field as fallback', () => {
      expect(summarizeActions([{ name: 'My Action' }])).toBe('My Action')
    })
  })

  describe('describeTrigger', () => {
    it('describes interval triggers', () => {
      expect(describeTrigger({ trigger_type: 'interval', interval_minutes: 15 })).toBe(
        'every 15 min'
      )
      expect(describeTrigger({ trigger_type: 'interval', interval_minutes: 30 })).toBe(
        'every 30 min'
      )
    })

    it('describes solar triggers', () => {
      expect(describeTrigger({ trigger_type: 'solar', solar_event: 'dusk' })).toBe('at Dusk')
      expect(describeTrigger({ trigger_type: 'solar', solar_event: 'dawn' })).toBe('at Dawn')
      expect(describeTrigger({ trigger_type: 'solar', solar_event: 'sunrise' })).toBe('at Sunrise')
      expect(describeTrigger({ trigger_type: 'solar', solar_event: 'sunset' })).toBe('at Sunset')
    })

    it('includes offset for solar triggers', () => {
      expect(
        describeTrigger({ trigger_type: 'solar', solar_event: 'dusk', offset_minutes: 30 })
      ).toBe('at Dusk +30min')
      expect(
        describeTrigger({ trigger_type: 'solar', solar_event: 'dawn', offset_minutes: -15 })
      ).toBe('at Dawn -15min')
    })

    it('describes fixed_time triggers', () => {
      expect(describeTrigger({ trigger_type: 'fixed_time', time_of_day: '18:00' })).toBe('at 18:00')
      expect(describeTrigger({ trigger_type: 'fixed_time', times: ['09:00'] })).toBe('at 09:00')
    })

    it('handles fixed_time with object format', () => {
      expect(
        describeTrigger({ trigger_type: 'fixed_time', times: [{ value: '14:30' }] })
      ).toBe('at 14:30')
    })

    it('describes moon_phase triggers', () => {
      expect(describeTrigger({ trigger_type: 'moon_phase', moon_phase: 'full' })).toBe(
        'on full moon'
      )
      expect(describeTrigger({ trigger_type: 'moon_phase', moon_phase: 'new' })).toBe('on new moon')
    })

    it('describes recurring_days triggers', () => {
      expect(
        describeTrigger({ trigger_type: 'recurring_days', days_interval: 3, time: '20:00' })
      ).toBe('every 3 days at 20:00')
    })

    it('describes cron triggers', () => {
      expect(describeTrigger({ trigger_type: 'cron', cron_expression: '0 * * * *' })).toBe(
        'on schedule'
      )
    })

    it('returns empty string for null/undefined', () => {
      expect(describeTrigger(null)).toBe('')
      expect(describeTrigger(undefined)).toBe('')
      expect(describeTrigger({})).toBe('')
    })
  })

  describe('generateRoutineName', () => {
    it('returns explicit name if provided', () => {
      expect(
        generateRoutineName({
          name: 'My Custom Routine',
          actions: [{ action_name: 'attract_on' }],
          trigger: { trigger_type: 'solar', solar_event: 'dusk' },
        })
      ).toBe('My Custom Routine')
    })

    it('ignores auto-generated placeholder names', () => {
      expect(
        generateRoutineName({
          name: 'Routine 1',
          actions: [{ action_name: 'attract_on' }],
          trigger: { trigger_type: 'solar', solar_event: 'dusk' },
        })
      ).toBe('Attract On at Dusk')
    })

    it('generates name from actions and trigger', () => {
      expect(
        generateRoutineName({
          actions: [{ action_name: 'attract_on' }],
          trigger: { trigger_type: 'solar', solar_event: 'dusk' },
        })
      ).toBe('Attract On at Dusk')

      expect(
        generateRoutineName({
          actions: [{ action_name: 'takephoto' }],
          trigger: { trigger_type: 'interval', interval_minutes: 15 },
        })
      ).toBe('Take Photo every 15 min')

      expect(
        generateRoutineName({
          actions: [{ action_name: 'attract_off' }],
          trigger: { trigger_type: 'solar', solar_event: 'dawn' },
        })
      ).toBe('Attract Off at Dawn')
    })

    it('returns action summary only if no trigger', () => {
      expect(
        generateRoutineName({
          actions: [{ action_name: 'flash_on' }],
        })
      ).toBe('Flash On')
    })

    it('returns trigger description with Run prefix if no actions', () => {
      expect(
        generateRoutineName({
          trigger: { trigger_type: 'interval', interval_minutes: 10 },
          actions: [],
        })
      ).toBe('Run every 10 min')
    })

    it('returns "New Routine" for empty routine', () => {
      expect(generateRoutineName({})).toBe('New Routine')
      expect(generateRoutineName({ actions: [], trigger: {} })).toBe('New Routine')
    })
  })

  describe('constants', () => {
    it('exports TRIGGER_LABELS', () => {
      expect(TRIGGER_LABELS).toHaveProperty('interval')
      expect(TRIGGER_LABELS).toHaveProperty('solar')
      expect(TRIGGER_LABELS).toHaveProperty('fixed_time')
      expect(TRIGGER_LABELS).toHaveProperty('moon_phase')
      expect(TRIGGER_LABELS).toHaveProperty('recurring_days')
      expect(TRIGGER_LABELS).toHaveProperty('cron')
    })

    it('exports ACTION_COLORS', () => {
      expect(ACTION_COLORS).toHaveProperty('gpio')
      expect(ACTION_COLORS).toHaveProperty('camera')
      expect(ACTION_COLORS).toHaveProperty('hdr')
      expect(ACTION_COLORS).toHaveProperty('gps_sync')
      expect(ACTION_COLORS).toHaveProperty('service')
    })
  })
})
