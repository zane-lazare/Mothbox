import { useEffect, useRef } from 'react'
import { useForm, Controller, useWatch } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import type { Resolver } from 'react-hook-form'
import {
  preConditionSchema,
  type PreConditionFormData,
} from '../../../schemas/scheduler/pre-condition'
import { SENSOR_TYPES, SCHEDULE_LIMITS } from './constants'

// -- Types -------------------------------------------------------------------

export interface PreConditionValue {
  trigger_type?: string
  sensor_type: string
  comparison: string
  threshold: number
  cooldown_minutes: number
  time_window?: { start_time: string; end_time: string } | null
}

interface PreConditionFormProps {
  preCondition: PreConditionValue | null
  onChange: (value: PreConditionValue | null) => void
  routineIndex: number
  disabled?: boolean
  errors?: Record<string, string>
}

// -- Constants ---------------------------------------------------------------

/** Default pre-condition when enabled */
const DEFAULT_PRE_CONDITION: PreConditionValue = {
  trigger_type: 'sensor',
  sensor_type: 'light',
  comparison: 'lt',
  threshold: 100,
  cooldown_minutes: 5,
}

/** Unit labels for sensor types */
const SENSOR_UNITS: Record<string, string> = {
  light: 'lux',
  temperature: '\u00B0C',
}

// -- Resolver ----------------------------------------------------------------

// Zod 4 + @hookform/resolvers type workaround (@hookform/resolvers@3.x + zod@4.x)
// TODO(#450): remove cast when resolvers#800 is fixed
// Upstream: https://github.com/react-hook-form/resolvers/issues/800
const resolver = zodResolver(
  preConditionSchema as unknown as Parameters<typeof zodResolver>[0],
) as unknown as Resolver<PreConditionFormData>

// -- Component ---------------------------------------------------------------

