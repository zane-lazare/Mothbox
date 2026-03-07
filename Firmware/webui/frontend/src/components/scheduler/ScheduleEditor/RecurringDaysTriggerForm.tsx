import { useEffect, useMemo, useRef } from 'react'
import { useForm, Controller, useWatch } from 'react-hook-form'
import {
  recurringDaysTriggerSchema,
  type RecurringDaysTriggerFormData,
} from '../../../schemas/scheduler/recurring-days'
import { createZodResolver } from './zodResolverWorkaround'
import { DAYS_OF_WEEK } from './constants'
import type { TriggerErrors } from './scheduler-types'

// -- Types ------------------------------------------------------------------

export interface RecurringDaysTriggerValue {
  days: number[]
  time: string
}

interface RecurringDaysTriggerFormProps {
  value?: RecurringDaysTriggerValue
  onChange: (value: RecurringDaysTriggerValue) => void
  disabled?: boolean
  errors?: TriggerErrors
}

// -- Constants --------------------------------------------------------------

// Defaults to weekend nights (Sun/Fri/Sat at 8 PM) — typical Mothbox deployment schedule
const DEFAULT_VALUE: RecurringDaysTriggerValue = {
  days: [0, 5, 6],
  time: '20:00',
}

const TIME_PRESETS = [
  { label: '6 AM', value: '06:00' },
  { label: '8 PM', value: '20:00' },
  { label: '9 PM', value: '21:00' },
  { label: '10 PM', value: '22:00' },
] as const

// -- Formatting helpers (pure functions, no React state) --------------------

function formatDays(days: number[]): string {
  if (days.length === 0) return 'no days'
  if (days.length === 7) return 'every day'

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

const resolver = createZodResolver<RecurringDaysTriggerFormData>(recurringDaysTriggerSchema)

export default function RecurringDaysTriggerForm({
  value = DEFAULT_VALUE,
  onChange,
  disabled = false,
  errors: parentErrors = {},
}: RecurringDaysTriggerFormProps) {
  // Stable callback ref -- prevents useWatch effect from re-running when
  // parent passes an inline arrow function as onChange.
  const onChangeRef = useRef(onChange)
  onChangeRef.current = onChange

  // Stable ref for the full value prop -- lets the propagation effect read
  // current days without adding `value` to its deps.
  const valueRef = useRef(value)
  valueRef.current = value

  // Initialized to current prop so prop-sync skips the first render
  // (no external change to detect yet).
  const lastPropagatedRef = useRef(value.time)

  const {
    control,
    reset,
    formState: { errors },
  } = useForm<RecurringDaysTriggerFormData>({
    resolver,
    defaultValues: { days: value.days, time: value.time },
    mode: 'onChange',
  })

  // Prop sync: reset form when time changes externally
  // (e.g., preset button click, parent state change)
  useEffect(() => {
    if (value.time !== lastPropagatedRef.current) {
      lastPropagatedRef.current = value.time
      reset({ days: value.days, time: value.time })
    }
  }, [value.time, value.days, reset])

  // Propagate validated form changes -> parent
  const watchedTime = useWatch({ control, name: 'time' })
  useEffect(() => {
    if (watchedTime === undefined) return
    // Skip if value matches props (avoids cycle from prop sync)
    if (watchedTime === valueRef.current.time) return
    // Only propagate valid values
    const result = recurringDaysTriggerSchema.safeParse({
      days: valueRef.current.days,
      time: watchedTime,
    })
    if (!result.success) return
    lastPropagatedRef.current = watchedTime
    onChangeRef.current({ ...valueRef.current, time: watchedTime })
  }, [watchedTime])

  // Day toggle handler
  const handleDayToggle = (dayValue: number) => {
    const currentDays = valueRef.current.days
    const isSelected = currentDays.includes(dayValue)

    let newDays: number[]
    if (isSelected) {
      // Don't allow deselecting the last day
      if (currentDays.length <= 1) return
      newDays = currentDays.filter((d) => d !== dayValue)
    } else {
      newDays = [...currentDays, dayValue].sort((a, b) => a - b)
    }

    onChangeRef.current({ ...valueRef.current, days: newDays })
  }

  // Preset buttons bypass the form -- call onChange directly
  const handlePresetClick = (presetValue: string) => {
    onChangeRef.current({ ...valueRef.current, time: presetValue })
  }

  const previewText = useMemo(() => {
    const daysText = formatDays(value.days)
    return `At ${value.time} on ${daysText}`
  }, [value.days, value.time])

  return (
    <div className="space-y-6">
      {/* Header */}
      <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
        Recurring Days Configuration
      </h3>

      {/* Day Selection */}
      <div>
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
          Days of week:
        </label>
        <div
          className="flex flex-wrap gap-2"
          role="group"
          aria-label="Days of week"
          aria-describedby={parentErrors.days ? 'days-error' : undefined}
        >
          {DAYS_OF_WEEK.map((day) => {
            const isSelected = value.days.includes(day.value)
            const isLastSelected = isSelected && value.days.length === 1
            return (
              <button
                key={day.value}
                type="button"
                onClick={() => handleDayToggle(day.value)}
                disabled={disabled || isLastSelected}
                title={isLastSelected ? 'At least one day required' : undefined}
                className={`
                  px-4 py-2 rounded-md text-sm font-medium
                  transition-colors duration-150
                  focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2
                  dark:focus:ring-offset-gray-800
                  ${
                    isSelected
                      ? 'bg-blue-500 text-white hover:bg-blue-600 dark:bg-blue-600 dark:hover:bg-blue-700'
                      : 'bg-gray-100 text-gray-700 hover:bg-gray-200 dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600'
                  }
                  ${disabled || isLastSelected ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
                `}
                aria-pressed={isSelected}
                aria-label={day.label}
              >
                {day.shortLabel}
              </button>
            )
          })}
        </div>
        {(parentErrors.days && typeof parentErrors.days === 'string') && (
          <p
            id="days-error"
            role="alert"
            className="mt-1 text-sm text-red-600 dark:text-red-400"
          >
            {parentErrors.days}
          </p>
        )}
      </div>

      {/* Time Input */}
      <div>
        <label
          htmlFor="recurring_time"
          className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2"
        >
          Time of day:
        </label>
        <Controller
          name="time"
          control={control}
          render={({ field }) => (
            <input
              id="recurring_time"
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
              aria-invalid={!!errors.time}
              aria-describedby={
                errors.time ? 'recurring_time-error' : undefined
              }
            />
          )}
        />
        {(errors.time?.message ||
          (parentErrors.time &&
            typeof parentErrors.time === 'string')) && (
          <p
            id="recurring_time-error"
            role="alert"
            className="mt-1 text-sm text-red-600 dark:text-red-400"
          >
            {errors.time?.message ||
              (parentErrors.time as string)}
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
                  value.time === preset.value
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
