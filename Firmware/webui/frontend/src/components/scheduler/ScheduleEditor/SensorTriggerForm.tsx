import { useCallback, useEffect, useMemo, useRef } from 'react'
import { useForm, Controller, useWatch } from 'react-hook-form'
import {
  sensorTriggerSchema,
  type SensorTriggerFormData,
} from '../../../schemas/scheduler/sensor'
import { createZodResolver } from './zodResolverWorkaround'
import { SENSOR_TYPES, SENSOR_COMPARISONS, SCHEDULE_LIMITS } from './constants'
import type { TriggerErrors } from './scheduler-types'

// -- Types ------------------------------------------------------------------

export interface SensorTriggerValue {
  sensor_type: string
  comparison: string
  threshold: number
  cooldown_minutes: number
}

interface SensorTriggerFormProps {
  value?: SensorTriggerValue
  onChange: (value: SensorTriggerValue) => void
  disabled?: boolean
  errors?: TriggerErrors
}

// -- Constants --------------------------------------------------------------

const DEFAULT_VALUE: SensorTriggerValue = {
  sensor_type: 'light',
  comparison: 'lt',
  threshold: 100,
  cooldown_minutes: 5,
}

// -- Helpers ----------------------------------------------------------------

/** Serialize the four form-owned fields for quick equality checks. */
function serializeFormFields(v: SensorTriggerFormData): string {
  return `${v.sensor_type}|${v.comparison}|${v.threshold}|${v.cooldown_minutes}`
}

/**
 * Get description for a sensor type value.
 */
function getSensorDescription(sensorType: string): string {
  const sensor = SENSOR_TYPES.find((s) => s.value === sensorType)
  return sensor ? sensor.description : ''
}

/**
 * Get label for a sensor type value.
 */
function getSensorLabel(sensorType: string): string {
  const sensor = SENSOR_TYPES.find((s) => s.value === sensorType)
  return sensor ? sensor.label.toLowerCase() : sensorType
}

/**
 * Get symbol for a comparison operator value.
 */
function getComparisonSymbol(comparison: string): string {
  const comp = SENSOR_COMPARISONS.find((c) => c.value === comparison)
  return comp ? comp.symbol : comparison
}

/**
 * Get unit string for a sensor type value.
 */
function getSensorUnit(sensorType: string): string {
  const units: Record<string, string> = {
    motion: '',
    light: 'lux',
    temperature: '\u00B0C',
  }
  return units[sensorType] || ''
}

// -- Component --------------------------------------------------------------

const resolver = createZodResolver<SensorTriggerFormData>(sensorTriggerSchema)