export default function PreConditionForm({
  preCondition,
  onChange,
  routineIndex,
  disabled = false,
  errors: parentErrors = {},
}: PreConditionFormProps) {
  // Whether the pre-condition is currently enabled (derived from prop)
  const enabled = preCondition !== null

  // Stable callback ref -- prevents useWatch effect from re-running when
  // parent passes an inline arrow function as onChange.
  const onChangeRef = useRef(onChange)
  onChangeRef.current = onChange

  // Stable ref for the full preCondition prop -- lets the propagation effect
  // read current value without adding `preCondition` to its deps.
  const preConditionRef = useRef(preCondition)
  preConditionRef.current = preCondition

  // Build default values for the form. When preCondition is null, use our
  // defaults so the form always has valid data for internal rendering.
  const defaults: PreConditionFormData = {
    sensor_type: (preCondition?.sensor_type ?? 'light') as PreConditionFormData['sensor_type'],
    comparison: (preCondition?.comparison ?? 'lt') as PreConditionFormData['comparison'],
    threshold: preCondition?.threshold ?? 100,
    cooldown_minutes: preCondition?.cooldown_minutes ?? 5,
    time_window: preCondition?.time_window ?? null,
  }

  // Initialized to current prop so prop-sync skips the first render
  // (no external change to detect yet).
  const lastPropagatedRef = useRef<PreConditionFormData>({
    sensor_type: defaults.sensor_type,
    comparison: defaults.comparison,
    threshold: defaults.threshold,
    cooldown_minutes: defaults.cooldown_minutes,
    time_window: defaults.time_window,
  })

  const {
    control,
    reset,
    formState: { errors },
  } = useForm<PreConditionFormData>({
    resolver,
    defaultValues: defaults,
    mode: 'onChange',
  })

  // Prop sync: reset form when fields change externally
  // (e.g., preset button click, parent state change, toggle on/off)
  useEffect(() => {
    const pc = preConditionRef.current
    if (!pc) return
    const last = lastPropagatedRef.current
    if (
      pc.sensor_type !== last.sensor_type ||
      pc.comparison !== last.comparison ||
      pc.threshold !== last.threshold ||
      pc.cooldown_minutes !== last.cooldown_minutes ||
      pc.time_window?.start_time !== last.time_window?.start_time ||
      pc.time_window?.end_time !== last.time_window?.end_time ||
      (pc.time_window === null) !== (last.time_window === null)
    ) {
      const next: PreConditionFormData = {
        sensor_type: pc.sensor_type as PreConditionFormData['sensor_type'],
        comparison: pc.comparison as PreConditionFormData['comparison'],
        threshold: pc.threshold,
        cooldown_minutes: pc.cooldown_minutes,
        time_window: pc.time_window ?? null,
      }
      lastPropagatedRef.current = next
      reset(next)
    }
  }, [
    preCondition?.sensor_type,
    preCondition?.comparison,
    preCondition?.threshold,
    preCondition?.cooldown_minutes,
    preCondition?.time_window?.start_time,
    preCondition?.time_window?.end_time,
    reset,
  ])

  // Watch individual form fields for propagation
  const watchedSensorType = useWatch({ control, name: 'sensor_type' })
  const watchedComparison = useWatch({ control, name: 'comparison' })
  const watchedThreshold = useWatch({ control, name: 'threshold' })
  const watchedCooldown = useWatch({ control, name: 'cooldown_minutes' })
  const watchedTimeWindow = useWatch({ control, name: 'time_window' })

  // Propagate validated form changes -> parent
  useEffect(() => {
    if (
      watchedSensorType === undefined ||
      watchedComparison === undefined ||
      watchedThreshold === undefined ||
      watchedCooldown === undefined
    ) return

    // Only propagate when enabled
    const current = preConditionRef.current
    if (!current) return

    // Skip if values match props (avoids cycle from prop sync)
    if (
      watchedSensorType === current.sensor_type &&
      watchedComparison === current.comparison &&
      watchedThreshold === current.threshold &&
      watchedCooldown === current.cooldown_minutes &&
      watchedTimeWindow?.start_time === current.time_window?.start_time &&
      watchedTimeWindow?.end_time === current.time_window?.end_time &&
      (watchedTimeWindow === null) === ((current.time_window ?? null) === null)
    ) return

    // Only propagate valid values
    const result = preConditionSchema.safeParse({
      sensor_type: watchedSensorType,
      comparison: watchedComparison,
      threshold: watchedThreshold,
      cooldown_minutes: watchedCooldown,
      time_window: watchedTimeWindow,
    })
    if (!result.success) return

    const next: PreConditionFormData = {
      sensor_type: watchedSensorType,
      comparison: watchedComparison,
      threshold: watchedThreshold,
      cooldown_minutes: watchedCooldown,
      time_window: watchedTimeWindow,
    }
    lastPropagatedRef.current = next

    // Preserve trigger_type and any extra fields from the prop
    onChangeRef.current({
      ...current,
      sensor_type: watchedSensorType,
      comparison: watchedComparison,
      threshold: watchedThreshold,
      cooldown_minutes: watchedCooldown,
      time_window: watchedTimeWindow,
    })
  }, [watchedSensorType, watchedComparison, watchedThreshold, watchedCooldown, watchedTimeWindow])

  // -- Toggle handlers (bypass RHF) ------------------------------------------

  /** Enable/disable pre-condition toggle */
  const handleToggle = (e: React.ChangeEvent<HTMLInputElement>) => {
    const isEnabled = e.target.checked
    if (!isEnabled) {
      onChangeRef.current(null)
    } else {
      onChangeRef.current(DEFAULT_PRE_CONDITION)
    }
  }

  /** Enable/disable time window toggle */
  const handleTimeWindowToggle = (e: React.ChangeEvent<HTMLInputElement>) => {
    const isEnabled = e.target.checked
    const current = preConditionRef.current
    if (!current) return
    if (isEnabled) {
      onChangeRef.current({
        ...current,
        time_window: { start_time: '21:00', end_time: '06:00' },
      })
    } else {
      onChangeRef.current({
        ...current,
        time_window: null,
      })
    }
  }

  // -- Cross-field derived error ----------------------------------------------

  const timeWindowError =
    watchedTimeWindow?.start_time &&
    watchedTimeWindow?.end_time &&
    watchedTimeWindow.start_time === watchedTimeWindow.end_time
      ? 'Start and end times cannot be the same'
      : null

  return (
    <div className="space-y-3">
      {/* Toggle */}
      <div className="flex items-center gap-3 text-sm">
        <input
          type="checkbox"
          id={`pre-condition-toggle-${routineIndex}`}
          checked={enabled}
          onChange={handleToggle}
          disabled={disabled}
          className="rounded border-gray-600 disabled:opacity-50"
          data-testid={`pre-condition-toggle-${routineIndex}`}
        />
        <label
          htmlFor={`pre-condition-toggle-${routineIndex}`}
          className="text-gray-400 cursor-pointer"
        >
          Only run if sensor condition met
        </label>
      </div>

      {/* Conditional fields */}
      {enabled && preCondition && (
        <div className="pl-6 space-y-3">
          <div className="flex items-center gap-3 text-sm flex-wrap">
            {/* Sensor type - filtered to light/temperature per issue #325 */}
            <Controller
              name="sensor_type"
              control={control}
              render={({ field }) => (
                <select
                  value={field.value}
                  onChange={(e) => field.onChange(e.target.value)}
                  onBlur={field.onBlur}
                  ref={field.ref}
                  disabled={disabled}
                  aria-label="Sensor type"
                  aria-invalid={!!(errors.sensor_type || parentErrors.sensor_type)}
                  aria-describedby={
                    (errors.sensor_type || parentErrors.sensor_type)
                      ? 'sensor_type-error'
                      : undefined
                  }
                  className="rounded-md border border-gray-300 dark:border-gray-600
                             bg-white dark:bg-gray-800 px-2 py-1 text-gray-900 dark:text-white
                             focus:ring-2 focus:ring-blue-500 focus:border-transparent
                             disabled:opacity-50 disabled:cursor-not-allowed"
                  data-testid="pre-condition-sensor"
                >
                  {SENSOR_TYPES.filter(
                    (s: { value: string; label: string }) => s.value !== 'motion',
                  ).map((sensor: { value: string; label: string }) => (
                    <option key={sensor.value} value={sensor.value}>
                      {sensor.label}
                    </option>
                  ))}
                </select>
              )}
            />
            {(errors.sensor_type?.message || parentErrors.sensor_type) && (
              <p
                id="sensor_type-error"
                role="alert"
                className="text-sm text-red-600 dark:text-red-400"
              >
                {errors.sensor_type?.message || parentErrors.sensor_type}
              </p>
            )}

            {/*
             * Comparison operator - only lt/gt/eq per issue #325 spec.
             * SENSOR_COMPARISONS in constants.js also has gte/lte, but
             * pre-conditions only need basic comparisons.
             */}
            <Controller
              name="comparison"
              control={control}
              render={({ field }) => (
                <select
                  value={field.value}
                  onChange={(e) => field.onChange(e.target.value)}
                  onBlur={field.onBlur}
                  ref={field.ref}
                  disabled={disabled}
                  aria-label="Comparison operator"
                  aria-invalid={!!(errors.comparison || parentErrors.comparison)}
                  aria-describedby={
                    (errors.comparison || parentErrors.comparison)
                      ? 'comparison-error'
                      : undefined
                  }
                  className="rounded-md border border-gray-300 dark:border-gray-600
                             bg-white dark:bg-gray-800 px-2 py-1 text-gray-900 dark:text-white
                             focus:ring-2 focus:ring-blue-500 focus:border-transparent
                             disabled:opacity-50 disabled:cursor-not-allowed"
                  data-testid="pre-condition-op"
                >
                  <option value="lt">is below</option>
                  <option value="gt">is above</option>
                  <option value="eq">equals</option>
                </select>
              )}
            />
            {(errors.comparison?.message || parentErrors.comparison) && (
              <p
                id="comparison-error"
                role="alert"
                className="text-sm text-red-600 dark:text-red-400"
              >
                {errors.comparison?.message || parentErrors.comparison}
              </p>
            )}

            {/* Threshold */}
            <Controller
              name="threshold"
              control={control}
              render={({ field }) => (
                <input
                  type="number"
                  min={0}
                  step="any"
                  value={Number.isNaN(field.value) ? '' : field.value}
                  onChange={(e) => {
                    const raw = e.target.value
                    field.onChange(raw === '' ? NaN : Number(raw))
                  }}
                  onBlur={field.onBlur}
                  ref={field.ref}
                  disabled={disabled}
                  aria-label="Threshold value"
                  aria-invalid={!!(errors.threshold || parentErrors.threshold)}
                  aria-describedby={
                    (errors.threshold || parentErrors.threshold)
                      ? 'threshold-error'
                      : undefined
                  }
                  className="w-20 rounded-md border border-gray-300 dark:border-gray-600
                             bg-white dark:bg-gray-800 px-2 py-1 text-gray-900 dark:text-white text-center
                             focus:ring-2 focus:ring-blue-500 focus:border-transparent
                             disabled:opacity-50 disabled:cursor-not-allowed"
                  data-testid="pre-condition-threshold"
                />
              )}
            />
            <span
              className="text-xs text-gray-500 dark:text-gray-400"
              data-testid="pre-condition-unit"
            >
              {SENSOR_UNITS[watchedSensorType] || ''}
            </span>
          </div>
          {/* Threshold validation error */}
          {(errors.threshold?.message || parentErrors.threshold) && (
            <p
              id="threshold-error"
              role="alert"
              className="text-sm text-red-600 dark:text-red-400"
              data-testid="pre-condition-error"
            >
              {errors.threshold?.message || parentErrors.threshold}
            </p>
          )}

          {/* Cooldown */}
          <div className="flex items-center gap-2 text-sm">
            <span className="text-gray-400">Cooldown:</span>
            <Controller
              name="cooldown_minutes"
              control={control}
              render={({ field }) => (
                <input
                  type="number"
                  min={SCHEDULE_LIMITS.MIN_COOLDOWN_MINUTES}
                  max={SCHEDULE_LIMITS.MAX_COOLDOWN_MINUTES}
                  step="any"
                  value={Number.isNaN(field.value) ? '' : field.value}
                  onChange={(e) => {
                    const raw = e.target.value
                    field.onChange(raw === '' ? NaN : Number(raw))
                  }}
                  onBlur={field.onBlur}
                  ref={field.ref}
                  disabled={disabled}
                  aria-label="Cooldown minutes"
                  aria-invalid={!!(errors.cooldown_minutes || parentErrors.cooldown_minutes)}
                  aria-describedby={
                    (errors.cooldown_minutes || parentErrors.cooldown_minutes)
                      ? 'cooldown_minutes-error'
                      : undefined
                  }
                  className="w-16 rounded-md border border-gray-300 dark:border-gray-600
                             bg-white dark:bg-gray-800 px-2 py-1 text-gray-900 dark:text-white text-center
                             focus:ring-2 focus:ring-blue-500 focus:border-transparent
                             disabled:opacity-50 disabled:cursor-not-allowed"
                  data-testid="pre-condition-cooldown"
                />
              )}
            />
            <span className="text-xs text-gray-500 dark:text-gray-400">minutes</span>
          </div>
          {(errors.cooldown_minutes?.message || parentErrors.cooldown_minutes) && (
            <p
              id="cooldown_minutes-error"
              role="alert"
              className="text-sm text-red-600 dark:text-red-400"
              data-testid="pre-condition-cooldown-error"
            >
              {errors.cooldown_minutes?.message || parentErrors.cooldown_minutes}
            </p>
          )}

          {/* Time window toggle */}
          <div className="flex items-center gap-3 text-sm">
            <input
              type="checkbox"
              id={`pre-condition-tw-toggle-${routineIndex}`}
              checked={!!preCondition?.time_window}
              onChange={handleTimeWindowToggle}
              disabled={disabled}
              className="rounded border-gray-600 disabled:opacity-50"
              data-testid="pre-condition-time-window-toggle"
            />
            <label
              htmlFor={`pre-condition-tw-toggle-${routineIndex}`}
              className="text-gray-400 cursor-pointer"
            >
              Restrict to time window
            </label>
          </div>

          {/* Time window fields */}
          {preCondition?.time_window && (
            <div className="pl-6 flex items-center gap-2 text-sm">
              <Controller
                name="time_window.start_time"
                control={control}
                render={({ field }) => (
                  <input
                    type="time"
                    value={field.value || '21:00'}
                    onChange={(e) => field.onChange(e.target.value)}
                    onBlur={field.onBlur}
                    ref={field.ref}
                    disabled={disabled}
                    aria-label="Time window start"
                    className="rounded-md border border-gray-300 dark:border-gray-600
                               bg-white dark:bg-gray-800 px-2 py-1 text-gray-900 dark:text-white
                               focus:ring-2 focus:ring-blue-500 focus:border-transparent
                               disabled:opacity-50 disabled:cursor-not-allowed"
                    data-testid="pre-condition-tw-start"
                  />
                )}
              />
              <span className="text-gray-400">to</span>
              <Controller
                name="time_window.end_time"
                control={control}
                render={({ field }) => (
                  <input
                    type="time"
                    value={field.value || '06:00'}
                    onChange={(e) => field.onChange(e.target.value)}
                    onBlur={field.onBlur}
                    ref={field.ref}
                    disabled={disabled}
                    aria-label="Time window end"
                    className="rounded-md border border-gray-300 dark:border-gray-600
                               bg-white dark:bg-gray-800 px-2 py-1 text-gray-900 dark:text-white
                               focus:ring-2 focus:ring-blue-500 focus:border-transparent
                               disabled:opacity-50 disabled:cursor-not-allowed"
                    data-testid="pre-condition-tw-end"
                  />
                )}
              />
            </div>
          )}
          {/* Time window validation error */}
          {timeWindowError && (
            <p
              role="alert"
              className="pl-6 text-sm text-red-600 dark:text-red-400"
              data-testid="pre-condition-tw-error"
            >
              {timeWindowError}
            </p>
          )}
        </div>
      )}
    </div>
  )
}
