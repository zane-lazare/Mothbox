import { useEffect, useRef } from 'react'
import { useForm, Controller, useWatch } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import type { Resolver } from 'react-hook-form'
import {
  timeWindowSchema,
  type TimeWindowFormData,
} from '../../../schemas/scheduler/time-window'
import { SOLAR_EVENTS, TIME_FORMAT_REGEX, isValidSolarEvent } from './constants'

// ── Types ──────────────────────────────────────────────────────────────

export interface TimeWindowValue {
  start_time: string
  end_time: string
  start_offset_minutes: number
  end_offset_minutes: number
}

interface TimeWindowInputProps {
  value?: TimeWindowValue
  onChange: (value: TimeWindowValue) => void
  disabled?: boolean
  showSolarEvents?: boolean
  errors?: Record<string, string>
}

// ── Constants ──────────────────────────────────────────────────────────

const DEFAULT_VALUE: TimeWindowValue = {
  start_time: '',
  end_time: '',
  start_offset_minutes: 0,
  end_offset_minutes: 0,
}

// ── Formatting helpers ─────────────────────────────────────────────────

function getSolarEventLabel(eventValue: string): string {
  const event = SOLAR_EVENTS.find((e) => e.value === eventValue)
  return event ? event.label : eventValue
}

function getSolarPreviewText(
  eventValue: string,
  offsetMinutes: number,
): string | null {
  if (!eventValue || TIME_FORMAT_REGEX.test(eventValue)) return null
  const label = getSolarEventLabel(eventValue)
  const offset = offsetMinutes || 0
  if (offset === 0) return `At ${label.toLowerCase()}`
  if (offset > 0)
    return `${offset} minute${offset !== 1 ? 's' : ''} after ${label.toLowerCase()}`
  return `${Math.abs(offset)} minute${Math.abs(offset) !== 1 ? 's' : ''} before ${label.toLowerCase()}`
}

function getMixedTimeWindowWarning(
  startIsFixed: boolean,
  endIsFixed: boolean,
): string | null {
  if (startIsFixed === endIsFixed) return null
  return 'Note: Mixing fixed time with solar event may result in time windows that vary with sunrise/sunset times.'
}

// ── Component ──────────────────────────────────────────────────────────

// Zod 4 + @hookform/resolvers type workaround (@hookform/resolvers@3.x + zod@4.x)
// TODO(#449): remove cast when resolvers#800 is fixed
// Upstream: https://github.com/react-hook-form/resolvers/issues/800
const resolver = zodResolver(
  timeWindowSchema as unknown as Parameters<typeof zodResolver>[0],
) as unknown as Resolver<TimeWindowFormData>

