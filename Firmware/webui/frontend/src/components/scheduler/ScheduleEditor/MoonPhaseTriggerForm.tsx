import { useEffect, useMemo, useRef } from 'react'
import { useForm, Controller, useWatch } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import type { Resolver } from 'react-hook-form'
import {
  moonPhaseTriggerSchema,
  type MoonPhaseTriggerFormData,
} from '../../../schemas/scheduler/moon-phase'
import { MOON_PHASES, SCHEDULE_LIMITS } from './constants'

// ── Types ──────────────────────────────────────────────────────────────

export interface MoonPhaseTriggerValue {
  moon_phase: string
  time_of_day: string
  offset_days: number
}

interface MoonPhaseTriggerFormProps {
  value?: MoonPhaseTriggerValue
  onChange: (value: MoonPhaseTriggerValue) => void
  disabled?: boolean
  errors?: Record<string, string>
}

// ── Constants ──────────────────────────────────────────────────────────

const DEFAULT_VALUE: MoonPhaseTriggerValue = {
  moon_phase: 'full',
  time_of_day: '20:00',
  offset_days: 0,
}

const OFFSET_PRESETS = [
  { label: '-1 day', value: -1 },
  { label: 'No offset', value: 0 },
  { label: '+1 day', value: 1 },
] as const

// ── Formatting helpers (pure functions, no React state) ────────────────

function formatOffset(days: number): string {
  if (days === 0) return ''
  const absDays = Math.abs(days)
  return `${absDays} day${absDays !== 1 ? 's' : ''}`
}

// ── Component ──────────────────────────────────────────────────────────

// Zod 4 + @hookform/resolvers type workaround (@hookform/resolvers@3.x + zod@4.x)
// TODO(#448): remove cast when resolvers#800 is fixed
// Upstream: https://github.com/react-hook-form/resolvers/issues/800
const resolver = zodResolver(
  moonPhaseTriggerSchema as unknown as Parameters<typeof zodResolver>[0],
) as unknown as Resolver<MoonPhaseTriggerFormData>

