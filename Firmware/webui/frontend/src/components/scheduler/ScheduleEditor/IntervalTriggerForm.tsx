import { useEffect, useMemo, useRef } from 'react'
import { useForm, Controller, useWatch } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import type { Resolver } from 'react-hook-form'
import {
  intervalTriggerSchema,
  type IntervalTriggerFormData,
} from '../../../schemas/scheduler/interval'
import { SCHEDULE_LIMITS, DAYS_OF_WEEK } from './constants'
import TimeWindowInput from './TimeWindowInput'
import type { TimeWindowValue as TimeWindow } from './TimeWindowInput'
import DaysOfWeekSelector from './DaysOfWeekSelector'

// ── Types ──────────────────────────────────────────────────────────────

export interface IntervalTriggerValue {
  interval_minutes: number
  time_window: TimeWindow
  days_of_week: number[] | null
}

interface IntervalTriggerFormProps {
  value?: IntervalTriggerValue
  onChange: (value: IntervalTriggerValue) => void
  disabled?: boolean
  errors?: Record<string, string | Record<string, string>>
}

// ── Constants ──────────────────────────────────────────────────────────

const DEFAULT_VALUE: IntervalTriggerValue = {
  interval_minutes: 60,
  time_window: {
    start_time: '',
    end_time: '',
    start_offset_minutes: 0,
    end_offset_minutes: 0,
  },
  days_of_week: null,
}

const QUICK_PRESETS = [
  { label: '15 min', value: 15 },
  { label: '30 min', value: 30 },
  { label: '60 min', value: 60 },
  { label: '2 hours', value: 120 },
  { label: '4 hours', value: 240 },
] as const

// ── Formatting helpers (pure functions, no React state) ────────────────

function formatInterval(minutes: number): string {
  if (!minutes) return '—' // defensive: schema enforces min 1, but prop may be 0
  if (minutes < 60) {
    return `Every ${minutes} minute${minutes !== 1 ? 's' : ''}`
  } else if (minutes % 60 === 0) {
    const hours = minutes / 60
    return `Every ${hours} hour${hours !== 1 ? 's' : ''}`
  }
  const hours = Math.floor(minutes / 60)
  const mins = minutes % 60
  return `Every ${hours}h ${mins}m`
}

function formatTimeWindow(
  timeWindow: TimeWindow | undefined,
): string {
  if (!timeWindow || !timeWindow.start_time || !timeWindow.end_time) return ''

  const formatTime = (time: string, offset?: number): string => {
    if (!/^\d{2}:\d{2}$/.test(time)) {
      const formattedEvent = time.replace(/_/g, ' ')
      if (offset) {
        const sign = offset > 0 ? '+' : ''
        return `${formattedEvent}${sign}${offset}`
      }
      return formattedEvent
    }
    return time
  }

  const startText = formatTime(timeWindow.start_time, timeWindow.start_offset_minutes)
  const endText = formatTime(timeWindow.end_time, timeWindow.end_offset_minutes)
  return `from ${startText} to ${endText}`
}

function formatDays(days: number[] | null | undefined): string {
  if (days === null || days === undefined) return ''
  if (!Array.isArray(days) || days.length === 0) return ''
  if (days.length === 7) return ''

  const dayLabels = days
    .slice()
    .sort((a, b) => a - b)
    .map((dayValue) => {
      const day = DAYS_OF_WEEK.find((d) => d.value === dayValue)
      return day ? day.shortLabel : ''
    })
    .filter(Boolean)

  return dayLabels.join(', ')
}

// ── Component ──────────────────────────────────────────────────────────

// Zod 4 + @hookform/resolvers type workaround (@hookform/resolvers@3.x + zod@4.x)
// TODO(#446): remove cast when resolvers#800 is fixed
// Upstream: https://github.com/react-hook-form/resolvers/issues/800
const resolver = zodResolver(
  intervalTriggerSchema as unknown as Parameters<typeof zodResolver>[0],
) as unknown as Resolver<IntervalTriggerFormData>