export default function TimeWindowInput({
  value = DEFAULT_VALUE,
  onChange,
  disabled = false,
  showSolarEvents = true,
  errors: parentErrors = {},
}: TimeWindowInputProps) {
  const onChangeRef = useRef(onChange)
  onChangeRef.current = onChange

  const valueRef = useRef(value)
  valueRef.current = value

  const lastPropagatedRef = useRef({
    start_time: value.start_time,
    end_time: value.end_time,
    start_offset_minutes: value.start_offset_minutes,
    end_offset_minutes: value.end_offset_minutes,
  })

  const {
    control,
    reset,
    formState: { errors },
    watch,
  } = useForm<TimeWindowFormData>({
    resolver,
    defaultValues: {
      start_time: value.start_time,
      end_time: value.end_time,
      start_offset_minutes: value.start_offset_minutes,
      end_offset_minutes: value.end_offset_minutes,
    },
    mode: 'onChange',
  })

  // Derive mode from watched values — no useState
  const startTime = watch('start_time')
  const endTime = watch('end_time')
  const startIsFixedTime = !startTime || TIME_FORMAT_REGEX.test(startTime)
  const endIsFixedTime = !endTime || TIME_FORMAT_REGEX.test(endTime)

  // Console.warn for invalid solar event values (preserves original behavior)
  useEffect(() => {
    if (
      value.start_time &&
      !TIME_FORMAT_REGEX.test(value.start_time) &&
      !isValidSolarEvent(value.start_time)
    ) {
      console.warn(`Invalid solar event: ${value.start_time}`)
    }
    if (
      value.end_time &&
      !TIME_FORMAT_REGEX.test(value.end_time) &&
      !isValidSolarEvent(value.end_time)
    ) {
      console.warn(`Invalid solar event: ${value.end_time}`)
    }
  }, [value.start_time, value.end_time])

  // Prop-sync: reset form when value changes externally
  useEffect(() => {
    const last = lastPropagatedRef.current
    if (
      value.start_time !== last.start_time ||
      value.end_time !== last.end_time ||
      value.start_offset_minutes !== last.start_offset_minutes ||
      value.end_offset_minutes !== last.end_offset_minutes
    ) {
      lastPropagatedRef.current = {
        start_time: value.start_time,
        end_time: value.end_time,
        start_offset_minutes: value.start_offset_minutes,
        end_offset_minutes: value.end_offset_minutes,
      }
      reset({
        start_time: value.start_time,
        end_time: value.end_time,
        start_offset_minutes: value.start_offset_minutes,
        end_offset_minutes: value.end_offset_minutes,
      })
    }
  }, [
    value.start_time,
    value.end_time,
    value.start_offset_minutes,
    value.end_offset_minutes,
    reset,
  ])

  // Propagate validated form changes → parent
  const watchedStartTime = useWatch({ control, name: 'start_time' })
  const watchedEndTime = useWatch({ control, name: 'end_time' })
  const watchedStartOffset = useWatch({
    control,
    name: 'start_offset_minutes',
  })
  const watchedEndOffset = useWatch({ control, name: 'end_offset_minutes' })
  useEffect(() => {
    if (
      watchedStartTime === undefined ||
      watchedEndTime === undefined ||
      watchedStartOffset === undefined ||
      watchedEndOffset === undefined
    )
      return
    const current = valueRef.current
    if (
      watchedStartTime === current.start_time &&
      watchedEndTime === current.end_time &&
      watchedStartOffset === current.start_offset_minutes &&
      watchedEndOffset === current.end_offset_minutes
    )
      return
    const result = timeWindowSchema.safeParse({
      start_time: watchedStartTime,
      end_time: watchedEndTime,
      start_offset_minutes: watchedStartOffset,
      end_offset_minutes: watchedEndOffset,
    })
    if (!result.success) return
    lastPropagatedRef.current = {
      start_time: watchedStartTime,
      end_time: watchedEndTime,
      start_offset_minutes: watchedStartOffset,
      end_offset_minutes: watchedEndOffset,
    }
    onChangeRef.current({
      start_time: watchedStartTime,
      end_time: watchedEndTime,
      start_offset_minutes: watchedStartOffset,
      end_offset_minutes: watchedEndOffset,
    })
  }, [watchedStartTime, watchedEndTime, watchedStartOffset, watchedEndOffset])

  // Mode switching — bypass form, call onChange directly (like presets)
  const handleStartTypeChange = (isFixed: boolean) => {
    const newValue = {
      ...valueRef.current,
      start_time: isFixed ? '' : SOLAR_EVENTS[0].value,
      start_offset_minutes: 0,
    }
    lastPropagatedRef.current = newValue
    onChangeRef.current(newValue)
  }

  const handleEndTypeChange = (isFixed: boolean) => {
    const newValue = {
      ...valueRef.current,
      end_time: isFixed ? '' : SOLAR_EVENTS[0].value,
      end_offset_minutes: 0,
    }
    lastPropagatedRef.current = newValue
    onChangeRef.current(newValue)
  }

  const mixedTimeWarning = getMixedTimeWindowWarning(
    startIsFixedTime,
    endIsFixedTime,
  )

  return (
    <div className="space-y-6">
      {/* Start Time */}
      <div>
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
          Start Time
        </label>

        {showSolarEvents && (
          <div className="mb-3 flex gap-4">
            <label className="flex items-center">
              <input
                type="radio"
                name="start-time-type"
                checked={startIsFixedTime}
                onChange={() => handleStartTypeChange(true)}
                disabled={disabled}
                className="mr-2 focus:ring-2 focus:ring-blue-500"
              />
              <span className="text-sm text-gray-700 dark:text-gray-300">
                Fixed Time
              </span>
            </label>
            <label className="flex items-center">
              <input
                type="radio"
                name="start-time-type"
                checked={!startIsFixedTime}
                onChange={() => handleStartTypeChange(false)}
                disabled={disabled}
                className="mr-2 focus:ring-2 focus:ring-blue-500"
              />
              <span className="text-sm text-gray-700 dark:text-gray-300">
                Solar Event
              </span>
            </label>
          </div>
        )}

        {startIsFixedTime ? (
          <div>
            <Controller
              name="start_time"
              control={control}
              render={({ field }) => (
                <input
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
                  aria-label="Start time (fixed)"
                  data-testid="time-window-start"
                  aria-invalid={
                    !!(errors.start_time || parentErrors.start_time)
                  }
                  aria-describedby={
                    errors.start_time || parentErrors.start_time
                      ? 'start_time-error'
                      : undefined
                  }
                />
              )}
            />
          </div>
        ) : (
          <div className="space-y-2">
            <div className="flex gap-2">
              <Controller
                name="start_time"
                control={control}
                render={({ field }) => (
                  <select
                    value={field.value}
                    onChange={(e) => field.onChange(e.target.value)}
                    onBlur={field.onBlur}
                    ref={field.ref}
                    disabled={disabled}
                    className="flex-1 rounded-md border border-gray-300 dark:border-gray-600
                             bg-white dark:bg-gray-800 px-3 py-2 text-gray-900 dark:text-white
                             focus:ring-2 focus:ring-blue-500 focus:border-transparent
                             disabled:opacity-50 disabled:cursor-not-allowed"
                    aria-label="Start time (solar event)"
                    aria-invalid={
                      !!(errors.start_time || parentErrors.start_time)
                    }
                    aria-describedby={
                      errors.start_time || parentErrors.start_time
                        ? 'start_time-error'
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

              <div className="flex items-center gap-2">
                <label
                  htmlFor="start_offset"
                  className="text-sm text-gray-700 dark:text-gray-300 whitespace-nowrap"
                >
                  Offset:
                </label>
                <Controller
                  name="start_offset_minutes"
                  control={control}
                  render={({ field }) => (
                    <input
                      id="start_offset"
                      type="number"
                      min={-120}
                      max={120}
                      value={Number.isNaN(field.value) ? '' : field.value}
                      onChange={(e) => {
                        const raw = e.target.value
                        field.onChange(raw === '' ? NaN : Number(raw))
                      }}
                      onBlur={field.onBlur}
                      ref={field.ref}
                      disabled={disabled}
                      className="w-20 rounded-md border border-gray-300 dark:border-gray-600
                               bg-white dark:bg-gray-800 px-2 py-2 text-gray-900 dark:text-white
                               focus:ring-2 focus:ring-blue-500 focus:border-transparent
                               disabled:opacity-50 disabled:cursor-not-allowed"
                      aria-label="Start time offset (minutes)"
                    />
                  )}
                />
                <span className="text-sm text-gray-500 dark:text-gray-300">
                  min
                </span>
              </div>
            </div>

            {startTime && (
              <p className="text-sm text-gray-600 dark:text-gray-300 italic">
                {getSolarPreviewText(startTime, value.start_offset_minutes)}
              </p>
            )}
          </div>
        )}

        {(errors.start_time?.message || parentErrors.start_time) && (
          <p
            id="start_time-error"
            role="alert"
            className="mt-1 text-sm text-red-600 dark:text-red-400"
          >
            {errors.start_time?.message || parentErrors.start_time}
          </p>
        )}
      </div>

      {/* End Time — mirrors start time structure exactly */}
      <div>
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
          End Time
        </label>

        {showSolarEvents && (
          <div className="mb-3 flex gap-4">
            <label className="flex items-center">
              <input
                type="radio"
                name="end-time-type"
                checked={endIsFixedTime}
                onChange={() => handleEndTypeChange(true)}
                disabled={disabled}
                className="mr-2 focus:ring-2 focus:ring-blue-500"
              />
              <span className="text-sm text-gray-700 dark:text-gray-300">
                Fixed Time
              </span>
            </label>
            <label className="flex items-center">
              <input
                type="radio"
                name="end-time-type"
                checked={!endIsFixedTime}
                onChange={() => handleEndTypeChange(false)}
                disabled={disabled}
                className="mr-2 focus:ring-2 focus:ring-blue-500"
              />
              <span className="text-sm text-gray-700 dark:text-gray-300">
                Solar Event
              </span>
            </label>
          </div>
        )}

        {endIsFixedTime ? (
          <div>
            <Controller
              name="end_time"
              control={control}
              render={({ field }) => (
                <input
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
                  aria-label="End time (fixed)"
                  data-testid="time-window-end"
                  aria-invalid={
                    !!(errors.end_time || parentErrors.end_time)
                  }
                  aria-describedby={
                    errors.end_time || parentErrors.end_time
                      ? 'end_time-error'
                      : undefined
                  }
                />
              )}
            />
          </div>
        ) : (
          <div className="space-y-2">
            <div className="flex gap-2">
              <Controller
                name="end_time"
                control={control}
                render={({ field }) => (
                  <select
                    value={field.value}
                    onChange={(e) => field.onChange(e.target.value)}
                    onBlur={field.onBlur}
                    ref={field.ref}
                    disabled={disabled}
                    className="flex-1 rounded-md border border-gray-300 dark:border-gray-600
                             bg-white dark:bg-gray-800 px-3 py-2 text-gray-900 dark:text-white
                             focus:ring-2 focus:ring-blue-500 focus:border-transparent
                             disabled:opacity-50 disabled:cursor-not-allowed"
                    aria-label="End time (solar event)"
                    aria-invalid={
                      !!(errors.end_time || parentErrors.end_time)
                    }
                    aria-describedby={
                      errors.end_time || parentErrors.end_time
                        ? 'end_time-error'
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

              <div className="flex items-center gap-2">
                <label
                  htmlFor="end_offset"
                  className="text-sm text-gray-700 dark:text-gray-300 whitespace-nowrap"
                >
                  Offset:
                </label>
                <Controller
                  name="end_offset_minutes"
                  control={control}
                  render={({ field }) => (
                    <input
                      id="end_offset"
                      type="number"
                      min={-120}
                      max={120}
                      value={Number.isNaN(field.value) ? '' : field.value}
                      onChange={(e) => {
                        const raw = e.target.value
                        field.onChange(raw === '' ? NaN : Number(raw))
                      }}
                      onBlur={field.onBlur}
                      ref={field.ref}
                      disabled={disabled}
                      className="w-20 rounded-md border border-gray-300 dark:border-gray-600
                               bg-white dark:bg-gray-800 px-2 py-2 text-gray-900 dark:text-white
                               focus:ring-2 focus:ring-blue-500 focus:border-transparent
                               disabled:opacity-50 disabled:cursor-not-allowed"
                      aria-label="End time offset (minutes)"
                    />
                  )}
                />
                <span className="text-sm text-gray-500 dark:text-gray-300">
                  min
                </span>
              </div>
            </div>

            {endTime && (
              <p className="text-sm text-gray-600 dark:text-gray-300 italic">
                {getSolarPreviewText(endTime, value.end_offset_minutes)}
              </p>
            )}
          </div>
        )}

        {(errors.end_time?.message || parentErrors.end_time) && (
          <p
            id="end_time-error"
            role="alert"
            className="mt-1 text-sm text-red-600 dark:text-red-400"
          >
            {errors.end_time?.message || parentErrors.end_time}
          </p>
        )}
      </div>

      {/* Mixed Time Window Warning */}
      {mixedTimeWarning && (
        <p className="text-sm text-amber-600 dark:text-amber-400">
          {mixedTimeWarning}
        </p>
      )}

      {/* General Errors */}
      {parentErrors.general && (
        <p
          id="general-error"
          role="alert"
          className="text-sm text-red-600 dark:text-red-400"
        >
          {parentErrors.general}
        </p>
      )}
    </div>
  )
}
