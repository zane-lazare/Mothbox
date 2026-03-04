import { useCallback, useEffect, useMemo, useRef } from 'react'
import { useForm, Controller, useWatch } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import type { Resolver } from 'react-hook-form'
import {
  fixedTimeTriggerSchema,
  type FixedTimeTriggerFormData,
} from '../../../schemas/scheduler/fixed-time'
import { DAYS_OF_WEEK } from './constants'
import DaysOfWeekSelector from './DaysOfWeekSelector'
import type { TriggerErrors } from './scheduler-types'

// -- Types ------------------------------------------------------------------

export interface FixedTimeTriggerValue {
  time_of_day: string
  days_of_week: number[] | null
}

interface FixedTimeTriggerFormProps {
  value?: FixedTimeTriggerValue
  onChange: (value: FixedTimeTriggerValue) => void
  disabled?: boolean
  errors?: TriggerErrors
}

// -- Constants --------------------------------------------------------------

const DEFAULT_VALUE: FixedTimeTriggerValue = {
  time_of_day: '12:00',
  days_of_week: null,
}

const TIME_PRESETS = [
  { label: '6 AM', value: '06:00' },
  { label: '12 PM', value: '12:00' },
  { label: '6 PM', value: '18:00' },
  { label: '9 PM', value: '21:00' },
] as const

// -- Formatting helpers (pure functions, no React state) --------------------

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

// -- Component --------------------------------------------------------------

// Zod 4 + @hookform/resolvers type workaround (@hookform/resolvers@3.x + zod@4.x)
// TODO(#446): remove cast when resolvers#800 is fixed
// Upstream: https://github.com/react-hook-form/resolvers/issues/800
const resolver = zodResolver(
  fixedTimeTriggerSchema as unknown as Parameters<typeof zodResolver>[0],
) as unknown as Resolver<FixedTimeTriggerFormData>

export default function FixedTimeTriggerForm({
  value = DEFAULT_VALUE,
  onChange,
  disabled = false,
  errors: parentErrors = {},
}: FixedTimeTriggerFormProps) {
  // Stable callback ref -- prevents useWatch effect from re-running when
  // parent passes an inline arrow function as onChange.
  const onChangeRef = useRef(onChange)
  onChangeRef.current = onChange

  // Stable ref for the full value prop -- lets the propagation effect read
  // current days_of_week without adding `value` to its deps.
  const valueRef = useRef(value)
  valueRef.current = value

  // Initialized to current prop so prop-sync skips the first render
  // (no external change to detect yet).
  const lastPropagatedRef = useRef(value.time_of_day)

  const {
    control,
    reset,
    formState: { errors },
  } = useForm<FixedTimeTriggerFormData>({
    resolver,
    defaultValues: { time_of_day: value.time_of_day },
    mode: 'onChange',
  })

  // Prop sync: reset form when time_of_day changes externally
  // (e.g., preset button click, parent state change)
  useEffect(() => {
    if (value.time_of_day !== lastPropagatedRef.current) {
      lastPropagatedRef.current = value.time_of_day
      reset({ time_of_day: value.time_of_day })
    }
  }, [value.time_of_day, reset])

  // Propagate validated form changes -> parent
  const timeOfDay = useWatch({ control, name: 'time_of_day' })
  useEffect(() => {
    if (timeOfDay === undefined) return
    // Skip if value matches props (avoids cycle from prop sync)
    if (timeOfDay === valueRef.current.time_of_day) return
    // Only propagate valid values
    const result = fixedTimeTriggerSchema.safeParse({ time_of_day: timeOfDay })
    if (!result.success) return
    lastPropagatedRef.current = timeOfDay
    onChangeRef.current({ ...valueRef.current, time_of_day: timeOfDay })
  }, [timeOfDay])

  // Preset buttons bypass the form -- call onChange directly
  const handlePresetClick = (presetValue: string) => {
    onChangeRef.current({ ...valueRef.current, time_of_day: presetValue })
  }

  // DaysOfWeekSelector stays as direct callback (not in form)
  const handleDaysChange = useCallback((newDays: number[] | null) => {
    onChangeRef.current({ ...valueRef.current, days_of_week: newDays })
  }, [])

  const previewText = useMemo(() => {
    const daysText = formatDays(value.days_of_week)

    let preview = `At ${value.time_of_day}`
    if (daysText) preview += ` on ${daysText}`
    return preview
  }, [value.time_of_day, value.days_of_week])

  return (
    <div className="space-y-6">
      {/* Header */}
      <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
        Fixed Time Configuration
      </h3>

      {/* Time of Day Input */}
      <div>
        <label
          htmlFor="time_of_day"
          className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2"
        >
          Time of day:
        </label>
        <Controller
          name="time_of_day"
          control={control}
          render={({ field }) => (
            <input
              id="time_of_day"
              type="time"
              value={field.value}
              onChange={(e) => {
                field.onChange(e.target.value)
              }}
              onBlur={field.onBlur}
              ref={field.ref}
              disabled={disabled}
              className="w-full rounded-md border border-gray-300 dark:border-gray-600
                       bg-white dark:bg-gray-800 px-3 py-2 text-gray-900 dark:text-white
                       focus:ring-2 focus:ring-blue-500 focus:border-transparent
                       disabled:opacity-50 disabled:cursor-not-allowed"
              aria-label="Time of day"
              aria-invalid={!!errors.time_of_day}
              aria-describedby={
                errors.time_of_day ? 'time_of_day-error' : undefined
              }
            />
          )}
        />
        {(errors.time_of_day?.message ||
          (parentErrors.time_of_day &&
            typeof parentErrors.time_of_day === 'string')) && (
          <p
            id="time_of_day-error"
            role="alert"
            className="mt-1 text-sm text-red-600 dark:text-red-400"
          >
            {errors.time_of_day?.message ||
              (parentErrors.time_of_day as string)}
          </p>
        )}
      </div>

      {/* Quick Time Presets */}
      <div>
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
          Quick presets:
        </label>
        <div className="flex flex-wrap gap-2">
          {TIME_PRESETS.map((preset) => (
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
                  value.time_of_day === preset.value
                    ? 'bg-blue-500 text-white hover:bg-blue-600 dark:bg-blue-600 dark:hover:bg-blue-700'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200 dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600'
                }
                ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
              `}
              aria-label={`Set time to ${preset.value}`}
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