export default function IntervalTriggerForm({
  value = DEFAULT_VALUE,
  onChange,
  disabled = false,
  errors: parentErrors = {},
}: IntervalTriggerFormProps) {
  // Stable callback ref — prevents useWatch effect from re-running when
  // parent passes an inline arrow function as onChange.
  const onChangeRef = useRef(onChange)
  onChangeRef.current = onChange

  // Stable ref for the full value prop — lets the propagation effect read
  // current time_window/days_of_week without adding `value` to its deps.
  const valueRef = useRef(value)
  valueRef.current = value

  // Initialized to current prop so prop-sync skips the first render
  // (no external change to detect yet).
  const lastPropagatedRef = useRef(value.interval_minutes)

  const {
    control,
    reset,
    formState: { errors },
  } = useForm<IntervalTriggerFormData>({
    resolver,
    defaultValues: { interval_minutes: value.interval_minutes },
    mode: 'onChange',
  })

  // Prop sync: reset form when interval_minutes changes externally
  // (e.g., preset button click, parent state change)
  useEffect(() => {
    if (value.interval_minutes !== lastPropagatedRef.current) {
      lastPropagatedRef.current = value.interval_minutes
      reset({ interval_minutes: value.interval_minutes })
    }
  }, [value.interval_minutes, reset])

  // Propagate validated form changes → parent
  const intervalMinutes = useWatch({ control, name: 'interval_minutes' })
  useEffect(() => {
    if (intervalMinutes === undefined) return
    // Skip if value matches props (avoids cycle from prop sync)
    if (intervalMinutes === valueRef.current.interval_minutes) return
    // Only propagate valid values
    const result = intervalTriggerSchema.safeParse({ interval_minutes: intervalMinutes })
    if (!result.success) return
    lastPropagatedRef.current = intervalMinutes
    onChangeRef.current({ ...valueRef.current, interval_minutes: intervalMinutes })
  }, [intervalMinutes])

  // Preset buttons bypass the form — call onChange directly
  const handlePresetClick = (presetValue: number) => {
    onChangeRef.current({ ...valueRef.current, interval_minutes: presetValue })
  }

  const handleTimeWindowChange = (newTimeWindow: TimeWindow) => {
    onChangeRef.current({ ...valueRef.current, time_window: newTimeWindow })
  }

  const handleDaysChange = (newDays: number[] | null) => {
    onChangeRef.current({ ...valueRef.current, days_of_week: newDays })
  }

  const previewText = useMemo(() => {
    const intervalText = formatInterval(value.interval_minutes)
    const windowText = formatTimeWindow(value.time_window)
    const daysText = formatDays(value.days_of_week)

    let preview = intervalText
    if (windowText) preview += ` ${windowText}`
    if (daysText) preview += ` on ${daysText}`
    return preview
  }, [value.interval_minutes, value.time_window, value.days_of_week])

  return (
    <div className="space-y-6">
      {/* Header */}
      <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
        Interval Configuration
      </h3>

      {/* Interval Input */}
      <div>
        <label
          htmlFor="interval_minutes"
          className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2"
        >
          Repeat every:
        </label>
        <div className="flex items-center gap-2">
          <Controller
            name="interval_minutes"
            control={control}
            render={({ field }) => (
              <input
                id="interval_minutes"
                type="number"
                min={SCHEDULE_LIMITS.MIN_INTERVAL_MINUTES}
                max={SCHEDULE_LIMITS.MAX_INTERVAL_MINUTES}
                step={1}
                value={Number.isNaN(field.value) ? '' : field.value}
                onChange={(e) => {
                  const raw = e.target.value
                  field.onChange(raw === '' ? NaN : Number(raw))
                }}
                onBlur={field.onBlur}
                ref={field.ref}
                disabled={disabled}
                className="w-32 rounded-md border border-gray-300 dark:border-gray-600
                         bg-white dark:bg-gray-800 px-3 py-2 text-gray-900 dark:text-white
                         focus:ring-2 focus:ring-blue-500 focus:border-transparent
                         disabled:opacity-50 disabled:cursor-not-allowed"
                aria-label="Interval in minutes"
                aria-invalid={!!errors.interval_minutes}
                aria-describedby={
                  errors.interval_minutes ? 'interval_minutes-error' : undefined
                }
              />
            )}
          />
          <span className="text-sm text-gray-700 dark:text-gray-300">minutes</span>
        </div>
        {(errors.interval_minutes?.message ||
          (parentErrors.interval_minutes &&
            typeof parentErrors.interval_minutes === 'string')) && (
          <p
            id="interval_minutes-error"
            role="alert"
            className="mt-1 text-sm text-red-600 dark:text-red-400"
          >
            {errors.interval_minutes?.message ||
              (parentErrors.interval_minutes as string)}
          </p>
        )}
      </div>

      {/* Quick Presets */}
      <div>
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
          Quick presets:
        </label>
        <div className="flex flex-wrap gap-2">
          {QUICK_PRESETS.map((preset) => (
            <button
              key={preset.value}
              type="button"
              onClick={() => handlePresetClick(preset.value)}
              disabled={disabled}
              className={`
                px-4 py-2 rounded-md text-sm font-medium
                transition-colors duration-150
                focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2
                dark:focus:ring-offset-gray-800
                ${
                  value.interval_minutes === preset.value
                    ? 'bg-blue-500 text-white hover:bg-blue-600 dark:bg-blue-600 dark:hover:bg-blue-700'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200 dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600'
                }
                ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
              `}
              aria-label={`Set interval to ${preset.label}`}
            >
              {preset.label}
            </button>
          ))}
        </div>
      </div>

      {/* Time Window */}
      <div>
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">
          Time Window:
        </label>
        <TimeWindowInput
          value={value.time_window}
          onChange={handleTimeWindowChange}
          disabled={disabled}
          showSolarEvents={true}
          errors={(parentErrors.time_window as Record<string, string>) || {}}
        />
      </div>

      {/* Days of Week */}
      <DaysOfWeekSelector
        value={value.days_of_week}
        onChange={handleDaysChange}
        disabled={disabled}
      />

      {/* Preview */}
      <div className="pt-4 border-t border-gray-200 dark:border-gray-700">
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
          Preview:
        </label>
        <p className="text-sm text-gray-600 dark:text-gray-300 italic bg-gray-50 dark:bg-gray-800 p-3 rounded-md">
          {previewText}
        </p>
      </div>
    </div>
  )
}