export default function SensorTriggerForm({
  value = DEFAULT_VALUE,
  onChange,
  disabled = false,
  errors: parentErrors = {},
}: SensorTriggerFormProps) {
  // Stable callback ref -- prevents useWatch effect from re-running when
  // parent passes an inline arrow function as onChange.
  const onChangeRef = useRef(onChange)
  onChangeRef.current = onChange

  // Stable ref for the full value prop -- lets the propagation effect read
  // current value without adding `value` to its deps.
  const valueRef = useRef(value)
  valueRef.current = value

  // Track last propagated form fields to avoid loops between prop sync and
  // propagation. Initialized to current prop so prop-sync skips first render.
  const lastPropagatedRef = useRef(
    serializeFormFields({
      sensor_type: value.sensor_type,
      comparison: value.comparison,
      threshold: value.threshold,
      cooldown_minutes: value.cooldown_minutes,
    } as SensorTriggerFormData),
  )

  const {
    control,
    reset,
    formState: { errors },
  } = useForm<SensorTriggerFormData>({
    resolver,
    defaultValues: {
      sensor_type: value.sensor_type as SensorTriggerFormData['sensor_type'],
      comparison: value.comparison as SensorTriggerFormData['comparison'],
      threshold: value.threshold,
      cooldown_minutes: value.cooldown_minutes,
    },
    mode: 'onChange',
  })

  // Prop sync: reset form when value fields change externally
  // (e.g., parent state change)
  useEffect(() => {
    const incoming = serializeFormFields({
      sensor_type: value.sensor_type,
      comparison: value.comparison,
      threshold: value.threshold,
      cooldown_minutes: value.cooldown_minutes,
    } as SensorTriggerFormData)
    if (incoming !== lastPropagatedRef.current) {
      lastPropagatedRef.current = incoming
      reset({
        sensor_type: value.sensor_type as SensorTriggerFormData['sensor_type'],
        comparison: value.comparison as SensorTriggerFormData['comparison'],
        threshold: value.threshold,
        cooldown_minutes: value.cooldown_minutes,
      })
    }
  }, [value.sensor_type, value.comparison, value.threshold, value.cooldown_minutes, reset])

  // Propagate validated form changes -> parent
  const watched = useWatch({ control })
  useEffect(() => {
    if (
      watched.sensor_type === undefined ||
      watched.comparison === undefined ||
      watched.threshold === undefined ||
      watched.cooldown_minutes === undefined
    ) {
      return
    }

    const currentSerial = serializeFormFields(watched as SensorTriggerFormData)

    // Skip if value matches props (avoids cycle from prop sync)
    const propsSerial = serializeFormFields({
      sensor_type: valueRef.current.sensor_type,
      comparison: valueRef.current.comparison,
      threshold: valueRef.current.threshold,
      cooldown_minutes: valueRef.current.cooldown_minutes,
    } as SensorTriggerFormData)
    if (currentSerial === propsSerial) return

    // Only propagate valid values
    const result = sensorTriggerSchema.safeParse(watched)
    if (!result.success) return

    lastPropagatedRef.current = currentSerial
    onChangeRef.current({
      sensor_type: watched.sensor_type as string,
      comparison: watched.comparison as string,
      threshold: watched.threshold as number,
      cooldown_minutes: watched.cooldown_minutes as number,
    })
  }, [watched])

  // Memoized sensor unit for current sensor type (used in JSX)
  const sensorUnit = useMemo(
    () => getSensorUnit(value.sensor_type),
    [value.sensor_type],
  )

  // Memoized preview text
  const previewText = useMemo(() => {
    const sensorLabel = getSensorLabel(value.sensor_type)
    const comparisonSymbol = getComparisonSymbol(value.comparison)
    const unit = getSensorUnit(value.sensor_type)
    const thresholdText = unit
      ? `${value.threshold} ${unit}`
      : value.threshold

    return `When ${sensorLabel} ${comparisonSymbol} ${thresholdText}, cooldown: ${value.cooldown_minutes} min`
  }, [value.sensor_type, value.comparison, value.threshold, value.cooldown_minutes])

  return (
    <div className="space-y-6">
      {/* Header */}
      <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
        Sensor Configuration
      </h3>

      {/* Sensor Type Selection */}
      <div>
        <label
          htmlFor="sensor_type"
          className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2"
        >
          Sensor Type:
        </label>
        <Controller
          name="sensor_type"
          control={control}
          render={({ field }) => (
            <select
              id="sensor_type"
              value={field.value}
              onChange={(e) => field.onChange(e.target.value)}
              onBlur={field.onBlur}
              ref={field.ref as React.Ref<HTMLSelectElement>}
              disabled={disabled}
              className="w-full rounded-md border border-gray-300 dark:border-gray-600
                       bg-white dark:bg-gray-800 px-3 py-2 text-gray-900 dark:text-white
                       focus:ring-2 focus:ring-blue-500 focus:border-transparent
                       disabled:opacity-50 disabled:cursor-not-allowed"
              aria-label="Sensor type"
              aria-invalid={!!errors.sensor_type}
              aria-describedby={
                errors.sensor_type ? 'sensor_type-error' : undefined
              }
            >
              {SENSOR_TYPES.map((sensor) => (
                <option key={sensor.value} value={sensor.value}>
                  {sensor.label}
                </option>
              ))}
            </select>
          )}
        />
        {(errors.sensor_type?.message ||
          (parentErrors.sensor_type &&
            typeof parentErrors.sensor_type === 'string')) && (
          <p
            id="sensor_type-error"
            role="alert"
            className="mt-1 text-sm text-red-600 dark:text-red-400"
          >
            {errors.sensor_type?.message ||
              (parentErrors.sensor_type as string)}
          </p>
        )}
        {/* Sensor Type Description */}
        <p className="mt-2 text-sm text-gray-500 dark:text-gray-300">
          {getSensorDescription(value.sensor_type)}
        </p>
      </div>

      {/* Comparison Operator Selection */}
      <div>
        <label
          htmlFor="comparison"
          className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2"
        >
          Comparison:
        </label>
        <Controller
          name="comparison"
          control={control}
          render={({ field }) => (
            <select
              id="comparison"
              value={field.value}
              onChange={(e) => field.onChange(e.target.value)}
              onBlur={field.onBlur}
              ref={field.ref as React.Ref<HTMLSelectElement>}
              disabled={disabled}
              className="w-full rounded-md border border-gray-300 dark:border-gray-600
                       bg-white dark:bg-gray-800 px-3 py-2 text-gray-900 dark:text-white
                       focus:ring-2 focus:ring-blue-500 focus:border-transparent
                       disabled:opacity-50 disabled:cursor-not-allowed"
              aria-label="Comparison"
              aria-invalid={!!errors.comparison}
              aria-describedby={
                errors.comparison ? 'comparison-error' : undefined
              }
            >
              {SENSOR_COMPARISONS.map((comp) => (
                <option key={comp.value} value={comp.value}>
                  {comp.label} ({comp.symbol})
                </option>
              ))}
            </select>
          )}
        />
        {(errors.comparison?.message ||
          (parentErrors.comparison &&
            typeof parentErrors.comparison === 'string')) && (
          <p
            id="comparison-error"
            role="alert"
            className="mt-1 text-sm text-red-600 dark:text-red-400"
          >
            {errors.comparison?.message ||
              (parentErrors.comparison as string)}
          </p>
        )}
      </div>

      {/* Threshold Input */}
      <div>
        <label
          htmlFor="threshold"
          className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2"
        >
          Threshold:
        </label>
        <div className="flex items-center gap-2">
          <Controller
            name="threshold"
            control={control}
            render={({ field }) => (
              <input
                id="threshold"
                type="number"
                min={0}
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
                aria-label="Threshold"
                aria-invalid={!!errors.threshold}
                aria-describedby={
                  errors.threshold ? 'threshold-error' : undefined
                }
              />
            )}
          />
          {sensorUnit && (
            <span className="text-sm text-gray-700 dark:text-gray-300">
              {sensorUnit}
            </span>
          )}
        </div>
        {(errors.threshold?.message ||
          (parentErrors.threshold &&
            typeof parentErrors.threshold === 'string')) && (
          <p
            id="threshold-error"
            role="alert"
            className="mt-1 text-sm text-red-600 dark:text-red-400"
          >
            {errors.threshold?.message ||
              (parentErrors.threshold as string)}
          </p>
        )}
      </div>

      {/* Cooldown Input */}
      <div>
        <label
          htmlFor="cooldown_minutes"
          className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2"
        >
          Cooldown (minutes):
        </label>
        <div className="flex items-center gap-2">
          <Controller
            name="cooldown_minutes"
            control={control}
            render={({ field }) => (
              <input
                id="cooldown_minutes"
                type="number"
                min={1}
                max={SCHEDULE_LIMITS.MAX_COOLDOWN_MINUTES}
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
                aria-label="Cooldown in minutes"
                aria-invalid={!!errors.cooldown_minutes}
                aria-describedby={
                  errors.cooldown_minutes ? 'cooldown_minutes-error' : undefined
                }
              />
            )}
          />
          <span className="text-sm text-gray-700 dark:text-gray-300">minutes</span>
        </div>
        <p className="mt-1 text-xs text-gray-500 dark:text-gray-300">
          Minimum time between consecutive triggers
        </p>
        {(errors.cooldown_minutes?.message ||
          (parentErrors.cooldown_minutes &&
            typeof parentErrors.cooldown_minutes === 'string')) && (
          <p
            id="cooldown_minutes-error"
            role="alert"
            className="mt-1 text-sm text-red-600 dark:text-red-400"
          >
            {errors.cooldown_minutes?.message ||
              (parentErrors.cooldown_minutes as string)}
          </p>
        )}
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
