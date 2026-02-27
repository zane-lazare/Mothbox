import { useEffect, useMemo, useRef } from 'react'
import { useForm, Controller, useWatch } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import type { Resolver } from 'react-hook-form'
import {
  solarTriggerSchema,
  type SolarTriggerFormData,
} from '../../../schemas/scheduler/solar'
import { SOLAR_EVENTS, SCHEDULE_LIMITS, DAYS_OF_WEEK } from './constants'
import DaysOfWeekSelector from './DaysOfWeekSelector'

// ── Types ──────────────────────────────────────────────────────────────

export interface SolarTriggerValue {
  solar_event: string
  offset_minutes: number
  days_of_week: number[] | null
}

interface SolarTriggerFormProps {
  value?: SolarTriggerValue
  onChange: (value: SolarTriggerValue) => void
  disabled?: boolean
  errors?: Record<string, string>
}

// ── Constants ──────────────────────────────────────────────────────────

const DEFAULT_VALUE: SolarTriggerValue = {
  solar_event: 'sunset',
  offset_minutes: 0,
  days_of_week: null,
}

const OFFSET_PRESETS = [
  { label: '-1h', value: -60 },
  { label: '-30m', value: -30 },
  { label: 'No offset', value: 0 },
  { label: '+30m', value: 30 },
  { label: '+1h', value: 60 },
] as const

// ── Formatting helpers (pure functions, no React state) ────────────────

