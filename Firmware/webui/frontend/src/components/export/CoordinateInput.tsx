import { useState, useEffect, useId, useRef } from 'react'
import { useForm, Controller, useWatch } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import type { Resolver } from 'react-hook-form'
import { formatCoordinateDisplay } from '../../utils/gpsCoordinates'
import { coordinatesSchema, type CoordinatesFormData } from '../../schemas/coordinates'

interface CoordinateInputProps {
  latitude: number | null
  longitude: number | null
  onChange: (coords: { latitude: number | null; longitude: number | null }) => void
  error?: string | null
  disabled?: boolean
}

export default function CoordinateInput({
  latitude,
  longitude,
  onChange,
  error = null,
  disabled = false,
}: CoordinateInputProps) {
  const [showDMS, setShowDMS] = useState(false)
  const uid = useId()

  // Track last values propagated to parent, so prop-sync can distinguish
  // "our own updates echoing back" from "external updates" (e.g., GPS auto-fill)
  const lastPropagatedRef = useRef({
    latitude: latitude ?? null,
    longitude: longitude ?? null,
  })

  // Stable callback ref — prevents effect re-runs when parent passes inline arrow
  const onChangeRef = useRef(onChange)
  onChangeRef.current = onChange

  // Zod 4 + @hookform/resolvers type workaround
  // TODO: remove cast when resolvers#800 is fixed
  // Upstream: https://github.com/react-hook-form/resolvers/issues/800
  const resolver = zodResolver(
    coordinatesSchema as unknown as Parameters<typeof zodResolver>[0],
  ) as unknown as Resolver<CoordinatesFormData>

  const {
    control,
    reset,
    formState: { errors },
  } = useForm<CoordinatesFormData>({
    resolver,
    defaultValues: {
      latitude: latitude ?? null,
      longitude: longitude ?? null,
    },
    mode: 'onBlur',
  })

  // Sync parent props → form (only for external updates, not our own echoes)
  useEffect(() => {
    const incomingLat = latitude ?? null
    const incomingLon = longitude ?? null
    const { latitude: lastLat, longitude: lastLon } = lastPropagatedRef.current
    if (incomingLat !== lastLat || incomingLon !== lastLon) {
      lastPropagatedRef.current = { latitude: incomingLat, longitude: incomingLon }
      // Parent value wins (e.g., GPS auto-fill). reset() also clears any user error state — intentional.
      reset({ latitude: incomingLat, longitude: incomingLon })
    }
  }, [latitude, longitude, reset])

  // Propagate valid form changes → parent (only valid values, matching pre-migration behavior)
  const watched = useWatch({ control })
  useEffect(() => {
    const lat = watched.latitude ?? null
    const lon = watched.longitude ?? null
    // Skip if values match props (avoids cycle from prop sync)
    if (lat === (latitude ?? null) && lon === (longitude ?? null)) return
    // Second validation gate (separate from zodResolver's onBlur validation):
    // ensures parent never receives NaN or out-of-range values while user is mid-edit.
    const result = coordinatesSchema.safeParse({ latitude: lat, longitude: lon })
    if (!result.success) return
    lastPropagatedRef.current = { latitude: lat, longitude: lon }
    onChangeRef.current({ latitude: lat, longitude: lon })
  }, [watched.latitude, watched.longitude, latitude, longitude])

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
          GPS Coordinates
        </label>
        {watched.latitude != null && watched.longitude != null && (
          <button
            type="button"
            onClick={() => setShowDMS(!showDMS)}
            aria-label="Toggle format"
            className="text-xs text-blue-600 dark:text-blue-400 hover:underline"
            disabled={disabled}
          >
            {showDMS ? 'Show Decimal' : 'Show DMS'}
          </button>
        )}
      </div>

      {/* Decimal inputs */}
      {!showDMS && (
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label htmlFor={`${uid}-latitude`} className="block text-xs text-gray-600 dark:text-gray-400 mb-1">
              Latitude
            </label>
            <Controller
              name="latitude"
              control={control}
              render={({ field }) => (
                <input
                  id={`${uid}-latitude`}
                  type="number"
                  step="0.000001"
                  min="-90"
                  max="90"
                  value={field.value ?? ''}
                  onChange={(e) => {
                    const val = e.target.value
                    field.onChange(val === '' ? null : parseFloat(val))
                  }}
                  onBlur={field.onBlur}
                  ref={field.ref}
                  disabled={disabled}
                  placeholder="e.g., 37.7749"
                  aria-invalid={!!errors.latitude}
                  aria-describedby={errors.latitude ? `${uid}-latitude-error` : undefined}
                  className={`w-full px-3 py-2 border rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent
                    dark:bg-gray-700 dark:text-gray-100
                    ${errors.latitude ? 'border-red-500' : 'border-gray-300 dark:border-gray-600'}
                    disabled:opacity-50 disabled:cursor-not-allowed`}
                />
              )}
            />
            {errors.latitude?.message && (
              <p id={`${uid}-latitude-error`} role="alert" className="text-xs text-red-600 dark:text-red-400 mt-1">
                {errors.latitude.message}
              </p>
            )}
          </div>

          <div>
            <label htmlFor={`${uid}-longitude`} className="block text-xs text-gray-600 dark:text-gray-400 mb-1">
              Longitude
            </label>
            <Controller
              name="longitude"
              control={control}
              render={({ field }) => (
                <input
                  id={`${uid}-longitude`}
                  type="number"
                  step="0.000001"
                  min="-180"
                  max="180"
                  value={field.value ?? ''}
                  onChange={(e) => {
                    const val = e.target.value
                    field.onChange(val === '' ? null : parseFloat(val))
                  }}
                  onBlur={field.onBlur}
                  ref={field.ref}
                  disabled={disabled}
                  placeholder="e.g., -122.4194"
                  aria-invalid={!!errors.longitude}
                  aria-describedby={errors.longitude ? `${uid}-longitude-error` : undefined}
                  className={`w-full px-3 py-2 border rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent
                    dark:bg-gray-700 dark:text-gray-100
                    ${errors.longitude ? 'border-red-500' : 'border-gray-300 dark:border-gray-600'}
                    disabled:opacity-50 disabled:cursor-not-allowed`}
                />
              )}
            />
            {errors.longitude?.message && (
              <p id={`${uid}-longitude-error`} role="alert" className="text-xs text-red-600 dark:text-red-400 mt-1">
                {errors.longitude.message}
              </p>
            )}
          </div>
        </div>
      )}

      {/* DMS display */}
      {showDMS && watched.latitude != null && watched.longitude != null && (
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-xs text-gray-600 dark:text-gray-400 mb-1">
              Latitude (DMS)
            </label>
            <div className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md
                          bg-gray-50 dark:bg-gray-800 text-gray-900 dark:text-gray-100">
              {formatCoordinateDisplay(watched.latitude, true, 'dms')}
            </div>
          </div>

          <div>
            <label className="block text-xs text-gray-600 dark:text-gray-400 mb-1">
              Longitude (DMS)
            </label>
            <div className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md
                          bg-gray-50 dark:bg-gray-800 text-gray-900 dark:text-gray-100">
              {formatCoordinateDisplay(watched.longitude, false, 'dms')}
            </div>
          </div>
        </div>
      )}

      {/* External error message */}
      {error && (
        <p role="alert" className="text-sm text-red-600 dark:text-red-400">
          {error}
        </p>
      )}

      <p className="text-xs text-gray-500 dark:text-gray-400">
        Latitude: -90 to 90, Longitude: -180 to 180
      </p>
    </div>
  )
}