export default function MoonPhaseTriggerForm({
  value = DEFAULT_VALUE,
  onChange,
  disabled = false,
  errors: parentErrors = {},
}: MoonPhaseTriggerFormProps) {
  // Stable callback ref — prevents useWatch effect from re-running when
  // parent passes an inline arrow function as onChange.
  const onChangeRef = useRef(onChange)
  onChangeRef.current = onChange

  // Stable ref for the full value prop — lets the propagation effect read
  // current value without adding `value` to its deps.
  const valueRef = useRef(value)
  valueRef.current = value

  // Initialized to current prop so prop-sync skips the first render
  // (no external change to detect yet).
  const lastPropagatedRef = useRef({
    moon_phase: value.moon_phase,
    time_of_day: value.time_of_day,
    offset_days: value.offset_days,
  })

  const {
    control,
    reset,
    formState: { errors },
  } = useForm<MoonPhaseTriggerFormData>({
    resolver,
    defaultValues: {
      moon_phase: value.moon_phase as MoonPhaseTriggerFormData['moon_phase'],
      time_of_day: value.time_of_day,
      offset_days: value.offset_days,
    },
    mode: 'onChange',
  })

  // Prop sync: reset form when any field changes externally
  // (e.g., preset button click, parent state change)
  useEffect(() => {
    const last = lastPropagatedRef.current
    if (
      value.moon_phase !== last.moon_phase ||
      value.time_of_day !== last.time_of_day ||
      value.offset_days !== last.offset_days
    ) {
      lastPropagatedRef.current = {
        moon_phase: value.moon_phase,
        time_of_day: value.time_of_day,
        offset_days: value.offset_days,
      }
      reset({
        moon_phase: value.moon_phase as MoonPhaseTriggerFormData['moon_phase'],
        time_of_day: value.time_of_day,
        offset_days: value.offset_days,
      })
    }
  }, [value.moon_phase, value.time_of_day, value.offset_days, reset])

  // Propagate validated form changes → parent
  const watchedMoonPhase = useWatch({ control, name: 'moon_phase' })
  const watchedTimeOfDay = useWatch({ control, name: 'time_of_day' })
  const watchedOffset = useWatch({ control, name: 'offset_days' })
  useEffect(() => {
    if (
      watchedMoonPhase === undefined ||
      watchedTimeOfDay === undefined ||
      watchedOffset === undefined
    ) return
    // Skip if values match props (avoids cycle from prop sync)
    const current = valueRef.current
    if (
      watchedMoonPhase === current.moon_phase &&
      watchedTimeOfDay === current.time_of_day &&
      watchedOffset === current.offset_days
    ) return
    // Only propagate valid values
    const result = moonPhaseTriggerSchema.safeParse({
      moon_phase: watchedMoonPhase,
      time_of_day: watchedTimeOfDay,
      offset_days: watchedOffset,
    })
    if (!result.success) return
    lastPropagatedRef.current = {
      moon_phase: watchedMoonPhase,
      time_of_day: watchedTimeOfDay,
      offset_days: watchedOffset,
    }
    onChangeRef.current({
      moon_phase: watchedMoonPhase,
      time_of_day: watchedTimeOfDay,
      offset_days: watchedOffset,
    })
  }, [watchedMoonPhase, watchedTimeOfDay, watchedOffset])

  // Preset buttons bypass the form — call onChange directly
  const handlePresetClick = (presetValue: number) => {
    onChangeRef.current({ ...valueRef.current, offset_days: presetValue })
  }

  const previewText = useMemo(() => {
    const phase = MOON_PHASES.find((p) => p.value === value.moon_phase)
    const phaseLabel = phase ? phase.label : value.moon_phase
    const offsetText = formatOffset(value.offset_days)
    const time = value.time_of_day

    if (value.offset_days === 0) {
      return `On ${phaseLabel} at ${time}`
    } else if (value.offset_days > 0) {
      return `${offsetText} after ${phaseLabel} at ${time}`
    } else {
      return `${offsetText} before ${phaseLabel} at ${time}`
    }
  }, [value.moon_phase, value.time_of_day, value.offset_days])

  return (
    <div className="space-y-6">
      {/* Header */}
      <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
        Moon Phase Configuration
      </h3>

      {/* Moon Phase Selection */}
      <div>
        <label
          htmlFor="moon_phase"
          className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2"
        >
          Moon Phase:
        </label>
        <Controller
          name="moon_phase"
          control={control}
          render={({ field }) => (
            <select
              id="moon_phase"
              value={field.value}
              onChange={(e) => field.onChange(e.target.value)}
              onBlur={field.onBlur}
              ref={field.ref}
              disabled={disabled}
              className="w-full rounded-md border border-gray-300 dark:border-gray-600
                       bg-white dark:bg-gray-800 px-3 py-2 text-gray-900 dark:text-white
                       focus:ring-2 focus:ring-blue-500 focus:border-transparent
                       disabled:opacity-50 disabled:cursor-not-allowed"
              aria-label="Moon phase"
              aria-invalid={!!(errors.moon_phase || parentErrors.moon_phase)}
              aria-describedby={
                (errors.moon_phase || parentErrors.moon_phase)
                  ? 'moon_phase-error'
                  : undefined
              }
            >
              {MOON_PHASES.map((phase) => (
                <option key={phase.value} value={phase.value}>
                  {phase.label}
                </option>
              ))}
            </select>
          )}
        />
        {(errors.moon_phase?.message || parentErrors.moon_phase) && (
          <p
            id="moon_phase-error"
            role="alert"
            className="mt-1 text-sm text-red-600 dark:text-red-400"
          >
            {errors.moon_phase?.message || parentErrors.moon_phase}
          </p>
        )}
      </div>

      {/* Time of Day Input */}
      <div>
        <label
          htmlFor="time_of_day"
          className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2"
        >
          Time of Day:
        </label>
        <Controller
          name="time_of_day"
          control={control}
          render={({ field }) => (
            <input
              id="time_of_day"
              type="time"
              value={field.value}
              onChange={(e) => field.onChange(e.target.value)}
              onBlur={field.onBlur}
              ref={field.ref}
              disabled={disabled}
              className="w-full rounded-md border border-gray-300 dark:border-gray-600
                       bg-white dark:bg-gray-800 px-3 py-2 text-gray-900 dark:text-white
                       focus:ring-2 focus:ring-blue-500 focus:border-transparent
                       disabled:opacity-50 disabled:cursor-not-allowed"
              aria-label="Time of day"
              aria-invalid={!!(errors.time_of_day || parentErrors.time_of_day)}
              aria-describedby={
                (errors.time_of_day || parentErrors.time_of_day)
                  ? 'time_of_day-error'
                  : undefined
              }
            />
          )}
        />
        {(errors.time_of_day?.message || parentErrors.time_of_day) && (
          <p
            id="time_of_day-error"
            role="alert"
            className="mt-1 text-sm text-red-600 dark:text-red-400"
          >
            {errors.time_of_day?.message || parentErrors.time_of_day}
          </p>
        )}
      </div>

      {/* Offset Days Input */}
      <div>
        <label
          htmlFor="offset_days"
          className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2"
        >
          Offset (days):
        </label>
        <div className="flex items-center gap-2">
          <Controller
            name="offset_days"
            control={control}
            render={({ field }) => (
              <input
                id="offset_days"
                type="number"
                min={-SCHEDULE_LIMITS.MAX_OFFSET_DAYS}
                max={SCHEDULE_LIMITS.MAX_OFFSET_DAYS}
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
                aria-label="Offset in days"
                aria-invalid={!!(errors.offset_days || parentErrors.offset_days)}
                aria-describedby={
                  (errors.offset_days || parentErrors.offset_days)
                    ? 'offset_days-error'
                    : undefined
                }
              />
            )}
          />
          <span className="text-sm text-gray-700 dark:text-gray-300">days</span>
        </div>
        {(errors.offset_days?.message || parentErrors.offset_days) && (
          <p
            id="offset_days-error"
            role="alert"
            className="mt-1 text-sm text-red-600 dark:text-red-400"
          >
            {errors.offset_days?.message || parentErrors.offset_days}
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
                  value.offset_days === preset.value
                    ? 'bg-blue-500 text-white hover:bg-blue-600 dark:bg-blue-600 dark:hover:bg-blue-700'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200 dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600'
                }
                ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
              `}
              aria-label={`Set offset to ${preset.value} day${Math.abs(preset.value) !== 1 ? 's' : ''}`}
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