function formatOffset(minutes: number): string {
  if (minutes === 0) return ''

  const absMinutes = Math.abs(minutes)

  if (absMinutes < 60) {
    return `${absMinutes} minute${absMinutes !== 1 ? 's' : ''}`
  } else if (absMinutes % 60 === 0) {
    const hours = absMinutes / 60
    return `${hours} hour${hours !== 1 ? 's' : ''}`
  }
  const hours = Math.floor(absMinutes / 60)
  const mins = absMinutes % 60
  return `${hours}h ${mins}m`
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
// TODO(#447): remove cast when resolvers#800 is fixed
// Upstream: https://github.com/react-hook-form/resolvers/issues/800
const resolver = zodResolver(
  solarTriggerSchema as unknown as Parameters<typeof zodResolver>[0],
) as unknown as Resolver<SolarTriggerFormData>

export default function SolarTriggerForm({
  value = DEFAULT_VALUE,
  onChange,
  disabled = false,
  errors: parentErrors = {},
}: SolarTriggerFormProps) {
  // Stable callback ref — prevents useWatch effect from re-running when
  // parent passes an inline arrow function as onChange.
  const onChangeRef = useRef(onChange)
  onChangeRef.current = onChange

  // Stable ref for the full value prop — lets the propagation effect read
  // current days_of_week without adding `value` to its deps.
  const valueRef = useRef(value)
  valueRef.current = value

  // Initialized to current prop so prop-sync skips the first render
  // (no external change to detect yet).
  const lastPropagatedRef = useRef({
    solar_event: value.solar_event,
    offset_minutes: value.offset_minutes,
  })

  const {
    control,
    reset,
    formState: { errors },
  } = useForm<SolarTriggerFormData>({
    resolver,
    defaultValues: {
      solar_event: value.solar_event as SolarTriggerFormData['solar_event'],
      offset_minutes: value.offset_minutes,
    },
    mode: 'onChange',
  })

  // Prop sync: reset form when solar_event or offset_minutes changes externally
  // (e.g., preset button click, parent state change)
  useEffect(() => {
    const lastProp = lastPropagatedRef.current
    if (
      value.solar_event !== lastProp.solar_event ||
      value.offset_minutes !== lastProp.offset_minutes
    ) {
      lastPropagatedRef.current = {
        solar_event: value.solar_event,
        offset_minutes: value.offset_minutes,
      }
      reset({
        solar_event: value.solar_event as SolarTriggerFormData['solar_event'],
        offset_minutes: value.offset_minutes,
      })
    }
  }, [value.solar_event, value.offset_minutes, reset])

  // Propagate validated form changes → parent
  const watchedSolarEvent = useWatch({ control, name: 'solar_event' })
  const watchedOffset = useWatch({ control, name: 'offset_minutes' })
  useEffect(() => {
    if (watchedSolarEvent === undefined || watchedOffset === undefined) return
    // Skip if values match props (avoids cycle from prop sync)
    const current = valueRef.current
    if (
      watchedSolarEvent === current.solar_event &&
      watchedOffset === current.offset_minutes
    ) return
    // Only propagate valid values
    const result = solarTriggerSchema.safeParse({
      solar_event: watchedSolarEvent,
      offset_minutes: watchedOffset,
    })
    if (!result.success) return
    lastPropagatedRef.current = {
      solar_event: watchedSolarEvent,
      offset_minutes: watchedOffset,
    }
    onChangeRef.current({
      ...valueRef.current,
      solar_event: watchedSolarEvent,
      offset_minutes: watchedOffset,
    })
  }, [watchedSolarEvent, watchedOffset])

  // Preset buttons bypass the form — call onChange directly
  const handlePresetClick = (presetValue: number) => {
    onChangeRef.current({ ...valueRef.current, offset_minutes: presetValue })
  }

  const handleDaysChange = (newDays: number[] | null) => {
    onChangeRef.current({ ...valueRef.current, days_of_week: newDays })
  }

  const previewText = useMemo(() => {
    const event = SOLAR_EVENTS.find((e) => e.value === value.solar_event)
    const eventLabel = event ? event.label.toLowerCase() : value.solar_event
    const offsetText = formatOffset(value.offset_minutes)
    const daysText = formatDays(value.days_of_week)

    let preview: string
    if (value.offset_minutes === 0) {
      preview = `At ${eventLabel}`
    } else if (value.offset_minutes > 0) {
      preview = `${offsetText} after ${eventLabel}`
    } else {
      preview = `${offsetText} before ${eventLabel}`
    }

    if (daysText) {
      preview += ` on ${daysText}`
    }

    return preview
  }, [value.solar_event, value.offset_minutes, value.days_of_week])

  return (
    <div className="space-y-6">
      {/* Header */}
      <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
        Solar Event Configuration
      </h3>

      {/* Solar Event Selection */}
      <div>
        <label
          htmlFor="solar_event"
          className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2"
        >
          Solar Event:
        </label>
        <Controller
          name="solar_event"
          control={control}
          render={({ field }) => (
            <select
              id="solar_event"
              value={field.value}
              onChange={(e) => field.onChange(e.target.value)}
              onBlur={field.onBlur}
              ref={field.ref}
              disabled={disabled}
              className="w-full rounded-md border border-gray-300 dark:border-gray-600
                       bg-white dark:bg-gray-800 px-3 py-2 text-gray-900 dark:text-white
                       focus:ring-2 focus:ring-blue-500 focus:border-transparent
                       disabled:opacity-50 disabled:cursor-not-allowed"
              aria-label="Solar event"
              aria-invalid={!!(errors.solar_event || parentErrors.solar_event)}
              aria-describedby={
                (errors.solar_event || parentErrors.solar_event)
                  ? 'solar_event-error'
                  : undefined
              }
            >
              {SOLAR_EVENTS.map((event) => (
                <option key={event.value} value={event.value}>
                  {event.label}
                </option>
              ))}
            </select>
          )}
        />
        {(errors.solar_event?.message || parentErrors.solar_event) && (
          <p
            id="solar_event-error"
            role="alert"
            className="mt-1 text-sm text-red-600 dark:text-red-400"
          >
            {errors.solar_event?.message || parentErrors.solar_event}
          </p>
        )}
        {/* Event Description */}
        <p className="mt-2 text-sm text-gray-500 dark:text-gray-300">
          {SOLAR_EVENTS.find((e) => e.value === value.solar_event)?.description ?? ''}
        </p>
      </div>

      {/* Offset Input */}
      <div>
        <label
          htmlFor="offset_minutes"
          className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2"
        >
          Offset (minutes):
        </label>
        <div className="flex items-center gap-2">
          <Controller
            name="offset_minutes"
            control={control}
            render={({ field }) => (
              <input
                id="offset_minutes"
                type="number"
                min={-SCHEDULE_LIMITS.MAX_OFFSET_MINUTES}
                max={SCHEDULE_LIMITS.MAX_OFFSET_MINUTES}
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
                aria-label="Offset in minutes"
                aria-invalid={!!(errors.offset_minutes || parentErrors.offset_minutes)}
                aria-describedby={
                  (errors.offset_minutes || parentErrors.offset_minutes)
                    ? 'offset_minutes-error'
                    : undefined
                }
              />
            )}
          />
          <span className="text-sm text-gray-700 dark:text-gray-300">minutes</span>
        </div>
        {(errors.offset_minutes?.message ||
          parentErrors.offset_minutes) && (
          <p
            id="offset_minutes-error"
            role="alert"
            className="mt-1 text-sm text-red-600 dark:text-red-400"
          >
            {errors.offset_minutes?.message || parentErrors.offset_minutes}
          </p>
        )}
      </div>

      {/* Quick Offset Presets */}
      <div>
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
          Quick presets:
        </label>
        <div className="flex flex-wrap gap-2">
          {OFFSET_PRESETS.map((preset) => (
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
                  value.offset_minutes === preset.value
                    ? 'bg-blue-500 text-white hover:bg-blue-600 dark:bg-blue-600 dark:hover:bg-blue-700'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200 dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600'
                }
                ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
              `}
              aria-label={`Set offset to ${preset.value > 0 ? '+' : ''}${preset.value} minutes`}
            >
              {preset.label}
            </button>
          ))}
        </div>
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
